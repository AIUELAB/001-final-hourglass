#!/usr/bin/env python3
"""
外国語名自動変換ルールシステム
芸名・アーティスト名は維持、それ以外は日本語に変換
"""

import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json


class ForeignNameConverter:
    """外国語名を日本語に変換するクラス（芸名は維持）"""
    
    def __init__(self):
        # 芸名として維持すべき職業カテゴリ
        self.artist_occupations = {
            '歌手', 'ミュージシャン', 'アーティスト', 'ラッパー', 'DJ',
            'タレント', 'YouTuber', '美容家', 'ダンサー', 
            'プロデューサー', 'ボーカリスト', 'ギタリスト', 'ベーシスト', 'ドラマー'
        }
        
        # 日本語変換すべき職業カテゴリ
        self.non_artist_occupations = {
            '大統領', '首相', '政治家', '研究者', 'イノベーター', 
            '実業家', '起業家', 'CEO', '作家', '学者', '教授',
            'アスリート', '選手', '監督', 'コーチ'
        }
        
        self.converted_count = 0
        self.conversion_log = []
        
    def is_foreign_name(self, name: str) -> bool:
        """名前が外国語かどうかを判定"""
        if not name or pd.isna(name):
            return False
        
        # 日本語文字（ひらがな、カタカナ、漢字）を含むかチェック
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
        has_japanese = bool(re.search(japanese_pattern, str(name)))
        
        # アルファベットを含むかチェック
        alphabet_pattern = r'[A-Za-z]'
        has_alphabet = bool(re.search(alphabet_pattern, str(name)))
        
        # 日本語がなく、アルファベットがある場合に外国語と判定
        return not has_japanese and has_alphabet
    
    def should_keep_foreign_name(self, occupation: str, nationality: str) -> bool:
        """外国語名を維持すべきか判定"""
        if pd.isna(occupation):
            return False
        
        occupation_str = str(occupation).lower()
        
        # アーティスト系の職業は外国語名を維持
        for artist_occ in self.artist_occupations:
            if artist_occ.lower() in occupation_str:
                return True
        
        # 日本人のアーティストは特に維持
        if nationality == '日本' and any(word in occupation_str for word in ['芸', 'アート', '音楽']):
            return True
        
        return False
    
    def convert_foreign_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """外国語名を日本語に変換"""
        print("\n=== 外国語名変換処理開始 ===")
        
        df = df.copy()
        self.converted_count = 0
        self.conversion_log = []
        
        # 外国語名を持つレコードを特定
        foreign_mask = df['person_name_display'].apply(self.is_foreign_name)
        foreign_df = df[foreign_mask]
        
        print(f"外国語person_name_display: {len(foreign_df)}件")
        
        # 各レコードを処理
        for idx in foreign_df.index:
            row = df.loc[idx]
            display_name = row['person_name_display']
            ja_name = row.get('person_name_ja', '')
            occupation = row.get('occupation', '')
            nationality = row.get('nationality', '')
            
            # 芸名として維持すべきか判定
            if self.should_keep_foreign_name(occupation, nationality):
                # 芸名は維持
                continue
            
            # 日本語名が利用可能か確認
            if ja_name and not pd.isna(ja_name) and str(ja_name).strip():
                # person_name_jaが日本語の場合、それを使用
                if not self.is_foreign_name(ja_name):
                    old_display = display_name
                    df.at[idx, 'person_name_display'] = ja_name
                    self.converted_count += 1
                    self.conversion_log.append({
                        'index': idx,
                        'old': old_display,
                        'new': ja_name,
                        'occupation': occupation,
                        'nationality': nationality,
                        'reason': 'person_name_jaから取得'
                    })
        
        print(f"\n変換完了:")
        print(f"  変換対象: {len(foreign_df)}件")
        print(f"  芸名維持: {len(foreign_df) - self.converted_count}件")
        print(f"  日本語変換: {self.converted_count}件")
        
        # 変換例を表示
        if self.conversion_log:
            print("\n変換例（最初の10件）:")
            for i, log in enumerate(self.conversion_log[:10]):
                print(f"  {i+1}. {log['old']:30} → {log['new']:20} ({log['nationality']}, {log['occupation']})")
        
        return df
    
    def analyze_conversion_targets(self, df: pd.DataFrame) -> Dict:
        """変換対象の分析"""
        foreign_mask = df['person_name_display'].apply(self.is_foreign_name)
        foreign_df = df[foreign_mask]
        
        stats = {
            'total_foreign': len(foreign_df),
            'artists_to_keep': 0,
            'non_artists_to_convert': 0,
            'by_occupation': {},
            'by_nationality': {}
        }
        
        for idx, row in foreign_df.iterrows():
            occupation = row.get('occupation', '')
            nationality = row.get('nationality', '')
            
            if self.should_keep_foreign_name(occupation, nationality):
                stats['artists_to_keep'] += 1
            else:
                stats['non_artists_to_convert'] += 1
            
            # 職業別統計
            if occupation:
                if occupation not in stats['by_occupation']:
                    stats['by_occupation'][occupation] = {'keep': 0, 'convert': 0}
                if self.should_keep_foreign_name(occupation, nationality):
                    stats['by_occupation'][occupation]['keep'] += 1
                else:
                    stats['by_occupation'][occupation]['convert'] += 1
        
        return stats
    
    def save_conversion_log(self, filename: str = None):
        """変換ログを保存"""
        if not self.conversion_log:
            print("変換ログがありません。")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filename is None:
            filename = f"foreign_name_conversions_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'total_converted': self.converted_count,
                'conversions': self.conversion_log
            }, f, ensure_ascii=False, indent=2)
        
        print(f"変換ログを保存: {filename}")


def main():
    """メイン処理"""
    print("=== 外国語名変換ルール実行 ===\n")
    
    # クリーンなCSVファイル読み込み
    csv_file = "ultra_think_CLEANED_20250827_223821.csv"
    print(f"読み込み中: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
        print(f"読み込み完了: {len(df)}行\n")
    except Exception as e:
        print(f"エラー: CSVファイルの読み込みに失敗しました: {e}")
        return
    
    # 変換器を初期化
    converter = ForeignNameConverter()
    
    # 分析
    print("変換対象の分析中...")
    stats = converter.analyze_conversion_targets(df)
    
    print(f"\n分析結果:")
    print(f"  外国語名合計: {stats['total_foreign']}件")
    print(f"  芸名として維持: {stats['artists_to_keep']}件")
    print(f"  日本語に変換: {stats['non_artists_to_convert']}件")
    
    # 職業別の詳細（上位5件）
    if stats['by_occupation']:
        print("\n職業別（変換対象が多い順）:")
        sorted_occs = sorted(stats['by_occupation'].items(), 
                           key=lambda x: x[1]['convert'], reverse=True)
        for occ, counts in sorted_occs[:5]:
            print(f"  {occ}: 変換{counts['convert']}件, 維持{counts['keep']}件")
    
    # 変換処理実行
    df_converted = converter.convert_foreign_names(df)
    
    if converter.converted_count > 0:
        # 変換ログを保存
        converter.save_conversion_log()
        
        # 変換後のデータを新しいCSVに保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_CONVERTED_{timestamp}.csv"
        df_converted.to_csv(output_file, index=False)
        print(f"\n変換後のデータを保存: {output_file}")
        
        # 統計レポート
        print("\n=== 変換統計レポート ===")
        print(f"総外国語名: {stats['total_foreign']}件")
        print(f"日本語変換: {converter.converted_count}件")
        print(f"芸名維持: {stats['artists_to_keep']}件")
        print(f"変換率: {converter.converted_count/stats['total_foreign']*100:.1f}%")
    else:
        print("\n変換対象が見つかりませんでした。")
    
    return df_converted


if __name__ == "__main__":
    main()