#!/usr/bin/env python3
"""
内容密度改善スクリプト

冗長なエピソードをLLMでリライトし、品質を向上させる。
完全自動承認: 品質低下なしなら即時CSV反映。

使用方法:
    # ドライラン（評価のみ）
    python scripts/improve_content_density.py --limit 5

    # 実行（CSV更新）
    python scripts/improve_content_density.py --batch-size 30 --execute

    # 特定問題タイプのみ
    python scripts/improve_content_density.py --issue-type long_low_score --execute
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# APIキー
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 評価モジュールをインポート
from evaluate_content_density import (
    calculate_content_density_quality,
    detect_redundancy_patterns,
)

# =============================================================================
# リライトプロンプト
# =============================================================================

REWRITE_PROMPT_LONG = """あなたはエピソードの品質最適化専門家です。

【元エピソード】
{episode_text}

【人物情報】
- 名前: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}
- タイプ: {person_type}

【検出された冗長パターン】
{redundancy_patterns}

【リライト指示】
このエピソードは「長いのにスコアが低い」と判定されました。以下の原則に従ってリライトしてください:

1. 削除すべき要素:
   - 結論の一般化: 「礎となった」「刻まれている」「後世に影響を与えた」
   - メタ的説明: 「この経験が」「という言葉」「という思いから」
   - 検証不可能な感情: 「震える手」「涙を流した」「胸が熱くなった」
   - 抽象的評価: 「画期的な」「歴史的な」「重要な転機」

2. 強化・維持すべき要素:
   - 4桁の年号（必須: 1つ以上）
   - 固有名詞（人名、作品名、賞名、組織名）
   - 数値データ（記録、順位、金額、部数）
   - 本人の発言の引用（「」で囲む）

3. 構造:
   - 「あなたと同じ{age}歳のとき、{person_name}は〜」で必ず開始
   - 200-280文字（目安）
   - 事実 → 背景/文脈 → 具体的影響 の順

4. 禁止:
   - 同じ年齢の繰り返し言及
   - 架空の詳細（会話、心境の詳細）
   - 「歴史に刻まれた」等の検証不可能な主張

リライトしたエピソードのみを出力してください（説明不要）:"""

REWRITE_PROMPT_SHORT = """あなたはエピソードの品質最適化専門家です。

【元エピソード】
{episode_text}

【人物情報】
- 名前: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}
- タイプ: {person_type}

【リライト指示】
このエピソードは「短すぎて情報不足」と判定されました。以下の要素を追加してリライトしてください:

1. 追加すべき要素:
   - 背景情報（なぜその出来事が起きたか）
   - 具体的な数値データ（年号、記録、順位など）
   - 感情的インパクト（ただし検証可能な範囲で）
   - その出来事の意義や影響（具体的に）

2. 構造:
   - 「あなたと同じ{age}歳のとき、{person_name}は〜」で必ず開始
   - 200-280文字（目安）

3. 禁止:
   - 架空の詳細を作り出すこと
   - 抽象的な表現で水増しすること

リライトしたエピソードのみを出力してください（説明不要）:"""

REWRITE_PROMPT_REDUNDANT = """あなたはエピソードの品質最適化専門家です。

【元エピソード】
{episode_text}

【人物情報】
- 名前: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}
- タイプ: {person_type}

【検出された冗長パターン】
{redundancy_patterns}

【リライト指示】
このエピソードには「冗長なパターン」が検出されました。以下の原則に従ってリライトしてください:

1. 削除すべきパターン:
{patterns_to_remove}

2. 代替案:
   - 「礎となった」→ 具体的な影響（「〇〇賞の創設につながった」など）
   - 「この経験が」→ 事実の直接記述
   - 「涙を流した」→ 証言引用または省略

3. 構造:
   - 「あなたと同じ{age}歳のとき、{person_name}は〜」で必ず開始
   - 200-280文字（目安）

リライトしたエピソードのみを出力してください（説明不要）:"""


def identify_issues(df: pd.DataFrame) -> pd.DataFrame:
    """問題エピソードを特定"""
    issues_list = []

    # 7軸スコアカラム
    score_cols = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    for idx, row in df.iterrows():
        text = str(row.get("episode_text", ""))
        char_count = len(text)
        seven_axis_avg = sum(float(row.get(col, 0) or 0) for col in score_cols) / len(score_cols)
        redundancy = detect_redundancy_patterns(text)

        issues = []
        priority = 0

        # 長文低スコア
        if char_count > 300 and seven_axis_avg < 6.5:
            issues.append("long_low_score")
            priority += 3

        # 短文
        if char_count < 150:
            issues.append("too_short")
            priority += 2

        # 高冗長性
        if redundancy["total_count"] >= 2:
            issues.append("high_redundancy")
            priority += 2

        if issues:
            issues_list.append(
                {
                    "idx": idx,
                    "episode_id": row["episode_id"],
                    "person_name": row["person_name"],
                    "age": row["age"],
                    "category": row.get("category", ""),
                    "person_type": row.get("person_type", "REAL"),
                    "char_count": char_count,
                    "seven_axis_avg": seven_axis_avg,
                    "redundancy_count": redundancy["total_count"],
                    "redundancy_patterns": redundancy["by_severity"],
                    "issues": issues,
                    "priority": priority,
                    "episode_text": text,
                }
            )

    return pd.DataFrame(issues_list).sort_values("priority", ascending=False)


def rewrite_episode(client, episode_data: dict) -> str | None:
    """LLMでエピソードをリライト"""
    issues = episode_data["issues"]

    # プロンプト選択
    if "long_low_score" in issues:
        prompt = REWRITE_PROMPT_LONG
    elif "too_short" in issues:
        prompt = REWRITE_PROMPT_SHORT
    elif "high_redundancy" in issues:
        prompt = REWRITE_PROMPT_REDUNDANT
    else:
        prompt = REWRITE_PROMPT_LONG

    # 冗長パターンの説明を生成
    patterns_desc = []
    for severity, count in episode_data.get("redundancy_patterns", {}).items():
        if count > 0:
            patterns_desc.append(f"- {severity}: {count}件")
    patterns_str = "\n".join(patterns_desc) if patterns_desc else "なし"

    # 削除すべきパターンのリスト
    patterns_to_remove = []
    from evaluate_content_density import REDUNDANCY_PATTERNS

    for severity, config in REDUNDANCY_PATTERNS.items():
        if episode_data.get("redundancy_patterns", {}).get(severity, 0) > 0:
            patterns_to_remove.append(f"- {config['description']}: {', '.join(config['patterns'][:3])}")

    formatted_prompt = prompt.format(
        episode_text=episode_data["episode_text"],
        person_name=episode_data["person_name"],
        age=int(episode_data["age"]),
        category=episode_data["category"],
        person_type=episode_data["person_type"],
        redundancy_patterns=patterns_str,
        patterns_to_remove="\n".join(patterns_to_remove) if patterns_to_remove else "なし",
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": formatted_prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"    ⚠️ LLMエラー: {e}")
        return None


def validate_rewrite(original: dict, new_text: str) -> tuple[bool, str]:
    """リライト結果を検証"""
    # 必須チェック: 開始形式
    expected_start = f"あなたと同じ{int(original['age'])}歳のとき、{original['person_name']}は"
    if not new_text.startswith(expected_start):
        return False, "開始形式が不正"

    # 文字数チェック
    new_char_count = len(new_text)
    if new_char_count < 100:
        return False, "文字数が短すぎる"
    if new_char_count > 450:
        return False, "文字数が長すぎる"

    # 品質比較
    original_result = calculate_content_density_quality({"episode_text": original["episode_text"]})
    new_result = calculate_content_density_quality({"episode_text": new_text})

    original_score = original_result["content_density_score"]
    new_score = new_result["content_density_score"]

    # 完全自動承認基準: 品質低下なし
    if new_score < original_score - 0.5:
        return False, f"品質低下 ({original_score:.2f} -> {new_score:.2f})"

    # 冗長パターン増加チェック
    original_redundancy = original_result["redundancy"]["total_count"]
    new_redundancy = new_result["redundancy"]["total_count"]
    if new_redundancy > original_redundancy:
        return False, f"冗長パターン増加 ({original_redundancy} -> {new_redundancy})"

    return True, f"OK (score: {original_score:.2f} -> {new_score:.2f})"


def main():
    parser = argparse.ArgumentParser(description="内容密度改善")
    parser.add_argument("--execute", action="store_true", help="CSVを更新")
    parser.add_argument("--batch-size", type=int, default=30, help="バッチサイズ")
    parser.add_argument("--limit", type=int, help="処理件数の上限")
    parser.add_argument(
        "--issue-type",
        type=str,
        choices=["long_low_score", "too_short", "high_redundancy"],
        help="特定の問題タイプのみ処理",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("📊 内容密度改善")
    print("=" * 80)
    print()

    # APIキーチェック
    if not API_KEY:
        print("❌ ANTHROPIC_API_KEYが設定されていません")
        return

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    # CSV読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  読み込み完了: {len(df):,}件")
    print()

    # 問題エピソード特定
    print("Step 2: 問題エピソード特定中...")
    issues_df = identify_issues(df)
    print(f"  問題エピソード: {len(issues_df)}件")

    # 問題タイプでフィルタ
    if args.issue_type:
        issues_df = issues_df[issues_df["issues"].apply(lambda x: args.issue_type in x)]
        print(f"  フィルタ後 ({args.issue_type}): {len(issues_df)}件")

    # 件数制限
    if args.limit:
        issues_df = issues_df.head(args.limit)
    elif args.batch_size:
        issues_df = issues_df.head(args.batch_size)

    print(f"  処理対象: {len(issues_df)}件")
    print()

    if len(issues_df) == 0:
        print("✅ 対象エピソードがありません")
        return

    # 問題内訳
    print("【問題内訳】")
    for issue_type in ["long_low_score", "too_short", "high_redundancy"]:
        count = len(issues_df[issues_df["issues"].apply(lambda x: issue_type in x)])
        print(f"  {issue_type}: {count}件")
    print()

    # リライト実行
    print("Step 3: リライト実行中...")
    results = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for i, (_, row) in enumerate(issues_df.iterrows(), 1):
        episode_data = row.to_dict()
        print(
            f"  [{i}/{len(issues_df)}] {episode_data['episode_id']}: {episode_data['person_name']} ({int(episode_data['age'])}歳)"
        )
        print(f"      問題: {episode_data['issues']}, 文字数: {episode_data['char_count']}")

        # リライト
        new_text = rewrite_episode(client, episode_data)
        if new_text is None:
            failed_count += 1
            results.append({"episode_id": episode_data["episode_id"], "status": "failed", "reason": "LLMエラー"})
            continue

        # 検証
        is_valid, message = validate_rewrite(episode_data, new_text)

        if is_valid:
            success_count += 1
            results.append(
                {
                    "episode_id": episode_data["episode_id"],
                    "status": "approved",
                    "reason": message,
                    "original_text": episode_data["episode_text"],
                    "new_text": new_text,
                    "original_char_count": episode_data["char_count"],
                    "new_char_count": len(new_text),
                }
            )
            print(f"      ✅ 承認: {message}")

            # CSV更新
            if args.execute:
                idx = df[df["episode_id"] == episode_data["episode_id"]].index[0]
                df.at[idx, "episode_text"] = new_text
                # sourceを更新
                current_source = df.at[idx, "source"] if "source" in df.columns else ""
                df.at[idx, "source"] = f"{current_source}→DENSITY_IMPROVED"
        else:
            skipped_count += 1
            results.append({"episode_id": episode_data["episode_id"], "status": "skipped", "reason": message})
            print(f"      ⏭️ スキップ: {message}")

    print()

    # CSV保存
    if args.execute and success_count > 0:
        print("Step 4: CSVファイル保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ CSV更新完了: {CSV_PATH}")
        print()

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"content_density_improvement_{timestamp}.json"
    REPORTS_DIR.mkdir(exist_ok=True)

    report = {
        "timestamp": timestamp,
        "execute_mode": args.execute,
        "total_processed": len(issues_df),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート保存: {report_path}")
    print()

    # サマリー
    print("=" * 80)
    print("📈 サマリー")
    print("=" * 80)
    print(f"処理対象: {len(issues_df)}件")
    print(f"成功（承認）: {success_count}件")
    print(f"失敗: {failed_count}件")
    print(f"スキップ: {skipped_count}件")
    if not args.execute:
        print("モード: ドライラン（--execute で実行）")
    print()
    print("🎉 完了!")


if __name__ == "__main__":
    main()
