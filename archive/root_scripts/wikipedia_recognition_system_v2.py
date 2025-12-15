#!/usr/bin/env python3
"""
Wikipedia Recognition System V2 - 改善版
括弧処理、名前正規化、複数検索戦略を実装
"""

import re
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import wikipediaapi

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikipediaRecognitionSystemV2:
    """
    改善版Wikipedia知名度評価システム

    主な改善点:
    1. 名前の正規化（括弧除去、カタカナ→英語変換）
    2. 複数の検索戦略
    3. 失敗キャッシュの短期化
    4. 曖昧検索の実装
    """

    def __init__(self, cache_dir: str = "cache/wikipedia"):
        """初期化"""
        # Wikipedia API設定（日本語）
        self.wiki_wiki = wikipediaapi.Wikipedia(
            user_agent='Recognition System v2.0 (contact@example.com)',
            language='ja'
        )

        # キャッシュディレクトリ
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 統計情報
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'wikipedia_found': 0,
            'wikipedia_not_found': 0,
            'normalized_searches': 0,
            'variation_searches': 0
        }

        # カタカナ→英語変換辞書
        self.katakana_to_english = {
            'エヌシーティー': 'NCT',
            'ル・セラフィム': 'LE SSERAFIM',
            'ビーティーエス': 'BTS',
            'セブンティーン': 'SEVENTEEN',
            'トゥワイス': 'TWICE',
            'ブラックピンク': 'BLACKPINK',
            'エンハイプン': 'ENHYPEN',
            'ストレイキッズ': 'Stray Kids',
            'エイティーズ': 'ATEEZ',
            'アイブ': 'IVE',
            'イッツィー': 'ITZY',
            'エスパ': 'aespa',
            'トレジャー': 'TREASURE',
            'ドリームズ・カム・トゥルー': 'DREAMS COME TRUE',
            'ドリカム': 'DREAMS COME TRUE',
            'サイ': 'PSY',
            'ビッグバン': 'BIGBANG',
            'シャイニー': 'SHINee',
            'エクソ': 'EXO',
            'ゴット・セブン': 'GOT7',
            'モンスター・エックス': 'MONSTA X',
            'トゥモロー・バイ・トゥギャザー': 'TXT',
            'ニュージーンズ': 'NewJeans',
            'エックス・ジャパン': 'X JAPAN',
            'ラルク・アン・シエル': "L'Arc-en-Ciel",
            'グレイ': 'GLAY',
            'ビーズ': "B'z",
            'ミスター・チルドレン': 'Mr.Children',
            'サザン・オール・スターズ': 'サザンオールスターズ',
            'エグザイル': 'EXILE',
            'サンダイ': '&TEAM',
            'ダディー・ヤンキー': 'Daddy Yankee',
            'バッド・バニー': 'Bad Bunny'
        }

        # 略称辞書
        self.abbreviations = {
            'ドリカム': ['DREAMS COME TRUE', 'Dreams Come True'],
            'ミスチル': ['Mr.Children', 'ミスターチルドレン'],
            'サザン': ['サザンオールスターズ', 'Southern All Stars'],
            'ラルク': ["L'Arc-en-Ciel", 'ラルク・アン・シエル'],
            'Bz': ["B'z", 'ビーズ'],
            'エグ': ['EXILE', 'エグザイル'],
            'セカオワ': ['SEKAI NO OWARI', '世界の終わり'],
            'ヒゲダン': ['Official髭男dism', 'オフィシャルヒゲダンディズム'],
            'キンプリ': ['King & Prince', 'キング・アンド・プリンス'],
            'スノ': ['Snow Man', 'スノーマン'],
            'スト': ['SixTONES', 'ストーンズ'],
            'なにわ': ['なにわ男子', 'Naniwa Danshi']
        }

        # チェックポイント
        self.checkpoint_interval = 100
        self.last_checkpoint = 0

    def normalize_name_for_wikipedia(self, name: str) -> List[str]:
        """
        Wikipedia検索用に名前を正規化し、複数のバリエーションを生成

        Args:
            name: 元の名前

        Returns:
            検索用名前バリエーションのリスト
        """
        variations = []
        base_name = None  # base_nameを事前に定義

        # 1. オリジナル名
        variations.append(name)

        # 2. 括弧とその内容を除去（全角・半角両対応）
        if '(' in name or '（' in name:
            # 括弧とその中身を除去
            base_name = re.sub(r'[（(][^）)]*[）)]', '', name).strip()
            if base_name and base_name != name:
                variations.append(base_name)

            # 括弧内の内容を抽出
            bracket_content = re.findall(r'[（(]([^）)]*)[）)]', name)
            for content in bracket_content:
                if content:
                    variations.append(content.strip())

        # 3. スペースのバリエーション
        if ' ' in name:
            variations.append(name.replace(' ', '_'))
            variations.append(name.replace(' ', ''))

        # 4. 中点（・）の処理
        if '・' in name:
            variations.append(name.replace('・', ' '))
            variations.append(name.replace('・', ''))

        # 5. カタカナ→英語変換
        for katakana, english in self.katakana_to_english.items():
            if katakana in name:
                variations.append(name.replace(katakana, english))
                # 括弧がある場合は除去してから変換も試す
                if base_name:
                    variations.append(base_name.replace(katakana, english))

        # 6. 略称の展開
        for abbr, full_names in self.abbreviations.items():
            if abbr in name:
                for full_name in full_names:
                    variations.append(name.replace(abbr, full_name))

        # 7. 英語→カタカナ逆変換
        for katakana, english in self.katakana_to_english.items():
            if english in name:
                variations.append(name.replace(english, katakana))

        # 重複を除去して返す
        seen = set()
        unique_variations = []
        for v in variations:
            if v and v not in seen:
                seen.add(v)
                unique_variations.append(v)

        self.stats['normalized_searches'] += 1
        logger.debug(f"Generated {len(unique_variations)} variations for '{name}': {unique_variations[:5]}")

        return unique_variations

    def get_cache_key(self, name: str) -> str:
        """キャッシュキーを生成"""
        return hashlib.md5(name.encode('utf-8')).hexdigest()

    def get_cached_data(self, name: str) -> Optional[Dict]:
        """
        改善されたキャッシュ取得
        失敗結果は24時間で無効化
        """
        cache_key = self.get_cache_key(name)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            # キャッシュファイルの更新時刻を確認
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)

            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # 失敗結果の場合は24時間で無効化
                if not data.get('found', False):
                    if datetime.now() - mtime > timedelta(hours=24):
                        logger.debug(f"Expired failed cache for '{name}'")
                        return None
                # 成功結果は7日間有効
                elif datetime.now() - mtime > timedelta(days=7):
                    return None

                self.stats['cache_hits'] += 1
                return data

        return None

    def save_to_cache(self, name: str, data: Dict) -> None:
        """データをキャッシュに保存"""
        cache_key = self.get_cache_key(name)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # タイムスタンプを追加
        data['cached_at'] = datetime.now().isoformat()

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def calculate_recognition_score(self, page_info: Dict[str, Any]) -> float:
        """Wikipedia情報から知名度スコアを計算（0-10スケール）"""
        score = 0.0

        # 基本スコア（Wikipediaページの存在）
        if page_info.get('found', False):
            score = 3.0  # 基本点

            # ページの長さ（最大2点）
            page_length = page_info.get('page_length', 0)
            if page_length > 10000:
                score += 2.0
            elif page_length > 5000:
                score += 1.5
            elif page_length > 2000:
                score += 1.0
            elif page_length > 500:
                score += 0.5

            # 言語リンク数（最大2点）
            languages = page_info.get('languages', 0)
            if languages > 10:
                score += 2.0
            elif languages > 5:
                score += 1.5
            elif languages > 2:
                score += 1.0
            elif languages > 0:
                score += 0.5

            # 参照・リンク数（最大2点）
            links = page_info.get('links', 0)
            references = page_info.get('references', 0)
            if links > 100 or references > 50:
                score += 2.0
            elif links > 50 or references > 25:
                score += 1.5
            elif links > 20 or references > 10:
                score += 1.0
            elif links > 10 or references > 5:
                score += 0.5

            # カテゴリ数（最大1点）
            categories = page_info.get('categories', [])
            if len(categories) > 10:
                score += 1.0
            elif len(categories) > 5:
                score += 0.7
            elif len(categories) > 2:
                score += 0.5

        # スコアを0-10の範囲に制限
        return min(10.0, max(0.0, score))

    def extract_page_info(self, page) -> Dict[str, Any]:
        """Wikipediaページから情報を抽出"""
        result = {
            'found': True,
            'page_title': page.title,
            'summary': page.summary[:500] if page.summary else "",
            'page_length': len(page.text) if page.text else 0,
            'categories': list(page.categories.keys())[:10],
            'links': len(list(page.links.keys())),
            'languages': len(page.langlinks),
            'references': len(page.sections) * 5,  # セクション数から推定
            'images': 5 if len(page.text) > 5000 else 2,  # ページサイズから推定
            'views': 0  # ビュー数は別途取得が必要
        }

        # 英語版の存在確認（国際的認知度の指標）
        if 'en' in page.langlinks:
            result['languages'] += 1

        return result

    def search_wikipedia(self, name: str) -> Dict[str, Any]:
        """
        改善版Wikipedia検索
        複数の検索戦略を試行
        """
        # キャッシュチェック
        cached = self.get_cached_data(name)
        if cached:
            return cached

        # デフォルトの結果
        result = {
            'found': False,
            'page_title': None,
            'summary': None,
            'page_length': 0,
            'languages': 0,
            'categories': [],
            'references': 0,
            'images': 0,
            'links': 0,
            'views': 0,
            'search_attempts': 0,
            'successful_variant': None
        }

        try:
            self.stats['api_calls'] += 1

            # 名前のバリエーションを生成
            variations = self.normalize_name_for_wikipedia(name)
            result['search_attempts'] = len(variations)

            # 各バリエーションで検索を試行
            for i, variant in enumerate(variations):
                logger.debug(f"Trying variant {i+1}/{len(variations)}: '{variant}'")

                try:
                    page = self.wiki_wiki.page(variant)

                    if page.exists():
                        logger.info(f"Found Wikipedia page for '{name}' as '{variant}'")
                        result = self.extract_page_info(page)
                        result['successful_variant'] = variant
                        result['search_attempts'] = i + 1
                        # スコアを計算
                        result['recognition_score'] = self.calculate_recognition_score(result)
                        self.stats['wikipedia_found'] += 1
                        self.stats['variation_searches'] += i

                        # 成功結果をキャッシュ
                        self.save_to_cache(name, result)
                        return result

                except Exception as e:
                    logger.debug(f"Error searching variant '{variant}': {str(e)}")
                    continue

            # すべてのバリエーションで見つからなかった場合
            # 最後の手段として検索APIを使用（実装は省略）
            logger.info(f"Wikipedia page not found for '{name}' after {len(variations)} attempts")
            self.stats['wikipedia_not_found'] += 1

            # スコアを0に設定
            result['recognition_score'] = 0.0

            # 失敗結果もキャッシュ（24時間で無効化される）
            self.save_to_cache(name, result)

        except Exception as e:
            logger.error(f"Wikipedia検索エラー ({name}): {str(e)}")
            self.stats['errors'] = self.stats.get('errors', 0) + 1

        return result

    def evaluate_person(self, name: str, display_name: str = None) -> Dict[str, Any]:
        """
        人物の知名度を評価

        Args:
            name: 評価対象の名前
            display_name: 表示用の名前（オプション）

        Returns:
            評価結果の辞書
        """
        # Wikipedia検索
        wiki_data = self.search_wikipedia(name)

        # スコア計算
        recognition_score = self.calculate_recognition_score(wiki_data)

        # 削除判定
        should_delete = recognition_score < 5.0

        # 理由の生成
        if not wiki_data.get('found', False):
            reason = "Wikipediaページなし"
        elif should_delete:
            reason = f"知名度不足 (スコア: {recognition_score:.1f})"
        else:
            reason = f"知名度あり (スコア: {recognition_score:.1f})"

        return {
            'name': display_name or name,
            'original_name': name,
            'recognition_score': recognition_score,
            'wikipedia_found': wiki_data.get('found', False),
            'wikipedia_data': wiki_data,
            'should_delete': should_delete,
            'reason': reason,
            'search_attempts': wiki_data.get('search_attempts', 1),
            'successful_variant': wiki_data.get('successful_variant')
        }

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_searches = self.stats['api_calls'] + self.stats['cache_hits']

        return {
            'total_searches': total_searches,
            'api_calls': self.stats['api_calls'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': self.stats['cache_hits'] / max(total_searches, 1),
            'wikipedia_found': self.stats['wikipedia_found'],
            'wikipedia_not_found': self.stats['wikipedia_not_found'],
            'found_rate': self.stats['wikipedia_found'] / max(self.stats['api_calls'], 1),
            'normalized_searches': self.stats['normalized_searches'],
            'average_variations': self.stats['variation_searches'] / max(self.stats['normalized_searches'], 1),
            'errors': self.stats.get('errors', 0)
        }


def test_improved_system():
    """改善されたシステムのテスト"""
    print("="*60)
    print("Wikipedia Recognition System V2 - テスト")
    print("="*60)

    system = WikipediaRecognitionSystemV2()

    # 問題があった名前をテスト
    test_cases = [
        "吉田美和 (DREAMS COME TRUE)",
        "PSY (サイ)",
        "ル・セラフィム",
        "エヌシーティー",
        "ヒカキン",
        "大谷翔平",
        "安倍晋三",
        "Ado",
        "トゥモロー・バイ・トゥギャザー",
        "ニュージーンズ"
    ]

    print("\nテスト結果:")
    print("-"*60)

    for name in test_cases:
        result = system.evaluate_person(name)
        status = "✓" if not result['should_delete'] else "✗"
        variant = result.get('successful_variant', '-')

        print(f"{status} {name:30} スコア: {result['recognition_score']:4.1f} "
              f"検索: {result.get('search_attempts', 0)}回 "
              f"成功形: {variant if variant else 'なし'}")

    print("\n" + "="*60)
    print("統計情報:")
    print("-"*60)

    stats = system.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key:25}: {value:.2f}")
        else:
            print(f"{key:25}: {value}")

    print("="*60)


if __name__ == "__main__":
    test_improved_system()
