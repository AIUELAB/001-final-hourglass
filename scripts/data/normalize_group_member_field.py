#!/usr/bin/env python3
"""
is_group_memberフィールドの型正規化スクリプト

6種類の混在型を True/False に統一する。

変換ルール:
- 0.0, '0.0', False, 'False', 'FALSE', '', None, NaN → False
- 1.0, '1.0', True, 'True', 'TRUE', 'YES' → True
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Any

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========================================
# 定数
# ========================================

CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = "preserved/data"
REPORT_DIR = "reports"


def normalize_value(value: Any) -> bool:
    """
    is_group_memberの値をboolに正規化

    Args:
        value: 元の値

    Returns:
        bool: 正規化された値
    """
    # NaN/None/空文字列
    if pd.isna(value) or value is None or value == "":
        return False

    # 文字列の場合
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ("true", "yes", "1", "1.0"):
            return True
        else:
            return False

    # 数値の場合
    if isinstance(value, (int, float)):
        return value == 1 or value == 1.0

    # bool の場合
    if isinstance(value, bool):
        return value

    # その他
    return False


def analyze_current_state(df: pd.DataFrame) -> dict:
    """
    現在のis_group_memberフィールドの状態を分析

    Args:
        df: DataFrame

    Returns:
        dict: 分析結果
    """
    col = "is_group_member"

    if col not in df.columns:
        return {"error": f"カラム {col} が存在しません"}

    # 値の分布
    value_counts = {}
    type_counts = {}

    for value in df[col]:
        # 値のカウント
        str_value = str(value) if not pd.isna(value) else "NaN"
        value_counts[str_value] = value_counts.get(str_value, 0) + 1

        # 型のカウント
        type_name = type(value).__name__
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    return {
        "total_rows": len(df),
        "value_distribution": dict(sorted(value_counts.items(), key=lambda x: -x[1])),
        "type_distribution": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "unique_values": len(value_counts),
        "unique_types": len(type_counts),
    }


def check_group_consistency(df: pd.DataFrame) -> dict:
    """
    group_name と is_group_member の整合性をチェック

    ルール:
    - group_name が "未登録" または空 → is_group_member = False
    - group_name に具体的な値 → is_group_member = True

    Args:
        df: DataFrame

    Returns:
        dict: 整合性チェック結果
    """
    inconsistencies = []

    for idx, row in df.iterrows():
        group_name = row.get("group_name", "")
        is_member = row.get("is_group_member")

        # 未登録・空の場合
        if pd.isna(group_name) or group_name == "" or group_name == "未登録":
            if is_member is not False:
                inconsistencies.append(
                    {
                        "index": idx,
                        "person_name": row.get("person_name", "不明"),
                        "group_name": group_name,
                        "is_group_member": is_member,
                        "expected": False,
                        "reason": "group_name is empty or 未登録",
                    }
                )
        # 具体的なグループ名がある場合
        else:
            if is_member is not True:
                inconsistencies.append(
                    {
                        "index": idx,
                        "person_name": row.get("person_name", "不明"),
                        "group_name": group_name,
                        "is_group_member": is_member,
                        "expected": True,
                        "reason": f"group_name is {group_name}",
                    }
                )

    return {"total_checked": len(df), "inconsistencies": inconsistencies, "inconsistency_count": len(inconsistencies)}


def fix_group_consistency(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    group_name に基づいて is_group_member を修正

    Args:
        df: DataFrame

    Returns:
        tuple: (修正されたDataFrame, 修正統計)
    """
    df = df.copy()
    stats = {"fixed": 0, "unchanged": 0}

    for idx, row in df.iterrows():
        group_name = row.get("group_name", "")

        # 未登録・空 → False
        if pd.isna(group_name) or group_name == "" or group_name == "未登録":
            if row["is_group_member"]:
                df.loc[idx, "is_group_member"] = False
                stats["fixed"] += 1
            else:
                stats["unchanged"] += 1
        # 具体的なグループ名 → True
        else:
            if not row["is_group_member"]:
                df.loc[idx, "is_group_member"] = True
                stats["fixed"] += 1
            else:
                stats["unchanged"] += 1

    return df, stats


def normalize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    DataFrameのis_group_memberカラムを正規化

    Args:
        df: 元のDataFrame

    Returns:
        tuple: (正規化されたDataFrame, 変換統計)
    """
    col = "is_group_member"

    if col not in df.columns:
        raise ValueError(f"カラム {col} が存在しません")

    # 変換統計
    stats = {"total_rows": len(df), "to_true": 0, "to_false": 0, "unchanged_true": 0, "unchanged_false": 0}

    # 正規化
    new_values = []
    for idx, value in enumerate(df[col]):
        original_bool = normalize_value(value)
        new_values.append(original_bool)

        if original_bool:
            if isinstance(value, bool) and value is True:
                stats["unchanged_true"] += 1
            else:
                stats["to_true"] += 1
        else:
            if isinstance(value, bool) and value is False:
                stats["unchanged_false"] += 1
            else:
                stats["to_false"] += 1

    # カラムを更新
    df = df.copy()
    df[col] = new_values

    return df, stats


def main():
    parser = argparse.ArgumentParser(description="is_group_memberフィールドの型正規化")
    parser.add_argument("--csv", default=CSV_PATH, help="対象CSVファイル")
    parser.add_argument("--execute", action="store_true", help="実際に正規化を実行")
    parser.add_argument("--analyze-only", action="store_true", help="分析のみ（正規化しない）")
    parser.add_argument("--with-group-check", action="store_true", help="group_nameとの整合性もチェック・修正")
    parser.add_argument("--check-only", action="store_true", help="整合性チェックのみ（修正なし）")
    args = parser.parse_args()

    print("=" * 70)
    print("is_group_member フィールド型正規化スクリプト")
    print("=" * 70)

    # CSV読み込み
    df = pd.read_csv(args.csv)
    print(f"\n📂 CSV読み込み: {args.csv}")
    print(f"   総レコード数: {len(df)}")

    # 現状分析
    print("\n🔍 現状分析...")
    analysis = analyze_current_state(df)

    if "error" in analysis:
        print(f"   ❌ エラー: {analysis['error']}")
        return

    print("\n📊 値の分布:")
    for value, count in analysis["value_distribution"].items():
        percentage = count / analysis["total_rows"] * 100
        print(f"   {value}: {count}件 ({percentage:.1f}%)")

    print("\n📊 型の分布:")
    for type_name, count in analysis["type_distribution"].items():
        percentage = count / analysis["total_rows"] * 100
        print(f"   {type_name}: {count}件 ({percentage:.1f}%)")

    if args.analyze_only:
        print("\n⚠️ --analyze-only モード: 正規化は実行しません")
        return

    # 整合性チェックのみモード
    if args.check_only:
        print("\n🔍 group_nameとの整合性チェック...")
        consistency = check_group_consistency(df)

        print("\n📊 整合性チェック結果:")
        print(f"   総レコード数: {consistency['total_checked']}")
        print(f"   不整合: {consistency['inconsistency_count']}件")

        if consistency["inconsistency_count"] > 0:
            print("\n⚠️ 不整合の例（最初の5件）:")
            for i, inc in enumerate(consistency["inconsistencies"][:5]):
                print(f"   {i + 1}. {inc['person_name']}")
                print(f"      group_name: '{inc['group_name']}'")
                print(f"      is_group_member: {inc['is_group_member']} (期待値: {inc['expected']})")
        else:
            print("   ✅ 整合性問題なし")

        return

    # 正規化実行
    print("\n🔧 正規化処理...")
    df_normalized, stats = normalize_dataframe(df)

    # group_nameとの整合性もチェック・修正
    if args.with_group_check:
        print("\n🔍 group_nameとの整合性チェック・修正...")
        consistency_before = check_group_consistency(df_normalized)
        print(f"   整合性チェック前の不整合: {consistency_before['inconsistency_count']}件")

        if consistency_before["inconsistency_count"] > 0:
            df_normalized, fix_stats = fix_group_consistency(df_normalized)
            print(f"   整合性修正: {fix_stats['fixed']}件")

            consistency_after = check_group_consistency(df_normalized)
            print(f"   整合性チェック後の不整合: {consistency_after['inconsistency_count']}件")

    print("\n📊 変換結果:")
    print(f"   True維持: {stats['unchanged_true']}件")
    print(f"   False維持: {stats['unchanged_false']}件")
    print(f"   → Trueに変換: {stats['to_true']}件")
    print(f"   → Falseに変換: {stats['to_false']}件")

    # 正規化後の確認
    print("\n🔍 正規化後の状態:")
    post_analysis = analyze_current_state(df_normalized)
    for value, count in post_analysis["value_distribution"].items():
        percentage = count / post_analysis["total_rows"] * 100
        print(f"   {value}: {count}件 ({percentage:.1f}%)")

    if not args.execute:
        print("\n⚠️ --execute を指定すると実際に保存されます")
        return

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"MASTER_EPISODES_CURRENT_backup_{timestamp}.csv")
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 バックアップ: {backup_path}")

    # CSV保存
    df_normalized.to_csv(args.csv, index=False, encoding="utf-8-sig")
    print(f"✅ CSV更新完了: {args.csv}")

    # レポート保存
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "csv_path": args.csv,
        "before": analysis,
        "after": post_analysis,
        "stats": stats,
    }

    import json

    report_path = os.path.join(REPORT_DIR, f"normalize_group_member_{timestamp}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {report_path}")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
