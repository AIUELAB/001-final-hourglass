#!/usr/bin/env python3
"""
データベースのルール違反を修正
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Any
import io


class RuleViolationFixer:
    """ルール違反を修正"""
    
    def __init__(self):
        # 敬称パターン
        self.honorifics = ['さん', 'くん', 'ちゃん', '様', '殿', '氏', '先生', '博士']
        
        # 標準カテゴリマッピング
        self.category_mapping = {
            'エンターテイメント': 'エンタメ',
            '歴史的偉人': '歴史上の人物',
            '歴史': '歴史上の人物',
            '一般': 'その他',
            'メディア': 'エンタメ',
            '芸術': '文化・芸術',
            '文化': '文化・芸術',
            '音楽': '文化・芸術',
            '文化・学術': '学術・科学',
        }
        
        # 有効なカテゴリ
        self.valid_categories = [
            'エンタメ', 'スポーツ', '学術・科学', 'ビジネス', '文化・芸術',
            '歴史上の人物', '政治', 'テクノロジー', 'インフルエンサー',
            '社会活動家', '現代のイノベーター', '架空の存在', '動物',
            '政治・経済', '科学', '国際', 'その他'
        ]
        
        # 教科書必修人物（知名度90以上にすべき）
        self.textbook_figures = [
            '織田信長', '豊臣秀吉', '徳川家康', '源頼朝', '足利尊氏',
            '武田信玄', '上杉謙信', '聖徳太子', '坂本龍馬', '西郷隆盛'
        ]
        
        self.fixed_count = {
            'honorifics': 0,
            'missing_display': 0,
            'categories': 0,
            'recognition': 0,
            'total': 0
        }
    
    def fix_database(self, input_file: str, output_file: str):
        """データベースを修正"""
        
        print("🔧 ルール違反修正開始...")
        print(f"  入力: {input_file}")
        
        # ファイル読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)
            persons = list(reader)
        
        print(f"  読み込み: {len(persons)}人")
        
        # 修正処理
        fixed_persons = []
        for i, person in enumerate(persons, 1):
            fixed_person = self.fix_person(person)
            fixed_persons.append(fixed_person)
            
            if i % 1000 == 0:
                print(f"  修正中: {i}件処理済み...")
        
        # CSV保存
        if fixed_persons:
            headers = list(fixed_persons[0].keys())
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(fixed_persons)
        
        print(f"\n✅ 修正完了: {output_file}")
        print(f"  修正内容:")
        print(f"    敬称除去: {self.fixed_count['honorifics']}件")
        print(f"    display補完: {self.fixed_count['missing_display']}件")
        print(f"    カテゴリ正規化: {self.fixed_count['categories']}件")
        print(f"    知名度調整: {self.fixed_count['recognition']}件")
        print(f"    合計修正: {self.fixed_count['total']}件")
        
        return fixed_persons
    
    def fix_person(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """個人データを修正"""
        
        fixed = dict(person)
        modified = False
        
        # 1. 敬称除去
        for field in ['person_name', 'person_name_ja', 'person_name_display']:
            original = fixed.get(field, '')
            if original:
                cleaned = self.remove_honorifics(original)
                if cleaned != original:
                    fixed[field] = cleaned
                    self.fixed_count['honorifics'] += 1
                    modified = True
        
        # 2. person_name_display補完
        if not fixed.get('person_name_display'):
            # 日本語名優先、なければ英語名
            display = fixed.get('person_name_ja') or fixed.get('person_name', '')
            if display:
                fixed['person_name_display'] = display
                self.fixed_count['missing_display'] += 1
                modified = True
        
        # 3. カテゴリ正規化
        category = fixed.get('category', '')
        if category in self.category_mapping:
            fixed['category'] = self.category_mapping[category]
            self.fixed_count['categories'] += 1
            modified = True
        elif category not in self.valid_categories:
            # 無効なカテゴリは「その他」に
            fixed['category'] = 'その他'
            self.fixed_count['categories'] += 1
            modified = True
        
        # 4. 知名度調整（教科書必修人物）
        name_ja = fixed.get('person_name_ja', '')
        if name_ja in self.textbook_figures:
            recognition = fixed.get('name_recognition', '')
            try:
                rec_value = int(recognition) if recognition else 50
                if rec_value < 90:
                    fixed['name_recognition'] = '95'  # 教科書必修なので高めに設定
                    self.fixed_count['recognition'] += 1
                    modified = True
            except ValueError:
                fixed['name_recognition'] = '95'
                self.fixed_count['recognition'] += 1
                modified = True
        
        # 5. Newton特別処理（元の問題）
        if fixed.get('person_name') == 'Isaac Newton':
            if fixed.get('person_name_display') != 'ニュートン':
                fixed['person_name_display'] = 'ニュートン'
                modified = True
        
        if modified:
            self.fixed_count['total'] += 1
        
        return fixed
    
    def remove_honorifics(self, text: str) -> str:
        """敬称を除去"""
        
        result = text
        
        # 「ちゃん」「くん」「さん」など
        for honorific in self.honorifics:
            # 文末の敬称
            if result.endswith(honorific):
                result = result[:-len(honorific)]
            
            # カッコ内の敬称も処理
            # 例: しずちゃん（南海キャンディーズ） → しず（南海キャンディーズ）
            pattern = f'([^（\\(]+){re.escape(honorific)}([（\\(])'
            result = re.sub(pattern, r'\1\2', result)
            
            # アンダースコア前の敬称
            # 例: しずちゃん_南海キャンディーズ → しず_南海キャンディーズ
            pattern = f'([^_]+){re.escape(honorific)}(_)'
            result = re.sub(pattern, r'\1\2', result)
        
        return result


def main():
    """メイン処理"""
    
    print("="*60)
    print("🔧 データベースルール違反修正")
    print("="*60)
    
    fixer = RuleViolationFixer()
    
    # 最新データベースを修正
    input_file = 'ULTRA_THINK_COMPLETE_17074_20250827_081310.csv'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ULTRA_THINK_FIXED_{timestamp}.csv'
    
    fixed_persons = fixer.fix_database(input_file, output_file)
    
    # JSON版も保存
    json_file = f'ULTRA_THINK_FIXED_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'total_persons': len(fixed_persons),
                'timestamp': timestamp,
                'version': '4.1',
                'description': 'Ultra Think Database - ルール違反修正版',
                'fixes_applied': fixer.fixed_count
            },
            'persons': fixed_persons
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 出力ファイル:")
    print(f"  CSV: {output_file}")
    print(f"  JSON: {json_file}")
    print("="*60)


if __name__ == "__main__":
    main()