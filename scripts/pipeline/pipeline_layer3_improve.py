#!/usr/bin/env python3
"""
3層パイプライン Layer3: 集中改稿スクリプト

Layer2で「improvement_queue」に分類されたエピソードを軸別に改稿する。

使用方法:
    # プレビュー
    python scripts/pipeline_layer3_improve.py --preview

    # 本番実行
    python scripts/pipeline_layer3_improve.py --execute

    # 件数制限
    python scripts/pipeline_layer3_improve.py --count 30 --execute

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
# Layer3 設定
# =============================================================================

LAYER3_CONFIG = {
    "api_delay": 0.5,  # API呼び出し間隔（秒）
    "final_accept_threshold": 550,  # 改稿後採用ライン
    "min_improvement": 100,  # 最小改善幅
    "max_retries": 1,  # 最大リトライ回数
}

# 7軸フィールド
SEVEN_AXIS_FIELDS = [
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "story_quality",
    "factual_density",
]

# 軸別改善プロンプト
AXIS_IMPROVEMENT_PROMPTS = {
    "memorability_score": """
【記憶に残るエピソードにしてください】
- 印象的なシーンや名言を追加
- 具体的で視覚的な描写を強化
- 読後も思い出せる特徴的な要素を入れる
""",
    "empathy_score": """
【共感性を高めてください】
- 人物の感情や内面の葛藤をより具体的に描写
- 読者が「自分だったら」と思える普遍的な状況を追加
- 感情的なクライマックスを明確に
""",
    "surprise_score": """
【意外性を劇的に高めてください - 最重要改善軸】
以下の手法を1つ以上、具体的に適用してください:

1. 逆説的事実: 「○○で有名な人物が、実は△△だった」
   例: 「天才と呼ばれた人物が、この時期は落ちこぼれだった」

2. 意外な転機: 失敗・挫折→成功、または成功→危機→再起
   例: 「全てを失った瞬間が、最大のチャンスだった」

3. 知られざる一面: 公のイメージと私的な姿のギャップ
   例: 「厳格なリーダーが、実は○○に夢中だった」

4. 意外な接点: 予想外の人物・出来事との関わり
   例: 「全く別分野の人物からの助言が運命を変えた」

5. 時代の先取り: 当時は理解されなかった先見性
   例: 「周囲に反対されたアイデアが、後に主流となった」

【禁止】ありきたりな成功譚、予想通りの展開
""",
    "generation_quality_score": """
【文章品質を向上させてください】
- 冗長な表現を削除
- 具体的で簡潔な文に書き換え
- リズム感のある文章構成に
""",
    "educational_value": """
【学びや教訓を明確にしてください】
- 普遍的な教訓や知恵を含める
- 読者が参考にできる具体的な行動や考え方
- 人生の転機となった決断の理由を明示
""",
    "story_quality": """
【ストーリー構成を改善してください】
- 起承転結を明確に
- 読者を引き込む導入
- 余韻の残る結末
""",
    "factual_density": """
【具体的な事実・数値を必ず追加してください】
- 具体的な年号（1985年、2003年など）
- 数値データ（100万部、3時間、世界2位など）
- 固有名詞（作品名、場所名、関係者名）
- 検証可能な記録（史上初、ギネス記録、○○賞など）
""",
}


@dataclass
class Layer3Stats:
    """Layer3改稿統計"""

    total_processed: int = 0
    improved_accepted: int = 0
    improvement_insufficient: int = 0
    rejected: int = 0
    api_errors: int = 0
    post_validation_failed: int = 0  # 改稿後検証で失敗した件数
    total_improvement: float = 0
    start_time: datetime = field(default_factory=datetime.now)

    def summary(self) -> Dict:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_improvement = self.total_improvement / max(1, self.improved_accepted)
        return {
            "total_processed": self.total_processed,
            "improved_accepted": self.improved_accepted,
            "improvement_insufficient": self.improvement_insufficient,
            "rejected": self.rejected,
            "api_errors": self.api_errors,
            "post_validation_failed": self.post_validation_failed,
            "success_rate": round(self.improved_accepted / max(1, self.total_processed) * 100, 1),
            "avg_improvement": round(avg_improvement, 1),
            "elapsed_seconds": round(elapsed, 1),
        }


def llm_improve_episode(
    episode_text: str,
    person_name: str,
    age: int,
    weak_axes: List[str],
) -> Optional[str]:
    """弱軸に基づいてエピソードを改稿"""

    # 弱軸の改善指示を構築
    improvement_instructions = []
    for axis in weak_axes:
        if axis in AXIS_IMPROVEMENT_PROMPTS:
            improvement_instructions.append(AXIS_IMPROVEMENT_PROMPTS[axis])

    if not improvement_instructions:
        improvement_instructions.append("全体的な品質向上を図ってください。")

    prompt = f"""以下のエピソードを改善してください。

【現在のエピソード】
{episode_text}

【改善指示】
{chr(10).join(improvement_instructions)}

【守るべきルール】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 250-320文字程度を維持
3. 元の良い部分は活かしながら、弱点を改善する
4. 事実に基づいた内容を維持する

改善後のエピソード:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ 改稿エラー: {e}")
        return None


def llm_evaluate_7axis(episode_text: str) -> Optional[Dict[str, float]]:
    """LLMに7軸評価させる"""

    prompt = f"""以下のエピソードを7軸で評価してください。各軸1.0〜10.0点で採点。

【エピソード】
{episode_text}

必ず以下のJSON形式のみで回答:
{{"memorability_score": X.X, "empathy_score": X.X, "surprise_score": X.X, "generation_quality_score": X.X, "educational_value": X.X, "story_quality": X.X, "factual_density": X.X}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=200, messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
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
    normalized = max(0, (avg - 1.0) / 9.0)
    transformed = normalized**0.85
    return round(transformed * 1000, 1)


def post_improvement_validation(episode: Dict, improved_text: str) -> tuple[bool, List[str]]:
    """
    改稿後のテキストを検証

    Args:
        episode: 元エピソードデータ
        improved_text: 改稿後テキスト

    Returns:
        (検証合格フラグ, ブロッキング問題メッセージリスト)
    """
    # 改稿後テキストで一時的なエピソードを作成
    temp_ep = episode.copy()
    temp_ep["episode_text"] = improved_text

    issues = validate_episode(temp_ep)

    # CRITICAL または WARNING は採用ブロック
    blocking_issues = [i for i in issues if i.severity in ("CRITICAL", "WARNING")]

    if blocking_issues:
        messages = [f"[{i.severity}] {i.issue_type}: {i.message}" for i in blocking_issues]
        return False, messages

    return True, []


def load_improvement_queue(limit: Optional[int] = None) -> List[Dict]:
    """改稿キューからエピソードを読み込む"""
    if not STAGING_CSV.exists():
        return []

    queue = []
    with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("layer1_status") == "improvement_queue":
                queue.append(row)
                if limit and len(queue) >= limit:
                    break

    return queue


def run_layer3(count: Optional[int], execute: bool) -> Dict:
    """
    Layer3 集中改稿を実行
    """
    print("=" * 60)
    print("🔧 Layer3: 集中改稿")
    print("=" * 60)

    # 改稿キュー読み込み
    queue = load_improvement_queue(count)
    print(f"  📋 改稿キュー: {len(queue)}件")

    if not queue:
        print("  ⚠️ 改稿対象がありません")
        return {}

    stats = Layer3Stats()
    processed_episodes = []

    for i, ep in enumerate(queue):
        stats.total_processed += 1
        person_name = ep.get("person_name", "")
        age = int(ep.get("age", 0) or 0)
        episode_text = ep.get("episode_text", "")
        original_composite = float(ep.get("composite_score", 0) or 0)
        weak_axes = ep.get("weak_axes", "").split(",") if ep.get("weak_axes") else []

        print(f"\n[{i + 1}/{len(queue)}] {person_name} ({age}歳) | 元スコア: {original_composite}")
        print(f"  弱軸: {weak_axes}")

        # 改稿
        improved_text = llm_improve_episode(episode_text, person_name, age, weak_axes)

        if not improved_text:
            stats.api_errors += 1
            ep["layer1_status"] = "improvement_failed"
            processed_episodes.append(ep)
            print("  ❌ 改稿失敗")
            continue

        time.sleep(LAYER3_CONFIG["api_delay"])

        # 再評価
        new_scores = llm_evaluate_7axis(improved_text)

        if not new_scores:
            stats.api_errors += 1
            ep["layer1_status"] = "evaluation_failed"
            processed_episodes.append(ep)
            print("  ❌ 再評価失敗")
            continue

        new_composite = calculate_composite_score(new_scores)
        improvement = new_composite - original_composite

        print(f"  → 新スコア: {new_composite} (改善幅: {improvement:+.1f})")

        # 改稿後検証（CRITICAL/WARNINGがあれば棄却）
        is_valid, blocking_messages = post_improvement_validation(ep, improved_text)
        if not is_valid:
            stats.post_validation_failed += 1
            ep["layer1_status"] = "post_validation_failed"
            ep["validation_issues"] = "; ".join(blocking_messages)
            processed_episodes.append(ep)
            print(f"  ❌ 改稿後検証失敗: {blocking_messages[0]}")
            continue

        # 判定
        if new_composite >= LAYER3_CONFIG["final_accept_threshold"] and improvement >= LAYER3_CONFIG["min_improvement"]:
            stats.improved_accepted += 1
            stats.total_improvement += improvement

            # エピソード更新
            ep["episode_text"] = improved_text
            for axis in SEVEN_AXIS_FIELDS:
                ep[axis] = str(new_scores.get(axis, ""))
            ep["composite_score"] = str(new_composite)
            ep["layer1_status"] = "improved_accepted"
            ep["improvement"] = str(improvement)

            print("  ✅ 採用")
        elif improvement < LAYER3_CONFIG["min_improvement"]:
            stats.improvement_insufficient += 1
            ep["layer1_status"] = "improvement_insufficient"
            print("  ⚠️ 改善幅不足")
        else:
            stats.rejected += 1
            ep["layer1_status"] = "rejected_after_improvement"
            print("  ❌ 棄却（スコア不足）")

        processed_episodes.append(ep)
        time.sleep(LAYER3_CONFIG["api_delay"])

    # 結果サマリ
    print("\n" + "=" * 60)
    print("📊 Layer3 改稿結果")
    print("=" * 60)
    summary = stats.summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if not execute:
        print("\n⚠️ --execute オプションなし: 保存スキップ")
        return summary

    # ステージングCSV更新
    all_episodes = []
    fieldnames = []
    if STAGING_CSV.exists():
        with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                ep_id = row.get("episode_id", "")
                updated = next((e for e in processed_episodes if e.get("episode_id") == ep_id), None)
                if updated:
                    all_episodes.append(updated)
                else:
                    all_episodes.append(row)

    # 新しいフィールド追加
    if "improvement" not in fieldnames:
        fieldnames.append("improvement")

    with open(STAGING_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ep in all_episodes:
            row = {k: ep.get(k, "") for k in fieldnames}
            writer.writerow(row)

    print(f"\n✅ ステージングCSV更新: {STAGING_CSV}")

    # 改稿成功エピソードをマスターに統合
    improved_accepted = [e for e in processed_episodes if e.get("layer1_status") == "improved_accepted"]
    if improved_accepted:
        merge_to_master(improved_accepted)
        print(f"✅ マスターCSVに統合: {len(improved_accepted)}件")

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"layer3_improve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "config": LAYER3_CONFIG,
                "stats": summary,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"📝 レポート保存: {report_path}")

    return summary


def merge_to_master(episodes: List[Dict]):
    """改稿成功エピソードをマスターCSVに統合"""
    if not episodes:
        return

    master_rows = []
    master_fieldnames = []
    if MASTER_CSV.exists():
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            master_fieldnames = list(reader.fieldnames or [])
            master_rows = list(reader)

    for f in SEVEN_AXIS_FIELDS + ["composite_score"]:
        if f not in master_fieldnames:
            master_fieldnames.append(f)

    for ep in episodes:
        row = {k: ep.get(k, "") for k in master_fieldnames}
        row["source"] = "pipeline_layer3"
        master_rows.append(row)

    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=master_fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)


def main():
    parser = argparse.ArgumentParser(description="Layer3 集中改稿")
    parser.add_argument("--count", type=int, help="処理件数上限")
    parser.add_argument("--preview", action="store_true", help="プレビューのみ")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    execute = args.execute and not args.preview

    run_layer3(args.count, execute)


if __name__ == "__main__":
    main()
