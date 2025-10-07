#!/usr/bin/env python3
"""
Phase 10-3: CSV最終整形

不要カラムの削除、カラム順序の最適化、最終出力形式の確定

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
from datetime import datetime


class Phase10CSVFinalizer:
    """
    CSV最終整形システム
    """

    # 最終出力カラム（順序最適化済み）
    FINAL_COLUMNS = [
        # 基本情報
        '人物ID',
        '人物名',
        '年齢',
        'カテゴリ',

        # エピソード
        'エピソード本文',
        '文字数',

        # 品質評価
        '記憶性スコア',
        '共感性スコア',
        '意外性スコア',
        '品質スコア',

        # ステータス
        'ステータス',
        '削除理由'
    ]

    def __init__(self):
        pass

    def finalize_csv(self, input_csv: str):
        """
        CSVの最終整形

        Args:
            input_csv: 入力CSVパス
        """
        print(f"\n{'='*60}")
        print(f"Phase 10-3: CSV最終整形")
        print(f"{'='*60}")

        # CSV読み込み
        df = pd.read_csv(input_csv, encoding='utf-8-sig')
        print(f"\n入力CSV: {input_csv}")
        print(f"総レコード数: {len(df)}件")
        print(f"入力カラム数: {len(df.columns)}列")

        # 必要カラムのみ抽出
        df_final = df[self.FINAL_COLUMNS].copy()

        # データ型最適化
        df_final['年齢'] = df_final['年齢'].astype(int)
        df_final['文字数'] = df_final['文字数'].astype(int)

        # スコアを小数点第1位で丸める
        score_columns = [
            '記憶性スコア', '共感性スコア', '意外性スコア', '品質スコア'
        ]
        for col in score_columns:
            df_final[col] = df_final[col].round(1)

        # 統計情報
        qualified = df_final[df_final['ステータス'] == '合格']
        deleted = df_final[df_final['ステータス'] == '削除済み']

        print(f"\n{'='*60}")
        print(f"最終統計")
        print(f"{'='*60}")
        print(f"合格レコード: {len(qualified)}件")
        print(f"削除済みレコード: {len(deleted)}件")
        print(f"合格率: {len(qualified) / len(df_final) * 100:.1f}%")

        # カテゴリ別集計
        print(f"\n【カテゴリ別合格数】")
        category_stats = qualified['カテゴリ'].value_counts()
        for category, count in category_stats.items():
            print(f"{category}: {count}件")

        # 文字数範囲チェック
        char_counts = qualified['文字数']
        print(f"\n【文字数統計（合格レコードのみ）】")
        print(f"最小: {char_counts.min()}文字")
        print(f"最大: {char_counts.max()}文字")
        print(f"平均: {char_counts.mean():.1f}文字")
        print(f"180-280範囲内: {len(char_counts[(char_counts >= 180) & (char_counts <= 280)])}件")

        # スコア統計
        print(f"\n【スコア統計（合格レコードのみ）】")
        print(f"品質スコア平均: {qualified['品質スコア'].mean():.1f}")
        print(f"記憶性スコア平均: {qualified['記憶性スコア'].mean():.1f}")
        print(f"共感性スコア平均: {qualified['共感性スコア'].mean():.1f}")
        print(f"意外性スコア平均: {qualified['意外性スコア'].mean():.1f}")

        # 最終CSV保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv = f"final_hourglass_week1_6_complete_{timestamp}.csv"
        df_final.to_csv(output_csv, index=False, encoding='utf-8-sig')

        print(f"\n{'='*60}")
        print(f"Phase 10-3完了")
        print(f"{'='*60}")
        print(f"出力CSV: {output_csv}")
        print(f"出力カラム数: {len(df_final.columns)}列")
        print(f"削減カラム数: {len(df.columns) - len(df_final.columns)}列")
        print(f"{'='*60}\n")

        return output_csv


def main():
    """メイン処理"""
    input_csv = "final_hourglass_master_v10_phase10_2_fixed_20251008_072327.csv"

    finalizer = Phase10CSVFinalizer()
    output_csv = finalizer.finalize_csv(input_csv)

    print(f"✅ Week 1-6データベース完成: {output_csv}\n")


if __name__ == "__main__":
    main()
