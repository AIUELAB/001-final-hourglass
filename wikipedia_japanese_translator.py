#!/usr/bin/env python3
"""
Wikipedia日本語版API翻訳システム
Wikidata IDを使ってWikipedia日本語版から正確な日本語表記を取得
"""

import json
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


class WikipediaJapaneseTranslator:
    """Wikipedia日本語版を使った翻訳システム"""
    
    def __init__(self):
        self.wikipedia_api = "https://ja.wikipedia.org/w/api.php"
        self.wikidata_api = "https://www.wikidata.org/w/api.php"
        self.translation_cache = self.load_cache()
        self.stats = {
            'processed': 0,
            'translated': 0,
            'failed': 0,
            'cached': 0
        }
    
    def load_cache(self) -> Dict[str, str]:
        """既存の翻訳キャッシュを読み込み"""
        cache_file = Path('translation_cache.json')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """翻訳キャッシュを保存"""
        with open('translation_cache.json', 'w', encoding='utf-8') as f:
            json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
    
    def get_wikipedia_title_from_wikidata(self, wikidata_id: str) -> Optional[str]:
        """Wikidata IDからWikipedia日本語版のタイトルを取得"""
        
        # キャッシュチェック
        cache_key = f"wiki_ja_{wikidata_id}"
        if cache_key in self.translation_cache:
            self.stats['cached'] += 1
            return self.translation_cache[cache_key]
        
        try:
            # WikidataからWikipedia日本語版のリンクを取得
            params = {
                'action': 'wbgetentities',
                'ids': wikidata_id,
                'props': 'sitelinks',
                'sitefilter': 'jawiki',
                'format': 'json'
            }
            
            response = requests.get(self.wikidata_api, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Wikipedia日本語版のタイトルを抽出
                if 'entities' in data and wikidata_id in data['entities']:
                    entity = data['entities'][wikidata_id]
                    if 'sitelinks' in entity and 'jawiki' in entity['sitelinks']:
                        title = entity['sitelinks']['jawiki']['title']
                        
                        # キャッシュに保存
                        self.translation_cache[cache_key] = title
                        self.stats['translated'] += 1
                        return title
        except Exception as e:
            print(f"  ⚠️ Wikidata API エラー ({wikidata_id}): {e}")
        
        self.stats['failed'] += 1
        return None
    
    def get_japanese_name_from_english(self, english_name: str, wikidata_id: Optional[str] = None) -> Optional[str]:
        """英語名から日本語名を取得（Wikidata ID優先）"""
        
        # Wikidata IDがある場合は優先
        if wikidata_id:
            japanese_title = self.get_wikipedia_title_from_wikidata(wikidata_id)
            if japanese_title:
                # 曖昧さ回避の括弧を除去
                if '(' in japanese_title:
                    japanese_title = japanese_title.split('(')[0].strip()
                return japanese_title
        
        # Wikipedia検索APIを使用（フォールバック）
        try:
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': english_name,
                'format': 'json',
                'srlimit': 1
            }
            
            response = requests.get(self.wikipedia_api, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'query' in data and 'search' in data['query'] and data['query']['search']:
                    title = data['query']['search'][0]['title']
                    
                    # 英語名と大きく異なる場合のみ採用
                    if not any(c.isascii() for c in title):
                        self.stats['translated'] += 1
                        return title
        except Exception as e:
            print(f"  ⚠️ Wikipedia検索エラー ({english_name}): {e}")
        
        return None
    
    def batch_translate(self, items: List[Dict]) -> Dict[str, str]:
        """バッチで翻訳実行"""
        translations = {}
        
        for item in items:
            self.stats['processed'] += 1
            
            wikidata_id = item.get('wikidata_id', '')
            english_name = item.get('name', '')
            key = item.get('id', '')
            
            # 翻訳試行
            japanese_name = self.get_japanese_name_from_english(english_name, wikidata_id)
            
            if japanese_name:
                translations[key] = japanese_name
                print(f"  ✓ {english_name} → {japanese_name}")
            
            # レート制限対策
            if self.stats['processed'] % 10 == 0:
                time.sleep(0.5)
        
        return translations
    
    def translate_database(self, input_file: str = None) -> Tuple[str, Dict]:
        """データベース全体を翻訳"""
        
        # 入力ファイル決定
        if not input_file:
            input_file = 'perfect_database_20250824_172451.json'
        
        print("🌐 Wikipedia日本語版翻訳開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        # 未翻訳データ抽出
        untranslated = []
        for key, value in all_data.items():
            if isinstance(value, dict):
                name = value.get('name', '')
                wikidata_id = value.get('wikidata_id', '')
                
                # 英語名のみ対象
                if name and not any(ord(c) > 0x3000 for c in name):
                    untranslated.append({
                        'id': key,
                        'name': name,
                        'wikidata_id': wikidata_id
                    })
        
        print(f"  対象: {len(untranslated)}件")
        
        # バッチ処理（50件ずつ）
        batch_size = 50
        all_translations = {}
        
        for i in range(0, len(untranslated), batch_size):
            batch = untranslated[i:i+batch_size]
            print(f"\n  バッチ {i//batch_size + 1}/{(len(untranslated)-1)//batch_size + 1} 処理中...")
            
            translations = self.batch_translate(batch)
            all_translations.update(translations)
            
            # 進捗保存
            if i % 200 == 0 and i > 0:
                self.save_cache()
        
        # 最終保存
        self.save_cache()
        
        # データベース更新
        for key, japanese_name in all_translations.items():
            if key in all_data:
                all_data[key]['original_name'] = all_data[key].get('name', '')
                all_data[key]['name'] = japanese_name
        
        # 出力ファイル保存
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"wikipedia_translated_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print("\n📊 Wikipedia翻訳結果:")
        print(f"  処理: {self.stats['processed']}件")
        print(f"  翻訳成功: {self.stats['translated']}件")
        print(f"  キャッシュ使用: {self.stats['cached']}件")
        print(f"  失敗: {self.stats['failed']}件")
        print(f"  出力: {output_file}")
        
        return output_file, self.stats


def main():
    """メイン実行"""
    translator = WikipediaJapaneseTranslator()
    
    # Wikipedia日本語版からの翻訳実行
    output_file, stats = translator.translate_database()
    
    # 成功率計算
    if stats['processed'] > 0:
        success_rate = stats['translated'] / stats['processed'] * 100
        print(f"\n🎯 翻訳成功率: {success_rate:.1f}%")


if __name__ == "__main__":
    main()