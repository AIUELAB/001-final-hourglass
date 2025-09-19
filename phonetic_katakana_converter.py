#!/usr/bin/env python3
"""
音声ベースカタカナ変換システム
外国人名を言語別の発音規則に基づいてカタカナに変換
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class PhoneticKatakanaConverter:
    """音声ベースのカタカナ変換システム"""

    def __init__(self):
        # 言語別変換ルール
        self.conversion_rules = self.initialize_conversion_rules()
        self.translation_cache = self.load_cache()
        self.stats = {
            'processed': 0,
            'converted': 0,
            'cached': 0,
            'skipped': 0
        }

    def load_cache(self) -> Dict[str, Any]:
        """翻訳キャッシュを読み込み"""
        cache_file = Path('translation_cache.json')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        return {}

    def save_cache(self):
        """翻訳キャッシュを保存"""
        with open('translation_cache.json', 'w', encoding='utf-8') as f:
            json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)

    def initialize_conversion_rules(self) -> Dict[str, Any]:
        """言語別の音声変換ルールを初期化"""
        return {
            'german': {
                'patterns': [
                    # ドイツ語特有のパターン（単語境界を考慮）
                    (r'\bBach\b', 'バッハ'),
                    (r'berg$', 'ベルク'),
                    (r'burg$', 'ブルク'),
                    (r'stein$', 'シュタイン'),
                    (r'mann$', 'マン'),
                    (r'schmidt', 'シュミット'),
                    (r'müller', 'ミュラー'),
                    (r'wagner', 'ワーグナー'),
                    (r'sch', 'シュ'),
                    (r'ch', 'ヒ'),
                    (r'ck', 'ック'),
                    (r'z', 'ツ'),
                    (r'v', 'フ'),
                    (r'w', 'ヴ'),
                    (r'ö', 'エ'),
                    (r'ü', 'ユ'),
                    (r'ä', 'エ'),
                    (r'ß', 'ス'),
                    (r'ei', 'アイ'),
                    (r'eu', 'オイ'),
                    (r'au', 'アウ'),
                ],
                'common_names': {
                    'Johann': 'ヨハン',
                    'Wolfgang': 'ヴォルフガング',
                    'Ludwig': 'ルートヴィヒ',
                    'Friedrich': 'フリードリヒ',
                    'Heinrich': 'ハインリヒ',
                    'Wilhelm': 'ヴィルヘルム',
                    'Karl': 'カール',
                    'Ernst': 'エルンスト',
                    'Otto': 'オットー',
                    'Hermann': 'ヘルマン'
                }
            },
            'french': {
                'patterns': [
                    # フランス語特有のパターン
                    (r'eau$', 'オー'),
                    (r'eux$', 'ー'),
                    (r'ois$', 'ワ'),
                    (r'ais$', 'エ'),
                    (r'et$', 'エ'),
                    (r'ard$', 'アール'),
                    (r'ier$', 'イエ'),
                    (r'eur$', 'ウール'),
                    (r'que$', 'ク'),
                    (r'gne$', 'ニュ'),
                    (r'ille', 'イユ'),
                    (r'ain', 'アン'),
                    (r'ein', 'アン'),
                    (r'oin', 'ワン'),
                    (r'ch', 'シュ'),
                    (r'ph', 'フ'),
                    (r'th', 'ト'),
                    (r'ou', 'ウ'),
                    (r'oi', 'ワ'),
                    (r'ai', 'エ'),
                    (r'au', 'オ'),
                ],
                'common_names': {
                    'Jean': 'ジャン',
                    'Pierre': 'ピエール',
                    'Jacques': 'ジャック',
                    'François': 'フランソワ',
                    'Louis': 'ルイ',
                    'Charles': 'シャルル',
                    'Henri': 'アンリ',
                    'Michel': 'ミシェル',
                    'Claude': 'クロード',
                    'André': 'アンドレ'
                }
            },
            'english': {
                'patterns': [
                    # 英語の基本パターン
                    (r'tion$', 'ション'),
                    (r'sion$', 'ジョン'),
                    (r'ness$', 'ネス'),
                    (r'ment$', 'メント'),
                    (r'ing$', 'イング'),
                    (r'son$', 'ソン'),
                    (r'ton$', 'トン'),
                    (r'ford$', 'フォード'),
                    (r'field$', 'フィールド'),
                    (r'wood$', 'ウッド'),
                    (r'land$', 'ランド'),
                    (r'ley$', 'リー'),
                    (r'ly$', 'リー'),
                    (r'th', 'ス'),
                    (r'ph', 'フ'),
                    (r'ck', 'ック'),
                    (r'gh', ''),
                    (r'wh', 'ホ'),
                    (r'qu', 'ク'),
                    (r'ee', 'イー'),
                    (r'oo', 'ウー'),
                ],
                'common_names': {
                    'John': 'ジョン',
                    'William': 'ウィリアム',
                    'James': 'ジェームズ',
                    'Robert': 'ロバート',
                    'Michael': 'マイケル',
                    'David': 'デビッド',
                    'Richard': 'リチャード',
                    'George': 'ジョージ',
                    'Thomas': 'トーマス',
                    'Charles': 'チャールズ'
                }
            },
            'italian': {
                'patterns': [
                    (r'ini$', 'イーニ'),
                    (r'ino$', 'イーノ'),
                    (r'ello$', 'エッロ'),
                    (r'etti$', 'エッティ'),
                    (r'acci$', 'アッチ'),
                    (r'ucci$', 'ウッチ'),
                    (r'ese$', 'エーゼ'),
                    (r'gli', 'リ'),
                    (r'gn', 'ニャ'),
                    (r'sc', 'シュ'),
                    (r'cc', 'ッチ'),
                    (r'zz', 'ッツ'),
                    (r'chi', 'キ'),
                    (r'che', 'ケ'),
                    (r'ci', 'チ'),
                    (r'ce', 'チェ'),
                    (r'gi', 'ジ'),
                    (r'ge', 'ジェ'),
                ],
                'common_names': {
                    'Giuseppe': 'ジュゼッペ',
                    'Giovanni': 'ジョヴァンニ',
                    'Antonio': 'アントニオ',
                    'Francesco': 'フランチェスコ',
                    'Luigi': 'ルイージ',
                    'Mario': 'マリオ',
                    'Carlo': 'カルロ',
                    'Paolo': 'パオロ',
                    'Marco': 'マルコ',
                    'Roberto': 'ロベルト'
                }
            },
            'spanish': {
                'patterns': [
                    (r'ez$', 'エス'),
                    (r'az$', 'アス'),
                    (r'iz$', 'イス'),
                    (r'oz$', 'オス'),
                    (r'uz$', 'ウス'),
                    (r'ción$', 'シオン'),
                    (r'dor$', 'ドール'),
                    (r'ero$', 'エロ'),
                    (r'illo$', 'イージョ'),
                    (r'ito$', 'イート'),
                    (r'ñ', 'ニャ'),
                    (r'll', 'ジャ'),
                    (r'rr', 'ル'),
                    (r'j', 'ホ'),
                    (r'x', 'クス'),
                    (r'v', 'ブ'),
                    (r'z', 'ス'),
                ],
                'common_names': {
                    'José': 'ホセ',
                    'Juan': 'フアン',
                    'Antonio': 'アントニオ',
                    'Francisco': 'フランシスコ',
                    'Manuel': 'マヌエル',
                    'Miguel': 'ミゲル',
                    'Carlos': 'カルロス',
                    'Luis': 'ルイス',
                    'Pedro': 'ペドロ',
                    'Diego': 'ディエゴ'
                }
            },
            'russian': {
                'patterns': [
                    (r'ov$', 'オフ'),
                    (r'ev$', 'エフ'),
                    (r'sky$', 'スキー'),
                    (r'ski$', 'スキー'),
                    (r'ich$', 'イッチ'),
                    (r'ovich$', 'オヴィッチ'),
                    (r'evich$', 'エヴィッチ'),
                    (r'enko$', 'エンコ'),
                    (r'uk$', 'ウク'),
                    (r'in$', 'イン'),
                    (r'ch', 'チ'),
                    (r'sh', 'シュ'),
                    (r'zh', 'ジ'),
                    (r'ts', 'ツ'),
                    (r'kh', 'フ'),
                ],
                'common_names': {
                    'Ivan': 'イワン',
                    'Mikhail': 'ミハイル',
                    'Alexander': 'アレクサンドル',
                    'Sergei': 'セルゲイ',
                    'Vladimir': 'ウラジーミル',
                    'Dmitri': 'ドミトリー',
                    'Nikolai': 'ニコライ',
                    'Andrei': 'アンドレイ',
                    'Pavel': 'パーヴェル',
                    'Boris': 'ボリス'
                }
            }
        }

    def detect_language(self, name: str, nationality: str = '') -> str:
        """名前と国籍から言語を推測"""
        nationality_lower = nationality.lower()

        # 国籍から言語を判定
        if any(x in nationality_lower for x in ['german', 'deutsch', 'ドイツ']):
            return 'german'
        elif any(x in nationality_lower for x in ['french', 'france', 'フランス']):
            return 'french'
        elif any(x in nationality_lower for x in ['italian', 'italy', 'イタリア']):
            return 'italian'
        elif any(x in nationality_lower for x in ['spanish', 'spain', 'スペイン']):
            return 'spanish'
        elif any(x in nationality_lower for x in ['russian', 'soviet', 'ロシア', 'ソビエト']):
            return 'russian'
        elif any(x in nationality_lower for x in ['united states', 'america', 'british', 'england', 'アメリカ', 'イギリス']):
            return 'english'

        # 名前のパターンから言語を推測
        name_lower = name.lower()
        if any(ending in name_lower for ending in ['mann', 'berg', 'stein', 'schmidt']):
            return 'german'
        elif any(ending in name_lower for ending in ['eau', 'ois', 'eux']):
            return 'french'
        elif any(ending in name_lower for ending in ['ini', 'elli', 'etti']):
            return 'italian'
        elif any(ending in name_lower for ending in ['ez', 'az', 'oz']):
            return 'spanish'
        elif any(ending in name_lower for ending in ['ov', 'ev', 'sky', 'ich']):
            return 'russian'

        return 'english'  # デフォルト

    def convert_to_katakana(self, name: str, language: str) -> str:
        """名前をカタカナに変換"""

        # 言語別ルールを取得
        if language not in self.conversion_rules:
            language = 'english'

        rules = self.conversion_rules[language]

        # 名前を分割（名・姓）
        parts = name.split()
        converted_parts = []

        for part in parts:
            # 一般的な名前の辞書をチェック
            if part in rules['common_names']:
                converted_parts.append(rules['common_names'][part])
                continue

            # パターンルールを適用
            converted = part
            for pattern, replacement in rules['patterns']:
                converted = re.sub(pattern, replacement, converted, flags=re.IGNORECASE)

            # 基本的な文字変換
            basic_conversions = {
                'a': 'ア', 'b': 'ブ', 'c': 'ク', 'd': 'ド', 'e': 'エ',
                'f': 'フ', 'g': 'グ', 'h': 'ハ', 'i': 'イ', 'j': 'ジ',
                'k': 'ク', 'l': 'ル', 'm': 'ム', 'n': 'ン', 'o': 'オ',
                'p': 'プ', 'q': 'ク', 'r': 'ル', 's': 'ス', 't': 'ト',
                'u': 'ウ', 'v': 'ヴ', 'w': 'ウ', 'x': 'クス', 'y': 'イ',
                'z': 'ズ'
            }

            # 残りの文字を変換
            result = ''
            for char in converted.lower():
                if char in basic_conversions:
                    result += basic_conversions[char]
                elif not char.isalpha():
                    result += char

            if result:
                # 最初の文字を大文字に相当するカタカナに
                converted_parts.append(result)

        return '・'.join(converted_parts) if converted_parts else name

    def process_name(self, name: str, nationality: str = '') -> Optional[str]:
        """名前を処理してカタカナに変換"""

        # キャッシュチェック
        cache_key = f"phonetic_{name}"
        if cache_key in self.translation_cache:
            cached_value = self.translation_cache[cache_key]
            if isinstance(cached_value, str):
                self.stats['cached'] += 1
                return cached_value

        # すでに日本語の場合はスキップ
        if any(ord(c) > 0x3000 for c in name):
            self.stats['skipped'] += 1
            return None

        # 言語を検出
        language = self.detect_language(name, nationality)

        # カタカナに変換
        katakana = self.convert_to_katakana(name, language)

        # キャッシュに保存
        if katakana and katakana != name:
            self.translation_cache[cache_key] = katakana
            self.stats['converted'] += 1
            return katakana

        return None

    def _determine_input_file(self, input_file: Optional[str] = None) -> str:
        """入力ファイルを決定する"""
        if input_file:
            return input_file

        from pathlib import Path
        wikipedia_files = list(Path('.').glob('wikipedia_translated_*.json'))
        if wikipedia_files:
            return str(sorted(wikipedia_files)[-1])
        return 'perfect_database_20250824_172451.json'

    def _process_single_entry(self, value: Dict[str, Any]) -> bool:
        """単一エントリを処理し、変換成功時はTrueを返す"""
        if not isinstance(value, dict):
            return False

        name = value.get('name', '')
        nationality = value.get('nationality', '')

        # 英語名の場合のみ処理
        if not name or any(ord(c) > 0x3000 for c in name):
            return False

        self.stats['processed'] += 1
        katakana = self.process_name(name, nationality)

        if katakana:
            value['original_name'] = name
            value['name'] = katakana
            return True

        return False

    def _save_output_file(self, all_data: Dict[str, Any]) -> str:
        """出力ファイルを保存し、ファイル名を返す"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"phonetic_converted_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        return output_file

    def _print_conversion_results(self, converted_count: int, output_file: str):
        """変換結果を表示する"""
        print("\n📊 カタカナ変換結果:")
        print(f"  処理: {self.stats['processed']}件")
        print(f"  変換成功: {converted_count}件")
        print(f"  キャッシュ使用: {self.stats['cached']}件")
        print(f"  スキップ: {self.stats['skipped']}件")
        print(f"  出力: {output_file}")

    def translate_database(self, input_file: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """データベース全体をカタカナ変換"""

        # 入力ファイル決定
        input_file = self._determine_input_file(input_file)
        print("🔤 音声ベースカタカナ変換開始")
        print(f"  入力: {input_file}")

        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

        # 未翻訳データ処理
        converted_count = 0
        for _, value in all_data.items():
            if self._process_single_entry(value):
                converted_count += 1
                # 最初の10件のみ表示
                if converted_count <= 10:
                    name = value.get('original_name', '')
                    katakana = value.get('name', '')
                    nationality = value.get('nationality', '')
                    print(f"  ✓ {name} → {katakana} ({nationality})")

        # キャッシュ保存
        self.save_cache()

        # 出力ファイル保存
        output_file = self._save_output_file(all_data)

        # 結果表示
        self._print_conversion_results(converted_count, output_file)

        return output_file, self.stats


def main():
    """メイン実行"""
    converter = PhoneticKatakanaConverter()

    # カタカナ変換実行
    result_file, stats = converter.translate_database()

    # 成功率計算
    if stats['processed'] > 0:
        success_rate = stats['converted'] / stats['processed'] * 100
        print(f"\n🎯 変換成功率: {success_rate:.1f}%")
        print(f"  出力ファイル: {result_file}")


if __name__ == "__main__":
    main()
