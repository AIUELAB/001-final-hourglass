#!/usr/bin/env python3
"""
創業者パターン名義変更スクリプト

処理方針:
1. 「○○創業者△△」形式のperson_nameを検出
2. 「△△」（個人名）部分を抽出
3. person_nameを個人名に変更
4. エピソードテキストを個人視点に調整（必要に応じて）

例:
  「楽天創業者三木谷浩史」→「三木谷浩史」
  「ウォルマート創業者サム・ウォルトン」→「サム・ウォルトン」
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed")
    sys.exit(1)


# 創業者パターンの正規表現
# 「○○創業者△△」形式から個人名を抽出
FOUNDER_PATTERN = re.compile(r"^(.+)創業者(.+)$")

# 創業者パターンで個人名が含まれないケース（DELETE対象）
FOUNDER_WITHOUT_NAME = {"富士フイルム創業者", "島津製作所創業者"}


def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY required")
    return Anthropic(api_key=api_key)


def extract_individual_name(person_name: str) -> str | None:
    """
    創業者パターンから個人名を抽出

    Args:
        person_name: 「○○創業者△△」形式の名前

    Returns:
        個人名、または抽出できない場合はNone
    """
    if person_name in FOUNDER_WITHOUT_NAME:
        return None

    match = FOUNDER_PATTERN.match(person_name)
    if match:
        return match.group(2).strip()
    return None


def get_or_create_person_id(df: pd.DataFrame, name: str) -> str:
    """既存のperson_idを取得、なければ生成"""
    existing = df[df["person_name"] == name]
    if not existing.empty:
        return existing["person_id"].iloc[0]
    hash_val = hashlib.md5(name.encode()).hexdigest()[:8].upper()
    return f"P{hash_val}"


def rewrite_episode_to_individual(
    client: Anthropic,
    original_text: str,
    founder_name: str,
    individual_name: str,
    age: float,
) -> str:
    """エピソードテキストを個人名義に書き換え"""
    prompt = f"""以下の創業者エピソードを「{individual_name}」個人のエピソードとして書き直してください。

【元のエピソード（{int(age)}歳時点）】
{original_text}

【変換ルール】
1. 「あなたと同じ{int(age)}歳のとき、{individual_name}は」で始める
2. 「{founder_name}創業者」という表現は削除し、{individual_name}個人の視点で描写
3. 会社名（{founder_name}）は背景情報として残してよい
4. 文字数は350-500文字程度
5. メタ的な説明は含めない

【出力】
変換後のエピソード本文のみを出力してください。"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def process_founder_episodes(
    df: pd.DataFrame,
    client: Anthropic | None,
    dry_run: bool = True,
    rewrite_text: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """創業者パターンエピソードを処理"""

    # 創業者パターンを検出
    founder_eps = df[df["person_name"].str.contains("創業者", na=False)]

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_founder_episodes": len(founder_eps),
        "renamed": [],
        "skipped": [],
        "errors": [],
    }

    if len(founder_eps) == 0:
        print("創業者パターンのエピソードが見つかりません")
        return df, report

    print(f"検出された創業者パターン: {len(founder_eps)}件")

    renamed_count = 0
    skipped_count = 0

    for idx, row in founder_eps.iterrows():
        episode_id = row["episode_id"]
        person_name = row["person_name"]
        age = row["age"]
        original_text = row.get("episode_text", "")

        # 個人名を抽出
        individual_name = extract_individual_name(person_name)

        if individual_name:
            print(f"  {episode_id}: {person_name} → {individual_name}")

            if dry_run:
                report["renamed"].append(
                    {
                        "episode_id": episode_id,
                        "original_name": person_name,
                        "new_name": individual_name,
                        "age": age,
                        "dry_run": True,
                    }
                )
            else:
                try:
                    # person_idを取得または生成
                    person_id = get_or_create_person_id(df, individual_name)

                    # DataFrameを更新
                    df.at[idx, "person_name"] = individual_name
                    df.at[idx, "person_id"] = person_id
                    df.at[idx, "source"] = f"FOUNDER_RENAME_{row.get('source', '')}"

                    # オプション: テキストも書き換え
                    if rewrite_text and client:
                        company_name = FOUNDER_PATTERN.match(person_name).group(1)
                        new_text = rewrite_episode_to_individual(
                            client, original_text, company_name, individual_name, age
                        )
                        df.at[idx, "episode_text"] = new_text
                        print("    ✅ テキスト書き換え完了")

                    report["renamed"].append(
                        {
                            "episode_id": episode_id,
                            "original_name": person_name,
                            "new_name": individual_name,
                            "age": age,
                            "dry_run": False,
                        }
                    )
                    renamed_count += 1
                    print("    ✅ 名義変更完了")
                except Exception as e:
                    print(f"    ❌ エラー: {e}")
                    report["errors"].append(
                        {
                            "episode_id": episode_id,
                            "error": str(e),
                        }
                    )
        else:
            # 個人名が含まれないケース（スキップ）
            print(f"  {episode_id}: {person_name} → 個人名なし（スキップ）")
            report["skipped"].append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "reason": "個人名抽出不可",
                }
            )
            skipped_count += 1

    report["summary"] = {
        "renamed_count": renamed_count if not dry_run else len(report["renamed"]),
        "skipped_count": skipped_count,
        "error_count": len(report["errors"]),
    }

    if not dry_run:
        print(f"\n✅ {renamed_count}件名義変更, {skipped_count}件スキップ")

    return df, report


def main():
    parser = argparse.ArgumentParser(description="創業者パターン名義変更")
    parser.add_argument("--execute", action="store_true", help="実際に実行")
    parser.add_argument("--rewrite-text", action="store_true", help="テキストも書き換え")
    parser.add_argument(
        "--output",
        type=str,
        default="reports/founder_naming_fix.json",
        help="レポート出力先",
    )
    args = parser.parse_args()

    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    print(f"📂 読み込み: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📋 総エピソード数: {len(df)}件")

    if args.execute:
        backup_path = csv_path.replace(".csv", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"💾 バックアップ: {backup_path}")

    client = None
    if args.rewrite_text:
        client = get_anthropic_client()

    dry_run = not args.execute
    mode = "[DRY-RUN]" if dry_run else "[EXECUTE]"
    print(f"\n🚀 {mode} 処理開始...")

    df_updated, report = process_founder_episodes(df, client, dry_run=dry_run, rewrite_text=args.rewrite_text)

    if args.execute:
        df_updated.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n💾 保存完了: {csv_path}")

    # タイムスタンプ付きレポートファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output.replace(".json", f"_{timestamp}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {output_path}")

    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"  創業者パターン総数: {report['total_founder_episodes']}件")
    print(f"  名義変更: {len(report['renamed'])}件")
    print(f"  スキップ: {len(report['skipped'])}件")
    print(f"  エラー: {len(report['errors'])}件")


if __name__ == "__main__":
    main()
