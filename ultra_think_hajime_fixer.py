#!/usr/bin/env python3
"""
Ultra Think はじめしゃちょー修正システム
P000104を含む残存する日本語表記問題を修正
"""
import pandas as pd
import json
import re
from datetime import datetime
import shutil

class HajimeShachoFixer:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)
        self.fixes = []
        self.stats = {
            'total_youtubers': 0,
            'problems_found': 0,
            'fixed': 0,
            'hajime_fixed': False
        }
    
    def has_japanese(self, text):
        """日本語文字が含まれているか確認"""
        if pd.isna(text):
            return False
        return bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', str(text)))
    
    def identify_problems(self):
        """修正が必要なレコードを特定"""
        # 日本人YouTuberを抽出
        japanese_youtubers = self.df[(self.df['nationality'] == '日本') & (self.df['occupation'] == 'YouTuber')]
        self.stats['total_youtubers'] = len(japanese_youtubers)
        
        problems = []
        
        for idx, row in japanese_youtubers.iterrows():
            person_id = row['person_id']
            person_name_display = str(row['person_name_display'])
            person_name_ja = row['person_name_ja']
            
            # person_name_jaが存在し、日本語文字を含む
            if pd.notna(person_name_ja) and self.has_japanese(person_name_ja):
                # でもperson_name_displayが英語表記
                if not self.has_japanese(person_name_display):
                    # 英語の芸名として適切なものを除外
                    # （前回の修正システムで除外されたもの）
                    if person_name_display.upper() not in ['HIKAKIN', 'SEIKIN', 'DAIGO']:
                        problems.append({
                            'index': idx,
                            'person_id': person_id,
                            'current_display': person_name_display,
                            'correct_display': person_name_ja,
                            'person_name': row['person_name']
                        })
        
        self.stats['problems_found'] = len(problems)
        return problems
    
    def fix_display_names(self):
        """表示名を修正"""
        print("🔧 日本語表記を修正中...")
        
        problems = self.identify_problems()
        
        for problem in problems:
            idx = problem['index']
            person_id = problem['person_id']
            old_display = problem['current_display']
            new_display = problem['correct_display']
            
            # グループ名が含まれている場合は保持
            if '(' in old_display and ')' in old_display:
                # グループ名を抽出して追加
                group_match = re.search(r'\((.+?)\)', old_display)
                if group_match:
                    group_name = group_match.group(1)
                    # LUNA SEAなどの誤ったグループ名は除外
                    if group_name not in ['LUNA SEA', 'ONE OK ROCK']:
                        new_display = f"{new_display} ({group_name})"
            
            # 修正を適用
            self.df.loc[idx, 'person_name_display'] = new_display
            
            self.fixes.append({
                'person_id': person_id,
                'old_display': old_display,
                'new_display': new_display,
                'person_name': problem['person_name']
            })
            
            self.stats['fixed'] += 1
            
            # はじめしゃちょーの修正を確認
            if person_id == 'P000104':
                self.stats['hajime_fixed'] = True
    
    def save_results(self):
        """結果を保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 修正済みCSVを保存
        output_csv = f'ultra_think_HAJIME_FIXED_{timestamp}.csv'
        self.df.to_csv(output_csv, index=False, encoding='utf-8')
        
        # 修正ログを保存
        fix_log = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'fixes': self.fixes
        }
        
        with open(f'hajime_fix_log_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(fix_log, f, ensure_ascii=False, indent=2)
        
        return output_csv, fix_log
    
    def print_report(self):
        """レポートを表示"""
        print("\n" + "="*60)
        print("📊 はじめしゃちょー修正レポート")
        print("="*60)
        print(f"日本人YouTuber総数: {self.stats['total_youtubers']}")
        print(f"問題発見: {self.stats['problems_found']}件")
        print(f"修正済み: {self.stats['fixed']}件")
        
        if self.stats['hajime_fixed']:
            print("\n✅ P000104（はじめしゃちょー）の修正: 成功！")
        else:
            print("\n⚠️ P000104（はじめしゃちょー）の修正: 未実施")
        
        print("\n📝 修正内容:")
        for fix in self.fixes:
            status = "🌟" if fix['person_id'] == 'P000104' else "✅"
            print(f"{status} {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")

def main():
    print("🚀 Ultra Think はじめしゃちょー修正システム起動")
    print("="*60)
    
    # バックアップ作成
    backup_file = f"backup_before_hajime_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy('ultra_think_JAPANESE_DISPLAY_FIXED_20250828_192840.csv', backup_file)
    print(f"📁 バックアップ作成: {backup_file}")
    
    # 修正システムを実行
    fixer = HajimeShachoFixer('ultra_think_JAPANESE_DISPLAY_FIXED_20250828_192840.csv')
    
    # 問題を特定
    problems = fixer.identify_problems()
    print(f"\n🔍 問題発見: {len(problems)}件")
    
    if problems:
        print("\n問題のあるレコード:")
        for p in problems:
            highlight = " 🌟" if p['person_id'] == 'P000104' else ""
            print(f"  {p['person_id']}: {p['current_display']} → {p['correct_display']}{highlight}")
    
    # 修正を実行
    fixer.fix_display_names()
    
    # 結果を保存
    output_file, log = fixer.save_results()
    
    # レポートを表示
    fixer.print_report()
    
    print(f"\n📁 出力ファイル: {output_file}")
    
    # はじめしゃちょーの最終確認
    final_df = pd.read_csv(output_file)
    hajime = final_df[final_df['person_id'] == 'P000104']
    if not hajime.empty:
        display = hajime.iloc[0]['person_name_display']
        print(f"\n🎯 P000104の最終表示名: {display}")
        if display == 'はじめしゃちょー':
            print("   ✅ 正しく「はじめしゃちょー」に修正されました！")
    
    return output_file, fixer.stats

if __name__ == "__main__":
    output, stats = main()