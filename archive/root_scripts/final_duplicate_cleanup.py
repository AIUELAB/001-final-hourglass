#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終重複クリーンアップ - 残りの明確な重複を削除

発見された重複:
- P015985 (George Washington) vs P000753 (George Washington) - 100%一致
- P015986 (Thomas Jefferson) vs P000949 (Thomas Jefferson) - 100%一致
- P003511 (Yukina Kinoshita) vs P003510 (Yuka Kinoshita) - 93.3%類似
"""

import pandas as pd
import json
import shutil
from datetime import datetime

def analyze_final_duplicates():
    """最終重複を詳細分析"""
    df = pd.read_csv("ultra_think_DUPLICATES_REMOVED_20250831_191147.csv")

    # 明確な重複ペア
    duplicate_pairs = [
        ('P015985', 'P000753'),  # George Washington
        ('P015986', 'P000949'),  # Thomas Jefferson
        ('P003511', 'P003510')   # Yukina/Yuka Kinoshita
    ]

    print("🔍 最終重複ペア詳細分析")
    print("="*60)

    final_removals = []
    analysis_details = []

    for newer_id, older_id in duplicate_pairs:
        newer_record = df[df['person_id'] == newer_id]
        older_record = df[df['person_id'] == older_id]

        if not newer_record.empty and not older_record.empty:
            newer = newer_record.iloc[0]
            older = older_record.iloc[0]

            print(f"\n📋 重複ペア分析: {newer_id} vs {older_id}")
            print(f"  新: {newer['person_name']} (認知度: {newer['name_recognition']})")
            print(f"  旧: {older['person_name']} (認知度: {older['name_recognition']})")

            # 削除判定
            if newer['name_recognition'] > older['name_recognition']:
                remove_id = older_id
                keep_id = newer_id
                reason = f"認知度が低い ({older['name_recognition']} < {newer['name_recognition']})"
            elif newer['name_recognition'] < older['name_recognition']:
                remove_id = newer_id
                keep_id = older_id
                reason = f"認知度が低い ({newer['name_recognition']} < {older['name_recognition']})"
            else:
                # 認知度が同じ場合、より新しいIDを削除
                remove_id = newer_id
                keep_id = older_id
                reason = f"IDが新しい ({newer_id} > {older_id})"

            final_removals.append(remove_id)
            analysis_details.append({
                'remove_id': remove_id,
                'keep_id': keep_id,
                'reason': reason,
                'name_match': newer['person_name'] == older['person_name'],
                'recognition_diff': abs(newer['name_recognition'] - older['name_recognition'])
            })

            print(f"  決定: {remove_id} を削除, {keep_id} を保持")
            print(f"  理由: {reason}")

    return final_removals, analysis_details

def execute_final_cleanup():
    """最終クリーンアップを実行"""
    # 現在のクリーンファイルを読み込み
    df = pd.read_csv("ultra_think_DUPLICATES_REMOVED_20250831_191147.csv")

    # 最終削除対象を特定
    final_removals, analysis_details = analyze_final_duplicates()

    if not final_removals:
        print("✅ 追加削除不要 - すべての重複が解決済み")
        return "ultra_think_DUPLICATES_REMOVED_20250831_191147.csv"

    print(f"\n🗑️ 最終削除実行: {len(final_removals)} 件")

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_before_final_cleanup_{timestamp}.csv"
    shutil.copy2("ultra_think_DUPLICATES_REMOVED_20250831_191147.csv", backup_file)
    print(f"💾 バックアップ作成: {backup_file}")

    # 最終削除実行
    initial_count = len(df)
    final_df = df[~df['person_id'].isin(final_removals)].copy()
    final_count = len(final_df)

    # 出力ファイル保存
    output_file = f"ultra_think_FINAL_CLEAN_{timestamp}.csv"
    final_df.to_csv(output_file, index=False, encoding='utf-8')

    # ログ作成
    cleanup_log = {
        "final_cleanup_timestamp": datetime.now().isoformat(),
        "input_file": "ultra_think_DUPLICATES_REMOVED_20250831_191147.csv",
        "output_file": output_file,
        "backup_file": backup_file,
        "records_before": initial_count,
        "records_after": final_count,
        "final_removals": len(final_removals),
        "removed_person_ids": final_removals,
        "analysis_details": analysis_details,
        "total_duplicates_removed": 77 + len(final_removals),  # 前回 + 今回
        "cleanup_efficiency": f"{((77 + len(final_removals)) / 4881 * 100):.2f}%"
    }

    log_file = f"FINAL_CLEANUP_LOG_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(cleanup_log, f, ensure_ascii=False, indent=2)

    print(f"✅ 最終クリーンアップ完了:")
    print(f"  - 削除前: {initial_count:,} レコード")
    print(f"  - 削除後: {final_count:,} レコード")
    print(f"  - 今回削除: {len(final_removals)} レコード")
    print(f"  - 総削除数: {77 + len(final_removals)} レコード")
    print(f"  - クリーンアップ効率: {cleanup_log['cleanup_efficiency']}")
    print(f"📄 最終クリーンファイル: {output_file}")
    print(f"📝 クリーンアップログ: {log_file}")

    return output_file

def verify_final_database():
    """最終データベースの品質検証"""
    # 最新の出力ファイルを確認
    import glob
    clean_files = glob.glob("ultra_think_FINAL_CLEAN_*.csv")
    if clean_files:
        latest_file = max(clean_files)
        df = pd.read_csv(latest_file)

        print(f"\n📊 最終データベース品質検証: {latest_file}")
        print("="*60)
        print(f"総レコード数: {len(df):,}")
        print(f"カテゴリ分布:")
        category_counts = df['category'].value_counts()
        for category, count in category_counts.head(10).items():
            print(f"  {category}: {count}")

        print(f"\n国籍分布:")
        nationality_counts = df['nationality'].value_counts()
        for nationality, count in nationality_counts.head(10).items():
            print(f"  {nationality}: {count}")

        # 重複チェック
        duplicate_names = df[df.duplicated(subset=['person_name'], keep=False)]
        print(f"\n重複チェック結果:")
        print(f"  person_name重複: {len(duplicate_names)} 件")

        if len(duplicate_names) > 0:
            print("  残り重複例:")
            for idx, row in duplicate_names.head(5).iterrows():
                print(f"    {row['person_id']}: {row['person_name']}")

        return latest_file
    else:
        print("⚠️ クリーンファイルが見つかりません")
        return None

def main():
    """メイン実行"""
    print("🚀 最終重複クリーンアップ開始")
    print("="*60)

    # 最終クリーンアップ実行
    output_file = execute_final_cleanup()

    # 品質検証
    verify_final_database()

    print(f"\n🎉 すべての重複処理完了！")
    print(f"📄 最終クリーンデータベース: {output_file}")

    return output_file

if __name__ == "__main__":
    main()
