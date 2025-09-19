#!/usr/bin/env python3
"""
Mass Wikipedia Collector - 大規模収集プログラム
20,000人のデータを段階的に収集
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests


class MassWikipediaCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 Mass Collection'
        })
        
        # 実証済み設定
        self.delay = 0.2  # 0.2秒遅延
        self.batch_size = 3  # 3タイトルずつ
        self.all_collected = []
        self.checkpoint_file = 'mass_collection_checkpoint.json'
        
        # 拡張クエリリスト（多様性確保）
        self.query_pool = self.create_query_pool()
        self.query_index = 0
        
    def create_query_pool(self) -> List[str]:
        """大規模クエリプール作成"""
        queries = []
        
        # エンターテインメント
        entertainment = [
            '日本 俳優', '日本 女優', '日本 歌手', 'お笑い芸人', 'アイドル',
            '声優', 'YouTuber', 'タレント', 'モデル', 'グラビア',
            'ミュージシャン', 'バンド', 'アニメ監督', '映画監督', 'プロデューサー',
            '振付師', '演出家', '脚本家', 'K-POP', 'J-POP',
            'ロック歌手', 'ラッパー', 'DJ', 'VTuber', 'TikToker'
        ]
        
        # スポーツ
        sports = [
            '野球選手', 'プロ野球', 'メジャーリーガー', 'サッカー選手', 'Jリーガー',
            'テニス選手', 'ゴルファー', 'オリンピック選手', 'パラリンピック',
            '相撲力士', '横綱', 'プロレスラー', '格闘家', 'ボクサー',
            'フィギュアスケート', 'マラソン選手', '陸上選手', '水泳選手', '体操選手',
            'バスケットボール選手', 'バレーボール選手', 'ラグビー選手', 'F1ドライバー', 'プロゲーマー'
        ]
        
        # ビジネス・テクノロジー
        business = [
            '起業家', '実業家', 'CEO', '社長', '創業者',
            'IT起業家', 'スタートアップ', '投資家', 'エンジニア', 'プログラマー',
            'AI研究者', 'データサイエンティスト', 'ゲームクリエイター', 'Web開発者',
            '経営者', '企業家', 'ベンチャー', 'イノベーター', '発明家'
        ]
        
        # 文化・芸術
        culture = [
            '作家', '小説家', '詩人', '漫画家', '画家',
            '彫刻家', '写真家', '書道家', '陶芸家', '建築家',
            'デザイナー', 'イラストレーター', 'アーティスト', '芸術家', '美術家',
            '茶道', '華道', '日本画家', '版画家', '現代美術'
        ]
        
        # 政治・社会
        politics = [
            '政治家', '首相', '大臣', '知事', '市長',
            '国会議員', '外交官', '官僚', '活動家', '社会運動家',
            'ジャーナリスト', 'キャスター', 'アナウンサー', '評論家', '学者',
            '教授', '研究者', '弁護士', '裁判官', '検察官'
        ]
        
        # 歴史
        history = [
            '戦国武将', '武士', '侍', '忍者', '大名',
            '幕末志士', '明治維新', '将軍', '天皇', '皇族',
            '歴史上の人物', '偉人', '英雄', '探検家', '冒険家',
            '軍人', '提督', '元帥', '革命家', '思想家'
        ]
        
        # 架空・キャラクター
        fictional = [
            'アニメキャラクター', '漫画キャラクター', 'ゲームキャラクター',
            '特撮ヒーロー', '仮面ライダー', 'ウルトラマン', '戦隊ヒーロー',
            'ディズニーキャラクター', 'ジブリキャラクター', 'ポケモン'
        ]
        
        # すべて結合
        queries.extend(entertainment)
        queries.extend(sports)
        queries.extend(business)
        queries.extend(culture)
        queries.extend(politics)
        queries.extend(history)
        queries.extend(fictional)
        
        return queries
    
    def search(self, query: str) -> List[str]:
        """検索実行"""
        time.sleep(self.delay)
        try:
            r = self.session.get(
                'https://ja.wikipedia.org/w/api.php',
                params={
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 30
                },
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                return [item['title'] for item in data.get('query', {}).get('search', [])]
        except:
            pass
        return []
    
    def get_pages(self, titles: List[str]) -> List[Dict]:
        """ページ情報取得"""
        people = []
        for i in range(0, len(titles), self.batch_size):
            batch = titles[i:i+self.batch_size]
            time.sleep(self.delay)
            
            try:
                r = self.session.get(
                    'https://ja.wikipedia.org/w/api.php',
                    params={
                        'action': 'query',
                        'format': 'json',
                        'prop': 'extracts|categories',
                        'exintro': True,
                        'explaintext': True,
                        'exsentences': 2,
                        'titles': '|'.join(batch)
                    },
                    timeout=5
                )
                if r.status_code == 200:
                    data = r.json()
                    for pid, pdata in data.get('query', {}).get('pages', {}).items():
                        if pid != '-1':
                            person = self.parse_page(pdata)
                            if person:
                                people.append(person)
            except:
                pass
                
        return people
    
    def parse_page(self, pdata: Dict) -> Dict:
        """ページ解析"""
        title = pdata.get('title', '')
        extract = pdata.get('extract', '')
        
        if len(extract) < 30:
            return None
            
        categories = [c.get('title', '') for c in pdata.get('categories', [])]
        cat_text = ' '.join(categories) + ' ' + extract
        
        return {
            'name': title,
            'birth_date': self.extract_year(extract),
            'death_date': '',
            'nationality': self.infer_nationality(extract),
            'occupation': self.infer_occupation(cat_text),
            'main_category': self.categorize(cat_text),
            'subcategory': '',
            'wikidata_id': '',
            'description': extract[:300],
            'impact_score': 7,
            'japanese_relevance': 8,
            'grade': 'B',
            'data_source': 'wikipedia_mass'
        }
    
    def extract_year(self, text: str) -> str:
        """年抽出"""
        import re
        match = re.search(r'(\d{4})年', text)
        return f"{match.group(1)}-01-01" if match else ''
    
    def infer_nationality(self, text: str) -> str:
        """国籍推定"""
        if '日本' in text:
            return '日本'
        elif 'アメリカ' in text or 'America' in text:
            return 'アメリカ'
        elif '韓国' in text:
            return '韓国'
        elif '中国' in text:
            return '中国'
        return ''
    
    def infer_occupation(self, text: str) -> str:
        """職業推定"""
        occupations = {
            '俳優': ['俳優', '女優', '出演'],
            '歌手': ['歌手', '歌', 'ボーカル'],
            '芸人': ['芸人', 'お笑い', 'コメディ'],
            'スポーツ選手': ['選手', 'プレイヤー', 'アスリート'],
            '作家': ['作家', '小説', '著者'],
            '政治家': ['政治', '首相', '大臣'],
            '実業家': ['実業', '社長', 'CEO'],
            'キャラクター': ['キャラクター', 'アニメ', '漫画']
        }
        
        for occ, keywords in occupations.items():
            if any(kw in text for kw in keywords):
                return occ
        return '著名人'
    
    def categorize(self, text: str) -> str:
        """カテゴリ分類"""
        if any(w in text for w in ['俳優', '女優', '歌手', '芸能', 'アイドル', 'タレント']):
            return 'エンターテインメント'
        elif any(w in text for w in ['選手', 'スポーツ', 'オリンピック', '野球', 'サッカー']):
            return 'スポーツ'
        elif any(w in text for w in ['政治', '首相', '大臣', '議員']):
            return '政治・社会'
        elif any(w in text for w in ['社長', 'CEO', '起業', '実業']):
            return 'ビジネス・テクノロジー'
        elif any(w in text for w in ['歴史', '武将', '江戸', '幕末', '戦国']):
            return '歴史的教訓'
        elif any(w in text for w in ['キャラクター', 'アニメ', '漫画', 'ゲーム']):
            return 'エンターテインメント'
        else:
            return '文化・芸術'
    
    def collect_batch(self, batch_size: int = 300, timeout: int = 85):
        """バッチ収集（85秒）"""
        start = time.time()
        batch_collected = []
        
        while time.time() - start < timeout:
            # クエリプールから取得
            if self.query_index >= len(self.query_pool):
                self.query_index = 0
            
            query = self.query_pool[self.query_index]
            self.query_index += 1
            
            titles = self.search(query)
            if titles:
                people = self.get_pages(titles[:20])
                batch_collected.extend(people)
                
                if len(batch_collected) >= batch_size:
                    break
        
        return batch_collected
    
    def save_checkpoint(self):
        """チェックポイント保存"""
        checkpoint = {
            'collected': len(self.all_collected),
            'query_index': self.query_index,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
    
    def load_checkpoint(self):
        """チェックポイント読み込み"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                self.query_index = checkpoint.get('query_index', 0)
                return checkpoint
        return None
    
    def collect_mass(self, target: int = 2000):
        """大規模収集（2000人）"""
        print(f"目標: {target}人収集")
        
        # 既存データ読み込み
        existing_files = [
            'wikipedia_turbo_20250822_200648.csv',
            'wikidata_quick_20250822_193210.csv'
        ]
        
        for file in existing_files:
            if os.path.exists(file):
                df = pd.read_csv(file, encoding='utf-8-sig')
                self.all_collected.extend(df.to_dict('records'))
                print(f"既存データ読み込み: {file} ({len(df)}人)")
        
        print(f"開始時点: {len(self.all_collected)}人")
        
        # 新規収集
        rounds = 0
        while len(self.all_collected) < target:
            rounds += 1
            print(f"\nラウンド {rounds}:")
            
            batch = self.collect_batch(300, 85)
            self.all_collected.extend(batch)
            
            # 重複削除
            seen = set()
            unique = []
            for p in self.all_collected:
                if p['name'] not in seen:
                    seen.add(p['name'])
                    unique.append(p)
            self.all_collected = unique
            
            print(f"  収集: {len(batch)}人")
            print(f"  累計: {len(self.all_collected)}人")
            
            # チェックポイント保存
            self.save_checkpoint()
            
            if rounds >= 10:  # 最大10ラウンド
                break
        
        print(f"\n収集完了: {len(self.all_collected)}人")
    
    def save_final(self):
        """最終保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_mass_{timestamp}.csv"
        
        if self.all_collected:
            df = pd.DataFrame(self.all_collected)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            print(f"\n保存: {filename}")
            print(f"総人数: {len(self.all_collected)}")
            print("\nカテゴリ分布:")
            print(df['main_category'].value_counts())
            
        return filename

def main():
    collector = MassWikipediaCollector()
    print("大規模Wikipedia収集開始")
    collector.collect_mass(2000)  # まず2000人収集
    return collector.save_final()

if __name__ == "__main__":
    main()