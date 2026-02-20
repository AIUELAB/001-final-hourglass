"""
Hybrid Generation Orchestrator

ハイブリッドエピソード生成のメインオーケストレータ。
全コンポーネントを統合し、エンドツーエンドの生成パイプラインを提供。
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from src.utils.fictional_characters import is_fictional_character as _is_fictional_by_name

from .adapters import Candidate, GenerationResult
from .config import (
    MASTER_CSV,
    QUALITY_THRESHOLDS,
    HybridConfig,
    RejectionReason,
    Strategy,
)
from .gates import (
    AntiGamingMonitor,
    CandidatePrioritizer,
    DiversityManager,
    DuplicateDetector,
    FactChecker,
)
from .gates.post_processor import apply_post_processing
from .persistence import SafeCSVWriter, WriteResult
from .inventory_manager import InventoryManager, ReplacementTarget
from .gates.taigendome import check_taigendome
from .pre_generation_rules import PreGenerationRules, check_prohibited_patterns, check_specificity
from .quality import ImprovementLoop, QualityEvaluator, SuperTotalCalculator
from .strategy_router import StrategyRouter

# FictionalQualityGate（架空キャラクター品質ゲート）
from src.utils.fictional_quality_gate import FictionalQualityGate, QualityViolationError

# ロガー設定
logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """候補処理結果 (Phase 4)"""

    result: Optional[GenerationResult] = None
    rejection: Optional[dict] = None
    is_replacement: bool = False
    replacement_target: Optional[ReplacementTarget] = None


@dataclass
class GenerationRun:
    """生成実行結果"""

    run_id: str
    started_at: str
    completed_at: str = ""
    strategy: str = ""
    target_count: int = 0
    generated_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    replaced_count: int = 0  # Phase 4: 置換数
    dry_run: bool = True
    results: list[GenerationResult] = field(default_factory=list)
    rejections: list[dict] = field(default_factory=list)
    replacements: list[dict] = field(default_factory=list)  # Phase 4: 置換履歴
    write_result: Optional[WriteResult] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "strategy": self.strategy,
            "target_count": self.target_count,
            "generated_count": self.generated_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "replaced_count": self.replaced_count,
            "dry_run": self.dry_run,
            "acceptance_rate": (self.accepted_count / self.generated_count if self.generated_count > 0 else 0.0),
        }


class HybridOrchestrator:
    """
    ハイブリッド生成オーケストレータ

    候補選定→生成前チェック→生成→品質検証→永続化のパイプラインを統合実行。
    詳細なステップは _process_candidate() メソッドを参照。
    """

    def __init__(self, config: Optional[HybridConfig] = None):
        self.config = config or HybridConfig()

        # コンポーネント初期化
        self._pre_rules = PreGenerationRules(
            master_csv=self.config.master_csv,
            rules=self.config.generation_rules,
            thresholds=self.config.quality_thresholds,
        )
        # Phase 9-10: 評価モデル・プロンプト設定を適用
        use_haiku = "haiku" in self.config.evaluation_model.lower()
        self._router = StrategyRouter(
            strategy=self.config.strategy,
            use_mock=self.config.use_mock,
            use_haiku_evaluation=use_haiku,
            use_compact_prompt=self.config.use_compact_prompt,
        )
        self._evaluator = QualityEvaluator(self.config.quality_thresholds)
        self._super_total = SuperTotalCalculator(self.config.quality_thresholds)
        self._fact_checker = FactChecker()
        self._duplicate_detector = DuplicateDetector(
            master_csv=self.config.master_csv,
            thresholds=self.config.quality_thresholds,
        )
        self._diversity_manager = DiversityManager(
            master_csv=self.config.master_csv,
            targets=self.config.diversity_targets,
            rules=self.config.generation_rules,
        )
        self._writer = SafeCSVWriter(
            master_csv=self.config.master_csv,
            logs_dir=self.config.logs_dir,
        )

        # Phase 1: 年齢別在庫管理（365本停止機能）
        self._inventory_manager = InventoryManager(
            master_csv=self.config.master_csv,
            cache_dir=self.config.cache_dir,
        )

        # Phase 17: PreGenerationRulesにInventoryManagerを注入（置換モード対応）
        self._pre_rules._inventory_manager = self._inventory_manager  # type: ignore[attr-defined]

        # Phase 3: アンチゲーミングモニター
        self._anti_gaming = AntiGamingMonitor()

        # 架空キャラクター品質ゲート（RCA-20260115）
        self._fictional_quality_gate = FictionalQualityGate()

        # マスターデータ
        self._master_df: Optional[pd.DataFrame] = None

        # Phase 29: deficit優先年齢のキャッシュ（パフォーマンス最適化）
        self._cached_deficit_ages: Optional[list[int]] = None

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.config.master_csv.exists():
                self._master_df = pd.read_csv(self.config.master_csv, encoding="utf-8-sig")
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def reload_master(self) -> None:
        """マスターデータを再読み込み"""
        self._master_df = None
        self._duplicate_detector.reload_master()

    def run(
        self,
        candidates: list[Candidate],
        dry_run: bool = True,
    ) -> GenerationRun:
        """
        生成を実行

        Args:
            candidates: 生成候補リスト
            dry_run: True の場合は実際に書き込まない

        Returns:
            GenerationRun: 実行結果
        """
        # Phase 18: 統計をリセット（累積問題を修正）
        self._router.reset_stats()

        # Phase 18: バッチ評価モードを使用
        if self.config.use_batch_evaluation:
            return self._run_batch_mode(candidates, dry_run)

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = GenerationRun(
            run_id=run_id,
            started_at=datetime.now().isoformat(),
            strategy=self.config.strategy.value,
            target_count=len(candidates),
            dry_run=dry_run,
        )

        accepted_results = []
        rejections = []
        replacements = []

        for candidate in candidates:
            try:
                proc_result = self._process_candidate(candidate)

                if proc_result.result and proc_result.result.success:
                    run.generated_count += 1

                    # Phase 4: 置換モード処理
                    if proc_result.is_replacement and proc_result.replacement_target:
                        # 置換実行
                        replace_result = self._writer.replace_episode(
                            old_episode_id=proc_result.replacement_target.episode_id,
                            new_result=proc_result.result,
                            dry_run=dry_run,
                        )
                        if replace_result.success:
                            run.replaced_count += 1
                            replacements.append(
                                {
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "old_episode_id": proc_result.replacement_target.episode_id,
                                    "old_score": proc_result.replacement_target.score,
                                    "new_score": proc_result.result.evaluation.super_total_score
                                    if proc_result.result.evaluation
                                    else 0,
                                }
                            )
                        else:
                            # 置換失敗
                            run.rejected_count += 1
                            rejections.append(
                                {
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": "replacement_failed",
                                    "message": replace_result.error_message,
                                }
                            )
                    else:
                        # 通常の追加
                        accepted_results.append(proc_result.result)
                        run.accepted_count += 1
                else:
                    run.generated_count += 1
                    run.rejected_count += 1
                    if proc_result.rejection:
                        rejections.append(proc_result.rejection)

            except Exception as e:
                logger.error(f"Error processing {candidate.person_name}: {e}")
                run.rejected_count += 1
                rejections.append(
                    {
                        "person_id": candidate.person_id,
                        "person_name": candidate.person_name,
                        "age": candidate.age,
                        "reason": RejectionReason.GENERATION_ERROR.value,
                        "message": str(e),
                    }
                )

        # 永続化（新規追加分のみ）
        if accepted_results:
            if dry_run:
                run.write_result = self._writer.dry_run(accepted_results)
            else:
                run.write_result = self._writer.write(accepted_results)

        run.results = accepted_results
        run.rejections = rejections
        run.replacements = replacements
        run.completed_at = datetime.now().isoformat()

        # ログ保存
        self._save_run_log(run)

        return run

    def _run_batch_mode(
        self,
        candidates: list[Candidate],
        dry_run: bool = True,
    ) -> GenerationRun:
        """
        バッチ評価モードで生成を実行

        Phase 18: 生成と評価を分離してLLM呼び出しを削減。
        1. N件を生成（評価なし）
        2. N件を一括評価
        3. 品質ゲート処理

        Args:
            candidates: 生成候補リスト
            dry_run: True の場合は実際に書き込まない

        Returns:
            GenerationRun: 実行結果
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = GenerationRun(
            run_id=run_id,
            started_at=datetime.now().isoformat(),
            strategy=self.config.strategy.value,
            target_count=len(candidates),
            dry_run=dry_run,
        )

        accepted_results = []
        rejections = []
        replacements = []

        batch_size = self.config.batch_evaluation_size

        # バッチ単位で処理
        for batch_start in range(0, len(candidates), batch_size):
            batch_candidates = candidates[batch_start : batch_start + batch_size]
            batch_results = []
            batch_metadata = []  # 各結果に紐づくメタデータ

            # Phase 1: 生成（評価なし）
            for candidate in batch_candidates:  # type: ignore[union-attr]
                try:
                    # 生成前チェック
                    pre_check = self._pre_rules.check_all(candidate)
                    if not pre_check.passed:
                        run.generated_count += 1
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": pre_check.reason.value if pre_check.reason else "pre_check",
                                "message": pre_check.message,
                            }
                        )
                        continue

                    # 多様性クォータチェック
                    quota_passed, quota_reason = self._diversity_manager.check_person_quota(candidate.person_id)
                    if not quota_passed:
                        run.generated_count += 1
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": RejectionReason.WEEKLY_LIMIT_EXCEEDED.value,
                                "message": quota_reason,
                            }
                        )
                        continue

                    # 置換候補情報取得
                    details = pre_check.details or {}
                    is_replacement_candidate = details.get("is_replacement_candidate", False)
                    existing_episode_id = details.get("existing_episode_id")
                    existing_score = details.get("existing_score", 0.0)

                    # 重複チェック（非置換モード時）
                    if not is_replacement_candidate:
                        pre_dup_check = self._duplicate_detector.check_exact_duplicate(
                            candidate.person_id, candidate.age
                        )
                        if pre_dup_check.is_duplicate:
                            run.generated_count += 1
                            run.rejected_count += 1
                            rejections.append(
                                {
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": RejectionReason.SAME_AGE_DUPLICATE.value,
                                    "message": f"同一年齢エピソード既存: {pre_dup_check.most_similar_episode_id}",
                                }
                            )
                            continue

                    # 生成（評価なし）
                    result = self._router.route_without_eval(candidate)

                    if result.success:
                        # 定型パターン修正
                        result.episode_text, _ = apply_post_processing(
                            result.episode_text,
                            candidate.person_name,
                            candidate.age if candidate.age is not None else 0,
                            strict_mode=False,
                        )

                        batch_results.append(result)
                        batch_metadata.append(
                            {
                                "candidate": candidate,
                                "is_replacement_candidate": is_replacement_candidate,
                                "existing_episode_id": existing_episode_id,
                                "existing_score": existing_score,
                            }
                        )
                        run.generated_count += 1
                    else:
                        run.generated_count += 1
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": RejectionReason.GENERATION_ERROR.value,
                                "message": result.error_message,
                            }
                        )

                except Exception as e:
                    logger.error(f"Error generating {candidate.person_name}: {e}")
                    run.rejected_count += 1
                    rejections.append(
                        {
                            "person_id": candidate.person_id,
                            "person_name": candidate.person_name,
                            "age": candidate.age,
                            "reason": RejectionReason.GENERATION_ERROR.value,
                            "message": str(e),
                        }
                    )

            # Phase 2: バッチ評価
            if batch_results:
                batch_results = self._router.batch_evaluate(batch_results, batch_size=self.config.evaluation_batch_size)

            # Phase 3: 品質ゲートと後処理
            for i, result in enumerate(batch_results):
                if i >= len(batch_metadata):
                    continue

                meta = batch_metadata[i]
                candidate = meta["candidate"]

                try:
                    # 禁止パターンチェック
                    pattern_check = check_prohibited_patterns(result.episode_text)
                    if not pattern_check.passed:
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": pattern_check.reason.value if pattern_check.reason else "prohibited",
                                "message": pattern_check.message,
                            }
                        )
                        continue

                    # 体言止めチェック
                    taigendome_check = check_taigendome(result.episode_text)
                    if not taigendome_check.passed:
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": RejectionReason.TAIGENDOME_VIOLATION.value,
                                "message": taigendome_check.message,
                            }
                        )
                        continue

                    # 具体性チェック
                    specificity_check = check_specificity(result.episode_text)
                    if not specificity_check.passed:
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": specificity_check.reason.value if specificity_check.reason else "filler",
                                "message": specificity_check.message,
                            }
                        )
                        continue

                    # ファクトチェック
                    fact_result = self._fact_checker.check(result.episode_text, candidate.person_name)
                    if not fact_result.passed:
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": fact_result.rejection_reason.value
                                if fact_result.rejection_reason
                                else "fact_check",
                                "message": fact_result.reason,
                            }
                        )
                        continue

                    # 架空キャラクター品質ゲート（RCA-20260115, RCA-20260122）
                    if (
                        candidate.person_type and "FICTIONAL" in str(candidate.person_type).upper()
                    ) or _is_fictional_by_name(candidate.person_name):
                        fictional_episode = {
                            "episode_text": result.episode_text,
                            "work_title": getattr(candidate, "work_title", ""),
                            "person_type": candidate.person_type,
                            "person_name": candidate.person_name,
                        }
                        fictional_result = self._fictional_quality_gate.check(fictional_episode)
                        if not fictional_result.passed:
                            if fictional_result.fixable and fictional_result.auto_fixed_text:
                                # 自動修正を適用
                                result.episode_text = fictional_result.auto_fixed_text
                                logger.info(
                                    f"FictionalQualityGate(batch): 自動修正適用 - {candidate.person_name}({candidate.age}歳)"
                                )
                            else:
                                # 修正不可の場合は棄却
                                violation_details = "; ".join([v.detail for v in fictional_result.violations])
                                run.rejected_count += 1
                                rejections.append(
                                    {
                                        "person_id": candidate.person_id,
                                        "person_name": candidate.person_name,
                                        "age": candidate.age,
                                        "reason": "fictional_quality_gate",
                                        "message": f"架空キャラクター品質違反: {violation_details}",
                                    }
                                )
                                continue

                    # 重複チェック
                    dup_result = self._duplicate_detector.check_all(
                        result.episode_text, candidate.person_id, candidate.age
                    )
                    if dup_result.is_duplicate:
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": candidate.person_id,
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "reason": dup_result.rejection_reason.value
                                if dup_result.rejection_reason
                                else "duplicate",
                                "message": dup_result.reason,
                            }
                        )
                        continue

                    # 品質ゲートチェック
                    if result.evaluation:
                        gate_result = self._evaluator.check_quality_gates(
                            result.evaluation.axis_scores,
                            category=candidate.category,
                            use_category=self.config.use_category_thresholds,
                        )
                        if not gate_result.passed:
                            run.rejected_count += 1
                            rejections.append(
                                {
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": gate_result.reason.value if gate_result.reason else "quality_gate",
                                    "message": ", ".join(gate_result.failures),
                                }
                            )
                            continue

                        # 超総合スコア計算
                        super_result = self._super_total.calculate(
                            candidate.person_id,
                            result.evaluation.axis_scores,
                            self.master_df,
                        )
                        result.evaluation.super_total_score = super_result.score

                        if not super_result.passed_gate:
                            run.rejected_count += 1
                            rejections.append(
                                {
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": RejectionReason.LOW_SUPER_TOTAL.value,
                                    "message": ", ".join(super_result.gate_failures),
                                }
                            )
                            continue

                    # 生成履歴記録
                    self._pre_rules.record_generation(candidate.person_id, success=True)
                    self._diversity_manager.record_generation(candidate.person_id)

                    # 置換モード処理
                    is_replacement = False
                    replacement_target = None

                    if meta["is_replacement_candidate"] and result.evaluation:
                        new_score = result.evaluation.super_total_score or 0
                        improvement_threshold = meta["existing_score"] * 1.05
                        if new_score >= improvement_threshold:
                            is_replacement = True
                            from .inventory_manager import ReplacementTarget

                            replacement_target = ReplacementTarget(
                                episode_id=meta["existing_episode_id"],
                                person_id=candidate.person_id,
                                person_name=candidate.person_name,
                                age=candidate.age,
                                score=meta["existing_score"],
                            )
                        else:
                            run.rejected_count += 1
                            rejections.append(
                                {
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": "insufficient_improvement",
                                    "message": f"スコア改善不足: {new_score:.0f} < {improvement_threshold:.0f}",
                                }
                            )
                            continue

                    # 結果処理
                    if is_replacement and replacement_target:
                        replace_result = self._writer.replace_episode(
                            old_episode_id=replacement_target.episode_id,
                            new_result=result,
                            dry_run=dry_run,
                        )
                        if replace_result.success:
                            run.replaced_count += 1
                            replacements.append(
                                {
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "old_episode_id": replacement_target.episode_id,
                                    "old_score": replacement_target.score,
                                    "new_score": result.evaluation.super_total_score if result.evaluation else 0,
                                }
                            )
                        else:
                            run.rejected_count += 1
                            rejections.append(
                                {
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": "replacement_failed",
                                    "message": replace_result.error_message,
                                }
                            )
                    else:
                        accepted_results.append(result)
                        run.accepted_count += 1

                except Exception as e:
                    logger.error(f"Error processing {candidate.person_name}: {e}")
                    run.rejected_count += 1
                    rejections.append(
                        {
                            "person_id": candidate.person_id,
                            "person_name": candidate.person_name,
                            "age": candidate.age,
                            "reason": RejectionReason.GENERATION_ERROR.value,
                            "message": str(e),
                        }
                    )

        # 永続化
        if accepted_results:
            if dry_run:
                run.write_result = self._writer.dry_run(accepted_results)
            else:
                run.write_result = self._writer.write(accepted_results)

        run.results = accepted_results
        run.rejections = rejections
        run.replacements = replacements
        run.completed_at = datetime.now().isoformat()

        self._save_run_log(run)

        return run

    def _process_candidate(self, candidate: Candidate) -> ProcessingResult:
        """
        単一候補を処理

        Args:
            candidate: 生成候補

        Returns:
            ProcessingResult: 処理結果（生成結果、棄却情報、置換情報を含む）
        """
        # 1. 生成前ルールチェック
        pre_check = self._pre_rules.check_all(candidate)
        if not pre_check.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": pre_check.reason.value if pre_check.reason else "pre_check",
                    "message": pre_check.message,
                }
            )

        # 2. 多様性クォータチェック
        quota_passed, quota_reason = self._diversity_manager.check_person_quota(candidate.person_id)
        if not quota_passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": RejectionReason.WEEKLY_LIMIT_EXCEEDED.value,
                    "message": quota_reason,
                }
            )

        # 2.5. 同一人物×同一年齢の重複チェック（Phase 17: 置換モード対応）
        # Phase 17: pre_checkの結果から置換候補情報を取得
        details = pre_check.details or {}
        is_replacement_candidate = details.get("is_replacement_candidate", False)
        existing_episode_id = details.get("existing_episode_id")
        existing_score = details.get("existing_score", 0.0)

        if not is_replacement_candidate:
            # 通常モード: 既に同じ人物・同じ年齢のエピソードが存在する場合は生成をスキップ
            pre_dup_check = self._duplicate_detector.check_exact_duplicate(candidate.person_id, candidate.age)
            if pre_dup_check.is_duplicate:
                logger.info(
                    f"EPUP: 同一年齢重複スキップ - {candidate.person_name}({candidate.age}歳) "
                    f"既存EP: {pre_dup_check.most_similar_episode_id}"
                )
                return ProcessingResult(
                    rejection={
                        "person_id": candidate.person_id,
                        "person_name": candidate.person_name,
                        "age": candidate.age,
                        "reason": RejectionReason.SAME_AGE_DUPLICATE.value,
                        "message": f"同一年齢エピソード既存: {pre_dup_check.most_similar_episode_id}",
                    }
                )
        else:
            # Phase 17: 置換モード - 生成を許可、後でスコア比較
            logger.info(
                f"Phase 17: 置換候補として生成続行 - {candidate.person_name}({candidate.age}歳) "
                f"既存EP: {existing_episode_id}, 既存スコア: {existing_score:.0f}"
            )

        # 3. 生成
        result = self._router.route(candidate)

        if not result.success:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": RejectionReason.GENERATION_ERROR.value,
                    "message": result.error_message,
                }
            )

        # 3.6. 定型パターン後処理（EPUP準拠）
        # "あなたと同じ{age}歳のとき、{name}は" で開始するよう修正
        original_text = result.episode_text
        result.episode_text, post_changes = apply_post_processing(
            result.episode_text,
            candidate.person_name,
            candidate.age,
            strict_mode=False,  # 修正できない場合も継続
        )
        if post_changes:
            logger.info(f"定型パターン修正: {candidate.person_name}({candidate.age}歳) - {', '.join(post_changes)}")

        # 4. 禁止パターンチェック
        pattern_check = check_prohibited_patterns(result.episode_text)
        if not pattern_check.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": pattern_check.reason.value if pattern_check.reason else "prohibited",
                    "message": pattern_check.message,
                }
            )

        # 4.5. 体言止めチェック（EPUP: 文末完結性）
        taigendome_check = check_taigendome(result.episode_text)
        if not taigendome_check.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": RejectionReason.TAIGENDOME_VIOLATION.value,
                    "message": taigendome_check.message,
                }
            )

        # 5. 具体性チェック
        specificity_check = check_specificity(result.episode_text)
        if not specificity_check.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": specificity_check.reason.value if specificity_check.reason else "filler",
                    "message": specificity_check.message,
                }
            )

        # 5.5. Phase 3: アンチゲーミングチェック（キーワード詰め込み、抽象語過多、テンプレート臭）
        # Phase 17: use_anti_gaming=Falseで無効化（0%ブロック率のため処理時間短縮）
        if self.config.generation_rules.get("use_anti_gaming", True):
            gaming_result = self._anti_gaming.check(result.episode_text, candidate.person_name)
            # missing_specifics は step 5 でカバー済みなので除外
            gaming_violations = [v for v in gaming_result.violations if v != "missing_specifics"]
            if gaming_violations:
                return ProcessingResult(
                    rejection={
                        "person_id": candidate.person_id,
                        "person_name": candidate.person_name,
                        "age": candidate.age,
                        "reason": gaming_result.rejection_reason.value
                        if gaming_result.rejection_reason
                        else "anti_gaming",
                        "message": f"Anti-gaming violations: {', '.join(gaming_violations)}",
                    }
                )

        # 6. ファクトチェック
        fact_result = self._fact_checker.check(result.episode_text, candidate.person_name)
        if not fact_result.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": fact_result.rejection_reason.value if fact_result.rejection_reason else "fact_check",
                    "message": fact_result.reason,
                }
            )

        # 6.5. 架空キャラクター品質ゲート（RCA-20260115, RCA-20260122）
        # FICTIONALの場合、またはperson_nameが架空キャラの場合に追加チェック
        if (candidate.person_type and "FICTIONAL" in str(candidate.person_type).upper()) or _is_fictional_by_name(
            candidate.person_name
        ):
            fictional_episode = {
                "episode_text": result.episode_text,
                "work_title": getattr(candidate, "work_title", ""),
                "person_type": candidate.person_type,
                "person_name": candidate.person_name,
            }
            fictional_result = self._fictional_quality_gate.check(fictional_episode)
            if not fictional_result.passed:
                if fictional_result.fixable and fictional_result.auto_fixed_text:
                    # 自動修正を適用
                    result.episode_text = fictional_result.auto_fixed_text
                    logger.info(f"FictionalQualityGate: 自動修正適用 - {candidate.person_name}({candidate.age}歳)")
                else:
                    # 修正不可の場合は棄却
                    violation_details = "; ".join([v.detail for v in fictional_result.violations])
                    return ProcessingResult(
                        rejection={
                            "person_id": candidate.person_id,
                            "person_name": candidate.person_name,
                            "age": candidate.age,
                            "reason": "fictional_quality_gate",
                            "message": f"架空キャラクター品質違反: {violation_details}",
                        }
                    )

        # 7. 重複チェック
        dup_result = self._duplicate_detector.check_all(result.episode_text, candidate.person_id, candidate.age)
        if dup_result.is_duplicate:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "age": candidate.age,
                    "reason": dup_result.rejection_reason.value if dup_result.rejection_reason else "duplicate",
                    "message": dup_result.reason,
                }
            )

        # 8. 品質ゲートチェック（Phase 13: カテゴリ別閾値対応）
        # Phase 3最適化: LOW_GENERATION_QUALITYの場合1回リトライ
        retry_count = 0
        max_retry = 1

        while True:
            if result.evaluation:
                gate_result = self._evaluator.check_quality_gates(
                    result.evaluation.axis_scores,
                    category=candidate.category,
                    use_category=self.config.use_category_thresholds,
                )
                if not gate_result.passed:
                    # Phase 3: LOW_GENERATION_QUALITYの場合のみリトライ可能
                    is_retryable = (
                        gate_result.reason == RejectionReason.LOW_GENERATION_QUALITY and retry_count < max_retry
                    )

                    if is_retryable:
                        retry_count += 1
                        logger.info(
                            f"品質ゲート失敗、リトライ({retry_count}/{max_retry}): "
                            f"{candidate.person_name}({candidate.age}歳) - {', '.join(gate_result.failures)}"
                        )

                        # 再生成
                        result = self._router.route(candidate)
                        if not result.success:
                            return ProcessingResult(
                                rejection={
                                    "person_id": candidate.person_id,
                                    "person_name": candidate.person_name,
                                    "age": candidate.age,
                                    "reason": RejectionReason.GENERATION_ERROR.value,
                                    "message": f"リトライ失敗: {result.error_message}",
                                }
                            )

                        # 定型パターン修正を再適用
                        result.episode_text, _ = apply_post_processing(
                            result.episode_text,
                            candidate.person_name,
                            candidate.age if candidate.age is not None else 0,
                            strict_mode=False,
                        )

                        # ループ継続（再評価へ）
                        continue

                    # リトライ不可または回数上限到達
                    return ProcessingResult(
                        rejection={
                            "person_id": candidate.person_id,
                            "person_name": candidate.person_name,
                            "age": candidate.age,
                            "reason": gate_result.reason.value if gate_result.reason else "quality_gate",
                            "message": ", ".join(gate_result.failures)
                            + (f" (リトライ{retry_count}回後)" if retry_count > 0 else ""),
                        }
                    )

            # 品質ゲート通過
            break

        # 9. 超総合スコア計算
        if result.evaluation:
            super_result = self._super_total.calculate(
                candidate.person_id,
                result.evaluation.axis_scores,
                self.master_df,
            )
            result.evaluation.super_total_score = super_result.score

            if not super_result.passed_gate:
                return ProcessingResult(
                    rejection={
                        "person_id": candidate.person_id,
                        "person_name": candidate.person_name,
                        "age": candidate.age,
                        "reason": RejectionReason.LOW_SUPER_TOTAL.value,
                        "message": ", ".join(super_result.gate_failures),
                    }
                )

        # 10. 生成履歴を記録
        self._pre_rules.record_generation(candidate.person_id, success=True)
        self._diversity_manager.record_generation(candidate.person_id)

        # 11. Phase 4 + Phase 17: 置換モード判定
        is_replacement = False
        replacement_target = None

        # Phase 17: same_age_duplicate置換モード（Step 2.5で検出された置換候補）
        if is_replacement_candidate and result.evaluation:
            new_score = result.evaluation.super_total_score or 0
            # 5%以上の改善が必要
            improvement_threshold = existing_score * 1.05
            if new_score >= improvement_threshold:
                is_replacement = True
                # ReplacementTargetを構築
                from .inventory_manager import ReplacementTarget

                replacement_target = ReplacementTarget(
                    episode_id=str(existing_episode_id) if existing_episode_id else "",
                    person_id=candidate.person_id,
                    person_name=candidate.person_name,
                    age=candidate.age,
                    score=existing_score,
                )
                logger.info(
                    f"Phase 17: same_age置換決定 - {candidate.person_name}({candidate.age}歳) "
                    f"新スコア={new_score:.0f} > 既存スコア={existing_score:.0f} (+{(new_score / existing_score - 1) * 100:.1f}%)"
                )
            else:
                # 置換閾値未達 - 改善不十分なので棄却
                return ProcessingResult(
                    rejection={
                        "person_id": candidate.person_id,
                        "person_name": candidate.person_name,
                        "age": candidate.age,
                        "reason": "insufficient_improvement",
                        "message": f"スコア改善不足: {new_score:.0f} < {improvement_threshold:.0f} (既存{existing_score:.0f}の5%改善必要)",
                    }
                )
        elif self._inventory_manager.is_replacement_mode(candidate.age):
            # Phase 4: 年齢ベースの置換モード（従来ロジック）
            replacement_target = self._inventory_manager.get_replacement_target(candidate.age)
            if replacement_target and result.evaluation:
                new_score = result.evaluation.super_total_score or 0
                # 5%以上の改善が必要
                if self._inventory_manager.should_replace(candidate.age, new_score):
                    is_replacement = True
                    logger.info(
                        f"Replacement candidate: {candidate.person_name} age={candidate.age} "
                        f"new_score={new_score:.0f} > old_score={replacement_target.score:.0f}"
                    )
                else:
                    # 置換閾値未達
                    return ProcessingResult(
                        rejection={
                            "person_id": candidate.person_id,
                            "person_name": candidate.person_name,
                            "age": candidate.age,
                            "reason": "replacement_threshold_not_met",
                            "message": f"Score {new_score:.0f} does not exceed threshold for age {candidate.age}",
                        }
                    )

        return ProcessingResult(
            result=result,
            is_replacement=is_replacement,
            replacement_target=replacement_target,
        )

    def _save_run_log(self, run: GenerationRun) -> None:
        """実行ログを保存"""
        log_path = self.config.logs_dir / f"run_{run.run_id}.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # アダプター統計を収集してrouter_statsを更新
        adapter_stats = self._router.collect_adapter_stats()

        log_data = run.to_dict()
        log_data["rejections"] = run.rejections
        log_data["replacements"] = run.replacements  # Phase 4: 置換履歴
        log_data["router_stats"] = self._router.stats.to_dict()
        # Phase 1: コスト計測をログに追加
        log_data["cost_metrics"] = {
            "total_input_tokens": self._router.stats.total_input_tokens,
            "total_output_tokens": self._router.stats.total_output_tokens,
            "total_tokens": self._router.stats.total_input_tokens + self._router.stats.total_output_tokens,
            "total_llm_calls": self._router.stats.total_llm_calls,
            "estimated_cost_usd": round(self._router.stats.estimated_cost_usd, 4),
            "avg_tokens_per_episode": (
                round(
                    (self._router.stats.total_input_tokens + self._router.stats.total_output_tokens)
                    / run.generated_count,  # type: ignore[operator]
                    1,
                )
                if run.generated_count > 0
                else 0
            ),
            "avg_cost_per_episode_usd": (
                round(self._router.stats.estimated_cost_usd / run.generated_count, 6) if run.generated_count > 0 else 0
            ),
        }
        log_data["adapter_stats"] = adapter_stats

        # Phase 1: 在庫サマリーを追加
        try:
            log_data["inventory_summary"] = self._inventory_manager.get_summary()
        except Exception as e:
            logger.warning(f"在庫サマリーの取得に失敗: {e}")
            log_data["inventory_summary"] = {}

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    def get_recommended_candidates(
        self,
        count: int = 10,
        enable_cache: bool = True,
        age_filter_min: int | None = None,
        age_filter_max: int | None = None,
        target_ages: list[int] | None = None,
    ) -> list[Candidate]:
        """
        推奨候補を取得

        EP数、カテゴリバランス、年齢カバレッジを考慮して候補を選定。
        CandidatePrioritizer を使用してスコアリング・優先度付け。
        Phase 1: 365本達成年齢はスキップ。

        Args:
            count: 候補数
            enable_cache: H4キャッシュ最適化有効（同一人物の複数年齢を許可）
            age_filter_min: 年齢フィルタ下限（Q1ロジックバイパス用）
            age_filter_max: 年齢フィルタ上限（Q1ロジックバイパス用）
            target_ages: 特定年齢リスト（例: [81, 82, 87]）- 指定時はこの年齢のみ対象

        Returns:
            list[Candidate]: 優先度順の候補リスト
        """
        if self.master_df.empty:
            return []

        # Phase 29: deficit優先年齢キャッシュをクリア（毎回最新を取得）
        self._cached_deficit_ages = None

        # Phase 1: 在庫状況を更新
        self._inventory_manager.refresh()

        # 候補プールを構築（ユニークな人物×利用可能年齢）
        candidate_pool = []
        person_pool = {}  # H4: person_id -> list of ages for cache grouping
        unique_persons = self.master_df.drop_duplicates(subset=["person_id"])

        for _, row in unique_persons.iterrows():
            person_id = row["person_id"]

            # Phase 8: 架空キャラ除外フィルタ
            person_type = str(row.get("person_type", "REAL"))
            if not self.config.fictional_enabled and person_type != "REAL":
                continue

            person_name = str(row.get("person_name", ""))
            category = str(row.get("category", ""))

            # クールダウン・クォータチェック
            person_id_str = str(person_id)
            quota_passed, _ = self._diversity_manager.check_person_quota(person_id_str)
            if not quota_passed:
                continue

            # 既存年齢を取得
            person_data = self.master_df[self.master_df["person_id"] == person_id_str]
            age_col = person_data["age"]
            existing_ages = set(int(x) for x in age_col if pd.notna(x))

            birth_year = row.get("birth_year")
            death_year = row.get("death_year")

            # Phase 27: canonical_age を取得
            canonical_age = row.get("canonical_age")
            if canonical_age and not pd.isna(canonical_age):
                canonical_age = int(canonical_age)
            else:
                canonical_age = None

            # Phase 65: 年齢フィルタが有効な場合はdeficitベース制限をバイパス
            # 指定年齢範囲内の全年齢を直接計算する
            age_filter_active = target_ages is not None or age_filter_min is not None or age_filter_max is not None

            if age_filter_active and person_type == "REAL":
                # 年齢フィルタモード: 指定範囲内の全年齢が候補（deficitベースの[:30]制限をバイパス）
                birth_year_int = int(birth_year) if birth_year and not pd.isna(birth_year) else None
                death_year_int = int(death_year) if death_year and not pd.isna(death_year) else None

                if birth_year_int and death_year_int:
                    max_age = min(death_year_int - birth_year_int, 100)
                    available_ages = [age for age in range(1, max_age + 1) if age not in existing_ages]
                elif birth_year_int:
                    # 存命: 現在年 - 生年
                    from datetime import datetime

                    current_year = datetime.now().year
                    max_age = min(current_year - birth_year_int, 100)
                    available_ages = [age for age in range(1, max_age + 1) if age not in existing_ages]
                else:
                    available_ages = []
            else:
                # 通常モード: deficitベースの年齢計算
                # Phase 30: person_name を渡して象徴的業績年齢を優先
                available_ages = self._calculate_available_ages_for_person(
                    person_type=person_type,
                    birth_year=int(birth_year) if birth_year and not pd.isna(birth_year) else None,
                    death_year=int(death_year) if death_year and not pd.isna(death_year) else None,
                    canonical_age=canonical_age,
                    existing_ages=existing_ages,
                    category=category,
                    person_name=person_name,  # Phase 30: 象徴的業績年齢統合
                )

            # 各年齢を候補プールに追加
            # Phase 3最適化: 全ての有効年齢を候補プールに追加
            # CandidatePrioritizerが在庫優先度に基づいてバランスを取る
            # Phase 65: 年齢フィルタを最初に適用（Q1ロジックをバイパス）
            for age in available_ages:
                # target_agesが指定されている場合、そのリストに含まれる年齢のみ
                if target_ages is not None and age not in target_ages:
                    continue
                # 年齢フィルタが指定されている場合、範囲外の年齢をスキップ
                if age_filter_min is not None and age < age_filter_min:
                    continue
                if age_filter_max is not None and age > age_filter_max:
                    continue

                item = {
                    "person_id": person_id,
                    "person_name": person_name,
                    "category": category,
                    "age": age,
                    "person_type": person_type,
                    "birth_year": int(birth_year) if birth_year and not pd.isna(birth_year) else None,
                    "death_year": int(death_year) if death_year and not pd.isna(death_year) else None,
                    "canonical_age": canonical_age,  # Phase 27
                }
                candidate_pool.append(item)

                # H4: 人物ごとにグループ化
                if person_id not in person_pool:
                    person_pool[person_id] = []
                person_pool[person_id].append(item)

        if not candidate_pool:
            return []

        # CandidatePrioritizer でスコアリング（Phase 12: 閾値適用）
        # Phase 3最適化: 年齢グループバランスのため全候補をスコアリング
        prioritizer = CandidatePrioritizer(master_csv=self.config.master_csv)
        scored = prioritizer.prioritize_candidates(
            candidate_pool,
            top_n=len(candidate_pool),  # Phase 3: 全候補をスコアリング
            min_score=self.config.min_candidate_priority,
        )

        # Phase 65: 年齢フィルタが指定されている場合、Q1グループ分けをバイパス
        # 年齢フィルタは既に候補プール構築時に適用済みなので、スコア順でそのまま選択
        age_filter_active = age_filter_min is not None or age_filter_max is not None or target_ages is not None

        if age_filter_active:
            # Phase 65: 年齢フィルタモード - 各年齢から均等に選定（ラウンドロビン方式）
            # target_agesが指定されている場合はそれを使用、なければ範囲から生成
            if target_ages is not None:
                effective_target_ages = target_ages
            else:
                age_min = age_filter_min or 0
                age_max = age_filter_max or 100
                effective_target_ages = list(range(age_min, age_max + 1))

            # Phase 65: 空チェック（ZeroDivisionError防止）
            if not effective_target_ages:
                logger.warning("Phase 65: 対象年齢が空のため候補なし")
                return []

            # ログ用の範囲表示を構築
            if target_ages is not None:
                ages_display = f"指定年齢: {sorted(effective_target_ages)}"
            else:
                ages_display = f"範囲: {age_filter_min or 0}-{age_filter_max or 100}歳"

            logger.info(
                f"Phase 65: 年齢フィルタモード有効（均等選定） "
                f"({ages_display}, "
                f"対象年齢数: {len(effective_target_ages)}, "
                f"候補プール: {len(scored)}件)"
            )

            # 各年齢ごとにスコア順でソートされた候補リストを構築
            age_slots: dict[int, list] = {age: [] for age in effective_target_ages}
            for score_result in scored:
                age = score_result.age
                if age in age_slots:
                    age_slots[age].append(score_result)

            # 各年齢から均等に選定（ラウンドロビン）
            candidates = []
            used_person_ages: set[tuple] = set()
            seen_persons: set = set()

            # 各年齢から最低1件ずつ選定を試みる（ラウンドロビン）
            # 複数ラウンドで全枠を埋める
            round_idx = 0
            max_rounds = max(1, count // len(effective_target_ages) + 2)  # 十分なラウンド数

            while len(candidates) < count and round_idx < max_rounds:
                added_this_round = False
                for age in effective_target_ages:
                    if len(candidates) >= count:
                        break

                    # この年齢の候補リストからround_idx番目を取得
                    slot_candidates = age_slots[age]
                    slot_idx = 0

                    for score_result in slot_candidates:
                        person_id = score_result.person_id

                        # 重複チェック
                        key = (person_id, age)
                        if key in used_person_ages:
                            continue

                        # enable_cache=False時は同一人物を1回まで
                        if not enable_cache and person_id in seen_persons:
                            continue

                        # このラウンドでこの年齢から選ぶべき候補かどうか
                        if slot_idx < round_idx:
                            slot_idx += 1
                            continue

                        # 候補を選択
                        used_person_ages.add(key)
                        seen_persons.add(person_id)

                        # person_poolから該当アイテムを取得
                        pool_item = next((p for p in person_pool.get(person_id, []) if p["age"] == age), None)

                        if pool_item:
                            candidates.append(
                                Candidate(
                                    person_id=pool_item["person_id"],
                                    person_name=pool_item["person_name"],
                                    age=pool_item["age"],
                                    category=pool_item["category"],
                                    person_type=pool_item.get("person_type", "REAL"),
                                    birth_year=pool_item.get("birth_year"),
                                    death_year=pool_item.get("death_year"),
                                    canonical_age=pool_item.get("canonical_age"),
                                )
                            )
                            added_this_round = True
                            break  # この年齢からは1件選んだので次の年齢へ

                round_idx += 1
                if not added_this_round:
                    # どの年齢からも追加できなかった場合は終了
                    break

            # 選定結果のログ
            age_distribution = {}
            for c in candidates:
                age_distribution[c.age] = age_distribution.get(c.age, 0) + 1
            logger.info(
                f"Phase 65: 年齢別選定結果 - 総数: {len(candidates)}件, 分布: {dict(sorted(age_distribution.items()))}"
            )
        else:
            # Phase 29: Q1対応 - 80歳以下優先モード
            # 従来のyoung/elderly_safe/normalグループを廃止し、
            # 80歳以下と81歳以上の2グループに変更
            def get_age_group(age: int) -> str:
                if age <= 80:
                    return "under_80"
                else:
                    return "over_80"

            # Q1: 80歳以下優先（80% vs 20%）
            # 80歳以下を優先する理由: 高齢エピソードは品質リスクが高く、若年〜壮年のカバレッジを優先
            group_targets = {
                "under_80": max(5, int(count * 0.80)),  # 80歳以下を80%
                "over_80": max(2, int(count * 0.20)),  # 81歳以上を20%
            }

            # 各グループごとに候補を選択
            candidates = []
            used_person_ages = set()  # (person_id, age) の重複防止

            for group_name in ["under_80", "over_80"]:
                target = group_targets[group_name]
                group_candidates = []
                seen_persons_in_group = set()

                for score_result in scored:
                    if len(group_candidates) >= target:
                        break

                    person_id = score_result.person_id
                    age = score_result.age

                    # このグループに属する年齢のみ
                    if get_age_group(age) != group_name:
                        continue

                    # 重複チェック
                    key = (person_id, age)
                    if key in used_person_ages:
                        continue

                    # enable_cache=False時は同一人物を1回まで（全グループ通じて）
                    if not enable_cache and person_id in seen_persons_in_group:
                        continue

                    used_person_ages.add(key)
                    seen_persons_in_group.add(person_id)

                    # person_poolから該当アイテムを取得
                    pool_item = next((p for p in person_pool.get(person_id, []) if p["age"] == age), None)

                    if pool_item:
                        group_candidates.append(
                            Candidate(
                                person_id=pool_item["person_id"],
                                person_name=pool_item["person_name"],
                                age=pool_item["age"],
                                category=pool_item["category"],
                                person_type=pool_item.get("person_type", "REAL"),
                                birth_year=pool_item.get("birth_year"),
                                death_year=pool_item.get("death_year"),
                                canonical_age=pool_item.get("canonical_age"),  # Phase 27
                            )
                        )

                candidates.extend(group_candidates)

        # person_id, age順にソート（キャッシュ効率化）
        # Phase 16: 型の不整合を防ぐため文字列に統一
        candidates.sort(key=lambda x: (str(x.person_id), int(x.age) if x.age is not None else 0))
        return candidates[:count]

    def _calculate_available_ages_for_person(
        self,
        person_type: str,
        birth_year: int | None,
        death_year: int | None,
        canonical_age: int | None,
        existing_ages: set[int],
        category: str = "",
        person_name: str = "",  # Phase 30: 象徴的業績年齢統合用
    ) -> list[int]:
        """
        人物タイプ別の利用可能年齢を計算

        Phase 27: 架空キャラ・動物の年齢解釈ロジック
        - REAL: birth_year ~ death_year の範囲
        - FICTIONAL/MYTHOLOGICAL: canonical_age ±10 years、または 18-60
        - ANIMAL: 実年齢（birth_year ~ death_year）、または種別デフォルト

        Args:
            person_type: 人物タイプ (REAL, FICTIONAL, MYTHOLOGICAL, ANIMAL)
            birth_year: 生年（実在人物・動物）または作品開始年
            death_year: 没年（実在人物・動物）または作品終了年
            canonical_age: 設定年齢（架空キャラ）
            existing_ages: 既存エピソードの年齢セット
            category: カテゴリ（動物の種別判定用）

        Returns:
            list[int]: 利用可能な年齢リスト
        """
        available_ages = []

        # REAL: 既存ロジック（birth_year ~ death_year）
        # Phase 30: person_name を渡して象徴的業績年齢を優先
        if person_type == "REAL":
            return self._calculate_real_person_ages(birth_year, death_year, existing_ages, person_name)

        # FICTIONAL / MYTHOLOGICAL: 作品内設定年齢を使用
        elif person_type in ("FICTIONAL", "MYTHOLOGICAL"):
            if canonical_age is not None:
                # Phase 28: canonical_age > 100 の場合は90-100歳を許可
                if canonical_age > 100:
                    # 非常に長寿のキャラクター（神話キャラ、魔法使いなど）
                    # 90-100歳の範囲でエピソード生成を許可
                    min_age = 90
                    max_age = 100
                else:
                    # 設定年齢 ±10歳の範囲（1-100に制限）
                    min_age = max(1, canonical_age - 10)
                    max_age = min(100, canonical_age + 10)
                for age in range(min_age, max_age + 1):
                    if age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)
            else:
                # 設定年齢不明の場合は成人年齢帯
                for age in range(18, 60):
                    if age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)

        # ANIMAL: 実年齢（人間換算しない）
        elif person_type == "ANIMAL":
            if birth_year and death_year:
                # 活動期間から計算
                max_animal_age = death_year - birth_year
                for age in range(1, max_animal_age + 1):
                    if age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)
            elif canonical_age is not None:
                # canonical_ageがある場合はその周辺
                min_age = max(1, canonical_age - 3)
                max_age = min(20, canonical_age + 3)
                for age in range(min_age, max_age + 1):
                    if age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)
            else:
                # カテゴリ別デフォルト年齢範囲
                if "競走馬" in category:
                    # 競走馬: 2-5歳（現役期間）
                    age_range = range(2, 6)
                elif "犬" in category or "ハチ公" in category or "タロ" in category:
                    # 犬: 1-15歳
                    age_range = range(1, 16)
                elif "猫" in category or "タマ" in category:
                    # 猫: 1-20歳
                    age_range = range(1, 21)
                else:
                    # その他動物: 1-15歳
                    age_range = range(1, 16)
                for age in age_range:
                    if age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)

        return available_ages

    def _get_deficit_priority_ages(self) -> list[int]:
        """
        deficit順に優先すべき年齢を取得（Q1対応: 80歳以下優先）

        Phase 29: キャッシュを使用してパフォーマンス最適化
        - 同一get_recommended_candidates()呼び出し内ではキャッシュを使用
        - キャッシュはget_recommended_candidates()開始時にクリア

        Returns:
            list[int]: deficit降順の年齢リスト（80歳以下を先に）
        """
        # キャッシュがあれば使用
        if self._cached_deficit_ages is not None:
            return self._cached_deficit_ages

        if not self._inventory_manager:
            # フォールバック: 5歳単位制約撤廃 - 全年齢を80歳以下優先で返す
            return list(range(1, 81)) + list(range(81, 101))

        self._inventory_manager.refresh()

        # 80歳以下と81歳以上を分けてdeficit順にソート
        under_80_ages: list[tuple[int, int]] = []
        over_80_ages: list[tuple[int, int]] = []

        for age in range(1, 101):
            status = self._inventory_manager.get_status(age)
            if status and status.deficit > 0:
                if age <= 80:
                    under_80_ages.append((age, status.deficit))
                else:
                    over_80_ages.append((age, status.deficit))

        # deficit降順でソート
        under_80_ages.sort(key=lambda x: -x[1])
        over_80_ages.sort(key=lambda x: -x[1])

        # 80歳以下を先に、その後81歳以上
        result = [age for age, _ in under_80_ages] + [age for age, _ in over_80_ages]

        # キャッシュに保存
        self._cached_deficit_ages = result

        return result

    def get_dynamic_priority_ages(self, person_name: str, existing_ages: set[int] | None = None) -> list[int]:
        """
        人物ごとの優先年齢を動的に計算（5歳単位制約の撤廃対応）

        優先順位:
        1. 象徴的業績の年齢（iconic_achievements_master.json）
        2. deficitが大きい年齢
        3. 既存年齢から5歳以上離れた年齢

        Args:
            person_name: 人物名
            existing_ages: 既存エピソードの年齢セット（除外対象）

        Returns:
            list[int]: 優先度順の年齢リスト
        """
        from pathlib import Path

        existing = existing_ages or set()
        result_ages: list[int] = []
        added: set[int] = set()

        # Step 1: 象徴的業績の年齢を最優先
        iconic_path = Path(__file__).parent.parent.parent / "preserved" / "data" / "iconic_achievements_master.json"
        try:
            with open(iconic_path, "r", encoding="utf-8") as f:
                iconic_data = json.load(f)
            person_data = iconic_data.get("persons", {}).get(person_name, {})
            if person_data:
                # priorityでソートして年齢を取得
                episodes = person_data.get("required_episodes", [])
                sorted_episodes = sorted(episodes, key=lambda x: x.get("priority", 999))
                for ep in sorted_episodes:
                    age = ep.get("age")
                    if age and age not in existing and age not in added:
                        result_ages.append(age)
                        added.add(age)
                        logger.debug(f"[get_dynamic_priority_ages] {person_name}: iconic age {age} added")
        except FileNotFoundError:
            logger.debug("iconic_achievements_master.json not found, skipping iconic ages")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse iconic_achievements_master.json: {e}")

        # Step 2: deficitが大きい年齢を追加
        deficit_ages = self._get_deficit_priority_ages()
        for age in deficit_ages:
            if age not in existing and age not in added:
                result_ages.append(age)
                added.add(age)

        # Step 3: 結果が空の場合のフォールバック（1-100の全年齢）
        if not result_ages:
            for age in range(1, 101):
                if age not in existing:
                    result_ages.append(age)

        return result_ages

    def _calculate_real_person_ages(
        self,
        birth_year: int | None,
        death_year: int | None,
        existing_ages: set[int],
        person_name: str = "",  # Phase 30: 象徴的業績年齢統合用
    ) -> list[int]:
        """
        実在人物の利用可能年齢を計算

        Phase 30: 象徴的業績年齢を最優先 + deficitベースのフォールバック
        - get_dynamic_priority_ages()で象徴的業績年齢を取得
        - iconic_achievements_master.json に登録された年齢が最優先
        - 未登録の場合はdeficitベースにフォールバック

        Args:
            birth_year: 生年
            death_year: 没年
            existing_ages: 既存エピソードの年齢セット
            person_name: 人物名（象徴的業績年齢の検索用）

        Returns:
            list[int]: 利用可能な年齢リスト
        """
        from datetime import datetime

        available_ages = []
        current_year = datetime.now().year

        # Phase 30: 象徴的業績年齢を最優先 + deficitベースのフォールバック
        deficit_priority_ages = self.get_dynamic_priority_ages(person_name, existing_ages)

        # Phase 31: 1-5歳も候補に含める（deficitが残っている場合）
        # 極端年齢は別途処理（既存フィルターとの整合性維持）
        # 1-89歳の範囲でdeficitベースに並べ替え
        safe_deficit_ages = [age for age in deficit_priority_ages if 1 <= age <= 89]

        # centenarian_ages (90-100) は既存ロジックを維持
        centenarian_ages = [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100]

        # Phase 31: extreme_young_ages (1-10) は safe_deficit_ages に含まれるようになった
        # フォールバック用に残す（safe_deficit_agesが空の場合のみ使用）
        extreme_young_ages_fallback = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        if birth_year and not pd.isna(birth_year):
            birth_year_int = int(birth_year)

            # Phase 28: 最大年齢の計算
            if death_year and not pd.isna(death_year):
                # 故人: 没年 - 生年
                max_age = int(death_year) - birth_year_int
            else:
                # 存命: 現在年 - 生年（未来の年齢は生成不可）
                max_age = current_year - birth_year_int

            # 100歳で上限クリップ
            max_age = min(max_age, 100)

            # Phase 32: death_year制限を解除
            # 90-100歳の候補プールを拡大するため、death_year未確認でも候補に含める
            # （品質リスクはpre_generation_rulesで個別に判断）

            # Phase 29: deficitベースの年齢リストを使用
            # safe_deficit_ages（1-89歳）を優先、その後centenarian_ages
            all_age_lists = [
                safe_deficit_ages[:30],  # deficitベースの上位30年齢（1-89歳）
            ]
            # Phase 32: 90-100歳を常に候補に含める（death_year制限解除）
            all_age_lists.append(centenarian_ages)  # 90-100歳

            added_ages = set()
            for age_list in all_age_lists:
                for age in age_list:
                    if age in added_ages:
                        continue
                    if age <= max_age and age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)
                            added_ages.add(age)
        else:
            # birth_yearがない場合は安全な範囲のみ使用（89歳以下）
            added_ages = set()
            for age in safe_deficit_ages[:30]:
                if age in added_ages:
                    continue
                if age not in existing_ages:
                    if self._inventory_manager.should_generate(age):
                        available_ages.append(age)
                        added_ages.add(age)

            # フォールバック: safe_deficit_agesが空の場合
            if not available_ages:
                for age in extreme_young_ages_fallback:
                    if age not in existing_ages:
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)

        return available_ages


def create_orchestrator(
    strategy: str = "epgen_first",
    dry_run: bool = True,
    target_count: int = 10,
    use_mock: bool = False,
) -> HybridOrchestrator:
    """
    オーケストレータを作成

    Args:
        strategy: 戦略名
        dry_run: dry-runモード
        target_count: 目標生成数
        use_mock: モックアダプター使用

    Returns:
        HybridOrchestrator: オーケストレータ
    """
    config = HybridConfig(
        strategy=Strategy(strategy),
        dry_run=dry_run,
        target_count=target_count,
        use_mock=use_mock,
    )
    return HybridOrchestrator(config)
