#!/usr/bin/env python3
"""
低品質エピソード改稿スクリプト

400-500帯のエピソードを抽出し、LLMで改稿して品質を向上させる

使用方法:
    # テスト実行（10件）
    python scripts/improve_low_quality_episodes.py --count 10 --dry-run

    # 本番実行
    python scripts/improve_low_quality_episodes.py --count 50 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# CSVパス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

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


def calculate_composite_score(scores: Dict[str, float]) -> float:
    """7軸スコアから超総合スコア(0-1000)を計算"""
    vals = [scores.get(axis, 0) for axis in SEVEN_AXIS_FIELDS if axis in scores]
    if not vals:
        return 0
    avg = sum(vals) / len(vals)
    normalized = max(0, (avg - 1.0) / 9.0)
    transformed = normalized**0.85
    return round(transformed * 1000, 1)


def find_weak_axes(row: pd.Series) -> List[str]:
    """弱い軸を特定（5.0未満）"""
    weak = []
    for axis in SEVEN_AXIS_FIELDS:
        if axis in row:
            try:
                score = float(row[axis])
                if score < 5.0:
                    weak.append((axis, score))
            except (ValueError, TypeError):
                pass
    # スコアが低い順にソート
    weak.sort(key=lambda x: x[1])
    return [axis for axis, _ in weak[:3]]  # 最も弱い3軸


def build_improvement_prompt(weak_axes: List[str], episode_text: str, person_name: str, age: int) -> str:
    """改稿用プロンプトを構築"""

    axis_instructions = {
        "surprise_score": """
【意外性を劇的に高めてください】
- 一般的なイメージと正反対の側面を追加（例: 厳格な人物の意外な趣味）
- 逆転のエピソード（例: 絶望的状況からの復活）
- 「誰もが驚いたことに」「実は〜」「周囲の予想に反して」などの表現を使用
- 淡々とした業績の羅列は避ける
""",
        "factual_density": """
【具体的な事実・数値を必ず追加してください】
- 具体的な年号（例: 1985年、2003年）を追加
- 数値データ（例: 100万部、3時間、世界2位）を追加
- 固有名詞（作品名、場所名、関係者の名前）を追加
- 検証可能な記録（史上初、〇〇賞受賞）を含める
- 「多くの」「長年にわたり」などの曖昧な表現は具体化
""",
        "empathy_score": """
【共感性を高めてください】
- 人物の感情や内面の葛藤を具体的に描写
- 読者が「自分だったら」と思える普遍的な状況を追加
- 感情的なクライマックスを明確に
- 喜び、悲しみ、苦悩、決意などの感情を具体的に
""",
        "educational_value": """
【educational_valueを高めてください】
- この経験から得られる具体的な教訓や学びを追加
- 他の人が参考にできる普遍的な知恵を含める
- 「なるほど」と思わせる洞察を追加
- 具体的な行動指針や考え方を示す
""",
        "story_quality": """
【ストーリー構成を改善してください】
- 起承転結をより明確に
- 導入で興味を引き、展開で引き込む構成に
- クライマックスと余韻を意識した構成に
- 読者を引き込む導入文から始める
""",
        "memorability_score": """
【記憶に残る要素を追加してください】
- 印象的なエピソードや名言を追加
- 視覚的に想像できる具体的なシーンを描写
- 読後も思い出したくなる印象的な結末を
""",
    }

    instructions = []
    for axis in weak_axes:
        if axis in axis_instructions:
            instructions.append(axis_instructions[axis])

    return f"""以下のエピソードを改稿して、品質を大幅に向上させてください。

【元のエピソード】
{episode_text}

【人物情報】
人物名: {person_name}
年齢: {age}歳

【改善指示】
{chr(10).join(instructions)}

【必須ルール】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 250-350文字程度
3. 元のエピソードの核心は維持しつつ、上記の改善指示に従う
4. 事実に基づいた内容を維持（架空の情報を追加しない）

改稿後のエピソード:"""


def llm_improve_episode(episode_text: str, person_name: str, age: int, weak_axes: List[str]) -> Optional[str]:
    """LLMでエピソードを改稿"""
    prompt = build_improvement_prompt(weak_axes, episode_text, person_name, age)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=600, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ 改稿エラー: {e}")
        return None


def llm_evaluate_7axis(episode_text: str) -> Optional[Dict[str, float]]:
    """LLMで7軸評価"""
    prompt = f"""以下のエピソードを7軸で評価してください。各軸1.0〜10.0点で採点してください。

【エピソード】
{episode_text}

【評価軸】
1. memorability_score: 読後も印象に残るか
2. empathy_score: 感情移入できるか
3. surprise_score: 予想外の展開があるか
4. generation_quality_score: 文章として完成度が高いか
5. educational_value: 学びや教訓があるか
6. story_quality: 構成が良いか
7. factual_density: 具体的なデータ・事実があるか

必ず以下のJSON形式のみで回答してください:
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


def get_low_quality_episodes(df: pd.DataFrame, count: int) -> pd.DataFrame:
    """400-500帯の低品質エピソードを取得"""
    low_quality = df[(df["composite_score"] >= 400) & (df["composite_score"] < 500)].copy()
    # スコアが低い順にソート
    low_quality = low_quality.sort_values("composite_score")
    return low_quality.head(count)


def improve_episode(row: pd.Series) -> Optional[Dict]:
    """1件のエピソードを改稿"""
    episode_id = row["episode_id"]
    person_id = row.get("person_id", "")  # 複合キー用に追加
    person_name = row["person_name"]
    age = int(row["age"])
    original_text = str(row["episode_text"])
    original_composite = float(row["composite_score"])

    print(f"\n{'=' * 60}")
    print(f"改稿中: {person_name} ({age}歳)")
    print(f"元スコア: {original_composite:.1f}")
    print(f"{'=' * 60}")

    # 弱軸を特定
    weak_axes = find_weak_axes(row)
    if weak_axes:
        print(f"  弱軸: {', '.join(weak_axes)}")
    else:
        weak_axes = ["surprise_score", "factual_density", "empathy_score"]
        print(f"  デフォルト弱軸: {', '.join(weak_axes)}")

    # 改稿
    print("  改稿中...")
    improved_text = llm_improve_episode(original_text, person_name, age, weak_axes)

    if not improved_text:
        print("  ❌ 改稿失敗")
        return None

    print(f"  改稿後: {improved_text[:60]}...")

    # 評価
    print("  評価中...")
    new_scores = llm_evaluate_7axis(improved_text)

    if not new_scores:
        print("  ❌ 評価失敗")
        return None

    new_composite = calculate_composite_score(new_scores)
    improvement = new_composite - original_composite

    print(f"  新スコア: {new_composite:.1f} ({'+' if improvement >= 0 else ''}{improvement:.1f})")

    # 7軸表示
    for axis in SEVEN_AXIS_FIELDS:
        score = new_scores.get(axis, 0)
        indicator = "✓" if score >= 5.0 else "△" if score >= 4.0 else "✗"
        print(f"    {indicator} {axis}: {score:.1f}")

    # 改善されたかチェック
    if new_composite <= original_composite:
        print("  ⚠️ 改善なし（スキップ）")
        return None

    print(f"  ✅ 改善成功！ (+{improvement:.1f})")

    return {
        "episode_id": episode_id,
        "person_id": person_id,  # 複合キー用に追加
        "person_name": person_name,  # 検証用に追加
        "original_text": original_text,
        "improved_text": improved_text,
        "original_composite": original_composite,
        "new_composite": new_composite,
        "improvement": improvement,
        "new_scores": new_scores,
    }


def main():
    parser = argparse.ArgumentParser(description="低品質エピソード改稿")
    parser.add_argument("--count", type=int, default=10, help="改稿件数")
    parser.add_argument("--execute", action="store_true", help="本番実行（CSVを更新）")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 低品質エピソード改稿システム")
    print("=" * 80)
    print()

    # データ読み込み
    print("データ読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  総エピソード数: {len(df):,}")

    # 低品質エピソード取得
    targets = get_low_quality_episodes(df, args.count)
    print(f"  対象エピソード: {len(targets)}件（400-500帯）")
    print()

    # 改稿ループ
    improvements = []
    for i, (idx, row) in enumerate(targets.iterrows()):
        print(f"\n[{i + 1}/{len(targets)}]")
        result = improve_episode(row)
        if result:
            improvements.append(result)
        time.sleep(0.5)  # レート制限対策

    # 結果サマリー
    print()
    print("=" * 80)
    print("改稿完了")
    print("=" * 80)
    print()
    print("【統計サマリー】")
    print(f"  対象件数: {len(targets)}")
    print(f"  改善成功: {len(improvements)}")
    print(f"  改善率: {len(improvements) / len(targets) * 100:.1f}%")

    if improvements:
        avg_improvement = sum(r["improvement"] for r in improvements) / len(improvements)
        avg_new_composite = sum(r["new_composite"] for r in improvements) / len(improvements)
        print(f"  平均改善幅: +{avg_improvement:.1f}")
        print(f"  改善後平均スコア: {avg_new_composite:.1f}")

    # CSV更新（複合キーで安全に特定）
    if args.execute and improvements:
        print()
        print("CSVを更新中...")

        updated_count = 0
        for result in improvements:
            episode_id = result["episode_id"]
            person_id = result.get("person_id")
            person_name = result.get("person_name")

            # 複合キーでユニークに特定（person_idがあれば使用）
            matches = df[df["episode_id"] == episode_id]
            if len(matches) > 1 and person_id:
                matches = matches[matches["person_id"] == person_id]

            # 安全性チェック
            if len(matches) != 1:
                if len(matches) == 0:
                    print(f"  ⚠️ 該当行なし: {episode_id}")
                else:
                    print(f"  ⚠️ 重複検出（{len(matches)}行）: {episode_id} - スキップ")
                continue

            idx = matches.index[0]

            # テキスト更新
            df.loc[idx, "episode_text"] = result["improved_text"]

            # スコア更新
            for axis, score in result["new_scores"].items():
                if axis in df.columns:
                    df.loc[idx, axis] = score

            # composite_score更新
            df.loc[idx, "composite_score"] = result["new_composite"]

            # 更新フラグ
            df.loc[idx, "source"] = "improved_v1"
            updated_count += 1

        # 保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ {updated_count}件のエピソードを更新しました（{len(improvements) - updated_count}件スキップ）")

        # レポート保存
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"improvement_report_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_processed": len(targets),
            "improved": len(improvements),
            "average_improvement": avg_improvement if improvements else 0,
            "improvements": [
                {
                    "episode_id": r["episode_id"],
                    "original_composite": r["original_composite"],
                    "new_composite": r["new_composite"],
                    "improvement": r["improvement"],
                }
                for r in improvements
            ],
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📊 レポート保存: {report_path}")
    else:
        print()
        print("⚠️ ドライランモード: CSVは更新されません")
        print("   --execute オプションで本番実行してください")


if __name__ == "__main__":
    main()
