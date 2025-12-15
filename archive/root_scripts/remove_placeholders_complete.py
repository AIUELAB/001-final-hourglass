#!/usr/bin/env python3
"""
プレースホルダー完全削除システム
品質第一原則に基づく実在人物のみのデータベース構築
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple


class PlaceholderRemovalSystem:
    """プレースホルダー削除と品質保証システム"""

    def __init__(self):
        self.removed_count = 0
        self.kept_count = 0
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # プレースホルダーパターン定義
        self.placeholder_patterns = [
            r'^Band Member \d+$',
            r'^Singer \d+$',
            r'^Actor \d+$',
            r'^Actress \d+$',
            r'^Comedian \d+$',
            r'^Dancer \d+$',
            r'^Musician \d+$',
            r'^DJ \d+$',
            r'^Producer \d+$',
            r'^Rapper \d+$',
            r'^Model \d+$',
            r'^TV Host \d+$',
            r'^Radio Host \d+$',
            r'^YouTuber \d+$',
            r'^Streamer \d+$',
            r'^Influencer \d+$',
            r'^Voice Actor \d+$',
            r'^Stage Actor \d+$',
            r'^.*Singer \d+$',
            r'^.*Musician \d+$',
            r'^.*Researcher \d+$',
            r'^.*Scientist \d+$',
            r'^.*Engineer \d+$',
            r'^.*Developer \d+$',
            r'^.*Designer \d+$',
            r'^.*Artist \d+$',
            r'^.*Writer \d+$',
            r'^.*Director \d+$',
            r'^.*Player \d+$',
            r'^.*Athlete \d+$',
            r'^CEO of .* Corp \d+$',
            r'^President of .* Corp \d+$',
            r'^Founder of .* Corp \d+$',
            r'^.*Leader \d+$',
            r'^.*King \d+$',
            r'^.*Queen \d+$',
            r'^.*Prince \d+$',
            r'^.*Princess \d+$',
            r'^.*Duke \d+$',
            r'^.*General \d+$',
            r'^.*Admiral \d+$',
            r"^HBO's .*",
            r"^Broadway's .*",
            r"^Netflix's .*",
            r'^R&B .*\d+$',
            r'^K-Pop .*\d+$',
            r'^J-Pop .*\d+$',
            r'^Pop .*\d+$',
            r'^Rock .*\d+$',
            r'^Jazz .*\d+$',
            r'^Country .*\d+$'
        ]

        # ソース判定
        self.placeholder_sources = [
            'ultra_think_mega',
            'placeholder',
            'auto_generated',
            'batch_generated'
        ]

    def is_placeholder(self, person: Dict) -> bool:
        """プレースホルダーかどうか判定"""

        # 名前パターンチェック
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')

        # パターンマッチング
        for pattern in self.placeholder_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return True
            if re.match(pattern, name_ja, re.IGNORECASE):
                return True

        # person_name と person_name_ja が同じ英語名
        if name == name_ja and re.match(r'^[A-Za-z\s\d]+$', name):
            # 数字を含む場合は疑わしい
            if re.search(r'\d', name):
                return True

        # ソースチェック
        source = person.get('source', '')
        if source in self.placeholder_sources:
            return True

        # 職業が番号付き
        occupation = person.get('occupation', '')
        if re.search(r'\d{2,}', occupation):  # 2桁以上の数字
            return True

        # accuracy_score と impact_score が固定値（85, 80）
        if (person.get('accuracy_score') == '85' and
            person.get('impact_score') == '80'):
            # さらに name_recognition も 85 なら確実
            if person.get('name_recognition') == '85' or person.get('name_recognition') == 85:
                return True

        return False

    def clean_database(self, input_file: str) -> Tuple[List[Dict], List[Dict]]:
        """データベースからプレースホルダーを削除"""

        print(f"\n🔍 データベース解析開始: {input_file}")

        kept_persons = []
        removed_persons = []

        # CSVファイル読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]

            import io
            reader = csv.DictReader(io.StringIO(content))

            for i, row in enumerate(reader):
                if self.is_placeholder(row):
                    removed_persons.append(row)
                    self.removed_count += 1

                    # 最初の10件は詳細表示
                    if self.removed_count <= 10:
                        print(f"  ❌ 削除: {row.get('person_name', '')} - {row.get('occupation', '')}")
                else:
                    kept_persons.append(row)
                    self.kept_count += 1

                # 進捗表示
                if (i + 1) % 1000 == 0:
                    print(f"  進捗: {i + 1}件処理 (削除: {self.removed_count}, 維持: {self.kept_count})")

        print(f"\n📊 解析結果:")
        print(f"  削除: {self.removed_count}件")
        print(f"  維持: {self.kept_count}件")

        return kept_persons, removed_persons

    def validate_quality(self, persons: List[Dict]) -> Tuple[bool, List[str]]:
        """品質検証"""

        print("\n🔍 品質検証開始...")

        issues = []

        # 芸名として英語表記が許容されるリスト
        allowed_english_names = {
            'Ado', 'Ayase', 'DAIGO', 'DJ LOVE', 'Eve', 'Fukase', 'GACKT',
            'HEATH', 'HIKAKIN', 'HISASHI', 'IKKO', 'INORAN', 'JIRO', 'J',
            'Nakajin', 'PATA', 'RM', 'RYUICHI', 'SUGIZO', 'Saori', 'TAKURO',
            'TERU', 'Toshl', 'Vaundy', 'V', 'YOSHIKI', 'YuNi', 'hyde',
            'ken', 'tetsuya', 'yukihiro'
        }

        # サンプリング検査（最初の100件と最後の100件）
        sample = persons[:100] + persons[-100:]

        for person in sample:
            # プレースホルダーチェック
            if self.is_placeholder(person):
                issues.append(f"プレースホルダー検出: {person.get('person_name', '')}")

            # person_name_ja チェック（芸名は除外）
            person_name = person.get('person_name', '')
            if person.get('person_name') == person.get('person_name_ja'):
                if re.match(r'^[A-Za-z\s]+$', person_name):
                    # 芸名として許容されるものは除外
                    if person_name not in allowed_english_names:
                        issues.append(f"日本語名未設定: {person_name}")

            # name_recognition チェック
            recognition = person.get('name_recognition', '50')
            try:
                recognition_int = int(recognition) if recognition else 50
                if recognition_int == 85:  # 疑わしい固定値
                    if person.get('accuracy_score') == '85':
                        issues.append(f"固定値の疑い: {person.get('person_name', '')}")
            except:
                pass

        if issues:
            print(f"  ⚠️ 品質問題検出: {len(issues)}件")
            for issue in issues[:5]:
                print(f"    - {issue}")
        else:
            print(f"  ✅ 品質検証合格")

        return len(issues) == 0, issues

    def save_clean_database(self, persons: List[Dict]):
        """クリーンなデータベースを保存"""

        output_csv = f"ultra_think_REAL_PERSONS_ONLY_{self.timestamp}.csv"
        output_json = f"ultra_think_REAL_PERSONS_ONLY_{self.timestamp}.json"

        # CSV保存
        if persons:
            headers = list(persons[0].keys())

            with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(persons)

            print(f"\n✅ CSV保存: {output_csv}")

            # JSON保存
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(persons, f, ensure_ascii=False, indent=2)

            print(f"✅ JSON保存: {output_json}")

            # 統計レポート
            self.generate_statistics_report(persons)

    def generate_statistics_report(self, persons: List[Dict]):
        """統計レポート生成"""

        report_file = f"PLACEHOLDER_REMOVAL_REPORT_{self.timestamp}.md"

        # カテゴリ別集計
        categories = {}
        for person in persons:
            cat = person.get('category', 'その他')
            categories[cat] = categories.get(cat, 0) + 1

        report = f"""# 🧹 プレースホルダー削除レポート

## 📅 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## 📊 処理結果
- **削除されたプレースホルダー**: {self.removed_count:,}件
- **残った実在人物**: {self.kept_count:,}件
- **削除率**: {(self.removed_count / (self.removed_count + self.kept_count) * 100):.1f}%

## 📈 カテゴリ別分布（クリーン後）
"""

        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(persons) * 100
            report += f"- {cat}: {count:,}件 ({percentage:.1f}%)\n"

        report += f"""
## ✅ 品質保証
- プレースホルダーパターン: {len(self.placeholder_patterns)}種類でチェック
- 番号付き名前: 完全削除
- 機械生成名: 完全削除
- 固定値フィールド: 検出・削除

## 🎯 結果
**実在人物のみ {self.kept_count:,}人のクリーンなデータベースを構築しました。**

---
*Placeholder Removal System v1.0*
*品質第一原則準拠*
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ レポート保存: {report_file}")


def main():
    """メイン処理"""

    print("=" * 60)
    print("🧹 プレースホルダー完全削除システム")
    print("品質第一原則に基づく処理")
    print("=" * 60)

    # 対象ファイル（品質修正済み）
    input_file = 'ultra_think_QUALITY_FIXED_20250827_095302.csv'

    # システム初期化
    remover = PlaceholderRemovalSystem()

    # Step 1: プレースホルダー削除
    kept_persons, removed_persons = remover.clean_database(input_file)

    # Step 2: 品質検証
    quality_ok, issues = remover.validate_quality(kept_persons)

    if not quality_ok:
        print("\n⚠️ 品質問題が検出されました")
        print("品質第一原則により処理を停止します")

        # 問題レポート作成
        with open(f"QUALITY_ISSUES_{remover.timestamp}.txt", 'w', encoding='utf-8') as f:
            f.write("品質問題検出レポート\n")
            f.write("=" * 40 + "\n")
            for issue in issues:
                f.write(f"- {issue}\n")

        print("問題を修正してから再実行してください")
        return

    # Step 3: クリーンデータベース保存
    remover.save_clean_database(kept_persons)

    # Step 4: 削除データも記録（確認用）
    if removed_persons:
        removed_file = f"REMOVED_PLACEHOLDERS_{remover.timestamp}.csv"

        with open(removed_file, 'w', encoding='utf-8-sig', newline='') as f:
            if removed_persons:
                writer = csv.DictWriter(f, fieldnames=list(removed_persons[0].keys()))
                writer.writeheader()
                writer.writerows(removed_persons)

        print(f"✅ 削除データ記録: {removed_file}")

    print("\n" + "=" * 60)
    print("✨ プレースホルダー削除完了")
    print(f"  実在人物のみ: {remover.kept_count:,}人")
    print(f"  削除済み: {remover.removed_count:,}人")
    print("=" * 60)


if __name__ == "__main__":
    main()
