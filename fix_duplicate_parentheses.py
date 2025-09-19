#!/usr/bin/env python3
"""
重複した括弧を修正するスクリプト

問題の分析:
1. コード構造の理解:
   - person_name_displayフィールドに「名前 (グループ名) (グループ名)」のように
     同じグループ名が重複して括弧で追加されている
   
2. 各関数の動作検証:
   - 括弧内の内容を抽出して重複を検出
   - 重複がある場合は1つに統合
   
3. 潜在的なバグやエッジケース:
   - 異なるグループ名が括弧に入っている場合は保持
   - 括弧が3つ以上ある場合も対応
   - 括弧内が空の場合の処理
   - 全角・半角括弧の混在
   
4. 改善案:
   - 正規表現を使った柔軟な検出
   - 括弧内容の正規化（全角/半角統一）
   - バックアップ作成
   - 詳細なログ出力
"""

import pandas as pd
import re
from datetime import datetime
from typing import List, Tuple
import json

class DuplicateParenthesesFixer:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)
        self.fixed_records = []
        self.error_records = []
        
    def extract_parentheses_content(self, text: str) -> List[str]:
        """括弧内の内容を抽出（全角・半角両対応）"""
        if pd.isna(text):
            return []
        
        # 全角括弧と半角括弧の両方に対応
        pattern = r'[（\(]([^）\)]+)[）\)]'
        matches = re.findall(pattern, str(text))
        return matches
    
    def normalize_parentheses(self, text: str) -> str:
        """括弧を半角に統一"""
        if pd.isna(text):
            return text
        text = str(text).replace('（', '(').replace('）', ')')
        return text
    
    def remove_duplicate_parentheses(self, text: str) -> Tuple[str, bool]:
        """重複した括弧を削除"""
        if pd.isna(text):
            return text, False
        
        original_text = str(text)
        text = self.normalize_parentheses(original_text)
        
        # 括弧内容を抽出
        contents = self.extract_parentheses_content(text)
        
        if len(contents) <= 1:
            # 重複なし
            return original_text, False
        
        # 重複を検出して削除
        seen = []
        result_parts = []
        last_end = 0
        
        # すべての括弧の位置を取得
        pattern = r'[（\(][^）\)]+[）\)]'
        for match in re.finditer(pattern, text):
            content = self.extract_parentheses_content(match.group())[0]
            
            # 括弧前のテキストを追加
            result_parts.append(text[last_end:match.start()])
            
            # 重複していない場合のみ括弧を追加
            if content not in seen:
                result_parts.append(f'({content})')
                seen.append(content)
            
            last_end = match.end()
        
        # 残りのテキストを追加
        result_parts.append(text[last_end:])
        
        # 結果を結合
        fixed_text = ''.join(result_parts).strip()
        
        # 余分なスペースを削除
        fixed_text = re.sub(r'\s+', ' ', fixed_text)
        fixed_text = re.sub(r'\s+\(', ' (', fixed_text)
        
        return fixed_text, fixed_text != original_text
    
    def fix_all_records(self):
        """すべてのレコードを修正"""
        print("=" * 60)
        print("重複括弧修正処理を開始")
        print("=" * 60)
        
        total_fixed = 0
        
        for idx, row in self.df.iterrows():
            person_id = row['person_id']
            original_display = row['person_name_display']
            
            # 修正実行
            fixed_display, was_fixed = self.remove_duplicate_parentheses(original_display)
            
            if was_fixed:
                # データフレームを更新
                self.df.at[idx, 'person_name_display'] = fixed_display
                
                # ログ記録
                self.fixed_records.append({
                    'person_id': person_id,
                    'original': original_display,
                    'fixed': fixed_display
                })
                
                total_fixed += 1
                print(f"修正: {person_id}")
                print(f"  前: {original_display}")
                print(f"  後: {fixed_display}")
                print()
        
        return total_fixed
    
    def validate_fixes(self):
        """修正の妥当性を検証"""
        print("\n" + "=" * 60)
        print("修正の検証")
        print("=" * 60)
        
        issues = []
        
        for record in self.fixed_records:
            fixed = record['fixed']
            
            # 検証1: 括弧の数が適切か
            open_count = fixed.count('(') + fixed.count('（')
            close_count = fixed.count(')') + fixed.count('）')
            
            if open_count != close_count:
                issues.append({
                    'person_id': record['person_id'],
                    'issue': '括弧の数が不一致',
                    'text': fixed
                })
            
            # 検証2: 空の括弧がないか
            if '()' in fixed or '（）' in fixed:
                issues.append({
                    'person_id': record['person_id'],
                    'issue': '空の括弧',
                    'text': fixed
                })
            
            # 検証3: 必要な情報が失われていないか
            original_parts = record['original'].replace('(', ' ').replace(')', ' ').split()
            fixed_parts = fixed.replace('(', ' ').replace(')', ' ').split()
            
            # 重複を除いた単語セットで比較
            original_words = set(original_parts)
            fixed_words = set(fixed_parts)
            
            lost_words = original_words - fixed_words
            if lost_words:
                # 同じ単語の重複は問題ない
                real_lost = [w for w in lost_words if original_parts.count(w) == 1]
                if real_lost:
                    issues.append({
                        'person_id': record['person_id'],
                        'issue': f'情報の喪失: {real_lost}',
                        'text': fixed
                    })
        
        if issues:
            print("⚠️ 検証で問題が見つかりました:")
            for issue in issues:
                print(f"  {issue['person_id']}: {issue['issue']}")
                print(f"    テキスト: {issue['text']}")
        else:
            print("✅ すべての修正が検証を通過しました")
        
        return issues
    
    def save_results(self):
        """結果を保存"""
        # バックアップ作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_{self.csv_file}_{timestamp}'
        df_original = pd.read_csv(self.csv_file)
        df_original.to_csv(backup_file, index=False, encoding='utf-8-sig')
        print(f"\n📁 バックアップ作成: {backup_file}")
        
        # 修正済みデータを保存
        self.df.to_csv(self.csv_file, index=False, encoding='utf-8-sig')
        print(f"📁 修正済みデータ保存: {self.csv_file}")
        
        # 修正ログを保存
        if self.fixed_records:
            log_file = f'fix_duplicate_parentheses_log_{timestamp}.json'
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'total_fixed': len(self.fixed_records),
                    'records': self.fixed_records
                }, f, ensure_ascii=False, indent=2)
            print(f"📁 修正ログ保存: {log_file}")
    
    def generate_report(self):
        """レポート生成"""
        print("\n" + "=" * 60)
        print("修正レポート")
        print("=" * 60)
        print(f"総レコード数: {len(self.df)}")
        print(f"修正されたレコード数: {len(self.fixed_records)}")
        
        if self.fixed_records:
            print("\n修正されたレコード一覧:")
            for i, record in enumerate(self.fixed_records[:10], 1):
                print(f"{i}. {record['person_id']}")
                print(f"   前: {record['original']}")
                print(f"   後: {record['fixed']}")
            
            if len(self.fixed_records) > 10:
                print(f"   ... 他 {len(self.fixed_records) - 10} 件")

def main():
    """メイン処理"""
    csv_file = 'database_final_enriched_20250910_132247.csv'
    
    # 修正処理実行
    fixer = DuplicateParenthesesFixer(csv_file)
    
    # 修正実行
    total_fixed = fixer.fix_all_records()
    
    if total_fixed > 0:
        # 検証
        issues = fixer.validate_fixes()
        
        # 結果保存
        fixer.save_results()
        
        # レポート生成
        fixer.generate_report()
        
        # PDCAガーディアン用のルール提案
        print("\n" + "=" * 60)
        print("PDCAガーディアンシステムへの追加ルール提案")
        print("=" * 60)
        print("""
以下のルールをPDCAガーディアンシステムに追加することを推奨:

1. **括弧重複防止ルール**
   - person_name_displayフィールドで同じ内容の括弧が重複しないこと
   - 正規表現パターン: /\(([^)]+)\).*\(\1\)/ でチェック

2. **括弧正規化ルール**
   - 全角括弧（）と半角括弧()を統一すること
   - 推奨: 半角括弧()に統一

3. **グループ名追加時の重複チェック**
   - グループ名を括弧で追加する際、既存の括弧内容と重複しないこと
   - 追加前に既存の括弧内容を抽出して確認

4. **データ更新時の検証**
   - CSVファイル更新時に自動で重複括弧チェックを実行
   - 問題が検出されたら警告を出力

5. **バックアップルール**
   - データ修正前に必ずバックアップを作成
   - タイムスタンプ付きでバックアップファイルを保存
""")
    else:
        print("\n✅ 重複括弧は見つかりませんでした")

if __name__ == "__main__":
    main()