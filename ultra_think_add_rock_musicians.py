#!/usr/bin/env python3
"""
Ultra Think ロック/音楽アーティスト追加システム
欠落していた重要音楽アーティストを追加
"""
import csv
import json
from datetime import datetime
from typing import Dict, List
import os

class UltraThinkRockMusiciansAdder:
    def __init__(self):
        # クラシックロック/ハードロック
        self.classic_rock = [
            {
                "person_name": "Flea",
                "person_name_ja": "フリー",
                "person_name_display": "フリー（レッド・ホット・チリ・ペッパーズ）",
                "category": "エンタメ",
                "nationality": "オーストラリア/アメリカ",
                "occupation": "ベーシスト",
                "era": "現代",
                "name_recognition": 85,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1962,
                "note": "本名マイケル・バルザリー、RHCP創設メンバー"
            },
            {
                "person_name": "Ritchie Blackmore",
                "person_name_ja": "リッチー・ブラックモア",
                "person_name_display": "リッチー・ブラックモア",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 88,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1945,
                "note": "ディープ・パープル、レインボー創設者"
            },
            {
                "person_name": "Jon Lord",
                "person_name_ja": "ジョン・ロード",
                "person_name_display": "ジョン・ロード",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "キーボーディスト",
                "era": "現代",
                "name_recognition": 82,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1941,
                "death_year": 2012,
                "note": "ディープ・パープル、ハモンドオルガンの名手"
            },
            {
                "person_name": "Ian Gillan",
                "person_name_ja": "イアン・ギラン",
                "person_name_display": "イアン・ギラン",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 81,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1945,
                "note": "ディープ・パープル、黄金期のボーカル"
            },
            {
                "person_name": "Ian Paice",
                "person_name_ja": "イアン・ペイス",
                "person_name_display": "イアン・ペイス",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ドラマー",
                "era": "現代",
                "name_recognition": 79,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1948,
                "note": "ディープ・パープル唯一のオリジナルメンバー"
            },
            {
                "person_name": "Roger Glover",
                "person_name_ja": "ロジャー・グローヴァー",
                "person_name_display": "ロジャー・グローヴァー",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ベーシスト",
                "era": "現代",
                "name_recognition": 78,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1945,
                "note": "ディープ・パープル、プロデューサーとしても活動"
            },
            {
                "person_name": "Anthony Kiedis",
                "person_name_ja": "アンソニー・キーディス",
                "person_name_display": "アンソニー・キーディス（RHCP）",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 84,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1962,
                "note": "レッド・ホット・チリ・ペッパーズ、フロントマン"
            },
            {
                "person_name": "Chad Smith",
                "person_name_ja": "チャド・スミス",
                "person_name_display": "チャド・スミス（RHCP）",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ドラマー",
                "era": "現代",
                "name_recognition": 80,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1961,
                "note": "レッド・ホット・チリ・ペッパーズ"
            },
            {
                "person_name": "John Frusciante",
                "person_name_ja": "ジョン・フルシアンテ",
                "person_name_display": "ジョン・フルシアンテ",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 83,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1970,
                "note": "レッド・ホット・チリ・ペッパーズ"
            }
        ]
        
        # ヘヴィメタル/ネオクラシカル
        self.heavy_metal = [
            {
                "person_name": "Yngwie Malmsteen",
                "person_name_ja": "イングヴェイ・マルムスティーン",
                "person_name_display": "イングヴェイ・マルムスティーン",
                "category": "エンタメ",
                "nationality": "スウェーデン",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 86,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1963,
                "note": "ネオクラシカルメタルの創始者"
            },
            {
                "person_name": "Randy Rhoads",
                "person_name_ja": "ランディ・ローズ",
                "person_name_display": "ランディ・ローズ",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 87,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1956,
                "death_year": 1982,
                "note": "オジー・オズボーン・バンド、伝説のギタリスト"
            },
            {
                "person_name": "Zakk Wylde",
                "person_name_ja": "ザック・ワイルド",
                "person_name_display": "ザック・ワイルド",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 82,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1967,
                "note": "オジー・オズボーン・バンド、ブラック・レーベル・ソサイアティ"
            },
            {
                "person_name": "Tony Iommi",
                "person_name_ja": "トニー・アイオミ",
                "person_name_display": "トニー・アイオミ",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 88,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1948,
                "note": "ブラック・サバス、ヘヴィメタルの創始者"
            },
            {
                "person_name": "Dio",
                "person_name_ja": "ディオ",
                "person_name_display": "ロニー・ジェイムス・ディオ",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 85,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1942,
                "death_year": 2010,
                "note": "レインボー、ブラック・サバス"
            }
        ]
        
        # アメリカンロック
        self.american_rock = [
            {
                "person_name": "Steven Tyler",
                "person_name_ja": "スティーヴン・タイラー",
                "person_name_display": "スティーヴン・タイラー",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 90,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1948,
                "note": "エアロスミス、フロントマン"
            },
            {
                "person_name": "Joe Perry",
                "person_name_ja": "ジョー・ペリー",
                "person_name_display": "ジョー・ペリー（エアロスミス）",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 84,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1950,
                "note": "エアロスミス、リードギター"
            },
            {
                "person_name": "Steve Perry",
                "person_name_ja": "スティーブ・ペリー",
                "person_name_display": "スティーブ・ペリー",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 86,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1949,
                "note": "ジャーニー、黄金期のボーカル"
            },
            {
                "person_name": "Neal Schon",
                "person_name_ja": "ニール・ショーン",
                "person_name_display": "ニール・ショーン",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 82,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1954,
                "note": "ジャーニー、創設メンバー"
            },
            {
                "person_name": "Brad Whitford",
                "person_name_ja": "ブラッド・ウィットフォード",
                "person_name_display": "ブラッド・ウィットフォード",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 78,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1952,
                "note": "エアロスミス、リズムギター"
            }
        ]
        
        # 現代音楽/エレクトロニック
        self.modern_electronic = [
            {
                "person_name": "Steve Aoki",
                "person_name_ja": "スティーブ・アオキ",
                "person_name_display": "スティーブ・アオキ",
                "category": "エンタメ",
                "nationality": "アメリカ",
                "occupation": "DJ/プロデューサー",
                "era": "現代",
                "name_recognition": 87,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1977,
                "note": "EDMアーティスト、Dim Mak Records創設者"
            },
            {
                "person_name": "Enya",
                "person_name_ja": "エンヤ",
                "person_name_display": "エンヤ",
                "category": "エンタメ",
                "nationality": "アイルランド",
                "occupation": "歌手/作曲家",
                "era": "現代",
                "name_recognition": 89,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1961,
                "note": "ニューエイジ音楽の代表的アーティスト"
            },
            {
                "person_name": "Henryk Gorecki",
                "person_name_ja": "ヘンリク・グレツキ",
                "person_name_display": "ヘンリク・グレツキ",
                "category": "エンタメ",
                "nationality": "ポーランド",
                "occupation": "作曲家",
                "era": "現代",
                "name_recognition": 75,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1933,
                "death_year": 2010,
                "note": "現代クラシック作曲家、交響曲第3番「悲歌のシンフォニー」"
            },
            {
                "person_name": "David Guetta",
                "person_name_ja": "デヴィッド・ゲッタ",
                "person_name_display": "デヴィッド・ゲッタ",
                "category": "エンタメ",
                "nationality": "フランス",
                "occupation": "DJ/プロデューサー",
                "era": "現代",
                "name_recognition": 88,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1967,
                "note": "世界的EDMアーティスト"
            },
            {
                "person_name": "Calvin Harris",
                "person_name_ja": "カルヴィン・ハリス",
                "person_name_display": "カルヴィン・ハリス",
                "category": "エンタメ",
                "nationality": "スコットランド",
                "occupation": "DJ/プロデューサー",
                "era": "現代",
                "name_recognition": 86,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1984,
                "note": "EDMアーティスト、プロデューサー"
            },
            {
                "person_name": "Deadmau5",
                "person_name_ja": "デッドマウス",
                "person_name_display": "デッドマウス",
                "category": "エンタメ",
                "nationality": "カナダ",
                "occupation": "DJ/プロデューサー",
                "era": "現代",
                "name_recognition": 84,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1981,
                "note": "プログレッシブハウスDJ"
            },
            {
                "person_name": "Armin van Buuren",
                "person_name_ja": "アーミン・ヴァン・ブーレン",
                "person_name_display": "アーミン・ヴァン・ブーレン",
                "category": "エンタメ",
                "nationality": "オランダ",
                "occupation": "DJ/プロデューサー",
                "era": "現代",
                "name_recognition": 83,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1976,
                "note": "トランスDJ、A State of Trance"
            }
        ]
        
        # ビートルズメンバー（ジョン・レノン以外）
        self.beatles_members = [
            {
                "person_name": "Paul McCartney",
                "person_name_ja": "ポール・マッカートニー",
                "person_name_display": "ポール・マッカートニー（ビートルズ）",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ミュージシャン",
                "era": "現代",
                "name_recognition": 95,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1942,
                "note": "ビートルズ、ウイングス"
            },
            {
                "person_name": "George Harrison",
                "person_name_ja": "ジョージ・ハリスン",
                "person_name_display": "ジョージ・ハリスン（ビートルズ）",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ミュージシャン",
                "era": "現代",
                "name_recognition": 91,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1943,
                "death_year": 2001,
                "note": "ビートルズ、リードギター"
            },
            {
                "person_name": "Ringo Starr",
                "person_name_ja": "リンゴ・スター",
                "person_name_display": "リンゴ・スター（ビートルズ）",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ドラマー",
                "era": "現代",
                "name_recognition": 90,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1940,
                "note": "ビートルズ、本名リチャード・スターキー"
            }
        ]
        
        # ローリング・ストーンズ
        self.rolling_stones = [
            {
                "person_name": "Mick Jagger",
                "person_name_ja": "ミック・ジャガー",
                "person_name_display": "ミック・ジャガー",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 93,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1943,
                "note": "ローリング・ストーンズ、フロントマン"
            },
            {
                "person_name": "Keith Richards",
                "person_name_ja": "キース・リチャーズ",
                "person_name_display": "キース・リチャーズ",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 91,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1943,
                "note": "ローリング・ストーンズ、リードギター"
            },
            {
                "person_name": "Charlie Watts",
                "person_name_ja": "チャーリー・ワッツ",
                "person_name_display": "チャーリー・ワッツ",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ドラマー",
                "era": "現代",
                "name_recognition": 86,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1941,
                "death_year": 2021,
                "note": "ローリング・ストーンズ"
            },
            {
                "person_name": "Ronnie Wood",
                "person_name_ja": "ロニー・ウッド",
                "person_name_display": "ロニー・ウッド",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 84,
                "accuracy_score": 5,
                "impact_score": 4,
                "birth_year": 1947,
                "note": "ローリング・ストーンズ、元フェイセズ"
            }
        ]
        
        # レッド・ツェッペリン
        self.led_zeppelin = [
            {
                "person_name": "Robert Plant",
                "person_name_ja": "ロバート・プラント",
                "person_name_display": "ロバート・プラント",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ボーカリスト",
                "era": "現代",
                "name_recognition": 90,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1948,
                "note": "レッド・ツェッペリン"
            },
            {
                "person_name": "Jimmy Page",
                "person_name_ja": "ジミー・ペイジ",
                "person_name_display": "ジミー・ペイジ",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ギタリスト",
                "era": "現代",
                "name_recognition": 92,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1944,
                "note": "レッド・ツェッペリン、プロデューサー"
            },
            {
                "person_name": "John Paul Jones",
                "person_name_ja": "ジョン・ポール・ジョーンズ",
                "person_name_display": "ジョン・ポール・ジョーンズ",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ベーシスト/キーボーディスト",
                "era": "現代",
                "name_recognition": 85,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1946,
                "note": "レッド・ツェッペリン"
            },
            {
                "person_name": "John Bonham",
                "person_name_ja": "ジョン・ボーナム",
                "person_name_display": "ジョン・ボーナム",
                "category": "エンタメ",
                "nationality": "イギリス",
                "occupation": "ドラマー",
                "era": "現代",
                "name_recognition": 88,
                "accuracy_score": 5,
                "impact_score": 5,
                "birth_year": 1948,
                "death_year": 1980,
                "note": "レッド・ツェッペリン、伝説のドラマー"
            }
        ]
        
        self.stats = {
            'total_input': 0,
            'musicians_added': 0,
            'total_output': 0
        }
    
    def generate_episode_id(self, person_idx: int) -> str:
        """エピソードID生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"EP_{timestamp}_RM{person_idx:04d}"
    
    def generate_person_id(self, current_max: int, idx: int) -> str:
        """person_ID生成"""
        return f"P{current_max + idx:06d}"
    
    def create_person_row(self, person: Dict, episode_id: str, person_id: str) -> Dict:
        """人物データを24フィールド形式に変換"""
        timestamp = datetime.now().isoformat()
        
        # 拡張データ
        extended_data = {
            "original_batch_id": "rock_musicians_addition",
            "cultural_significance": str(person.get('impact_score', 4) * 2),
            "educational_value": str(person.get('accuracy_score', 5)),
            "historical_impact": str(person.get('impact_score', 4)),
            "global_recognition": str(min(person.get('name_recognition', 70) / 10, 9)),
            "main_category": person.get('category', 'エンタメ'),
            "subcategory": "音楽",
            "is_fictional": "FALSE",
            "note": person.get('note', ''),
            "birth_year": person.get('birth_year', ''),
            "death_year": person.get('death_year', ''),
            "conversion_date": timestamp
        }
        
        return {
            "episode_id": episode_id,
            "person_id": person_id,
            "episode_hash": "",
            "person_name": person.get('person_name', ''),
            "person_name_ja": person.get('person_name_ja', ''),
            "person_name_display": person.get('person_name_display', ''),
            "episode_title": "",
            "episode_text": "",
            "episode_year": "",
            "episode_date": "",
            "episode_type": "",
            "age": "",
            "age_months": "",
            "category": person.get('category', 'エンタメ'),
            "nationality": person.get('nationality', ''),
            "occupation": person.get('occupation', ''),
            "era": person.get('era', '現代'),
            "name_recognition": str(person.get('name_recognition', 70)),
            "accuracy_score": str(person.get('accuracy_score', 5)),
            "impact_score": str(person.get('impact_score', 4)),
            "source": "Ultra Think Rock Musicians Addition",
            "created_at": timestamp,
            "is_published": "true",
            "extended_data": json.dumps(extended_data, ensure_ascii=False)
        }
    
    def process_and_add(self, input_file: str) -> str:
        """既存ファイルにロックミュージシャンを追加"""
        print("🎸 Ultra Think ロックミュージシャン追加開始...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_WITH_ROCK_MUSICIANS_{timestamp}.csv"
        
        # 1. 既存データ読み込み
        print("\n📂 既存データ読み込み中...")
        existing_rows = []
        fieldnames = None
        
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            existing_rows = list(reader)
            self.stats['total_input'] = len(existing_rows)
        
        print(f"  ✅ {self.stats['total_input']:,}件の既存データ読み込み完了")
        
        # 現在の最大person_id取得
        max_person_id = 0
        for row in existing_rows:
            pid = row.get('person_id', 'P000000')
            try:
                num = int(pid[1:])
                max_person_id = max(max_person_id, num)
            except (ValueError, IndexError):
                pass
        
        # 2. 新規データ作成
        print("\n🎯 ロックミュージシャン追加中...")
        new_rows = []
        person_idx = 1
        
        # 各カテゴリーの追加
        all_musicians = (
            self.classic_rock +
            self.heavy_metal +
            self.american_rock +
            self.modern_electronic +
            self.beatles_members +
            self.rolling_stones +
            self.led_zeppelin
        )
        
        print(f"  📌 {len(all_musicians)}名のミュージシャンを追加...")
        for musician in all_musicians:
            episode_id = self.generate_episode_id(person_idx)
            person_id = self.generate_person_id(max_person_id, person_idx)
            new_row = self.create_person_row(musician, episode_id, person_id)
            new_rows.append(new_row)
            self.stats['musicians_added'] += 1
            person_idx += 1
        
        print(f"  ✅ {len(new_rows)}名の新規ミュージシャンを追加")
        
        # 3. データ統合と書き出し
        print("\n📝 統合データ書き出し中...")
        all_rows = existing_rows + new_rows
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in all_rows:
                writer.writerow(row)
                self.stats['total_output'] += 1
        
        print(f"  ✅ 書き出し完了: {self.stats['total_output']:,}件")
        
        # 4. レポート作成
        self.create_report(timestamp, output_file, input_file)
        
        return output_file
    
    def create_report(self, timestamp: str, output_file: str, input_file: str):
        """追加レポート作成"""
        report = f"""# 🎸 Ultra Think ロックミュージシャン追加レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- 入力ファイル: {input_file}
- 出力ファイル: {output_file}

## 📊 追加統計

### 追加結果
- **既存データ数**: {self.stats['total_input']:,}件
- **ミュージシャン追加**: {self.stats['musicians_added']:,}名
- **最終出力数**: {self.stats['total_output']:,}件

## ✅ 追加された主要アーティスト

### レッド・ホット・チリ・ペッパーズ
- フリー（マイケル・バルザリー）
- アンソニー・キーディス
- チャド・スミス
- ジョン・フルシアンテ

### ディープ・パープル
- リッチー・ブラックモア
- ジョン・ロード
- イアン・ギラン
- イアン・ペイス
- ロジャー・グローヴァー

### アメリカンロック
- スティーヴン・タイラー（エアロスミス）
- スティーブ・ペリー（ジャーニー）

### ヘヴィメタル/ネオクラシカル
- イングヴェイ・マルムスティーン
- ランディ・ローズ
- トニー・アイオミ（ブラック・サバス）

### 現代音楽/エレクトロニック
- スティーブ・アオキ
- エンヤ
- ヘンリク・グレツキ
- デヴィッド・ゲッタ
- カルヴィン・ハリス
- デッドマウス

### ビートルズ（完全版）
- ポール・マッカートニー
- ジョージ・ハリスン
- リンゴ・スター
- （ジョン・レノンは既存）

### ローリング・ストーンズ
- ミック・ジャガー
- キース・リチャーズ
- チャーリー・ワッツ
- ロニー・ウッド

### レッド・ツェッペリン
- ロバート・プラント
- ジミー・ペイジ
- ジョン・ポール・ジョーンズ
- ジョン・ボーナム

## 🏆 改善成果
ロック音楽史の重要人物が網羅され、
クラシックロックから現代EDMまでバランスよく表現されるようになりました。
"""
        
        report_file = f"ULTRA_THINK_ROCK_MUSICIANS_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📋 レポート: {report_file}")
        
        # 統計をJSON保存
        stats_file = f"ultra_think_rock_musicians_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        print(f"📊 統計: {stats_file}")

def main():
    adder = UltraThinkRockMusiciansAdder()
    
    # 入力ファイル（女子プロレスラー追加済みデータ）
    input_file = "ultra_think_WITH_FEMALE_WRESTLERS_20250827_061752.csv"
    
    # ファイル存在確認
    if not os.path.exists(input_file):
        print(f"❌ ファイルが見つかりません: {input_file}")
        # 代替ファイルを試す
        input_file = "ultra_think_FINAL_CLEAN_20250827_060225.csv"
        if not os.path.exists(input_file):
            print(f"❌ 代替ファイルも見つかりません: {input_file}")
            return None
        print(f"  📌 代替ファイルを使用: {input_file}")
    
    # 処理実行
    output_file = adder.process_and_add(input_file)
    
    print("\n" + "=" * 50)
    print("✨ Ultra Think ロックミュージシャン追加完了!")
    print(f"📁 出力ファイル: {output_file}")
    print("=" * 50)
    
    return output_file

if __name__ == "__main__":
    main()