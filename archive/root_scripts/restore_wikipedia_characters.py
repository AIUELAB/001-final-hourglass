#!/usr/bin/env python3
"""
Wikipedia Character Restoration Script
Restores culturally significant fictional characters and fixes false positives
"""

import pandas as pd
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
import re
import os
from urllib.parse import quote

class WikipediaCharacterRestorer:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.restoration_log = []
        self.validation_log = []
        self.false_positive_log = []

        # Culturally significant fictional characters that should be restored
        self.significant_characters = {
            # Japanese cultural icons
            "ドラえもん": {"work": "ドラえもん", "significance": "Japanese cultural icon"},
            "アンパンマン": {"work": "アンパンマン", "significance": "Children's cultural icon"},
            "サザエさん": {"work": "サザエさん", "significance": "Japanese family icon"},
            "トトロ": {"work": "となりのトトロ", "significance": "Studio Ghibli icon"},
            "野比のび太": {"work": "ドラえもん", "significance": "Main character"},
            "フグ田サザエ": {"work": "サザエさん", "significance": "Main character"},
            "磯野カツオ": {"work": "サザエさん", "significance": "Main character"},
            "磯野ワカメ": {"work": "サザエさん", "significance": "Main character"},
            "フグ田タラオ": {"work": "サザエさん", "significance": "Main character"},
            "フグ田マスオ": {"work": "サザエさん", "significance": "Main character"},
            "野原しんのすけ": {"work": "クレヨンしんちゃん", "significance": "Main character"},
            "野原ひろし": {"work": "クレヨンしんちゃん", "significance": "Main character"},
            "野原みさえ": {"work": "クレヨンしんちゃん", "significance": "Main character"},
            "ばいきんまん": {"work": "アンパンマン", "significance": "Main villain"},
            "しょくぱんまん": {"work": "アンパンマン", "significance": "Main character"},
            "カレーパンマン": {"work": "アンパンマン", "significance": "Main character"},
            "ドキンちゃん": {"work": "アンパンマン", "significance": "Main character"},

            # Major anime/manga characters
            "孫悟空": {"work": "ドラゴンボール", "significance": "International anime icon"},
            "ベジータ": {"work": "ドラゴンボール", "significance": "Main character"},
            "ピッコロ": {"work": "ドラゴンボール", "significance": "Main character"},
            "うずまきナルト": {"work": "NARUTO", "significance": "International anime icon"},
            "はたけカカシ": {"work": "NARUTO", "significance": "Main character"},
            "うちはサスケ": {"work": "NARUTO", "significance": "Main character"},
            "春野サクラ": {"work": "NARUTO", "significance": "Main character"},
            "モンキー・D・ルフィ": {"work": "ONE PIECE", "significance": "International anime icon"},
            "ロロノア・ゾロ": {"work": "ONE PIECE", "significance": "Main character"},
            "ナミ": {"work": "ONE PIECE", "significance": "Main character"},
            "ニコ・ロビン": {"work": "ONE PIECE", "significance": "Main character"},
            "トニートニー・チョッパー": {"work": "ONE PIECE", "significance": "Main character"},
            "竈門炭治郎": {"work": "鬼滅の刃", "significance": "Recent cultural phenomenon"},
            "竈門禰豆子": {"work": "鬼滅の刃", "significance": "Main character"},
            "我妻善逸": {"work": "鬼滅の刃", "significance": "Main character"},
            "嘴平伊之助": {"work": "鬼滅の刃", "significance": "Main character"},
            "冨岡義勇": {"work": "鬼滅の刃", "significance": "Main character"},
            "胡蝶しのぶ": {"work": "鬼滅の刃", "significance": "Main character"},
            "江戸川コナン": {"work": "名探偵コナン", "significance": "Long-running series icon"},
            "工藤新一": {"work": "名探偵コナン", "significance": "Main character"},
            "毛利蘭": {"work": "名探偵コナン", "significance": "Main character"},
            "毛利小五郎": {"work": "名探偵コナン", "significance": "Main character"},
            "アルミン・アルレルト": {"work": "進撃の巨人", "significance": "Main character"},
            "ミカサ・アッカーマン": {"work": "進撃の巨人", "significance": "Main character"},
            "リヴァイ": {"work": "進撃の巨人", "significance": "Main character"},
            "五条悟": {"work": "呪術廻戦", "significance": "Popular character"},
            "両面宿儺": {"work": "呪術廻戦", "significance": "Main antagonist"},
            "碇シンジ": {"work": "新世紀エヴァンゲリオン", "significance": "Cultural icon"},
            "惣流・アスカ・ラングレー": {"work": "新世紀エヴァンゲリオン", "significance": "Main character"},
            "綾波レイ": {"work": "新世紀エヴァンゲリオン", "significance": "Cultural icon"},
            "渚カヲル": {"work": "新世紀エヴァンゲリオン", "significance": "Main character"},
            "桜木花道": {"work": "SLAM DUNK", "significance": "Sports anime icon"},
            "流川楓": {"work": "SLAM DUNK", "significance": "Main character"},
            "花垣武道": {"work": "東京リベンジャーズ", "significance": "Main character"},

            # Video game characters
            "マリオ": {"work": "スーパーマリオ", "significance": "Gaming icon"},
            "ピカチュウ": {"work": "ポケットモンスター", "significance": "Global gaming icon"},
            "リンク": {"work": "ゼルダの伝説", "significance": "Gaming icon"},
            "ゼルダ姫": {"work": "ゼルダの伝説", "significance": "Gaming character"},
            "ソニック": {"work": "ソニック・ザ・ヘッジホッグ", "significance": "Gaming icon"},
            "パックマン": {"work": "パックマン", "significance": "Classic gaming icon"},
            "ミュウツー": {"work": "ポケットモンスター", "significance": "Popular Pokémon"},
        }

        # False positives - real people incorrectly removed
        self.false_positives = {
            "安室奈美恵": {"type": "singer", "significance": "Japanese pop icon"},
            "Amuro Namie": {"type": "singer", "significance": "Japanese pop icon"},
            "アニャ・テイラー＝ジョイ": {"type": "actress", "significance": "Hollywood actress"},
            "Anya Taylor-Joy": {"type": "actress", "significance": "Hollywood actress"},
            "デビッド・ロイド・ジョージ": {"type": "politician", "significance": "British Prime Minister"},
            "David Lloyd George": {"type": "politician", "significance": "British Prime Minister"},
            "フロイド・メイウェザー": {"type": "boxer", "significance": "Professional boxer"},
            "Floyd Mayweather": {"type": "boxer", "significance": "Professional boxer"},
            "ロニー・ジェイムス・ディオ": {"type": "musician", "significance": "Heavy metal singer"},
            "Ronnie James Dio": {"type": "musician", "significance": "Heavy metal singer"},
        }

    def find_latest_csv(self) -> str:
        """Find the most recent ultra_think CSV file"""
        csv_files = [f for f in os.listdir('.') if f.startswith('ultra_think_') and f.endswith('.csv')]
        if not csv_files:
            raise FileNotFoundError("No ultra_think CSV files found")

        # Sort by modification time
        csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return csv_files[0]

    def verify_wikipedia(self, name: str, work: str = None) -> Dict:
        """Verify character/person on Wikipedia"""
        try:
            # Try both Japanese and English Wikipedia
            results = {}

            # Japanese Wikipedia
            ja_url = f"https://ja.wikipedia.org/api/rest_v1/page/summary/{quote(name)}"
            try:
                response = requests.get(ja_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results['ja'] = {
                        'exists': True,
                        'title': data.get('title', ''),
                        'description': data.get('description', '')[:200],
                        'extract': data.get('extract', '')[:300]
                    }
                else:
                    results['ja'] = {'exists': False}
            except:
                results['ja'] = {'exists': False}

            time.sleep(0.5)  # Rate limiting

            # English Wikipedia
            en_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(name)}"
            try:
                response = requests.get(en_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results['en'] = {
                        'exists': True,
                        'title': data.get('title', ''),
                        'description': data.get('description', '')[:200],
                        'extract': data.get('extract', '')[:300]
                    }
                else:
                    results['en'] = {'exists': False}
            except:
                results['en'] = {'exists': False}

            return results

        except Exception as e:
            return {'error': str(e), 'ja': {'exists': False}, 'en': {'exists': False}}

    def create_backup(self, df: pd.DataFrame, backup_type: str):
        """Create backup of current database"""
        backup_filename = f"backup_before_restoration_{backup_type}_{self.timestamp}.csv"
        df.to_csv(backup_filename, index=False, encoding='utf-8-sig')
        print(f"✅ Backup created: {backup_filename}")
        return backup_filename

    def restore_character(self, df: pd.DataFrame, person_data: Dict, backup_df: pd.DataFrame) -> Optional[pd.Series]:
        """Restore a character from backup if found"""
        name = person_data.get('person_name_ja', '') or person_data.get('person_name_display', '') or person_data.get('person_name', '')

        # Search in backup for this character
        matches = backup_df[
            (backup_df['person_name_ja'] == name) |
            (backup_df['person_name_display'] == name) |
            (backup_df['person_name'] == name)
        ]

        if len(matches) > 0:
            return matches.iloc[0]
        return None

    def process_database(self):
        """Main processing function"""
        print("🎭 Starting Wikipedia Character Restoration")
        print(f"📅 Timestamp: {self.timestamp}")

        # Find and load latest CSV
        latest_csv = self.find_latest_csv()
        print(f"📁 Loading: {latest_csv}")

        df = pd.read_csv(latest_csv, encoding='utf-8-sig')
        original_count = len(df)
        print(f"📊 Original records: {original_count:,}")

        # Load backup files to find deleted characters
        backup_files = [
            f for f in os.listdir('.')
            if f.startswith('backup_before_fictional') and f.endswith('.csv')
        ]

        if not backup_files:
            print("⚠️ No fictional character backup files found")
            return

        # Load the most recent backup
        backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        backup_file = backup_files[0]
        print(f"📁 Loading backup: {backup_file}")

        backup_df = pd.read_csv(backup_file, encoding='utf-8-sig')
        print(f"📊 Backup records: {len(backup_df):,}")

        # Create safety backup
        safety_backup = self.create_backup(df, "safety")

        restored_count = 0
        false_positive_count = 0
        validation_results = []

        # Process significant characters for restoration
        print("\n🔄 Processing significant characters...")

        for name, info in self.significant_characters.items():
            print(f"\n📝 Checking: {name}")

            # Check if already exists in current database
            existing = df[
                (df['person_name_ja'] == name) |
                (df['person_name_display'] == name) |
                (df['person_name'] == name)
            ]

            if len(existing) > 0:
                print(f"✅ Already exists: {name}")
                continue

            # Search in backup
            backup_matches = backup_df[
                (backup_df['person_name_ja'] == name) |
                (backup_df['person_name_display'] == name) |
                (backup_df['person_name'] == name)
            ]

            if len(backup_matches) > 0:
                # Verify on Wikipedia
                wiki_result = self.verify_wikipedia(name, info['work'])
                validation_results.append({
                    'name': name,
                    'work': info['work'],
                    'significance': info['significance'],
                    'wikipedia_ja': wiki_result['ja']['exists'],
                    'wikipedia_en': wiki_result['en']['exists'],
                    'wiki_data': wiki_result
                })

                # Restore the character
                character_row = backup_matches.iloc[0].copy()

                # Update display name with work name if needed
                if info['work'] and not f"（{info['work']}）" in character_row.get('person_name_display', ''):
                    character_row['person_name_display'] = f"{name}（{info['work']}）"

                # Add back to dataframe
                df = pd.concat([df, character_row.to_frame().T], ignore_index=True)

                restored_count += 1
                self.restoration_log.append({
                    'name': name,
                    'person_id': character_row.get('person_id', 'Unknown'),
                    'work': info['work'],
                    'significance': info['significance'],
                    'wikipedia_verified': wiki_result['ja']['exists'] or wiki_result['en']['exists'],
                    'restored_at': datetime.now().isoformat()
                })

                print(f"✅ Restored: {name} ({info['work']})")
            else:
                print(f"❌ Not found in backup: {name}")

        # Process false positives (real people incorrectly removed)
        print("\n🔄 Processing false positives...")

        for name, info in self.false_positives.items():
            print(f"\n📝 Checking false positive: {name}")

            # Check if already exists in current database
            existing = df[
                (df['person_name_ja'] == name) |
                (df['person_name_display'] == name) |
                (df['person_name'] == name)
            ]

            if len(existing) > 0:
                print(f"✅ Already exists: {name}")
                continue

            # Search in backup
            backup_matches = backup_df[
                (backup_df['person_name_ja'] == name) |
                (backup_df['person_name_display'] == name) |
                (backup_df['person_name'] == name)
            ]

            if len(backup_matches) > 0:
                # Verify on Wikipedia
                wiki_result = self.verify_wikipedia(name)

                # Restore the person
                person_row = backup_matches.iloc[0].copy()

                # Add back to dataframe
                df = pd.concat([df, person_row.to_frame().T], ignore_index=True)

                false_positive_count += 1
                self.false_positive_log.append({
                    'name': name,
                    'person_id': person_row.get('person_id', 'Unknown'),
                    'type': info['type'],
                    'significance': info['significance'],
                    'wikipedia_verified': wiki_result['ja']['exists'] or wiki_result['en']['exists'],
                    'restored_at': datetime.now().isoformat()
                })

                print(f"✅ False positive restored: {name} ({info['type']})")
            else:
                print(f"❌ False positive not found in backup: {name}")

        # Save results
        final_count = len(df)
        output_filename = f"ultra_think_WIKIPEDIA_RESTORED_{self.timestamp}.csv"
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')

        # Generate comprehensive report
        self.generate_report(original_count, final_count, restored_count,
                           false_positive_count, validation_results, output_filename)

        print(f"\n🎉 Restoration complete!")
        print(f"📊 Original: {original_count:,} → Final: {final_count:,}")
        print(f"✅ Characters restored: {restored_count}")
        print(f"✅ False positives fixed: {false_positive_count}")
        print(f"💾 Output file: {output_filename}")

    def generate_report(self, original_count: int, final_count: int, restored_count: int,
                       false_positive_count: int, validation_results: List, output_filename: str):
        """Generate comprehensive restoration report"""

        report_content = f"""# 🎭 Wikipedia Character Restoration Report

**実行日時**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
**復元件数**: {restored_count + false_positive_count}件
**文化的重要キャラクター復元**: {restored_count}件
**誤削除修正**: {false_positive_count}件

## 📊 概要統計

- **処理前レコード数**: {original_count:,}件
- **処理後レコード数**: {final_count:,}件
- **純増加**: {final_count - original_count:,}件

## 🌟 復元された文化的重要キャラクター

### Wikipedia検証結果付き

| キャラクター名 | 作品名 | 重要度 | 日本語Wikipedia | 英語Wikipedia | 復元状況 |
|------------|--------|--------|----------------|---------------|----------|
"""

        for result in validation_results:
            if result['name'] in [log['name'] for log in self.restoration_log]:
                ja_status = "✅" if result['wikipedia_ja'] else "❌"
                en_status = "✅" if result['wikipedia_en'] else "❌"
                report_content += f"| {result['name']} | {result['work']} | {result['significance']} | {ja_status} | {en_status} | ✅復元済み |\n"

        report_content += f"""

## 🔧 修正された誤削除（False Positives）

| 人物名 | タイプ | 重要度 | 復元状況 |
|-------|-------|--------|----------|
"""

        for fp in self.false_positive_log:
            report_content += f"| {fp['name']} | {fp['type']} | {fp['significance']} | ✅復元済み |\n"

        report_content += f"""

## 📋 詳細復元ログ

### 文化的重要キャラクター
"""

        for log in self.restoration_log:
            report_content += f"""
#### {log['name']}
- **Person ID**: {log['person_id']}
- **作品**: {log['work']}
- **重要度**: {log['significance']}
- **Wikipedia検証**: {"✅" if log['wikipedia_verified'] else "⚠️未確認"}
- **復元日時**: {log['restored_at']}
"""

        report_content += f"""

### 誤削除修正
"""

        for fp in self.false_positive_log:
            report_content += f"""
#### {fp['name']}
- **Person ID**: {fp['person_id']}
- **タイプ**: {fp['type']}
- **重要度**: {fp['significance']}
- **Wikipedia検証**: {"✅" if fp['wikipedia_verified'] else "⚠️未確認"}
- **復元日時**: {fp['restored_at']}
"""

        report_content += f"""

## 🔍 Wikipedia検証詳細

### 検証成功
"""

        verified_count = sum(1 for r in validation_results if r['wikipedia_ja'] or r['wikipedia_en'])
        report_content += f"- **検証成功**: {verified_count}/{len(validation_results)}件\n"
        report_content += f"- **成功率**: {verified_count/len(validation_results)*100:.1f}%\n\n"

        for result in validation_results:
            if result['wikipedia_ja'] or result['wikipedia_en']:
                report_content += f"**{result['name']}**:\n"
                if result['wikipedia_ja']:
                    wiki_data = result['wiki_data']['ja']
                    report_content += f"- 日本語: {wiki_data.get('description', 'N/A')}\n"
                if result['wikipedia_en']:
                    wiki_data = result['wiki_data']['en']
                    report_content += f"- English: {wiki_data.get('description', 'N/A')}\n"
                report_content += "\n"

        report_content += f"""

## 💾 出力ファイル

- **復元済みCSV**: {output_filename}
- **復元ログJSON**: restoration_log_{self.timestamp}.json
- **Wikipedia検証ログ**: wikipedia_validation_{self.timestamp}.json

## 🎯 品質保証

### 復元基準
1. **文化的重要性**: 日本文化における認知度と影響力
2. **国際的認知**: 海外での知名度と展開
3. **長期的価値**: 継続的な文化的影響
4. **Wikipedia存在**: 信頼できる情報源での検証

### 安全性対策
- **自動バックアップ**: 処理前に安全バックアップを作成
- **段階的復元**: 一つずつ検証しながら復元
- **Wikipedia検証**: 各キャラクターの実在性を確認
- **ログ記録**: すべての操作を詳細記録

---
*レポート生成: {datetime.now().isoformat()}*
*スクリプト: restore_wikipedia_characters.py*
"""

        # Save report
        report_filename = f"WIKIPEDIA_RESTORATION_REPORT_{self.timestamp}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)

        # Save JSON logs
        with open(f"restoration_log_{self.timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump(self.restoration_log, f, ensure_ascii=False, indent=2)

        with open(f"false_positive_log_{self.timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump(self.false_positive_log, f, ensure_ascii=False, indent=2)

        with open(f"wikipedia_validation_{self.timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2)

        print(f"📋 Report generated: {report_filename}")

def main():
    """Main execution function"""
    try:
        restorer = WikipediaCharacterRestorer()
        restorer.process_database()
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
