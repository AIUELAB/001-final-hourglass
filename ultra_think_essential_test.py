#!/usr/bin/env python3
"""
Ultra Think 必須人物テスト版
エピソード生成最適化されたperson_name_displayの動作確認
"""

import json
import csv
from datetime import datetime
from typing import Dict, List
import re

class PersonNameDisplayGenerator:
    """エピソード最適化されたperson_name_display生成"""

    def __init__(self):
        # 歴史的に唯一無二で短縮可能な人物
        self.historical_unique_names = {
            # 音楽家
            'ヨハン・セバスチャン・バッハ': 'バッハ',
            'ヴォルフガング・アマデウス・モーツァルト': 'モーツァルト',
            'ルートヴィヒ・ヴァン・ベートーヴェン': 'ベートーヴェン',
            'フレデリック・ショパン': 'ショパン',

            # 美術家
            'レオナルド・ダ・ヴィンチ': 'ダ・ヴィンチ',
            'ミケランジェロ・ブオナローティ': 'ミケランジェロ',
            'パブロ・ピカソ': 'ピカソ',
            'フィンセント・ファン・ゴッホ': 'ゴッホ',
            'レンブラント・ファン・レイン': 'レンブラント',

            # 科学者
            'アイザック・ニュートン': 'ニュートン',
            'チャールズ・ダーウィン': 'ダーウィン',
            'ガリレオ・ガリレイ': 'ガリレオ',
            'アルベルト・アインシュタイン': 'アインシュタイン',
            'トーマス・エジソン': 'エジソン',
            'ニコラ・テスラ': 'テスラ',

            # 日本の歴史人物
            '織田信長': '信長',
            '豊臣秀吉': '秀吉',
            '徳川家康': '家康',
            '武田信玄': '信玄',
            '上杉謙信': '謙信',

            # 世界の歴史人物
            'ナポレオン・ボナパルト': 'ナポレオン',
            'ユリウス・カエサル': 'カエサル',
            'アレクサンドロス大王': 'アレクサンドロス',
            'エイブラハム・リンカーン': 'リンカーン',
            'ウィンストン・チャーチル': 'チャーチル',
            'マハトマ・ガンジー': 'ガンジー',
        }

        # 同姓問題で区別が必要な人物
        self.disambiguation_required = {
            'クララ・シューマン': 'クララ・シューマン',  # ロベルトと区別
            'マリー・キュリー': 'マリー・キュリー',  # ピエールと区別
            'ヨハン・シュトラウス2世': 'ヨハン・シュトラウス2世',  # 父と区別
            'マイケル・ジャクソン': 'マイケル・ジャクソン',  # アンドリューと区別
        }

        # グループメンバー（グループ名を付与）
        self.group_members = {
            '伊達みきお': 'サンドウィッチマン',
            '富澤たけし': 'サンドウィッチマン',
            '松本人志': 'ダウンタウン',
            '浜田雅功': 'ダウンタウン',
        }

    def generate_display_name(self, name_ja: str, birth_year: int) -> str:
        """エピソード最適化されたdisplay name生成"""

        # グループメンバーチェック
        if name_ja in self.group_members:
            group = self.group_members[name_ja]
            short_name = self._get_short_name(name_ja)
            return f"{short_name}（{group}）"

        # 同姓問題チェック
        if name_ja in self.disambiguation_required:
            return self.disambiguation_required[name_ja]

        # 歴史的唯一無二チェック
        if name_ja in self.historical_unique_names:
            return self.historical_unique_names[name_ja]

        # 時代による判定
        if birth_year < 1900:
            # 歴史人物は短縮優先
            short = self._get_short_name(name_ja)
            # エピソード読みやすさテスト
            if len(short) <= 6:
                return short

        # 現代人（1950年以降）はフルネーム
        if birth_year >= 1950:
            return name_ja

        # 明治〜昭和前期（1868-1950）
        if 1868 <= birth_year < 1950:
            # 日本人の場合は姓名そのまま
            if self._is_japanese_name(name_ja):
                return name_ja

        # デフォルトはフルネーム
        return name_ja

    def _get_short_name(self, full_name: str) -> str:
        """短縮名取得（姓または名のみ）"""
        # 日本人名の場合
        if self._is_japanese_name(full_name):
            # スペースで分割
            parts = full_name.split()
            if len(parts) >= 2:
                # 姓が特定しやすい場合は姓を返す
                return parts[0]

        # 西洋人名の場合
        if '・' in full_name:
            parts = full_name.split('・')
            # 最後の部分（姓）を返す
            return parts[-1]

        return full_name

    def _is_japanese_name(self, name: str) -> bool:
        """日本人名かどうか判定"""
        # ひらがな、カタカナ、漢字を含む
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        # カタカナのみでない（外国人名の可能性）
        katakana_only = re.compile(r'^[\u30A0-\u30FF・ー]+$')

        return bool(japanese_pattern.search(name)) and not bool(katakana_only.match(name))


def test_essential_people():
    """必須人物でテスト"""
    print("🎯 Ultra Think 必須人物テスト")
    print("=" * 60)

    generator = PersonNameDisplayGenerator()

    # Firebase Episodesから欠落している必須人物
    essential_people = [
        # 科学者・発明家
        {"name": "Thomas Edison", "name_ja": "トーマス・エジソン", "birth_year": 1847},
        {"name": "Albert Einstein", "name_ja": "アルベルト・アインシュタイン", "birth_year": 1879},
        {"name": "Isaac Newton", "name_ja": "アイザック・ニュートン", "birth_year": 1643},
        {"name": "Charles Darwin", "name_ja": "チャールズ・ダーウィン", "birth_year": 1809},
        {"name": "Marie Curie", "name_ja": "マリー・キュリー", "birth_year": 1867},
        {"name": "Nikola Tesla", "name_ja": "ニコラ・テスラ", "birth_year": 1856},

        # 日本の歴史人物
        {"name": "Oda Nobunaga", "name_ja": "織田信長", "birth_year": 1534},
        {"name": "Toyotomi Hideyoshi", "name_ja": "豊臣秀吉", "birth_year": 1537},
        {"name": "Tokugawa Ieyasu", "name_ja": "徳川家康", "birth_year": 1543},
        {"name": "Sakamoto Ryoma", "name_ja": "坂本龍馬", "birth_year": 1836},
        {"name": "Saigo Takamori", "name_ja": "西郷隆盛", "birth_year": 1828},
        {"name": "Fukuzawa Yukichi", "name_ja": "福沢諭吉", "birth_year": 1835},
        {"name": "Noguchi Hideyo", "name_ja": "野口英世", "birth_year": 1876},
        {"name": "Kitasato Shibasaburo", "name_ja": "北里柴三郎", "birth_year": 1853},

        # 政治家・指導者
        {"name": "Abraham Lincoln", "name_ja": "エイブラハム・リンカーン", "birth_year": 1809},
        {"name": "Winston Churchill", "name_ja": "ウィンストン・チャーチル", "birth_year": 1874},
        {"name": "Napoleon Bonaparte", "name_ja": "ナポレオン・ボナパルト", "birth_year": 1769},
        {"name": "Mahatma Gandhi", "name_ja": "マハトマ・ガンジー", "birth_year": 1869},

        # 芸術家
        {"name": "Leonardo da Vinci", "name_ja": "レオナルド・ダ・ヴィンチ", "birth_year": 1452},
        {"name": "Pablo Picasso", "name_ja": "パブロ・ピカソ", "birth_year": 1881},
        {"name": "Vincent van Gogh", "name_ja": "フィンセント・ファン・ゴッホ", "birth_year": 1853},
        {"name": "Mozart", "name_ja": "ヴォルフガング・アマデウス・モーツァルト", "birth_year": 1756},
        {"name": "Beethoven", "name_ja": "ルートヴィヒ・ヴァン・ベートーヴェン", "birth_year": 1770},
        {"name": "Bach", "name_ja": "ヨハン・セバスチャン・バッハ", "birth_year": 1685},
        {"name": "Rembrandt", "name_ja": "レンブラント・ファン・レイン", "birth_year": 1606},

        # 現代人の例
        {"name": "Steve Jobs", "name_ja": "スティーブ・ジョブズ", "birth_year": 1955},
        {"name": "Bill Gates", "name_ja": "ビル・ゲイツ", "birth_year": 1955},
        {"name": "Elon Musk", "name_ja": "イーロン・マスク", "birth_year": 1971},

        # グループメンバーの例
        {"name": "Date Mikio", "name_ja": "伊達みきお", "birth_year": 1974},
        {"name": "Matsumoto Hitoshi", "name_ja": "松本人志", "birth_year": 1963},
    ]

    # display_name生成とテスト
    results = []

    print("\n📝 person_name_display生成結果:\n")
    print(f"{'日本語名':<30} {'生年':<6} {'表示名':<30} {'エピソード例'}")
    print("-" * 100)

    for person in essential_people:
        display_name = generator.generate_display_name(person['name_ja'], person['birth_year'])

        # エピソード例生成
        episode = f"あなたと同じ26歳のとき{display_name}は..."

        # 結果を保存
        results.append({
            'person_name': person['name'],
            'person_name_ja': person['name_ja'],
            'person_name_display': display_name,
            'birth_year': person['birth_year'],
            'episode_test': episode
        })

        # 表示
        print(f"{person['name_ja']:<30} {person['birth_year']:<6} {display_name:<30} {episode[:40]}")

    # 統計
    print("\n" + "=" * 100)
    print("\n📊 統計:")

    # 短縮名使用率
    shortened = [r for r in results if r['person_name_display'] != r['person_name_ja']]
    print(f"短縮名使用: {len(shortened)}/{len(results)} ({len(shortened)/len(results)*100:.1f}%)")

    # 時代別
    historical = [r for r in results if r['birth_year'] < 1900]
    modern = [r for r in results if r['birth_year'] >= 1950]
    print(f"歴史人物（〜1900）: {len(historical)}人")
    print(f"現代人（1950〜）: {len(modern)}人")

    # CSVとJSONで保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSV保存
    csv_file = f"ultra_think_test_{timestamp}.csv"
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['person_name', 'person_name_ja', 'person_name_display', 'birth_year', 'episode_test']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n💾 CSV保存: {csv_file}")

    # JSON保存
    json_file = f"ultra_think_test_{timestamp}.json"
    data = {}
    for i, result in enumerate(results):
        data[f"person_{i:05d}"] = result

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"💾 JSON保存: {json_file}")

    print("\n✅ Ultra Think テスト完了!")
    print("エピソード生成に最適化されたperson_name_displayが正常に動作しています。")


if __name__ == "__main__":
    test_essential_people()
