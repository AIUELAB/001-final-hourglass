#!/usr/bin/env python3
"""
エピソードのドラマ性・品質を評価するスクリプト

年齢カバレッジではなく、エピソードの「読み物としての価値」を評価する。
ハードコードスコアを廃止し、LLMによる実質的な品質評価を行う。

評価基準:
1. drama_score: 事件性・意外性・葛藤の有無 (1-10)
2. factuality_score: 事実に基づいているか (1-10)
3. memorability_score: 記憶に残るか (1-10)
4. is_fictional: 架空の出来事が主体か (true/false)

使用方法:
    # 全エピソードを評価（サンプル）
    python scripts/evaluate_episode_drama.py --sample 100

    # 特定sourceのエピソードを評価
    python scripts/evaluate_episode_drama.py --source PHASE12_AGE_EXPANSION --execute

    # 低品質候補の検出
    python scripts/evaluate_episode_drama.py --detect-low-quality --threshold 5.0
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# パス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# APIキー
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ドラマ性評価プロンプト
DRAMA_EVALUATION_PROMPT = """あなたはエピソードの品質を評価する専門家です。

以下のエピソードを評価してください。

【人物】{person_name}
【年齢】{age}歳
【カテゴリ】{category}

【エピソード】
{episode_text}

【評価基準】
1. drama_score (1-10): 読者の心を動かすか。具体的な事件・転機・葛藤があるか。
   - 1-3: 日常的な描写、特に印象に残らない
   - 4-6: 何かしらの出来事はあるが、ドラマ性は弱い
   - 7-8: 明確な転機・挑戦・葛藤がある
   - 9-10: 強烈なドラマ性、読者の心を揺さぶる

2. factuality_score (1-10): 事実に基づいているか。架空の詳細が少ないか。
   - 1-3: ほぼ架空（存在しない作品、実現していない出来事など）
   - 4-6: 一部事実だが、架空の詳細が多い
   - 7-8: 主に事実に基づいているが、推測も含む
   - 9-10: 検証可能な事実のみ

3. memorability_score (1-10): 読後に印象が残るか。
   - 1-3: すぐに忘れる
   - 4-6: 少し印象に残る
   - 7-8: 記憶に残る
   - 9-10: 強く心に刻まれる

4. is_fictional: このエピソードの中心的な出来事は架空か？
   - true: 架空の出来事が主体（存在しない作品、実現していない受賞など）
   - false: 実際に起きた出来事が主体

5. key_event: エピソードの中心となる出来事を一文で要約

6. fictional_elements: 架空と思われる要素があれば列挙（なければ空配列）

【出力形式】JSONのみを出力してください:
{{
  "drama_score": 数値,
  "factuality_score": 数値,
  "memorability_score": 数値,
  "is_fictional": true/false,
  "key_event": "文字列",
  "fictional_elements": ["要素1", "要素2"],
  "evaluation_reason": "評価理由を1-2文で"
}}"""


def evaluate_single_episode(client, episode: dict) -> dict | None:
    """単一エピソードのドラマ性を評価"""
    prompt = DRAMA_EVALUATION_PROMPT.format(
        person_name=episode.get("person_name", "不明"),
        age=episode.get("age", "不明"),
        category=episode.get("category", "不明"),
        episode_text=episode.get("episode_text", ""),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.0,  # 評価は一貫性を重視
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()

        # JSON部分を抽出
        if "{" in result_text and "}" in result_text:
            json_start = result_text.index("{")
            json_end = result_text.rindex("}") + 1
            json_str = result_text[json_start:json_end]
            return json.loads(json_str)

        return None

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON解析エラー: {e}")
        return None
    except Exception as e:
        print(f"  ❌ API エラー: {e}")
        return None


def calculate_composite_drama_score(evaluation: dict) -> float:
    """複合ドラマスコアを計算"""
    drama = evaluation.get("drama_score", 5)
    factuality = evaluation.get("factuality_score", 5)
    memorability = evaluation.get("memorability_score", 5)
    is_fictional = evaluation.get("is_fictional", False)

    # 架空エピソードにはペナルティ
    fictional_penalty = 2.0 if is_fictional else 0.0

    # 複合スコア = ドラマ性40% + 事実性30% + 記憶性30% - 架空ペナルティ
    composite = (drama * 0.4 + factuality * 0.3 + memorability * 0.3) - fictional_penalty

    return max(1.0, min(10.0, composite))


def detect_low_quality_candidates(df: pd.DataFrame, threshold: float = 5.0) -> pd.DataFrame:
    """低品質候補を検出（既存スコアベース）"""
    # 意外性スコアが低い
    low_surprise = df[df["意外性スコア"] < threshold] if "意外性スコア" in df.columns else pd.DataFrame()

    # sourceがPHASE12_AGE_EXPANSION（年齢穴埋め）
    age_expansion = df[df["source"] == "PHASE12_AGE_EXPANSION"]

    # 品質スコアがNaN（未評価）
    unscored = df[df["記憶性スコア"].isna()] if "記憶性スコア" in df.columns else pd.DataFrame()

    # 統合（重複排除）
    candidates = pd.concat([low_surprise, age_expansion, unscored]).drop_duplicates(subset=["episode_id"])

    return candidates


def main():
    parser = argparse.ArgumentParser(description="エピソードドラマ性評価")
    parser.add_argument("--sample", type=int, help="ランダムサンプル数")
    parser.add_argument("--source", type=str, help="特定sourceのみ評価")
    parser.add_argument("--episode-id", type=str, help="特定episode_idを評価")
    parser.add_argument("--detect-low-quality", action="store_true", help="低品質候補を検出")
    parser.add_argument("--threshold", type=float, default=5.0, help="低品質閾値")
    parser.add_argument("--limit", type=int, default=50, help="評価上限")
    parser.add_argument("--execute", action="store_true", help="評価を実行")
    parser.add_argument("--update-csv", action="store_true", help="CSVを更新")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 エピソードドラマ性評価システム")
    print("=" * 70)

    # CSV読み込み
    if not CSV_PATH.exists():
        print(f"❌ CSVが見つかりません: {CSV_PATH}")
        return 1

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"\n📂 DB: {len(df)}件")

    # 低品質候補検出モード
    if args.detect_low_quality:
        print(f"\n🔍 低品質候補を検出中（閾値: {args.threshold}）...")
        candidates = detect_low_quality_candidates(df, args.threshold)

        print("\n【低品質候補】")
        print(f"  総数: {len(candidates)}件")

        if "source" in candidates.columns:
            print("\n【source別内訳】")
            print(candidates["source"].value_counts().head(10).to_string())

        print("\n【サンプル（最初の10件）】")
        for _, row in candidates.head(10).iterrows():
            surprise = row.get("意外性スコア", "N/A")
            source = row.get("source", "N/A")
            text_preview = str(row.get("episode_text", ""))[:50]
            print(f"  {row['person_name']} ({row['age']}歳): 意外性={surprise}, source={source}")
            print(f"    {text_preview}...")

        return 0

    # 評価対象の選定
    if args.episode_id:
        targets = df[df["episode_id"] == args.episode_id]
    elif args.source:
        targets = df[df["source"] == args.source]
    elif args.sample:
        targets = df.sample(min(args.sample, len(df)))
    else:
        # デフォルト: 低品質候補
        targets = detect_low_quality_candidates(df, args.threshold)

    targets = targets.head(args.limit)

    print(f"\n🎯 評価対象: {len(targets)}件")

    if not args.execute:
        print("\n💡 --execute オプションで評価を実行します")

        print("\n【評価対象サンプル】")
        for _, row in targets.head(5).iterrows():
            print(f"  {row['episode_id']}: {row['person_name']} ({row['age']}歳)")
            text_preview = str(row.get("episode_text", ""))[:80]
            print(f"    {text_preview}...")
        return 0

    # API確認
    if not API_KEY:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        return 1

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    print(f"\n🔧 ドラマ性評価を開始（{len(targets)}件）...")

    results = []
    low_quality = []
    fictional = []

    for i, (_, row) in enumerate(targets.iterrows(), 1):
        episode_id = row["episode_id"]
        person_name = row["person_name"]
        age = row["age"]

        print(f"\n[{i}/{len(targets)}] {person_name} ({age}歳) - {episode_id}")

        evaluation = evaluate_single_episode(client, row.to_dict())

        if not evaluation:
            print("  ❌ 評価失敗")
            continue

        # 複合スコア計算
        composite = calculate_composite_drama_score(evaluation)
        evaluation["composite_drama_score"] = composite

        result = {
            "episode_id": episode_id,
            "person_name": person_name,
            "age": age,
            "source": row.get("source", ""),
            **evaluation,
        }
        results.append(result)

        # 分類
        drama_score = evaluation.get("drama_score", 5)
        is_fictional = evaluation.get("is_fictional", False)

        if drama_score < 5 or composite < 5:
            low_quality.append(result)
            status = "🔴 低品質"
        elif is_fictional:
            fictional.append(result)
            status = "🟡 架空"
        else:
            status = "✅ OK"

        print(
            f"  {status}: drama={drama_score}, fact={evaluation.get('factuality_score', '?')}, composite={composite:.1f}"
        )
        if is_fictional:
            print(f"    架空要素: {evaluation.get('fictional_elements', [])}")

    # 結果サマリー
    print(f"\n{'=' * 70}")
    print("📊 評価結果サマリー")
    print(f"{'=' * 70}")
    print(f"  評価完了: {len(results)}件")
    print(f"  低品質: {len(low_quality)}件 ({len(low_quality)/max(1,len(results))*100:.1f}%)")
    print(f"  架空EP: {len(fictional)}件 ({len(fictional)/max(1,len(results))*100:.1f}%)")

    if results:
        avg_drama = sum(r.get("drama_score", 0) for r in results) / len(results)
        avg_fact = sum(r.get("factuality_score", 0) for r in results) / len(results)
        avg_composite = sum(r.get("composite_drama_score", 0) for r in results) / len(results)
        print(f"\n  平均ドラマ性: {avg_drama:.2f}")
        print(f"  平均事実性: {avg_fact:.2f}")
        print(f"  平均複合スコア: {avg_composite:.2f}")

    # 低品質リスト表示
    if low_quality:
        print("\n【低品質エピソード（要改善）】")
        for r in low_quality[:10]:
            print(f"  {r['person_name']} ({r['age']}歳): composite={r['composite_drama_score']:.1f}")
            print(f"    理由: {r.get('evaluation_reason', 'N/A')}")

    # 架空リスト表示
    if fictional:
        print("\n【架空エピソード（要検証）】")
        for r in fictional[:10]:
            print(f"  {r['person_name']} ({r['age']}歳)")
            print(f"    架空要素: {r.get('fictional_elements', [])}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"drama_evaluation_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "total_evaluated": len(results),
        "low_quality_count": len(low_quality),
        "fictional_count": len(fictional),
        "average_scores": {
            "drama": avg_drama if results else 0,
            "factuality": avg_fact if results else 0,
            "composite": avg_composite if results else 0,
        },
        "low_quality_episodes": low_quality,
        "fictional_episodes": fictional,
        "all_results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート: {report_path}")

    # CSV更新
    if args.update_csv and results:
        print("\n💾 CSVを更新中...")

        # 新しいカラムを追加
        if "drama_score_llm" not in df.columns:
            df["drama_score_llm"] = None
        if "factuality_score_llm" not in df.columns:
            df["factuality_score_llm"] = None
        if "is_fictional_llm" not in df.columns:
            df["is_fictional_llm"] = None
        if "composite_drama_score" not in df.columns:
            df["composite_drama_score"] = None

        for result in results:
            ep_id = result["episode_id"]
            mask = df["episode_id"] == ep_id
            df.loc[mask, "drama_score_llm"] = result.get("drama_score")
            df.loc[mask, "factuality_score_llm"] = result.get("factuality_score")
            df.loc[mask, "is_fictional_llm"] = result.get("is_fictional")
            df.loc[mask, "composite_drama_score"] = result.get("composite_drama_score")

        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"💾 CSV更新完了: {CSV_PATH}")

    print("\n" + "=" * 70)
    print("✅ ドラマ性評価完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
