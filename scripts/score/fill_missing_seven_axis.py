#!/usr/bin/env python3
"""
欠損している7軸スコアを補完するスクリプト

LLMを使用して、記憶性・共感性・意外性・生成品質・educational_valueを評価し、
ルールベースでstory_quality・factual_densityを算出する。

使用方法:
    # ドライラン（評価のみ）
    python scripts/fill_missing_seven_axis.py --limit 10

    # 実行（CSVを更新）
    python scripts/fill_missing_seven_axis.py --execute

    # バッチサイズ指定
    python scripts/fill_missing_seven_axis.py --batch-size 30 --execute

NOTE: story_qualityとfactual_densityの算出ロジックは統一モジュールからインポート
      backend/app/utils/score_calculator.py に正規実装あり
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

# 統一モジュールからインポート（重複実装の排除）
from backend.app.utils.score_calculator import (
    calculate_factual_density,
    calculate_story_quality,
)

# パス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# APIキー
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 7軸評価プロンプト
SEVEN_AXIS_PROMPT = """あなたはエピソードの品質を評価する専門家です。

以下のエピソードを7つの軸で評価してください。

【人物】{person_name}
【年齢】{age}歳
【カテゴリ】{category}
【人物タイプ】{person_type}

【エピソード】
{episode_text}

【評価軸】（すべて1-10の整数で評価）

1. memorability_score: 読後にどれだけ印象に残るか
   - 1-3: すぐに忘れる一般的な内容
   - 4-6: いくらか印象に残る
   - 7-8: しっかり記憶に残る
   - 9-10: 強烈に心に刻まれる

2. empathy_score: 読者が感情移入できるか
   - 1-3: 共感しにくい
   - 4-6: ある程度共感できる
   - 7-8: 強く共感できる
   - 9-10: 深く心が動かされる

3. surprise_score: 予想外の展開や発見があるか
   - 1-3: 予想通りの内容
   - 4-6: 少し意外な要素がある
   - 7-8: 明確な意外性がある
   - 9-10: 驚きの展開がある

4. generation_quality_score: 文章の質・構成・表現力
   - 1-3: 文章が粗い
   - 4-6: 標準的な品質
   - 7-8: 高品質な文章
   - 9-10: 優れた文学的表現

5. educational_value: 読者に学びや気づきを与えるか
   - 1-3: 学びが少ない
   - 4-6: いくらか学びがある
   - 7-8: 明確な学びがある
   - 9-10: 深い洞察を与える

【出力形式】JSONのみを出力してください:
{{
  "memorability_score": 数値,
  "empathy_score": 数値,
  "surprise_score": 数値,
  "generation_quality_score": 数値,
  "educational_value": 数値,
  "評価理由": "1-2文で簡潔に"
}}"""


def evaluate_with_llm(client, episode: dict) -> dict | None:
    """LLMで5軸を評価"""
    prompt = SEVEN_AXIS_PROMPT.format(
        person_name=episode.get("person_name", "不明"),
        age=episode.get("age", "不明"),
        category=episode.get("category", "不明"),
        person_type=episode.get("person_type", "REAL"),
        episode_text=episode.get("episode_text", ""),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()

        # JSONを抽出
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        return json.loads(result_text)
    except Exception as e:
        print(f"    ⚠️ LLM評価エラー: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="欠損7軸スコアを補完")
    parser.add_argument("--execute", action="store_true", help="CSVを更新")
    parser.add_argument("--limit", type=int, help="処理件数の上限")
    parser.add_argument("--batch-size", type=int, default=50, help="バッチサイズ")
    args = parser.parse_args()

    print("=" * 80)
    print("📊 欠損7軸スコア補完スクリプト")
    print("=" * 80)
    print()

    # CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # 欠損エピソードを特定
    print("Step 2: 欠損エピソードを特定中...")
    missing_indices = []
    for idx, row in df.iterrows():
        if pd.isna(row.get("memorability_score")):
            missing_indices.append(idx)

    print(f"  ✅ 欠損エピソード: {len(missing_indices)}件")
    print()

    if len(missing_indices) == 0:
        print("✅ 欠損エピソードはありません")
        return

    # LLMクライアント初期化
    if not API_KEY:
        print("❌ ANTHROPIC_API_KEYが設定されていません")
        return

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    # 処理件数を制限
    if args.limit:
        missing_indices = missing_indices[: args.limit]
    if args.batch_size:
        missing_indices = missing_indices[: args.batch_size]

    print(f"Step 3: {len(missing_indices)}件の7軸スコアを算出中...")
    print()

    updated_count = 0
    failed_count = 0
    results = []

    for i, idx in enumerate(missing_indices, 1):
        row = df.loc[idx]
        episode_id = row["episode_id"]
        person_name = row["person_name"]
        age = row["age"]

        print(f"  [{i}/{len(missing_indices)}] {episode_id}: {person_name} ({age}歳)")

        # ルールベースでstory_qualityとfactual_densityを算出
        episode_text = str(row["episode_text"])
        episode_type = str(row["episode_type"]) if pd.notna(row["episode_type"]) else ""

        storytelling_score = calculate_story_quality(episode_text, episode_type)
        factual_score = calculate_factual_density(episode_text, episode_type)

        # LLMで5軸を評価
        episode_dict = row.to_dict()
        llm_result = evaluate_with_llm(client, episode_dict)

        if llm_result:
            result = {
                "episode_id": episode_id,
                "person_name": person_name,
                "age": age,
                "memorability_score": llm_result.get("memorability_score", 6),
                "empathy_score": llm_result.get("empathy_score", 6),
                "surprise_score": llm_result.get("surprise_score", 6),
                "generation_quality_score": llm_result.get("generation_quality_score", 7),
                "educational_value": llm_result.get("educational_value", 7),
                "story_quality": storytelling_score,
                "factual_density": factual_score,
            }
            results.append(result)

            if args.execute:
                # CSVを更新
                df.at[idx, "memorability_score"] = result["memorability_score"]
                df.at[idx, "empathy_score"] = result["empathy_score"]
                df.at[idx, "surprise_score"] = result["surprise_score"]
                df.at[idx, "generation_quality_score"] = result["generation_quality_score"]
                df.at[idx, "educational_value"] = result["educational_value"]
                df.at[idx, "story_quality"] = result["story_quality"]
                df.at[idx, "factual_density"] = result["factual_density"]

            updated_count += 1
            print(
                f"    ✅ 記憶:{result['memorability_score']} 共感:{result['empathy_score']} 意外:{result['surprise_score']} 品質:{result['generation_quality_score']} 教育:{result['educational_value']} ストーリー:{storytelling_score:.1f} 事実:{factual_score:.1f}"
            )
        else:
            failed_count += 1
            print("    ❌ 評価失敗")

    print()

    # CSVを保存
    if args.execute and updated_count > 0:
        print("Step 4: CSVファイル保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ 保存完了: {CSV_PATH}")
        print()

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"seven_axis_fill_{timestamp}.json"
    REPORTS_DIR.mkdir(exist_ok=True)

    report = {
        "timestamp": timestamp,
        "total_missing": len(missing_indices),
        "updated_count": updated_count,
        "failed_count": failed_count,
        "execute_mode": args.execute,
        "results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📄 レポート保存: {report_path}")
    print()

    # サマリー
    print("=" * 80)
    print("✅ 7軸スコア補完完了")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 対象エピソード: {len(missing_indices)}件")
    print(f"  - 成功: {updated_count}件")
    print(f"  - 失敗: {failed_count}件")
    if not args.execute:
        print("  - モード: ドライラン（--execute で実行）")
    print()


if __name__ == "__main__":
    main()
