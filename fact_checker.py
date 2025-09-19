#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファクトチェックシステム
生成されたエピソードの事実確認を行う
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import wikipediaapi
import requests

logger = logging.getLogger(__name__)


@dataclass
class FactCheckResult:
    """事実確認結果"""
    is_verified: bool
    confidence_score: float  # 0.0-1.0
    warnings: List[str]
    corrections: Dict[str, str]
    sources: List[str]


class FactChecker:
    """エピソードのファクトチェッカー"""

    def __init__(self):
        """初期化"""
        self.wiki = wikipediaapi.Wikipedia(
            user_agent='EpisodeFactChecker/1.0 (https://example.com/contact)',
            language='ja'
        )

        # 既知の誤情報パターン
        self.known_errors = {
            'Ado': {
                'incorrect': ['ヨルシカ.*うっせぇわ', 'アルバム.*Ado'],
                'correct': {
                    'うっせぇわ作者': 'syudou',
                    '1stアルバム': '狂言',
                    'デビュー年': '2020年',
                    'デビュー年齢': '18歳'
                }
            },
            'GACKT': {
                'incorrect': ['レーベル.*Dracula'],
                'correct': {
                    'レーベル': 'Dears/GACKTJob'
                }
            }
        }

        # 警告ワード（創作の可能性が高い表現）
        self.warning_patterns = [
            r'約\d+',  # 「約〜」は推定値
            r'推定',
            r'とされ',
            r'といわれ',
            r'らしい',
            r'かもしれ',
            r'おそらく'
        ]

    def check_episode(self, episode_text: str, person_name: str,
                     age: int, birth_year: int) -> FactCheckResult:
        """エピソードの事実確認

        Args:
            episode_text: エピソード本文
            person_name: 人物名
            age: エピソード年齢
            birth_year: 生年

        Returns:
            事実確認結果
        """
        warnings = []
        corrections = {}
        sources = []

        # 1. 既知のエラーパターンチェック
        if person_name in self.known_errors:
            for pattern in self.known_errors[person_name]['incorrect']:
                if re.search(pattern, episode_text):
                    warnings.append(f"既知の誤情報パターンを検出: {pattern}")
                    corrections.update(self.known_errors[person_name]['correct'])

        # 2. 年代の整合性チェック
        year_check = self._check_year_consistency(episode_text, age, birth_year)
        if year_check:
            warnings.append(year_check)

        # 3. Wikipedia確認
        wiki_result = self._check_wikipedia(person_name, episode_text)
        if wiki_result['found']:
            sources.append(f"Wikipedia: {wiki_result['url']}")
            if wiki_result['conflicts']:
                warnings.extend(wiki_result['conflicts'])
        else:
            warnings.append(f"Wikipediaで{person_name}の情報が見つかりません")

        # 4. 数値の妥当性チェック
        number_check = self._check_number_validity(episode_text)
        warnings.extend(number_check)

        # 5. 警告表現の検出
        for pattern in self.warning_patterns:
            if re.search(pattern, episode_text):
                warnings.append(f"不確実な表現を検出: {pattern}")

        # 信頼度スコアの計算
        confidence_score = self._calculate_confidence(warnings, corrections, sources)

        return FactCheckResult(
            is_verified=confidence_score > 0.7,
            confidence_score=confidence_score,
            warnings=warnings,
            corrections=corrections,
            sources=sources
        )

    def _check_year_consistency(self, episode_text: str, age: int,
                               birth_year: int) -> Optional[str]:
        """年代の整合性チェック"""
        episode_year = birth_year + age

        # エピソード内の年号を抽出
        year_pattern = r'(19|20)\d{2}年'
        years_in_text = re.findall(year_pattern, episode_text)

        for year_str in years_in_text:
            year = int(year_str.replace('年', ''))
            if abs(year - episode_year) > 1:  # 1年以上のズレ
                return f"年代の不整合: {age}歳は{episode_year}年のはずだが、{year}年と記載"

        return None

    def _check_wikipedia(self, person_name: str, episode_text: str) -> Dict:
        """Wikipedia情報との照合"""
        result = {
            'found': False,
            'url': '',
            'conflicts': []
        }

        try:
            page = self.wiki.page(person_name)
            if page.exists():
                result['found'] = True
                result['url'] = page.fullurl

                # 簡易的な矛盾チェック
                # 実際はより高度な自然言語処理が必要
                page_text = page.text[:5000]  # 最初の5000文字

                # エピソード内の固有名詞を抽出
                proper_nouns = self._extract_proper_nouns(episode_text)

                for noun in proper_nouns:
                    if noun not in page_text and len(noun) > 3:
                        result['conflicts'].append(
                            f"'{noun}'はWikipediaに記載がありません（要確認）"
                        )

        except Exception as e:
            logger.error(f"Wikipedia確認エラー: {e}")

        return result

    def _extract_proper_nouns(self, text: str) -> List[str]:
        """固有名詞の抽出（簡易版）"""
        # 「」で囲まれた部分を抽出
        quoted = re.findall(r'「([^」]+)」', text)
        # 『』で囲まれた部分を抽出
        quoted.extend(re.findall(r'『([^』]+)』', text))

        return quoted

    def _check_number_validity(self, episode_text: str) -> List[str]:
        """数値の妥当性チェック"""
        warnings = []

        # 大きすぎる数値のチェック
        large_numbers = re.findall(r'(\d{4,})[万億]', episode_text)
        for num in large_numbers:
            if int(num) > 9999:  # 1億以上
                warnings.append(f"非常に大きな数値を検出: {num} - 要検証")

        # 年間ライブ本数のチェック
        live_pattern = r'年間(\d+)本'
        live_matches = re.findall(live_pattern, episode_text)
        for count in live_matches:
            if int(count) > 365:
                warnings.append(f"年間{count}本のライブは物理的に困難")

        return warnings

    def _calculate_confidence(self, warnings: List[str],
                            corrections: Dict, sources: List[str]) -> float:
        """信頼度スコアの計算"""
        score = 1.0

        # 警告ごとに減点
        score -= len(warnings) * 0.15

        # 修正が必要な項目ごとに減点
        score -= len(corrections) * 0.2

        # ソースがあれば加点
        score += len(sources) * 0.1

        # 0.0-1.0の範囲に制限
        return max(0.0, min(1.0, score))

    def validate_person_data(self, person_name: str, birth_year: int,
                            category: str) -> Dict[str, any]:
        """人物の基本情報を検証"""
        validation_result = {
            'valid': True,
            'verified_data': {},
            'warnings': []
        }

        # Wikipedia確認
        try:
            page = self.wiki.page(person_name)
            if page.exists():
                validation_result['verified_data']['wikipedia_url'] = page.fullurl

                # 生年の確認（簡易的）
                if str(birth_year) not in page.text:
                    validation_result['warnings'].append(
                        f"生年{birth_year}年がWikipediaと一致しない可能性"
                    )
            else:
                validation_result['warnings'].append(
                    f"Wikipediaに{person_name}の記事が見つかりません"
                )
                validation_result['valid'] = False

        except Exception as e:
            logger.error(f"人物データ検証エラー: {e}")
            validation_result['valid'] = False

        return validation_result


class HallucinationDetector:
    """ハルシネーション（幻覚）検出器"""

    def __init__(self):
        """初期化"""
        # ハルシネーションの典型的パターン
        self.hallucination_patterns = [
            # 存在しない作品名のパターン
            r'「[^」]{20,}」',  # 異常に長いタイトル

            # 非現実的な数値
            r'\d{5,}万',  # 10000万以上
            r'\d{4,}億',  # 1000億以上

            # 矛盾する表現
            r'同時に.*かつ',
            r'しながら.*別の',

            # 過度に詳細な描写（創作の可能性）
            r'具体的には.*詳細に.*正確に',
        ]

        # 信頼できるソース
        self.trusted_sources = [
            'wikipedia.org',
            'nhk.or.jp',
            'oricon.co.jp',
            'billboard-japan.com'
        ]

    def detect(self, episode_text: str) -> Tuple[bool, List[str]]:
        """ハルシネーション検出

        Returns:
            (ハルシネーション検出フラグ, 検出理由リスト)
        """
        detected_reasons = []

        for pattern in self.hallucination_patterns:
            matches = re.findall(pattern, episode_text)
            if matches:
                detected_reasons.append(f"疑わしいパターン: {matches[0][:50]}")

        # 複数の固有名詞の組み合わせチェック
        if self._check_unlikely_combinations(episode_text):
            detected_reasons.append("あり得ない組み合わせを検出")

        return len(detected_reasons) > 0, detected_reasons

    def _check_unlikely_combinations(self, text: str) -> bool:
        """あり得ない組み合わせのチェック"""
        # 例: 異なるアーティストの作品を混同
        unlikely_pairs = [
            ('ヨルシカ', 'うっせぇわ'),
            ('米津玄師', 'ちびまる子'),
            ('HIKAKIN', '紅白歌合戦.*優勝')
        ]

        for pair in unlikely_pairs:
            if pair[0] in text and re.search(pair[1], text):
                return True

        return False


def main():
    """テスト実行"""
    checker = FactChecker()
    detector = HallucinationDetector()

    # 問題のあるエピソード例
    test_episode = """あなたと同じ21歳のとき、Adoは日本のデビューアルバム「Ado」がオリコンデイリーランキング1位を獲得し、同年には「ヨルシカ」と共同で発表した「うっせぇわ」がストリーミング1億回再生を突破するなど、驚異的なデビューを遂げました。"""

    print("="*60)
    print("🔍 ファクトチェック実行")
    print("="*60)

    # ファクトチェック
    result = checker.check_episode(test_episode, "Ado", 21, 2002)

    print(f"✓ 検証済み: {result.is_verified}")
    print(f"📊 信頼度スコア: {result.confidence_score:.2f}")

    if result.warnings:
        print("\n⚠️ 警告:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.corrections:
        print("\n📝 必要な修正:")
        for key, value in result.corrections.items():
            print(f"  - {key}: {value}")

    # ハルシネーション検出
    print("\n" + "="*60)
    print("🧠 ハルシネーション検出")
    print("="*60)

    is_hallucination, reasons = detector.detect(test_episode)

    if is_hallucination:
        print("❌ ハルシネーションを検出しました:")
        for reason in reasons:
            print(f"  - {reason}")
    else:
        print("✅ ハルシネーションは検出されませんでした")


if __name__ == "__main__":
    main()