#!/usr/bin/env python3
"""
グループエンティティ包括修正スクリプト

処理方針:
1. ALL/REPRESENTATIVE戦略: メンバー個人にエピソード分解
2. DELETE戦略: エピソード内の個人名を抽出して紐付け、不可なら削除
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.group_master import (
    DISPERSION_RULES,
    GROUP_ENTITIES,
    DispersionStrategy,
    get_dispersion_rule,
)

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed")
    sys.exit(1)


# エピソード内の個人名抽出パターン（DELETE戦略用）
INDIVIDUAL_EXTRACTION_PATTERNS = {
    # ===== Phase 4: スポーツ・研究チーム =====
    "清水エスパルス": r"(竹内彬|三浦知良|武田修宏|長谷川健太)",
    "湘南ベルマーレ": r"(中田英寿|名良橋晃|呂比須ワグナー)",
    "星稜高校": r"(松井秀喜|山下智茂|本田圭佑)",
    "東海大学相模": r"(田中広輔|菅野智之|原辰徳)",
    "青色LED開発チーム": r"(中村修二|赤崎勇|天野浩)",
    "ASIMO開発チーム": r"(広瀬真人|石井裕之)",
    # ===== Phase 5追加: 学校チーム =====
    "智弁和歌山": r"(高嶋仁|岡田龍生|中谷仁|武内晋一|西川遥輝)",
    "流経大柏高校": r"(本田裕一郎|田中順也|関川郁万)",
    "駒大苫小牧": r"(田中将大|香田誉士史|林裕也|本間篤史)",
    "早稲田実業": r"(斎藤佑樹|荒木大輔|王貞治|清宮幸太郎)",
    # ===== Phase 5追加: 創業者チーム =====
    "富士フイルム創業者": r"(古森重隆|小林節太郎)",
    "島津製作所創業者": r"(島津源蔵)",
}


def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY required")
    return Anthropic(api_key=api_key)


def extract_individual_from_text(group_name: str, text: str) -> str | None:
    """エピソードテキストから個人名を抽出"""
    pattern = INDIVIDUAL_EXTRACTION_PATTERNS.get(group_name)
    if pattern:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def generate_member_episode(
    client: Anthropic,
    group_name: str,
    member_name: str,
    original_text: str,
    age: float,
) -> str:
    """LLMでメンバー個人視点のエピソードを生成"""
    prompt = f"""以下のグループ「{group_name}」のエピソードを、メンバー「{member_name}」個人の視点で書き直してください。

【元のグループエピソード（{age}歳時点）】
{original_text}

【変換ルール】
1. 「あなたと同じ{int(age)}歳のとき、{member_name}は」で始める
2. グループ名ではなく{member_name}個人の行動・心情・決断を中心に描写
3. 事実に基づきつつ、{member_name}らしい表現を心がける
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


def rename_episode_to_individual(
    client: Anthropic,
    individual_name: str,
    original_text: str,
    age: float,
) -> str:
    """エピソードを個人名義に書き換え"""
    prompt = f"""以下のエピソードを「{individual_name}」個人のエピソードとして書き直してください。

【元のエピソード（{age}歳時点）】
{original_text}

【変換ルール】
1. 「あなたと同じ{int(age)}歳のとき、{individual_name}は」で始める
2. {individual_name}個人の視点・行動・決断を中心に描写
3. 組織名（チーム名、学校名など）は背景情報として残してよい
4. 文字数は350-500文字程度

【出力】
変換後のエピソード本文のみを出力してください。"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_new_episode_id(existing_ids: set) -> str:
    import random

    while True:
        new_id = f"EP-{random.randint(900000, 999999)}"
        if new_id not in existing_ids:
            return new_id


def get_or_create_person_id(df: pd.DataFrame, name: str) -> str:
    existing = df[df["person_name"] == name]
    if not existing.empty:
        return existing["person_id"].iloc[0]
    import hashlib

    hash_val = hashlib.md5(name.encode()).hexdigest()[:8].upper()
    return f"P{hash_val}"


def process_group_episodes(
    df: pd.DataFrame,
    client: Anthropic,
    dry_run: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """グループエピソードを処理"""

    # GROUP_ENTITIESに含まれるエピソードを検出
    group_eps = df[df["person_name"].apply(lambda x: str(x) in GROUP_ENTITIES)]

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_group_episodes": len(group_eps),
        "decomposed": [],
        "renamed": [],
        "deleted": [],
        "errors": [],
    }

    if len(group_eps) == 0:
        print("グループエピソードが見つかりません")
        return df, report

    print(f"検出されたグループエピソード: {len(group_eps)}件")

    existing_ids = set(df["episode_id"].tolist())
    new_rows = []
    rows_to_delete = []
    rows_to_update = []  # (index, updates_dict)

    groups = group_eps.groupby("person_name")

    for group_name, group_df in groups:
        print(f"\n処理中: {group_name} ({len(group_df)}件)")

        rule = get_dispersion_rule(group_name)
        if rule is None:
            print(f"  ⚠️ DISPERSION_RULE未定義: {group_name}")
            report["errors"].append({"group_name": group_name, "error": "DISPERSION_RULE未定義"})
            continue

        strategy = rule.strategy
        members = rule.members
        print(f"  戦略: {strategy.name}")

        for idx, row in group_df.iterrows():
            episode_id = row["episode_id"]
            age = row["age"]
            original_text = row["episode_text"]

            if strategy == DispersionStrategy.DELETE:
                # DELETE戦略: エピソード内の個人名を抽出
                individual = extract_individual_from_text(group_name, str(original_text))

                if individual:
                    print(f"    {episode_id}: 個人名検出 → {individual}")
                    if dry_run:
                        report["renamed"].append(
                            {
                                "episode_id": episode_id,
                                "group_name": group_name,
                                "new_person_name": individual,
                                "dry_run": True,
                            }
                        )
                    else:
                        try:
                            # エピソードを個人名義に書き換え
                            new_text = rename_episode_to_individual(client, individual, original_text, age)
                            person_id = get_or_create_person_id(df, individual)

                            rows_to_update.append(
                                (
                                    idx,
                                    {
                                        "person_id": person_id,
                                        "person_name": individual,
                                        "episode_text": new_text,
                                        "source": f"GROUP_RENAME_{row.get('source', '')}",
                                    },
                                )
                            )

                            report["renamed"].append(
                                {
                                    "episode_id": episode_id,
                                    "group_name": group_name,
                                    "new_person_name": individual,
                                    "dry_run": False,
                                }
                            )
                            print(f"      ✅ {individual}に名義変更完了")
                        except Exception as e:
                            print(f"      ❌ エラー: {e}")
                            report["errors"].append(
                                {
                                    "episode_id": episode_id,
                                    "error": str(e),
                                }
                            )
                else:
                    print(f"    {episode_id}: 個人名検出不可 → 削除")
                    if not dry_run:
                        rows_to_delete.append(episode_id)
                    report["deleted"].append(
                        {
                            "episode_id": episode_id,
                            "group_name": group_name,
                            "reason": "個人名抽出不可",
                            "dry_run": dry_run,
                        }
                    )

            elif strategy in (DispersionStrategy.ALL, DispersionStrategy.REPRESENTATIVE):
                # ALL/REPRESENTATIVE戦略: メンバーに分解
                target_members = members if strategy == DispersionStrategy.ALL else members[:1]

                for member in target_members:
                    if dry_run:
                        print(f"    {episode_id} → {member} (DRY-RUN)")
                        report["decomposed"].append(
                            {
                                "original_episode_id": episode_id,
                                "group_name": group_name,
                                "member_name": member,
                                "age": age,
                                "dry_run": True,
                            }
                        )
                    else:
                        try:
                            new_text = generate_member_episode(client, group_name, member, original_text, age)
                            new_id = generate_new_episode_id(existing_ids)
                            existing_ids.add(new_id)
                            person_id = get_or_create_person_id(df, member)

                            new_row = row.copy()
                            new_row["episode_id"] = new_id
                            new_row["person_id"] = person_id
                            new_row["person_name"] = member
                            new_row["episode_text"] = new_text
                            new_row["group_name"] = group_name
                            new_row["is_group_member"] = True
                            new_row["source"] = f"GROUP_DECOMPOSE_{row.get('source', '')}"

                            new_rows.append(new_row)
                            print(f"    ✅ {member}: {new_id}")

                            report["decomposed"].append(
                                {
                                    "original_episode_id": episode_id,
                                    "new_episode_id": new_id,
                                    "group_name": group_name,
                                    "member_name": member,
                                    "age": age,
                                    "dry_run": False,
                                }
                            )
                        except Exception as e:
                            print(f"    ❌ {member}: {e}")
                            report["errors"].append(
                                {
                                    "episode_id": episode_id,
                                    "member_name": member,
                                    "error": str(e),
                                }
                            )

                if not dry_run:
                    rows_to_delete.append(episode_id)

    # DataFrameを更新
    if not dry_run:
        # 行の更新
        for idx, updates in rows_to_update:
            for col, val in updates.items():
                df.at[idx, col] = val

        # 新しい行を追加
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            df = pd.concat([df, new_df], ignore_index=True)

        # 削除
        if rows_to_delete:
            df = df[~df["episode_id"].isin(rows_to_delete)]

        print(f"\n✅ {len(new_rows)}件追加, {len(rows_to_update)}件更新, {len(rows_to_delete)}件削除")

    report["summary"] = {
        "new_episodes": len(new_rows),
        "renamed_episodes": len([r for r in report["renamed"] if not r.get("dry_run")]),
        "deleted_episodes": len(rows_to_delete),
    }

    return df, report


def main():
    parser = argparse.ArgumentParser(description="グループエンティティ包括修正")
    parser.add_argument("--execute", action="store_true", help="実際に実行")
    parser.add_argument(
        "--output",
        type=str,
        default="reports/group_entity_fix_comprehensive.json",
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

    client = get_anthropic_client()

    dry_run = not args.execute
    mode = "[DRY-RUN]" if dry_run else "[EXECUTE]"
    print(f"\n🚀 {mode} 処理開始...")

    df_updated, report = process_group_episodes(df, client, dry_run=dry_run)

    if args.execute:
        df_updated.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n💾 保存完了: {csv_path}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {args.output}")

    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"  グループエピソード総数: {report['total_group_episodes']}件")
    print(f"  分解: {len(report['decomposed'])}件")
    print(f"  名義変更: {len(report['renamed'])}件")
    print(f"  削除: {len(report['deleted'])}件")
    print(f"  エラー: {len(report['errors'])}件")


if __name__ == "__main__":
    main()
