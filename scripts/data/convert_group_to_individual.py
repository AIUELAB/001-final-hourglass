#!/usr/bin/env python3
"""
グループ名エピソードを個人エピソードに変換するスクリプト

拡張機能:
1. GROUP_MEMBER_MAPから自動的に変換マッピングを生成
2. 連結名（グループ・個人）の分解機能
3. DISPERSION_RULESに基づく分散処理
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
import anthropic

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.group_master import (
    GROUP_ENTITIES,
    GROUP_MEMBER_MAP,
    get_dispersion_rule,
    get_group_members,
)


# ========================================
# 定数
# ========================================

CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = "reports"
CONCAT_DELIMITERS = ["・", "/", "･"]

# 手動定義のグループ→個人マッピング（追加情報を含む）
MANUAL_GROUP_TO_INDIVIDUAL = {
    "東海オンエア": {"name": "てつや", "birth_year": 1993, "note": "東海オンエアのリーダー、YouTuber"},
    "村田製作所": {"name": "村田恒夫", "birth_year": 1950, "note": "村田製作所会長、電子部品業界のリーダー"},
    "霜降り明星": {"name": "せいや", "birth_year": 1992, "note": "霜降り明星のボケ担当、M-1グランプリ2018優勝"},
    "三代目JSB": {"name": "岩田剛典", "birth_year": 1989, "note": "三代目J SOUL BROTHERSのパフォーマー、俳優"},
    "EXIT": {"name": "兼近大樹", "birth_year": 1991, "note": "EXITのボケ担当、チャラ男キャラで人気"},
    "SANAA": {"name": "妹島和世", "birth_year": 1956, "note": "建築家、プリツカー賞受賞、SANAAの共同創設者"},
    "Official髭男dism": {"name": "藤原聡", "birth_year": 1991, "note": "Official髭男dismのボーカル、作詞作曲"},
    "コムドット": {"name": "やまと", "birth_year": 1998, "note": "コムドットのリーダー、YouTuber"},
    "Kiichi Nakai": {"name": "中井貴一", "birth_year": 1961, "note": "俳優、映画・ドラマで活躍"},
}

# 誤検出除外リスト
EXCLUDE_FROM_SPLIT = {
    "オードリー・ヘプバーン",
    "Audrey Hepburn",
    "マリリン・モンロー",
    "ジャッキー・チェン",
    "ブルース・リー",
}


# ========================================
# 連結名分解
# ========================================


def split_concatenated_name(name: str) -> Tuple[Optional[str], str]:
    """
    連結名を分解: (グループ名, 個人名) または (None, 元の名前)

    例:
    - "嵐・大野智" → ("嵐", "大野智")
    - "ビートルズ・ジョン・レノン" → ("ビートルズ", "ジョン・レノン")
    - "山田太郎" → (None, "山田太郎")
    """
    if name in EXCLUDE_FROM_SPLIT:
        return (None, name)

    for delim in CONCAT_DELIMITERS:
        if delim in name:
            parts = name.split(delim, 1)
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()
                # 左側がグループ名かどうか確認
                if left in GROUP_ENTITIES:
                    return (left, right)
                # GROUP_MEMBER_MAPで右側が登録されているか確認
                if right in GROUP_MEMBER_MAP:
                    expected_group = GROUP_MEMBER_MAP[right]
                    if left == expected_group or left in expected_group:
                        return (left, right)
    return (None, name)


def generate_concat_mappings() -> Dict[str, Dict]:
    """
    GROUP_MEMBER_MAPから連結パターンのマッピングを自動生成

    Returns:
        {"嵐・大野智": {"name": "大野智", "group": "嵐"}, ...}
    """
    mappings = {}

    for member, group in GROUP_MEMBER_MAP.items():
        for delim in CONCAT_DELIMITERS[:2]:  # ・と/
            concat_name = f"{group}{delim}{member}"
            mappings[concat_name] = {"name": member, "group": group, "note": f"{group}のメンバー"}

    return mappings


def get_representative_member(group_name: str) -> Optional[str]:
    """
    グループ名から代表メンバーを取得

    Args:
        group_name: グループ名

    Returns:
        代表メンバー名 または None
    """
    # DISPERSION_RULESから取得
    rule = get_dispersion_rule(group_name)
    if rule and rule.members:
        return rule.members[0]

    # MANUAL_GROUP_TO_INDIVIDUALから取得
    if group_name in MANUAL_GROUP_TO_INDIVIDUAL:
        return MANUAL_GROUP_TO_INDIVIDUAL[group_name]["name"]

    # GROUP_MEMBER_MAPから取得
    members = get_group_members(group_name)
    if members:
        return members[0]

    return None


# ========================================
# LLM変換
# ========================================


def convert_episode_with_llm(
    client, old_name: str, new_name: str, note: str, age: float, old_content: str, category: str
) -> str:
    """LLMを使ってエピソードを個人向けに変換"""

    prompt = f"""以下のグループ/団体名のエピソードを、個人のエピソードに書き換えてください。

【変換ルール】
- グループ名「{old_name}」を個人名「{new_name}」に変換
- 個人情報: {note}
- 年齢: {age}歳のとき
- カテゴリ: {category}

【元のエピソード】
{old_content}

【出力形式】
- 「あなたと同じ{int(age)}歳のとき、{new_name}は...」で始める
- 200-350文字程度
- 事実に基づいた内容に書き換え（架空の内容は避ける）
- グループ活動を個人の視点から描写
- メタ的な説明は含めない

変換後のエピソード本文のみを出力してください（説明や前置きは不要）:"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()


# ========================================
# メイン処理
# ========================================


def main():
    parser = argparse.ArgumentParser(description="グループ名→個人名変換スクリプト")
    parser.add_argument("--execute", action="store_true", help="実際に変換を実行")
    parser.add_argument("--dry-run", action="store_true", help="変換内容を表示するだけ")
    parser.add_argument("--split-only", action="store_true", help="連結名分解のみ（LLM不使用）")
    parser.add_argument("--csv", default=CSV_PATH, help="対象CSVファイル")
    args = parser.parse_args()

    print("=" * 70)
    print("グループ名→個人名 変換スクリプト（拡張版）")
    print("=" * 70)

    # CSVロード
    df = pd.read_csv(args.csv)
    print(f"\n📂 CSV読み込み: {args.csv}")
    print(f"   総レコード数: {len(df)}")

    # 自動生成マッピング
    concat_mappings = generate_concat_mappings()
    print(f"   連結パターンマッピング: {len(concat_mappings)}件")

    # ========================================
    # 変換対象を特定
    # ========================================

    targets = []

    # 1. グループ名が人物名のケース
    for group_name in GROUP_ENTITIES:
        mask = df["person_name"] == group_name
        group_eps = df[mask]
        for idx, row in group_eps.iterrows():
            rep_member = get_representative_member(group_name)
            if rep_member:
                note = f"{group_name}のメンバー"
                if group_name in MANUAL_GROUP_TO_INDIVIDUAL:
                    note = MANUAL_GROUP_TO_INDIVIDUAL[group_name].get("note", note)

                targets.append(
                    {
                        "idx": idx,
                        "episode_id": row["episode_id"],
                        "old_name": group_name,
                        "new_name": rep_member,
                        "group_name": group_name,
                        "age": row.get("age", 0),
                        "old_content": row.get("episode_text", ""),
                        "category": row.get("category", ""),
                        "note": note,
                        "type": "group_as_person",
                    }
                )

    # 2. 連結名パターン
    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", "")).strip()
        if not person_name or person_name in EXCLUDE_FROM_SPLIT:
            continue

        group_name, individual_name = split_concatenated_name(person_name)
        if group_name is not None:
            targets.append(
                {
                    "idx": idx,
                    "episode_id": row.get("episode_id", ""),
                    "old_name": person_name,
                    "new_name": individual_name,
                    "group_name": group_name,
                    "age": row.get("age", 0),
                    "old_content": row.get("episode_text", ""),
                    "category": row.get("category", ""),
                    "note": f"{group_name}のメンバー",
                    "type": "concatenated_name",
                }
            )

    print(f"\n🎯 変換対象: {len(targets)}件")
    print(f"   ├─ グループ名→個人名: {len([t for t in targets if t['type'] == 'group_as_person'])}件")
    print(f"   └─ 連結名分解: {len([t for t in targets if t['type'] == 'concatenated_name'])}件")

    if targets:
        print("\n   【変換対象サンプル（最大20件）】")
        for t in targets[:20]:
            print(f"      {t['episode_id']}: {t['old_name']} → {t['new_name']}")
        if len(targets) > 20:
            print(f"      ... 他 {len(targets) - 20}件")

    if not args.execute and not args.dry_run:
        print("\n💡 --execute または --dry-run を指定してください")
        return

    if not targets:
        print("\n✅ 変換対象がありません")
        return

    # ========================================
    # 変換実行
    # ========================================

    dry_run = not args.execute

    if args.split_only:
        # 連結名分解のみ（LLM不使用）
        print("\n🔧 連結名分解モード（LLM不使用）...")
        converted = []

        for t in targets:
            if t["type"] == "concatenated_name":
                if not dry_run:
                    df.at[t["idx"], "person_name"] = t["new_name"]
                    df.at[t["idx"], "group_name"] = t["group_name"]
                    df.at[t["idx"], "is_group_member"] = True
                converted.append(t["episode_id"])
                print(f"   ✅ {t['old_name']} → {t['new_name']}")

        if not dry_run and converted:
            df.to_csv(args.csv, index=False, encoding="utf-8-sig")
            print(f"\n✅ CSV更新完了: {len(converted)}件変換")
    else:
        # LLMを使った変換
        print("\n🔧 LLM変換モード...")
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        converted = []
        for i, t in enumerate(targets, 1):
            print(f"\n[{i}/{len(targets)}] {t['old_name']} → {t['new_name']} ({t['age']}歳)")

            if not t["old_content"] or pd.isna(t["old_content"]):
                print("  ⏭️ スキップ: コンテンツが空")
                continue

            try:
                new_content = convert_episode_with_llm(
                    client, t["old_name"], t["new_name"], t["note"], t["age"], t["old_content"], t["category"]
                )

                print("  ✅ 変換完了")
                print(f"     旧: {str(t['old_content'])[:60]}...")
                print(f"     新: {new_content[:60]}...")

                if not dry_run:
                    df.at[t["idx"], "person_name"] = t["new_name"]
                    df.at[t["idx"], "episode_text"] = new_content
                    df.at[t["idx"], "group_name"] = t["group_name"]
                    df.at[t["idx"], "is_group_member"] = True
                    converted.append(t["episode_id"])

            except Exception as e:
                print(f"  ❌ エラー: {e}")

        if not dry_run and converted:
            df.to_csv(args.csv, index=False, encoding="utf-8-sig")
            print(f"\n✅ CSV更新完了: {len(converted)}件変換")

    # レポート保存
    if not dry_run:
        os.makedirs(REPORT_DIR, exist_ok=True)
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "split_only" if args.split_only else "llm_convert",
            "converted_count": len(converted),
            "converted_episodes": converted,
        }
        report_path = os.path.join(REPORT_DIR, f"group_to_individual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 レポート: {report_path}")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
