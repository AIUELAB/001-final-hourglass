#!/usr/bin/env python3
"""
データベースルール遵守検証システム
PERSON_NAME_DISPLAY_UNIFIED_RULES.mdに基づく検証
"""

import csv
import json
import re
from typing import Dict, List, Any, Tuple
from datetime import datetime


class DatabaseRuleValidator:
    """データベースのルール遵守を検証"""
    
    def __init__(self):
        self.violations = []
        self.warnings = []
        self.stats = {
            'total_checked': 0,
            'violations': 0,
            'warnings': 0,
            'categories': {}
        }
        
        # 日本の歴史人物（フルネーム必須）
        self.japanese_historical = [
            '織田信長', '豊臣秀吉', '徳川家康', '源頼朝', '足利尊氏',
            '武田信玄', '上杉謙信', '伊達政宗', '坂本龍馬', '西郷隆盛'
        ]
        
        # 敬称禁止リスト
        self.honorifics = ['さん', 'くん', 'ちゃん', '様', '殿', '氏', '先生', '博士']
        
        # カテゴリ定義（正式なもの）
        self.valid_categories = [
            'エンタメ', 'スポーツ', '学術・科学', 'ビジネス', '文化・芸術',
            '歴史上の人物', '政治', 'テクノロジー', 'インフルエンサー',
            '社会活動家', '現代のイノベーター', '架空の存在', '動物', 
            '政治・経済', '科学', '国際', 'その他'
        ]
    
    def validate_database(self, filename: str) -> Tuple[List, List, Dict]:
        """データベースを検証"""
        
        print("🔍 データベース検証開始...")
        print(f"  ファイル: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            import io
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)
            
            for i, row in enumerate(reader, 1):
                self.validate_person(row, i)
                
                if i % 1000 == 0:
                    print(f"  検証中: {i}件処理済み...")
        
        self.stats['total_checked'] = i
        self.stats['violations'] = len(self.violations)
        self.stats['warnings'] = len(self.warnings)
        
        return self.violations, self.warnings, self.stats
    
    def validate_person(self, person: Dict[str, Any], row_num: int):
        """個人データを検証"""
        
        # 1. person_name_display検証
        self.validate_person_name_display(person, row_num)
        
        # 2. カテゴリ検証
        self.validate_category(person, row_num)
        
        # 3. 必須フィールド検証
        self.validate_required_fields(person, row_num)
        
        # 4. 知名度検証
        self.validate_name_recognition(person, row_num)
        
        # 5. 敬称チェック
        self.validate_no_honorifics(person, row_num)
    
    def validate_person_name_display(self, person: Dict, row_num: int):
        """person_name_displayのルール検証"""
        
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        display = person.get('person_name_display', '')
        category = person.get('category', '')
        
        # ルール1: 日本の歴史人物はフルネーム
        if category == '歴史上の人物' and name_ja in self.japanese_historical:
            if display != name_ja:
                self.violations.append({
                    'row': row_num,
                    'type': 'DISPLAY_NAME',
                    'rule': '日本の歴史人物はフルネーム表記',
                    'person': name_ja,
                    'current': display,
                    'expected': name_ja
                })
        
        # ルール2: displayが空
        if not display:
            self.violations.append({
                'row': row_num,
                'type': 'MISSING_DISPLAY',
                'rule': 'person_name_displayが必須',
                'person': name_ja or name,
                'current': '',
                'expected': name_ja or name
            })
        
        # ルール3: 英語名がそのまま使われている（日本語があるのに）
        if name_ja and display == name and display != name_ja:
            self.warnings.append({
                'row': row_num,
                'type': 'ENGLISH_DISPLAY',
                'rule': '日本語名がある場合は日本語表示推奨',
                'person': name,
                'current': display,
                'suggested': name_ja
            })
    
    def validate_category(self, person: Dict, row_num: int):
        """カテゴリの検証"""
        
        category = person.get('category', '')
        
        # 空のカテゴリ
        if not category:
            self.violations.append({
                'row': row_num,
                'type': 'MISSING_CATEGORY',
                'rule': 'カテゴリが必須',
                'person': person.get('person_name_ja', person.get('person_name', '')),
                'current': '',
                'expected': 'その他'
            })
        
        # 無効なカテゴリ
        elif category not in self.valid_categories:
            # 空文字列も無効とする
            if category == '':
                category = '(空)'
            
            self.warnings.append({
                'row': row_num,
                'type': 'INVALID_CATEGORY',
                'rule': '標準カテゴリを使用',
                'person': person.get('person_name_ja', person.get('person_name', '')),
                'current': category,
                'suggested': 'その他'
            })
        
        # カテゴリ統計
        cat = category if category else '(空)'
        if cat not in self.stats['categories']:
            self.stats['categories'][cat] = 0
        self.stats['categories'][cat] += 1
    
    def validate_required_fields(self, person: Dict, row_num: int):
        """必須フィールドの検証"""
        
        required_fields = ['person_name', 'person_name_ja', 'person_name_display']
        
        for field in required_fields:
            if not person.get(field):
                self.violations.append({
                    'row': row_num,
                    'type': 'MISSING_FIELD',
                    'rule': f'{field}が必須',
                    'person': person.get('person_name', f'行{row_num}'),
                    'current': '',
                    'expected': '値が必要'
                })
    
    def validate_name_recognition(self, person: Dict, row_num: int):
        """知名度の検証"""
        
        recognition = person.get('name_recognition', '')
        
        if recognition:
            try:
                rec_value = int(recognition)
                
                # 範囲チェック
                if rec_value < 1 or rec_value > 100:
                    self.violations.append({
                        'row': row_num,
                        'type': 'INVALID_RECOGNITION',
                        'rule': '知名度は1-100の範囲',
                        'person': person.get('person_name_ja', person.get('person_name', '')),
                        'current': str(rec_value),
                        'expected': '1-100'
                    })
                
                # 日本の歴史的重要人物の知名度チェック
                name_ja = person.get('person_name_ja', '')
                if name_ja in ['織田信長', '豊臣秀吉', '徳川家康'] and rec_value < 90:
                    self.warnings.append({
                        'row': row_num,
                        'type': 'LOW_RECOGNITION',
                        'rule': '教科書必修人物の知名度',
                        'person': name_ja,
                        'current': str(rec_value),
                        'suggested': '90以上'
                    })
                    
            except ValueError:
                self.violations.append({
                    'row': row_num,
                    'type': 'INVALID_RECOGNITION_FORMAT',
                    'rule': '知名度は数値である必要',
                    'person': person.get('person_name_ja', person.get('person_name', '')),
                    'current': recognition,
                    'expected': '数値'
                })
    
    def validate_no_honorifics(self, person: Dict, row_num: int):
        """敬称が含まれていないかチェック"""
        
        fields_to_check = ['person_name', 'person_name_ja', 'person_name_display']
        
        for field in fields_to_check:
            value = person.get(field, '')
            if value:
                for honorific in self.honorifics:
                    if honorific in value:
                        self.violations.append({
                            'row': row_num,
                            'type': 'HONORIFIC_FOUND',
                            'rule': '敬称は使用禁止',
                            'person': value,
                            'current': value,
                            'expected': value.replace(honorific, '')
                        })
    
    def generate_report(self, violations: List, warnings: List, stats: Dict):
        """検証レポートを生成"""
        
        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        report = f"""# 📋 データベースルール検証レポート

## 📅 実行情報
- 実行日時: {timestamp}
- 検証件数: {stats['total_checked']}件
- 違反件数: {stats['violations']}件
- 警告件数: {stats['warnings']}件

## 🚨 ルール違反 ({len(violations)}件)
"""
        
        if violations:
            # 違反タイプ別に集計
            violation_types = {}
            for v in violations:
                vtype = v['type']
                if vtype not in violation_types:
                    violation_types[vtype] = []
                violation_types[vtype].append(v)
            
            for vtype, items in violation_types.items():
                report += f"\n### {vtype} ({len(items)}件)\n"
                
                # 最初の5件を表示
                for item in items[:5]:
                    report += f"- 行{item['row']}: {item['person']}\n"
                    report += f"  ルール: {item['rule']}\n"
                    report += f"  現在: {item['current']}\n"
                    report += f"  期待: {item['expected']}\n"
                
                if len(items) > 5:
                    report += f"  ...他{len(items)-5}件\n"
        else:
            report += "\n✅ ルール違反なし\n"
        
        report += f"""
## ⚠️ 警告 ({len(warnings)}件)
"""
        
        if warnings:
            # 警告タイプ別に集計
            warning_types = {}
            for w in warnings:
                wtype = w['type']
                if wtype not in warning_types:
                    warning_types[wtype] = []
                warning_types[wtype].append(w)
            
            for wtype, items in warning_types.items():
                report += f"\n### {wtype} ({len(items)}件)\n"
                
                # 最初の5件を表示
                for item in items[:5]:
                    report += f"- 行{item['row']}: {item['person']}\n"
                    report += f"  ルール: {item['rule']}\n"
                    report += f"  現在: {item['current']}\n"
                    report += f"  推奨: {item['suggested']}\n"
                
                if len(items) > 5:
                    report += f"  ...他{len(items)-5}件\n"
        else:
            report += "\n✅ 警告なし\n"
        
        report += f"""
## 📊 カテゴリ分布

| カテゴリ | 件数 | 割合 |
|---------|------|------|
"""
        
        sorted_categories = sorted(stats['categories'].items(), 
                                  key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_categories[:20]:
            percentage = (count / stats['total_checked']) * 100
            report += f"| {category} | {count} | {percentage:.1f}% |\n"
        
        report += """
## 📝 検証基準

### 必須ルール
1. **person_name_display**: 日本の歴史人物はフルネーム表記
2. **カテゴリ**: 定義された標準カテゴリを使用
3. **必須フィールド**: person_name, person_name_ja, person_name_display
4. **知名度**: 1-100の範囲
5. **敬称禁止**: さん、くん、様、殿、氏、先生、博士は使用禁止

### 推奨事項
- 教科書必修人物は知名度90以上
- 日本語名がある場合は日本語表示を優先
- カテゴリは適切に分類

## 🎯 総合評価
"""
        
        if stats['violations'] == 0 and stats['warnings'] < 100:
            report += "\n### ✅ 優秀\nルール違反がなく、警告も最小限です。"
        elif stats['violations'] < 10 and stats['warnings'] < 500:
            report += "\n### ⚠️ 良好\n軽微な違反がありますが、概ねルールを遵守しています。"
        elif stats['violations'] < 100:
            report += "\n### ⚠️ 要改善\n複数の違反があります。修正が必要です。"
        else:
            report += "\n### 🚨 要大幅修正\n多数の違反があります。大幅な修正が必要です。"
        
        return report


def main():
    """メイン処理"""
    
    print("="*60)
    print("📋 データベースルール遵守検証")
    print("="*60)
    
    validator = DatabaseRuleValidator()
    
    # 最新のデータベースを検証
    database_file = 'ULTRA_THINK_FIXED_20250827_081848.csv'
    
    violations, warnings, stats = validator.validate_database(database_file)
    
    # レポート生成
    report = validator.generate_report(violations, warnings, stats)
    
    # レポート保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"RULE_VALIDATION_REPORT_{timestamp}.md"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 検証完了")
    print(f"  違反: {len(violations)}件")
    print(f"  警告: {len(warnings)}件")
    print(f"  レポート: {report_filename}")
    
    # サマリー表示
    if violations:
        print("\n🚨 主な違反:")
        violation_types = {}
        for v in violations:
            violation_types[v['type']] = violation_types.get(v['type'], 0) + 1
        
        for vtype, count in sorted(violation_types.items(), 
                                  key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {vtype}: {count}件")
    
    if warnings:
        print("\n⚠️ 主な警告:")
        warning_types = {}
        for w in warnings:
            warning_types[w['type']] = warning_types.get(w['type'], 0) + 1
        
        for wtype, count in sorted(warning_types.items(), 
                                  key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {wtype}: {count}件")


if __name__ == "__main__":
    main()