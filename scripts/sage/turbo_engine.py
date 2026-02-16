"""
SAGE Turbo Engine

APIレート制限まで自動的にエピソードを生成し続けるエンジン。
"""

import hashlib
import json
import logging
import signal
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import HybridConfig, Strategy
from .orchestrator import GenerationRun, HybridOrchestrator
from .pre_generation_rules import Candidate as PreRulesCandidate, PreGenerationRules

# Phase 20: Batch API統合
from .batch_processor import BatchProcessor, BatchRequest, BatchJob

# Step 2.5: EPUP重複チェック用
from .gates.duplicate import DuplicateDetector

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# チェックポイントパス
CHECKPOINT_PATH = PROJECT_ROOT / "src" / "cache" / "turbo_checkpoint.json"


class RateLimitError(Exception):
    """レート制限エラー"""

    pass


@dataclass
class TurboConfig:
    """Turboモード設定"""

    # バッチサイズ
    initial_batch_size: int = 10
    max_batch_size: int = 50
    min_batch_size: int = 3

    # 制限
    cost_limit_usd: float = 10.0
    time_limit_minutes: int = 60

    # レート制限対応
    rate_limit_cooldown: int = 60  # 秒
    max_rate_limit_count: int = 3

    # チェックポイント
    checkpoint_interval: int = 20  # 件数ごと

    # 実行モード
    dry_run: bool = True
    use_mock: bool = False
    strategy: Strategy = Strategy.EPGEN_FIRST
    fictional_enabled: bool = False

    # 年齢フィルタ（Q1ロジックバイパス用）
    age_filter_min: Optional[int] = None
    age_filter_max: Optional[int] = None
    # 特定年齢指定（例: [81, 82, 87] で特定年齢のみ対象）
    target_ages: Optional[list[int]] = None


@dataclass
class TurboState:
    """実行状態（チェックポイント用）"""

    total_generated: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    rate_limit_count: int = 0
    current_batch_size: int = 10
    batch_count: int = 0
    candidates_processed: list[str] = field(default_factory=list)  # person_id:age

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_generated": self.total_generated,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
            "total_cost_usd": self.total_cost_usd,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "rate_limit_count": self.rate_limit_count,
            "current_batch_size": self.current_batch_size,
            "batch_count": self.batch_count,
            "candidates_processed": self.candidates_processed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TurboState":
        return cls(**data)


@dataclass
class TurboReport:
    """Turbo実行レポート"""

    start_time: str
    end_time: str
    duration_minutes: float
    total_generated: int
    total_accepted: int
    total_rejected: int
    acceptance_rate: float
    total_cost_usd: float
    cost_per_episode_usd: float
    total_input_tokens: int
    total_output_tokens: int
    rate_limit_count: int
    batch_count: int
    stop_reason: str
    checkpoint_path: Optional[str] = None
    # Phase 1最適化: 生成前フィルタ統計
    pre_filter_stats: dict[str, int] = field(default_factory=dict)
    pre_filter_saved_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TurboEngine:
    """
    APIレート制限まで生成し続けるエンジン

    特徴:
    - コスト上限・時間上限・レート制限での自動停止
    - 成功率に基づくアダプティブバッチサイズ調整
    - チェックポイント保存・再開
    - グレースフルシャットダウン（Ctrl+C対応）
    """

    def __init__(self, config: Optional[TurboConfig] = None):
        self.config = config or TurboConfig()
        self.state = TurboState(current_batch_size=self.config.initial_batch_size)

        # オーケストレータ設定
        hybrid_config = HybridConfig(
            strategy=self.config.strategy,
            dry_run=self.config.dry_run,
            use_mock=self.config.use_mock,
            fictional_enabled=self.config.fictional_enabled,
        )
        self.orchestrator = HybridOrchestrator(hybrid_config)

        # Phase 1最適化: 生成前フィルタ
        self._pre_rules = PreGenerationRules()
        self._pre_filter_stats: dict[str, int] = {}  # {reason: count}

        # Phase 3最適化: 候補プール（年齢バランス維持）
        self._candidate_pool: list = []
        self._pool_refill_threshold = 50  # プールが50件以下になったら補充

        # 開始時刻
        self._start_time: Optional[datetime] = None
        self._stop_requested = False
        self._stop_reason = ""

        # Phase 28最適化: 評価用キャッシュ
        self._super_total_calc = None  # 遅延初期化
        self._master_df_cache = None  # マスターDFキャッシュ

        # シグナルハンドラ設定
        self._setup_signal_handlers()

    def _get_min_length(self, age: int, category: str) -> int:
        """
        Phase 22: 年齢・カテゴリ別の動的最小長

        Args:
            age: 対象年齢
            category: カテゴリ名

        Returns:
            最小文字数
        """
        # 幼少期・晩年は短くてもOK（史料が少ない）
        if age <= 15 or age >= 75:
            return 150

        # 史料が少ないカテゴリ
        if category in ["歴史上の動物", "架空キャラ", "神話・伝説"]:
            return 160

        # 通常ケース（200→180に緩和）
        return 180

    def _evaluate_episode(
        self,
        text: str,
        person_id: str,
        category: str,
        person_name: str = "",
        age: int = 0,
    ):
        """
        Phase 25: エピソードの品質評価（iconic_score計算追加）
        Phase 28: パフォーマンス最適化（キャッシュ活用）

        Args:
            text: エピソードテキスト
            person_id: 人物ID
            category: カテゴリ
            person_name: 人物名（Phase 25: iconic_score用）
            age: 年齢（Phase 25: iconic_score用）

        Returns:
            EvaluationResult: 評価結果
        """
        from .adapters.base import AxisScores, EvaluationResult
        from .quality.evaluator import QualityEvaluator, CompositeScoreCalculator, IconicScoreCalculator
        from .quality.super_total import SuperTotalCalculator
        import pandas as pd
        from pathlib import Path

        # テキスト分析
        evaluator = QualityEvaluator()
        text_quality = evaluator.evaluate_text_quality(text)

        # 具体性スコアから7軸を推定
        specificity = text_quality.get("specificity_score", 0)
        has_year = text_quality.get("has_year", False)
        has_proper_nouns = text_quality.get("has_proper_nouns", False)
        proper_noun_count = text_quality.get("proper_noun_count", 0)

        # Batch API生成のベースライン（高品質想定）
        base_score = 7.5

        # 具体性によるボーナス
        specificity_bonus = min(specificity * 0.3, 1.5)
        if has_year:
            specificity_bonus += 0.3
        if has_proper_nouns and proper_noun_count >= 3:
            specificity_bonus += 0.5

        fd_score = min(base_score + specificity_bonus, 9.5)
        gq_score = min(base_score + 0.5 + specificity_bonus * 0.5, 9.5)

        # Phase 25: iconic_score 計算（person_name + age でマスターデータ参照）
        iconic_calc = IconicScoreCalculator()
        iconic_score = iconic_calc.calculate(text, person_name, age)

        axis_scores = AxisScores(
            memorability=min(7.0 + specificity_bonus * 0.3, 9.0),
            empathy=7.0,
            surprise=6.5,
            generation_quality=gq_score,
            educational_value=7.0,
            story_quality=7.5,
            factual_density=fd_score,
            iconic_score=iconic_score,  # Phase 25: 動的計算
        )

        # composite score
        composite = CompositeScoreCalculator.calculate(axis_scores)

        # Phase 28最適化: super_total計算（キャッシュ活用）
        if self._super_total_calc is None:
            self._super_total_calc = SuperTotalCalculator()

        if self._master_df_cache is None:
            master_csv = Path(__file__).parent.parent.parent / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
            if master_csv.exists():
                self._master_df_cache = pd.read_csv(master_csv, encoding="utf-8-sig")

        super_result = self._super_total_calc.calculate(person_id, axis_scores, self._master_df_cache)

        return EvaluationResult(
            axis_scores=axis_scores,
            composite_score=composite,
            super_total_score=super_result.score,
            passed_gate=super_result.passed_gate,
            gate_failures=super_result.gate_failures,
        )

    def _write_accepted_episodes(self, accepted: list[dict], batch_id: str, model_used: str = "") -> tuple[int, int]:
        """
        Phase 24: 後処理 + 品質評価 + CSV書き込み
        Phase 26: モデル追跡とコスト可視化

        Args:
            accepted: 採用エピソードのリスト（dict形式）
            batch_id: バッチID
            model_used: 使用モデル名（Phase 26追加）

        Returns:
            tuple: (書き込み成功数, スキップ数)
        """
        from .adapters import Candidate, GenerationResult
        from .persistence.csv_writer import SafeCSVWriter
        from .gates.post_processor import apply_post_processing

        logger.info(f"Phase 25: 後処理+品質評価+iconic_score+CSV書き込み ({len(accepted)}件)")

        generation_results = []
        quality_rejected = 0
        post_processed_count = 0

        for ep in accepted:
            # person_idをメタデータから直接取得
            person_id = ep.get("person_id", "")
            if not person_id:
                # フォールバック（古いフォーマット対応）
                custom_id = ep.get("custom_id", "")
                parts = custom_id.rsplit("_", 1)
                person_id = parts[0] if len(parts) >= 1 else custom_id
            person_name = ep.get("person_name", "")
            age = ep.get("age", 0)
            category = ep.get("category", "")
            original_text = ep.get("text", "")

            # Step 1: 後処理適用
            processed_text, changes = apply_post_processing(
                episode_text=original_text,
                person_name=person_name,
                age=age,
                strict_mode=True,
            )
            if changes:
                post_processed_count += 1
                logger.debug(f"後処理: {person_name}({age}歳) - {changes}")

            # Step 2: 品質評価（Phase 25: person_name, age 追加）
            evaluation = self._evaluate_episode(
                processed_text,
                person_id,
                category,
                person_name=person_name,
                age=age,
            )

            # 品質ゲートチェック（super_total_score基準）
            if not evaluation.passed_gate:
                logger.info(f"品質ゲート不合格: {person_name}({age}歳) super_total={evaluation.super_total_score:.0f}")
                quality_rejected += 1
                continue

            # Step 3: GenerationResult作成（evaluation付き）
            candidate = Candidate(
                person_id=person_id,
                person_name=person_name,
                age=age,
                category=category,
                person_type="REAL",
            )

            # Phase 26: モデル追跡とコスト計算
            is_haiku = "haiku" in model_used.lower() if model_used else True
            generator_type = "batch_api_haiku" if is_haiku else "batch_api_sonnet"

            # トークン使用量からコスト計算（Batch API 50%割引適用）
            usage = ep.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            if is_haiku:
                # Haiku Batch: input $0.40/1M, output $2.00/1M
                cost_usd = (input_tokens * 0.40 + output_tokens * 2.00) / 1_000_000
            else:
                # Sonnet Batch: input $1.50/1M, output $7.50/1M
                cost_usd = (input_tokens * 1.50 + output_tokens * 7.50) / 1_000_000

            result = GenerationResult(
                success=True,
                candidate=candidate,
                episode_text=processed_text,
                episode_type="生成",
                char_count=len(processed_text),
                generator_type=generator_type,
                evaluation=evaluation,  # Phase 24: 評価結果を付加
                model=model_used,  # Phase 26: 使用モデル名
                cost_usd=round(cost_usd, 6),  # Phase 26: コスト（USD）
            )
            generation_results.append(result)

        logger.info(f"後処理適用: {post_processed_count}件")
        logger.info(f"品質ゲート除外: {quality_rejected}件")

        # Step 4: CSV書き込み
        if generation_results:
            writer = SafeCSVWriter()
            write_result = writer.write(generation_results)

            if write_result.success:
                logger.info(f"✓ 書き込み成功: {write_result.added_count}件追加")
                if write_result.skipped_count:
                    logger.info(f"  EPUP重複スキップ: {write_result.skipped_count}件")
                if write_result.backup_path:
                    logger.info(f"  バックアップ: {write_result.backup_path}")
            else:
                logger.error(f"✗ 書き込みエラー: {write_result.error_message}")

            return (write_result.added_count or 0, write_result.skipped_count or 0)

        return (0, len(accepted))

    def _setup_signal_handlers(self) -> None:
        """シグナルハンドラを設定"""

        def handler(signum, _frame):
            logger.info(f"シグナル受信: {signum}")
            self._stop_requested = True
            self._stop_reason = "manual_interrupt"

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def run(self) -> TurboReport:
        """メインループ - レート制限まで実行"""
        self._start_time = datetime.now()
        logger.info("Turboモード開始")
        logger.info(f"コスト上限: ${self.config.cost_limit_usd:.2f}")
        logger.info(f"時間上限: {self.config.time_limit_minutes}分")

        while not self._should_stop():
            try:
                # 1. 候補取得
                candidates = self._get_next_batch()
                if not candidates:
                    logger.info("候補が枯渇しました")
                    self._stop_reason = "candidates_exhausted"
                    break

                logger.info(f"バッチ#{self.state.batch_count + 1}: {len(candidates)}件の候補を処理")

                # 2. バッチ生成
                run_result = self._generate_batch(candidates)

                # 3. 状態更新
                self._update_state(run_result)

                # 4. アダプティブ調整
                self._adapt_batch_size(run_result)

                # 5. 進捗表示
                self._print_progress()

                # 6. チェックポイント保存
                if self._should_checkpoint():
                    self._save_checkpoint()

            except RateLimitError as e:
                self._handle_rate_limit(e)
            except Exception as e:
                logger.error(f"予期しないエラー: {e}")
                self._stop_reason = f"error: {e}"
                break

        # 最終チェックポイント保存
        checkpoint_path = self._save_checkpoint()

        return self._generate_report(checkpoint_path)

    def _should_stop(self) -> bool:
        """停止条件チェック"""
        if self._stop_requested:
            if not self._stop_reason:
                self._stop_reason = "manual_stop"
            return True

        if self.state.total_cost_usd >= self.config.cost_limit_usd:
            logger.info(f"コスト上限到達: ${self.state.total_cost_usd:.2f}")
            self._stop_reason = "cost_limit"
            return True

        if self._elapsed_minutes() >= self.config.time_limit_minutes:
            logger.info(f"時間上限到達: {self._elapsed_minutes():.1f}分")
            self._stop_reason = "time_limit"
            return True

        if self.state.rate_limit_count >= self.config.max_rate_limit_count:
            logger.info(f"レート制限上限到達: {self.state.rate_limit_count}回")
            self._stop_reason = "rate_limit"
            return True

        return False

    def _elapsed_minutes(self) -> float:
        """経過時間（分）"""
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds() / 60

    def _get_next_batch(self) -> list:
        """次のバッチの候補を取得（Phase 3最適化: 年齢バランス維持プール版）"""
        # 処理済みセット
        processed_set = set(self.state.candidates_processed)

        # プールが少なくなったら補充（年齢バランスを維持）
        if len(self._candidate_pool) < self._pool_refill_threshold:
            # 大量に取得（200件）して年齢バランスを確保
            new_candidates = self.orchestrator.get_recommended_candidates(
                200,  # 十分な量を取得
                enable_cache=False,
            )

            # 処理済み・プール内の候補を除外
            pool_keys = {f"{c.person_id}:{c.age}" for c in self._candidate_pool}
            for c in new_candidates:
                key = f"{c.person_id}:{c.age}"
                if key in processed_set or key in pool_keys:
                    continue

                # 生成前ルールチェック
                pre_candidate = PreRulesCandidate(
                    person_id=c.person_id,
                    person_name=c.person_name,
                    age=c.age,
                    category=c.category,
                    person_type=c.person_type,
                    birth_year=c.birth_year,
                    death_year=c.death_year,
                )
                rule_result = self._pre_rules.check_all(pre_candidate)
                if not rule_result.passed:
                    reason = rule_result.reason.value if rule_result.reason else "unknown"
                    self._pre_filter_stats[reason] = self._pre_filter_stats.get(reason, 0) + 1
                    logger.debug(f"生成前フィルタ除外: {c.person_name}({c.age}歳) - {reason}")
                    continue

                self._candidate_pool.append(c)

            logger.info(f"候補プール補充: {len(self._candidate_pool)}件")

        # プールから処理済みを除外（他バッチで処理された可能性）
        self._candidate_pool = [c for c in self._candidate_pool if f"{c.person_id}:{c.age}" not in processed_set]

        # バッチサイズ分を取得（プールの先頭から）
        batch_size = min(self.state.current_batch_size, len(self._candidate_pool))
        candidates = self._candidate_pool[:batch_size]

        # 取得した候補をプールから削除
        self._candidate_pool = self._candidate_pool[batch_size:]

        # 【H4最適化】person_id順にソート（Prompt Caching効率化）
        candidates.sort(key=lambda x: (x.person_id, x.age))

        logger.info(f"バッチ取得: {len(candidates)}件, プール残り: {len(self._candidate_pool)}件")

        return candidates

    def _generate_batch(self, candidates: list) -> GenerationRun:
        """バッチ生成を実行"""
        # エラーメッセージからレート制限を検出
        try:
            run = self.orchestrator.run(candidates, dry_run=self.config.dry_run)

            # 棄却理由からレート制限を検出
            for rejection in run.rejections:
                msg = str(rejection.get("message", "")).lower()
                if any(kw in msg for kw in ["rate_limit", "429", "too many requests", "overloaded"]):
                    raise RateLimitError(rejection.get("message", ""))

            return run

        except Exception as e:
            error_msg = str(e).lower()
            if any(kw in error_msg for kw in ["rate_limit", "429", "too many requests", "overloaded"]):
                raise RateLimitError(str(e))
            raise

    def _update_state(self, run: GenerationRun) -> None:
        """状態を更新"""
        self.state.total_generated += run.generated_count
        self.state.total_accepted += run.accepted_count
        self.state.total_rejected += run.rejected_count
        self.state.batch_count += 1

        # コスト計算（ルーターからアダプター統計を取得）
        try:
            router = getattr(self.orchestrator, "_router", None)
            if router and hasattr(router, "collect_adapter_stats"):
                stats = router.collect_adapter_stats()
                combined = stats.get("combined", {})
                self.state.total_input_tokens = combined.get("total_input_tokens", 0)
                self.state.total_output_tokens = combined.get("total_output_tokens", 0)
                self.state.total_cost_usd = combined.get("estimated_cost_usd", 0.0)
        except Exception as e:
            logger.warning(f"コスト取得エラー（計算が不正確な可能性）: {e}")
            # コスト計算失敗を明示（-1は計算失敗を示す）
            self.state.total_cost_usd = -1.0

        # 処理済みを記録（採用されたもの）
        for result in run.results:
            key = f"{result.candidate.person_id}:{result.candidate.age}"
            if key not in self.state.candidates_processed:
                self.state.candidates_processed.append(key)

        # 処理済みを記録（棄却されたもの）
        # Phase 3修正: 棄却された候補も再処理を防ぐため記録
        for rejection in run.rejections:
            person_id = rejection.get("person_id", "")
            age = rejection.get("age", "")
            if person_id and age != "":
                key = f"{person_id}:{age}"
                if key not in self.state.candidates_processed:
                    self.state.candidates_processed.append(key)

    def _adapt_batch_size(self, run: GenerationRun) -> None:
        """成功率に基づくバッチサイズ調整"""
        if run.generated_count == 0:
            return

        success_rate = run.accepted_count / run.generated_count

        if success_rate > 0.9:
            # 高成功率 → バッチ増加
            new_size = min(self.state.current_batch_size + 5, self.config.max_batch_size)
            if new_size != self.state.current_batch_size:
                logger.info(
                    f"バッチサイズ増加: {self.state.current_batch_size} → {new_size} (成功率: {success_rate:.1%})"
                )
                self.state.current_batch_size = new_size
        elif success_rate < 0.5:
            # 低成功率 → バッチ縮小
            new_size = max(self.state.current_batch_size - 5, self.config.min_batch_size)
            if new_size != self.state.current_batch_size:
                logger.info(
                    f"バッチサイズ縮小: {self.state.current_batch_size} → {new_size} (成功率: {success_rate:.1%})"
                )
                self.state.current_batch_size = new_size

    def _handle_rate_limit(self, error: RateLimitError) -> None:
        """レート制限ハンドリング"""
        self.state.rate_limit_count += 1
        cooldown = self.config.rate_limit_cooldown * self.state.rate_limit_count

        logger.warning(f"レート制限検出 (#{self.state.rate_limit_count}): {error}")
        logger.info(f"クールダウン: {cooldown}秒")

        # バッチサイズ縮小
        new_size = max(self.state.current_batch_size // 2, self.config.min_batch_size)
        if new_size != self.state.current_batch_size:
            logger.info(f"バッチサイズ縮小: {self.state.current_batch_size} → {new_size}")
            self.state.current_batch_size = new_size

        # 上限チェック
        if self.state.rate_limit_count >= self.config.max_rate_limit_count:
            logger.error(f"レート制限{self.config.max_rate_limit_count}回到達 - 停止")
            self._stop_requested = True
            self._stop_reason = "rate_limit"
            return

        # クールダウン待機
        logger.info(f"{cooldown}秒待機中...")
        time.sleep(cooldown)

    def _should_checkpoint(self) -> bool:
        """チェックポイント保存タイミング判定"""
        return self.state.total_generated % self.config.checkpoint_interval == 0

    def _save_checkpoint(self) -> str:
        """チェックポイント保存"""
        CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "state": self.state.to_dict(),
            "config": {
                "cost_limit_usd": self.config.cost_limit_usd,
                "time_limit_minutes": self.config.time_limit_minutes,
                "strategy": self.config.strategy.value,
            },
            "timestamp": datetime.now().isoformat(),
        }

        CHECKPOINT_PATH.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
        logger.debug(f"チェックポイント保存: {CHECKPOINT_PATH}")

        return str(CHECKPOINT_PATH)

    def resume_from_checkpoint(self) -> bool:
        """チェックポイントから再開

        Returns:
            True: 正常に再開
            False: チェックポイントが存在しない（新規開始）

        Raises:
            json.JSONDecodeError: チェックポイントファイルが破損
            KeyError: 必須キーが欠落
            ValueError: 状態データが不正
        """
        if not CHECKPOINT_PATH.exists():
            logger.info("チェックポイントなし - 新規開始")
            return False

        try:
            data = json.loads(CHECKPOINT_PATH.read_text())
            if "state" not in data:
                raise KeyError("チェックポイントに'state'キーがありません")
            self.state = TurboState.from_dict(data["state"])
            logger.info(f"チェックポイントから再開: {self.state.total_generated}件生成済み")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"チェックポイントファイル破損 (JSON不正): {e}")
            raise
        except KeyError as e:
            logger.error(f"チェックポイントに必須キー欠落: {e}")
            raise
        except Exception as e:
            logger.error(f"チェックポイント読み込みエラー: {e}")
            raise

    def _print_progress(self) -> None:
        """進捗表示"""
        acceptance_rate = (
            self.state.total_accepted / self.state.total_generated if self.state.total_generated > 0 else 0
        )
        # 生成前フィルタ統計
        pre_filter_total = sum(self._pre_filter_stats.values())
        pre_filter_info = f" 事前除外={pre_filter_total}" if pre_filter_total > 0 else ""

        logger.info(
            f"進捗: 生成={self.state.total_generated} "
            f"採用={self.state.total_accepted} "
            f"(採用率: {acceptance_rate:.1%}){pre_filter_info} "
            f"コスト=${self.state.total_cost_usd:.3f} "
            f"経過={self._elapsed_minutes():.1f}分"
        )

    def _generate_report(self, checkpoint_path: Optional[str]) -> TurboReport:
        """最終レポート生成"""
        end_time = datetime.now()
        duration = (end_time - self._start_time).total_seconds() / 60 if self._start_time else 0

        acceptance_rate = (
            self.state.total_accepted / self.state.total_generated if self.state.total_generated > 0 else 0
        )

        cost_per_episode = self.state.total_cost_usd / self.state.total_accepted if self.state.total_accepted > 0 else 0

        # Phase 1最適化: 生成前フィルタで節約したコストを推定
        # 平均1件あたり約$0.005のLLMコスト（生成+評価）を節約
        pre_filter_total = sum(self._pre_filter_stats.values())
        pre_filter_saved_cost = pre_filter_total * 0.005

        return TurboReport(
            start_time=self._start_time.isoformat() if self._start_time else "",
            end_time=end_time.isoformat(),
            duration_minutes=duration,
            total_generated=self.state.total_generated,
            total_accepted=self.state.total_accepted,
            total_rejected=self.state.total_rejected,
            acceptance_rate=acceptance_rate,
            total_cost_usd=self.state.total_cost_usd,
            cost_per_episode_usd=cost_per_episode,
            total_input_tokens=self.state.total_input_tokens,
            total_output_tokens=self.state.total_output_tokens,
            rate_limit_count=self.state.rate_limit_count,
            batch_count=self.state.batch_count,
            stop_reason=self._stop_reason,
            checkpoint_path=checkpoint_path,
            pre_filter_stats=self._pre_filter_stats.copy(),
            pre_filter_saved_cost_usd=pre_filter_saved_cost,
        )

    # ==========================================================================
    # Phase 20: Batch API メソッド
    # ==========================================================================

    def submit_batch_job(
        self, count: int = 100, use_haiku: bool = True, person_names: list[str] | None = None
    ) -> Optional[str]:
        """
        Batch APIジョブを送信

        候補を選定し、プロンプトを生成してBatch APIに送信。
        結果は24時間以内に取得可能。

        Args:
            count: 生成する件数
            use_haiku: True=Haikuモデル使用（Phase 21統合、さらに-92%コスト）
            person_names: 特定人物名リスト（指定時はその人物のみ対象）

        Returns:
            batch_id: 送信されたバッチのID（後で結果取得に使用）
        """
        import asyncio
        from scripts.generate.mass_production.generator import GenerationInput, create_prompt_builder

        logger.info(f"Phase 20: Batch APIジョブ送信開始 (count={count})")

        if person_names:
            # 特定人物指定モード: cli.py の find_candidates_by_name を再利用
            from scripts.sage.cli import find_candidates_by_name

            all_candidates = []
            for name in person_names:
                # target_agesが指定されている場合、各年齢ごとに候補を作成
                if self.config.target_ages:
                    for age in self.config.target_ages:
                        name_candidates = find_candidates_by_name(self.orchestrator, [name], age=age)
                        all_candidates.extend(name_candidates)
                else:
                    # target_ages未指定: 動的年齢選択で候補を自動選定
                    name_candidates = find_candidates_by_name(self.orchestrator, [name])
                    all_candidates.extend(name_candidates)

            candidates = all_candidates[:count]
            logger.info(f"指定人物モード: {len(candidates)} 件の候補を選定")
        else:
            # 既存のロジック（get_recommended_candidates）
            # Phase 65: 年齢フィルタを候補選定の最初に適用（Q1ロジックをバイパス）
            # 候補選定時にフィルタを適用することで、81-90歳を直接ターゲットできる
            candidates = self.orchestrator.get_recommended_candidates(
                count=count,
                age_filter_min=self.config.age_filter_min,
                age_filter_max=self.config.age_filter_max,
                target_ages=self.config.target_ages,
            )

            if self.config.age_filter_min is not None or self.config.age_filter_max is not None:
                logger.info(
                    f"Phase 65: 年齢フィルタモード - "
                    f"{self.config.age_filter_min or 0}-{self.config.age_filter_max or 100}歳 "
                    f"→ {len(candidates)}件選定"
                )
            else:
                logger.info(f"候補 {len(candidates)} 件を選定")

        if not candidates:
            if person_names:
                logger.warning(f"指定人物の候補が見つかりませんでした: {person_names}")
            elif self.config.age_filter_min is not None or self.config.age_filter_max is not None:
                logger.warning(
                    f"年齢フィルタ範囲 {self.config.age_filter_min or 0}-{self.config.age_filter_max or 100}歳 "
                    "に該当する候補が見つかりませんでした"
                )
            else:
                logger.warning("候補が見つかりませんでした")
            return None

        # 生成前フィルタ適用
        filtered_candidates = []
        for candidate in candidates:
            # Phase 28: person_type, birth_year, death_year を渡して90歳以上の検証を可能に
            pre_candidate = PreRulesCandidate(
                person_id=candidate.person_id,
                person_name=candidate.person_name,
                age=candidate.age,
                category=candidate.category,
                person_type=candidate.person_type,
                birth_year=candidate.birth_year,
                death_year=candidate.death_year,
            )
            result = self._pre_rules.check_all(pre_candidate)
            passed = result.passed
            reason = result.reason.value if result.reason else ""
            if passed:
                filtered_candidates.append(candidate)
            else:
                self._pre_filter_stats[reason] = self._pre_filter_stats.get(reason, 0) + 1

        logger.info(f"フィルタ後 {len(filtered_candidates)} 件")

        if not filtered_candidates:
            logger.warning("フィルタ後の候補がありません")
            return None

        # Step 2.5: EPUP重複チェック（生成前の最終防御）
        # 既にマスターCSVに存在するperson_id+age組み合わせをスキップ
        duplicate_detector = DuplicateDetector()
        epup_filtered_candidates = []
        epup_skip_count = 0

        for candidate in filtered_candidates:
            pre_dup_check = duplicate_detector.check_exact_duplicate(candidate.person_id, candidate.age)
            if pre_dup_check.is_duplicate:
                logger.debug(
                    f"Step 2.5 SKIP: 既存EP {candidate.person_name} age {candidate.age} "
                    f"(EP: {pre_dup_check.most_similar_episode_id})"
                )
                epup_skip_count += 1
                continue
            epup_filtered_candidates.append(candidate)

        if epup_skip_count > 0:
            logger.info(f"Step 2.5 EPUP重複スキップ: {epup_skip_count}件")

        filtered_candidates = epup_filtered_candidates

        if not filtered_candidates:
            logger.warning("EPUP重複チェック後の候補がありません")
            return None

        logger.info(f"EPUP重複チェック後 {len(filtered_candidates)} 件")

        # プロンプト生成
        prompt_builder = create_prompt_builder(compact=True)
        batch_requests = []

        for candidate in filtered_candidates:
            gen_input = GenerationInput(
                person_id=candidate.person_id,
                person_name=candidate.person_name,
                age=candidate.age,
                category=candidate.category,
                additional_context=(
                    "重要: 以下の要素を必ず含めること:\n"
                    "- 西暦年号を2つ以上\n"
                    "- 固有名詞（人名、作品名、組織名、地名）を5つ以上\n"
                    "- 「」で囲んだ作品名・イベント名を2つ以上\n"
                    "- 数値データを3つ以上\n"
                    "- 必ず200文字以上で記述すること\n"  # Phase 22: 最小長明示
                    "抽象的な表現や推測・伝聞は禁止"
                ),
            )

            # Phase 32: 1-5歳は early_childhood スタイルを使用
            style = "early_childhood" if 1 <= candidate.age <= 5 else "factual"
            prompt = prompt_builder.build(gen_input, style=style)

            # custom_id: person_id_age でユニーク化
            # Phase 28: custom_idは英数字・アンダースコア・ハイフンのみ許可
            # 日本語person_idはハッシュ化
            safe_person_id = hashlib.md5(candidate.person_id.encode()).hexdigest()[:16]
            custom_id = f"{safe_person_id}_{candidate.age}"

            # Phase 21統合: Haikuモデル使用で追加コスト削減
            model = "claude-3-5-haiku-20241022" if use_haiku else "claude-sonnet-4-20250514"

            batch_requests.append(
                BatchRequest(
                    custom_id=custom_id,
                    person_name=candidate.person_name,
                    age=candidate.age,
                    category=candidate.category,
                    prompt=prompt,
                    model=model,
                    max_tokens=1024,
                )
            )

        logger.info(f"BatchRequest {len(batch_requests)} 件を作成")

        # Batch API送信
        processor = BatchProcessor()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            job = loop.run_until_complete(processor.submit_batch(batch_requests))
            logger.info(f"Batch APIジョブ送信成功: batch_id={job.batch_id}")

            # ジョブ情報をログに保存
            job_log_path = self.config.logs_dir if hasattr(self.config, "logs_dir") else Path("src/reports/logs")
            job_log_path = job_log_path / "batch_jobs" / f"{job.batch_id}_meta.json"
            job_log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(job_log_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "batch_id": job.batch_id,
                        "submitted_at": datetime.now().isoformat(),
                        "request_count": len(batch_requests),
                        "model": model,  # Phase 21: コスト計算用
                        "dry_run": self.config.dry_run,
                        "candidates": [
                            {
                                "custom_id": r.custom_id,
                                "person_id": candidate.person_id,  # オリジナルのperson_id
                                "person_name": candidate.person_name,
                                "age": candidate.age,
                                "category": candidate.category,
                            }
                            for candidate, r in zip(filtered_candidates, batch_requests)
                        ],
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            return job.batch_id

        except Exception as e:
            logger.error(f"Batch API送信エラー: {e}")
            raise

    def check_batch_status(self, batch_id: str) -> dict:
        """
        Batchジョブのステータスを確認

        Args:
            batch_id: バッチID

        Returns:
            dict: ステータス情報
        """
        import asyncio

        processor = BatchProcessor()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        job = loop.run_until_complete(processor.check_status(batch_id))

        return {
            "batch_id": job.batch_id,
            "status": job.status,
            "request_count": job.request_count,
            "succeeded_count": job.succeeded_count,
            "failed_count": job.failed_count,
            "expired_count": job.expired_count,
            "canceled_count": job.canceled_count,
        }

    def retrieve_batch_results(
        self, batch_id: str, wait: bool = True, write_to_csv: bool = False
    ) -> Optional[GenerationRun]:
        """
        Batch API結果を取得して処理

        Args:
            batch_id: バッチID
            wait: 完了を待機するか（最大24時間）
            write_to_csv: True=マスターCSVに書き込み（Phase 23）

        Returns:
            GenerationRun: 生成結果（orchestratorと互換）
        """
        import asyncio

        logger.info(f"Phase 20: Batch API結果取得開始 (batch_id={batch_id})")

        processor = BatchProcessor()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # ステータス確認
        job = loop.run_until_complete(processor.check_status(batch_id))

        if job.status != "ended":
            if wait:
                logger.info(f"Batch処理中... ステータス: {job.status}")
                poll_interval = 300  # 5分
                job = loop.run_until_complete(processor.wait_for_completion(batch_id, poll_interval=poll_interval))
            else:
                logger.info(f"Batch未完了: {job.status}")
                return None

        if job.status != "ended":
            logger.error(f"Batchが正常終了していません: {job.status}")
            return None

        # 結果取得
        results = loop.run_until_complete(processor.get_results(batch_id))
        logger.info(f"結果 {len(results)} 件を取得")

        # メタデータ読み込み（候補情報）
        job_log_path = Path("src/reports/logs/batch_jobs") / f"{batch_id}_meta.json"
        candidate_map = {}
        meta = {}  # Phase 21: モデル情報用
        if job_log_path.exists():
            with open(job_log_path, encoding="utf-8") as f:
                meta = json.load(f)
                for c in meta.get("candidates", []):
                    candidate_map[c["custom_id"]] = c

        # 結果をGenerationRun形式に変換
        from .adapters import Candidate, GenerationResult
        from .adapters.base import EvaluationResult

        accepted = []
        rejected = []
        rejections = []

        for result in results:
            custom_id = result.get("custom_id", "")
            candidate_info = candidate_map.get(custom_id, {})

            if result.get("result_type") != "succeeded":
                rejections.append(
                    {
                        "custom_id": custom_id,
                        "reason": "batch_error",
                        "message": result.get("error", "Unknown error"),
                    }
                )
                continue

            text = result.get("text", "")
            if not text:
                rejections.append(
                    {
                        "custom_id": custom_id,
                        "reason": "empty_response",
                        "message": "Empty response from API",
                    }
                )
                continue

            # Phase 22: 動的最小長チェック
            age = candidate_info.get("age", 30)
            category = candidate_info.get("category", "")
            min_length = self._get_min_length(age, category)

            if len(text) < min_length:
                rejections.append(
                    {
                        "custom_id": custom_id,
                        "reason": "too_short",
                        "message": f"Text too short: {len(text)} chars (min={min_length})",
                    }
                )
                rejected.append(custom_id)
                continue

            # 成功として記録
            accepted.append(
                {
                    "custom_id": custom_id,
                    "person_id": candidate_info.get("person_id", ""),  # オリジナルのperson_id
                    "person_name": candidate_info.get("person_name", ""),
                    "age": candidate_info.get("age", 0),
                    "category": candidate_info.get("category", ""),
                    "text": text,
                    "usage": result.get("usage", {}),
                }
            )

        logger.info(f"結果処理完了: accepted={len(accepted)}, rejected={len(rejected)}")

        # トークン使用量集計
        total_input = sum(r.get("usage", {}).get("input_tokens", 0) for r in accepted)
        total_output = sum(r.get("usage", {}).get("output_tokens", 0) for r in accepted)

        # Batch APIの50%割引コスト計算
        # モデル判定（メタデータから取得）
        model_used = meta.get("model", "claude-sonnet-4-20250514")
        is_haiku = "haiku" in model_used.lower()

        if is_haiku:
            # Haiku: input $0.25/1M, output $1.25/1M → Batch 50%割引
            batch_cost = (total_input * 0.125 / 1_000_000) + (total_output * 0.625 / 1_000_000)
        else:
            # Sonnet: input $3/1M, output $15/1M → Batch 50%割引
            batch_cost = (total_input * 1.5 / 1_000_000) + (total_output * 7.5 / 1_000_000)

        # 結果をファイルに保存
        result_path = Path("src/reports/logs/batch_jobs") / f"{batch_id}_processed.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "batch_id": batch_id,
                    "processed_at": datetime.now().isoformat(),
                    "accepted_count": len(accepted),
                    "rejected_count": len(rejected),
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "estimated_cost_usd": round(batch_cost, 4),
                    "accepted": accepted,
                    "rejections": rejections,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"処理結果を保存: {result_path}")
        logger.info(f"コスト: ${batch_cost:.4f} (50%割引適用)")

        # Phase 23: マスターCSV書き込み（Phase 26: モデル情報追加）
        added_count = 0
        skipped_count = 0
        if write_to_csv and accepted:
            added_count, skipped_count = self._write_accepted_episodes(accepted, batch_id, model_used=model_used)

        # GenerationRun互換形式で返す
        return GenerationRun(
            run_id=batch_id,
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            target_count=len(candidate_map),
            generated_count=len(accepted) + len(rejected),
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            results=[],  # 詳細は別ファイル参照
            rejections=rejections,
            dry_run=self.config.dry_run,
        )


def run_turbo(
    cost_limit_usd: float = 10.0,
    time_limit_minutes: int = 60,
    dry_run: bool = True,
    resume: bool = False,
    use_mock: bool = False,
) -> TurboReport:
    """
    Turboモード実行ユーティリティ関数

    Args:
        cost_limit_usd: コスト上限（USD）
        time_limit_minutes: 時間上限（分）
        dry_run: dry-runモード
        resume: チェックポイントから再開
        use_mock: モックモード

    Returns:
        TurboReport
    """
    config = TurboConfig(
        cost_limit_usd=cost_limit_usd,
        time_limit_minutes=time_limit_minutes,
        dry_run=dry_run,
        use_mock=use_mock,
    )

    engine = TurboEngine(config)

    if resume:
        engine.resume_from_checkpoint()

    return engine.run()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    dry_run = "--execute" not in sys.argv
    resume = "--resume" in sys.argv
    use_mock = "--mock" in sys.argv

    # コスト上限
    cost_limit = 10.0
    for i, arg in enumerate(sys.argv):
        if arg == "--cost-limit" and i + 1 < len(sys.argv):
            cost_limit = float(sys.argv[i + 1])

    # 時間上限
    time_limit = 60
    for i, arg in enumerate(sys.argv):
        if arg == "--time-limit" and i + 1 < len(sys.argv):
            time_limit = int(sys.argv[i + 1])

    print(f"\n{'=' * 60}")
    print("SAGE Turbo Engine")
    print(f"{'=' * 60}")
    print(f"コスト上限: ${cost_limit:.2f}")
    print(f"時間上限: {time_limit}分")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print(f"再開: {'あり' if resume else 'なし'}")
    print(f"{'=' * 60}\n")

    report = run_turbo(
        cost_limit_usd=cost_limit,
        time_limit_minutes=time_limit,
        dry_run=dry_run,
        resume=resume,
        use_mock=use_mock,
    )

    print(f"\n{'=' * 60}")
    print("実行結果")
    print(f"{'=' * 60}")
    print(f"停止理由: {report.stop_reason}")
    print(f"実行時間: {report.duration_minutes:.1f}分")
    print(f"生成数: {report.total_generated}")
    print(f"採用数: {report.total_accepted}")
    print(f"採用率: {report.acceptance_rate:.1%}")
    print(f"総コスト: ${report.total_cost_usd:.3f}")
    print(f"1件あたりコスト: ${report.cost_per_episode_usd:.4f}")
    print(f"レート制限回数: {report.rate_limit_count}")
    print(f"チェックポイント: {report.checkpoint_path}")
    # Phase 1最適化: 生成前フィルタ統計
    if report.pre_filter_stats:
        pre_filter_total = sum(report.pre_filter_stats.values())
        print("\n--- 生成前フィルタ（Phase 1最適化）---")
        print(f"事前除外件数: {pre_filter_total}")
        print(f"節約コスト: ${report.pre_filter_saved_cost_usd:.3f}")
        for reason, count in sorted(report.pre_filter_stats.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}件")
    print(f"{'=' * 60}")
