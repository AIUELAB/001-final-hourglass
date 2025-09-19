from src.secure_config import config
#!/usr/bin/env python3
"""
Firestore episodesコレクション完全エクスポートツール
Ultra Think: 包括的なデータ分析と最適化されたCSV出力
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict

import firebase_admin
from firebase_admin import credentials, firestore

# Firebase初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(config.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: Firebase service account key file not found")
        print("Firebaseコンソールからサービスアカウントキーをダウンロードしてください")
        exit(1)

db = firestore.client()

class FirebaseEpisodeExporter:
    """Firebase エピソード完全エクスポートクラス"""
    
    def __init__(self):
        self.episodes = []
        self.all_fields = set()
        self.stats = {
            'total_episodes': 0,
            'unique_persons': set(),
            'age_distribution': defaultdict(int),
            'year_distribution': defaultdict(int),
            'field_coverage': defaultdict(int),
            'data_quality': {
                'complete': 0,
                'partial': 0,
                'minimal': 0
            }
        }
    
    def fetch_all_episodes(self) -> List[Dict]:
        """全エピソードを取得"""
        print("🔄 Firestoreから全エピソードを取得中...")
        
        try:
            episodes_ref = db.collection('episodes')
            episodes_stream = episodes_ref.stream()
            
            for episode_doc in episodes_stream:
                episode_data = episode_doc.to_dict()
                episode_data['_document_id'] = episode_doc.id
                
                # 全フィールドを収集
                self.all_fields.update(episode_data.keys())
                
                # 統計情報を更新
                self._update_statistics(episode_data)
                
                self.episodes.append(episode_data)
                self.stats['total_episodes'] += 1
                
                # 進捗表示（100件ごと）
                if self.stats['total_episodes'] % 100 == 0:
                    print(f"  📊 {self.stats['total_episodes']}件処理済み...")
            
            print(f"✅ 取得完了: {self.stats['total_episodes']}件のエピソード")
            return self.episodes
            
        except Exception as e:
            print(f"❌ エラーが発生しました: {str(e)}")
            return []
    
    def _update_statistics(self, episode_data: Dict):
        """統計情報を更新"""
        # 人物名
        person_name = episode_data.get('person_name') or episode_data.get('person', 'Unknown')
        self.stats['unique_persons'].add(person_name)
        
        # 年齢分布
        age = episode_data.get('age')
        if age is not None:
            self.stats['age_distribution'][age] += 1
        
        # 年分布
        year = episode_data.get('year')
        if year:
            self.stats['year_distribution'][year] += 1
        
        # フィールドカバレッジ
        for field in episode_data.keys():
            self.stats['field_coverage'][field] += 1
        
        # データ品質評価
        field_count = len(episode_data)
        if field_count >= 10:
            self.stats['data_quality']['complete'] += 1
        elif field_count >= 5:
            self.stats['data_quality']['partial'] += 1
        else:
            self.stats['data_quality']['minimal'] += 1
    
    def export_to_csv(self, filename: str = None) -> str:
        """エピソードをCSVに出力（最適化版）"""
        if not self.episodes:
            print("⚠️ エクスポートするエピソードがありません")
            return None
        
        # ファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            filename = f"firebase_episodes_complete_{timestamp}.csv"
        
        print(f"\n📝 CSVファイル生成中: {filename}")
        
        # フィールドを重要度順にソート
        priority_fields = ['_document_id', 'person_name', 'person', 'age', 'year', 'month', 'day']
        content_fields = ['title', 'content', 'description', 'summary']
        metadata_fields = ['created_at', 'updated_at', 'source', 'category']
        
        # フィールドリストを構築
        ordered_fields = []
        
        # 優先フィールド
        for field in priority_fields:
            if field in self.all_fields:
                ordered_fields.append(field)
        
        # コンテンツフィールド
        for field in content_fields:
            if field in self.all_fields:
                ordered_fields.append(field)
        
        # メタデータフィールド
        for field in metadata_fields:
            if field in self.all_fields:
                ordered_fields.append(field)
        
        # その他のフィールド（アルファベット順）
        remaining_fields = sorted(self.all_fields - set(ordered_fields))
        ordered_fields.extend(remaining_fields)
        
        # CSV書き込み（UTF-8 BOM付き）
        with open(filename, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ordered_fields, extrasaction='ignore')
            writer.writeheader()
            
            # データをソート（年齢 → 人物名）
            sorted_episodes = sorted(self.episodes, 
                                   key=lambda x: (
                                       x.get('age', 999),
                                       x.get('person_name', x.get('person', 'ZZZ'))
                                   ))
            
            for episode in sorted_episodes:
                # 欠損値を空文字で埋める
                row = {field: episode.get(field, '') for field in ordered_fields}
                
                # 長いテキストフィールドの処理
                for field in ['content', 'description', 'summary']:
                    if field in row and isinstance(row[field], str) and len(row[field]) > 1000:
                        row[field] = row[field][:997] + "..."
                
                writer.writerow(row)
        
        print(f"✅ CSV出力完了: {filename}")
        return filename
    
    def export_to_json(self, filename: str = None) -> str:
        """JSON形式でバックアップ"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            filename = f"firebase_episodes_complete_{timestamp}.json"
        
        print(f"\n💾 JSONバックアップ作成中: {filename}")
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.episodes, jsonfile, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ JSON保存完了: {filename}")
        return filename
    
    def generate_analysis_report(self) -> str:
        """分析レポート生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"FIREBASE_EPISODES_ANALYSIS_{timestamp}.md"
        
        report = f"""# Firebase Episodes コレクション分析レポート

## 📊 基本統計
- **生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **総エピソード数**: {self.stats['total_episodes']:,}件
- **ユニーク人物数**: {len(self.stats['unique_persons'])}人
- **フィールド総数**: {len(self.all_fields)}個

## 👥 人物分布（上位20名）
"""
        
        # 人物ごとのエピソード数を集計
        person_counts = defaultdict(int)
        for episode in self.episodes:
            person = episode.get('person_name') or episode.get('person', 'Unknown')
            person_counts[person] += 1
        
        sorted_persons = sorted(person_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (person, count) in enumerate(sorted_persons[:20], 1):
            percentage = count / self.stats['total_episodes'] * 100
            report += f"{i:2}. {person}: {count}件 ({percentage:.1f}%)\n"
        
        report += f"\n## 📈 年齢分布\n"
        if self.stats['age_distribution']:
            sorted_ages = sorted(self.stats['age_distribution'].items())
            for age, count in sorted_ages[:20]:  # 最初の20歳まで
                bar = '█' * min(int(count/10), 50)
                report += f"年齢 {age:3}: {count:4}件 {bar}\n"
        
        report += f"\n## 🔍 データ品質\n"
        report += f"- **完全** (10+フィールド): {self.stats['data_quality']['complete']}件\n"
        report += f"- **部分** (5-9フィールド): {self.stats['data_quality']['partial']}件\n"
        report += f"- **最小** (<5フィールド): {self.stats['data_quality']['minimal']}件\n"
        
        report += f"\n## 📝 フィールドカバレッジ\n"
        sorted_fields = sorted(self.stats['field_coverage'].items(), 
                             key=lambda x: x[1], reverse=True)
        for field, count in sorted_fields[:20]:
            coverage = count / self.stats['total_episodes'] * 100
            report += f"- {field}: {count}件 ({coverage:.1f}%)\n"
        
        report += f"""
## 🎯 カバー率分析
- **必要エピソード数**: 37,230件（102歳 × 365日）
- **現在のエピソード数**: {self.stats['total_episodes']:,}件
- **カバー率**: {self.stats['total_episodes'] / 37230 * 100:.2f}%
- **不足数**: {max(0, 37230 - self.stats['total_episodes']):,}件

## 📁 出力ファイル
- CSVファイル: `firebase_episodes_complete_{timestamp}.csv`
- JSONバックアップ: `firebase_episodes_complete_{timestamp}.json`
- 分析レポート: `{report_filename}`

---
*Ultra Think Analysis Complete*
"""
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 分析レポート生成: {report_filename}")
        return report_filename
    
    def display_summary(self):
        """サマリー表示"""
        print("\n" + "=" * 60)
        print("📊 エクスポート完了サマリー")
        print("=" * 60)
        print(f"✅ 総エピソード数: {self.stats['total_episodes']:,}件")
        print(f"✅ ユニーク人物数: {len(self.stats['unique_persons'])}人")
        print(f"✅ フィールド数: {len(self.all_fields)}個")
        print(f"✅ カバー率: {self.stats['total_episodes'] / 37230 * 100:.2f}%")
        
        # データ品質
        total = sum(self.stats['data_quality'].values())
        if total > 0:
            complete_pct = self.stats['data_quality']['complete'] / total * 100
            print(f"✅ データ品質（完全）: {complete_pct:.1f}%")

def main():
    """メイン実行"""
    print("🚀 Firebase Episodes 完全エクスポートツール (Ultra Think)")
    print("=" * 60)
    
    exporter = FirebaseEpisodeExporter()
    
    # 全エピソード取得
    episodes = exporter.fetch_all_episodes()
    
    if episodes:
        # CSV出力
        csv_file = exporter.export_to_csv()
        
        # JSONバックアップ
        json_file = exporter.export_to_json()
        
        # 分析レポート生成
        report_file = exporter.generate_analysis_report()
        
        # サマリー表示
        exporter.display_summary()
        
        print("\n🎉 全処理完了！")
        print(f"\n📦 生成ファイル:")
        print(f"  1. CSV: {csv_file}")
        print(f"  2. JSON: {json_file}")
        print(f"  3. レポート: {report_file}")
        print("\n💡 CSVファイルはExcelで直接開けます（UTF-8 BOM付き）")
    else:
        print("\n⚠️ エピソードの取得に失敗しました")

if __name__ == "__main__":
    main()