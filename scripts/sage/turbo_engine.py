"""
SAGE Turbo Engine

APIレート制限まで自動的にエピソードを生成し続けるエンジン。
"""

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

        # 開始時刻
        self._start_time: Optional[datetime] = None
        self._stop_requested = False
        self._stop_reason = ""

        # シグナルハンドラ設定
        self._setup_signal_handlers()

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
        """次のバッチの候補を取得（Phase 1最適化版 + H4キャッシュ最適化）"""
        # 処理済みを除外して候補を取得（余裕を持って3倍取得）
        all_candidates = self.orchestrator.get_recommended_candidates(
            self.state.current_batch_size * 3
        )

        # 処理済みを除外 + 生成前フィルタ適用
        processed_set = set(self.state.candidates_processed)
        filtered_candidates = []

        for c in all_candidates:
            key = f"{c.person_id}:{c.age}"
            if key in processed_set:
                continue

            # 【Phase 1最適化】生成前ルールチェック（LLMコスト0で棄却予測）
            # 型変換（adapters.base.Candidate → pre_generation_rules.Candidate）
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
                continue  # LLMコストなしでスキップ

            filtered_candidates.append(c)

        # 【H4最適化】person_id順にソート（Prompt Caching効率化）
        # 同一人物の複数年齢を連続処理することでキャッシュヒット率向上
        filtered_candidates.sort(key=lambda x: (x.person_id, x.age))

        # バッチサイズ分を取得
        candidates = filtered_candidates[: self.state.current_batch_size]

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
            logger.debug(f"コスト取得エラー: {e}")

        # 処理済みを記録
        for result in run.results:
            key = f"{result.candidate.person_id}:{result.candidate.age}"
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
        """チェックポイントから再開"""
        if not CHECKPOINT_PATH.exists():
            logger.warning("チェックポイントが見つかりません")
            return False

        try:
            data = json.loads(CHECKPOINT_PATH.read_text())
            self.state = TurboState.from_dict(data["state"])
            logger.info(f"チェックポイントから再開: {self.state.total_generated}件生成済み")
            return True
        except Exception as e:
            logger.error(f"チェックポイント読み込みエラー: {e}")
            return False

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
        print(f"\n--- 生成前フィルタ（Phase 1最適化）---")
        print(f"事前除外件数: {pre_filter_total}")
        print(f"節約コスト: ${report.pre_filter_saved_cost_usd:.3f}")
        for reason, count in sorted(report.pre_filter_stats.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}件")
    print(f"{'=' * 60}")
