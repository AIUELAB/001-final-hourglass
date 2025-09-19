#!/usr/bin/env python3
"""
Wikipediaから有名人データをスクレイピング（無料）
"""

import csv
import re
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup


class WikipediaScraper:
    """Wikipediaから有名人リストをスクレイピング"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 (Educational Purpose) Python/3.9'
        })
        self.collected_people = []
    
    def scrape_wikipedia_list(self, url, category_name):
        """Wikipediaのリストページからデータを取得"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # テーブルを探す
            tables = soup.find_all('table', class_='wikitable')
            
            people_data = []
            for table in tables:
                rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        # 名前を取得
                        name_cell = cols[0]
                        name_link = name_cell.find('a')
                        if name_link:
                            name = name_link.text.strip()
                            # 生年を探す
                            birth_year = self.extract_year_from_row(row.text)
                            
                            person = {
                                'name': name,
                                'name_ja': name if self.is_japanese(name) else '',
                                'birth_year': birth_year,
                                'category': category_name,
                                'source': 'Wikipedia'
                            }
                            people_data.append(person)
            
            return people_data
            
        except Exception as e:
            print(f"スクレイピングエラー ({url}): {e}")
            return []
    
    def extract_year_from_row(self, text):
        """テキストから年を抽出"""
        # 年のパターンを探す（例: 1990年、1990、(1990)など）
        patterns = [
            r'(\d{4})年生',
            r'(\d{4})年',
            r'\((\d{4})[^\)]*\)',
            r'(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year = match.group(1)
                if 1800 <= int(year) <= 2024:  # 妥当な年の範囲
                    return year
        return ''
    
    def is_japanese(self, text):
        """日本語の文字が含まれているかチェック"""
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
    
    def scrape_japanese_comedians(self):
        """日本のお笑い芸人をスクレイピング"""
        print("📚 日本のお笑い芸人をスクレイピング中...")
        
        urls = [
            # M-1グランプリ歴代優勝者
            ('https://ja.wikipedia.org/wiki/M-1グランプリ', 'お笑い芸人（M-1）'),
            # R-1グランプリ
            ('https://ja.wikipedia.org/wiki/R-1グランプリ', 'お笑い芸人（R-1）'),
            # キングオブコント
            ('https://ja.wikipedia.org/wiki/キングオブコント', 'お笑い芸人（KOC）'),
        ]
        
        all_comedians = []
        for url, category in urls:
            print(f"  スクレイピング: {category}")
            comedians = self.scrape_wikipedia_list(url, category)
            all_comedians.extend(comedians)
            time.sleep(1)  # サーバー負荷軽減
        
        return all_comedians
    
    def scrape_nobel_laureates(self):
        """ノーベル賞受賞者をスクレイピング"""
        print("📚 ノーベル賞受賞者をスクレイピング中...")
        
        # 日本人ノーベル賞受賞者
        url = 'https://ja.wikipedia.org/wiki/日本人のノーベル賞受賞者'
        laureates = self.scrape_wikipedia_list(url, 'ノーベル賞受賞者')
        
        return laureates
    
    def scrape_olympic_athletes(self):
        """オリンピック選手をスクレイピング"""
        print("📚 オリンピック選手をスクレイピング中...")
        
        # 日本のオリンピック金メダリスト
        url = 'https://ja.wikipedia.org/wiki/オリンピックの日本人メダリスト一覧'
        athletes = self.scrape_wikipedia_list(url, 'オリンピック選手')
        
        return athletes[:100]  # 最初の100人のみ
    
    def scrape_all_categories(self):
        """すべてのカテゴリからスクレイピング"""
        print("🔍 Wikipediaスクレイピング開始...")
        
        all_people = []
        
        # お笑い芸人
        comedians = self.scrape_japanese_comedians()
        all_people.extend(comedians)
        print(f"  ✅ お笑い芸人: {len(comedians)}人")
        
        # ノーベル賞受賞者
        laureates = self.scrape_nobel_laureates()
        all_people.extend(laureates)
        print(f"  ✅ ノーベル賞受賞者: {len(laureates)}人")
        
        # オリンピック選手
        athletes = self.scrape_olympic_athletes()
        all_people.extend(athletes)
        print(f"  ✅ オリンピック選手: {len(athletes)}人")
        
        # データを整形
        for person in all_people:
            formatted_person = {
                'id': f"wiki_{person['name'].replace(' ', '_').lower()}",
                'name': person['name'],
                'name_ja': person.get('name_ja', ''),
                'birth_year': person.get('birth_year', ''),
                'death_year': '',
                'death_age': '',
                'nationality': '日本' if person.get('name_ja') else '',
                'occupation': person.get('category', ''),
                'main_category': person.get('category', ''),
                'subcategory': '',
                'special_tags': 'Wikipedia',
                'source': 'Wikipedia',
                'wikidata_id': '',
                'description': '',
                'key_ages': ''
            }
            self.collected_people.append(formatted_person)
        
        print(f"\n🎯 合計 {len(self.collected_people)}人のデータを収集しました")
        return len(self.collected_people)
    
    def save_to_csv(self, filename=None):
        """収集したデータをCSVに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wikipedia_people_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
                'nationality', 'occupation', 'main_category', 'subcategory',
                'special_tags', 'source', 'wikidata_id', 'description', 'key_ages'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(self.collected_people)
        
        print(f"💾 データを保存しました: {filename}")
        return filename

def scrape_wikipedia_table_pandas(url):
    """pandasを使ったWikipediaテーブルの簡単な取得"""
    try:
        # pandasでWikipediaのテーブルを直接読み込み
        tables = pd.read_html(url)
        
        if tables:
            print(f"✅ {len(tables)}個のテーブルを発見")
            # 最初のテーブルを返す
            return tables[0]
        else:
            print("テーブルが見つかりませんでした")
            return None
            
    except Exception as e:
        print(f"エラー: {e}")
        return None

def main():
    """メイン処理"""
    scraper = WikipediaScraper()
    
    # データ収集
    total = scraper.scrape_all_categories()
    
    # CSV保存
    if total > 0:
        output_file = scraper.save_to_csv()
        
        print("\n✅ Wikipedia収集完了！")
        print(f"📊 総収集人数: {total}人")
        print("💰 コスト: $0（完全無料）")
    else:
        print("\n⚠️ データが収集できませんでした")
    
    # pandasでの簡単な例も実行
    print("\n📊 pandasでの例（日本人ノーベル賞受賞者）:")
    url = 'https://ja.wikipedia.org/wiki/日本人のノーベル賞受賞者'
    df = scrape_wikipedia_table_pandas(url)
    if df is not None:
        print(df.head())
    
    return output_file if total > 0 else None

if __name__ == "__main__":
    main()