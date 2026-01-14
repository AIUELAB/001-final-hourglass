#!/usr/bin/env python3
"""
EPUP: 架空キャラクター エピソード バリデータ

架空キャラクターのエピソードに対する包括的な検証ルールを提供する。

検証ルール:
1. era_consistency_check: 時代設定整合性チェック
   - 歴史設定作品（鬼滅の刃=大正時代、るろうに剣心=明治時代）で現代年号を検出

2. name_format_check: 名前フォーマットチェック
   - 「{名}（{姓}）」パターンの検出（正しくは「{姓}{名}」フルネーム）

3. work_fact_check: 作品ファクトチェック
   - キャラクターと編/アーク/イベントの整合性

使用方法:
    # 全件スキャン
    python scripts/validation/fictional_episode_validator.py

    # 特定のエピソードチェック
    python scripts/validation/fictional_episode_validator.py --episode-id EP-123456

    # 特定ルールのみ
    python scripts/validation/fictional_episode_validator.py --rule era_consistency

    # CI用（違反があればexit 1）
    python scripts/validation/fictional_episode_validator.py --strict

    # JSONレポート出力
    python scripts/validation/fictional_episode_validator.py --output report.json

Author: EPUP Validation Team
Date: 2026-01-15
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"


# =============================================================================
# 検証ルールの定義
# =============================================================================


class ViolationType(Enum):
    """違反タイプ"""

    ERA_INCONSISTENCY = "ERA_INCONSISTENCY"  # 時代設定不整合
    NAME_FORMAT_ERROR = "NAME_FORMAT_ERROR"  # 名前フォーマット違反
    WORK_FACT_ERROR = "WORK_FACT_ERROR"  # 作品ファクト違反
    META_REFERENCE = "META_REFERENCE"  # メタ参照（作品名の直接言及）
    MODERN_YEAR_IN_HISTORICAL = "MODERN_YEAR_IN_HISTORICAL"  # 歴史作品内の現代年号


# =============================================================================
# 作品・時代マッピング
# =============================================================================

# 作品の時代設定マッピング
# キー: 作品タイトル（部分一致用）
# 値: (開始年, 終了年, 時代名, 許可されない現代年号パターン)
WORK_ERA_SETTINGS: dict[str, dict] = {
    # 大正時代作品
    "鬼滅の刃": {
        "era_start": 1912,
        "era_end": 1926,
        "era_name": "大正時代",
        "prohibited_years": range(1945, 2030),  # 昭和後期〜現代の年号は禁止
        "description": "大正時代の日本が舞台",
    },
    # 明治時代作品
    "るろうに剣心": {
        "era_start": 1868,
        "era_end": 1912,
        "era_name": "明治時代",
        "prohibited_years": range(1930, 2030),
        "description": "明治時代の日本が舞台",
    },
    # 戦国時代作品
    "信長の野望": {
        "era_start": 1467,
        "era_end": 1615,
        "era_name": "戦国時代",
        "prohibited_years": range(1800, 2030),
        "description": "戦国時代の日本が舞台",
    },
    "戦国BASARA": {
        "era_start": 1467,
        "era_end": 1615,
        "era_name": "戦国時代",
        "prohibited_years": range(1800, 2030),
        "description": "戦国時代の日本が舞台（ファンタジー要素あり）",
    },
    # 幕末作品
    "銀魂": {
        "era_start": 1853,
        "era_end": 1868,
        "era_name": "幕末（パラレル）",
        "prohibited_years": [],  # 銀魂はSFパラレルなので年号制限なし
        "description": "幕末パラレルワールド（宇宙人来襲設定）",
    },
    "薄桜鬼": {
        "era_start": 1853,
        "era_end": 1869,
        "era_name": "幕末",
        "prohibited_years": range(1900, 2030),
        "description": "幕末の新選組が舞台",
    },
    # 三国志時代
    "三国志": {
        "era_start": 184,
        "era_end": 280,
        "era_name": "三国時代",
        "prohibited_years": range(500, 2030),
        "description": "中国三国時代が舞台",
    },
    "キングダム": {
        "era_start": -259,
        "era_end": -206,
        "era_name": "秦の始皇帝時代",
        "prohibited_years": range(0, 2030),
        "description": "中国戦国時代〜秦統一が舞台",
    },
    # 中世ヨーロッパ風
    "ベルセルク": {
        "era_start": 1000,
        "era_end": 1500,
        "era_name": "中世ヨーロッパ風",
        "prohibited_years": range(1800, 2030),
        "description": "中世ヨーロッパ風のダークファンタジー",
    },
    "進撃の巨人": {
        "era_start": 845,  # 作品内年号
        "era_end": 860,
        "era_name": "独自年号",
        "prohibited_years": range(1000, 2030),  # 西暦は全て禁止
        "description": "独自の年号体系を使用",
    },
    # 現代設定（年号制限なし）
    "名探偵コナン": {
        "era_start": 1990,
        "era_end": 2030,
        "era_name": "現代",
        "prohibited_years": [],
        "description": "現代日本が舞台",
    },
    "ドラえもん": {
        "era_start": 1970,
        "era_end": 2030,
        "era_name": "現代",
        "prohibited_years": [],
        "description": "現代日本が舞台",
    },
    "ONE PIECE": {
        "era_start": None,  # 架空世界
        "era_end": None,
        "era_name": "架空世界",
        "prohibited_years": range(1000, 2030),  # 西暦は使用しない
        "description": "架空の海賊世界",
    },
    "NARUTO": {
        "era_start": None,
        "era_end": None,
        "era_name": "架空世界",
        "prohibited_years": range(1000, 2030),
        "description": "架空の忍者世界",
    },
    "ドラゴンボール": {
        "era_start": None,
        "era_end": None,
        "era_name": "架空世界",
        "prohibited_years": [],  # エイジという独自年号を使用
        "description": "架空世界（エイジ年号使用）",
    },
}

# キャラクターの作品出演マッピング
# キー: キャラクター名
# 値: 出演作品・アーク情報
CHARACTER_WORK_MAP: dict[str, dict] = {
    # 鬼滅の刃キャラクター
    "竈門炭治郎": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": [
            "最終選別編",
            "浅草編",
            "那田蜘蛛山編",
            "柱合会議・蝶屋敷編",
            "無限列車編",
            "遊郭編",
            "刀鍛冶の里編",
            "柱稽古編",
            "無限城編",
        ],
        "not_appears_in_arcs": [],
    },
    "竈門禰豆子": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": [
            "最終選別編",
            "浅草編",
            "那田蜘蛛山編",
            "柱合会議・蝶屋敷編",
            "無限列車編",
            "遊郭編",
            "刀鍛冶の里編",
            "柱稽古編",
            "無限城編",
        ],
        "not_appears_in_arcs": [],
    },
    "我妻善逸": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": [
            "最終選別編",
            "那田蜘蛛山編",
            "柱合会議・蝶屋敷編",
            "無限列車編",
            "遊郭編",
            "刀鍛冶の里編",
            "柱稽古編",
            "無限城編",
        ],
        "not_appears_in_arcs": ["浅草編"],
    },
    "嘴平伊之助": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": [
            "那田蜘蛛山編",
            "柱合会議・蝶屋敷編",
            "無限列車編",
            "遊郭編",
            "刀鍛冶の里編",
            "柱稽古編",
            "無限城編",
        ],
        "not_appears_in_arcs": ["最終選別編", "浅草編"],
    },
    "栗花落カナヲ": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["最終選別編", "柱合会議・蝶屋敷編", "柱稽古編", "無限城編"],
        "not_appears_in_arcs": [
            "浅草編",
            "那田蜘蛛山編",
            "無限列車編",
            "遊郭編",
            "刀鍛冶の里編",
        ],  # 重要: カナヲは無限列車編に登場しない
    },
    "煉獄杏寿郎": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["柱合会議・蝶屋敷編", "無限列車編"],
        "not_appears_in_arcs": ["浅草編", "那田蜘蛛山編", "遊郭編", "刀鍛冶の里編"],  # 無限列車編で死亡
    },
    "胡蝶しのぶ": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["那田蜘蛛山編", "柱合会議・蝶屋敷編", "柱稽古編", "無限城編"],
        "not_appears_in_arcs": ["最終選別編", "浅草編", "無限列車編", "遊郭編", "刀鍛冶の里編"],
    },
    "冨岡義勇": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["最終選別編", "那田蜘蛛山編", "柱合会議・蝶屋敷編", "柱稽古編", "無限城編"],
        "not_appears_in_arcs": ["浅草編", "無限列車編", "遊郭編", "刀鍛冶の里編"],
    },
    "宇髄天元": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["柱合会議・蝶屋敷編", "遊郭編", "柱稽古編"],
        "not_appears_in_arcs": [
            "最終選別編",
            "浅草編",
            "那田蜘蛛山編",
            "無限列車編",
            "刀鍛冶の里編",
            "無限城編",
        ],  # 遊郭編後引退
    },
    "甘露寺蜜璃": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["柱合会議・蝶屋敷編", "刀鍛冶の里編", "柱稽古編", "無限城編"],
        "not_appears_in_arcs": ["最終選別編", "浅草編", "那田蜘蛛山編", "無限列車編", "遊郭編"],
    },
    "時透無一郎": {
        "work_title": "鬼滅の刃",
        "appears_in_arcs": ["柱合会議・蝶屋敷編", "刀鍛冶の里編", "柱稽古編", "無限城編"],
        "not_appears_in_arcs": ["最終選別編", "浅草編", "那田蜘蛛山編", "無限列車編", "遊郭編"],
    },
    # るろうに剣心キャラクター
    "緋村剣心": {
        "work_title": "るろうに剣心",
        "appears_in_arcs": ["東京編", "京都編", "人誅編"],
        "not_appears_in_arcs": [],
    },
    "神谷薫": {
        "work_title": "るろうに剣心",
        "appears_in_arcs": ["東京編", "京都編", "人誅編"],
        "not_appears_in_arcs": [],
    },
    # 進撃の巨人キャラクター
    "エレン・イェーガー": {
        "work_title": "進撃の巨人",
        "appears_in_arcs": [
            "トロスト区攻防戦",
            "第57回壁外調査",
            "ウトガルド城の戦い",
            "ウォール・マリア最終奪還作戦",
            "マーレ編",
        ],
        "not_appears_in_arcs": [],
    },
    "ミカサ・アッカーマン": {
        "work_title": "進撃の巨人",
        "appears_in_arcs": [
            "トロスト区攻防戦",
            "第57回壁外調査",
            "ウトガルド城の戦い",
            "ウォール・マリア最終奪還作戦",
            "マーレ編",
        ],
        "not_appears_in_arcs": [],
    },
}

# 名前フォーマット検出パターン
# 「{名}（{姓}）」形式は誤りとして検出
NAME_FORMAT_ERROR_PATTERNS = [
    # カタカナ名（姓）パターン
    (r"^([ァ-ヶー]{2,})（([ァ-ヶー]{2,})）$", "カタカナ名（姓）"),
    # ひらがな名（姓）パターン
    (r"^([ぁ-ん]{2,})（([ぁ-ん]{2,})）$", "ひらがな名（姓）"),
    # 漢字+カナ混合パターン
    (r"^(.{1,5})（(.{1,5})）$", "一般名（姓）"),
]

# 作品名の直接言及検出パターン（メタ参照）
# 注: 非キャプチャグループ(?:...)を使用し、re.findall()が完全マッチを返すようにする
# Phase 36: パターン拡張（『』対応、助詞拡張、作品リスト拡充）
_WORK_TITLES = r"鬼滅の刃|るろうに剣心|進撃の巨人|ONE PIECE|NARUTO|ドラゴンボール|ハリー・ポッター|聖闘士星矢|コードギアス|グラップラー刃牙|呪術廻戦|ポケットモンスター|スター・ウォーズ|範馬刃牙|ジョジョの奇妙な冒険|新世紀エヴァンゲリオン|機動戦士ガンダム|銀魂|BLEACH|HUNTER×HUNTER"
_PARTICLES = r"に|を|が|は|も|で|の|において|の世界で|という|では"

META_WORK_REFERENCE_PATTERNS = [
    # 「作品名」+助詞 パターン（拡張版）
    rf"「(?:{_WORK_TITLES})」(?:{_PARTICLES})",
    # 『作品名』+助詞 パターン（二重鉤括弧対応）
    rf"『(?:{_WORK_TITLES})』(?:{_PARTICLES})",
    # 〜の世界観/物語/作品 パターン
    rf"(?:{_WORK_TITLES})の(?:世界|物語|作品|ストーリー)(?:観|設定|の中)?",
    # 作品タイトル+公開年 パターン
    r"\d{4}年(?:に|の)「.+?」(?:公開|放映|連載)",
    # 「作品名」シリーズ/作品 パターン
    r"「.+?」(?:シリーズ|作品)(?:に|を|が|は|で|の|において)",
]


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class Violation:
    """違反情報"""

    episode_id: str
    person_name: str
    violation_type: ViolationType
    message: str
    details: dict = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class ValidationResult:
    """検証結果"""

    episode_id: str
    person_name: str
    is_valid: bool
    violations: list[Violation] = field(default_factory=list)
    checked_rules: list[str] = field(default_factory=list)


# =============================================================================
# バリデータクラス
# =============================================================================


class FictionalEpisodeValidator:
    """
    架空キャラクターエピソードバリデータ

    複数の検証ルールを組み合わせて、架空キャラクターのエピソードを包括的に検証する。
    """

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None

        # ルール有効/無効設定
        self.enabled_rules = {
            "era_consistency": True,
            "name_format": True,
            "work_fact": True,
            "meta_reference": True,
        }

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def enable_rule(self, rule_name: str, enabled: bool = True) -> None:
        """ルールの有効/無効を設定"""
        if rule_name in self.enabled_rules:
            self.enabled_rules[rule_name] = enabled

    def validate_episode(self, row: dict) -> ValidationResult:
        """
        単一エピソードを検証

        Args:
            row: エピソードデータ（dict形式）

        Returns:
            ValidationResult: 検証結果
        """
        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()
        episode_text = str(row.get("episode_text", ""))
        work_title = str(row.get("work_title", ""))

        result = ValidationResult(
            episode_id=episode_id,
            person_name=person_name,
            is_valid=True,
            violations=[],
            checked_rules=[],
        )

        # FICTIONALのみを対象
        if "FICTIONAL" not in person_type:
            return result

        # 1. 時代整合性チェック
        if self.enabled_rules.get("era_consistency"):
            era_violations = self._check_era_consistency(episode_id, person_name, episode_text, work_title)
            result.violations.extend(era_violations)
            result.checked_rules.append("era_consistency")

        # 2. 名前フォーマットチェック
        if self.enabled_rules.get("name_format"):
            name_violations = self._check_name_format(episode_id, person_name)
            result.violations.extend(name_violations)
            result.checked_rules.append("name_format")

        # 3. 作品ファクトチェック
        if self.enabled_rules.get("work_fact"):
            fact_violations = self._check_work_facts(episode_id, person_name, episode_text, work_title)
            result.violations.extend(fact_violations)
            result.checked_rules.append("work_fact")

        # 4. メタ参照チェック
        if self.enabled_rules.get("meta_reference"):
            meta_violations = self._check_meta_references(episode_id, person_name, episode_text)
            result.violations.extend(meta_violations)
            result.checked_rules.append("meta_reference")

        result.is_valid = len(result.violations) == 0
        return result

    def _check_era_consistency(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        work_title: str,
    ) -> list[Violation]:
        """
        時代整合性チェック

        歴史設定の作品で現代の年号が使われていないかをチェックする。
        """
        violations = []

        # 作品タイトルから時代設定を特定
        era_setting = self._get_era_setting(work_title, person_name)
        if era_setting is None:
            return violations

        prohibited_years = era_setting.get("prohibited_years", [])
        if not prohibited_years:
            return violations

        # エピソードテキストから年号を抽出
        # 西暦パターン: 1900年〜2099年
        year_pattern = r"(19\d{2}|20\d{2})年"
        found_years = re.findall(year_pattern, episode_text)

        for year_str in found_years:
            year = int(year_str)
            if year in prohibited_years:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        violation_type=ViolationType.MODERN_YEAR_IN_HISTORICAL,
                        message=f"歴史設定作品に現代年号を検出: {year}年",
                        details={
                            "work_title": work_title or era_setting.get("work_title"),
                            "era_name": era_setting.get("era_name"),
                            "era_range": f"{era_setting.get('era_start')}-{era_setting.get('era_end')}",
                            "detected_year": year,
                            "text_snippet": self._get_context_snippet(episode_text, str(year)),
                        },
                        severity="ERROR",
                    )
                )

        return violations

    def _check_name_format(self, episode_id: str, person_name: str) -> list[Violation]:
        """
        名前フォーマットチェック

        「{名}（{姓}）」形式の誤った名前フォーマットを検出する。
        """
        violations = []

        for pattern, pattern_name in NAME_FORMAT_ERROR_PATTERNS:
            if re.match(pattern, person_name):
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        violation_type=ViolationType.NAME_FORMAT_ERROR,
                        message=f"名前フォーマット違反: {pattern_name}形式",
                        details={
                            "detected_pattern": pattern_name,
                            "expected_format": "「{姓}{名}」のフルネーム形式",
                            "current_format": person_name,
                        },
                        severity="ERROR",
                    )
                )
                break  # 1つ検出したら終了

        return violations

    def _check_work_facts(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        work_title: str,
    ) -> list[Violation]:
        """
        作品ファクトチェック

        キャラクターが登場しないアーク/編への言及を検出する。
        """
        violations = []

        # キャラクター情報を取得
        char_info = CHARACTER_WORK_MAP.get(person_name)
        if char_info is None:
            return violations

        not_appears_in = char_info.get("not_appears_in_arcs", [])

        for arc in not_appears_in:
            if arc in episode_text:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
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
                )

        return violations

    def _check_meta_references(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
    ) -> list[Violation]:
        """
        メタ参照チェック

        作品名を直接言及するメタ的な表現を検出する。
        """
        violations = []

        for pattern in META_WORK_REFERENCE_PATTERNS:
            matches = re.findall(pattern, episode_text)
            if matches:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        violation_type=ViolationType.META_REFERENCE,
                        message="作品名の直接言及（メタ参照）を検出",
                        details={
                            "pattern": pattern,
                            "matches": matches[:3],  # 最大3件
                            "text_snippet": self._get_context_snippet(episode_text, str(matches[0]) if matches else ""),
                        },
                        severity="WARNING",
                    )
                )

        return violations

    def _get_era_setting(self, work_title: str, person_name: str) -> Optional[dict]:
        """作品の時代設定を取得"""
        # 作品タイトルから検索
        if work_title and str(work_title) != "nan":
            for title_key, setting in WORK_ERA_SETTINGS.items():
                if title_key in work_title:
                    return setting

        # キャラクター名から検索
        char_info = CHARACTER_WORK_MAP.get(person_name)
        if char_info:
            work = char_info.get("work_title")
            if work and work in WORK_ERA_SETTINGS:
                return WORK_ERA_SETTINGS[work]

        return None

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

    def scan_all_episodes(self, person_type_filter: str = "FICTIONAL") -> list[ValidationResult]:
        """
        全エピソードをスキャン

        Args:
            person_type_filter: フィルタリングする人物タイプ

        Returns:
            違反のあるエピソードの検証結果リスト
        """
        if self.master_df.empty:
            return []

        results = []

        # FICTIONALのみフィルタ
        df = self.master_df
        if person_type_filter:
            df = df[df["person_type"].str.upper().str.contains(person_type_filter, na=False)]

        for _, row in df.iterrows():
            result = self.validate_episode(row.to_dict())
            if not result.is_valid:
                results.append(result)

        return results

    def get_violation_summary(self, results: list[ValidationResult]) -> dict:
        """
        違反サマリーを生成

        Args:
            results: 検証結果リスト

        Returns:
            サマリー辞書
        """
        total_violations = 0
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        affected_characters: set[str] = set()
        affected_works: set[str] = set()

        for result in results:
            for violation in result.violations:
                total_violations += 1

                # タイプ別集計
                vtype = violation.violation_type.value
                by_type[vtype] = by_type.get(vtype, 0) + 1

                # 重大度別集計
                by_severity[violation.severity] += 1

                # 影響キャラクター
                affected_characters.add(violation.person_name)

                # 影響作品
                work = violation.details.get("work_title")
                if work:
                    affected_works.add(work)

        summary: dict[str, Any] = {
            "total_violations": total_violations,
            "by_type": by_type,
            "by_severity": by_severity,
            "affected_characters": list(affected_characters),
            "affected_works": list(affected_works),
        }

        return summary


# =============================================================================
# CLI
# =============================================================================


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 架空キャラクター エピソード バリデータ")
    parser.add_argument(
        "--episode-id",
        type=str,
        help="特定のエピソードIDをチェック",
    )
    parser.add_argument(
        "--rule",
        choices=["era_consistency", "name_format", "work_fact", "meta_reference"],
        help="特定のルールのみ実行",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="違反があればexit 1",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="JSONレポート出力先",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="表示する違反の最大件数（0=無制限）",
    )

    args = parser.parse_args()

    # バリデータ初期化
    validator = FictionalEpisodeValidator()

    # 特定ルールのみ有効化
    if args.rule:
        for rule in validator.enabled_rules:
            validator.enable_rule(rule, rule == args.rule)

    # 特定エピソードのチェック
    if args.episode_id:
        df = validator.master_df
        if df.empty:
            print(f"Error: Master CSV not found: {validator.master_csv}")
            return 2

        row = df[df["episode_id"] == args.episode_id]
        if row.empty:
            print(f"Error: Episode not found: {args.episode_id}")
            return 1

        result = validator.validate_episode(row.iloc[0].to_dict())

        print(f"Episode: {result.episode_id}")
        print(f"Person: {result.person_name}")
        print(f"Valid: {result.is_valid}")
        print(f"Checked rules: {', '.join(result.checked_rules)}")

        if result.violations:
            print("\nViolations:")
            for v in result.violations:
                print(f"  [{v.severity}] {v.violation_type.value}")
                print(f"    Message: {v.message}")
                for key, value in v.details.items():
                    print(f"    {key}: {value}")

        return 0 if result.is_valid else 1

    # 全件スキャン
    print("=" * 70)
    print("EPUP: 架空キャラクター エピソード バリデータ")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print("\nスキャン中...")
    results = validator.scan_all_episodes()

    # サマリー生成
    summary = validator.get_violation_summary(results)

    print(f"\n検出された違反: {summary['total_violations']}件")
    print(f"影響を受けるエピソード: {len(results)}件")
    print(f"影響を受けるキャラクター: {len(summary['affected_characters'])}人")

    if summary["by_type"]:
        print("\n違反タイプ別:")
        for vtype, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
            print(f"  {vtype}: {count}件")

    if summary["by_severity"]["ERROR"] > 0 or summary["by_severity"]["WARNING"] > 0:
        print("\n重大度別:")
        for severity, count in summary["by_severity"].items():
            if count > 0:
                print(f"  {severity}: {count}件")

    # 詳細表示
    if results:
        limit = args.limit or 20
        print(f"\n詳細（上位{min(limit, len(results))}件）:")

        for i, result in enumerate(results[:limit], 1):
            print(f"\n{i}. {result.episode_id} | {result.person_name}")
            for v in result.violations:
                print(f"   [{v.severity}] {v.violation_type.value}: {v.message}")

    # JSONレポート出力
    if args.output:
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "violations": [
                {
                    "episode_id": r.episode_id,
                    "person_name": r.person_name,
                    "violations": [
                        {
                            "type": v.violation_type.value,
                            "severity": v.severity,
                            "message": v.message,
                            "details": v.details,
                        }
                        for v in r.violations
                    ],
                }
                for r in results
            ],
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nレポート保存: {output_path}")

    # 終了コード
    if args.strict and summary["total_violations"] > 0:
        print(f"\n[FAILED] {summary['total_violations']}件の違反があります")
        return 1

    print("\n[OK] スキャン完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
