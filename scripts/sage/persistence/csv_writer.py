"""
Safe CSV Writer

安全なCSV追記とトランザクション管理。
"""

import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
import pandas as pd
from postgrest.exceptions import APIError
from supabase import Client as SupabaseClient, create_client
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Supabase同期設定
SUPABASE_TABLE = "episodes"
SUPABASE_BATCH_SIZE = 100
INTEGER_COLUMNS = {
    "episode_count",
    "age",
    "wikipedia_pv",
    "fame_rank_v3",
    "multi_lang_pv",
    "sitelinks_count",
    "google_hits",
    "celebrity_rank_v2",
    "episode_fame_tier_v6",
    "birth_year",
    "death_year",
}

from ..adapters.base import GenerationResult
from ..config import LOGS_DIR, MASTER_CSV
from .backup import BackupManager, create_pre_operation_backup
from ..gates.completeness import (
    auto_fill_all_derived_fields,
    check_completeness_extended,
)

# FICTIONAL文頭フォーマットゲート
from scripts.validation.fictional_lead_gate import check_fictional_lead_row

# FictionalQualityGate（架空キャラクター品質ゲート - RCA-20260115）
from src.utils.fictional_quality_gate import FictionalQualityGate

# UnifiedGate（DB反映前の最終ゲート - バイパス経路塞ぎ）
from .unified_gate import UnifiedGate, ViolationType

# RealPersonVerifier（REAL人物のハルシネーション検出 - RCA-20260203）
from scripts.validation.real_person_verifier import RealPersonVerifier

# 架空キャラクター名リスト（RCA-20260123: src/utils/に移動してアーキテクチャ違反解消）
from src.utils.fictional_characters import (
    ALL_FICTIONAL_CHARACTERS,
    BLACKLIST_NAMES,
    normalize_fictional_name,
)


@dataclass
class WriteResult:
    """書き込み結果"""

    success: bool
    added_count: int = 0
    skipped_count: int = 0
    replaced_count: int = 0  # Phase 4: 置換数
    error_message: str = ""
    backup_path: Optional[Path] = None
    diff_log_path: Optional[Path] = None
    supabase_synced: bool = True  # Supabase同期成功フラグ
    supabase_sync_count: int = 0  # Supabase同期成功件数

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "added_count": self.added_count,
            "skipped_count": self.skipped_count,
            "replaced_count": self.replaced_count,
            "error_message": self.error_message,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "diff_log_path": str(self.diff_log_path) if self.diff_log_path else None,
            "supabase_synced": self.supabase_synced,
            "supabase_sync_count": self.supabase_sync_count,
        }


@dataclass
class DiffEntry:
    """差分エントリ"""

    episode_id: str
    person_name: str
    age: int
    action: str  # 'add', 'update', 'delete'
    details: dict = field(default_factory=dict)


class SafeCSVWriter:
    """
    安全なCSV書き込み

    - dry-runモード
    - バックアップ作成
    - 差分ログ
    - トランザクション的操作
    """

    # Precompiled regex patterns for grammar/quality checking (H1: パフォーマンス最適化)
    _RE_HAWED = re.compile(r"[ぁ-んァ-ヶー一-龯a-zA-Z]はで、")
    _RE_TEIKITA = re.compile(r"ていきた[。、]")
    _RE_FIX_HAWED = re.compile(r"([ぁ-んァ-ヶー一-龯a-zA-Z])はで、")
    _RE_FIX_TEIKITA = re.compile(r"ていきた([。、])")
    _RE_NIARITA = re.compile(r"にありた([。、]|$)")
    _RE_TSUNAGARITA = re.compile(r"繋がりた([。、]|$)")
    _RE_NINARITA = re.compile(r"になりた([。、]|$)")
    _RE_TONARITA = re.compile(r"となりた([。、]|$)")
    _RE_GARITA = re.compile(r"(上|下|広|拡|高|深)がりた([。、]|$)")
    # 「◯◯は◯◯は」などの直後重複（読みづらさの主要因）
    _RE_DUP_HA = re.compile(r"([^\s、。]{2,60}は)([ \t]*\n?[ \t]*)(?:\1\2)+")
    _RE_PATTERN_C = re.compile(
        r"(あなたと同じ\d+歳のとき[、,]?[ \t]*\n?[ \t]*)" r"([^、。\n]{2,30})" r"(は)" r"([ \t]*\n?[ \t]*)" r"、"
    )

    # CSVカラム順序
    COLUMN_ORDER = [
        "episode_id",
        "person_id",
        "person_name",
        "age",
        "category",
        "episode_text",
        "episode_type",
        "char_count",
        "person_type",
        "slot",
        "tier",
        "generation_timestamp",
        "memorability_score",  # Phase 28: 英語化
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
        "iconic_score",  # Phase 28: 追加
        "grammar_quality_score",
        "composite_score",
        "super_total_score",
        # Phase 26: モデル追跡とコスト可視化
        "model",  # 使用モデル名（claude-3-5-haiku-20241022 等）
        "generator_type",  # batch_api_haiku / batch_api_sonnet
        "cost_usd",  # エピソード単位のコスト（USD）
    ]

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        logs_dir: Path = LOGS_DIR,
    ):
        self.master_csv = master_csv
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._backup_manager = BackupManager()

    def _generate_episode_id(self) -> str:
        """エピソードIDを生成"""
        timestamp = datetime.now().strftime("%y%m%d%H%M%S%f")[:15]
        return f"EP-{timestamp}"

    def _result_to_row(self, result: GenerationResult) -> dict:
        """GenerationResultをCSV行に変換"""
        row = result.to_csv_row()

        # エピソードIDを追加
        if "episode_id" not in row or not row["episode_id"]:
            row["episode_id"] = self._generate_episode_id()

        return row

    def _is_fictional_character(self, person_name: str) -> bool:
        """
        人物名から架空キャラクターを検出（RCA-20260122）

        detect_person_type_mismatch.py と同じ判定ロジックを使用。
        person_type誤分類時のフォールバック検出用。

        Args:
            person_name: 人物名

        Returns:
            架空キャラクターならTrue
        """
        if not person_name:
            return False
        # ブラックリスト（一般名との混同防止）
        if person_name in BLACKLIST_NAMES:
            return False
        return person_name in ALL_FICTIONAL_CHARACTERS

    def _check_grammar_errors(self, text: str) -> list[str]:
        """
        日本語文法エラーを検出する。

        Args:
            text: チェック対象テキスト

        Returns:
            検出されたエラーのリスト
        """
        # H2: None/型チェック追加
        if not text:
            return []
        errors = []
        # P1: 「はで、」パターン（助詞の誤用）- H1: プリコンパイル済みパターン使用
        if self._RE_HAWED.search(text):
            errors.append("「はで、」パターン検出 - 正しくは「は、」")
        # P2: 「ていきた」パターン（動詞活用の誤り）- H1: プリコンパイル済みパターン使用
        if self._RE_TEIKITA.search(text):
            errors.append("「ていきた」パターン検出 - 正しくは「ていった」")
        return errors

    def _fix_grammar_errors(self, text: str) -> str:
        """
        日本語文法エラーを自動修正する。

        Args:
            text: 修正対象テキスト

        Returns:
            修正後のテキスト
        """
        # H2: None/型チェック追加
        if not text:
            return ""
        # P1: 「はで、」→「は、」- H1: プリコンパイル済みパターン使用
        text = self._RE_FIX_HAWED.sub(r"\1は、", text)
        # P2: 「ていきた」→「ていった」- H1: プリコンパイル済みパターン使用
        text = self._RE_FIX_TEIKITA.sub(r"ていった\1", text)
        return text

    def _fix_text_quality(self, text: str) -> tuple[str, list[str]]:
        """
        文章品質の低下要因を自動修正する（安全な範囲のみ）。

        対象:
        - ルールA: 終止形の誤り（「にありた」「繋がりた」「になりた」「となりた」「○がりた」）
        - ルールB: 末尾句点欠落（「。」「！」「？」等で終わらない場合）
        - ルールC: 導入文パターンの「は、」→「は」（改行崩れの「は\\n、」も含む）

        Args:
            text: 修正対象テキスト

        Returns:
            (修正後テキスト, 変更内容リスト)
        """
        if not text:
            return text, []

        changes: list[str] = []
        updated = text

        # ルールA（終止形）- H1: プリコンパイル済みパターン使用
        updated, count = self._RE_NIARITA.subn(r"にいた\1", updated)
        if count:
            changes.append("A1: にありた→にいた")

        updated, count = self._RE_TSUNAGARITA.subn(r"繋がった\1", updated)
        if count:
            changes.append("A2: 繋がりた→繋がった")

        updated, count = self._RE_NINARITA.subn(r"になった\1", updated)
        if count:
            changes.append("A3: になりた→になった")

        updated, count = self._RE_TONARITA.subn(r"となった\1", updated)
        if count:
            changes.append("A4: となりた→となった")

        updated, count = self._RE_GARITA.subn(r"\1がった\2", updated)
        if count:
            changes.append("A5: ○がりた→○がった")

        # ルールC（導入文の「は、」読点削除）- H1: プリコンパイル済みパターン使用
        updated, count = self._RE_PATTERN_C.subn(r"\1\2\3\4", updated)
        if count:
            changes.append("C: 導入文の「は、」→「は」(改行崩れ含む)")

        # ルールD（「〜は」の直後重複）
        updated, count = self._RE_DUP_HA.subn(r"\1\2", updated)
        if count:
            changes.append("D: 「〜は」の重複削除")

        # ルールB（末尾句点）
        stripped = updated.rstrip()
        if stripped:
            # M1: 「」」を追加（引用符で終わる場合も有効な終端とする）
            valid_endings = ("。", "！", "？", "」", "!", "?")
            if not stripped.endswith(valid_endings):
                updated = stripped + "。"
                changes.append("B: 末尾句点追加")

        return updated, changes

    def _validate_row(self, row: dict) -> tuple[bool, str]:
        """行を検証"""
        required = ["person_id", "person_name", "age", "episode_text"]

        for field_name in required:
            if field_name not in row or not row[field_name]:
                return False, f"Missing required field: {field_name}"

        # 文字数チェック
        text = row.get("episode_text", "")
        if len(text) < 100:
            return False, f"Episode text too short: {len(text)}"

        # 日本語文法チェック（品質ゲート）
        grammar_errors = self._check_grammar_errors(text)
        if grammar_errors:
            # 自動修正を適用
            fixed_text = self._fix_grammar_errors(text)
            row["episode_text"] = fixed_text
            # M2: ログフォーマット統一（%フォーマット）
            logger.info(
                "SafeCSVWriter: 日本語文法エラー自動修正 - %s (%s歳): %s",
                row.get("person_name"),
                row.get("age"),
                grammar_errors,
            )

        # 文章品質の自動修正（誤字/句読点/導入文の読点崩れ）
        # なぜ: 文章の読みにくさを増やす「定型ミス」を書き込み前に除去し、再発を防ぐため。
        current_text = str(row.get("episode_text", "") or "")
        fixed_text, changes = self._fix_text_quality(current_text)
        if changes:
            row["episode_text"] = fixed_text
            logger.info(
                "SafeCSVWriter: 文章品質自動修正 - %s (%s歳): %s",
                row.get("person_name"),
                row.get("age"),
                changes,
            )

        # FICTIONAL文頭フォーマットチェック（EPUP必須ルール）
        is_valid, msg = check_fictional_lead_row(row)
        if not is_valid:
            return False, f"FICTIONAL文頭違反: {msg}"

        # FictionalQualityGate チェック（RCA-20260115, 強化: RCA-20260122）
        # 二重チェック: person_typeだけでなくperson_nameからも判定
        # これにより、person_type誤分類（REAL）でも架空キャラを検出可能
        person_type = str(row.get("person_type", "")).upper()
        person_name = row.get("person_name", "")

        is_fictional_by_type = "FICTIONAL" in person_type
        is_fictional_by_name = self._is_fictional_character(person_name)

        # 架空キャラクター名の正規化（書き込み前 - RCA-20260128）
        # 表記揺れを統一形式に変換（例: 「ナルト・うずまき」→「うずまきナルト」）
        if is_fictional_by_type or is_fictional_by_name:
            original_name = person_name
            normalized_name, was_changed = normalize_fictional_name(original_name)
            if was_changed:
                logger.info(
                    "SafeCSVWriter: [正規化] person_name: %s -> %s",
                    original_name,
                    normalized_name,
                )
                row["person_name"] = normalized_name
                person_name = normalized_name  # 後続処理用に更新

        if is_fictional_by_type or is_fictional_by_name:
            gate = FictionalQualityGate()

            # person_typeとperson_nameが矛盾する場合は自動修正（RCA-20260125強化）
            # 警告から自動修正に格上げ（バイパス経路完全封鎖）
            if is_fictional_by_name and not is_fictional_by_type:
                row["person_type"] = "FICTIONAL"
                logger.info(
                    "SafeCSVWriter: person_type自動修正 - %s: %s → FICTIONAL",
                    person_name,
                    person_type,
                )

            result = gate.check(row)
            if not result.passed:
                # 修正可能な違反は自動修正を適用
                if result.fixable and result.auto_fixed_text:
                    row["episode_text"] = result.auto_fixed_text
                    logger.info(f"SafeCSVWriter: FictionalQualityGate自動修正 - {person_name} ({row.get('age')}歳)")
                else:
                    # 修正不可の場合は棄却
                    violations = "; ".join([v.detail for v in result.violations])
                    return False, f"FictionalQualityGate違反: {violations}"

            # 真正性検証（canonのみ保存方針）- RCA-20260130
            from src.utils.authenticity_checker import AuthenticityChecker, AuthenticityStatus

            auth_checker = AuthenticityChecker()
            auth_result = auth_checker.check(row)

            if not auth_result.passed:
                if auth_result.status == AuthenticityStatus.NO_MATCH:
                    # 該当年齢に原作シーンなし → 棄却（生成しない）
                    logger.warning(f"AuthenticityGate: canon出典なし - {person_name} 年齢{row.get('age')}")
                    return False, f"canon出典なし: {auth_result.suggestion}"
                elif auth_result.status == AuthenticityStatus.INVALID:
                    # 設定違反 → 棄却
                    logger.warning(f"AuthenticityGate: 設定違反 - {auth_result.violations}")
                    return False, f"真正性違反: {'; '.join(auth_result.violations)}"
            else:
                # canon検証通過 → 出典情報をログに記録
                if auth_result.canon_source:
                    logger.info(f"AuthenticityGate: canon確認 - {auth_result.canon_source}")

        # REAL人物のハルシネーションチェック（RCA-20260203）
        # FICTIONAL は FictionalQualityGate でカバー済みなので、REAL のみ追加チェック
        if "REAL" in person_type and not is_fictional_by_name:
            real_verifier = RealPersonVerifier()
            episode_text = str(row.get("episode_text", ""))

            # 年齢・生年・没年取得
            try:
                age = float(row.get("age", 0))
            except (ValueError, TypeError):
                age = 0.0

            birth_year = row.get("birth_year")
            death_year = row.get("death_year")
            source = row.get("source")

            # 型変換
            try:
                birth_year = int(birth_year) if birth_year else None
            except (ValueError, TypeError):
                birth_year = None

            try:
                death_year = int(death_year) if death_year else None
            except (ValueError, TypeError):
                death_year = None

            # RealPersonVerifier で検証
            real_result = real_verifier.verify(
                person_name=person_name,
                episode_text=episode_text,
                age=age,
                birth_year=birth_year,
                death_year=death_year,
                source=source,
            )

            if not real_result.passed:
                # 埋草（filler）とfabricationはブロック
                violation_type = real_result.violation_type
                if violation_type:
                    logger.warning(
                        "HallucinationGate: REAL人物ハルシネーション検出 - %s (%s歳): %s",
                        person_name,
                        row.get("age"),
                        real_result.violation_detail,
                    )
                    return False, f"HallucinationGate違反: {real_result.violation_detail}"

        # UnifiedGateチェック（バイパス経路塞ぎ - DB反映前最終ゲート）
        # REAL/FICTIONAL両方をカバーする統合検証
        # WARNINGレベルの違反タイプ（通過を許可）
        WARNING_TYPES = {ViolationType.UNVERIFIED_CLAIM}

        unified_gate = UnifiedGate(strict_mode=False)
        unified_result = unified_gate.validate(row)
        if not unified_result.is_valid:
            # ERRORレベルのみブロック（WARNINGは通過）
            # violationsとmessagesをペアでフィルタリング
            error_items = [
                (v, m) for v, m in zip(unified_result.violations, unified_result.messages) if v not in WARNING_TYPES
            ]
            if error_items:
                error_msgs = [m for _, m in error_items]
                return False, f"UnifiedGate違反: {'; '.join(error_msgs)}"

        return True, ""

    def _check_duplicate(self, row: dict, existing_df: pd.DataFrame) -> tuple[bool, str]:
        """
        重複チェック（EPUP再発防止強化版）

        Args:
            row: 書き込み対象の行
            existing_df: 既存データ

        Returns:
            (is_duplicate: bool, reason: str)
        """
        if existing_df.empty:
            return False, ""

        person_id = row.get("person_id", "")
        age = row.get("age")

        if not person_id or age is None:
            return False, ""

        # 同一人物・同一年齢チェック（EPUP: 1人1年齢1エピソード原則）
        duplicates = existing_df[(existing_df["person_id"] == person_id) & (existing_df["age"] == age)]

        if not duplicates.empty:
            existing_ep = duplicates.iloc[0]
            reason = (
                f"EPUP違反: 同一人物×同一年齢のエピソード既存 - "
                f"person_id={person_id}, age={age}, "
                f"existing_ep={existing_ep.get('episode_id', 'unknown')}"
            )
            return True, reason

        return False, ""

    def dry_run(self, results: list[GenerationResult]) -> WriteResult:
        """
        dry-run実行（実際には書き込まない）

        Args:
            results: 生成結果リスト

        Returns:
            WriteResult: 実行結果
        """
        # 既存データ読み込み
        if self.master_csv.exists():
            existing_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
        else:
            existing_df = pd.DataFrame()

        added_count = 0
        skipped_count = 0
        diff_entries = []

        for result in results:
            if not result.success:
                skipped_count += 1
                continue

            row = self._result_to_row(result)

            # 検証
            valid, _error = self._validate_row(row)
            if not valid:
                skipped_count += 1
                continue

            # 重複チェック（EPUP: 1人1年齢1エピソード原則）
            is_dup, _dup_reason = self._check_duplicate(row, existing_df)
            if is_dup:
                skipped_count += 1
                continue

            added_count += 1
            diff_entries.append(
                DiffEntry(
                    episode_id=row["episode_id"],
                    person_name=row["person_name"],
                    age=row["age"],
                    action="add",
                    details={"category": row.get("category", "")},
                )
            )

        # 差分ログを保存
        diff_log_path = self._save_diff_log(diff_entries, dry_run=True)

        return WriteResult(
            success=True,
            added_count=added_count,
            skipped_count=skipped_count,
            diff_log_path=diff_log_path,
        )

    def write(self, results: list[GenerationResult]) -> WriteResult:
        """
        実際に書き込み

        Args:
            results: 生成結果リスト

        Returns:
            WriteResult: 実行結果
        """
        try:
            # 1. バックアップ作成
            backup_info = create_pre_operation_backup("hybrid_gen")
            backup_path = backup_info.path if backup_info else None

            # 2. 既存データ読み込み
            if self.master_csv.exists():
                existing_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            else:
                existing_df = pd.DataFrame()

            new_rows = []
            skipped_count = 0
            diff_entries = []

            for result in results:
                if not result.success:
                    skipped_count += 1
                    continue

                row = self._result_to_row(result)

                # 検証
                valid, _error = self._validate_row(row)
                if not valid:
                    skipped_count += 1
                    continue

                # RCA-20260110: 派生フィールド自動補完
                row = auto_fill_all_derived_fields(row)

                # RCA-20260110: 完全性チェック（欠損があれば書き込まない - 厳格モード）
                completeness_result = check_completeness_extended(row, auto_fill=False)
                if not completeness_result.passed:
                    # EPUP原則: 不完全レコードは書き込まない
                    # RCA-20260110: invalid_fieldsも表示（原因特定を容易に）
                    logger.warning(
                        f"EPUP violation - incomplete record skipped: "
                        f"{row.get('person_name')} ({row.get('age')}歳) - "
                        f"missing: {completeness_result.missing_fields}, "
                        f"invalid: {completeness_result.invalid_fields}"
                    )
                    skipped_count += 1
                    continue

                # 重複チェック
                is_dup, _dup_reason = self._check_duplicate(row, existing_df)
                if is_dup:
                    skipped_count += 1
                    continue

                new_rows.append(row)
                diff_entries.append(
                    DiffEntry(
                        episode_id=row["episode_id"],
                        person_name=row["person_name"],
                        age=row["age"],
                        action="add",
                        details={"category": row.get("category", "")},
                    )
                )

            if not new_rows:
                return WriteResult(
                    success=True,
                    added_count=0,
                    skipped_count=skipped_count,
                    backup_path=backup_path,
                )

            # 3. 新しい行を追加
            new_df = pd.DataFrame(new_rows)

            # カラム順序を整える
            for col in self.COLUMN_ORDER:
                if col not in new_df.columns:
                    new_df[col] = ""

            # 既存データと結合
            if not existing_df.empty:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df

            # 4. 書き込み
            combined_df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")

            # 🔸 Phase C-2: Supabase同期（新規追加）
            sync_success, sync_count = self._sync_to_supabase(new_rows)

            # 5. 差分ログを保存
            diff_log_path = self._save_diff_log(diff_entries, dry_run=False)

            return WriteResult(
                success=True,
                added_count=len(new_rows),
                skipped_count=skipped_count,
                backup_path=backup_path,
                diff_log_path=diff_log_path,
                supabase_synced=sync_success,
                supabase_sync_count=sync_count,
            )

        except (IOError, pd.errors.ParserError, PermissionError, pd.errors.EmptyDataError) as e:
            logger.error(f"CSV write operation failed: {e}", exc_info=True)
            return WriteResult(
                success=False,
                error_message=f"ファイル操作エラー: {str(e)}",
            )
        except Exception as e:
            logger.exception(f"Unexpected error during CSV write: {e}")
            raise

    def _get_supabase_client(self) -> SupabaseClient | None:
        """Supabaseクライアント取得"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url and not key:
            logger.debug("Supabase環境変数未設定（SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY）")
            return None
        if not url:
            logger.warning("SUPABASE_URL未設定（SUPABASE_SERVICE_ROLE_KEYは設定済み）")
            return None
        if not key:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY未設定（SUPABASE_URLは設定済み）")
            return None

        try:
            return create_client(url, key)
        except Exception as e:
            logger.error(f"Supabaseクライアント作成失敗: {e}")
            return None

    def _sanitize_for_supabase(self, row: dict) -> dict:
        """Supabase用にNaN/Inf/numpy型を変換（JSON互換形式）"""
        sanitized = {}
        for key, value in row.items():
            try:
                # None/pandas NA/NaT の明示的な処理
                if value is None or value is pd.NA:
                    sanitized[key] = None
                    continue
                try:
                    if pd.isna(value):
                        sanitized[key] = None
                        continue
                except (TypeError, ValueError):
                    pass

                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    sanitized[key] = None
                elif isinstance(value, (np.integer,)):
                    sanitized[key] = int(value)
                elif isinstance(value, (np.floating,)):
                    sanitized[key] = None if math.isnan(value) or math.isinf(value) else float(value)
                elif isinstance(value, (np.bool_,)):
                    sanitized[key] = bool(value)
                elif isinstance(value, (np.str_,)):
                    sanitized[key] = str(value)
                elif isinstance(value, np.ndarray):
                    logger.warning(f"_sanitize_for_supabase: 配列型は未サポート - key={key}")
                    sanitized[key] = None
                else:
                    sanitized[key] = value

                # INTEGER_COLUMNSの処理
                if key in INTEGER_COLUMNS and sanitized[key] is not None:
                    try:
                        sanitized[key] = int(float(sanitized[key]))
                    except (ValueError, TypeError) as e:
                        logger.debug(f"INTEGER_COLUMNS変換失敗: key={key}, value={sanitized[key]}, error={e}")
                        sanitized[key] = None
            except Exception as e:
                logger.warning(
                    f"_sanitize_for_supabase: 予期しないエラー - key={key}, value_type={type(value)}, error={e}"
                )
                sanitized[key] = None
        return sanitized

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, ConnectionError, TimeoutError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _upsert_batch(self, supabase: SupabaseClient, batch: list[dict]) -> int:
        """バッチupsert with リトライ"""
        result = supabase.table(SUPABASE_TABLE).upsert(batch, on_conflict="episode_id").execute()
        return len(result.data) if result.data else 0

    def _sync_to_supabase(self, new_rows: list[dict]) -> tuple[bool, int]:
        """新規行をSupabaseに同期（エラー時は警告のみ）

        Returns:
            tuple[bool, int]: (完全成功フラグ, 成功件数)
        """
        if not new_rows:
            return True, 0

        supabase = self._get_supabase_client()
        if not supabase:
            logger.warning("Supabase環境変数未設定 - 同期スキップ")
            return False, 0

        try:
            sanitized = [self._sanitize_for_supabase(row) for row in new_rows]
        except Exception as e:
            logger.error(f"Supabase同期: データ変換中に予期しないエラー: {e}", exc_info=True)
            return False, 0

        success_count = 0
        failed_batches = []

        for batch_idx, i in enumerate(range(0, len(sanitized), SUPABASE_BATCH_SIZE)):
            batch = sanitized[i : i + SUPABASE_BATCH_SIZE]
            try:
                success_count += self._upsert_batch(supabase, batch)
            except (APIError, ConnectionError, TimeoutError, httpx.HTTPStatusError) as e:
                logger.warning(f"Supabase同期: バッチ{batch_idx}失敗: {e}")
                failed_batches.append(batch_idx)
            except Exception as e:
                logger.error(f"Supabase同期: バッチ{batch_idx}で予期しないエラー: {e}", exc_info=True)
                failed_batches.append(batch_idx)

        if failed_batches:
            logger.warning(f"Supabase同期部分成功: {success_count}/{len(new_rows)}件, 失敗バッチ: {failed_batches}")
            return False, success_count

        logger.info(f"Supabase同期完了: {success_count}/{len(new_rows)}件")
        return True, success_count

    def replace_episode(
        self,
        old_episode_id: str,
        new_result: GenerationResult,
        dry_run: bool = True,
    ) -> WriteResult:
        """
        Phase 4: エピソードを置換

        Args:
            old_episode_id: 置換対象のエピソードID
            new_result: 新しい生成結果
            dry_run: True の場合は実際に書き込まない

        Returns:
            WriteResult: 実行結果
        """
        try:
            # 1. 既存データ読み込み
            if not self.master_csv.exists():
                return WriteResult(
                    success=False,
                    error_message="Master CSV not found",
                )

            existing_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")

            # 2. 置換対象を検索
            target_mask = existing_df["episode_id"] == old_episode_id
            if not target_mask.any():
                return WriteResult(
                    success=False,
                    error_message=f"Episode not found: {old_episode_id}",
                )

            old_row = existing_df[target_mask].iloc[0].to_dict()

            # 3. 新しい行を準備
            new_row = self._result_to_row(new_result)

            # 検証
            valid, error = self._validate_row(new_row)
            if not valid:
                return WriteResult(
                    success=False,
                    error_message=f"Validation failed: {error}",
                )

            # 差分エントリ
            # RCA-20260123: 年齢 "nan" 対応（int変換時のValueError防止）
            # RCA-20260123 Phase7: 異常値検出時の警告ログ追加
            age_value = old_row.get("age", 0)
            try:
                if age_value and str(age_value).lower() != "nan":
                    age_int = int(float(age_value))
                else:
                    logger.debug(f"年齢フィールド異常値（nan）: episode_id={old_episode_id}")
                    age_int = 0
            except (ValueError, TypeError) as e:
                logger.debug(f"年齢フィールド変換エラー: {age_value}, episode_id={old_episode_id}, error={e}")
                age_int = 0
            diff_entries = [
                DiffEntry(
                    episode_id=old_episode_id,
                    person_name=str(old_row.get("person_name", "")),
                    age=age_int,
                    action="replace",
                    details={
                        "old_episode_id": old_episode_id,
                        "new_episode_id": new_row["episode_id"],
                        "old_score": old_row.get("super_total_score", 0),
                        "new_score": new_row.get("super_total_score", 0),
                    },
                )
            ]

            if dry_run:
                diff_log_path = self._save_diff_log(diff_entries, dry_run=True)
                return WriteResult(
                    success=True,
                    replaced_count=1,
                    diff_log_path=diff_log_path,
                )

            # 4. バックアップ作成
            backup_info = create_pre_operation_backup("replace_episode")
            backup_path = backup_info.path if backup_info else None

            # 5. 置換実行（古いエピソードを削除して新しいエピソードを追加）
            existing_df = existing_df[~target_mask]
            new_df = pd.DataFrame([new_row])

            # カラム順序を整える
            for col in self.COLUMN_ORDER:
                if col not in new_df.columns:
                    new_df[col] = ""

            # 結合
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            # 6. 書き込み
            combined_df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")

            # 6.5. Supabase同期（新しいエピソードをupsert）
            sync_success, sync_count = self._sync_to_supabase([new_row])

            # 7. 差分ログを保存
            diff_log_path = self._save_diff_log(diff_entries, dry_run=False)

            # 8. 置換履歴を保存
            self._save_replacement_log(old_episode_id, new_row["episode_id"], old_row, new_row)

            return WriteResult(
                success=True,
                replaced_count=1,
                backup_path=backup_path,
                diff_log_path=diff_log_path,
                supabase_synced=sync_success,
                supabase_sync_count=sync_count,
            )

        except (IOError, pd.errors.ParserError, PermissionError, pd.errors.EmptyDataError) as e:
            logger.error(f"CSV replace operation failed: {e}", exc_info=True)
            return WriteResult(
                success=False,
                error_message=f"ファイル操作エラー: {str(e)}",
            )
        except Exception as e:
            logger.exception(f"Unexpected error during CSV replace: {e}")
            raise

    def _save_replacement_log(
        self,
        old_episode_id: str,
        new_episode_id: str,
        old_row: dict,
        new_row: dict,
    ) -> None:
        """置換履歴を保存（H3: エラーハンドリング強化）"""
        log_path = self.logs_dir / "replacement_log.json"

        try:
            # 既存ログを読み込み
            if log_path.exists():
                try:
                    with open(log_path, encoding="utf-8") as f:
                        log_data = json.load(f)
                except json.JSONDecodeError as e:
                    # H3: 破損したログファイルのハンドリング
                    logger.error(f"Corrupted replacement log, creating new: {e}")
                    backup_path = log_path.with_suffix(".json.corrupted")
                    log_path.rename(backup_path)
                    log_data = {"replacements": []}
            else:
                log_data = {"replacements": []}

            # 新しいエントリを追加
            log_data["replacements"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "old_episode_id": old_episode_id,
                    "new_episode_id": new_episode_id,
                    "person_name": old_row.get("person_name", ""),
                    "age": old_row.get("age", 0),
                    "old_score": old_row.get("super_total_score", 0),
                    "new_score": new_row.get("super_total_score", 0),
                    "score_improvement": (new_row.get("super_total_score", 0) - old_row.get("super_total_score", 0)),
                }
            )

            # 保存
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        except (IOError, OSError, PermissionError) as e:
            # H3: ファイル操作エラーは警告のみ（メイン処理を中断しない）
            logger.warning(f"Failed to save replacement log: {e}")

    def _save_diff_log(self, entries: list[DiffEntry], dry_run: bool = False) -> Optional[Path]:
        """差分ログを保存"""
        if not entries:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "dryrun" if dry_run else "applied"
        log_path = self.logs_dir / f"diff_{prefix}_{timestamp}.json"

        log_data = {
            "timestamp": timestamp,
            "dry_run": dry_run,
            "entries": [
                {
                    "episode_id": e.episode_id,
                    "person_name": e.person_name,
                    "age": e.age,
                    "action": e.action,
                    "details": e.details,
                }
                for e in entries
            ],
        }

        # RCA-20260123: IOError等でクラッシュしないよう警告のみに
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        except (IOError, OSError, PermissionError) as e:
            logger.warning(f"Failed to save diff log: {e}")
            return None

        return log_path


def safe_append_episodes(results: list[GenerationResult], dry_run: bool = True) -> WriteResult:
    """
    エピソードを安全に追記

    Args:
        results: 生成結果リスト
        dry_run: True の場合は実際に書き込まない

    Returns:
        WriteResult: 実行結果
    """
    writer = SafeCSVWriter()

    if dry_run:
        return writer.dry_run(results)
    else:
        return writer.write(results)
