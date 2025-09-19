#!/usr/bin/env python3
"""
Ultra Think 自動表示名検証システム
person_name_displayの自動検証・修正を行う

作成日: 2025-08-31
"""

import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import hashlib

class AutoDisplayNameValidator:
    """自動的にperson_name_displayを検証・修正するクラス"""
    
    def __init__(self):
        self.rules_file = Path("display_name_correction_rules_latest.json")
        self.groups_file = Path("groups_database.json")
        self.load_rules()
        self.load_groups()
        
    def load_rules(self):
        """修正ルールを読み込み"""
        if self.rules_file.exists():
            with open(self.rules_file, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
        else:
            # デフォルトルール
            self.rules = {
                "auto_japanese_conversion": True,
                "remove_incorrect_groups": True,
                "validate_group_membership": True,
                "known_groups": {
                    "LUNA SEA": ["INORAN", "J", "RYUICHI", "SUGIZO", "真矢"],
                    "SMAP": ["中居正広", "木村拓哉", "稲垣吾郎", "草彅剛", "香取慎吾"],
                    "嵐": ["大野智", "櫻井翔", "相葉雅紀", "二宮和也", "松本潤"],
                    "V6": ["坂本昌行", "長野博", "井ノ原快彦", "森田剛", "三宅健", "岡田准一"],
                },
                "manual_translations": {
                    "HIKAKIN": "ヒカキン",
                    "DAIGO": "ダイゴ",
                    "GACKT": "ガクト",
                    "HYDE": "ハイド",
                    "YOSHIKI": "ヨシキ",
                    "Michael Jackson": "マイケル・ジャクソン",
                    "John Lennon": "ジョン・レノン",
                    "Paul McCartney": "ポール・マッカートニー",
                }
            }
    
    def load_groups(self):
        """グループデータベースを読み込み"""
        if self.groups_file.exists():
            with open(self.groups_file, "r", encoding="utf-8") as f:
                self.groups_db = json.load(f)
        else:
            self.groups_db = {}
    
    def has_non_japanese(self, text: str) -> bool:
        """非日本語文字が含まれているかチェック"""
        if pd.isna(text) or text == "":
            return False
        # 英数字、ハングル等の非日本語文字パターン
        non_japanese_pattern = re.compile(r'[A-Za-z]{2,}|[\u1100-\u11FF\uAC00-\uD7AF]+')
        return bool(non_japanese_pattern.search(text))
    
    def extract_group_annotation(self, display_name: str) -> Tuple[str, Optional[str]]:
        """表示名からグループ注釈を抽出"""
        if pd.isna(display_name):
            return "", None
        
        match = re.match(r'^(.+?)\s*\(([^)]+)\)$', display_name)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return display_name.strip(), None
    
    def validate_group_membership(self, person_name: str, group_name: str) -> bool:
        """グループメンバーシップを検証"""
        if not group_name:
            return True
        
        # ルールに定義されたグループをチェック
        if group_name in self.rules.get("known_groups", {}):
            members = self.rules["known_groups"][group_name]
            # メンバー名の部分一致も許可
            for member in members:
                if member in person_name or person_name in member:
                    return True
            return False
        
        # groups_database.jsonをチェック
        if group_name in self.groups_db:
            members = self.groups_db[group_name]
            if isinstance(members, list):
                for member in members:
                    if member in person_name or person_name in member:
                        return True
            return False
        
        # 不明なグループは一旦許可
        return True
    
    def apply_japanese_conversion(self, row: pd.Series) -> str:
        """日本語変換を適用"""
        display_name = row.get('person_name_display', '')
        person_name_ja = row.get('person_name_ja', '')
        
        # person_name_jaが利用可能な場合
        if person_name_ja and not pd.isna(person_name_ja) and person_name_ja.strip():
            # グループ注釈を保持
            name, group = self.extract_group_annotation(display_name)
            if self.validate_group_membership(person_name_ja, group):
                if group:
                    return f"{person_name_ja} ({group})"
                return person_name_ja
            else:
                # 不正なグループ注釈は削除
                return person_name_ja
        
        # マニュアル翻訳辞書をチェック
        name, group = self.extract_group_annotation(display_name)
        if name in self.rules.get("manual_translations", {}):
            translated = self.rules["manual_translations"][name]
            if self.validate_group_membership(translated, group):
                if group:
                    return f"{translated} ({group})"
                return translated
            else:
                return translated
        
        return display_name
    
    def validate_and_fix(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """データフレーム全体を検証・修正"""
        fixes = []
        df_fixed = df.copy()
        
        for idx, row in df.iterrows():
            if row.get('nationality') != '日本':
                continue
            
            display_name = row.get('person_name_display', '')
            
            # 非日本語チェック
            if self.has_non_japanese(display_name):
                new_display = self.apply_japanese_conversion(row)
                if new_display != display_name:
                    df_fixed.at[idx, 'person_name_display'] = new_display
                    fixes.append({
                        'person_id': row.get('person_id'),
                        'original': display_name,
                        'fixed': new_display,
                        'reason': 'non_japanese_to_japanese'
                    })
            
            # グループ注釈の検証
            else:
                name, group = self.extract_group_annotation(display_name)
                if group and not self.validate_group_membership(name, group):
                    df_fixed.at[idx, 'person_name_display'] = name
                    fixes.append({
                        'person_id': row.get('person_id'),
                        'original': display_name,
                        'fixed': name,
                        'reason': 'invalid_group_removed'
                    })
        
        # 統計情報
        stats = {
            'total_records': len(df),
            'japanese_records': len(df[df['nationality'] == '日本']),
            'fixes_applied': len(fixes),
            'timestamp': datetime.now().isoformat()
        }
        
        return df_fixed, {'fixes': fixes, 'stats': stats}
    
    def save_rules(self, additional_rules: Dict = None):
        """現在のルールを保存"""
        if additional_rules:
            self.rules.update(additional_rules)
        
        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)
    
    def process_file(self, input_file: str, output_file: str = None) -> str:
        """ファイルを処理して修正を適用"""
        print(f"📂 ファイル読み込み中: {input_file}")
        df = pd.read_csv(input_file)
        
        print(f"🔍 {len(df)}件のレコードを検証中...")
        df_fixed, report = self.validate_and_fix(df)
        
        # 出力ファイル名生成
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ultra_think_AUTO_VALIDATED_{timestamp}.csv"
        
        # 保存
        df_fixed.to_csv(output_file, index=False)
        print(f"✅ 修正済みファイル保存: {output_file}")
        
        # レポート保存
        report_file = output_file.replace('.csv', '_report.json')
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📝 レポート保存: {report_file}")
        
        # 統計表示
        print(f"\n📊 修正統計:")
        print(f"  - 総レコード数: {report['stats']['total_records']}")
        print(f"  - 日本人レコード: {report['stats']['japanese_records']}")
        print(f"  - 修正適用数: {report['stats']['fixes_applied']}")
        
        return output_file


def main():
    """メイン処理"""
    validator = AutoDisplayNameValidator()
    
    # 最新のultra_think_*.csvを検索
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        print("❌ ultra_think_*.csv ファイルが見つかりません")
        return
    
    latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"🎯 対象ファイル: {latest_csv.name}")
    
    # 処理実行
    output_file = validator.process_file(str(latest_csv))
    
    print(f"\n✨ 検証・修正完了！")
    print(f"📌 出力ファイル: {output_file}")
    
    # ルール保存
    validator.save_rules()
    print(f"💾 ルール保存完了: {validator.rules_file}")


if __name__ == "__main__":
    main()