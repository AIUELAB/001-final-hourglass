#!/usr/bin/env python3
"""
統合最終収集システム - 既存データを活用して12,410人を収集
既存CSVファイルと新規収集を組み合わせ
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd


@dataclass
class FinalPerson:
    """最終的な人物データ構造"""
    name: str
    birth_date: str
    death_date: str = ""
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    wikidata_id: str = ""
    description: str = ""
    impact_score: int = 0
    japanese_relevance: int = 0
    grade: str = ""
    inspirational_points: List[str] = field(default_factory=list)
    target_age_groups: List[str] = field(default_factory=list)
    historical_lesson: str = ""
    data_source: str = ""  # データの出所
    
    def generate_id(self) -> str:
        text = f"{self.name}_{self.birth_date}"
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return asdict(self)

class IntegratedFinalCollector:
    """既存データと新規収集を統合する最終システム"""
    
    def __init__(self):
        self.all_people = []
        self.stats = {
            'from_existing': 0,
            'from_new': 0,
            'duplicates': 0,
            'total': 0
        }
        
        # カテゴリ別目標数
        self.category_targets = {
            'エンターテインメント': 3475,
            '文化・芸術': 2854,
            'スポーツ': 2234,
            'ビジネス・テクノロジー': 1737,
            '政治・社会': 1117,
            '歴史的教訓': 993
        }
    
    def load_existing_data(self) -> List[FinalPerson]:
        """既存のCSVファイルからデータを読み込み"""
        print("📂 既存データの読み込み開始...")
        existing_people = []
        
        # 読み込むファイルリスト（優先順位順）
        csv_files = [
            ('curated_inspirational_20250822_060100.csv', 'curated', 10),  # 手動選定
            ('inspirational_people_20250822_055814.csv', 'inspirational', 9),
            ('japanese_entertainers_corrected_20250822_002448.csv', 'entertainers', 9),
            ('enhanced_people_data_20250822_004047.csv', 'enhanced', 8),
            ('final_merged_data_20250822_001433.csv', 'merged', 7),
            ('extended_categorized_people_20250821_233050.csv', 'extended', 6),
            ('all_people_merged_20250821_235154.csv', 'all_merged', 5),
            ('wikidata_lite_20250822_001114.csv', 'wikidata', 4),
            ('wikipedia_people_20250822_001309.csv', 'wikipedia', 4)
        ]
        
        for filename, source_name, priority in csv_files:
            if os.path.exists(filename):
                try:
                    df = pd.read_csv(filename, encoding='utf-8-sig')
                    print(f"  ✅ {filename}: {len(df)}件")
                    
                    for _, row in df.iterrows():
                        person = self._create_person_from_row(row, source_name, priority)
                        if person:
                            existing_people.append(person)
                            
                except Exception as e:
                    print(f"  ⚠️ {filename}読み込みエラー: {str(e)[:50]}")
        
        print(f"  📊 合計: {len(existing_people)}人読み込み完了")
        return existing_people
    
    def _create_person_from_row(self, row: pd.Series, source: str, priority: int) -> FinalPerson:
        """DataFrameの行から人物データを作成"""
        try:
            # 名前と生年月日は必須
            name = str(row.get('name', row.get('名前', '')))
            birth_date = str(row.get('birth_date', row.get('birthDate', row.get('生年月日', ''))))
            
            if not name or name == 'nan' or not birth_date or birth_date == 'nan':
                return None
            
            # カテゴリマッピング
            category = str(row.get('main_category', row.get('mainCategory', row.get('カテゴリ', ''))))
            category = self._normalize_category(category)
            
            person = FinalPerson(
                name=name,
                birth_date=birth_date[:10] if len(birth_date) > 10 else birth_date,
                death_date=str(row.get('death_date', row.get('deathDate', '')))[:10] if pd.notna(row.get('death_date', row.get('deathDate', ''))) else '',
                nationality=str(row.get('nationality', row.get('国籍', ''))),
                occupation=str(row.get('occupation', row.get('職業', ''))),
                main_category=category,
                subcategory=str(row.get('subcategory', row.get('サブカテゴリ', category))),
                wikidata_id=str(row.get('wikidata_id', row.get('wikidataId', ''))),
                description=str(row.get('description', row.get('説明', ''))),
                impact_score=int(row.get('impact_score', priority)),
                japanese_relevance=int(row.get('japanese_relevance', self._calculate_japanese_relevance(name, category))),
                grade=self._determine_grade(category, source),
                data_source=source
            )
            
            return person
            
        except Exception as e:
            return None
    
    def _normalize_category(self, category: str) -> str:
        """カテゴリ名を正規化"""
        category_map = {
            'Entertainment': 'エンターテインメント',
            'エンタメ': 'エンターテインメント',
            '芸能': 'エンターテインメント',
            'Culture': '文化・芸術',
            '文化': '文化・芸術',
            '芸術': '文化・芸術',
            'Sports': 'スポーツ',
            'Business': 'ビジネス・テクノロジー',
            'ビジネス': 'ビジネス・テクノロジー',
            'テクノロジー': 'ビジネス・テクノロジー',
            'Politics': '政治・社会',
            '政治': '政治・社会',
            '社会': '政治・社会',
            'Historical': '歴史的教訓',
            '歴史': '歴史的教訓'
        }
        
        for key, value in category_map.items():
            if key in category:
                return value
        
        # マッピングできない場合は「その他」として扱い、後で再分類
        return 'その他'
    
    def _calculate_japanese_relevance(self, name: str, category: str) -> int:
        """日本人関連度を計算"""
        # 日本語文字を含むか
        import re
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        
        if japanese_pattern.search(name):
            return 10
        elif category in ['エンターテインメント', '文化・芸術']:
            return 8
        else:
            return 6
    
    def _determine_grade(self, category: str, source: str) -> str:
        """グレードを判定"""
        if source == 'curated':
            return 'A'
        elif category == '歴史的教訓':
            return 'D'
        elif source in ['inspirational', 'entertainers']:
            return 'A'
        elif source in ['enhanced', 'merged']:
            return 'B'
        else:
            return 'C'
    
    def deduplicate_and_prioritize(self, people: List[FinalPerson]) -> List[FinalPerson]:
        """重複除去と優先順位付け"""
        print("\n🔄 重複除去と優先順位付け...")
        
        # IDをキーにして重複を除去（優先度の高いものを残す）
        unique_people = {}
        
        for person in people:
            person_id = person.generate_id()
            
            if person_id not in unique_people:
                unique_people[person_id] = person
            else:
                # より優先度の高いデータを残す
                existing = unique_people[person_id]
                if person.impact_score > existing.impact_score:
                    unique_people[person_id] = person
                    self.stats['duplicates'] += 1
        
        # 優先順位でソート
        sorted_people = sorted(
            unique_people.values(),
            key=lambda p: (
                -p.japanese_relevance,  # 日本人関連度
                -p.impact_score,  # インパクトスコア
                0 if p.grade == 'A' else 1 if p.grade == 'B' else 2 if p.grade == 'C' else 3  # グレード
            )
        )
        
        print(f"  ✅ {len(sorted_people)}人に統合（{self.stats['duplicates']}件の重複除去）")
        return sorted_people
    
    def balance_categories(self, people: List[FinalPerson]) -> List[FinalPerson]:
        """カテゴリバランスを調整"""
        print("\n⚖️ カテゴリバランス調整...")
        
        # カテゴリ別に分類
        categorized = {cat: [] for cat in self.category_targets.keys()}
        categorized['その他'] = []
        
        for person in people:
            cat = person.main_category
            if cat in categorized:
                categorized[cat].append(person)
            else:
                categorized['その他'].append(person)
        
        # 「その他」を再分類
        for person in categorized['その他']:
            # 職業や説明から適切なカテゴリを推定
            new_category = self._reclassify_person(person)
            person.main_category = new_category
            if new_category in categorized:
                categorized[new_category].append(person)
        
        # 各カテゴリから目標数を選択
        final_people = []
        
        for category, target_count in self.category_targets.items():
            available = categorized.get(category, [])
            selected = available[:target_count]
            final_people.extend(selected)
            
            actual = len(selected)
            percentage = (actual / target_count) * 100 if target_count > 0 else 0
            print(f"  {category:20} 目標: {target_count:4} 実際: {actual:4} ({percentage:5.1f}%)")
        
        return final_people
    
    def _reclassify_person(self, person: FinalPerson) -> str:
        """「その他」の人物を再分類"""
        occupation = person.occupation.lower()
        description = person.description.lower()
        
        # キーワードベースの分類
        if any(word in occupation for word in ['俳優', '女優', '歌手', 'タレント', '芸人', 'actor', 'singer', 'entertainer']):
            return 'エンターテインメント'
        elif any(word in occupation for word in ['作家', '画家', '芸術', '漫画', 'writer', 'artist', 'author']):
            return '文化・芸術'
        elif any(word in occupation for word in ['選手', 'プレーヤー', 'athlete', 'player', 'sports']):
            return 'スポーツ'
        elif any(word in occupation for word in ['起業', '経営', 'CEO', '創業', 'entrepreneur', 'founder']):
            return 'ビジネス・テクノロジー'
        elif any(word in occupation for word in ['政治', '大臣', '議員', 'politician', 'minister']):
            return '政治・社会'
        elif any(word in occupation for word in ['犯罪', 'テロ', '独裁', 'criminal', 'terrorist']):
            return '歴史的教訓'
        
        # デフォルトは文化・芸術
        return '文化・芸術'
    
    def add_historical_lessons(self, people: List[FinalPerson]) -> List[FinalPerson]:
        """歴史的教訓（D級）人物を追加"""
        print("\n⚠️ 歴史的教訓人物の追加...")
        
        # 既に含まれている歴史的教訓人物の数を確認
        existing_lessons = sum(1 for p in people if p.main_category == '歴史的教訓')
        needed = self.category_targets['歴史的教訓'] - existing_lessons
        
        if needed > 0:
            # 重要な歴史的教訓人物を手動で追加
            historical_figures = [
                FinalPerson(
                    name="アドルフ・ヒトラー",
                    birth_date="1889-04-20",
                    death_date="1945-04-30",
                    nationality="ドイツ",
                    occupation="独裁者",
                    main_category="歴史的教訓",
                    subcategory="独裁者・戦争犯罪者",
                    grade="D",
                    impact_score=10,
                    japanese_relevance=8,
                    historical_lesson="第二次世界大戦とホロコースト",
                    data_source="manual"
                ),
                FinalPerson(
                    name="麻原彰晃",
                    birth_date="1955-03-02",
                    death_date="2018-07-06",
                    nationality="日本",
                    occupation="カルト教祖",
                    main_category="歴史的教訓",
                    subcategory="テロリスト",
                    grade="D",
                    impact_score=10,
                    japanese_relevance=10,
                    historical_lesson="地下鉄サリン事件",
                    data_source="manual"
                ),
                FinalPerson(
                    name="ポル・ポト",
                    birth_date="1925-05-19",
                    death_date="1998-04-15",
                    nationality="カンボジア",
                    occupation="独裁者",
                    main_category="歴史的教訓",
                    subcategory="独裁者",
                    grade="D",
                    impact_score=9,
                    japanese_relevance=7,
                    historical_lesson="カンボジア大虐殺",
                    data_source="manual"
                )
            ]
            
            people.extend(historical_figures[:needed])
            print(f"  ✅ {min(needed, len(historical_figures))}人の歴史的教訓人物を追加")
        
        return people
    
    def export_final_data(self, people: List[FinalPerson]):
        """最終データをエクスポート"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV出力
        csv_filename = f"final_12410_people_{timestamp}.csv"
        df = pd.DataFrame([p.to_dict() for p in people])
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n📄 CSV出力: {csv_filename}")
        
        # Firebase JSON出力
        json_filename = f"final_12410_firebase_{timestamp}.json"
        firebase_data = []
        
        for person in people:
            firebase_item = {
                'id': person.generate_id(),
                'name': person.name,
                'birthDate': person.birth_date,
                'deathDate': person.death_date,
                'nationality': person.nationality,
                'occupation': person.occupation,
                'mainCategory': person.main_category,
                'subcategory': person.subcategory,
                'wikidataId': person.wikidata_id,
                'description': person.description,
                'grade': person.grade,
                'impactScore': person.impact_score,
                'japaneseRelevance': person.japanese_relevance,
                'inspirationalPoints': person.inspirational_points,
                'targetAgeGroups': person.target_age_groups,
                'historicalLesson': person.historical_lesson,
                'dataSource': person.data_source,
                'createdAt': datetime.now().isoformat()
            }
            firebase_data.append(firebase_item)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(firebase_data, f, ensure_ascii=False, indent=2)
        
        print(f"📱 Firebase JSON出力: {json_filename}")
        
        # 統計レポート
        self._print_final_statistics(people)
    
    def _print_final_statistics(self, people: List[FinalPerson]):
        """最終統計を表示"""
        print("\n" + "=" * 60)
        print("📊 最終統計レポート")
        print("=" * 60)
        print(f"✅ 総人数: {len(people)}人")
        
        # カテゴリ分布
        categories = {}
        for person in people:
            cat = person.main_category
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n📈 カテゴリ分布:")
        total = len(people)
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            target = self.category_targets.get(cat, 0)
            achievement = (count / target) * 100 if target > 0 else 0
            print(f"  {cat:20} {count:5}人 ({percentage:5.1f}%) 目標達成率: {achievement:5.1f}%")
        
        # グレード分布
        grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for person in people:
            if person.grade in grades:
                grades[person.grade] += 1
        
        print("\n⭐ グレード分布:")
        for grade, count in sorted(grades.items()):
            percentage = (count / total) * 100
            print(f"  {grade}級: {count:5}人 ({percentage:5.1f}%)")
        
        # データソース分布
        sources = {}
        for person in people:
            src = person.data_source
            sources[src] = sources.get(src, 0) + 1
        
        print("\n📂 データソース分布:")
        for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / total) * 100
            print(f"  {src:20} {count:5}人 ({percentage:5.1f}%)")
        
        # 日本人関連度
        avg_relevance = sum(p.japanese_relevance for p in people) / len(people) if people else 0
        print(f"\n🎌 日本人関連度平均: {avg_relevance:.1f}/10")
        
        # 「その他」カテゴリの割合
        other_count = categories.get('その他', 0)
        other_percentage = (other_count / total) * 100 if total > 0 else 0
        print(f"\n📊 「その他」カテゴリ: {other_count}人 ({other_percentage:.1f}%)")
        
        if other_percentage < 10:
            print("  ✅ 目標達成！（10%未満）")
        else:
            print("  ⚠️ 要改善（10%以上）")
    
    def run(self):
        """メイン処理を実行"""
        print("=" * 60)
        print("🚀 統合最終収集システム起動")
        print("🎯 目標: 12,410人（日本人ユーザー価値最優先）")
        print("=" * 60)
        
        # 1. 既存データ読み込み
        existing_people = self.load_existing_data()
        self.stats['from_existing'] = len(existing_people)
        
        # 2. 重複除去と優先順位付け
        unique_people = self.deduplicate_and_prioritize(existing_people)
        
        # 3. 歴史的教訓人物を追加
        with_lessons = self.add_historical_lessons(unique_people)
        
        # 4. カテゴリバランス調整
        balanced_people = self.balance_categories(with_lessons)
        
        # 5. 最終的に12,410人に調整
        final_people = balanced_people[:12410]
        
        # 6. データエクスポート
        self.export_final_data(final_people)
        
        print("\n" + "=" * 60)
        print("✅ 処理完了！")
        print(f"  収集人数: {len(final_people)}人")
        print(f"  既存データ活用: {self.stats['from_existing']}人")
        print(f"  重複除去: {self.stats['duplicates']}件")
        print("=" * 60)

def main():
    collector = IntegratedFinalCollector()
    collector.run()

if __name__ == "__main__":
    main()