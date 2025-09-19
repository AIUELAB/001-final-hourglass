#!/usr/bin/env python3
"""
Firebase Episodesにあってfinal_clean_databaseにない317名の歴史的人物をCSV出力
Export 317 missing historical figures from Firebase Episodes to CSV
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Set
import unicodedata

class MissingPersonsExporter:
    """Firebase Episodesの欠落人物CSV出力"""
    
    def __init__(self):
        self.episodes_persons = {}
        self.final_db_persons = set()
        self.missing_persons = []
    
    def normalize_name(self, name: str) -> str:
        """名前を正規化"""
        if not name:
            return ""
        
        # Unicode正規化
        name = unicodedata.normalize('NFKC', name)
        
        # 空白と記号を統一
        name = name.strip()
        name = name.replace('　', ' ')
        name = name.replace('・', '·')
        
        return name
    
    def load_episodes(self, episodes_file: str):
        """Firebase Episodesデータを読み込み"""
        print("📖 Firebase Episodes読み込み中...")
        
        with open(episodes_file, 'r', encoding='utf-8') as f:
            episodes = json.load(f)
        
        # エピソードから人物を抽出
        for episode in episodes:
            if isinstance(episode, dict):
                # 人物名フィールドを確認
                person_name = None
                for field in ['person_name', 'person_name_ja', 'person_name_display']:
                    if field in episode and episode[field]:
                        person_name = self.normalize_name(episode[field])
                        break
                
                if person_name:
                    if person_name not in self.episodes_persons:
                        self.episodes_persons[person_name] = {
                            'name': person_name,
                            'original_name': episode.get('person_name', ''),
                            'name_ja': episode.get('person_name_ja', ''),
                            'display_name': episode.get('person_name_display', ''),
                            'episodes': [],
                            'count': 0
                        }
                    
                    self.episodes_persons[person_name]['episodes'].append(episode.get('id', ''))
                    self.episodes_persons[person_name]['count'] += 1
        
        print(f"  ✅ {len(self.episodes_persons)}名の人物を抽出")
    
    def load_final_database(self, db_file: str):
        """Final databaseを読み込み"""
        print("📖 Final Database読み込み中...")
        
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 全ての名前フィールドを正規化して追加
        for key, person in data.items():
            if isinstance(person, dict):
                # 各種名前フィールドを確認
                for field in ['name', 'original_name', 'person_name_ja', 'display_name']:
                    if field in person and person[field]:
                        normalized = self.normalize_name(person[field])
                        if normalized:
                            self.final_db_persons.add(normalized)
        
        print(f"  ✅ {len(self.final_db_persons)}個のユニーク名を抽出")
    
    def find_missing_persons(self):
        """欠落している人物を特定"""
        print("\n🔍 欠落人物の分析中...")
        
        for person_name, person_data in self.episodes_persons.items():
            if person_name not in self.final_db_persons:
                self.missing_persons.append(person_data)
        
        # エピソード数でソート（多い順）
        self.missing_persons.sort(key=lambda x: x['count'], reverse=True)
        
        print(f"  ⚠️ {len(self.missing_persons)}名の欠落人物を発見")
    
    def export_to_csv(self, output_file: str):
        """CSVファイルに出力"""
        print(f"\n📝 CSV出力中: {output_file}")
        
        # CSVフィールド定義
        fieldnames = [
            'name',
            'original_name', 
            'name_ja',
            'display_name',
            'episode_count',
            'episode_ids'
        ]
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for person in self.missing_persons:
                writer.writerow({
                    'name': person['name'],
                    'original_name': person['original_name'],
                    'name_ja': person['name_ja'],
                    'display_name': person['display_name'],
                    'episode_count': person['count'],
                    'episode_ids': ', '.join(person['episodes'][:5])  # 最初の5個のエピソードID
                })
        
        print(f"  ✅ {len(self.missing_persons)}名の欠落人物をCSVに出力完了")
    
    def generate_report(self):
        """分析レポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"MISSING_PERSONS_REPORT_{timestamp}.md"
        
        report = f"""# 🔍 Firebase Episodes 欠落人物分析レポート

## 📊 サマリー
- **実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Firebase Episodes人物数**: {len(self.episodes_persons):,}名
- **Final Database照合済み**: {len(self.episodes_persons) - len(self.missing_persons):,}名
- **欠落人物数**: {len(self.missing_persons):,}名

## 🎯 欠落人物TOP 30（エピソード数順）
"""
        
        for i, person in enumerate(self.missing_persons[:30], 1):
            report += f"{i}. **{person['name']}**\n"
            if person['name_ja']:
                report += f"   - 日本語名: {person['name_ja']}\n"
            report += f"   - エピソード数: {person['count']}件\n\n"
        
        if len(self.missing_persons) > 30:
            report += f"\n... 他 {len(self.missing_persons) - 30}名\n"
        
        report += f"""
## 💡 分析結果
これらの人物がFinal Databaseに存在しない理由：
1. データ収集時に漏れた可能性
2. 重複排除プロセスで誤って削除された可能性
3. birth_year情報がないために削除された
4. 異なる名前表記で既に存在している可能性

## 📈 統計
- **平均エピソード数**: {sum(p['count'] for p in self.missing_persons) / len(self.missing_persons):.1f}件
- **最大エピソード数**: {max(p['count'] for p in self.missing_persons)}件
- **最小エピソード数**: {min(p['count'] for p in self.missing_persons)}件

---
*Firebase Episodes Missing Persons Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 詳細レポート: {report_file}")
        
        # コンソール出力
        print("\n" + "=" * 80)
        print("📊 欠落人物分析結果")
        print("=" * 80)
        print(f"Firebase Episodes人物数: {len(self.episodes_persons):,}名")
        print(f"Final Databaseに存在: {len(self.episodes_persons) - len(self.missing_persons):,}名")
        print(f"欠落人物数: {len(self.missing_persons):,}名")
        print(f"\n🔝 TOP 10 欠落人物（エピソード数順）:")
        for i, person in enumerate(self.missing_persons[:10], 1):
            print(f"  {i}. {person['name']} ({person['count']}エピソード)")


def main():
    """メイン実行"""
    exporter = MissingPersonsExporter()
    
    # データ読み込み
    exporter.load_episodes('firebase_episodes_complete_20250825_094949.json')
    exporter.load_final_database('final_clean_database_20250825_110858.json')
    
    # 欠落人物を特定
    exporter.find_missing_persons()
    
    # CSV出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"missing_persons_firebase_{timestamp}.csv"
    exporter.export_to_csv(csv_file)
    
    # レポート生成
    exporter.generate_report()
    
    print(f"\n✅ 完了!")
    print(f"  CSV: {csv_file}")
    print(f"  {len(exporter.missing_persons)}名の欠落人物を出力しました")


if __name__ == "__main__":
    main()