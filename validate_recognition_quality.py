#!/usr/bin/env python3
"""
知名度評価結果の品質検証スクリプト
PDCAガーディアンと連携して品質チェックを実行
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys

def validate_recognition_quality(csv_file):
    """
    知名度評価結果の品質を検証
    """
    print("="*60)
    print("🔍 知名度評価結果 品質検証")
    print("="*60)
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    print(f"📂 検証対象: {csv_file}")
    print(f"📊 レコード数: {len(df)}")
    
    # 基本統計
    print("\n📈 スコア統計:")
    print(f"  平均: {df['final_score'].mean():.2f}")
    print(f"  中央値: {df['final_score'].median():.2f}")
    print(f"  標準偏差: {df['final_score'].std():.2f}")
    print(f"  最小値: {df['final_score'].min():.2f}")
    print(f"  最大値: {df['final_score'].max():.2f}")
    
    # 分布チェック
    print("\n📊 スコア分布:")
    bins = [0, 2, 4, 6, 8, 10]
    hist = pd.cut(df['final_score'], bins=bins).value_counts().sort_index()
    for interval, count in hist.items():
        percentage = (count / len(df)) * 100
        print(f"  {interval}: {count}件 ({percentage:.1f}%)")
    
    # 評価方法の内訳
    print("\n🔧 評価方法別:")
    method_counts = df['method'].value_counts()
    for method, count in method_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {method}: {count}件 ({percentage:.1f}%)")
    
    # 品質チェック項目
    print("\n✅ 品質チェック:")
    
    issues = []
    
    # 1. NULL値チェック
    null_count = df['final_score'].isna().sum()
    if null_count > 0:
        issues.append(f"❌ NULL値が{null_count}件存在")
    else:
        print("  ✅ NULL値なし")
    
    # 2. 範囲チェック
    out_of_range = ((df['final_score'] < 0) | (df['final_score'] > 10)).sum()
    if out_of_range > 0:
        issues.append(f"❌ 範囲外スコアが{out_of_range}件")
    else:
        print("  ✅ 全スコアが0-10の範囲内")
    
    # 3. 有名人チェック
    famous_people = ['HIKAKIN', '大谷翔平', '嵐', '新垣結衣', '米津玄師']
    print("\n🏆 有名人スコア検証:")
    for name in famous_people:
        person = df[df['person_name'] == name]
        if not person.empty:
            score = person.iloc[0]['final_score']
            method = person.iloc[0]['method']
            if score >= 7.0:
                print(f"  ✅ {name}: {score:.2f} ({method})")
            else:
                issues.append(f"❌ {name}のスコアが低すぎる: {score:.2f}")
        else:
            print(f"  ⚠️ {name}: データなし")
    
    # 4. 架空キャラクター保護チェック
    fictional_chars = ['ドラえもん', '孫悟空', 'ピカチュウ', 'ルフィ']
    print("\n🎭 架空キャラクター保護確認:")
    for char in fictional_chars:
        # 部分一致で検索
        char_data = df[df['person_name'].str.contains(char, na=False)]
        if not char_data.empty:
            for _, row in char_data.iterrows():
                score = row['final_score']
                name = row['person_name']
                if score >= 5.0:  # 架空キャラクターとして適切な範囲
                    print(f"  ✅ {name}: {score:.2f} (保護済み)")
                else:
                    print(f"  ⚠️ {name}: {score:.2f}")
    
    # 5. 異常値検出
    print("\n🔍 異常値検出:")
    # スコア0の件数
    zero_scores = (df['final_score'] == 0).sum()
    if zero_scores > 10:
        issues.append(f"⚠️ スコア0が{zero_scores}件")
    
    # スコア10の件数
    perfect_scores = (df['final_score'] == 10).sum()
    if perfect_scores > 50:
        issues.append(f"⚠️ スコア10が{perfect_scores}件")
    
    # 最終結果
    print("\n" + "="*60)
    if issues:
        print("❌ 品質問題が検出されました:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ 品質検証合格")
        print("すべての品質基準を満たしています")
        return True

if __name__ == "__main__":
    # 最新の評価結果ファイルを検証
    import glob
    
    csv_files = sorted(glob.glob("recognition_evaluation_*.csv"))
    if csv_files:
        latest_file = csv_files[-1]
        success = validate_recognition_quality(latest_file)
        
        # PDCAガーディアンへの結果報告
        if success:
            print("\n🎯 PDCAガーディアン: 品質ゲート通過")
            sys.exit(0)
        else:
            print("\n⚠️ PDCAガーディアン: 品質問題を検出")
            sys.exit(1)
    else:
        print("評価結果ファイルが見つかりません")
        sys.exit(1)