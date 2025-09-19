#!/usr/bin/env python3
"""
プレースホルダー自動削除ルールシステム
_数字パターンを持つテストデータエントリーを検出して削除
"""

import re
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
import json


class PlaceholderRemover:
    """プレースホルダーエントリーを検出して削除するクラス"""
    
    def __init__(self):
        self.placeholder_pattern = re.compile(r'_\d+$')
        self.removed_entries = []
        
    def detect_placeholders(self, df: pd.DataFrame) -> pd.DataFrame:
        """プレースホルダーを検出"""
        if 'person_name' not in df.columns:
            print("Warning: person_name column not found")
            return pd.DataFrame()
            
        # _数字パターンを持つエントリーを検出
        mask = df['person_name'].astype(str).str.contains(self.placeholder_pattern, na=False)
        placeholders = df[mask].copy()
        
        print(f"検出されたプレースホルダー: {len(placeholders)}件")
        
        # 統計情報を表示
        if len(placeholders) > 0:
            print("\n職業別分布:")
            if 'occupation' in placeholders.columns:
                occupation_counts = placeholders['occupation'].value_counts()
                for occupation, count in occupation_counts.head(10).items():
                    print(f"  {occupation}: {count}件")
        
        return placeholders
    
    def remove_placeholders(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """プレースホルダーを削除"""
        print("\n=== プレースホルダー削除処理開始 ===")
        
        # プレースホルダーを検出
        placeholders = self.detect_placeholders(df)
        
        if len(placeholders) == 0:
            print("削除対象のプレースホルダーが見つかりませんでした。")
            return df, []
        
        # 削除前の記録を保存
        self.removed_entries = placeholders.to_dict('records')
        
        # 削除対象のインデックスを取得
        indices_to_remove = placeholders.index
        
        # データフレームから削除
        df_cleaned = df.drop(indices_to_remove).reset_index(drop=True)
        
        print(f"\n削除完了:")
        print(f"  削除前: {len(df)}行")
        print(f"  削除後: {len(df_cleaned)}行")
        print(f"  削除数: {len(placeholders)}行")
        
        # 削除されたエントリーのサンプルを表示
        print("\n削除されたエントリーの例（最初の5件）:")
        for i, entry in enumerate(self.removed_entries[:5]):
            print(f"  {i+1}. {entry.get('person_name', 'N/A')} - {entry.get('occupation', 'N/A')}")
        
        return df_cleaned, self.removed_entries
    
    def save_removed_entries(self, filename: str = None):
        """削除されたエントリーをファイルに保存"""
        if not self.removed_entries:
            print("削除されたエントリーがありません。")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filename is None:
            filename = f"removed_placeholders_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'count': len(self.removed_entries),
                'entries': self.removed_entries
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n削除記録を保存: {filename}")
    
    def verify_no_real_persons(self, placeholders: pd.DataFrame) -> bool:
        """実在の人物が含まれていないことを確認（簡易チェック）"""
        # ここでWikipedia APIを使用して実在確認することも可能
        # 今回は_数字パターンなので、明らかにテストデータと判断
        
        if len(placeholders) == 0:
            return True
        
        # パターンチェック: すべてが_数字で終わっているか確認
        all_match = placeholders['person_name'].str.contains(self.placeholder_pattern, na=False).all()
        
        if not all_match:
            print("警告: _数字パターンでないエントリーが含まれています")
            return False
        
        # 職業の分布をチェック（医師、教師、エンジニアが多い場合はテストデータの可能性高）
        if 'occupation' in placeholders.columns:
            top_occupations = placeholders['occupation'].value_counts().head(3)
            test_occupations = ['医師', '教師', 'エンジニア']
            if any(occ in test_occupations for occ in top_occupations.index):
                print("テストデータパターンを確認（医師/教師/エンジニアが多数）")
        
        return True


def main():
    """メイン処理"""
    print("=== プレースホルダー削除ルール実行 ===\n")
    
    # CSVファイル読み込み
    csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
    print(f"読み込み中: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
        print(f"読み込み完了: {len(df)}行\n")
    except Exception as e:
        print(f"エラー: CSVファイルの読み込みに失敗しました: {e}")
        return
    
    # プレースホルダー削除
    remover = PlaceholderRemover()
    
    # 削除処理実行
    df_cleaned, removed_entries = remover.remove_placeholders(df)
    
    if removed_entries:
        # 削除記録を保存
        remover.save_removed_entries()
        
        # クリーンなデータを新しいCSVに保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_CLEANED_{timestamp}.csv"
        df_cleaned.to_csv(output_file, index=False)
        print(f"\nクリーンなデータを保存: {output_file}")
        
        # 統計レポート
        print("\n=== 削除統計レポート ===")
        print(f"総削除数: {len(removed_entries)}件")
        print(f"残存データ: {len(df_cleaned)}件")
        print(f"削除率: {len(removed_entries)/len(df)*100:.1f}%")
    else:
        print("\n削除対象が見つかりませんでした。")
    
    return df_cleaned


if __name__ == "__main__":
    main()