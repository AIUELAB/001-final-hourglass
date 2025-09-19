#!/usr/bin/env python3
"""
生誕年抽出・補完システム
birth_dateから生誕年を抽出し、欠損データはWikidataから取得
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests


class BirthYearExtractor:
    """生誕年を抽出・補完するシステム"""
    
    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.stats = {
            'total': 0,
            'has_birth_date': 0,
            'extracted_from_date': 0,
            'fetched_from_wikidata': 0,
            'estimated': 0,
            'unknown': 0,
            'bc_dates': 0  # 紀元前
        }
        
        # 時代推定用の辞書
        self.era_estimates = {
            'Ancient Rome': -100,  # 紀元前1世紀
            'Ancient Greece': -400,  # 紀元前4世紀
            'Ancient Egypt': -1500,  # 紀元前15世紀
            'Medieval': 1200,  # 12世紀
            'Renaissance': 1500,  # 15世紀
            'Baroque': 1650,  # 17世紀
            'Classical': 1750,  # 18世紀
            'Romantic': 1820,  # 19世紀前半
            'Modern': 1900,  # 20世紀
            'Contemporary': 1950  # 20世紀後半
        }
        
        # キャッシュ
        self.year_cache = self.load_cache()
    
    def load_cache(self) -> Dict:
        """キャッシュを読み込み"""
        cache_file = Path('birth_year_cache.json')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """キャッシュを保存"""
        with open('birth_year_cache.json', 'w', encoding='utf-8') as f:
            json.dump(self.year_cache, f, ensure_ascii=False, indent=2)
    
    def extract_year_from_date(self, birth_date: str) -> Optional[int]:
        """birth_dateから年を抽出"""
        if not birth_date:
            return None
        
        # パターンマッチング
        patterns = [
            r'^(-?\d{1,4})[/-]',  # YYYY/MM/DD or YYYY-MM-DD
            r'^(-?\d{1,4})$',  # YYYY only
            r'(\d{1,4})\s*(?:年|AD|BC)',  # 1900年, 100 AD, 500 BC
            r'BC\s*(\d{1,4})',  # BC 500
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(birth_date))
            if match:
                year = int(match.group(1))
                
                # BCの処理
                if 'BC' in str(birth_date).upper() or '紀元前' in str(birth_date):
                    year = -abs(year)
                    self.stats['bc_dates'] += 1
                
                return year
        
        return None
    
    def fetch_birth_year_from_wikidata(self, wikidata_id: str) -> Optional[int]:
        """WikidataAPIから生誕年を取得"""
        if not wikidata_id or not wikidata_id.startswith('Q'):
            return None
        
        # キャッシュチェック
        cache_key = f"wiki_year_{wikidata_id}"
        if cache_key in self.year_cache:
            return self.year_cache[cache_key]
        
        try:
            query = f"""
            SELECT ?birthYear WHERE {{
              wd:{wikidata_id} wdt:P569 ?birthDate .
              BIND(YEAR(?birthDate) AS ?birthYear)
            }}
            LIMIT 1
            """
            
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                bindings = data.get('results', {}).get('bindings', [])
                
                if bindings:
                    year_str = bindings[0].get('birthYear', {}).get('value', '')
                    if year_str:
                        year = int(float(year_str))
                        self.year_cache[cache_key] = year
                        return year
        except Exception as e:
            print(f"  ⚠️ Wikidata API エラー ({wikidata_id}): {e}")
        
        return None
    
    def estimate_birth_year(self, person: Dict) -> Optional[int]:
        """職業や国籍から生誕年を推定"""
        occupation = person.get('occupation', '').lower()
        nationality = person.get('nationality', '')
        death_date = person.get('death_date', '')
        
        # 死亡年から推定（平均寿命60年と仮定）
        if death_date:
            death_year = self.extract_year_from_date(death_date)
            if death_year:
                return death_year - 60
        
        # 時代キーワードから推定
        for era, year in self.era_estimates.items():
            if era.lower() in nationality.lower() or era.lower() in occupation:
                return year
        
        # 職業別のデフォルト推定
        if 'composer' in occupation:
            # クラシック作曲家は18-19世紀が多い
            return 1780
        elif 'ancient' in occupation or 'ancient' in nationality:
            return -100  # 紀元前1世紀
        elif any(word in occupation for word in ['俳優', 'actor', '歌手', 'singer', '芸人']):
            # 現代のエンターテイナー
            return 1970
        elif 'scientist' in occupation:
            return 1850
        elif 'philosopher' in occupation:
            return 1700
        
        return None
    
    def process_person(self, person: Dict) -> int:
        """個人の生誕年を処理"""
        birth_date = person.get('birth_date', '')
        wikidata_id = person.get('wikidata_id', '')
        
        # 1. birth_dateから抽出
        if birth_date:
            year = self.extract_year_from_date(birth_date)
            if year is not None:
                self.stats['extracted_from_date'] += 1
                return year
        
        # 2. Wikidataから取得
        if wikidata_id:
            year = self.fetch_birth_year_from_wikidata(wikidata_id)
            if year is not None:
                self.stats['fetched_from_wikidata'] += 1
                return year
            # API制限対策
            time.sleep(0.1)
        
        # 3. 推定
        year = self.estimate_birth_year(person)
        if year is not None:
            self.stats['estimated'] += 1
            return year
        
        # 4. 不明
        self.stats['unknown'] += 1
        return 0  # 0は不明を表す
    
    def extract_all_birth_years(self, input_file: str = None) -> Tuple[str, Dict]:
        """全データの生誕年を抽出・補完"""
        
        if not input_file:
            input_file = 'advanced_grade_20250824_182846.json'
        
        print("📅 生誕年抽出・補完システム開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # プログレス表示用
        processed = 0
        examples = []
        
        # 各レコードを処理
        for key, value in data.items():
            if isinstance(value, dict):
                processed += 1
                
                # プログレス表示
                if processed % 500 == 0:
                    print(f"  進捗: {processed}/{self.stats['total']} ({processed/self.stats['total']*100:.1f}%)")
                
                # 生誕年を処理
                birth_year = self.process_person(value)
                value['birth_year'] = birth_year
                
                # サンプル収集
                if len(examples) < 20:
                    examples.append({
                        'name': value.get('preferred_display_name', ''),
                        'birth_date': value.get('birth_date', ''),
                        'birth_year': birth_year,
                        'method': 'extracted' if value.get('birth_date') else 'estimated'
                    })
        
        # キャッシュ保存
        self.save_cache()
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"birth_year_complete_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # レポート出力
        print("\n📊 生誕年抽出結果:")
        print(f"  総レコード: {self.stats['total']:,}")
        print(f"  birth_dateから抽出: {self.stats['extracted_from_date']:,} ({self.stats['extracted_from_date']/self.stats['total']*100:.1f}%)")
        print(f"  Wikidataから取得: {self.stats['fetched_from_wikidata']:,} ({self.stats['fetched_from_wikidata']/self.stats['total']*100:.1f}%)")
        print(f"  推定: {self.stats['estimated']:,} ({self.stats['estimated']/self.stats['total']*100:.1f}%)")
        print(f"  不明: {self.stats['unknown']:,} ({self.stats['unknown']/self.stats['total']*100:.1f}%)")
        print(f"  紀元前: {self.stats['bc_dates']:,}")
        
        if examples:
            print("\n📝 抽出例:")
            for ex in examples[:10]:
                if ex['birth_year'] < 0:
                    year_str = f"BC {abs(ex['birth_year'])}"
                elif ex['birth_year'] == 0:
                    year_str = "不明"
                else:
                    year_str = str(ex['birth_year'])
                print(f"  {ex['name']:20} : {ex['birth_date']:15} → {year_str:10} ({ex['method']})")
        
        # 年代分布
        year_distribution = {}
        for person in data.values():
            if isinstance(person, dict):
                year = person.get('birth_year', 0)
                if year != 0:
                    century = (year // 100) * 100
                    if century not in year_distribution:
                        year_distribution[century] = 0
                    year_distribution[century] += 1
        
        print("\n📈 年代分布:")
        for century in sorted(year_distribution.keys()):
            count = year_distribution[century]
            if century < 0:
                century_str = f"BC {abs(century)}年代"
            else:
                century_str = f"{century}年代"
            print(f"  {century_str}: {count:,}件")
        
        print(f"\n✅ 出力: {output_file}")
        
        return output_file, self.stats


def main():
    """メイン実行"""
    extractor = BirthYearExtractor()
    output_file, stats = extractor.extract_all_birth_years()
    
    # 完了率計算
    filled_rate = (stats['extracted_from_date'] + stats['fetched_from_wikidata'] + stats['estimated']) / stats['total'] * 100
    
    print("\n🏆 生誕年フィールド完成")
    print(f"  カバー率: {filled_rate:.1f}%")
    if filled_rate >= 99:
        print("  ✨ ほぼ全件の生誕年を埋めることができました！")
    else:
        print(f"  ⚠️ {stats['unknown']}件が不明のままです")


if __name__ == "__main__":
    main()