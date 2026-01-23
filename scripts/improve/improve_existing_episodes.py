#!/usr/bin/env python3
"""
既存低品質エピソード改善スクリプト

composite_score が低いエピソードを LLM で改稿し、品質を向上させる

使用方法:
    # プレビュー（改善候補を確認）
    python scripts/improve/improve_existing_episodes.py --preview

    # テスト実行（10件）
    python scripts/improve/improve_existing_episodes.py --count 10 --dry-run

    # 本番実行（50件、CSV更新）
    python scripts/improve/improve_existing_episodes.py --count 50 --execute

    # 特定スコア以下を対象
    python scripts/improve/improve_existing_episodes.py --threshold 450 --count 30 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
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
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# CSVパス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "data" / "backups"
REPORT_DIR = PROJECT_ROOT / "src" / "reports" / "logs"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント
client = anthropic.Anthropic(api_key=API_KEY)

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

# 品質ゲート設定
QUALITY_GATES = {
    "target_composite": 550,  # 目標ライン
    "minimum_improvement": 50,  # 最低改善幅
}


@dataclass
class ImprovementStats:
    """改善統計"""

    total_processed: int = 0
    improved: int = 0
    unchanged: int = 0
    failed: int = 0
    before_scores: List[float] = field(default_factory=list)
    after_scores: List[float] = field(default_factory=list)

    def add_result(self, before: float, after: Optional[float], improved: bool):
        self.total_processed += 1
        self.before_scores.append(before)
        if after is not None:
            self.after_scores.append(after)
            if improved:
                self.improved += 1
            else:
                self.unchanged += 1
        else:
            self.failed += 1

    def get_summary(self) -> Dict:
        before_avg = sum(self.before_scores) / len(self.before_scores) if self.before_scores else 0
        after_avg = sum(self.after_scores) / len(self.after_scores) if self.after_scores else 0

        return {
            "total_processed": self.total_processed,
            "improved": self.improved,
            "unchanged": self.unchanged,
            "failed": self.failed,
            "improvement_rate": self.improved / self.total_processed if self.total_processed > 0 else 0,
            "before_avg": round(before_avg, 1),
            "after_avg": round(after_avg, 1),
            "avg_improvement": round(after_avg - before_avg, 1),
        }


def calculate_composite_score(scores: Dict[str, float]) -> float:
    """7軸スコアから超総合スコア(0-1000)を計算"""
    vals = [scores.get(axis, 0) for axis in SEVEN_AXIS_FIELDS if axis in scores]
    if not vals:
        return 0

    avg = sum(vals) / len(vals)
    normalized = max(0, (avg - 1.0) / 9.0)
    transformed = normalized**0.85
    return round(transformed * 1000, 1)


def llm_improve_episode(
    original_text: str,
    person_name: str,
    category: str,
    age: int,
    current_scores: Dict[str, float],
) -> Optional[str]:
    """エピソードを改善"""

    # 弱い軸を特定
    weak_axes = []
    for axis in SEVEN_AXIS_FIELDS:
        score = current_scores.get(axis, 5.0)
        if score < 6.0:
            weak_axes.append(f"- {axis}: 現在{score:.1f}点")

    weak_axes_text = "\n".join(weak_axes) if weak_axes else "- 全体的に改善が必要"

    prompt = f"""以下のエピソードを「読みやすく・分かりやすく」改稿してください。

【元のエピソード】
{original_text}

【人物情報】
- 人物名: {person_name}
- カテゴリ: {category}
- 年齢: {age}歳

【改善が必要な軸】
{weak_axes_text}

【改稿の要件】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」で必ず始める
2. 文法・助詞・句読点・改行の崩れを直し、自然な日本語に整える
3. 元の文章に含まれる事実関係を絶対に変えない（誇張・創作・推測での追加は禁止）
4. 元文に無い固有名詞・年号・数値・場所・人物を新規追加しない（安全性のため）
5. 冗長さを減らし、1文を短くして読みやすくする
6. 250-320文字程度

【重要】
- 元のエピソードの良い部分は活かしつつ、弱い部分を大幅に改善
- 事実性を最優先する（文章の上手さよりも、誤情報ゼロ）

改稿後のエピソード:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ 改稿エラー: {e}")
        return None


def llm_evaluate_episode(episode_text: str) -> Optional[Dict[str, float]]:
    """エピソードを7軸評価"""

    prompt = f"""以下のエピソードを7軸で評価してください。各軸1.0〜10.0点で採点してください。

【エピソード】
{episode_text}

【評価軸と基準】
1. memorability_score: 読後も印象に残るか
2. empathy_score: 感情移入できるか
3. surprise_score: 予想外の展開があるか
4. generation_quality_score: 文章として完成度が高いか
5. educational_value: 学びや教訓があるか
6. story_quality: 構成が良いか
7. factual_density: 具体的なデータ・事実があるか

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


def get_current_scores(row: pd.Series) -> Dict[str, float]:
    """現在の7軸スコアを取得"""
    scores = {}
    for axis in SEVEN_AXIS_FIELDS:
        val = row.get(axis)
        if pd.notna(val):
            try:
                scores[axis] = float(val)
            except (ValueError, TypeError):
                scores[axis] = 5.0
        else:
            scores[axis] = 5.0
    return scores


def improve_episode(
    row: pd.Series,
    stats: ImprovementStats,
) -> Optional[Dict]:
    """1件のエピソードを改善"""

    episode_id = row["episode_id"]
    person_id = row.get("person_id", "")  # 複合キー用に追加
    person_name = row["person_name"]
    category = row["category"]
    age = int(row["age"]) if pd.notna(row["age"]) else 30
    original_text = str(row["episode_text"])
    current_scores = get_current_scores(row)
    try:
        before_composite = float(row.get("composite_score", 0) or 0)
    except (ValueError, TypeError):
        before_composite = 0.0

    print(f"\n{'='*60}")
    print(f"改善中: {episode_id} - {person_name} ({age}歳)")
    print(f"  現在スコア: {before_composite:.1f}")
    print(f"{'='*60}")

    # Step 1: 改稿
    print("  [1] 改稿生成中...")
    improved_text = llm_improve_episode(original_text, person_name, category, age, current_scores)

    if not improved_text:
        stats.add_result(before_composite, None, False)
        return None

    print(f"  改稿: {improved_text[:60]}...")

    # Step 2: 再評価
    print("  [2] 再評価中...")
    new_scores = llm_evaluate_episode(improved_text)

    if not new_scores:
        stats.add_result(before_composite, None, False)
        return None

    after_composite = calculate_composite_score(new_scores)
    improvement = after_composite - before_composite

    print(f"  新スコア: {after_composite:.1f} (改善: {improvement:+.1f})")

    # 7軸表示
    for axis in SEVEN_AXIS_FIELDS:
        old = current_scores.get(axis, 0)
        new = new_scores.get(axis, 0)
        diff = new - old
        indicator = "↑" if diff > 0.5 else "→" if diff > -0.5 else "↓"
        print(f"    {indicator} {axis}: {old:.1f} → {new:.1f}")

    # 改善判定
    # - dry-run/レポート用途では「不十分でも」成果物を残して手触り確認できるようにする
    is_approved = improvement >= QUALITY_GATES["minimum_improvement"]

    if is_approved:
        print(f"  ✅ 改善成功！ (+{improvement:.1f})")
        stats.add_result(before_composite, after_composite, True)
    else:
        print(f"  ⚠️ 改善不十分 (+{improvement:.1f} < +{QUALITY_GATES['minimum_improvement']})")
        stats.add_result(before_composite, after_composite, False)

    return {
        "episode_id": episode_id,
        "person_id": person_id,
        "person_name": person_name,
        "category": category,
        "age": age,
        "original_text": original_text,
        "episode_text": improved_text,  # 互換: CSV更新で使うキー
        "before_composite_score": before_composite,
        "composite_score": after_composite,
        **new_scores,
        "improved_at": datetime.now().isoformat(),
        "improvement": improvement,
        "approved": is_approved,
    }


def create_backup(df: pd.DataFrame) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"📦 バックアップ作成: {backup_path}")
    return backup_path


def main():
    parser = argparse.ArgumentParser(description="既存低品質エピソード改善")
    parser.add_argument("--threshold", type=float, default=500, help="改善対象の閾値（この値未満を対象）")
    parser.add_argument("--count", type=int, default=10, help="処理件数")
    parser.add_argument("--preview", action="store_true", help="改善候補のプレビューのみ")
    parser.add_argument("--execute", action="store_true", help="本番実行（CSV更新）")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（改善実行するがCSV更新しない）")

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 既存エピソード改善システム v1.0")
    print("=" * 80)
    print()

    # CSV読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"📁 読み込み: {len(df):,}件")

    # 改善対象を抽出
    low_quality = df[df["composite_score"] < args.threshold].copy()
    low_quality = low_quality.sort_values("composite_score", ascending=True)

    print(f"📊 改善対象 (スコア < {args.threshold}): {len(low_quality):,}件")
    print()

    if args.preview:
        # プレビューモード
        print("【改善候補TOP20】")
        print(f"{'No':>3} | {'episode_id':^15} | {'person_name':^20} | {'score':>6}")
        print("-" * 60)
        for i, (_, row) in enumerate(low_quality.head(20).iterrows(), 1):
            print(f"{i:3} | {row['episode_id']:^15} | {row['person_name'][:20]:^20} | {row['composite_score']:6.1f}")
        print()

        # スコア分布
        print("【スコア分布】")
        bins = [(0, 350), (350, 400), (400, 450), (450, 500)]
        for low, high in bins:
            count = len(low_quality[(low_quality["composite_score"] >= low) & (low_quality["composite_score"] < high)])
            print(f"  {low}-{high}: {count:,}件")
        return

    # 処理対象を選択
    targets = low_quality.head(args.count)
    print(f"処理対象: {len(targets)}件")
    print()

    # 統計
    stats = ImprovementStats()
    improvements: list[dict] = []

    # 改善ループ
    print("=" * 80)
    print("改善開始")
    print("=" * 80)

    for i, (idx, row) in enumerate(targets.iterrows(), 1):
        print(f"\n[{i}/{len(targets)}]")

        result = improve_episode(row, stats)
        if result:
            improvements.append(result)

        # レート制限対策
        time.sleep(0.5)

    # サマリー
    print(f"\n{'='*80}")
    print("改善完了")
    print(f"{'='*80}")

    summary = stats.get_summary()
    print("\n【統計サマリー】")
    print(f"  処理数: {summary['total_processed']}")
    print(f"  改善成功: {summary['improved']} ({summary['improvement_rate']*100:.1f}%)")
    print(f"  改善不十分: {summary['unchanged']}")
    print(f"  失敗: {summary['failed']}")
    print(f"  改善前平均: {summary['before_avg']:.1f}")
    print(f"  改善後平均: {summary['after_avg']:.1f}")
    print(f"  平均改善幅: +{summary['avg_improvement']:.1f}")
    print()

    # CSV更新（approvedのみ反映）
    approved = [imp for imp in improvements if imp.get("approved") is True]

    if args.execute and approved:
        print("【CSV更新】")

        # バックアップ
        create_backup(df)

        # 更新（複合キーで安全に特定）
        for imp in approved:
            episode_id = imp["episode_id"]
            person_id = imp.get("person_id")
            person_name = imp.get("person_name")

            # 複合キーでユニークに特定（person_idがあれば使用）
            if person_id:
                mask = (df["episode_id"] == episode_id) & (df["person_id"] == person_id)
            else:
                mask = df["episode_id"] == episode_id

            # 安全性チェック: 複数行マッチや0行マッチを検出
            match_count = mask.sum()
            if match_count != 1:
                if match_count == 0:
                    print(f"  ⚠️ 該当行なし: {episode_id}")
                else:
                    print(f"  ⚠️ 重複検出（{match_count}行）: {episode_id} - スキップ")
                continue

            df.loc[mask, "episode_text"] = imp["episode_text"]
            df.loc[mask, "composite_score"] = imp["composite_score"]
            for axis in SEVEN_AXIS_FIELDS:
                if axis in imp:
                    df.loc[mask, axis] = imp[axis]

        # 保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ CSV更新完了: {len(approved)}件を改善（承認済みのみ反映）")

    elif improvements:
        print("⚠️ ドライランモード: CSV更新は行いません")
        print("   --execute オプションで本番実行してください（承認済みのみ反映されます）")

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"improvement_report_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "threshold": args.threshold,
        "statistics": summary,
        "improvements": [
            {
                "episode_id": imp.get("episode_id"),
                "person_name": imp.get("person_name"),
                "age": imp.get("age"),
                "before_composite_score": imp.get("before_composite_score"),
                "after_composite_score": imp.get("composite_score"),
                "improvement": imp.get("improvement"),
                "approved": imp.get("approved"),
                # 手触り確認: 文章のbefore/after（10件程度なので全文を保存）
                "original_text": imp.get("original_text"),
                "improved_text": imp.get("episode_text"),
            }
            for imp in improvements
        ],
        "approved_count": len(approved),
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📊 レポート保存: {report_path}")


if __name__ == "__main__":
    main()
