#!/usr/bin/env python3
"""
Phase 3-B: 表記ゆれ正規化・特殊ケース修正スクリプト

対象:
1. 表記ゆれ正規化（同一IDで複数表記）
2. グループ名付き個人名の分離（YOASOBI・幾田りら→幾田りら）
3. 孫悟空/孫悟飯の別キャラクター分離
4. nan ID補完

Usage:
    python scripts/fix_variant_names.py [--analyze-only] [--execute]
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========================================
# 定数
# ========================================

CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = "preserved/data"
REPORT_DIR = "reports"

# ========================================
# 修正ルール
# ========================================

# 表記ゆれ正規化ルール: {person_id: 正規表記}
VARIANT_NORMALIZATION: dict[str, str] = {
    "P0023C1D": "アンドリュー・ン",  # ング→ン
    "P56E484": "スティーブン・ホーキング",  # スティーヴン→スティーブン
    "P8160B1F": "スティーブン・スピルバーグ",  # スティーヴン→スティーブン
    "PA8A3070": "アジャコング",  # アジャ・コング→アジャコング
    "PCC1D22": "ガブリエル・ガルシア＝マルケス",  # ・→＝
    "PD99CD83": "千代の富士",  # 千代の富士貢→千代の富士
}

# グループ名付き個人名の分離
GROUP_PREFIX_FIX = {
    "P5185842": {
        "patterns": ["YOASOBI・幾田りら", "YOASOBI（幾田りら）"],
        "individual_name": "幾田りら",
    }
}

# 孫悟空/孫悟飯分離ルール
# 同一IDに2つの別キャラクターが混在している問題を解決
GOKU_GOHAN_SEPARATION = {
    "original_id": "P7E0F1FE",
    "goku": {
        "pattern": "孫悟空",
        "canonical_name": "孫悟空『ドラゴンボール』",
        # 新IDは実行時に生成
    },
    "gohan": {
        "pattern": "孫悟飯",
        "canonical_name": "孫悟飯『ドラゴンボール』",
        "keep_id": True,  # 既存IDを維持
    },
}


def generate_person_id(name: str) -> str:
    """人物名からIDを生成"""
    hash_str = hashlib.md5(name.encode()).hexdigest()[:7].upper()
    return f"P{hash_str}"


def analyze_current_state(df: pd.DataFrame) -> dict:
    """現状分析"""
    from collections import defaultdict

    # 同一IDで複数表記
    id_to_names = defaultdict(set)
    for _, row in df.iterrows():
        if pd.notna(row["person_id"]):
            id_to_names[str(row["person_id"])].add(str(row["person_name"]))

    multi_name = {k: list(v) for k, v in id_to_names.items() if len(v) > 1}

    # nan IDカウント
    nan_rows = df[df["person_id"].isna()].copy()

    return {
        "total_records": len(df),
        "unique_ids": df["person_id"].dropna().nunique(),
        "nan_id_count": len(nan_rows),
        "nan_id_persons": nan_rows["person_name"].tolist() if len(nan_rows) > 0 else [],
        "multi_name_ids": multi_name,
        "multi_name_count": len(multi_name),
    }


def fix_variant_names(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """表記ゆれを正規化"""
    changes = []
    df = df.copy()

    for person_id, canonical_name in VARIANT_NORMALIZATION.items():
        mask = df["person_id"] == person_id
        if mask.sum() == 0:
            continue

        original_names = df.loc[mask, "person_name"].unique().tolist()
        needs_update = [n for n in original_names if n != canonical_name]

        if needs_update:
            df.loc[mask, "person_name"] = canonical_name
            changes.append(
                {
                    "type": "normalize_variant",
                    "person_id": person_id,
                    "original_names": original_names,
                    "canonical_name": canonical_name,
                    "affected_rows": mask.sum(),
                }
            )

    return df, changes


def fix_group_prefix_names(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """グループ名付き個人名を修正（YOASOBI・幾田りら → 幾田りら）"""
    changes = []
    df = df.copy()

    for person_id, rule in GROUP_PREFIX_FIX.items():
        individual_name = rule["individual_name"]

        mask = df["person_id"] == person_id
        if mask.sum() == 0:
            continue

        original_names = df.loc[mask, "person_name"].unique().tolist()
        needs_update = [n for n in original_names if n != individual_name]

        if needs_update:
            df.loc[mask, "person_name"] = individual_name
            changes.append(
                {
                    "type": "fix_group_prefix",
                    "person_id": person_id,
                    "original_names": original_names,
                    "individual_name": individual_name,
                    "affected_rows": mask.sum(),
                }
            )

    return df, changes


def separate_goku_gohan(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """孫悟空/孫悟飯を別キャラクターとして分離"""
    changes = []
    df = df.copy()

    original_id = GOKU_GOHAN_SEPARATION["original_id"]
    goku_rule = GOKU_GOHAN_SEPARATION["goku"]
    gohan_rule = GOKU_GOHAN_SEPARATION["gohan"]

    # 孫悟空用の新IDを生成
    goku_new_id = generate_person_id("孫悟空_ドラゴンボール_goku")

    # 孫悟空のエピソードを分離
    goku_mask = (df["person_id"] == original_id) & (df["person_name"].str.contains(goku_rule["pattern"], na=False))
    goku_count = goku_mask.sum()

    if goku_count > 0:
        df.loc[goku_mask, "person_id"] = goku_new_id
        df.loc[goku_mask, "person_name"] = goku_rule["canonical_name"]
        changes.append(
            {
                "type": "separate_character",
                "character": "孫悟空",
                "original_id": original_id,
                "new_id": goku_new_id,
                "canonical_name": goku_rule["canonical_name"],
                "affected_rows": goku_count,
            }
        )

    # 孫悟飯のエピソードは既存IDを維持、名前だけ正規化
    gohan_mask = (df["person_id"] == original_id) & (df["person_name"].str.contains(gohan_rule["pattern"], na=False))
    gohan_count = gohan_mask.sum()

    if gohan_count > 0:
        df.loc[gohan_mask, "person_name"] = gohan_rule["canonical_name"]
        changes.append(
            {
                "type": "normalize_character",
                "character": "孫悟飯",
                "person_id": original_id,
                "canonical_name": gohan_rule["canonical_name"],
                "affected_rows": gohan_count,
            }
        )

    return df, changes


def fix_nan_ids(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """nan IDを補完"""
    changes = []
    df = df.copy()

    nan_mask = df["person_id"].isna()

    for idx in df[nan_mask].index:
        row = df.loc[idx]
        person_name = row["person_name"]
        new_id = generate_person_id(str(person_name))

        df.at[idx, "person_id"] = new_id
        changes.append(
            {
                "type": "fix_nan_id",
                "episode_id": row["episode_id"],
                "person_name": person_name,
                "new_id": new_id,
            }
        )

    return df, changes


def main():
    parser = argparse.ArgumentParser(description="Phase 3-B: 表記ゆれ正規化・特殊ケース修正")
    parser.add_argument("--csv", default=CSV_PATH, help="対象CSVファイル")
    parser.add_argument("--execute", action="store_true", help="実際に修正を実行")
    parser.add_argument("--analyze-only", action="store_true", help="分析のみ（修正しない）")
    args = parser.parse_args()

    print("=" * 70)
    print("Phase 3-B: 表記ゆれ正規化・特殊ケース修正スクリプト")
    print("=" * 70)

    # CSV読み込み
    df = pd.read_csv(args.csv)
    print(f"\n📂 CSV読み込み: {args.csv}")
    print(f"   総レコード数: {len(df)}")

    # 現状分析
    print("\n🔍 現状分析...")
    analysis_before = analyze_current_state(df)
    print(f"   ユニークID: {analysis_before['unique_ids']}件")
    print(f"   nan ID: {analysis_before['nan_id_count']}件")
    print(f"   複数表記ID: {analysis_before['multi_name_count']}件")

    if analysis_before["multi_name_ids"]:
        print("\n   複数表記の詳細:")
        for pid, names in analysis_before["multi_name_ids"].items():
            print(f"     {pid}: {names}")

    if analysis_before["nan_id_persons"]:
        print("\n   nan IDの人物:")
        for name in analysis_before["nan_id_persons"]:
            print(f"     - {name}")

    if args.analyze_only:
        print("\n⚠️ --analyze-only モード: 修正は実行しません")
        return

    # 修正処理
    all_changes = []

    print("\n🔧 1. 表記ゆれ正規化...")
    df, changes = fix_variant_names(df)
    all_changes.extend(changes)
    print(f"   → {len(changes)}件の正規化")
    for c in changes:
        print(f"     {c['person_id']}: {c['original_names']} → {c['canonical_name']}")

    print("\n🔧 2. グループ名付き個人名修正...")
    df, changes = fix_group_prefix_names(df)
    all_changes.extend(changes)
    print(f"   → {len(changes)}件の修正")
    for c in changes:
        print(f"     {c['person_id']}: {c['original_names']} → {c['individual_name']}")

    print("\n🔧 3. 孫悟空/孫悟飯分離...")
    df, changes = separate_goku_gohan(df)
    all_changes.extend(changes)
    print(f"   → {len(changes)}件の分離/正規化")
    for c in changes:
        if c["type"] == "separate_character":
            print(f"     {c['character']}: 新ID {c['new_id']} ({c['affected_rows']}件)")
        else:
            print(f"     {c['character']}: ID維持 {c['person_id']} ({c['affected_rows']}件)")

    print("\n🔧 4. nan ID補完...")
    df, changes = fix_nan_ids(df)
    all_changes.extend(changes)
    print(f"   → {len(changes)}件の補完")
    for c in changes:
        print(f"     {c['person_name']}: {c['new_id']}")

    # 修正後の分析
    print("\n🔍 修正後の状態:")
    analysis_after = analyze_current_state(df)
    print(f"   ユニークID: {analysis_after['unique_ids']}件")
    print(f"   nan ID: {analysis_after['nan_id_count']}件")
    print(f"   複数表記ID: {analysis_after['multi_name_count']}件")

    # 変更サマリー
    print("\n📊 変更サマリー:")
    print(f"   総変更: {len(all_changes)}件")

    if not args.execute:
        print("\n⚠️ --execute を指定すると実際に保存されます")
        return

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"MASTER_EPISODES_CURRENT_backup_{timestamp}.csv")
    pd.read_csv(args.csv).to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 バックアップ: {backup_path}")

    # CSV保存
    df.to_csv(args.csv, index=False, encoding="utf-8-sig")
    print(f"✅ CSV更新完了: {args.csv}")

    # レポート保存
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "csv_path": args.csv,
        "before": {
            k: v
            for k, v in analysis_before.items()
            if k != "multi_name_ids"  # 大きすぎる場合省略
        },
        "after": {k: v for k, v in analysis_after.items() if k != "multi_name_ids"},
        "changes": all_changes,
        "summary": {
            "normalize_variant": len([c for c in all_changes if c["type"] == "normalize_variant"]),
            "fix_group_prefix": len([c for c in all_changes if c["type"] == "fix_group_prefix"]),
            "separate_character": len([c for c in all_changes if c["type"] == "separate_character"]),
            "normalize_character": len([c for c in all_changes if c["type"] == "normalize_character"]),
            "fix_nan_id": len([c for c in all_changes if c["type"] == "fix_nan_id"]),
        },
    }

    report_path = os.path.join(REPORT_DIR, f"fix_variant_names_{timestamp}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {report_path}")

    print("\n✅ Phase 3-B完了")


if __name__ == "__main__":
    main()
