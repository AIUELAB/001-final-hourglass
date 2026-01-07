"""
Hybrid Generation Orchestrator

ハイブリッドエピソード生成のメインオーケストレータ。
全コンポーネントを統合し、エンドツーエンドの生成パイプラインを提供。
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .adapters import Candidate, GenerationResult
from .config import (
    GENERATION_RULES,
    LOGS_DIR,
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
from .persistence import SafeCSVWriter, WriteResult
from .inventory_manager import InventoryManager, ReplacementTarget
from .pre_generation_rules import PreGenerationRules, check_prohibited_patterns, check_specificity
from .quality import ImprovementLoop, QualityEvaluator, SuperTotalCalculator
from .strategy_router import StrategyRouter

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

    全コンポーネントを統合し、以下のパイプラインを実行:
    1. 候補選定（多様性考慮）
    2. 生成前ルールチェック
    3. 戦略ベースの生成
    4. 品質ゲートチェック
    5. ファクトチェック
    6. 重複検出
    7. 改善ループ
    8. 安全な永続化
    """

    def __init__(self, config: HybridConfig = None):
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

        # Phase 3: アンチゲーミングモニター
        self._anti_gaming = AntiGamingMonitor()

        # マスターデータ
        self._master_df: Optional[pd.DataFrame] = None

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
                    "reason": RejectionReason.WEEKLY_LIMIT_EXCEEDED.value,
                    "message": quota_reason,
                }
            )

        # 3. 生成
        result = self._router.route(candidate)

        if not result.success:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "reason": RejectionReason.GENERATION_ERROR.value,
                    "message": result.error_message,
                }
            )

        # 4. 禁止パターンチェック
        pattern_check = check_prohibited_patterns(result.episode_text)
        if not pattern_check.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "reason": pattern_check.reason.value if pattern_check.reason else "prohibited",
                    "message": pattern_check.message,
                }
            )

        # 5. 具体性チェック
        specificity_check = check_specificity(result.episode_text)
        if not specificity_check.passed:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "reason": specificity_check.reason.value if specificity_check.reason else "filler",
                    "message": specificity_check.message,
                }
            )

        # 5.5. Phase 3: アンチゲーミングチェック（キーワード詰め込み、抽象語過多、テンプレート臭）
        gaming_result = self._anti_gaming.check(result.episode_text, candidate.person_name)
        # missing_specifics は step 5 でカバー済みなので除外
        gaming_violations = [v for v in gaming_result.violations if v != "missing_specifics"]
        if gaming_violations:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "reason": gaming_result.rejection_reason.value if gaming_result.rejection_reason else "anti_gaming",
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
                    "reason": fact_result.rejection_reason.value if fact_result.rejection_reason else "fact_check",
                    "message": fact_result.reason,
                }
            )

        # 7. 重複チェック
        dup_result = self._duplicate_detector.check_all(result.episode_text, candidate.person_id, candidate.age)
        if dup_result.is_duplicate:
            return ProcessingResult(
                rejection={
                    "person_id": candidate.person_id,
                    "person_name": candidate.person_name,
                    "reason": dup_result.rejection_reason.value if dup_result.rejection_reason else "duplicate",
                    "message": dup_result.reason,
                }
            )

        # 8. 品質ゲートチェック
        if result.evaluation:
            gate_result = self._evaluator.check_quality_gates(result.evaluation.axis_scores)
            if not gate_result.passed:
                return ProcessingResult(
                    rejection={
                        "person_id": candidate.person_id,
                        "person_name": candidate.person_name,
                        "reason": gate_result.reason.value if gate_result.reason else "quality_gate",
                        "message": ", ".join(gate_result.failures),
                    }
                )

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
                        "reason": RejectionReason.LOW_SUPER_TOTAL.value,
                        "message": ", ".join(super_result.gate_failures),
                    }
                )

        # 10. 生成履歴を記録
        self._pre_rules.record_generation(candidate.person_id, success=True)
        self._diversity_manager.record_generation(candidate.person_id)

        # 11. Phase 4: 置換モード判定
        is_replacement = False
        replacement_target = None

        if self._inventory_manager.is_replacement_mode(candidate.age):
            # 置換対象を取得
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
                    / run.generated_count,
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
        except Exception:
            log_data["inventory_summary"] = {}

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    def get_recommended_candidates(self, count: int = 10) -> list[Candidate]:
        """
        推奨候補を取得

        EP数、カテゴリバランス、年齢カバレッジを考慮して候補を選定。
        CandidatePrioritizer を使用してスコアリング・優先度付け。
        Phase 1: 365本達成年齢はスキップ。

        Args:
            count: 候補数

        Returns:
            list[Candidate]: 優先度順の候補リスト
        """
        if self.master_df.empty:
            return []

        # Phase 1: 在庫状況を更新
        self._inventory_manager.refresh()

        # 候補プールを構築（ユニークな人物×利用可能年齢）
        candidate_pool = []
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
            quota_passed, _ = self._diversity_manager.check_person_quota(person_id)
            if not quota_passed:
                continue

            # 既存年齢を取得
            person_data = self.master_df[self.master_df["person_id"] == person_id]
            existing_ages = set(person_data["age"].dropna().astype(int))

            birth_year = row.get("birth_year")
            death_year = row.get("death_year")

            # 利用可能な年齢を計算
            available_ages = []
            if birth_year and not pd.isna(birth_year):
                birth_year = int(birth_year)
                max_age = 100
                if death_year and not pd.isna(death_year):
                    max_age = int(death_year) - birth_year

                # 5歳刻みで候補年齢を生成（より細かく）
                for age in range(15, min(max_age + 1, 100), 5):
                    if age not in existing_ages:
                        # Phase 1: 365本達成年齢はスキップ
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)
            else:
                # birth_yearがない場合はデフォルト範囲を使用
                for age in [20, 25, 30, 35, 40, 45, 50, 55, 60]:
                    if age not in existing_ages:
                        # Phase 1: 365本達成年齢はスキップ
                        if self._inventory_manager.should_generate(age):
                            available_ages.append(age)

            # 各年齢を候補プールに追加
            for age in available_ages[:3]:  # 人物あたり最大3年齢
                candidate_pool.append(
                    {
                        "person_id": person_id,
                        "person_name": person_name,
                        "category": category,
                        "age": age,
                        "person_type": str(row.get("person_type", "REAL")),
                        "birth_year": birth_year if not pd.isna(birth_year) else None,
                        "death_year": int(death_year) if death_year and not pd.isna(death_year) else None,
                    }
                )

        if not candidate_pool:
            return []

        # CandidatePrioritizer でスコアリング
        prioritizer = CandidatePrioritizer(master_csv=self.config.master_csv)
        scored = prioritizer.prioritize_candidates(candidate_pool, top_n=count * 2)

        # 人物重複を避けて上位を選定
        seen_persons = set()
        candidates = []

        for score_result in scored:
            if score_result.person_id in seen_persons:
                continue

            seen_persons.add(score_result.person_id)

            # 候補データを取得
            pool_item = next(
                (
                    p
                    for p in candidate_pool
                    if p["person_id"] == score_result.person_id and p["age"] == score_result.age
                ),
                None,
            )

            if pool_item:
                candidates.append(
                    Candidate(
                        person_id=score_result.person_id,
                        person_name=score_result.person_name,
                        age=score_result.age,
                        category=score_result.category,
                        person_type=pool_item.get("person_type", "REAL"),
                        birth_year=pool_item.get("birth_year"),
                        death_year=pool_item.get("death_year"),
                    )
                )

            if len(candidates) >= count:
                break

        return candidates


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
