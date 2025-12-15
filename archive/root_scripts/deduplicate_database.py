#!/usr/bin/env python3
"""
データベース重複除去スクリプト
1人1エピソードに整理 - 品質スコア最高値を保持
"""

import pandas as pd
from datetime import datetime
import sys

def deduplicate_database(input_file: str, output_file: str) -> dict:
    """
    データベースから重複人物を除去し、最高品質スコアのエピソードのみを保持

    Args:
        input_file: 入力CSVファイル
        output_file: 出力CSVファイル

    Returns:
        処理結果の統計情報
    """
    # データ読み込み
    df = pd.read_csv(input_file)

    print(f"📊 元のデータベース: {len(df)}件")
    print(f"ユニーク人物数: {df['人物名'].nunique()}件")

    # 重複チェック
    duplicates = df.groupby('人物名').size()
    duplicates_count = len(duplicates[duplicates > 1])
    print(f"重複人物数: {duplicates_count}件")

    # 重複詳細を記録
    duplicate_details = []
    for name in df[df.duplicated(subset=['人物名'], keep=False)]['人物名'].unique():
        person_data = df[df['人物名'] == name].sort_values('品質スコア', ascending=False)
        duplicate_details.append({
            '人物名': name,
            '重複数': len(person_data),
            '保持エピソード': person_data.iloc[0]['人物ID'],
            '保持品質スコア': person_data.iloc[0]['品質スコア'],
            '削除エピソード': ', '.join(person_data.iloc[1:]['人物ID'].tolist()),
            '削除品質スコア': ', '.join(map(str, person_data.iloc[1:]['品質スコア'].tolist()))
        })

    # 品質スコアが最高のエピソードのみを保持
    # 同点の場合は人物IDが小さい方（先に作成された方）を優先
    df_deduped = df.sort_values(['人物名', '品質スコア', '人物ID'],
                                ascending=[True, False, True])
    df_deduped = df_deduped.drop_duplicates(subset=['人物名'], keep='first')

    # 人物IDでソート
    df_deduped = df_deduped.sort_values('人物ID')

    # UTF-8 BOMで出力（Excel対応）
    df_deduped.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n✅ 整理後のデータベース: {len(df_deduped)}件")
    print(f"削除されたエピソード数: {len(df) - len(df_deduped)}件")

    # 統計情報
    stats = {
        '元の件数': len(df),
        '整理後件数': len(df_deduped),
        '削除件数': len(df) - len(df_deduped),
        '重複人物数': duplicates_count,
        'ユニーク人物数': df['人物名'].nunique(),
        '重複詳細': duplicate_details
    }

    return stats, df_deduped

def print_duplicate_report(stats: dict):
    """重複除去レポートを出力"""
    print("\n" + "="*70)
    print("📋 重複除去レポート")
    print("="*70)
    print(f"元のエピソード数: {stats['元の件数']}件")
    print(f"整理後エピソード数: {stats['整理後件数']}件")
    print(f"削除されたエピソード数: {stats['削除件数']}件")
    print(f"重複していた人物数: {stats['重複人物数']}件")
    print(f"最終的なユニーク人物数: {stats['ユニーク人物数']}件")

    if stats['重複詳細']:
        print(f"\n重複人物の詳細:")
        for detail in stats['重複詳細']:
            print(f"\n  👤 {detail['人物名']} ({detail['重複数']}件)")
            print(f"     ✅ 保持: {detail['保持エピソード']} (品質スコア: {detail['保持品質スコア']})")
            print(f"     ❌ 削除: {detail['削除エピソード']} (品質スコア: {detail['削除品質スコア']})")

    print("="*70)

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_file = "final_hourglass_week1_6_date_fixed_20251008_134015.csv"
    output_file = f"final_hourglass_unique_persons_{timestamp}.csv"

    print("🚀 データベース重複除去処理を開始します")
    print(f"入力ファイル: {input_file}")
    print(f"出力ファイル: {output_file}\n")

    try:
        stats, df_deduped = deduplicate_database(input_file, output_file)
        print_duplicate_report(stats)

        print(f"\n✅ 処理完了!")
        print(f"整理済みデータベース: {output_file}")

        # カテゴリ別統計
        print(f"\n📊 カテゴリ別統計:")
        category_stats = df_deduped['カテゴリ'].value_counts()
        for category, count in category_stats.items():
            print(f"  {category}: {count}件")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
