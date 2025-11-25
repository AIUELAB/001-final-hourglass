#!/usr/bin/env python3
"""
Ultra Think person_name_display 完全修正スクリプト
文化的・歴史的文脈に適した表記名を生成
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class DisplayNameRule:
    """表示名ルールのデータクラス"""
    pattern_type: str  # 'nickname', 'group', 'fullname', 'surname', 'dynasty'
    display_format: str  # 実際の表示形式

class UltraThinkDisplayNameFixer:
    """person_name_display修正クラス"""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.all_people = []
        self.removed_groups = []
        self.stats = defaultdict(int)

        # 愛称が極めて有名な人物
        self.nickname_famous = {
            'Louis Armstrong': 'サッチモことルイ・アームストロング',
            'Edson Arantes do Nascimento': 'ペレことエドソン・アランテス・ド・ナシメント',
            'Pelé': 'ペレことエドソン・アランテス・ド・ナシメント',
            'Margaret Thatcher': '鉄の女ことマーガレット・サッチャー',
        }

        # グループメンバー（所属表記が必要）
        self.group_members = {
            'John Lennon': 'ジョン・レノン（ビートルズ）',
            'Paul McCartney': 'ポール・マッカートニー（ビートルズ）',
            'George Harrison': 'ジョージ・ハリスン（ビートルズ）',
            'Ringo Starr': 'リンゴ・スター（ビートルズ）',
            'Mick Jagger': 'ミック・ジャガー（ローリング・ストーンズ）',
            'Keith Richards': 'キース・リチャーズ（ローリング・ストーンズ）',
            'Freddie Mercury': 'フレディ・マーキュリー（クイーン）',
            'Brian May': 'ブライアン・メイ（クイーン）',
            'Flea': 'フリー（レッド・ホット・チリ・ペッパーズ）',
            'Anthony Kiedis': 'アンソニー・キーディス（レッド・ホット・チリ・ペッパーズ）',
        }

        # 削除すべきグループ名
        self.group_names = [
            'The Beatles', 'ビートルズ',
            'The Rolling Stones', 'ローリング・ストーンズ',
            'Queen', 'クイーン',
            'Led Zeppelin', 'レッド・ツェッペリン',
            'Pink Floyd', 'ピンク・フロイド',
            'The Who', 'ザ・フー',
            'Red Hot Chili Peppers', 'レッド・ホット・チリ・ペッパーズ'
        ]

        # 姓のみ表記の西洋の天才たち
        self.western_genius_surnames = {
            'Thomas Edison': 'エジソン',
            'Albert Einstein': 'アインシュタイン',
            'Isaac Newton': 'ニュートン',
            'Charles Darwin': 'ダーウィン',
            'Marie Curie': 'キュリー',
            'Galileo Galilei': 'ガリレオ',
            'Leonardo da Vinci': 'ダ・ヴィンチ',
            'Michelangelo': 'ミケランジェロ',
            'Pablo Picasso': 'ピカソ',
            'Vincent van Gogh': 'ゴッホ',
            'Claude Monet': 'モネ',
            'Ludwig van Beethoven': 'ベートーヴェン',
            'Wolfgang Amadeus Mozart': 'モーツァルト',
            'Johann Sebastian Bach': 'バッハ',
            'Frederic Chopin': 'ショパン',
            'Pyotr Tchaikovsky': 'チャイコフスキー',
            'Wilhelm Röntgen': 'レントゲン',
            'Max Planck': 'プランク',
            'Niels Bohr': 'ボーア',
            'Werner Heisenberg': 'ハイゼンベルク',
        }

        # 中国皇帝の王朝＋通称
        self.chinese_emperors = {
            'Qin Shi Huang': '秦の始皇帝',
            'Emperor Wu of Han': '漢の武帝',
            'Emperor Taizong of Tang': '唐の太宗',
            'Kublai Khan': 'フビライ・ハン',
        }

    def load_database(self):
        """1000人データベースを読み込み"""
        print("📂 データベース読み込み中...")

        # 最新の1000人データベースファイル
        csv_file = "ultra_think_ultimate_1000_final_20250825_140225.csv"

        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.all_people.append(row)
            print(f"  ✅ {len(self.all_people)}人のデータを読み込み")
        except Exception as e:
            print(f"  ❌ エラー: {e}")

    def is_group_name(self, person: Dict) -> bool:
        """グループ名かどうかを判定"""
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        occupation = person.get('occupation', '')

        # グループ名リストと照合
        if name in self.group_names or name_ja in self.group_names:
            return True

        # 職業が「バンド」「グループ」等の場合
        if any(word in occupation for word in ['バンド', 'グループ', '楽団', 'band', 'group']):
            return True

        return False

    def get_display_name(self, person: Dict) -> str:
        """適切なdisplay_nameを決定"""
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        nationality = person.get('nationality', '')
        occupation = person.get('occupation', '')

        try:
            birth_year = int(person.get('birth_year', 0))
        except:
            birth_year = 0

        # 1. 愛称が極めて有名な人物
        if name in self.nickname_famous:
            self.stats['nickname'] += 1
            return self.nickname_famous[name]

        # 2. グループメンバー（所属表記）
        if name in self.group_members:
            self.stats['group_member'] += 1
            return self.group_members[name]

        # 3. 西洋の天才（姓のみ）
        if name in self.western_genius_surnames:
            self.stats['surname_only'] += 1
            return self.western_genius_surnames[name]

        # 4. 中国皇帝（王朝＋通称）
        if name in self.chinese_emperors:
            self.stats['dynasty'] += 1
            return self.chinese_emperors[name]

        # 5. 日本の歴史人物（明治以前）→ フルネーム
        if nationality == '日本' and birth_year > 0 and birth_year < 1868:
            self.stats['japanese_historical'] += 1
            return name_ja

        # 6. 政治指導者 → フルネーム
        political_keywords = ['政治', '大統領', '首相', '皇帝', '王', '将軍', '指導者']
        if any(keyword in occupation for keyword in political_keywords):
            self.stats['political_leader'] += 1
            return name_ja

        # 7. デフォルト判定
        # 西洋の科学者・発明家・芸術家で、既知パターンに該当しない場合
        western_occupations = ['科学者', '物理学者', '化学者', '発明家', '画家', '音楽家', '作曲家']
        western_countries = ['アメリカ', 'イギリス', 'ドイツ', 'フランス', 'イタリア', 'オランダ', 'スペイン']

        if (nationality in western_countries and
            any(occ in occupation for occ in western_occupations)):
            # 姓のみ抽出を試みる
            parts = name_ja.split('・')
            if len(parts) >= 2:
                self.stats['surname_extracted'] += 1
                return parts[-1]  # 最後の部分を姓として返す

        # 8. その他はフルネーム
        self.stats['fullname_default'] += 1
        return name_ja

    def process_database(self):
        """データベースを処理"""
        print("\n🔧 display_name修正処理中...")

        processed_people = []

        for person in self.all_people:
            # グループ名は除外
            if self.is_group_name(person):
                self.removed_groups.append(person)
                self.stats['groups_removed'] += 1
                continue

            # display_nameを再計算
            old_display = person.get('person_name_display', '')
            new_display = self.get_display_name(person)

            if old_display != new_display:
                self.stats['names_changed'] += 1
                person['person_name_display_old'] = old_display

            person['person_name_display'] = new_display
            processed_people.append(person)

        self.all_people = processed_people
        print(f"  ✅ {len(self.all_people)}人の表示名を処理")
        print(f"  ⚠️ {len(self.removed_groups)}個のグループ名を削除")

    def save_results(self):
        """結果を保存"""
        print("\n💾 修正結果を保存中...")

        # 全フィールドを動的に収集
        all_fields = set()
        for person in self.all_people:
            all_fields.update(person.keys())

        # 標準フィールドを優先
        standard_fields = ['person_name', 'person_name_ja', 'person_name_display',
                          'person_name_display_old', 'birth_year', 'nationality',
                          'occupation', 'main_category', 'subcategory']

        fieldnames = []
        for field in standard_fields:
            if field in all_fields:
                fieldnames.append(field)
                all_fields.remove(field)
        fieldnames.extend(sorted(list(all_fields)))

        # CSV保存
        csv_file = f"ultra_think_perfect_display_1000_{self.timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_people)
        print(f"  ✅ CSV保存: {csv_file}")

        # JSON保存
        json_file = f"ultra_think_perfect_display_1000_{self.timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_people, f, ensure_ascii=False, indent=2)
        print(f"  ✅ JSON保存: {json_file}")

        # 削除されたグループを別ファイルに保存
        if self.removed_groups:
            removed_file = f"removed_groups_{self.timestamp}.json"
            with open(removed_file, 'w', encoding='utf-8') as f:
                json.dump(self.removed_groups, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 削除グループ保存: {removed_file}")

        return csv_file, json_file

    def generate_report(self):
        """修正レポートを生成"""
        print("\n📝 レポート生成中...")

        report = []
        report.append("# 🎯 Ultra Think person_name_display 修正レポート")
        report.append("")
        report.append(f"## 📅 実行日時")
        report.append(f"{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report.append("")

        report.append("## 📊 処理結果サマリー")
        report.append(f"- **処理人数**: {len(self.all_people)}人")
        report.append(f"- **表示名変更**: {self.stats['names_changed']}件")
        report.append(f"- **グループ削除**: {self.stats['groups_removed']}件")
        report.append("")

        report.append("## 🏷️ 表記パターン別集計")
        report.append(f"- 愛称優先型: {self.stats['nickname']}人")
        report.append(f"- グループ所属表記: {self.stats['group_member']}人")
        report.append(f"- 姓のみ（登録済み）: {self.stats['surname_only']}人")
        report.append(f"- 姓のみ（自動抽出）: {self.stats['surname_extracted']}人")
        report.append(f"- 王朝＋通称: {self.stats['dynasty']}人")
        report.append(f"- 日本歴史人物: {self.stats['japanese_historical']}人")
        report.append(f"- 政治指導者: {self.stats['political_leader']}人")
        report.append(f"- フルネーム（デフォルト）: {self.stats['fullname_default']}人")
        report.append("")

        # 変更例を表示
        report.append("## 📝 表示名変更例（最初の20件）")
        changed_count = 0
        for person in self.all_people[:100]:  # 最初の100人から抽出
            if 'person_name_display_old' in person:
                old = person['person_name_display_old']
                new = person['person_name_display']
                if old != new:
                    report.append(f"- {old} → {new}")
                    changed_count += 1
                    if changed_count >= 20:
                        break
        report.append("")

        # 削除されたグループ
        if self.removed_groups:
            report.append("## 🗑️ 削除されたグループ名")
            for group in self.removed_groups[:10]:
                report.append(f"- {group.get('person_name_ja', group.get('person_name', ''))}")
            if len(self.removed_groups) > 10:
                report.append(f"  ... 他{len(self.removed_groups)-10}件")
            report.append("")

        # 適用ルールの説明
        report.append("## 📋 適用された表記ルール")
        report.append("")
        report.append("### 1. 愛称優先型")
        report.append("- サッチモことルイ・アームストロング")
        report.append("- ペレことエドソン・アランテス・ド・ナシメント")
        report.append("- 鉄の女ことマーガレット・サッチャー")
        report.append("")

        report.append("### 2. グループ所属表記型")
        report.append("- ジョン・レノン（ビートルズ）")
        report.append("- フリー（レッド・ホット・チリ・ペッパーズ）")
        report.append("")

        report.append("### 3. 姓のみ型")
        report.append("- エジソン、アインシュタイン、ニュートン")
        report.append("- ピカソ、ゴッホ、ベートーヴェン")
        report.append("")

        report.append("### 4. フルネーム型")
        report.append("- 織田信長、豊臣秀吉、徳川家康（日本の歴史人物）")
        report.append("- ネルソン・マンデラ、マハトマ・ガンディー（政治指導者）")
        report.append("")

        report.append("### 5. 王朝＋通称型")
        report.append("- 秦の始皇帝、漢の武帝")
        report.append("")

        report.append("## ✅ 成果")
        report.append("- グループと個人の明確な区別を実現")
        report.append("- 文化的・歴史的文脈に適した表記を適用")
        report.append("- エピソード生成時の可読性を大幅改善")
        report.append("")

        report.append("---")
        report.append(f"*Display Name Fix Report v1.0*")
        report.append(f"*Generated: {datetime.now().isoformat()}*")
        report.append("")

        # レポート保存
        report_file = f"DISPLAY_NAME_FIX_REPORT_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        print(f"  ✅ レポート保存: {report_file}")

        return report_file

    def run(self):
        """修正処理を実行"""
        print("🚀 Ultra Think person_name_display 修正開始")
        print("="*60)

        try:
            # データベース読み込み
            self.load_database()

            # 処理実行
            self.process_database()

            # 結果保存
            csv_file, json_file = self.save_results()

            # レポート生成
            report_file = self.generate_report()

            print("\n" + "="*60)
            print("✨ 修正完了！")
            print(f"📁 出力ファイル:")
            print(f"  - CSV: {csv_file}")
            print(f"  - JSON: {json_file}")
            print(f"  - レポート: {report_file}")
            print("="*60)

        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fixer = UltraThinkDisplayNameFixer()
    fixer.run()
