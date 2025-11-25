#!/usr/bin/env python3
"""
Wikipedia APIを使用して人物の事実データを自動収集
79人分の不足データを補完
"""

import json
import time
import re
from typing import Dict, List, Optional
from pathlib import Path
import requests
from datetime import datetime

class WikipediaFactCollector:
    """Wikipedia事実収集システム"""

    def __init__(self):
        """初期化"""
        self.api_url = "https://ja.wikipedia.org/w/api.php"
        self.session = requests.Session()
        self.collected_data = {}

        # 既存データの読み込み
        self.existing_data = self._load_existing_data()

        # 収集が必要な人物リスト
        self.missing_persons = self._get_missing_persons()

    def _load_existing_data(self) -> Dict:
        """既存のデータを読み込み"""
        try:
            with open('expanded_person_facts.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('persons', {})
        except FileNotFoundError:
            return {}

    def _get_missing_persons(self) -> List[tuple]:
        """データが不足している人物のリストを取得"""
        all_persons = [
            # スポーツ選手（既存データあり: 大谷翔平、イチロー、松井秀喜、羽生結弦、藤井聡太、羽生善治）
            ('錦織圭', 'sports', ['テニス', '全米オープン', 'ATP']),
            ('内村航平', 'sports', ['体操', '五輪', '金メダル']),
            ('浅田真央', 'sports', ['フィギュアスケート', 'トリプルアクセル', '世界選手権']),
            ('高橋尚子', 'sports', ['マラソン', 'シドニー五輪', '金メダル']),
            ('北島康介', 'sports', ['水泳', '平泳ぎ', '五輪']),
            ('吉田沙保里', 'sports', ['レスリング', '五輪', '世界選手権']),
            ('伊調馨', 'sports', ['レスリング', '五輪', '4連覇']),
            ('室伏広治', 'sports', ['ハンマー投', 'アテネ五輪', '金メダル']),
            ('野村忠宏', 'sports', ['柔道', '五輪', '3連覇']),
            ('田臥勇太', 'sports', ['バスケットボール', 'NBA', '日本人初']),
            ('中田英寿', 'sports', ['サッカー', 'セリエA', '日本代表']),
            ('三浦知良', 'sports', ['サッカー', 'Jリーグ', 'カズ']),
            ('長友佑都', 'sports', ['サッカー', 'インテル', '日本代表']),
            ('香川真司', 'sports', ['サッカー', 'ドルトムント', 'マンチェスター']),
            ('久保建英', 'sports', ['サッカー', 'レアル・マドリード', 'バルセロナ']),
            ('八村塁', 'sports', ['バスケットボール', 'NBA', 'ウィザーズ']),

            # エンターテイメント（既存データあり: HIKAKIN、北野武、黒澤明、宮崎駿、新海誠、手塚治虫、坂本龍一）
            ('鳥山明', 'entertainment', ['ドラゴンボール', '漫画家', 'Dr.スランプ']),
            ('尾田栄一郎', 'entertainment', ['ONE PIECE', '漫画家', '週刊少年ジャンプ']),
            ('久石譲', 'entertainment', ['作曲家', 'ジブリ', '映画音楽']),
            ('小田和正', 'entertainment', ['オフコース', '歌手', '作曲家']),
            ('桑田佳祐', 'entertainment', ['サザンオールスターズ', '歌手', '作詞作曲']),
            ('矢沢永吉', 'entertainment', ['ロック', '歌手', 'キャロル']),
            ('松本人志', 'entertainment', ['ダウンタウン', 'お笑い芸人', '映画監督']),
            ('明石家さんま', 'entertainment', ['お笑い芸人', 'タレント', '司会者']),
            ('タモリ', 'entertainment', ['タレント', '司会者', 'ミュージックステーション']),
            ('渥美清', 'entertainment', ['俳優', '男はつらいよ', '寅さん']),
            ('高倉健', 'entertainment', ['俳優', '映画', '任侠映画']),
            ('渡辺謙', 'entertainment', ['俳優', 'ラストサムライ', 'ハリウッド']),
            ('役所広司', 'entertainment', ['俳優', '映画', 'カンヌ国際映画祭']),
            ('安室奈美恵', 'entertainment', ['歌手', 'ポップス', '平成の歌姫']),
            ('宇多田ヒカル', 'entertainment', ['歌手', 'シンガーソングライター', 'First Love']),
            ('浜崎あゆみ', 'entertainment', ['歌手', 'ポップス', '平成の歌姫']),
            ('中森明菜', 'entertainment', ['歌手', 'アイドル', '80年代']),
            ('美空ひばり', 'entertainment', ['歌手', '昭和', '国民的歌手']),

            # 文学（既存データあり: 村上春樹）
            ('大江健三郎', 'literature', ['ノーベル文学賞', '作家', '小説']),
            ('川端康成', 'literature', ['ノーベル文学賞', '作家', '雪国']),
            ('三島由紀夫', 'literature', ['作家', '金閣寺', '仮面の告白']),
            ('谷崎潤一郎', 'literature', ['作家', '細雪', '痴人の愛']),
            ('夏目漱石', 'literature', ['作家', '吾輩は猫である', '坊っちゃん']),
            ('芥川龍之介', 'literature', ['作家', '羅生門', '蜘蛛の糸']),
            ('太宰治', 'literature', ['作家', '人間失格', '走れメロス']),
            ('宮沢賢治', 'literature', ['作家', '銀河鉄道の夜', '詩人']),
            ('井上靖', 'literature', ['作家', '敦煌', '氷壁']),
            ('司馬遼太郎', 'literature', ['作家', '竜馬がゆく', '坂の上の雲']),
            ('吉本ばなな', 'literature', ['作家', 'キッチン', 'TUGUMI']),
            ('村上龍', 'literature', ['作家', '限りなく透明に近いブルー', 'コインロッカー・ベイビーズ']),
            ('東野圭吾', 'literature', ['作家', '容疑者Xの献身', 'ミステリー']),
            ('綿矢りさ', 'literature', ['作家', '蹴りたい背中', '芥川賞']),

            # ビジネス（既存データあり: 孫正義、松下幸之助、本田宗一郎、スティーブ・ジョブズ、ビル・ゲイツ、イーロン・マスク）
            ('盛田昭夫', 'business', ['ソニー', '創業者', 'ウォークマン']),
            ('稲盛和夫', 'business', ['京セラ', '創業者', 'JAL再建']),
            ('豊田章男', 'business', ['トヨタ自動車', '社長', '自動車']),
            ('柳井正', 'business', ['ユニクロ', 'ファーストリテイリング', '創業者']),
            ('三木谷浩史', 'business', ['楽天', '創業者', 'EC']),
            ('前澤友作', 'business', ['ZOZO', '創業者', '宇宙旅行']),
            ('堀江貴文', 'business', ['ライブドア', '起業家', 'ホリエモン']),
            ('渡邉美樹', 'business', ['ワタミ', '創業者', '外食産業']),
            ('永守重信', 'business', ['日本電産', '創業者', 'モーター']),
            ('似鳥昭雄', 'business', ['ニトリ', '創業者', '家具']),
            ('山田昇', 'business', ['ヤマダ電機', '創業者', '家電量販店']),

            # 科学（既存データあり: 山中伸弥）
            ('湯川秀樹', 'science', ['ノーベル物理学賞', '中間子', '理論物理学']),
            ('朝永振一郎', 'science', ['ノーベル物理学賞', '量子電磁力学', '物理学者']),
            ('江崎玲於奈', 'science', ['ノーベル物理学賞', 'トンネル効果', '半導体']),
            ('利根川進', 'science', ['ノーベル生理学・医学賞', '免疫学', 'MIT']),
            ('小柴昌俊', 'science', ['ノーベル物理学賞', 'ニュートリノ', 'カミオカンデ']),
            ('南部陽一郎', 'science', ['ノーベル物理学賞', '素粒子物理学', '対称性の破れ']),
            ('益川敏英', 'science', ['ノーベル物理学賞', 'CP対称性の破れ', '小林・益川理論']),
            ('小林誠', 'science', ['ノーベル物理学賞', 'CP対称性の破れ', '素粒子物理学']),
            ('梶田隆章', 'science', ['ノーベル物理学賞', 'ニュートリノ振動', 'スーパーカミオカンデ']),

            # 芸術（既存データあり: 草間彌生、安藤忠雄）
            ('奈良美智', 'art', ['現代美術', '画家', '彫刻家']),
            ('村上隆', 'art', ['現代美術', 'ポップアート', 'カイカイキキ']),
            ('横山大観', 'art', ['日本画', '画家', '富士山']),
            ('隈研吾', 'architecture', ['建築家', '新国立競技場', '木材']),
            ('伊東豊雄', 'architecture', ['建築家', 'せんだいメディアテーク', 'プリツカー賞']),

            # その他
            ('小澤征爾', 'music', ['指揮者', 'ボストン交響楽団', 'クラシック音楽']),
            ('マーク・ザッカーバーグ', 'business', ['Facebook', 'Meta', '創業者']),
            ('ジェフ・ベゾス', 'business', ['Amazon', '創業者', 'EC']),
        ]

        # 既存データにない人物のみを返す
        missing = []
        for person_info in all_persons:
            name = person_info[0]
            if name not in self.existing_data:
                missing.append(person_info)

        return missing

    def search_wikipedia(self, person_name: str, keywords: List[str]) -> Optional[Dict]:
        """Wikipediaから人物情報を検索"""
        try:
            # ページ検索
            search_params = {
                'action': 'opensearch',
                'search': person_name,
                'limit': 5,
                'format': 'json'
            }

            search_response = self.session.get(self.api_url, params=search_params)
            search_data = search_response.json()

            if len(search_data) > 1 and len(search_data[1]) > 0:
                # 最初の結果のページタイトル
                page_title = search_data[1][0]

                # ページ内容を取得
                content_params = {
                    'action': 'query',
                    'prop': 'extracts|pageprops',
                    'exintro': True,
                    'explaintext': True,
                    'titles': page_title,
                    'format': 'json'
                }

                content_response = self.session.get(self.api_url, params=content_params)
                content_data = content_response.json()

                pages = content_data.get('query', {}).get('pages', {})
                for page_id, page_data in pages.items():
                    if page_id != '-1':
                        extract = page_data.get('extract', '')
                        return self._parse_wikipedia_content(person_name, extract, keywords)

            return None

        except Exception as e:
            print(f"  ⚠️ Wikipedia検索エラー ({person_name}): {e}")
            return None
        finally:
            time.sleep(0.5)  # レート制限対策

    def _parse_wikipedia_content(self, person_name: str, content: str, keywords: List[str]) -> Dict:
        """Wikipedia内容から事実を抽出"""
        facts = {
            'achievements': [],
            'numbers': [],
            'works': []
        }

        # 文章を分割
        sentences = content.split('。')

        for sentence in sentences[:20]:  # 最初の20文のみ処理
            # キーワードが含まれる文を抽出
            for keyword in keywords:
                if keyword in sentence:
                    # 数値が含まれる場合はnumbersに
                    if re.search(r'\d+', sentence):
                        if len(sentence) < 100 and sentence not in facts['numbers']:
                            facts['numbers'].append(sentence.strip() + '。')
                            break
                    # 作品名が含まれる場合はworksに
                    elif '「' in sentence and '」' in sentence:
                        works = re.findall(r'「([^」]+)」', sentence)
                        for work in works:
                            if work not in facts['works']:
                                facts['works'].append(f'「{work}」')
                    # それ以外はachievementsに
                    elif len(sentence) < 150 and sentence not in facts['achievements']:
                        facts['achievements'].append(sentence.strip() + '。')
                        break

        # 各カテゴリを最大3つに制限
        facts['achievements'] = facts['achievements'][:3]
        facts['numbers'] = facts['numbers'][:3]
        facts['works'] = facts['works'][:5]

        # 空のリストは削除
        return {k: v for k, v in facts.items() if v}

    def collect_all_missing_persons(self) -> Dict:
        """全ての不足人物のデータを収集"""
        print(f"📚 Wikipedia事実データ収集開始")
        print(f"収集対象: {len(self.missing_persons)}人")
        print("=" * 60)

        collected_count = 0
        failed_persons = []

        for i, (person_name, category, keywords) in enumerate(self.missing_persons, 1):
            print(f"\n[{i}/{len(self.missing_persons)}] {person_name} ({category})")

            facts = self.search_wikipedia(person_name, keywords)

            if facts and any(facts.values()):
                self.collected_data[person_name] = {'facts': facts}
                collected_count += 1
                print(f"  ✅ データ収集成功")
                print(f"     achievements: {len(facts.get('achievements', []))}件")
                print(f"     numbers: {len(facts.get('numbers', []))}件")
                print(f"     works: {len(facts.get('works', []))}件")
            else:
                failed_persons.append(person_name)
                print(f"  ❌ データ収集失敗")

        print("\n" + "=" * 60)
        print(f"収集完了: {collected_count}/{len(self.missing_persons)}人")

        if failed_persons:
            print(f"\n失敗した人物 ({len(failed_persons)}人):")
            for name in failed_persons[:10]:
                print(f"  - {name}")

        return self.collected_data

    def merge_and_save(self):
        """既存データと新規データをマージして保存"""
        # 既存データと新規データをマージ
        all_data = self.existing_data.copy()
        all_data.update(self.collected_data)

        # 完全なデータベースを作成
        complete_database = {
            "persons": all_data,
            "metadata": {
                "total_persons": len(all_data),
                "last_updated": datetime.now().isoformat(),
                "sources": ["Wikipedia API", "Manual Entry"],
                "version": "2.0"
            }
        }

        # 保存
        output_file = 'expanded_person_facts_v2.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_database, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 拡張データベース保存: {output_file}")
        print(f"   総人物数: {len(all_data)}人")
        print(f"   新規追加: {len(self.collected_data)}人")
        print(f"   既存保持: {len(self.existing_data)}人")

        return output_file

def main():
    """メイン処理"""
    collector = WikipediaFactCollector()

    # データ収集
    collected_data = collector.collect_all_missing_persons()

    if collected_data:
        # データ保存
        output_file = collector.merge_and_save()

        # サンプル表示
        print("\n📝 収集データサンプル（最初の3人）:")
        for i, (name, data) in enumerate(list(collected_data.items())[:3], 1):
            print(f"\n{i}. {name}:")
            facts = data.get('facts', {})
            for key, values in facts.items():
                if values:
                    print(f"  {key}: {values[0][:100]}...")

if __name__ == "__main__":
    main()
