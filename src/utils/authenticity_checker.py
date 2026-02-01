#!/usr/bin/env python3
"""
AuthenticityChecker - 架空キャラクターエピソード真正性検証エンジン

LLMが生成した架空キャラクターのエピソードが、
原作に基づいているか（canon）を検証するクラス。

## 設計方針
- canonのみ保存: 原作に明確に描かれたシーンのみ許可
- 出典必須: エピソードには必ず原作出典が必要
- CanonKB照合: 出典がCanonKBに存在するか検証

## 検証フロー
1. ルールベース検証（メタ要素、年号等）- FictionalQualityGateに委譲
2. 原作整合性チェック（CanonKB照合）
3. 出典検証

## 使用例
    checker = AuthenticityChecker()
    result = checker.check(episode_dict)
    if result.passed:
        # 書き込みOK
    else:
        # 棄却または再生成

Author: EPUP Validation Team
Date: 2026-01-30
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.utils.canon_kb import CanonKB
from src.utils.fictional_characters import is_fictional_character

logger = logging.getLogger(__name__)


# =============================================================================
# データクラス定義
# =============================================================================


class AuthenticityStatus(Enum):
    """真正性ステータス"""

    CANON = "canon"  # 原作に描かれたシーン
    NO_MATCH = "no_match"  # 該当年齢に原作シーンなし
    INVALID = "invalid"  # 設定違反（年号・現実混入等）


@dataclass
class AuthenticityResult:
    """真正性検証結果"""

    passed: bool  # 書き込み可否
    status: AuthenticityStatus  # 分類結果
    canon_source: Optional[str] = None  # 出典（canonの場合）
    confidence: float = 0.0  # 確信度 0.0-1.0
    violations: list[str] = field(default_factory=list)  # 違反理由リスト
    suggestion: Optional[str] = None  # 修正提案（あれば）
    matching_scenes: list[dict] = field(default_factory=list)  # マッチしたシーン

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "passed": self.passed,
            "status": self.status.value,
            "canon_source": self.canon_source,
            "confidence": self.confidence,
            "violations": self.violations,
            "suggestion": self.suggestion,
            "matching_scenes": self.matching_scenes,
        }


# =============================================================================
# AuthenticityChecker クラス
# =============================================================================


class AuthenticityChecker:
    """
    真正性検証エンジン

    架空キャラクターエピソードが原作（canon）に基づいているかを検証する。
    CanonKBと照合し、出典の存在確認とエピソード内容の整合性をチェックする。
    """

    # キーワードマッチングの最小一致語数
    MIN_KEYWORD_MATCH_COUNT = 2

    # 確信度の閾値
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.5

    def __init__(self, canon_kb: Optional[CanonKB] = None):
        """
        CanonKBをロード

        Args:
            canon_kb: CanonKBインスタンス（指定しない場合は新規作成）
        """
        self._canon_kb = canon_kb or CanonKB()
        logger.info("AuthenticityChecker initialized")

    @property
    def canon_kb(self) -> CanonKB:
        """CanonKBインスタンスを取得"""
        return self._canon_kb

    def check(self, episode: dict) -> AuthenticityResult:
        """
        エピソードの真正性をチェック

        Args:
            episode: {
                "episode_text": str,
                "person_name": str,
                "person_type": str,
                "work_title": str,
                "age": int,
                "canon_source": Optional[str]  # 生成時に付与された出典
            }

        Returns:
            AuthenticityResult
        """
        # 必要なフィールドを取得
        episode_text = str(episode.get("episode_text", ""))
        person_name = str(episode.get("person_name", ""))
        person_type = str(episode.get("person_type", "")).upper()
        work_title = str(episode.get("work_title", ""))
        age = episode.get("age")
        canon_source = episode.get("canon_source")

        # 1. 架空キャラでなければスキップ（REAL人物は対象外）
        if not self._is_target(person_type, person_name):
            return AuthenticityResult(
                passed=True,
                status=AuthenticityStatus.CANON,
                confidence=1.0,
            )

        # 2. canon_source が付与されているか確認
        if not canon_source:
            # 出典なし → 利用可能な出典を提案
            available_sources = self.suggest_canon_source(work_title, person_name, age)
            suggestion = None
            if available_sources:
                suggestion = f"利用可能な出典: {', '.join(available_sources[:3])}"

            return AuthenticityResult(
                passed=False,
                status=AuthenticityStatus.NO_MATCH,
                violations=["canon出典が必要です"],
                suggestion=suggestion,
            )

        # 3. 出典がCanonKBに存在するか検証
        if not self.verify_canon_source(work_title, person_name, canon_source):
            available_sources = self.suggest_canon_source(work_title, person_name, age)
            suggestion = "CanonKBに登録されている出典を使用してください"
            if available_sources:
                suggestion += f"。利用可能な出典: {', '.join(available_sources[:3])}"

            return AuthenticityResult(
                passed=False,
                status=AuthenticityStatus.NO_MATCH,
                violations=[f"出典 '{canon_source}' がCanonKBに存在しません"],
                suggestion=suggestion,
            )

        # 4. エピソード内容と出典の整合性チェック（キーワードマッチング）
        matching_scenes = self.find_matching_scenes(work_title, person_name, age, episode_text)

        if not matching_scenes:
            # シーンが見つからなかったが、出典は存在する
            # → 低確信度でpassとする（厳格モードでは不可にする場合はここを変更）
            return AuthenticityResult(
                passed=True,
                status=AuthenticityStatus.CANON,
                canon_source=canon_source,
                confidence=0.5,
                suggestion="エピソード内容と出典の整合性が低い可能性があります",
            )

        # 5. 全検証通過
        # 最もマッチしたシーンから確信度を計算
        best_match = matching_scenes[0] if matching_scenes else {}
        confidence = best_match.get("match_score", 0.9)

        return AuthenticityResult(
            passed=True,
            status=AuthenticityStatus.CANON,
            canon_source=canon_source,
            confidence=confidence,
            matching_scenes=matching_scenes,
        )

    def _is_target(self, person_type: str, person_name: str) -> bool:
        """
        検証対象かどうかを判定

        Args:
            person_type: 人物タイプ
            person_name: 人物名

        Returns:
            True if fictional character (検証対象)
        """
        # person_type で判定
        if "FICTIONAL" in person_type:
            return True

        # person_name から架空キャラ判定（二重チェック）
        if is_fictional_character(person_name):
            logger.warning(
                f"AuthenticityChecker: person_type不整合 - {person_name} はFICTIONALであるべき (現在: {person_type})"
            )
            return True

        return False

    def verify_canon_source(self, work_title: str, character: str, source: str) -> bool:
        """
        出典がCanonKBに存在するか検証

        Args:
            work_title: 作品タイトル
            character: キャラクター名
            source: 出典（例: "第1話「残酷」"）

        Returns:
            True if source exists in CanonKB
        """
        if not source:
            return False

        # CanonKBのhas_sceneメソッドを使用
        return self._canon_kb.has_scene(work_title, character, source)

    def find_matching_scenes(self, work_title: str, character: str, _age: Optional[int], text: str) -> list[dict]:
        """
        エピソードテキストに合致するCanonKBシーンを検索

        キーワードマッチングで候補を返す

        Args:
            work_title: 作品タイトル
            character: キャラクター名
            _age: 年齢（将来の年齢フィルタリング用、現在未使用）
            text: エピソードテキスト

        Returns:
            マッチしたシーンのリスト（match_scoreでソート）
        """
        if not text:
            return []

        # キャラクターのシーンを取得
        char_obj = self._canon_kb.get_character(work_title, character)
        if not char_obj:
            return []

        scenes = char_obj.key_scenes

        # テキストからキーワードを抽出
        text_keywords = self._extract_keywords(text)

        matching_scenes: list[dict] = []

        for scene in scenes:
            # シーンの説明からキーワードを抽出
            scene_keywords = self._extract_keywords(scene.description)

            # キーワードマッチング
            matched_keywords = text_keywords & scene_keywords
            match_count = len(matched_keywords)

            if match_count >= self.MIN_KEYWORD_MATCH_COUNT:
                # マッチスコアを計算（0.0-1.0）
                total_keywords = len(text_keywords | scene_keywords)
                match_score = match_count / total_keywords if total_keywords > 0 else 0

                matching_scenes.append(
                    {
                        "scene_id": scene.scene_id,
                        "description": scene.description,
                        "story_arc": scene.story_arc,
                        "source_reference": scene.source_reference,
                        "matched_keywords": list(matched_keywords),
                        "match_score": round(match_score, 3),
                    }
                )

        # マッチスコアでソート（降順）
        matching_scenes.sort(key=lambda x: x["match_score"], reverse=True)

        return matching_scenes

    def _extract_keywords(self, text: str) -> set[str]:
        """
        テキストからキーワードを抽出

        Args:
            text: テキスト

        Returns:
            キーワードのセット
        """
        if not text:
            return set()

        # 日本語の名詞・動詞を抽出（簡易版）
        # より高度な解析にはMeCab等を使用することを推奨
        keywords: set[str] = set()

        # カタカナ語を抽出
        katakana_pattern = re.compile(r"[ァ-ヶー]{2,}")
        keywords.update(katakana_pattern.findall(text))

        # 漢字語を抽出（2文字以上）
        kanji_pattern = re.compile(r"[一-龥]{2,}")
        keywords.update(kanji_pattern.findall(text))

        # 固有名詞パターン（「」で囲まれた語）
        quoted_pattern = re.compile(r"「([^」]+)」")
        keywords.update(quoted_pattern.findall(text))

        # ストップワードを除外
        stopwords = {
            "これ",
            "それ",
            "あれ",
            "この",
            "その",
            "あの",
            "ここ",
            "そこ",
            "あそこ",
            "こちら",
            "どこ",
            "だれ",
            "なに",
            "なん",
            "何",
            "私",
            "僕",
            "俺",
            "自分",
            "である",
            "ある",
            "いる",
            "する",
            "なる",
            "れる",
            "られる",
            "せる",
            "させる",
            "ない",
            "たい",
            "ている",
            "ていた",
            "ました",
            "ません",
            "でした",
            "です",
            "ます",
        }
        keywords -= stopwords

        return keywords

    def suggest_canon_source(self, work_title: str, character: str, age: Optional[int]) -> list[str]:
        """
        指定年齢で利用可能なcanon出典を提案

        エピソード生成プロンプト強化用

        Args:
            work_title: 作品タイトル
            character: キャラクター名
            age: 年齢（Noneの場合は全年齢対象）

        Returns:
            利用可能な出典リスト
        """
        sources: list[str] = []

        # キャラクターを取得
        char_obj = self._canon_kb.get_character(work_title, character)
        if not char_obj:
            return sources

        # 年齢別マイルストーンがあれば、その出典を追加
        if age is not None:
            for milestone in char_obj.age_milestones:
                if milestone.age == age and milestone.source:
                    sources.append(milestone.source)

        # キーシーンの出典を追加
        for scene in char_obj.key_scenes:
            if scene.source_reference and scene.source_reference not in sources:
                sources.append(scene.source_reference)

        return sources

    def is_fictional_character(self, person_name: str) -> bool:
        """
        架空キャラクターか判定（fictional_characters.pyに委譲）

        Args:
            person_name: 人物名

        Returns:
            True if fictional character
        """
        return is_fictional_character(person_name)

    def get_character_info(self, work_title: str, character: str) -> Optional[dict]:
        """
        キャラクター情報を取得

        Args:
            work_title: 作品タイトル
            character: キャラクター名

        Returns:
            キャラクター情報（見つからない場合はNone）
        """
        char_obj = self._canon_kb.get_character(work_title, character)
        if not char_obj:
            return None

        return {
            "name": char_obj.name,
            "character_id": char_obj.character_id,
            "aliases": char_obj.aliases,
            "age_at_story": char_obj.age_at_story,
            "abilities": char_obj.abilities,
            "key_scenes_count": len(char_obj.key_scenes),
            "age_milestones_count": len(char_obj.age_milestones),
        }


# =============================================================================
# ユーティリティ関数
# =============================================================================


def check_authenticity(episode: dict) -> AuthenticityResult:
    """
    エピソードの真正性をチェック（シンプルAPI）

    Args:
        episode: エピソードデータ

    Returns:
        AuthenticityResult
    """
    checker = AuthenticityChecker()
    return checker.check(episode)


# =============================================================================
# CLI (テスト用)
# =============================================================================


if __name__ == "__main__":
    # テスト実行
    checker = AuthenticityChecker()

    print("=" * 60)
    print("AuthenticityChecker - テスト実行")
    print("=" * 60)

    # テストケース1: 出典ありのcanonエピソード
    episode1 = {
        "episode_text": "竈門炭治郎は家族を鬼に殺され、唯一生き残った妹・禰豆子が鬼になってしまった。",
        "person_name": "竈門炭治郎",
        "person_type": "FICTIONAL",
        "work_title": "鬼滅の刃",
        "age": 13,
        "canon_source": "第1話「残酷」",
    }
    result1 = checker.check(episode1)
    print("\n[Test 1: 出典ありのcanonエピソード]")
    print(f"  Passed: {result1.passed}")
    print(f"  Status: {result1.status.value}")
    print(f"  Confidence: {result1.confidence}")
    if result1.violations:
        print(f"  Violations: {result1.violations}")
    if result1.suggestion:
        print(f"  Suggestion: {result1.suggestion}")

    # テストケース2: 出典なしのエピソード
    episode2 = {
        "episode_text": "竈門炭治郎は鬼殺隊に入隊し、多くの鬼と戦った。",
        "person_name": "竈門炭治郎",
        "person_type": "FICTIONAL",
        "work_title": "鬼滅の刃",
        "age": 15,
        "canon_source": None,
    }
    result2 = checker.check(episode2)
    print("\n[Test 2: 出典なしのエピソード]")
    print(f"  Passed: {result2.passed}")
    print(f"  Status: {result2.status.value}")
    if result2.violations:
        print(f"  Violations: {result2.violations}")
    if result2.suggestion:
        print(f"  Suggestion: {result2.suggestion}")

    # テストケース3: 実在人物（スキップ）
    episode3 = {
        "episode_text": "アルベルト・アインシュタインは相対性理論を発表した。",
        "person_name": "アルベルト・アインシュタイン",
        "person_type": "REAL",
        "work_title": "",
        "age": 26,
        "canon_source": None,
    }
    result3 = checker.check(episode3)
    print("\n[Test 3: 実在人物（スキップ）]")
    print(f"  Passed: {result3.passed}")
    print(f"  Status: {result3.status.value}")

    # テストケース4: 利用可能な出典の提案
    print("\n[Test 4: 利用可能な出典の提案]")
    sources = checker.suggest_canon_source("鬼滅の刃", "竈門炭治郎", 13)
    print(f"  Available sources for 竈門炭治郎 (age 13): {sources[:5]}")

    # テストケース5: キャラクター情報の取得
    print("\n[Test 5: キャラクター情報の取得]")
    char_info = checker.get_character_info("鬼滅の刃", "竈門炭治郎")
    if char_info:
        print(f"  Character: {char_info['name']}")
        print(f"  Aliases: {char_info['aliases']}")
        print(f"  Key scenes: {char_info['key_scenes_count']}")
    else:
        print("  Character not found in CanonKB")
