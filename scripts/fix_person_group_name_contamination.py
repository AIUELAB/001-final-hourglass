#!/usr/bin/env python3
"""
人物名とグループ名の混在問題を検出・修正するスクリプト

問題パターン:
1. 「グループ名・個人名」形式（例: 水溜りボンド・トミー → トミー）
2. 「グループ名 個人名」形式（例: QuizKnock 伊沢拓司 → 伊沢拓司）

使用方法:
    # ドライラン（検出のみ）
    python scripts/fix_person_group_name_contamination.py --dry-run

    # 実行（修正を適用）
    python scripts/fix_person_group_name_contamination.py --execute

    # LLMを使用した曖昧ケースの判定
    python scripts/fix_person_group_name_contamination.py --use-llm --execute

環境変数:
    ANTHROPIC_API_KEY: LLM判定を使用する場合に必要
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP, get_group_info

# Anthropic API（オプション）
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ========================================
# 検出パターン定義
# ========================================

# 除外パターン（正規の名前として「・」を含むもの）
# これらの「・」は名前の区切りであり、グループ名ではない
EXCLUDE_FIRST_PART_PATTERNS = {
    # 西洋人名の「・」区切り
    "ジョン",
    "ポール",
    "ジョージ",
    "リンゴ",
    "マイケル",
    "フレディ",
    "ブライアン",
    "ロジャー",
    "ミック",
    "キース",
    "ジミー",
    "ロバート",
    "エディ",
    "クリス",
    "デイヴ",
    "チック",
    "パット",
    "アート",
    "ボブ",
    "マービン",
    "マーティン",
    "マーゴット",
    "マーク",
    "マリー",
    "マリア",
    "マララ",
    "マックス",
    "マザー",
    "ペレ",
    "マツコ",
    "モンキー",
    "ヤニス",
    "ロナウド",
    "ロアール",
    "ルイ",
    # 日本の架空キャラクターの名前
    "ミカサ",
    "エレン",
    "リヴァイ",
    "アルミン",
    # その他
    "藤子",  # 藤子・F・不二雄
    # 誤検出対策: お笑いコンビ名と同名の外国人名
    "オードリー",  # オードリー・ヘプバーン（女優）はお笑いコンビ「オードリー」とは無関係
}


def detect_contamination_patterns(df: pd.DataFrame) -> List[Dict]:
    """
    グループ名と個人名の混在パターンを検出

    Args:
        df: データフレーム

    Returns:
        検出結果のリスト
    """
    group_names = set(GROUP_ENTITIES) | set(GROUP_MEMBER_MAP.values())
    issues = []

    for _, row in df.drop_duplicates(subset=["person_name"]).iterrows():
        person_name = str(row["person_name"]).strip()
        person_id = row.get("person_id", "")
        current_group = row.get("group_name", "")

        # パターン1: 「グループ名 個人名」（スペース区切り）
        for gname in group_names:
            if person_name.startswith(gname + " "):
                individual = person_name[len(gname) + 1 :].strip()
                if individual:
                    issues.append(
                        {
                            "person_id": person_id,
                            "original_name": person_name,
                            "pattern": "SPACE_SEPARATOR",
                            "detected_group": gname,
                            "detected_individual": individual,
                            "current_group_name": current_group,
                            "confidence": 0.95,
                            "suggested_fix": {
                                "person_name": individual,
                                "group_name": gname,
                                "is_group_member": True,
                            },
                        }
                    )
                break

        # パターン2: 「グループ名・個人名」（中点区切り）
        if "・" in person_name:
            parts = person_name.split("・")
            first_part = parts[0]

            # 除外パターンをチェック
            if first_part in EXCLUDE_FIRST_PART_PATTERNS:
                continue

            # 最初の部分がグループ名として登録されているか
            if first_part in group_names:
                individual = "・".join(parts[1:])
                issues.append(
                    {
                        "person_id": person_id,
                        "original_name": person_name,
                        "pattern": "DOT_SEPARATOR",
                        "detected_group": first_part,
                        "detected_individual": individual,
                        "current_group_name": current_group,
                        "confidence": 0.9,
                        "suggested_fix": {
                            "person_name": individual,
                            "group_name": first_part,
                            "is_group_member": True,
                        },
                    }
                )

    return issues


def verify_with_llm(issue: Dict, client: "anthropic.Anthropic") -> Dict:
    """
    LLMを使用して曖昧なケースを検証

    Args:
        issue: 検出された問題
        client: Anthropic クライアント

    Returns:
        検証結果を追加した issue
    """
    prompt = f"""以下の人物名について、グループ名と個人名が混在しているかどうか判定してください。

【人物名】{issue['original_name']}
【検出されたグループ名】{issue['detected_group']}
【検出された個人名】{issue['detected_individual']}

以下のJSON形式で回答してください:
{{
  "is_contaminated": true/false,
  "correct_person_name": "正しい個人名",
  "correct_group_name": "正しいグループ名（所属していれば）または null",
  "confidence": 0.0-1.0,
  "reason": "判定理由（20文字以内）"
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()

        if "{" in result_text and "}" in result_text:
            json_start = result_text.index("{")
            json_end = result_text.rindex("}") + 1
            json_str = result_text[json_start:json_end]
            llm_result = json.loads(json_str)

            issue["llm_verified"] = True
            issue["llm_result"] = llm_result

            if llm_result.get("is_contaminated"):
                issue["suggested_fix"]["person_name"] = llm_result.get(
                    "correct_person_name", issue["detected_individual"]
                )
                if llm_result.get("correct_group_name"):
                    issue["suggested_fix"]["group_name"] = llm_result["correct_group_name"]
                issue["confidence"] = llm_result.get("confidence", issue["confidence"])
    except Exception as e:
        issue["llm_verified"] = False
        issue["llm_error"] = str(e)

    return issue


def apply_fixes(df: pd.DataFrame, issues: List[Dict], dry_run: bool = True) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    修正を適用

    Args:
        df: データフレーム
        issues: 検出された問題リスト
        dry_run: ドライランかどうか

    Returns:
        (修正後のデータフレーム, 適用された修正のリスト)
    """
    applied = []

    for issue in issues:
        if issue["confidence"] < 0.8:
            continue

        fix = issue["suggested_fix"]
        original_name = issue["original_name"]

        # 該当するすべての行を更新
        mask = df["person_name"] == original_name

        if mask.sum() > 0:
            if not dry_run:
                df.loc[mask, "person_name"] = fix["person_name"]
                df.loc[mask, "group_name"] = fix["group_name"]
                df.loc[mask, "is_group_member"] = fix["is_group_member"]

            applied.append(
                {
                    "original_name": original_name,
                    "new_name": fix["person_name"],
                    "group_name": fix["group_name"],
                    "affected_rows": int(mask.sum()),
                    "confidence": issue["confidence"],
                }
            )

    return df, applied


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="人物名とグループ名の混在問題を修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（検出のみ）")
    parser.add_argument("--execute", action="store_true", help="修正を実行")
    parser.add_argument("--use-llm", action="store_true", help="LLMで曖昧ケースを検証")
    parser.add_argument("--csv", type=str, help="対象CSVファイルパス")
    parser.add_argument("--min-confidence", type=float, default=0.8, help="最小信頼度（デフォルト: 0.8）")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        args.dry_run = True
        print("⚠️ --execute が指定されていないため、ドライランモードで実行します")

    # CSVファイルパス
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print("=" * 70)
    print("🔍 人物名・グループ名混在問題の検出・修正")
    print("=" * 70)
    print(f"📂 対象ファイル: {csv_path}")
    print(f"🔧 モード: {'ドライラン' if args.dry_run else '実行'}")
    print(f"🤖 LLM検証: {'有効' if args.use_llm else '無効'}")
    print("=" * 70)

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📊 読み込み完了: {len(df)}件")

    # 問題パターン検出
    print("\n🔍 問題パターンを検出中...")
    issues = detect_contamination_patterns(df)
    print(f"⚠️ 検出された問題: {len(issues)}件")

    if not issues:
        print("\n✅ 問題は検出されませんでした")
        return 0

    # LLM検証
    if args.use_llm and HAS_ANTHROPIC:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            print("\n🤖 LLMで曖昧ケースを検証中...")
            client = anthropic.Anthropic(api_key=api_key)
            for i, issue in enumerate(issues):
                print(f"  [{i+1}/{len(issues)}] {issue['original_name']}...", end=" ")
                issue = verify_with_llm(issue, client)
                if issue.get("llm_verified"):
                    print("✅")
                else:
                    print("⏭️")
        else:
            print("⚠️ ANTHROPIC_API_KEY が設定されていないため、LLM検証をスキップ")

    # 検出結果を表示
    print("\n" + "=" * 70)
    print("📋 検出結果一覧")
    print("=" * 70)

    for issue in issues:
        conf = issue["confidence"]
        status = "🟢" if conf >= 0.9 else "🟡" if conf >= 0.8 else "🔴"
        print(f"\n{status} {issue['original_name']}")
        print(f"   パターン: {issue['pattern']}")
        print(f"   検出グループ: {issue['detected_group']}")
        print(f"   検出個人名: {issue['detected_individual']}")
        print(f"   信頼度: {conf:.0%}")
        print(
            f"   修正案: person_name='{issue['suggested_fix']['person_name']}', group_name='{issue['suggested_fix']['group_name']}'"
        )

    # 修正適用
    if args.execute:
        print("\n" + "=" * 70)
        print("🔧 修正を適用中...")
        print("=" * 70)

        # バックアップ作成
        backup_path = csv_path.with_name(
            csv_path.stem + f"_backup_name_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"📦 バックアップ: {backup_path}")

        # 修正適用
        df, applied = apply_fixes(df, issues, dry_run=False)

        # 保存
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 保存完了: {csv_path}")

        # レポート
        report_path = project_root / "reports" / f"name_group_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "total_issues": len(issues),
                    "applied_fixes": len(applied),
                    "fixes": applied,
                    "issues": issues,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"📄 レポート: {report_path}")

        print(f"\n✅ 修正完了: {len(applied)}件")
    else:
        print("\n💡 実際に修正を適用するには --execute オプションを使用してください")
        print(f"   python {Path(__file__).name} --execute")

    return 0


if __name__ == "__main__":
    sys.exit(main())
