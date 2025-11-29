#!/usr/bin/env python3
"""
低品質エピソードの改善スクリプト

LLMベースのドラマ評価で低品質と判定されたエピソードを
より事実に基づいた、ドラマ性のあるエピソードに再生成する。

使用方法:
    # 評価のみ（ドライラン）
    python scripts/improve_low_drama_episodes.py --source PHASE17_COMPLETION --limit 10

    # 改善実行
    python scripts/improve_low_drama_episodes.py --source PHASE17_COMPLETION --limit 10 --execute

    # 特定エピソードを改善
    python scripts/improve_low_drama_episodes.py --episode-id EP-000004 --execute
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
EVALUATION_PROMPT = """あなたはエピソードの品質を評価する専門家です。

以下のエピソードを評価してください。

【人物】{person_name}
【年齢】{age}歳
【カテゴリ】{category}

【エピソード】
{episode_text}

【評価基準】
1. drama_score (1-10): 読者の心を動かすか
2. factuality_score (1-10): 事実に基づいているか
3. is_fictional: 中心的な出来事が架空か (true/false)
4. fictional_elements: 架空と思われる要素のリスト

【出力形式】JSONのみを出力:
{{
  "drama_score": 数値,
  "factuality_score": 数値,
  "is_fictional": true/false,
  "fictional_elements": ["要素1", "要素2"],
  "evaluation_reason": "評価理由"
}}"""

# 事実ベース再生成プロンプト
REGENERATE_PROMPT = """あなたは著名人のエピソードを作成する専門家です。
以下の情報に基づき、事実に基づいたドラマティックなエピソードを生成してください。

【人物情報】
- 名前: {person_name}
- カテゴリ: {category}
- 対象年齢: {age}歳

【現在のエピソード（問題あり）】
{current_text}

【検出された架空要素】
{fictional_elements}

【改善要件】
1. 形式: 「あなたと同じ{age}歳のとき、{person_name}は〜」で開始
2. 長さ: 200-300文字
3. 品質基準:
   - 検証可能な事実を中心に構成（受賞歴、発表作品、公開された発言など）
   - 具体的な日付、作品名、人物名を使用
   - 架空の心理描写は最小限に
   - 実際に起きた出来事・転機をベースにする
4. ドラマ性:
   - 葛藤、挑戦、転機を描く
   - 読者の心に残る印象的なエピソード

【注意】
- 存在しない作品名や賞を使わない
- 架空の詳細（具体的な会話、心境の詳細）は避ける
- 事実が不明な場合は、公開されている情報の範囲で書く

エピソードテキストのみを出力してください:"""


def evaluate_episode(client, episode: dict) -> dict | None:
    """エピソードを評価"""
    prompt = EVALUATION_PROMPT.format(
        person_name=episode.get("person_name", "不明"),
        age=episode.get("age", "不明"),
        category=episode.get("category", "不明"),
        episode_text=episode.get("episode_text", ""),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()

        if "{" in result_text and "}" in result_text:
            json_start = result_text.index("{")
            json_end = result_text.rindex("}") + 1
            json_str = result_text[json_start:json_end]
            return json.loads(json_str)

        return None

    except Exception as e:
        print(f"  ❌ 評価エラー: {e}")
        return None


def regenerate_episode(client, episode: dict, evaluation: dict) -> str | None:
    """エピソードを事実ベースで再生成"""
    fictional_elements = evaluation.get("fictional_elements", [])
    if not fictional_elements:
        fictional_elements = ["詳細が架空または推測に基づいている"]

    prompt = REGENERATE_PROMPT.format(
        person_name=episode.get("person_name", "不明"),
        age=episode.get("age", "不明"),
        category=episode.get("category", "不明"),
        current_text=episode.get("episode_text", ""),
        fictional_elements="\n".join(f"- {e}" for e in fictional_elements),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        new_text = response.content[0].text.strip()

        # 形式チェック
        if not new_text.startswith("あなたと同じ"):
            return None

        return new_text

    except Exception as e:
        print(f"  ❌ 再生成エラー: {e}")
        return None


def calculate_composite_score(evaluation: dict) -> float:
    """複合スコアを計算"""
    drama = evaluation.get("drama_score", 5)
    factuality = evaluation.get("factuality_score", 5)
    is_fictional = evaluation.get("is_fictional", False)

    fictional_penalty = 2.0 if is_fictional else 0.0
    composite = (drama * 0.4 + factuality * 0.6) - fictional_penalty

    return max(1.0, min(10.0, composite))


def main():
    parser = argparse.ArgumentParser(description="低品質エピソード改善")
    parser.add_argument("--source", type=str, help="特定sourceのみ対象")
    parser.add_argument("--episode-id", type=str, help="特定episode_idを対象")
    parser.add_argument("--threshold", type=float, default=5.0, help="改善対象の複合スコア閾値")
    parser.add_argument("--limit", type=int, default=20, help="処理上限")
    parser.add_argument("--execute", action="store_true", help="実際に改善を実行")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 低品質エピソード改善システム")
    print("=" * 70)

    # CSV読み込み
    if not CSV_PATH.exists():
        print(f"❌ CSVが見つかりません: {CSV_PATH}")
        return 1

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"\n📂 DB: {len(df)}件")

    # 対象選定
    if args.episode_id:
        targets = df[df["episode_id"] == args.episode_id]
    elif args.source:
        targets = df[df["source"] == args.source]
    else:
        # 意外性スコアが低いものを優先
        drama_scores = pd.to_numeric(df["意外性スコア"], errors="coerce")
        low_drama = df[drama_scores < 5.5]
        targets = low_drama

    targets = targets.head(args.limit)
    print(f"🎯 評価対象: {len(targets)}件")

    if len(targets) == 0:
        print("⚠️ 対象エピソードがありません")
        return 0

    if not args.execute:
        print("\n💡 --execute オプションで実際に改善を実行します")
        print("\n【対象サンプル】")
        for _, row in targets.head(5).iterrows():
            print(f"  {row['episode_id']}: {row['person_name']} ({row['age']}歳)")
            print(f"    source: {row.get('source', 'N/A')}")
        return 0

    # API確認
    if not API_KEY:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        return 1

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    print(f"\n🔧 評価・改善を開始（{len(targets)}件）...")

    results = []
    improved = []
    failed = []

    for i, (idx, row) in enumerate(targets.iterrows(), 1):
        episode_id = row["episode_id"]
        person_name = row["person_name"]
        age = row["age"]

        print(f"\n[{i}/{len(targets)}] {person_name} ({age}歳) - {episode_id}")

        # Step 1: 評価
        evaluation = evaluate_episode(client, row.to_dict())

        if not evaluation:
            print("  ❌ 評価失敗")
            failed.append({"episode_id": episode_id, "reason": "評価失敗"})
            continue

        composite = calculate_composite_score(evaluation)
        print(
            f"  📊 評価: drama={evaluation.get('drama_score')}, fact={evaluation.get('factuality_score')}, composite={composite:.1f}"
        )

        # Step 2: 改善が必要かチェック
        if composite >= args.threshold and not evaluation.get("is_fictional"):
            print(f"  ✅ 改善不要（複合スコア {composite:.1f} >= {args.threshold}）")
            results.append(
                {
                    "episode_id": episode_id,
                    "action": "skip",
                    "composite_score": composite,
                }
            )
            continue

        # Step 3: 再生成
        print(f"  🔄 再生成中（架空要素: {evaluation.get('fictional_elements', [])}）...")

        new_text = regenerate_episode(client, row.to_dict(), evaluation)

        if not new_text:
            print("  ❌ 再生成失敗")
            failed.append({"episode_id": episode_id, "reason": "再生成失敗"})
            continue

        # Step 4: 再生成後の評価
        new_episode = row.to_dict()
        new_episode["episode_text"] = new_text

        new_evaluation = evaluate_episode(client, new_episode)

        if new_evaluation:
            new_composite = calculate_composite_score(new_evaluation)
            print(
                f"  📊 再評価: drama={new_evaluation.get('drama_score')}, fact={new_evaluation.get('factuality_score')}, composite={new_composite:.1f}"
            )

            if new_composite > composite:
                print(f"  ✅ 改善成功: {composite:.1f} → {new_composite:.1f}")
                improved.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "age": age,
                        "old_composite": composite,
                        "new_composite": new_composite,
                        "old_text": row["episode_text"],
                        "new_text": new_text,
                    }
                )

                # CSVを更新
                df.loc[idx, "episode_text"] = new_text
                df.loc[idx, "source"] = f"{row.get('source', '')}→DRAMA_IMPROVED"

            else:
                print(f"  ⚠️ 改善なし: {composite:.1f} → {new_composite:.1f}")
                results.append(
                    {
                        "episode_id": episode_id,
                        "action": "no_improvement",
                        "old_composite": composite,
                        "new_composite": new_composite,
                    }
                )
        else:
            print("  ❌ 再評価失敗")
            failed.append({"episode_id": episode_id, "reason": "再評価失敗"})

    # 結果サマリー
    print(f"\n{'=' * 70}")
    print("📊 改善結果サマリー")
    print(f"{'=' * 70}")
    print(f"  処理完了: {len(targets)}件")
    print(f"  改善成功: {len(improved)}件")
    print(f"  改善不要/不可: {len(results)}件")
    print(f"  失敗: {len(failed)}件")

    if improved:
        print("\n【改善されたエピソード】")
        for imp in improved[:5]:
            print(f"  {imp['person_name']} ({imp['age']}歳): {imp['old_composite']:.1f} → {imp['new_composite']:.1f}")

        # CSV保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"\n💾 CSV更新完了: {CSV_PATH}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"drama_improvement_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "source": args.source,
        "threshold": args.threshold,
        "total_processed": len(targets),
        "improved_count": len(improved),
        "failed_count": len(failed),
        "improved_episodes": improved,
        "failed_episodes": failed,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート: {report_path}")

    print("\n" + "=" * 70)
    print("✅ 改善処理完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
