#!/usr/bin/env python3
"""
Ultra Think 強化版コレクター
見逃されていた有名人を徹底収集
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Any
import random


class EnhancedCelebrityCollector:
    """強化版有名人コレクター"""

    def __init__(self):
        self.categories = {
            'エンタメ': self._generate_entertainers,
            'スポーツ': self._generate_athletes,
            '学術・科学': self._generate_academics,
            'ビジネス': self._generate_business,
            '文化・芸術': self._generate_artists,
            '歴史上の人物': self._generate_historical,
            'インフルエンサー': self._generate_influencers,
            'テクノロジー': self._generate_tech,
            '政治': self._generate_politicians,
            '社会活動家': self._generate_activists
        }

        self.missing_patterns = {
            '女性タレント': ['女優', 'モデル', 'アイドル', 'グラビア'],
            '男性タレント': ['俳優', 'モデル', 'アイドル'],
            'お笑い芸人': ['ピン芸人', 'コンビ', 'トリオ'],
            'ミュージシャン': ['バンド', 'ソロ', 'DJ', 'プロデューサー'],
            'YouTuber': ['ゲーム実況', 'Vlog', '教育', 'エンタメ'],
            'スポーツ選手': ['野球', 'サッカー', 'テニス', 'ゴルフ', '格闘技'],
            '作家': ['小説家', '漫画家', 'ライトノベル', 'エッセイスト'],
            '声優': ['男性声優', '女性声優', 'ナレーター'],
            '料理人': ['シェフ', 'パティシエ', '和食', 'フレンチ']
        }

    def _generate_entertainers(self, count: int = 100) -> List[Dict[str, Any]]:
        """エンタメ系の追加生成"""
        entertainers = []

        # 見逃されていた日本のタレント
        japanese_entertainers = [
            {'name': '中居正広', 'name_ja': '中居正広', 'occupation': '司会者・元SMAP',
             'recognition': 95},
            {'name': '木村拓哉', 'name_ja': '木村拓哉', 'occupation': '俳優・元SMAP',
             'recognition': 98},
            {'name': '香取慎吾', 'name_ja': '香取慎吾', 'occupation': 'タレント・元SMAP',
             'recognition': 90},
            {'name': '草彅剛', 'name_ja': '草彅剛', 'occupation': '俳優・元SMAP',
             'recognition': 90},
            {'name': '稲垣吾郎', 'name_ja': '稲垣吾郎', 'occupation': 'タレント・元SMAP',
             'recognition': 85},

            # ジャニーズ系
            {'name': '山下智久', 'name_ja': '山下智久', 'occupation': '俳優・歌手',
             'recognition': 85},
            {'name': '亀梨和也', 'name_ja': '亀梨和也', 'occupation': 'タレント・KAT-TUN',
             'recognition': 80},
            {'name': '中島健人', 'name_ja': '中島健人', 'occupation': 'アイドル・Sexy Zone',
             'recognition': 75},
            {'name': '平野紫耀', 'name_ja': '平野紫耀', 'occupation': 'アイドル・元King & Prince',
             'recognition': 80},

            # 女性タレント
            {'name': '石原さとみ', 'name_ja': '石原さとみ', 'occupation': '女優',
             'recognition': 90},
            {'name': '北川景子', 'name_ja': '北川景子', 'occupation': '女優',
             'recognition': 88},
            {'name': '深田恭子', 'name_ja': '深田恭子', 'occupation': '女優',
             'recognition': 85},
            {'name': '長澤まさみ', 'name_ja': '長澤まさみ', 'occupation': '女優',
             'recognition': 88},
            {'name': '戸田恵梨香', 'name_ja': '戸田恵梨香', 'occupation': '女優',
             'recognition': 85},

            # ベテラン俳優
            {'name': '渡辺謙', 'name_ja': '渡辺謙', 'occupation': '俳優',
             'recognition': 90},
            {'name': '真田広之', 'name_ja': '真田広之', 'occupation': '俳優',
             'recognition': 85},
            {'name': '役所広司', 'name_ja': '役所広司', 'occupation': '俳優',
             'recognition': 88},
            {'name': '西田敏行', 'name_ja': '西田敏行', 'occupation': '俳優',
             'recognition': 90},

            # 若手俳優
            {'name': '菅田将暉', 'name_ja': '菅田将暉', 'occupation': '俳優・歌手',
             'recognition': 85},
            {'name': '神木隆之介', 'name_ja': '神木隆之介', 'occupation': '俳優',
             'recognition': 85},
            {'name': '山崎賢人', 'name_ja': '山崎賢人', 'occupation': '俳優',
             'recognition': 80},
            {'name': '吉沢亮', 'name_ja': '吉沢亮', 'occupation': '俳優',
             'recognition': 78},

            # お笑い（追加）
            {'name': 'みやぞん', 'name_ja': 'みやぞん', 'occupation': 'お笑い芸人・ANZEN漫才',
             'recognition': 75},
            {'name': 'あらぽん', 'name_ja': 'あらぽん', 'occupation': 'お笑い芸人・ANZEN漫才',
             'recognition': 65},
            {'name': 'カズレーザー', 'name_ja': 'カズレーザー', 'occupation': 'お笑い芸人・メイプル超合金',
             'recognition': 80},
            {'name': '安藤なつ', 'name_ja': '安藤なつ', 'occupation': 'お笑い芸人・メイプル超合金',
             'recognition': 70},

            # 声優
            {'name': '花澤香菜', 'name_ja': '花澤香菜', 'occupation': '声優',
             'recognition': 70},
            {'name': '梶裕貴', 'name_ja': '梶裕貴', 'occupation': '声優',
             'recognition': 68},
            {'name': '神谷浩史', 'name_ja': '神谷浩史', 'occupation': '声優',
             'recognition': 65},
            {'name': '水樹奈々', 'name_ja': '水樹奈々', 'occupation': '声優・歌手',
             'recognition': 70},
        ]

        for person in japanese_entertainers[:min(count, len(japanese_entertainers))]:
            entertainers.append({
                'person_name': person['name'],
                'person_name_ja': person['name_ja'],
                'person_name_display': person['name_ja'],
                'category': 'エンタメ',
                'nationality': '日本',
                'occupation': person['occupation'],
                'name_recognition': str(person['recognition'])
            })

        return entertainers

    def _generate_athletes(self, count: int = 100) -> List[Dict[str, Any]]:
        """スポーツ選手の追加生成"""
        athletes = []

        # 見逃されていたアスリート
        missing_athletes = [
            # 野球
            {'name': '大谷翔平', 'name_ja': '大谷翔平', 'sport': '野球',
             'recognition': 95},
            {'name': 'ダルビッシュ有', 'name_ja': 'ダルビッシュ有', 'sport': '野球',
             'recognition': 90},
            {'name': '田中将大', 'name_ja': '田中将大', 'sport': '野球',
             'recognition': 85},
            {'name': '松井秀喜', 'name_ja': '松井秀喜', 'sport': '野球',
             'recognition': 90},
            {'name': '王貞治', 'name_ja': '王貞治', 'sport': '野球',
             'recognition': 95},
            {'name': '長嶋茂雄', 'name_ja': '長嶋茂雄', 'sport': '野球',
             'recognition': 95},

            # サッカー
            {'name': '三笘薫', 'name_ja': '三笘薫', 'sport': 'サッカー',
             'recognition': 80},
            {'name': '久保建英', 'name_ja': '久保建英', 'sport': 'サッカー',
             'recognition': 78},
            {'name': '南野拓実', 'name_ja': '南野拓実', 'sport': 'サッカー',
             'recognition': 75},
            {'name': '中田英寿', 'name_ja': '中田英寿', 'sport': 'サッカー',
             'recognition': 85},
            {'name': '中村俊輔', 'name_ja': '中村俊輔', 'sport': 'サッカー',
             'recognition': 80},

            # テニス
            {'name': '錦織圭', 'name_ja': '錦織圭', 'sport': 'テニス',
             'recognition': 85},
            {'name': '大坂なおみ', 'name_ja': '大坂なおみ', 'sport': 'テニス',
             'recognition': 90},

            # フィギュアスケート
            {'name': '羽生結弦', 'name_ja': '羽生結弦', 'sport': 'フィギュアスケート',
             'recognition': 95},
            {'name': '浅田真央', 'name_ja': '浅田真央', 'sport': 'フィギュアスケート',
             'recognition': 90},
            {'name': '宇野昌磨', 'name_ja': '宇野昌磨', 'sport': 'フィギュアスケート',
             'recognition': 75},

            # ゴルフ
            {'name': '松山英樹', 'name_ja': '松山英樹', 'sport': 'ゴルフ',
             'recognition': 80},
            {'name': '渋野日向子', 'name_ja': '渋野日向子', 'sport': 'ゴルフ',
             'recognition': 75},

            # 水泳
            {'name': '北島康介', 'name_ja': '北島康介', 'sport': '水泳',
             'recognition': 85},
            {'name': '池江璃花子', 'name_ja': '池江璃花子', 'sport': '水泳',
             'recognition': 80},

            # 格闘技
            {'name': '井上尚弥', 'name_ja': '井上尚弥', 'sport': 'ボクシング',
             'recognition': 80},
            {'name': '村田諒太', 'name_ja': '村田諒太', 'sport': 'ボクシング',
             'recognition': 70},
            {'name': '朝倉未来', 'name_ja': '朝倉未来', 'sport': '総合格闘技',
             'recognition': 75},
            {'name': '朝倉海', 'name_ja': '朝倉海', 'sport': '総合格闘技',
             'recognition': 70},
        ]

        for athlete in missing_athletes[:min(count, len(missing_athletes))]:
            athletes.append({
                'person_name': athlete['name'],
                'person_name_ja': athlete['name_ja'],
                'person_name_display': athlete['name_ja'],
                'category': 'スポーツ',
                'nationality': '日本',
                'occupation': f"{athlete['sport']}選手",
                'name_recognition': str(athlete['recognition'])
            })

        return athletes

    def _generate_academics(self, count: int = 50) -> List[Dict[str, Any]]:
        """学術・科学者の追加生成"""
        academics = []

        # ノーベル賞受賞者
        nobel_winners = [
            {'name': '山中伸弥', 'name_ja': '山中伸弥', 'field': 'iPS細胞研究',
             'recognition': 85},
            {'name': '本庶佑', 'name_ja': '本庶佑', 'field': '免疫学',
             'recognition': 75},
            {'name': '大村智', 'name_ja': '大村智', 'field': '化学',
             'recognition': 70},
            {'name': '梶田隆章', 'name_ja': '梶田隆章', 'field': '物理学',
             'recognition': 65},
            {'name': '天野浩', 'name_ja': '天野浩', 'field': '半導体',
             'recognition': 60},
            {'name': '赤崎勇', 'name_ja': '赤崎勇', 'field': '半導体',
             'recognition': 60},
        ]

        for academic in nobel_winners:
            academics.append({
                'person_name': academic['name'],
                'person_name_ja': academic['name_ja'],
                'person_name_display': academic['name_ja'],
                'category': '学術・科学',
                'nationality': '日本',
                'occupation': f"{academic['field']}研究者",
                'name_recognition': str(academic['recognition'])
            })

        return academics

    def _generate_business(self, count: int = 50) -> List[Dict[str, Any]]:
        """ビジネス界の人物追加"""
        business_people = []

        japanese_business = [
            {'name': '孫正義', 'name_ja': '孫正義', 'company': 'ソフトバンク',
             'recognition': 90},
            {'name': '柳井正', 'name_ja': '柳井正', 'company': 'ファーストリテイリング',
             'recognition': 85},
            {'name': '三木谷浩史', 'name_ja': '三木谷浩史', 'company': '楽天',
             'recognition': 80},
            {'name': '前澤友作', 'name_ja': '前澤友作', 'company': 'ZOZO創業者',
             'recognition': 85},
            {'name': '堀江貴文', 'name_ja': '堀江貴文', 'company': '実業家',
             'recognition': 85},
        ]

        for person in japanese_business:
            business_people.append({
                'person_name': person['name'],
                'person_name_ja': person['name_ja'],
                'person_name_display': person['name_ja'],
                'category': 'ビジネス',
                'nationality': '日本',
                'occupation': f"{person['company']} 創業者/CEO",
                'name_recognition': str(person['recognition'])
            })

        return business_people

    def _generate_artists(self, count: int = 50) -> List[Dict[str, Any]]:
        """文化・芸術界の人物追加"""
        artists = []

        japanese_artists = [
            # 作家
            {'name': '村上春樹', 'name_ja': '村上春樹', 'field': '小説家',
             'recognition': 90},
            {'name': '東野圭吾', 'name_ja': '東野圭吾', 'field': '推理小説家',
             'recognition': 85},
            {'name': '宮部みゆき', 'name_ja': '宮部みゆき', 'field': '小説家',
             'recognition': 80},

            # 漫画家
            {'name': '尾田栄一郎', 'name_ja': '尾田栄一郎', 'field': '漫画家（ONE PIECE）',
             'recognition': 85},
            {'name': '岸本斉史', 'name_ja': '岸本斉史', 'field': '漫画家（NARUTO）',
             'recognition': 80},
            {'name': '諫山創', 'name_ja': '諫山創', 'field': '漫画家（進撃の巨人）',
             'recognition': 75},

            # 音楽家
            {'name': '坂本龍一', 'name_ja': '坂本龍一', 'field': '音楽家',
             'recognition': 85},
            {'name': '久石譲', 'name_ja': '久石譲', 'field': '作曲家',
             'recognition': 85},
            {'name': '小室哲哉', 'name_ja': '小室哲哉', 'field': '音楽プロデューサー',
             'recognition': 80},
        ]

        for artist in japanese_artists:
            artists.append({
                'person_name': artist['name'],
                'person_name_ja': artist['name_ja'],
                'person_name_display': artist['name_ja'],
                'category': '文化・芸術',
                'nationality': '日本',
                'occupation': artist['field'],
                'name_recognition': str(artist['recognition'])
            })

        return artists

    def _generate_historical(self, count: int = 30) -> List[Dict[str, Any]]:
        """歴史上の人物（追加）"""
        return []  # 既に十分収集済み

    def _generate_influencers(self, count: int = 50) -> List[Dict[str, Any]]:
        """インフルエンサー追加"""
        influencers = []

        japanese_influencers = [
            # YouTuber
            {'name': 'HIKAKIN', 'name_ja': 'ヒカキン', 'platform': 'YouTube',
             'recognition': 85},
            {'name': 'はじめしゃちょー', 'name_ja': 'はじめしゃちょー', 'platform': 'YouTube',
             'recognition': 80},
            {'name': "Fischer's", 'name_ja': 'フィッシャーズ', 'platform': 'YouTube',
             'recognition': 75},
            {'name': '東海オンエア', 'name_ja': '東海オンエア', 'platform': 'YouTube',
             'recognition': 75},
            {'name': 'ヒカル', 'name_ja': 'ヒカル', 'platform': 'YouTube',
             'recognition': 75},
            {'name': 'ラファエル', 'name_ja': 'ラファエル', 'platform': 'YouTube',
             'recognition': 70},

            # TikToker
            {'name': 'じゅんや', 'name_ja': 'じゅんや', 'platform': 'TikTok',
             'recognition': 65},
            {'name': '景井ひな', 'name_ja': '景井ひな', 'platform': 'TikTok',
             'recognition': 60},
        ]

        for influencer in japanese_influencers:
            influencers.append({
                'person_name': influencer['name'],
                'person_name_ja': influencer['name_ja'],
                'person_name_display': influencer['name_ja'],
                'category': 'インフルエンサー',
                'nationality': '日本',
                'occupation': f"{influencer['platform']}クリエイター",
                'name_recognition': str(influencer['recognition'])
            })

        return influencers

    def _generate_tech(self, count: int = 30) -> List[Dict[str, Any]]:
        """テクノロジー界の人物"""
        return []  # 後で実装

    def _generate_politicians(self, count: int = 30) -> List[Dict[str, Any]]:
        """政治家"""
        politicians = []

        japanese_politicians = [
            {'name': '岸田文雄', 'name_ja': '岸田文雄', 'position': '内閣総理大臣',
             'recognition': 85},
            {'name': '安倍晋三', 'name_ja': '安倍晋三', 'position': '元内閣総理大臣',
             'recognition': 95},
            {'name': '菅義偉', 'name_ja': '菅義偉', 'position': '元内閣総理大臣',
             'recognition': 80},
            {'name': '小泉進次郎', 'name_ja': '小泉進次郎', 'position': '衆議院議員',
             'recognition': 85},
            {'name': '河野太郎', 'name_ja': '河野太郎', 'position': 'デジタル大臣',
             'recognition': 80},
        ]

        for politician in japanese_politicians:
            politicians.append({
                'person_name': politician['name'],
                'person_name_ja': politician['name_ja'],
                'person_name_display': politician['name_ja'],
                'category': '政治',
                'nationality': '日本',
                'occupation': politician['position'],
                'name_recognition': str(politician['recognition'])
            })

        return politicians

    def _generate_activists(self, count: int = 20) -> List[Dict[str, Any]]:
        """社会活動家"""
        return []  # 後で実装

    def collect_all_categories(self, persons_per_category: int = 50) -> List[Dict[str, Any]]:
        """全カテゴリから収集"""
        all_persons = []

        for category, generator_func in self.categories.items():
            print(f"  📁 {category}カテゴリ生成中...")
            persons = generator_func(persons_per_category)
            all_persons.extend(persons)
            print(f"    ✅ {len(persons)}人追加")

        # メタデータ追加
        timestamp = datetime.now().isoformat()
        for i, person in enumerate(all_persons):
            if 'person_id' not in person:
                person['person_id'] = f"P{str(30000 + i).zfill(6)}"
            if 'episode_id' not in person:
                person['episode_id'] = f"EP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
            person['created_at'] = timestamp
            person['source'] = 'Ultra Think Enhanced Collector'

        return all_persons


def main():
    """メイン処理"""

    print("="*60)
    print("🚀 Ultra Think 強化版コレクター")
    print("="*60)

    # コレクター初期化
    collector = EnhancedCelebrityCollector()

    # 全カテゴリから収集
    print("\n📋 有名人収集開始...")
    all_persons = collector.collect_all_categories(persons_per_category=50)

    print(f"\n✅ 収集完了: {len(all_persons)}人")

    # 既存データベースと統合
    latest_db = 'ULTRA_THINK_COMEDIAN_EXPANDED_20250827_082620.csv'

    print(f"\n📊 既存データベースと統合中...")
    print(f"  ファイル: {latest_db}")

    # 既存データ読み込み
    existing_persons = []
    with open(latest_db, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]

        import io
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)
        existing_persons = list(reader)

    print(f"  既存: {len(existing_persons)}人")

    # 重複チェックして追加
    existing_names = set()
    for p in existing_persons:
        existing_names.add(p.get('person_name_ja', ''))
        existing_names.add(p.get('person_name', ''))

    # 最大ID取得
    max_id = 0
    for p in existing_persons:
        if p.get('person_id'):
            try:
                id_num = int(p['person_id'].replace('P', ''))
                max_id = max(max_id, id_num)
            except:
                pass

    added_count = 0
    for person in all_persons:
        name_ja = person.get('person_name_ja', '')
        name_en = person.get('person_name', '')

        if name_ja not in existing_names and name_en not in existing_names:
            max_id += 1
            person['person_id'] = f"P{str(max_id).zfill(6)}"

            # 既存のフィールド構造に合わせる
            if 'created_at' in person:
                del person['created_at']
            if 'source' in person:
                del person['source']

            existing_persons.append(person)
            existing_names.add(name_ja)
            existing_names.add(name_en)
            added_count += 1

    print(f"  追加: {added_count}人")
    print(f"  最終: {len(existing_persons)}人")

    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ULTRA_THINK_ENHANCED_{timestamp}.csv'

    # CSV保存
    if existing_persons:
        headers = list(existing_persons[0].keys())
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(existing_persons)

    print(f"\n✅ データベース保存: {output_file}")
    print(f"  最終人数: {len(existing_persons)}人")
    print(f"  12,410人最低ライン達成: {'✅' if len(existing_persons) >= 12410 else '❌'}（{len(existing_persons)/12410*100:.1f}%）")

    # サマリーレポート
    print("\n" + "="*60)
    print("📊 カテゴリ別統計")
    print("="*60)

    category_counts = {}
    for p in existing_persons:
        cat = p.get('category', 'その他')
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        bar = '█' * int(count / max(category_counts.values()) * 30)
        print(f"{cat:15} {bar} {count:5}人 ({count/len(existing_persons)*100:.1f}%)")

    print("="*60)


if __name__ == "__main__":
    main()
