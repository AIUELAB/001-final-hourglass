#!/usr/bin/env python3
"""
削除判定システムの修正スクリプト
Fix for deletion scoring system

問題点:
1. Web検索バリデーターがAPIを実装していない（常に0を返す）
2. これによりHIKAKINなど有名人が削除対象になってしまう

修正方法:
1. Web検索スコアのデフォルト値を適正化
2. ホワイトリスト機能を追加
3. YouTuberなど特定職業の特別扱い
"""

import pandas as pd
import json
from datetime import datetime
import os

def create_whitelist():
    """明らかに有名な人物のホワイトリストを作成"""
    whitelist = {
        # 日本のトップYouTuber
        'P000013': {'name': 'HIKAKIN', 'reason': '日本最大級YouTuber', 'min_score': 8.0},
        
        # 他の誤判定されやすい有名人も追加可能
    }
    
    # ホワイトリストをJSONファイルに保存
    with open('deletion_whitelist.json', 'w', encoding='utf-8') as f:
        json.dump(whitelist, f, ensure_ascii=False, indent=2)
    
    return whitelist

def fix_web_search_scores(csv_file):
    """Web検索スコアを修正（暫定的な対処）"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file, encoding='utf-8')
    
    # Web検索スコアが異常に低い（0.2）レコードを修正
    # person_nameにYouTuber関連の名前が含まれる場合は修正
    
    # HIKAKINなど特定の人物を識別
    youtuber_names = ['HIKAKIN', 'はじめしゃちょー', 'Fischer\'s', 'フィッシャーズ']
    is_youtuber = df['person_name'].isin(youtuber_names)
    
    # Web検索スコアが低すぎる有名YouTuberを修正
    if 'web_search_score' in df.columns:
        df.loc[is_youtuber & (df['web_search_score'] < 5.0), 'web_search_score'] = 7.0
    
    # 統合スコアを再計算（重み: Wikipedia 40%, Web検索 30%, メタデータ 30%）
    if all(col in df.columns for col in ['wikipedia_score', 'web_search_score', 'metadata_quality_score']):
        df['integrated_score_fixed'] = (
            df['wikipedia_score'] * 0.4 +
            df['web_search_score'] * 0.3 +
            df['metadata_quality_score'] * 0.3
        )
        
        # 推奨アクションを再判定
        def get_recommendation(score):
            if score < 2.0:
                return 'DELETE_HIGH_CONFIDENCE'
            elif score < 4.0:
                return 'DELETE_MEDIUM_CONFIDENCE'
            elif score < 6.0:
                return 'REVIEW_REQUIRED'
            else:
                return 'KEEP'
        
        df['recommendation_fixed'] = df['integrated_score_fixed'].apply(get_recommendation)
    
    return df

def apply_whitelist(df, whitelist):
    """ホワイトリストを適用"""
    
    for person_id, info in whitelist.items():
        if person_id in df['person_id'].values:
            idx = df[df['person_id'] == person_id].index[0]
            
            # 最低スコアを保証
            if 'integrated_score_fixed' in df.columns:
                current_score = df.loc[idx, 'integrated_score_fixed']
                if current_score < info['min_score']:
                    df.loc[idx, 'integrated_score_fixed'] = info['min_score']
                    df.loc[idx, 'recommendation_fixed'] = 'KEEP'
                    print(f"✅ {info['name']}: スコアを{current_score:.2f}から{info['min_score']:.2f}に修正")
    
    return df

def analyze_hikakin(df):
    """HIKAKINの詳細分析"""
    hikakin_data = df[df['person_id'] == 'P000013']
    
    if not hikakin_data.empty:
        print("\n=== HIKAKIN (P000013) の分析結果 ===")
        row = hikakin_data.iloc[0]
        
        print(f"名前: {row.get('person_name_display', 'N/A')}")
        print(f"person_name: {row.get('person_name', 'N/A')}")
        
        print("\n【現在のスコア】")
        print(f"  Wikipedia スコア: {row.get('wikipedia_score', 'N/A')}")
        print(f"  Web検索スコア: {row.get('web_search_score', 'N/A')} ⚠️ 問題あり")
        print(f"  メタデータ品質: {row.get('metadata_quality_score', 'N/A')}")
        print(f"  統合スコア: {row.get('integrated_score', 'N/A')}")
        print(f"  推奨: {row.get('recommendation', 'N/A')}")
        
        if 'integrated_score_fixed' in df.columns:
            print("\n【修正後のスコア】")
            print(f"  Web検索スコア（修正）: {row.get('web_search_score', 'N/A')}")
            print(f"  統合スコア（修正）: {row.get('integrated_score_fixed', 'N/A')}")
            print(f"  推奨（修正）: {row.get('recommendation_fixed', 'N/A')}")

def main():
    """メイン処理"""
    
    print("=== 削除判定システムの修正 ===\n")
    
    # 1. ホワイトリストを作成
    print("1. ホワイトリストを作成...")
    whitelist = create_whitelist()
    print(f"   {len(whitelist)}件の人物をホワイトリストに追加")
    
    # 2. 削除候補ファイルを修正
    input_file = 'deletion_results/delete_candidates_20250902_060313.csv'
    
    if os.path.exists(input_file):
        print(f"\n2. {input_file}を修正...")
        
        # Web検索スコアを修正
        df = fix_web_search_scores(input_file)
        
        # ホワイトリストを適用
        df = apply_whitelist(df, whitelist)
        
        # HIKAKINの詳細分析
        analyze_hikakin(df)
        
        # 修正版を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'delete_candidates_fixed_{timestamp}.csv'
        
        # UTF-8 BOM付きで保存（Excel対応）
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)
        
        print(f"\n✅ 修正完了: {output_file}")
        
        # 修正前後の統計
        if 'recommendation_fixed' in df.columns:
            print("\n=== 修正前後の比較 ===")
            print("修正前:")
            print(df['recommendation'].value_counts())
            print("\n修正後:")
            print(df['recommendation_fixed'].value_counts())
    else:
        print(f"⚠️ ファイルが見つかりません: {input_file}")

if __name__ == "__main__":
    main()