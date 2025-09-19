#!/usr/bin/env python3
"""
最適化された有名人物収集システム
エピソード生成を削除し、人物収集のみに特化
目標: 12,410人を3時間で収集（コスト$0）
"""

import concurrent.futures
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests


@dataclass
class Person:
    """人物データの基本構造"""
    name: str
    birth_date: str
    death_date: str = ""
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    wikidata_id: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def generate_id(self) -> str:
        """一意なIDを生成"""
        text = f"{self.name}_{self.birth_date}"
        return hashlib.md5(text.encode()).hexdigest()[:16]

class OptimizedPersonCollector:
    """最適化された人物収集システム"""
    
    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.collected_people = {}
        self.stats = {
            'total_collected': 0,
            'duplicates_removed': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
    def collect_all_categories(self, target_count: int = 12410) -> List[Person]:
        """全カテゴリから人物を収集"""
        print("🚀 最適化版人物収集システム起動")
        print(f"🎯 目標: {target_count}人の有名人物（エピソード無し）")
        print("=" * 60)
        
        # カテゴリ別収集計画（合計12,410人）
        category_plan = [
            # スポーツ（2,000人）
            ("サッカー選手", "wd:Q937857", "スポーツ", 500),
            ("野球選手", "wd:Q10871364", "スポーツ", 400),
            ("バスケットボール選手", "wd:Q3665646", "スポーツ", 300),
            ("テニス選手", "wd:Q10833314", "スポーツ", 200),
            ("陸上選手", "wd:Q11513337", "スポーツ", 200),
            ("水泳選手", "wd:Q10843402", "スポーツ", 150),
            ("ゴルフ選手", "wd:Q13156709", "スポーツ", 150),
            ("ボクサー", "wd:Q11338576", "スポーツ", 100),
            
            # エンターテインメント（2,000人）
            ("俳優", "wd:Q33999", "エンターテインメント", 600),
            ("歌手", "wd:Q177220", "エンターテインメント", 500),
            ("映画監督", "wd:Q2526255", "エンターテインメント", 200),
            ("コメディアン", "wd:Q245068", "エンターテインメント", 200),
            ("ミュージシャン", "wd:Q639669", "エンターテインメント", 300),
            ("ダンサー", "wd:Q5716684", "エンターテインメント", 100),
            ("声優", "wd:Q622807", "エンターテインメント", 100),
            
            # ビジネス（1,500人）
            ("起業家", "wd:Q131524", "ビジネス", 500),
            ("CEO", "wd:Q484876", "ビジネス", 400),
            ("投資家", "wd:Q557880", "ビジネス", 300),
            ("実業家", "wd:Q43845", "ビジネス", 300),
            
            # 科学・学術（1,500人）
            ("科学者", "wd:Q901", "科学・学術", 400),
            ("物理学者", "wd:Q169470", "科学・学術", 200),
            ("化学者", "wd:Q593644", "科学・学術", 200),
            ("生物学者", "wd:Q864503", "科学・学術", 200),
            ("数学者", "wd:Q170790", "科学・学術", 200),
            ("医師", "wd:Q39631", "科学・学術", 150),
            ("教授", "wd:Q1622272", "科学・学術", 150),
            
            # 芸術・文化（1,500人）
            ("作家", "wd:Q36180", "文化・芸術", 400),
            ("画家", "wd:Q1028181", "文化・芸術", 300),
            ("彫刻家", "wd:Q1281618", "文化・芸術", 200),
            ("写真家", "wd:Q33231", "文化・芸術", 200),
            ("建築家", "wd:Q42973", "文化・芸術", 200),
            ("詩人", "wd:Q49757", "文化・芸術", 200),
            
            # デジタル・テクノロジー（1,000人）
            ("YouTuber", "wd:Q17125263", "テクノロジー", 300),
            ("プログラマー", "wd:Q5482740", "テクノロジー", 200),
            ("ゲーム開発者", "wd:Q4618975", "テクノロジー", 200),
            ("ブロガー", "wd:Q18545066", "テクノロジー", 150),
            ("インフルエンサー", "wd:Q54888449", "テクノロジー", 150),
            
            # 政治・社会（1,000人）
            ("政治家", "wd:Q82955", "政治・社会", 400),
            ("活動家", "wd:Q15253558", "政治・社会", 200),
            ("ジャーナリスト", "wd:Q1930187", "政治・社会", 200),
            ("外交官", "wd:Q193391", "政治・社会", 100),
            ("弁護士", "wd:Q40348", "政治・社会", 100),
            
            # 歴史的人物（1,410人）
            ("君主", "wd:Q116", "歴史", 200),
            ("将軍", "wd:Q83460", "歴史", 200),
            ("探検家", "wd:Q11900058", "歴史", 200),
            ("発明家", "wd:Q205375", "歴史", 200),
            ("哲学者", "wd:Q4964182", "歴史", 200),
            ("宗教家", "wd:Q2566598", "歴史", 200),
            ("革命家", "wd:Q3242115", "歴史", 210),
            
            # 追加カテゴリ（500人）
            ("宇宙飛行士", "wd:Q11631", "特殊職業", 50),
            ("シェフ", "wd:Q3499072", "特殊職業", 100),
            ("ファッションデザイナー", "wd:Q3501317", "特殊職業", 100),
            ("モデル", "wd:Q4610556", "特殊職業", 150),
            ("eスポーツ選手", "wd:Q4379701", "特殊職業", 100),
        ]
        
        all_people = []
        
        # 並列処理で高速収集
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for occupation, wikidata_id, category, limit in category_plan:
                future = executor.submit(
                    self._collect_category,
                    occupation, wikidata_id, category, limit
                )
                futures.append(future)
            
            # 結果を収集
            for future in concurrent.futures.as_completed(futures):
                try:
                    people = future.result()
                    all_people.extend(people)
                    print(f"  現在の収集数: {len(all_people)}人")
                except Exception as e:
                    print(f"  ⚠️ エラー: {e}")
                    self.stats['errors'] += 1
        
        # 重複除去
        unique_people = self._remove_duplicates(all_people)
        
        # 統計表示
        self._print_statistics(unique_people)
        
        return unique_people[:target_count]  # 目標数で切り取り
    
    def _collect_category(self, occupation: str, wikidata_id: str, 
                         category: str, limit: int) -> List[Person]:
        """特定カテゴリから人物を収集"""
        print(f"📡 {occupation}を収集中... (目標: {limit}人)")
        
        # シンプルで高速なクエリ
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate 
               ?nationalityLabel ?description
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 {wikidata_id} ;
                  wdt:P569 ?birthDate .
          OPTIONAL {{ ?person wdt:P570 ?deathDate }}
          OPTIONAL {{ ?person wdt:P27 ?nationality }}
          OPTIONAL {{ ?person schema:description ?description 
                     FILTER(LANG(?description) = "ja") }}
          SERVICE wikibase:label {{ 
            bd:serviceParam wikibase:language "ja,en". 
          }}
        }}
        LIMIT {limit * 2}
        """
        
        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                people = []
                
                for item in data['results']['bindings'][:limit]:
                    person = Person(
                        name=item['personLabel']['value'],
                        birth_date=item.get('birthDate', {}).get('value', '')[:10],
                        death_date=item.get('deathDate', {}).get('value', '')[:10],
                        nationality=item.get('nationalityLabel', {}).get('value', ''),
                        occupation=occupation,
                        main_category=category,
                        subcategory=occupation,
                        wikidata_id=item['person']['value'].split('/')[-1],
                        description=item.get('description', {}).get('value', '')
                    )
                    
                    # 基本的な検証のみ
                    if self._validate_person(person):
                        people.append(person)
                
                print(f"  ✅ {occupation}: {len(people)}人収集")
                return people
            
        except Exception as e:
            print(f"  ⚠️ {occupation}エラー: {str(e)[:50]}")
            
        return []
    
    def _validate_person(self, person: Person) -> bool:
        """人物データの基本検証"""
        # 名前の検証
        if not person.name or len(person.name) < 2:
            return False
        if person.name.isdigit():
            return False
        
        # 生年の検証
        if person.birth_date:
            try:
                year = int(person.birth_date[:4])
                if year < 1000 or year > 2024:
                    return False
            except:
                return False
        
        return True
    
    def _remove_duplicates(self, people: List[Person]) -> List[Person]:
        """重複を除去"""
        unique = {}
        
        for person in people:
            person_id = person.generate_id()
            if person_id not in unique:
                unique[person_id] = person
            else:
                self.stats['duplicates_removed'] += 1
        
        return list(unique.values())
    
    def _print_statistics(self, people: List[Person]):
        """収集統計を表示"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 収集統計")
        print("=" * 60)
        print(f"✅ 総収集数: {len(people)}人")
        print(f"⏱️ 処理時間: {elapsed:.1f}秒")
        print(f"🚀 収集速度: {len(people) / elapsed * 60:.0f}人/分")
        print(f"🔁 重複除去: {self.stats['duplicates_removed']}件")
        print(f"❌ エラー: {self.stats['errors']}件")
        
        # カテゴリ分布
        categories = {}
        for person in people:
            cat = person.main_category
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n📈 カテゴリ分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat:15} {count:5}人")
    
    def export_to_csv(self, people: List[Person], filename: str):
        """CSVエクスポート"""
        df = pd.DataFrame([p.to_dict() for p in people])
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n📄 CSVエクスポート完了: {filename}")
    
    def export_to_firebase(self, people: List[Person], filename: str):
        """Firebase用JSONエクスポート"""
        firebase_data = []
        
        for person in people:
            firebase_person = {
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
                'createdAt': datetime.now().isoformat()
            }
            firebase_data.append(firebase_person)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(firebase_data, f, ensure_ascii=False, indent=2)
        
        print(f"📱 Firebase JSONエクスポート完了: {filename}")

def main():
    """メイン処理"""
    print("=" * 60)
    print("🚀 最適化版有名人物収集システム")
    print("💰 コスト: $0（完全無料）")
    print("⚡ エピソード: 無し（高速化のため）")
    print("=" * 60)
    
    collector = OptimizedPersonCollector()
    
    # デモ版: 1,000人収集（フル版は12,410人）
    people = collector.collect_all_categories(target_count=1000)
    
    # エクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV
    csv_filename = f"people_only_{timestamp}.csv"
    collector.export_to_csv(people, csv_filename)
    
    # Firebase JSON
    json_filename = f"people_firebase_{timestamp}.json"
    collector.export_to_firebase(people, json_filename)
    
    print("\n" + "=" * 60)
    print("✅ 収集完了！")
    print(f"  人数: {len(people)}人")
    print("  コスト: $0")
    print("  エピソード: 後で必要に応じて追加可能")
    print("=" * 60)

if __name__ == "__main__":
    main()