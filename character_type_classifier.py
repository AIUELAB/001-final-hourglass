#!/usr/bin/env python3
"""
キャラクタータイプ分類器
実在人物と架空キャラクターを高精度で判定する

Wikipedia API、作品名データベース、パターンマッチングを組み合わせた判定
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import requests
from time import sleep

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class CharacterType(Enum):
    """キャラクタータイプ"""
    REAL_PERSON = "real_person"              # 実在の人物
    FICTIONAL_CHARACTER = "fictional_character"  # 架空のキャラクター
    HISTORICAL_FIGURE = "historical_figure"   # 歴史上の人物
    MYTHOLOGICAL = "mythological"            # 神話・伝説上の存在
    GROUP = "group"                         # グループ・団体
    MASCOT = "mascot"                       # マスコットキャラクター
    UNKNOWN = "unknown"                     # 不明


@dataclass
class ClassificationResult:
    """分類結果"""
    character_type: CharacterType
    confidence: float  # 0.0 ~ 1.0
    work_name: Optional[str] = None
    evidence: List[str] = None
    wikipedia_data: Optional[Dict] = None


class CharacterTypeClassifier:
    """キャラクタータイプ分類器"""

    def __init__(self):
        """初期化"""
        # 作品名データベース（主要な作品とキャラクター）
        self.work_database = {
            # アニメ・マンガ
            "ドラゴンボール": ["孫悟空", "ベジータ", "ピッコロ", "フリーザ", "セル", "魔人ブウ"],
            "ONE PIECE": ["モンキー・D・ルフィ", "ルフィ", "ゾロ", "ナミ", "サンジ", "チョッパー"],
            "鬼滅の刃": ["竈門炭治郎", "竈門禰豆子", "我妻善逸", "嘴平伊之助", "煉獄杏寿郎"],
            "進撃の巨人": ["エレン・イェーガー", "ミカサ・アッカーマン", "アルミン", "リヴァイ"],
            "呪術廻戦": ["虎杖悠仁", "伏黒恵", "釘崎野薔薇", "五条悟"],
            "ドラえもん": ["ドラえもん", "のび太", "しずか", "ジャイアン", "スネ夫"],
            "ポケットモンスター": ["ピカチュウ", "サトシ", "カスミ", "タケシ"],
            "新世紀エヴァンゲリオン": ["碇シンジ", "綾波レイ", "惣流・アスカ・ラングレー", "渚カヲル"],
            "美少女戦士セーラームーン": ["月野うさぎ", "セーラームーン", "セーラーマーズ"],
            "NARUTO": ["うずまきナルト", "うちはサスケ", "春野サクラ", "はたけカカシ"],
            "BLEACH": ["黒崎一護", "朽木ルキア", "井上織姫"],
            "ジョジョの奇妙な冒険": ["ジョナサン・ジョースター", "ジョセフ・ジョースター", "空条承太郎", "DIO"],
            "鋼の錬金術師": ["エドワード・エルリック", "アルフォンス・エルリック"],
            "ワンパンマン": ["サイタマ", "ジェノス"],
            "東京リベンジャーズ": ["花垣武道", "佐野万次郎", "龍宮寺堅"],
            "SPY×FAMILY": ["ロイド・フォージャー", "アーニャ・フォージャー", "ヨル・フォージャー"],
            "チェンソーマン": ["デンジ", "パワー", "マキマ"],

            # ゲーム
            "ファイナルファンタジー": ["クラウド・ストライフ", "ティファ・ロックハート", "セフィロス", "エアリス"],
            "ドラゴンクエスト": ["ロト", "竜王", "スライム"],
            "ストリートファイター": ["リュウ", "ケン", "春麗", "ガイル", "豪鬼"],
            "スーパーマリオ": ["マリオ", "ルイージ", "ピーチ姫", "クッパ", "ヨッシー"],
            "ゼルダの伝説": ["リンク", "ゼルダ姫", "ガノンドロフ"],
            "モンスターハンター": ["ハンター", "アイルー", "オトモアイルー"],
            "ペルソナ": ["番長", "鳴上悠", "足立透"],
            "メタルギア": ["スネーク", "ソリッド・スネーク", "ビッグボス"],

            # 特撮
            "ウルトラマン": ["ウルトラマン", "ウルトラセブン", "ウルトラマンタロウ", "ウルトラマンゼロ"],
            "仮面ライダー": ["仮面ライダー1号", "仮面ライダーV3", "仮面ライダー電王", "仮面ライダーゼロワン"],
            "スーパー戦隊": ["ゴレンジャー", "ジュウレンジャー", "ゴーカイジャー"],
            "ゴジラ": ["ゴジラ", "キングギドラ", "モスラ", "メカゴジラ"],

            # ディズニー
            "ディズニー": ["ミッキーマウス", "ミニーマウス", "ドナルドダック", "グーフィー"],
            "アナと雪の女王": ["エルサ", "アナ", "オラフ", "クリストフ"],

            # サンリオ
            "サンリオ": ["ハローキティ", "キティちゃん", "マイメロディ", "ポムポムプリン", "シナモロール"],

            # その他
            "スター・ウォーズ": ["ルーク・スカイウォーカー", "ダース・ベイダー", "レイア姫", "ハン・ソロ"],
            "ハリー・ポッター": ["ハリー・ポッター", "ハーマイオニー・グレンジャー", "ロン・ウィーズリー"],
        }

        # 架空キャラクターを示すキーワード
        self.fictional_keywords = [
            '架空', 'キャラクター', 'アニメ', 'マンガ', '漫画',
            'ゲーム', '小説', 'ライトノベル', 'ラノベ',
            '特撮', 'ヒーロー', 'ヒロイン', '主人公',
            '登場人物', '登場キャラクター', 'ファンタジー',
            'SF', 'ロボット', '妖怪', 'ポケモン', 'デジモン',
            'プリキュア', '戦隊', 'ライダー', 'ウルトラ'
        ]

        # 実在人物を示すキーワード
        self.real_person_keywords = [
            '俳優', '女優', '歌手', 'アーティスト', 'ミュージシャン',
            '作家', '小説家', '漫画家', '監督', 'プロデューサー',
            '政治家', '大統領', '首相', '社長', 'CEO',
            'スポーツ選手', '野球選手', 'サッカー選手', 'テニス選手',
            '学者', '教授', '研究者', '科学者', '医師',
            'タレント', '芸人', 'お笑い芸人', 'アイドル',
            'YouTuber', 'インフルエンサー', 'ストリーマー'
        ]

        # マスコットキャラクター
        self.mascot_patterns = [
            'くん', 'ちゃん', 'マン', 'キャラ', 'マスコット',
            'ゆるキャラ', 'ご当地キャラ'
        ]

        logger.info("キャラクタータイプ分類器初期化完了")

    def classify(self,
                name: str,
                occupation: Optional[str] = None,
                category: Optional[str] = None,
                metadata: Optional[Dict] = None) -> ClassificationResult:
        """
        キャラクタータイプを分類

        Args:
            name: 名前
            occupation: 職業・説明
            category: カテゴリ
            metadata: 追加メタデータ

        Returns:
            分類結果
        """
        evidence = []
        confidence_scores = []

        # 1. 作品データベースでチェック
        work_name = self._check_work_database(name)
        if work_name:
            evidence.append(f"作品データベースで発見: {work_name}")
            confidence_scores.append(0.95)
            return ClassificationResult(
                character_type=CharacterType.FICTIONAL_CHARACTER,
                confidence=0.95,
                work_name=work_name,
                evidence=evidence
            )

        # 2. occupation/categoryからのキーワード判定
        text_to_check = f"{occupation or ''} {category or ''}"

        # 架空キャラクター判定
        fictional_score = self._calculate_keyword_score(text_to_check, self.fictional_keywords)
        if fictional_score > 0:
            evidence.append(f"架空キャラクターキーワード検出 (スコア: {fictional_score:.2f})")
            confidence_scores.append(min(0.9, fictional_score))

            # 作品名を抽出
            extracted_work = self._extract_work_name(text_to_check)
            if extracted_work:
                evidence.append(f"作品名抽出: {extracted_work}")
                return ClassificationResult(
                    character_type=CharacterType.FICTIONAL_CHARACTER,
                    confidence=min(0.9, fictional_score),
                    work_name=extracted_work,
                    evidence=evidence
                )

        # 実在人物判定
        real_person_score = self._calculate_keyword_score(text_to_check, self.real_person_keywords)
        if real_person_score > 0:
            evidence.append(f"実在人物キーワード検出 (スコア: {real_person_score:.2f})")
            confidence_scores.append(min(0.9, real_person_score))

            return ClassificationResult(
                character_type=CharacterType.REAL_PERSON,
                confidence=min(0.9, real_person_score),
                evidence=evidence
            )

        # 3. マスコットキャラクター判定
        if self._is_mascot(name, text_to_check):
            evidence.append("マスコットキャラクターパターン検出")
            return ClassificationResult(
                character_type=CharacterType.MASCOT,
                confidence=0.85,
                evidence=evidence
            )

        # 4. Wikipedia API チェック（オプション）
        if metadata and metadata.get('use_wikipedia', False):
            wiki_result = self._check_wikipedia(name)
            if wiki_result:
                evidence.append(f"Wikipedia情報: {wiki_result['summary'][:100]}...")
                character_type = self._analyze_wikipedia_data(wiki_result)
                return ClassificationResult(
                    character_type=character_type,
                    confidence=0.8,
                    evidence=evidence,
                    wikipedia_data=wiki_result
                )

        # 5. 名前パターン分析
        name_analysis = self._analyze_name_pattern(name)
        if name_analysis:
            evidence.append(f"名前パターン: {name_analysis['pattern']}")
            return ClassificationResult(
                character_type=name_analysis['type'],
                confidence=name_analysis['confidence'],
                evidence=evidence
            )

        # デフォルト
        return ClassificationResult(
            character_type=CharacterType.UNKNOWN,
            confidence=0.0,
            evidence=["判定不能"]
        )

    def _check_work_database(self, name: str) -> Optional[str]:
        """作品データベースでチェック"""
        for work_name, characters in self.work_database.items():
            for character in characters:
                if character in name or name in character:
                    return work_name
        return None

    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """キーワードスコア計算"""
        if not text:
            return 0.0

        text_lower = text.lower()
        match_count = 0
        total_weight = 0

        for keyword in keywords:
            if keyword in text_lower:
                # キーワードの重要度に応じて重み付け
                weight = len(keyword) / 10.0  # 長いキーワードほど重要
                match_count += 1
                total_weight += weight

        if match_count == 0:
            return 0.0

        # 正規化スコア
        return min(1.0, total_weight / len(keywords) * 10)

    def _extract_work_name(self, text: str) -> Optional[str]:
        """テキストから作品名を抽出"""
        # パターンマッチング
        patterns = [
            r'『(.*?)』',
            r'「(.*?)」',
            r'【(.*?)】',
            r'\((.*?)\)',
            r'（(.*?)）',
            r'『(.*?)』.*?[のに].*?登場',
            r'「(.*?)」.*?[のに].*?キャラクター',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                work_name = match.group(1)
                # 明らかに作品名でないものを除外
                if len(work_name) > 2 and '架空' not in work_name and 'キャラクター' not in work_name:
                    return work_name

        return None

    def _is_mascot(self, name: str, text: str) -> bool:
        """マスコットキャラクター判定"""
        for pattern in self.mascot_patterns:
            if pattern in name:
                return True

        # ゆるキャラ、ご当地キャラのパターン
        if 'ゆるキャラ' in text or 'ご当地' in text or 'マスコット' in text:
            return True

        return False

    def _check_wikipedia(self, name: str) -> Optional[Dict]:
        """Wikipedia APIでチェック（レート制限考慮）"""
        try:
            # Wikipedia API
            url = "https://ja.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|categories',
                'titles': name,
                'exintro': True,
                'explaintext': True,
                'exlimit': 1
            }

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})

                for page_id, page_data in pages.items():
                    if page_id != '-1':  # ページが存在
                        return {
                            'title': page_data.get('title'),
                            'summary': page_data.get('extract', ''),
                            'categories': page_data.get('categories', [])
                        }

            sleep(0.5)  # レート制限対策

        except Exception as e:
            logger.warning(f"Wikipedia API エラー: {e}")

        return None

    def _analyze_wikipedia_data(self, wiki_data: Dict) -> CharacterType:
        """Wikipediaデータから判定"""
        summary = wiki_data.get('summary', '').lower()
        categories = wiki_data.get('categories', [])

        # カテゴリから判定
        category_text = ' '.join([c.get('title', '') for c in categories]).lower()

        if '架空' in category_text or 'フィクション' in category_text:
            return CharacterType.FICTIONAL_CHARACTER
        elif '存命人物' in category_text or '日本の' in category_text:
            return CharacterType.REAL_PERSON
        elif '神話' in category_text or '伝説' in category_text:
            return CharacterType.MYTHOLOGICAL

        # サマリーから判定
        if '架空' in summary or 'キャラクター' in summary:
            return CharacterType.FICTIONAL_CHARACTER
        elif '生まれ' in summary or '出身' in summary:
            return CharacterType.REAL_PERSON

        return CharacterType.UNKNOWN

    def _analyze_name_pattern(self, name: str) -> Optional[Dict]:
        """名前パターンから判定"""
        # カタカナのみの外国人名
        if re.match(r'^[ァ-ヴー・]+$', name):
            # 実在の可能性が高い
            return {
                'type': CharacterType.REAL_PERSON,
                'confidence': 0.6,
                'pattern': 'カタカナ外国人名'
            }

        # ひらがな名（キャラクター名に多い）
        if re.match(r'^[ぁ-ん]+$', name):
            return {
                'type': CharacterType.FICTIONAL_CHARACTER,
                'confidence': 0.7,
                'pattern': 'ひらがな名'
            }

        # 特殊記号を含む（キャラクター名に多い）
        if re.search(r'[★☆♪♫◆◇■□●○]', name):
            return {
                'type': CharacterType.FICTIONAL_CHARACTER,
                'confidence': 0.8,
                'pattern': '特殊記号含む'
            }

        return None

    def validate_fictional_character(self, name: str, work_name: Optional[str] = None) -> Dict[str, Any]:
        """
        架空キャラクターの検証

        Args:
            name: キャラクター名
            work_name: 作品名

        Returns:
            検証結果
        """
        validation = {
            'is_valid': True,
            'has_work_name': bool(work_name),
            'work_name_verified': False,
            'confidence': 0.0,
            'issues': []
        }

        if not work_name:
            validation['is_valid'] = False
            validation['issues'].append("作品名が未設定")
            validation['confidence'] = 0.0
            return validation

        # 作品名が既知のデータベースに存在するか
        if work_name in self.work_database:
            validation['work_name_verified'] = True
            validation['confidence'] = 1.0

            # キャラクターが作品に属するか確認
            if name not in self.work_database[work_name]:
                validation['issues'].append(f"'{name}'は'{work_name}'の主要キャラクターリストに含まれていません")
                validation['confidence'] = 0.7
        else:
            validation['confidence'] = 0.5
            validation['issues'].append(f"作品名'{work_name}'はデータベースに未登録")

        return validation


# テスト用
def main():
    """テスト実行"""
    classifier = CharacterTypeClassifier()

    # テストケース
    test_cases = [
        {"name": "孫悟空", "occupation": "架空のキャラクター"},
        {"name": "大谷翔平", "occupation": "野球選手"},
        {"name": "ピカチュウ", "category": "アニメ"},
        {"name": "安倍晋三", "occupation": "政治家"},
        {"name": "ドラえもん", "occupation": "架空のキャラクター"},
        {"name": "くまモン", "occupation": "マスコットキャラクター"},
        {"name": "竈門炭治郎", "occupation": "鬼滅の刃の主人公"},
        {"name": "イチロー", "occupation": "元プロ野球選手"},
    ]

    for test in test_cases:
        result = classifier.classify(**test)
        print(f"""
        ========================================
        名前: {test['name']}
        判定: {result.character_type.value}
        確信度: {result.confidence:.2%}
        作品名: {result.work_name or 'なし'}
        根拠: {', '.join(result.evidence)}
        """)

    # 架空キャラクター検証テスト
    validation = classifier.validate_fictional_character("孫悟空", "ドラゴンボール")
    print(f"""
    架空キャラクター検証:
    有効: {validation['is_valid']}
    作品名検証: {validation['work_name_verified']}
    確信度: {validation['confidence']:.2%}
    """)


if __name__ == "__main__":
    main()