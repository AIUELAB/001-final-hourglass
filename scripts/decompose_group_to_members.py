#!/usr/bin/env python3
"""
グループエピソード → メンバー個人エピソード分解スクリプト

目的: グループ名義のエピソードを個人メンバーのエピソードに変換
原則: 「エピソードは個人のものであるべき」

処理フロー:
1. GROUP_ENTITIESに含まれるperson_nameのエピソードを検出
2. DISPERSION_RULESに基づきメンバーを特定
3. LLMで各メンバー視点のエピソードに変換
4. 元のグループエピソードを削除
5. 新しい個人エピソードを追加
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.group_master import (
    GROUP_ENTITIES,
    DispersionStrategy,
    get_dispersion_rule,
)

# Anthropic API
try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


def get_anthropic_client():
    """Anthropicクライアントを取得"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    return Anthropic(api_key=api_key)


def detect_group_episodes(df: pd.DataFrame) -> pd.DataFrame:
    """グループエピソードを検出"""
    group_eps = df[df["person_name"].apply(lambda x: str(x) in GROUP_ENTITIES)]
    return group_eps


def generate_member_episode(
    client: Anthropic,
    group_name: str,
    member_name: str,
    original_episode: str,
    age: float,
) -> str:
    """LLMでメンバー個人視点のエピソードを生成"""

    prompt = f"""以下のグループ「{group_name}」のエピソードを、メンバー「{member_name}」個人の視点で書き直してください。

【元のグループエピソード（{age}歳時点）】
{original_episode}

【変換ルール】
1. 「あなたと同じ{int(age)}歳のとき、{member_name}は」で始める
2. グループ名ではなく{member_name}個人の行動・心情・決断を中心に描写
3. グループとしての活動であっても、{member_name}の個人的な貢献や視点を強調
4. 事実に基づきつつ、{member_name}らしい表現を心がける
5. 文字数は350-500文字程度
6. メタ的な説明（「このエピソードは〜」など）は含めない

【出力】
変換後のエピソード本文のみを出力してください。"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()


def generate_new_episode_id(existing_ids: set) -> str:
    """新しいエピソードIDを生成"""
    import random

    while True:
        new_id = f"EP-{random.randint(900000, 999999)}"
        if new_id not in existing_ids:
            return new_id


def get_or_create_person_id(df: pd.DataFrame, member_name: str, group_name: str) -> str:
    """メンバーのperson_idを取得または新規生成"""
    existing = df[df["person_name"] == member_name]
    if not existing.empty:
        return existing["person_id"].iloc[0]

    # 新規生成
    import hashlib

    hash_input = f"{member_name}_{group_name}"
    hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()
    return f"P{hash_val}"


def decompose_group_episodes(
    df: pd.DataFrame,
    client: Anthropic,
    dry_run: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """グループエピソードをメンバー個人に分解"""

    group_eps = detect_group_episodes(df)
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_group_episodes": len(group_eps),
        "decomposed": [],
        "skipped": [],
        "errors": [],
    }

    if len(group_eps) == 0:
        print("グループエピソードが見つかりません")
        return df, report

    print(f"検出されたグループエピソード: {len(group_eps)}件")

    # グループごとに処理
    groups = group_eps.groupby("person_name")
    existing_ids = set(df["episode_id"].tolist())

    new_rows = []
    rows_to_delete = []

    for group_name, group_df in groups:
        print(f"\n処理中: {group_name} ({len(group_df)}件)")

        # DISPERSION_RULEを取得
        rule = get_dispersion_rule(group_name)
        if rule is None:
            print(f"  ⚠️ DISPERSION_RULE未定義: {group_name}")
            report["skipped"].append({"group_name": group_name, "reason": "DISPERSION_RULE未定義"})
            continue

        members = rule.members
        strategy = rule.strategy
        print(f"  ルール: {strategy.name}, メンバー: {members}")

        for _, row in group_df.iterrows():
            episode_id = row["episode_id"]
            age = row["age"]
            original_text = row["episode_text"]

            print(f"    エピソード: {episode_id} (age={age})")

            # 分解対象メンバーを決定
            if strategy == DispersionStrategy.ALL:
                target_members = members
            elif strategy == DispersionStrategy.REPRESENTATIVE:
                # 代表者1名のみ（最初のメンバー）
                target_members = [members[0]]
            else:
                target_members = members[:1]

            for member in target_members:
                if dry_run:
                    print(f"      [DRY-RUN] {member}用エピソード生成予定")
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
                        # LLMでエピソード生成
                        new_text = generate_member_episode(client, group_name, member, original_text, age)
                        new_id = generate_new_episode_id(existing_ids)
                        existing_ids.add(new_id)

                        person_id = get_or_create_person_id(df, member, group_name)

                        # 新しい行を作成
                        new_row = row.copy()
                        new_row["episode_id"] = new_id
                        new_row["person_id"] = person_id
                        new_row["person_name"] = member
                        new_row["episode_text"] = new_text
                        new_row["group_name"] = group_name
                        new_row["is_group_member"] = True
                        new_row["source"] = f"GROUP_DECOMPOSE_{row.get('source', '')}"
                        new_row["generation_timestamp"] = datetime.now().isoformat()

                        new_rows.append(new_row)
                        print(f"      ✅ {member}: {new_id} 生成完了")

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
                        print(f"      ❌ {member}: エラー - {e}")
                        report["errors"].append(
                            {
                                "episode_id": episode_id,
                                "member_name": member,
                                "error": str(e),
                            }
                        )

            # 元のグループエピソードを削除対象に追加
            if not dry_run:
                rows_to_delete.append(episode_id)

    # DataFrameを更新
    if not dry_run and new_rows:
        # 新しい行を追加
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)

        # 元のグループエピソードを削除
        df = df[~df["episode_id"].isin(rows_to_delete)]

        print(f"\n✅ {len(new_rows)}件の個人エピソード追加")
        print(f"✅ {len(rows_to_delete)}件のグループエピソード削除")

    report["new_episodes_count"] = len(new_rows)
    report["deleted_episodes_count"] = len(rows_to_delete)

    return df, report


def main():
    parser = argparse.ArgumentParser(description="グループエピソードをメンバー個人に分解")
    parser.add_argument("--execute", action="store_true", help="実際に分解を実行（デフォルトはdry-run）")
    parser.add_argument(
        "--output",
        type=str,
        default="reports/group_decompose_report.json",
        help="レポート出力先",
    )
    args = parser.parse_args()

    # データ読み込み
    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    print(f"📂 読み込み: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📋 総エピソード数: {len(df)}件")

    # バックアップ作成
    if args.execute:
        backup_path = csv_path.replace(".csv", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"💾 バックアップ: {backup_path}")

    # Anthropicクライアント取得
    client = get_anthropic_client()

    # 分解実行
    dry_run = not args.execute
    if dry_run:
        print("\n🔍 [DRY-RUN] 実行プレビュー（--executeで実行）")
    else:
        print("\n🚀 [EXECUTE] 分解実行中...")

    df_updated, report = decompose_group_episodes(df, client, dry_run=dry_run)

    # 結果保存
    if args.execute and report["new_episodes_count"] > 0:
        df_updated.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n💾 保存完了: {csv_path}")

    # レポート保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {args.output}")

    # サマリー
    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"  グループエピソード総数: {report['total_group_episodes']}件")
    print(f"  分解済み: {len(report['decomposed'])}件")
    print(f"  スキップ: {len(report['skipped'])}件")
    print(f"  エラー: {len(report['errors'])}件")


if __name__ == "__main__":
    main()
