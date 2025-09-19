#!/usr/bin/env python3
"""
Ultra Think 日本語表記修正システム
日本人なのに外国語表記になっているレコードを修正
"""
import json
import re
from datetime import datetime
from typing import Any

import pandas as pd


class JapaneseDisplayFixer:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)
        self.fixes: list[dict[str, Any]] = []
        self.stats = {
            'total_japanese': 0,
            'total_problems': 0,
            'fixed': 0,
            'skipped_english_names': 0,
            'errors': 0
        }

        # 英語表記が正しい芸名のリスト（全て大文字で保存）
        self.english_stage_names = {
            'HIKAKIN', 'SEIKIN', 'DAIGO', 'GACKT', 'HYDE', 'L\'Arc~en~Ciel',
            'YOSHIKI', 'DJ LOVE', 'DJ KOO', 'EXILE', 'GENERATIONS',
            'AAA', 'DA PUMP', 'w-inds.', 'TRF', 'MAX', 'SPEED',
            'LUNA SEA', 'X JAPAN', 'GLAY', 'SMAP', 'TOKIO', 'V6',
            'KinKi Kids', 'NEWS', 'KAT-TUN', 'Hey! Say! JUMP',
            'Kis-My-Ft2', 'Sexy Zone', 'A.B.C-Z', 'Johnny\'s WEST',
            'King & Prince', 'SixTONES', 'Snow Man', 'YOASOBI',
            'SEKAI NO OWARI', 'ONE OK ROCK', 'RADWIMPS', 'BUMP OF CHICKEN',
            'MAN WITH A MISSION', 'UVERworld', '[Alexandros]',
            'Eve', 'Ado', 'RIKU', 'JIN', 'TERU', 'TAKURO', 'HEATH',
            'PATA', 'hide', 'SUGIZO', 'INORAN', 'J', 'RYUICHI',
            'Fukase', 'Nakajin', 'Saori', 'HISASHI', 'Ayase', 'ikura',
            'NANA', 'NAMI', 'ERIKO', 'MINAMI', 'REINA', 'HIROKO',
            'TAKAKO', 'LiSA', 'Aimer', 'milet', 'Uru', 'MISIA',
            'AI', 'JUJU', 'Superfly', 'YUI', 'miwa', 'aiko',
            'Perfume', 'BABYMETAL', 'BiSH', 'BLACKPINK', 'TWICE',
            'BTS', 'Stray Kids', 'SEVENTEEN', 'NCT', 'ENHYPEN',
            'TXT', 'ATEEZ', 'TREASURE', 'IVE', 'LE SSERAFIM',
            'NewJeans', 'aespa', 'ITZY', 'NMIXX', 'STAYC',
            'K-POP', 'J-POP', 'C-POP', 'T-POP', 'V-POP'
        }

    def has_japanese_chars(self, text: str) -> bool:
        """日本語文字（ひらがな、カタカナ、漢字）が含まれているか確認"""
        if pd.isna(text):
            return False
        return bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', str(text)))

    def is_english_stage_name(self, name: str) -> bool:
        """英語表記が正しい芸名かどうか判定"""
        if pd.isna(name):
            return False
        name_upper = str(name).upper()

        # 完全一致チェック
        if name_upper in self.english_stage_names:
            return True

        # 部分一致チェック（グループ名が含まれる場合）
        for stage_name in self.english_stage_names:
            if stage_name in name_upper:
                return True

        return False

    def should_use_japanese_display(self, row) -> bool:
        """日本語表記を使用すべきか判定"""
        # person_name_jaが存在しない場合はスキップ
        if pd.isna(row['person_name_ja']) or not row['person_name_ja']:
            return False

        # すでに日本語表記の場合はスキップ
        if self.has_japanese_chars(row['person_name_display']):
            return False

        # 日本人でない場合はスキップ
        if row['nationality'] != '日本':
            return False

        # 英語の芸名の場合はスキップ
        if self.is_english_stage_name(row['person_name']):
            return False

        # person_name_jaも英語の芸名の場合はスキップ
        if self.is_english_stage_name(row['person_name_ja']):
            return False

        return True

    def _process_japanese_record(self, idx: Any, row) -> None:
        """日本人レコードを処理"""
        person_id = row['person_id']
        old_display = row['person_name_display']
        new_display = row['person_name_ja']

        # グループ名が含まれている場合は保持
        if '(' in str(old_display) and ')' in str(old_display):
            # グループ名を抽出して追加
            group_match = re.search(r'\((.+?)\)', str(old_display))
            if group_match:
                group_name = group_match.group(1)
                new_display = f"{new_display} ({group_name})"

        # 修正を適用
        self.df.loc[idx, 'person_name_display'] = new_display

        self.fixes.append({
            'person_id': person_id,
            'person_name': row['person_name'],
            'old_display': old_display,
            'new_display': new_display,
            'occupation': row['occupation'],
            'category': row['category']
        })

        self.stats['fixed'] += 1

    def _process_english_stage_name(self, row) -> None:
        """英語芸名を処理"""
        if self.is_english_stage_name(str(row['person_name'])) or self.is_english_stage_name(str(row['person_name_ja'])):
            self.stats['skipped_english_names'] += 1

    def fix_display_names(self):
        """表示名を修正"""
        # 日本人レコードをフィルタ
        japanese_records = self.df[self.df['nationality'] == '日本']
        self.stats['total_japanese'] = len(japanese_records)

        print(f"📊 日本人レコード数: {len(japanese_records)}")

        for idx, row in self.df.iterrows():
            if self.should_use_japanese_display(row):
                self._process_japanese_record(idx, row)
            elif row['nationality'] == '日本' and not self.has_japanese_chars(str(row['person_name_display'])):
                self._process_english_stage_name(row)

        self.stats['total_problems'] = self.stats['fixed'] + self.stats['skipped_english_names']

    def save_results(self):
        """結果を保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 修正済みCSVを保存
        output_csv = f'ultra_think_JAPANESE_DISPLAY_FIXED_{timestamp}.csv'
        self.df.to_csv(output_csv, index=False, encoding='utf-8')

        # 修正ログを保存
        fix_log = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'fixes': self.fixes
        }

        with open(f'japanese_display_fix_log_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(fix_log, f, ensure_ascii=False, indent=2)

        return output_csv, fix_log

    def print_report(self):
        """レポートを表示"""
        print("\n" + "="*60)
        print("📊 日本語表記修正レポート")
        print("="*60)
        print(f"日本人レコード総数: {self.stats['total_japanese']}")
        print(f"問題のあるレコード: {self.stats['total_problems']}")
        print(f"修正済み: {self.stats['fixed']}")
        print(f"英語芸名（スキップ）: {self.stats['skipped_english_names']}")
        print(f"エラー: {self.stats['errors']}")
        print("-"*60)

        # 職業別の修正数を集計
        occupation_counts = {}
        for fix in self.fixes:
            occ = fix['occupation']
            if occ not in occupation_counts:
                occupation_counts[occ] = 0
            occupation_counts[occ] += 1

        if occupation_counts:
            print("\n📈 職業別修正数:")
            for occ, count in sorted(occupation_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {occ}: {count}件")

        # 指定されたperson_idの修正結果を表示
        target_ids = ['P000064', 'P000065', 'P000066', 'P000067', 'P000068', 'P000069', 'P000070', 'P000073', 'P000074']
        print("\n🎯 指定されたperson_idの修正結果:")

        for fix in self.fixes:
            if fix['person_id'] in target_ids:
                print(f"  {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")

        if self.stats['fixed'] > 0:
            print("\n✅ 修正例（最初の20件）:")
            for fix in self.fixes[:20]:
                print(f"  {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")

def main():
    print("🚀 Ultra Think 日本語表記修正システム起動")

    # バックアップ作成
    import shutil
    backup_file = f"backup_before_japanese_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy('ultra_think_COMEDY_GROUPS_FIXED_20250828_190550.csv', backup_file)
    print(f"📁 バックアップ作成: {backup_file}")

    # 修正システムを実行
    fixer = JapaneseDisplayFixer('ultra_think_COMEDY_GROUPS_FIXED_20250828_190550.csv')

    print("\n🔧 日本語表記を修正中...")
    fixer.fix_display_names()

    # 結果を保存
    output_file, _ = fixer.save_results()

    # レポートを表示
    fixer.print_report()

    print(f"\n📁 出力ファイル: {output_file}")

    # 修正率を計算
    fix_rate = (fixer.stats['fixed'] / fixer.stats['total_japanese']) * 100 if fixer.stats['total_japanese'] > 0 else 0
    print(f"\n🎯 修正率: {fix_rate:.2f}%")

    return output_file, fixer.stats

if __name__ == "__main__":
    output, stats = main()
