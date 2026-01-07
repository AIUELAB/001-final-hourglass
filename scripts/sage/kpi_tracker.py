"""
KPI Tracker - SAGE運用監視とレポート生成

SAGE vNext: 週次レポート自動生成、コストダッシュボード、異常検知。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .config import CACHE_DIR, LOGS_DIR, MASTER_CSV, QUALITY_THRESHOLDS
from .inventory_manager import InventoryManager


# ==============================================================================
# KPI定義
# ==============================================================================


@dataclass
class KPITargets:
    """KPI目標値"""

    # Primary KPIs
    llm_calls_per_episode: float = 1.3  # LLM呼び出し/エピソード
    tokens_per_episode: int = 1500  # トークン/エピソード
    acceptance_rate: float = 0.90  # 採用率90%

    # Secondary KPIs
    avg_super_total: float = 400000  # 平均super_total_score
    retry_rate: float = 0.20  # リトライ率20%以下
    fallback_rate: float = 0.10  # フォールバック率10%以下

    # Diversity KPIs
    category_gini: float = 0.30  # カテゴリGini係数
    age_std: float = 15.0  # 年齢標準偏差


@dataclass
class KPISnapshot:
    """KPIスナップショット"""

    timestamp: str
    period_start: str
    period_end: str

    # Primary
    total_episodes: int = 0
    new_episodes: int = 0
    llm_calls: int = 0
    total_tokens: int = 0
    acceptance_rate: float = 0.0

    # Secondary
    avg_super_total: float = 0.0
    retry_count: int = 0
    fallback_count: int = 0

    # Diversity
    category_distribution: dict = field(default_factory=dict)
    age_distribution: dict = field(default_factory=dict)

    # Cost
    estimated_cost_usd: float = 0.0

    # Inventory
    achieved_ages: int = 0
    total_upper_episodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_episodes": self.total_episodes,
            "new_episodes": self.new_episodes,
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "acceptance_rate": round(self.acceptance_rate, 3),
            "avg_super_total": round(self.avg_super_total, 0),
            "retry_count": self.retry_count,
            "fallback_count": self.fallback_count,
            "category_distribution": self.category_distribution,
            "age_distribution": self.age_distribution,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "achieved_ages": self.achieved_ages,
            "total_upper_episodes": self.total_upper_episodes,
        }


@dataclass
class KPIAlert:
    """KPIアラート"""

    metric: str
    current_value: float
    target_value: float
    severity: str  # "warning", "critical"
    message: str


# ==============================================================================
# KPITracker
# ==============================================================================


class KPITracker:
    """
    KPIトラッカー

    機能:
    - 週次KPIスナップショット生成
    - 目標値との比較
    - 異常検知アラート
    - レポート生成
    """

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        logs_dir: Path = LOGS_DIR,
        cache_dir: Path = CACHE_DIR,
        targets: Optional[KPITargets] = None,
    ):
        self.master_csv = master_csv
        self.logs_dir = logs_dir
        self.cache_dir = cache_dir
        self.targets = targets or KPITargets()
        self._history_file = cache_dir / "kpi_history.json"
        self._inventory = InventoryManager(master_csv=master_csv, cache_dir=cache_dir)

    def _load_master(self) -> pd.DataFrame:
        """マスターCSV読み込み"""
        return pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)

    def _load_history(self) -> list[dict]:
        """履歴読み込み"""
        if self._history_file.exists():
            with open(self._history_file, encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_history(self, history: list[dict]) -> None:
        """履歴保存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self._history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def take_snapshot(self, period_days: int = 7) -> KPISnapshot:
        """
        KPIスナップショットを取得

        Args:
            period_days: 集計期間（デフォルト7日）

        Returns:
            KPISnapshot: スナップショット
        """
        now = datetime.now()
        period_start = now - timedelta(days=period_days)

        df = self._load_master()

        # 期間内の新規エピソード
        if "generation_timestamp" in df.columns:
            df["gen_time"] = pd.to_datetime(df["generation_timestamp"], errors="coerce")
            new_df = df[df["gen_time"] >= period_start]
        else:
            new_df = pd.DataFrame()

        # Inventory情報
        self._inventory.refresh()
        inv_summary = self._inventory.get_summary()

        # カテゴリ分布
        cat_dist = df["category"].value_counts().to_dict() if "category" in df.columns else {}

        # 年齢分布（10歳刻み）
        if "age" in df.columns:
            df["age_group"] = (df["age"] // 10 * 10).astype(str) + "s"
            age_dist = df["age_group"].value_counts().to_dict()
        else:
            age_dist = {}

        # 平均super_total_score
        if "super_total_score" in df.columns:
            avg_super = df["super_total_score"].mean()
        else:
            avg_super = 0.0

        # ログからLLM呼び出し数・トークン数を集計
        llm_calls, total_tokens, retry_count, fallback_count, estimated_cost = self._aggregate_logs(period_start)

        # 採用率（新規エピソード数 / LLM呼び出し数）
        acceptance_rate = len(new_df) / llm_calls if llm_calls > 0 else 0.0

        snapshot = KPISnapshot(
            timestamp=now.isoformat(),
            period_start=period_start.isoformat(),
            period_end=now.isoformat(),
            total_episodes=len(df),
            new_episodes=len(new_df),
            llm_calls=llm_calls,
            total_tokens=total_tokens,
            acceptance_rate=acceptance_rate,
            avg_super_total=avg_super,
            retry_count=retry_count,
            fallback_count=fallback_count,
            category_distribution=cat_dist,
            age_distribution=age_dist,
            estimated_cost_usd=estimated_cost,
            achieved_ages=inv_summary.get("achieved_ages", 0),
            total_upper_episodes=inv_summary.get("total_upper_episodes", 0),
        )

        return snapshot

    def _aggregate_logs(self, since: datetime) -> tuple[int, int, int, int, float]:
        """
        ログからメトリクスを集計

        Returns:
            tuple: (llm_calls, total_tokens, retry_count, fallback_count, estimated_cost)
        """
        llm_calls = 0
        total_tokens = 0
        retry_count = 0
        fallback_count = 0
        estimated_cost = 0.0

        # generation_runsログを集計
        log_pattern = self.logs_dir / "generation_run_*.json"
        for log_file in self.logs_dir.glob("generation_run_*.json"):
            try:
                with open(log_file, encoding="utf-8") as f:
                    data = json.load(f)

                # タイムスタンプチェック
                started = data.get("started_at", "")
                if started:
                    log_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    if log_time.replace(tzinfo=None) < since:
                        continue

                # メトリクス集計
                llm_calls += data.get("generated_count", 0)
                retry_count += sum(1 for r in data.get("results", []) if r.get("retry_count", 0) > 0)

                # トークン集計
                for result in data.get("results", []):
                    if "token_usage" in result:
                        usage = result["token_usage"]
                        total_tokens += usage.get("total_tokens", 0)
                        estimated_cost += usage.get("estimated_cost_usd", 0.0)

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return llm_calls, total_tokens, retry_count, fallback_count, estimated_cost

    def check_alerts(self, snapshot: KPISnapshot) -> list[KPIAlert]:
        """
        アラートチェック

        Args:
            snapshot: KPIスナップショット

        Returns:
            list[KPIAlert]: アラートリスト
        """
        alerts = []

        # 採用率チェック
        if snapshot.acceptance_rate < self.targets.acceptance_rate * 0.8:
            alerts.append(
                KPIAlert(
                    metric="acceptance_rate",
                    current_value=snapshot.acceptance_rate,
                    target_value=self.targets.acceptance_rate,
                    severity="critical",
                    message=f"採用率が目標の80%を下回っています: {snapshot.acceptance_rate:.1%} < {self.targets.acceptance_rate:.1%}",
                )
            )
        elif snapshot.acceptance_rate < self.targets.acceptance_rate:
            alerts.append(
                KPIAlert(
                    metric="acceptance_rate",
                    current_value=snapshot.acceptance_rate,
                    target_value=self.targets.acceptance_rate,
                    severity="warning",
                    message=f"採用率が目標を下回っています: {snapshot.acceptance_rate:.1%} < {self.targets.acceptance_rate:.1%}",
                )
            )

        # 平均スコアチェック
        if snapshot.avg_super_total < self.targets.avg_super_total * 0.8:
            alerts.append(
                KPIAlert(
                    metric="avg_super_total",
                    current_value=snapshot.avg_super_total,
                    target_value=self.targets.avg_super_total,
                    severity="critical",
                    message=f"平均スコアが目標の80%を下回っています: {snapshot.avg_super_total:.0f} < {self.targets.avg_super_total:.0f}",
                )
            )

        # リトライ率チェック
        if snapshot.llm_calls > 0:
            retry_rate = snapshot.retry_count / snapshot.llm_calls
            if retry_rate > self.targets.retry_rate:
                alerts.append(
                    KPIAlert(
                        metric="retry_rate",
                        current_value=retry_rate,
                        target_value=self.targets.retry_rate,
                        severity="warning",
                        message=f"リトライ率が目標を超えています: {retry_rate:.1%} > {self.targets.retry_rate:.1%}",
                    )
                )

        return alerts

    def generate_report(self, snapshot: KPISnapshot) -> str:
        """
        週次レポート生成

        Args:
            snapshot: KPIスナップショット

        Returns:
            str: Markdownレポート
        """
        alerts = self.check_alerts(snapshot)

        report = f"""# SAGE 週次KPIレポート

生成日時: {snapshot.timestamp}
集計期間: {snapshot.period_start[:10]} 〜 {snapshot.period_end[:10]}

## サマリー

| 指標 | 値 | 目標 | 状態 |
|------|-----|------|------|
| 総エピソード数 | {snapshot.total_episodes:,} | - | - |
| 新規エピソード | {snapshot.new_episodes:,} | - | - |
| 採用率 | {snapshot.acceptance_rate:.1%} | {self.targets.acceptance_rate:.1%} | {'✅' if snapshot.acceptance_rate >= self.targets.acceptance_rate else '⚠️'} |
| 平均スコア | {snapshot.avg_super_total:,.0f} | {self.targets.avg_super_total:,.0f} | {'✅' if snapshot.avg_super_total >= self.targets.avg_super_total else '⚠️'} |
| 推定コスト | ${snapshot.estimated_cost_usd:.4f} | - | - |

## 在庫状況

| 指標 | 値 |
|------|-----|
| 365本達成年齢数 | {snapshot.achieved_ages} / 121 |
| 上位レベル総数 | {snapshot.total_upper_episodes:,} |

## カテゴリ分布

| カテゴリ | エピソード数 |
|---------|-------------|
"""
        for cat, count in sorted(snapshot.category_distribution.items(), key=lambda x: -x[1])[:10]:
            report += f"| {cat} | {count:,} |\n"

        report += """
## 年齢分布

| 年齢帯 | エピソード数 |
|--------|-------------|
"""
        for age, count in sorted(snapshot.age_distribution.items()):
            report += f"| {age} | {count:,} |\n"

        if alerts:
            report += "\n## アラート\n\n"
            for alert in alerts:
                icon = "🚨" if alert.severity == "critical" else "⚠️"
                report += f"- {icon} **{alert.metric}**: {alert.message}\n"

        report += """
---
*Generated by SAGE KPI Tracker*
"""
        return report

    def save_snapshot(self, snapshot: KPISnapshot) -> Path:
        """
        スナップショットを保存

        Args:
            snapshot: KPIスナップショット

        Returns:
            Path: 保存先パス
        """
        # 履歴に追加
        history = self._load_history()
        history.append(snapshot.to_dict())
        self._save_history(history)

        # レポートも保存
        report = self.generate_report(snapshot)
        report_path = self.logs_dir / f"kpi_report_{datetime.now().strftime('%Y%m%d')}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        return report_path


# ==============================================================================
# 便利関数
# ==============================================================================


def generate_weekly_report() -> str:
    """週次レポートを生成して保存"""
    tracker = KPITracker()
    snapshot = tracker.take_snapshot(period_days=7)
    report_path = tracker.save_snapshot(snapshot)
    return str(report_path)


def check_kpi_alerts() -> list[dict]:
    """KPIアラートをチェック"""
    tracker = KPITracker()
    snapshot = tracker.take_snapshot(period_days=1)
    alerts = tracker.check_alerts(snapshot)
    return [
        {
            "metric": a.metric,
            "current": a.current_value,
            "target": a.target_value,
            "severity": a.severity,
            "message": a.message,
        }
        for a in alerts
    ]


if __name__ == "__main__":
    # 週次レポート生成
    path = generate_weekly_report()
    print(f"Report saved to: {path}")

    # アラートチェック
    alerts = check_kpi_alerts()
    if alerts:
        print("\nAlerts:")
        for a in alerts:
            print(f"  [{a['severity']}] {a['message']}")
    else:
        print("\nNo alerts.")
