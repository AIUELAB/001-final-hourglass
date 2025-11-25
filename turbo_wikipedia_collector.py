#!/usr/bin/env python3
"""
Turbo Wikipedia Collector - 超高速収集版
90秒で最大限のデータを収集
"""

import csv
import time
from datetime import datetime
from typing import Dict, List

import requests


class TurboWikipediaCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 Turbo Mode'
        })

        # 超高速設定
        self.delay = 0.2  # 0.2秒遅延
        self.batch_size = 3  # 3タイトルずつ
        self.collected = []

    def search(self, query: str) -> List[str]:
        """高速検索"""
        time.sleep(self.delay)
        try:
            r = self.session.get(
                'https://ja.wikipedia.org/w/api.php',
                params={
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 20
                },
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                return [item['title'] for item in data.get('query', {}).get('search', [])]
        except:
            pass
        return []

    def get_info(self, titles: List[str]) -> List[Dict]:
        """高速情報取得"""
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
                        'prop': 'extracts',
                        'exintro': True,
                        'explaintext': True,
                        'exsentences': 1,  # 1文のみ
                        'titles': '|'.join(batch)
                    },
                    timeout=5
                )
                if r.status_code == 200:
                    data = r.json()
                    for pid, pdata in data.get('query', {}).get('pages', {}).items():
                        if pid != '-1':
                            title = pdata.get('title', '')
                            extract = pdata.get('extract', '')
                            if len(extract) > 20:
                                people.append({
                                    'name': title,
                                    'birth_date': '',
                                    'death_date': '',
                                    'nationality': '日本' if '日本' in extract else '',
                                    'occupation': '',
                                    'main_category': self.categorize(extract),
                                    'subcategory': '',
                                    'wikidata_id': '',
                                    'description': extract[:200],
                                    'impact_score': 7,
                                    'japanese_relevance': 8,
                                    'grade': 'B',
                                    'data_source': 'wikipedia_turbo'
                                })
            except:
                pass

        return people

    def categorize(self, text: str) -> str:
        """簡易カテゴリ分類"""
        if any(w in text for w in ['俳優', '女優', '歌手', '芸']):
            return 'エンターテインメント'
        elif any(w in text for w in ['選手', 'スポーツ']):
            return 'スポーツ'
        elif any(w in text for w in ['政治', '首相', '大臣']):
            return '政治・社会'
        elif any(w in text for w in ['社長', 'CEO', '起業']):
            return 'ビジネス・テクノロジー'
        elif any(w in text for w in ['歴史', '武将', '江戸']):
            return '歴史的教訓'
        else:
            return '文化・芸術'

    def turbo_collect(self):
        """90秒ターボ収集"""
        start = time.time()
        queries = [
            # 最優先
            '日本 俳優', '日本 女優', '日本 歌手', 'お笑い芸人',
            'アイドル', '声優', 'YouTuber', 'タレント',
            # スポーツ
            '野球選手', 'サッカー選手', 'オリンピック', 'テニス',
            # ビジネス
            '起業家', '実業家', 'CEO',
            # 文化
            '作家', '漫画家', '映画監督',
            # 政治
            '政治家', '首相',
            # 歴史
            '戦国武将', '幕末'
        ]

        for query in queries:
            # 時間チェック
            if time.time() - start > 85:  # 85秒で終了
                break

            titles = self.search(query)
            if titles:
                people = self.get_info(titles[:15])
                self.collected.extend(people)
                print(f"{query}: {len(people)}人収集 (計{len(self.collected)}人)")

        # 重複削除
        seen = set()
        unique = []
        for p in self.collected:
            if p['name'] not in seen:
                seen.add(p['name'])
                unique.append(p)
        self.collected = unique

        elapsed = time.time() - start
        print(f"\n完了: {len(self.collected)}人を{elapsed:.1f}秒で収集")
        print(f"速度: {len(self.collected)/elapsed:.1f}人/秒")

    def save(self):
        """保存"""
        if self.collected:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wikipedia_turbo_{timestamp}.csv"

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.collected[0].keys())
                writer.writeheader()
                writer.writerows(self.collected)

            print(f"保存: {filename}")
            return filename

def main():
    collector = TurboWikipediaCollector()
    print("ターボモード開始（90秒収集）")
    collector.turbo_collect()
    return collector.save()

if __name__ == "__main__":
    main()
