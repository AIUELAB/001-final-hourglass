#!/usr/bin/env python3
"""
3層パイプライン Layer2: バッチ評価スクリプト

Layer1で生成されたエピソードを7軸評価し、スコア帯別に分類する。

使用方法:
    # 評価のみ（分類確認）
    python scripts/pipeline_layer2_evaluate.py --preview

    # 本番実行（評価 + 分類）
    python scripts/pipeline_layer2_evaluate.py --execute

    # 件数制限
    python scripts/pipeline_layer2_evaluate.py --count 50 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# バリデータインポート
from scripts.validation.episode_validator import validate_episode

# CSVパス
STAGING_CSV = PROJECT_ROOT / "generated" / "pipeline_staging.csv"
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント
client = anthropic.Anthropic(api_key=API_KEY)


# =============================================================================
# Layer2 設定
# =============================================================================

LAYER2_CONFIG = {
    "api_delay": 0.4,  # API呼び出し間隔（秒）
    "auto_accept_threshold": 600,  # 即採用ライン
    "improvement_queue_min": 400,  # 改稿キュー最低ライン
    "rejection_threshold": 400,  # 棄却ライン
    # 事実密度ゲート（新規追加 - EPUP Phase2）
    "fact_density_minimum": 3.5,  # これ未満は自動リジェクト
    "fact_density_preferred": 5.0,  # これ未満は警告
    "surprise_fiction_threshold": 8.5,  # これ以上は架空の疑い
}

# 7軸フィールド
SEVEN_AXIS_FIELDS = [
    "記憶性スコア",
    "共感性スコア",
    "意外性スコア",
    "生成品質スコア",
    "教育的価値",
    "ストーリー品質",
    "事実密度",
]


@dataclass
class Layer2Stats:
    """Layer2評価統計"""

    total_evaluated: int = 0
    auto_accepted: int = 0
    improvement_queue: int = 0
    rejected: int = 0
    api_errors: int = 0
    pre_validation_failed: int = 0  # 評価前検証で失敗した件数
    start_time: datetime = field(default_factory=datetime.now)

    def summary(self) -> Dict:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            "total_evaluated": self.total_evaluated,
            "auto_accepted": self.auto_accepted,
            "improvement_queue": self.improvement_queue,
            "rejected": self.rejected,
            "api_errors": self.api_errors,
            "pre_validation_failed": self.pre_validation_failed,
            "auto_accept_rate": round(self.auto_accepted / max(1, self.total_evaluated) * 100, 1),
            "rejection_rate": round(self.rejected / max(1, self.total_evaluated) * 100, 1),
            "elapsed_seconds": round(elapsed, 1),
        }


def llm_evaluate_7axis(episode_text: str) -> Optional[Dict[str, float]]:
    """LLMに7軸評価させる"""

    prompt = f"""以下のエピソードを7軸で評価してください。各軸1.0〜10.0点で採点してください。

【エピソード】
{episode_text}

【評価軸】
1. 記憶性スコア: 読後も印象に残るか
2. 共感性スコア: 感情移入できるか
3. 意外性スコア: 予想外の展開があるか
4. 生成品質スコア: 文章として完成度が高いか
5. 教育的価値: 学びや教訓があるか
6. ストーリー品質: 構成が良いか
7. 事実密度: 具体的なデータ・事実があるか

必ず以下のJSON形式のみで回答してください:
{{"記憶性スコア": X.X, "共感性スコア": X.X, "意外性スコア": X.X, "生成品質スコア": X.X, "教育的価値": X.X, "ストーリー品質": X.X, "事実密度": X.X}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=200, messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        # JSON部分を抽出
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        print(f"  ❌ 評価エラー: {e}")
        return None


def calculate_composite_score(scores: Dict[str, float]) -> float:
    """7軸スコアから超総合スコア(0-1000)を計算"""
    vals = [scores.get(axis, 0) for axis in SEVEN_AXIS_FIELDS if axis in scores]
    if not vals:
        return 0

    avg = sum(vals) / len(vals)
    # 正規化 (1-10 → 0-1) → 非線形変換 (k=0.85) → 0-1000スケール
    normalized = max(0, (avg - 1.0) / 9.0)
    transformed = normalized**0.85
    return round(transformed * 1000, 1)


def find_weak_axes(scores: Dict[str, float], threshold: float = 5.0) -> List[str]:
    """弱軸を特定"""
    weak = []
    for axis in SEVEN_AXIS_FIELDS:
        if scores.get(axis, 0) < threshold:
            weak.append(axis)
    return weak[:3]  # 最大3軸


def classify_episode(composite_score: float, scores: Dict[str, float] = None) -> tuple[str, str]:
    """スコアに基づいて分類（事実密度ゲート付き - EPUP Phase2）

    Returns: (classification, reason)
    """
    # Gate 1: 事実密度チェック（最優先）
    if scores:
        fact_density = scores.get("事実密度", 10)  # デフォルト高め（スコア未取得時はパス）
        if fact_density < LAYER2_CONFIG["fact_density_minimum"]:
            return "rejected", f"事実密度不足: {fact_density:.1f} < 3.5"

        # Gate 2: 意外性異常検知（架空エピソードの疑い）
        surprise = scores.get("意外性スコア", 0)
        if surprise > LAYER2_CONFIG["surprise_fiction_threshold"]:
            return "improvement_queue", f"意外性過多（架空の疑い）: {surprise:.1f}"

    # Gate 3: 従来のcomposite_scoreベース分類
    if composite_score >= LAYER2_CONFIG["auto_accept_threshold"]:
        return "auto_accept", "高品質"
    elif composite_score >= LAYER2_CONFIG["improvement_queue_min"]:
        return "improvement_queue", "改稿推奨"
    else:
        return "rejected", f"低品質: {composite_score:.0f}"


def pre_evaluate_validation(episode: Dict) -> tuple[bool, List[str]]:
    """
    7軸評価前の事前検証

    Args:
        episode: エピソードデータ

    Returns:
        (検証合格フラグ, CRITICALメッセージリスト)
    """
    issues = validate_episode(episode)
    critical_issues = [i for i in issues if i.severity == "CRITICAL"]

    if critical_issues:
        messages = [f"{i.issue_type}: {i.message}" for i in critical_issues]
        return False, messages

    return True, []


def load_pending_episodes(limit: Optional[int] = None) -> List[Dict]:
    """評価待ちエピソードを読み込む"""
    if not STAGING_CSV.exists():
        return []

    pending = []
    with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("layer1_status") == "pending_evaluation":
                pending.append(row)
                if limit and len(pending) >= limit:
                    break

    return pending


def run_layer2(count: Optional[int], execute: bool) -> Dict:
    """
    Layer2 バッチ評価を実行
    """
    print("=" * 60)
    print("📊 Layer2: バッチ評価・分類")
    print("=" * 60)

    # 評価待ちエピソード読み込み
    pending = load_pending_episodes(count)
    print(f"  📋 評価待ち: {len(pending)}件")

    if not pending:
        print("  ⚠️ 評価待ちエピソードがありません")
        return {}

    stats = Layer2Stats()
    evaluated_episodes = []

    for i, ep in enumerate(pending):
        stats.total_evaluated += 1
        person_name = ep.get("person_name", "")
        age = ep.get("age", "")
        episode_text = ep.get("episode_text", "")

        print(f"\n[{i+1}/{len(pending)}] {person_name} ({age}歳) ...", end=" ")

        # 評価前検証（CRITICAL問題があればスキップ）
        is_valid, critical_messages = pre_evaluate_validation(ep)
        if not is_valid:
            stats.pre_validation_failed += 1
            ep["layer1_status"] = "pre_validation_failed"
            ep["validation_issues"] = "; ".join(critical_messages)
            evaluated_episodes.append(ep)
            print(f"❌ 事前検証失敗: {critical_messages[0]}")
            continue

        # 7軸評価
        scores = llm_evaluate_7axis(episode_text)

        if not scores:
            stats.api_errors += 1
            ep["layer1_status"] = "evaluation_failed"
            evaluated_episodes.append(ep)
            print("❌ 評価失敗")
            continue

        # 超総合スコア計算
        composite = calculate_composite_score(scores)
        classification, reason = classify_episode(composite, scores)  # EPUP Phase2: 事実密度ゲート対応
        weak_axes = find_weak_axes(scores)

        # スコアをエピソードに追加
        for axis in SEVEN_AXIS_FIELDS:
            ep[axis] = str(scores.get(axis, ""))
        ep["composite_score"] = str(composite)
        ep["weak_axes"] = ",".join(weak_axes)
        ep["classification_reason"] = reason  # 分類理由を記録

        if classification == "auto_accept":
            stats.auto_accepted += 1
            ep["layer1_status"] = "auto_accepted"
            print(f"✅ 即採用 ({composite}点)")
        elif classification == "improvement_queue":
            stats.improvement_queue += 1
            ep["layer1_status"] = "improvement_queue"
            print(f"🔄 改稿キュー ({composite}点) 理由: {reason}")
        else:
            stats.rejected += 1
            ep["layer1_status"] = "rejected"
            print(f"❌ 棄却 ({composite}点) 理由: {reason}")

        evaluated_episodes.append(ep)
        time.sleep(LAYER2_CONFIG["api_delay"])

    # 結果サマリ
    print("\n" + "=" * 60)
    print("📊 Layer2 評価結果")
    print("=" * 60)
    summary = stats.summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if not execute:
        print("\n⚠️ --execute オプションなし: 保存スキップ")
        return summary

    # ステージングCSV更新
    all_episodes = []
    if STAGING_CSV.exists():
        with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                # 評価済みエピソードで上書き
                ep_id = row.get("episode_id", "")
                updated = next((e for e in evaluated_episodes if e.get("episode_id") == ep_id), None)
                if updated:
                    all_episodes.append(updated)
                else:
                    all_episodes.append(row)

    # 新しいフィールドを追加
    extra_fields = ["composite_score", "weak_axes"] + SEVEN_AXIS_FIELDS
    for f in extra_fields:
        if f not in fieldnames:
            fieldnames.append(f)

    with open(STAGING_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ep in all_episodes:
            row = {k: ep.get(k, "") for k in fieldnames}
            writer.writerow(row)

    print(f"\n✅ ステージングCSV更新: {STAGING_CSV}")

    # 即採用エピソードをマスターに統合
    auto_accepted = [e for e in evaluated_episodes if e.get("layer1_status") == "auto_accepted"]
    if auto_accepted:
        merge_to_master(auto_accepted)
        print(f"✅ マスターCSVに統合: {len(auto_accepted)}件")

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"layer2_evaluate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "config": LAYER2_CONFIG,
                "stats": summary,
                "classification_breakdown": {
                    "auto_accepted": stats.auto_accepted,
                    "improvement_queue": stats.improvement_queue,
                    "rejected": stats.rejected,
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"📝 レポート保存: {report_path}")

    return summary


def merge_to_master(episodes: List[Dict]):
    """即採用エピソードをマスターCSVに統合"""
    if not episodes:
        return

    # マスターCSV読み込み
    master_rows = []
    master_fieldnames = []
    if MASTER_CSV.exists():
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            master_fieldnames = list(reader.fieldnames or [])
            master_rows = list(reader)

    # 必要なフィールドを追加
    for f in SEVEN_AXIS_FIELDS + ["composite_score"]:
        if f not in master_fieldnames:
            master_fieldnames.append(f)

    # エピソード追加
    for ep in episodes:
        row = {k: ep.get(k, "") for k in master_fieldnames}
        row["source"] = "pipeline_layer2"
        master_rows.append(row)

    # 書き出し
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=master_fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)


def main():
    parser = argparse.ArgumentParser(description="Layer2 バッチ評価")
    parser.add_argument("--count", type=int, help="評価件数上限")
    parser.add_argument("--preview", action="store_true", help="プレビューのみ")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    execute = args.execute and not args.preview

    run_layer2(args.count, execute)


if __name__ == "__main__":
    main()
