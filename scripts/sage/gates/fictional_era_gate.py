#!/usr/bin/env python3
"""
SAGE Gate: 架空キャラクター 時代設定整合性ゲート

生成前および生成後に架空キャラクターの時代設定整合性をチェックする。

機能:
1. Pre-generation: 候補の時代設定を検証
2. Post-generation: 生成されたテキストの時代設定を検証

使用方法:
    # SAGEパイプラインから呼び出し
    from scripts.sage.gates.fictional_era_gate import FictionalEraGate

    gate = FictionalEraGate()
    result = gate.check_pre_generation(candidate)
    result = gate.check_post_generation(episode_text, person_name, work_title)

Author: SAGE Gates Team
Date: 2026-01-15
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.fictional_episode_validator import (
    CHARACTER_WORK_MAP,
    META_WORK_REFERENCE_PATTERNS,
    WORK_ERA_SETTINGS,
    ViolationType,
)


@dataclass
class GateCheckResult:
    """ゲートチェック結果"""

    passed: bool
    violation_type: Optional[ViolationType] = None
    message: str = ""
    details: dict = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class FictionalEraGate:
    """
    架空キャラクター時代設定整合性ゲート

    SAGE生成パイプラインに統合される品質ゲート。
    """

    def __init__(self):
        # 追加の作品・キャラクター情報を動的にロード可能
        self.work_era_settings = WORK_ERA_SETTINGS.copy()
        self.character_work_map = CHARACTER_WORK_MAP.copy()

    def check_pre_generation(
        self,
        person_name: str,
        age: int,
        person_type: str,
        work_title: str = "",
    ) -> GateCheckResult:
        """
        生成前チェック

        候補が時代設定に適合するかを事前検証する。

        Args:
            person_name: キャラクター名
            age: 年齢
            person_type: 人物タイプ
            work_title: 作品名

        Returns:
            GateCheckResult: チェック結果
        """
        # FICTIONAL以外はパス
        if "FICTIONAL" not in person_type.upper():
            return GateCheckResult(passed=True, message="Not a fictional character")

        # 作品情報を取得
        era_setting = self._get_era_setting(work_title, person_name)
        if era_setting is None:
            return GateCheckResult(
                passed=True,
                message="No era setting found for this work/character",
            )

        # キャラクター情報を取得
        char_info = self.character_work_map.get(person_name)

        # 注意事項をdetailsに含める
        return GateCheckResult(
            passed=True,
            message="Pre-generation check passed",
            details={
                "work_title": era_setting.get("work_title", work_title),
                "era_name": era_setting.get("era_name"),
                "era_range": f"{era_setting.get('era_start')}-{era_setting.get('era_end')}",
                "prohibited_years": bool(era_setting.get("prohibited_years")),
                "character_info": char_info is not None,
                "valid_arcs": char_info.get("appears_in_arcs", []) if char_info else [],
                "invalid_arcs": char_info.get("not_appears_in_arcs", []) if char_info else [],
            },
        )

    def check_post_generation(
        self,
        episode_text: str,
        person_name: str,
        person_type: str,
        work_title: str = "",
    ) -> GateCheckResult:
        """
        生成後チェック

        生成されたテキストが時代設定に適合するかを検証する。

        Args:
            episode_text: 生成されたエピソードテキスト
            person_name: キャラクター名
            person_type: 人物タイプ
            work_title: 作品名

        Returns:
            GateCheckResult: チェック結果
        """
        # FICTIONAL以外はパス
        if "FICTIONAL" not in person_type.upper():
            return GateCheckResult(passed=True, message="Not a fictional character")

        # 作品情報を取得
        era_setting = self._get_era_setting(work_title, person_name)

        # 1. 時代設定チェック
        if era_setting:
            era_result = self._check_era_in_text(episode_text, era_setting)
            if not era_result.passed:
                return era_result

        # 2. 作品ファクトチェック（キャラクター-アーク整合性）
        char_info = self.character_work_map.get(person_name)
        if char_info:
            fact_result = self._check_work_facts(episode_text, char_info, person_name)
            if not fact_result.passed:
                return fact_result

        # 3. メタ参照チェック
        meta_result = self._check_meta_references(episode_text)
        if not meta_result.passed:
            return meta_result

        return GateCheckResult(
            passed=True,
            message="Post-generation check passed",
            details={
                "era_check": "passed",
                "fact_check": "passed" if char_info else "skipped",
                "meta_check": "passed",
            },
        )

    def _get_era_setting(self, work_title: str, person_name: str) -> Optional[dict]:
        """作品の時代設定を取得"""
        if work_title and str(work_title) != "nan":
            for title_key, setting in self.work_era_settings.items():
                if title_key in work_title:
                    return {**setting, "work_title": title_key}

        char_info = self.character_work_map.get(person_name)
        if char_info:
            work = char_info.get("work_title")
            if work and work in self.work_era_settings:
                return {**self.work_era_settings[work], "work_title": work}

        return None

    def _check_era_in_text(self, episode_text: str, era_setting: dict) -> GateCheckResult:
        """テキスト内の年号をチェック"""
        prohibited_years = era_setting.get("prohibited_years", [])
        if not prohibited_years:
            return GateCheckResult(passed=True, message="No year restrictions")

        # 西暦パターン
        year_pattern = r"(19\d{2}|20\d{2})年"
        found_years = re.findall(year_pattern, episode_text)

        for year_str in found_years:
            year = int(year_str)
            if year in prohibited_years:
                return GateCheckResult(
                    passed=False,
                    violation_type=ViolationType.MODERN_YEAR_IN_HISTORICAL,
                    message=f"歴史設定作品に禁止年号を検出: {year}年",
                    details={
                        "work_title": era_setting.get("work_title"),
                        "era_name": era_setting.get("era_name"),
                        "detected_year": year,
                        "text_snippet": self._get_context_snippet(episode_text, str(year)),
                    },
                    severity="ERROR",
                )

        return GateCheckResult(passed=True, message="Era check passed")

    def _check_work_facts(self, episode_text: str, char_info: dict, person_name: str) -> GateCheckResult:
        """作品ファクト（キャラクター-アーク整合性）をチェック"""
        not_appears_in = char_info.get("not_appears_in_arcs", [])

        for arc in not_appears_in:
            if arc in episode_text:
                return GateCheckResult(
                    passed=False,
                    violation_type=ViolationType.WORK_FACT_ERROR,
                    message=f"キャラクターが登場しないアークへの言及: {arc}",
                    details={
                        "work_title": char_info.get("work_title"),
                        "character": person_name,
                        "invalid_arc": arc,
                        "valid_arcs": char_info.get("appears_in_arcs", []),
                        "text_snippet": self._get_context_snippet(episode_text, arc),
                    },
                    severity="ERROR",
                )

        return GateCheckResult(passed=True, message="Work fact check passed")

    def _check_meta_references(self, episode_text: str) -> GateCheckResult:
        """メタ参照をチェック"""
        for pattern in META_WORK_REFERENCE_PATTERNS:
            matches = re.findall(pattern, episode_text)
            if matches:
                return GateCheckResult(
                    passed=False,
                    violation_type=ViolationType.META_REFERENCE,
                    message="作品名の直接言及（メタ参照）を検出",
                    details={
                        "pattern": pattern,
                        "matches": matches[:3],
                    },
                    severity="WARNING",  # メタ参照はWARNING（棄却しないがログ）
                )

        return GateCheckResult(passed=True, message="Meta reference check passed")

    def _get_context_snippet(self, text: str, keyword: str, context_len: int = 50) -> str:
        """キーワード周辺のコンテキストを取得"""
        if not keyword or keyword not in text:
            return text[:100] + "..." if len(text) > 100 else text

        idx = text.find(keyword)
        start = max(0, idx - context_len)
        end = min(len(text), idx + len(keyword) + context_len)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet


# =============================================================================
# 便利関数（SAGEパイプラインから直接呼び出し用）
# =============================================================================

_gate_instance: Optional[FictionalEraGate] = None


def get_gate() -> FictionalEraGate:
    """シングルトンゲートインスタンスを取得"""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = FictionalEraGate()
    return _gate_instance


def check_fictional_era_pre(
    person_name: str,
    age: int,
    person_type: str,
    work_title: str = "",
) -> GateCheckResult:
    """
    生成前チェック（便利関数）

    Args:
        person_name: キャラクター名
        age: 年齢
        person_type: 人物タイプ
        work_title: 作品名

    Returns:
        GateCheckResult
    """
    return get_gate().check_pre_generation(person_name, age, person_type, work_title)


def check_fictional_era_post(
    episode_text: str,
    person_name: str,
    person_type: str,
    work_title: str = "",
) -> GateCheckResult:
    """
    生成後チェック（便利関数）

    Args:
        episode_text: 生成されたエピソードテキスト
        person_name: キャラクター名
        person_type: 人物タイプ
        work_title: 作品名

    Returns:
        GateCheckResult
    """
    return get_gate().check_post_generation(episode_text, person_name, person_type, work_title)


# =============================================================================
# CLI
# =============================================================================


def main():
    """CLI実行"""
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Gate: 架空キャラクター時代設定整合性ゲート")
    parser.add_argument(
        "--test",
        action="store_true",
        help="テスト実行",
    )

    args = parser.parse_args()

    if args.test:
        print("=" * 60)
        print("FictionalEraGate テスト実行")
        print("=" * 60)

        gate = FictionalEraGate()

        # テストケース1: 鬼滅の刃キャラクター（正常）
        print("\n[Test 1] Pre-generation check for 竈門炭治郎")
        result = gate.check_pre_generation(
            person_name="竈門炭治郎",
            age=15,
            person_type="FICTIONAL",
            work_title="鬼滅の刃",
        )
        print(f"  Passed: {result.passed}")
        print(f"  Details: {result.details}")

        # テストケース2: 現代年号を含むテキスト（違反）
        print("\n[Test 2] Post-generation check with modern year")
        test_text = "あなたと同じ15歳のとき、竈門炭治郎は2019年に鬼殺隊に入隊した。"
        result = gate.check_post_generation(
            episode_text=test_text,
            person_name="竈門炭治郎",
            person_type="FICTIONAL",
            work_title="鬼滅の刃",
        )
        print(f"  Passed: {result.passed}")
        print(f"  Message: {result.message}")
        print(f"  Details: {result.details}")

        # テストケース3: カナヲ + 無限列車（違反）
        print("\n[Test 3] Post-generation check with invalid arc")
        test_text = "あなたと同じ16歳のとき、栗花落カナヲは無限列車で戦った。"
        result = gate.check_post_generation(
            episode_text=test_text,
            person_name="栗花落カナヲ",
            person_type="FICTIONAL",
            work_title="鬼滅の刃",
        )
        print(f"  Passed: {result.passed}")
        print(f"  Message: {result.message}")
        print(f"  Details: {result.details}")

        # テストケース4: 正常なテキスト
        print("\n[Test 4] Post-generation check with valid text")
        test_text = "あなたと同じ16歳のとき、栗花落カナヲは蝶屋敷で機能回復訓練の指導にあたっていた。"
        result = gate.check_post_generation(
            episode_text=test_text,
            person_name="栗花落カナヲ",
            person_type="FICTIONAL",
            work_title="鬼滅の刃",
        )
        print(f"  Passed: {result.passed}")
        print(f"  Message: {result.message}")

        print("\n" + "=" * 60)
        print("テスト完了")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
