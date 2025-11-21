#!/usr/bin/env python3
"""
SuperClaude Metrics Tracking System
効果測定の自動化と分析機能
"""

import json
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TaskMetrics:
    """タスクの実行メトリクス"""

    task_name: str
    start_time: float
    end_time: float = 0.0
    success: bool = False
    error: Optional[str] = None
    tokens_used: int = 0
    parallel_count: int = 1
    tool_calls: List[str] = field(default_factory=list)
    file_operations: Dict[str, int] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """実行時間（秒）"""
        return self.end_time - self.start_time if self.end_time else 0

    @property
    def efficiency_score(self) -> float:
        """効率性スコア（並列処理とトークン使用量から算出）"""
        if self.tokens_used == 0:
            return 0.0

        parallel_bonus = min(self.parallel_count * 0.2, 1.0)
        token_efficiency = min(1000 / self.tokens_used, 1.0) if self.tokens_used > 0 else 0
        time_efficiency = min(60 / self.duration, 1.0) if self.duration > 0 else 1.0

        return (parallel_bonus + token_efficiency + time_efficiency) / 3 * 100


@dataclass
class SessionMetrics:
    """セッション全体のメトリクス"""

    session_id: str
    start_time: str
    end_time: Optional[str] = None
    tasks: List[TaskMetrics] = field(default_factory=list)
    total_tokens: int = 0
    mode_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    flag_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    mcp_server_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_count: int = 0
    success_rate: float = 0.0

    def calculate_summary(self) -> Dict[str, Any]:
        """セッションサマリーを計算"""
        if not self.tasks:
            return {}

        successful_tasks = [t for t in self.tasks if t.success]
        failed_tasks = [t for t in self.tasks if not t.success]

        durations = [t.duration for t in self.tasks if t.duration > 0]
        efficiency_scores = [t.efficiency_score for t in self.tasks]

        return {
            "total_tasks": len(self.tasks),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": len(successful_tasks) / len(self.tasks) * 100 if self.tasks else 0,
            "total_duration": sum(durations),
            "avg_duration": statistics.mean(durations) if durations else 0,
            "total_tokens": self.total_tokens,
            "avg_efficiency": statistics.mean(efficiency_scores) if efficiency_scores else 0,
            "most_used_mode": max(self.mode_usage.items(), key=lambda x: x[1])[0] if self.mode_usage else None,
            "most_used_mcp": max(self.mcp_server_usage.items(), key=lambda x: x[1])[0]
            if self.mcp_server_usage
            else None,
            "parallel_tasks_ratio": sum(1 for t in self.tasks if t.parallel_count > 1) / len(self.tasks) * 100
            if self.tasks
            else 0,
        }


class MetricsTracker:
    """メトリクス追跡システム"""

    def __init__(self, metrics_dir: str = "~/.claude/metrics"):
        self.metrics_dir = Path(metrics_dir).expanduser()
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[SessionMetrics] = None
        self.current_task: Optional[TaskMetrics] = None
        self.load_historical_metrics()

    def load_historical_metrics(self):
        """過去のメトリクスを読み込み"""
        self.historical_metrics = []
        metrics_files = sorted(self.metrics_dir.glob("session_*.json"))

        for file_path in metrics_files[-100:]:  # 最新100セッション
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.historical_metrics.append(json.load(f))
            except Exception:
                continue

    def start_session(self, session_id: Optional[str] = None) -> str:
        """新しいセッションを開始"""
        if not session_id:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        self.current_session = SessionMetrics(session_id=session_id, start_time=datetime.now().isoformat())
        return session_id

    def start_task(self, task_name: str, parallel_count: int = 1) -> None:
        """タスクの追跡を開始"""
        self.current_task = TaskMetrics(task_name=task_name, start_time=time.time(), parallel_count=parallel_count)

    def end_task(self, success: bool = True, error: Optional[str] = None, tokens_used: int = 0) -> None:
        """タスクを終了"""
        if not self.current_task:
            return

        self.current_task.end_time = time.time()
        self.current_task.success = success
        self.current_task.error = error
        self.current_task.tokens_used = tokens_used

        if self.current_session:
            self.current_session.tasks.append(self.current_task)
            self.current_session.total_tokens += tokens_used
            if not success:
                self.current_session.errors_count += 1

        self.current_task = None

    def track_tool_usage(self, tool_name: str) -> None:
        """ツール使用を記録"""
        if self.current_task:
            self.current_task.tool_calls.append(tool_name)

        # MCPサーバー使用を追跡
        if self.current_session and tool_name.startswith("mcp__"):
            server_name = tool_name.split("__")[1] if "__" in tool_name else tool_name
            self.current_session.mcp_server_usage[server_name] += 1

    def track_mode_usage(self, mode: str) -> None:
        """モード使用を記録"""
        if self.current_session:
            self.current_session.mode_usage[mode] += 1

    def track_flag_usage(self, flag: str) -> None:
        """フラグ使用を記録"""
        if self.current_session:
            self.current_session.flag_usage[flag] += 1

    def track_file_operation(self, operation: str, file_path: str) -> None:
        """ファイル操作を記録"""
        if self.current_task:
            if operation not in self.current_task.file_operations:
                self.current_task.file_operations[operation] = 0
            self.current_task.file_operations[operation] += 1

    def end_session(self) -> Dict[str, Any]:
        """セッションを終了してサマリーを返す"""
        if not self.current_session:
            return {}

        self.current_session.end_time = datetime.now().isoformat()
        summary = self.current_session.calculate_summary()

        # セッションデータを保存
        session_file = self.metrics_dir / f"{self.current_session.session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.current_session), f, indent=2, ensure_ascii=False)

        # 集計メトリクスを更新
        self.update_aggregate_metrics()

        self.current_session = None
        return summary

    def update_aggregate_metrics(self) -> None:
        """集計メトリクスを更新"""
        aggregate_file = self.metrics_dir / "aggregate_metrics.json"

        # 既存の集計データを読み込み
        if aggregate_file.exists():
            with open(aggregate_file, "r", encoding="utf-8") as f:
                aggregate = json.load(f)
        else:
            aggregate = {
                "total_sessions": 0,
                "total_tasks": 0,
                "total_tokens": 0,
                "avg_success_rate": 0,
                "mode_usage": {},
                "mcp_server_usage": {},
                "efficiency_trend": [],
            }

        # 最新セッションで更新
        if self.current_session:
            summary = self.current_session.calculate_summary()
            aggregate["total_sessions"] += 1
            aggregate["total_tasks"] += summary.get("total_tasks", 0)
            aggregate["total_tokens"] += self.current_session.total_tokens

            # 成功率の移動平均
            prev_rate = aggregate["avg_success_rate"]
            new_rate = summary.get("success_rate", 0)
            aggregate["avg_success_rate"] = prev_rate * 0.9 + new_rate * 0.1

            # 効率性トレンド（最新20セッション）
            aggregate["efficiency_trend"].append(
                {
                    "session": self.current_session.session_id,
                    "efficiency": summary.get("avg_efficiency", 0),
                    "timestamp": self.current_session.start_time,
                }
            )
            aggregate["efficiency_trend"] = aggregate["efficiency_trend"][-20:]

        # 保存
        with open(aggregate_file, "w", encoding="utf-8") as f:
            json.dump(aggregate, f, indent=2, ensure_ascii=False)

    def get_performance_insights(self) -> Dict[str, Any]:
        """パフォーマンスインサイトを取得"""
        aggregate_file = self.metrics_dir / "aggregate_metrics.json"
        if not aggregate_file.exists():
            return {"status": "No data available"}

        with open(aggregate_file, "r", encoding="utf-8") as f:
            aggregate = json.load(f)

        insights = {
            "overview": {
                "total_sessions": aggregate.get("total_sessions", 0),
                "total_tasks": aggregate.get("total_tasks", 0),
                "avg_success_rate": f"{aggregate.get('avg_success_rate', 0):.1f}%",
                "total_tokens_saved": aggregate.get("total_tokens", 0) * 0.3,  # 30%削減想定
            },
            "efficiency_trend": aggregate.get("efficiency_trend", []),
            "recommendations": [],
        }

        # 推奨事項を生成
        if aggregate.get("avg_success_rate", 0) < 80:
            insights["recommendations"].append("成功率が低いです。エラー処理の改善を検討してください")

        if aggregate.get("efficiency_trend", []):
            recent_efficiency = [e["efficiency"] for e in aggregate["efficiency_trend"][-5:]]
            if recent_efficiency and statistics.mean(recent_efficiency) < 50:
                insights["recommendations"].append("効率性が低下しています。並列処理の活用を増やしてください")

        # 最も使用されているMCPサーバー
        if aggregate.get("mcp_server_usage"):
            top_mcp = max(aggregate["mcp_server_usage"].items(), key=lambda x: x[1])
            insights["most_used_mcp"] = {"server": top_mcp[0], "count": top_mcp[1]}

        return insights


# グローバルインスタンス
metrics_tracker = MetricsTracker()


def track_performance(func):
    """パフォーマンス追跡デコレータ"""

    def wrapper(*args, **kwargs):
        task_name = func.__name__
        metrics_tracker.start_task(task_name)

        try:
            result = func(*args, **kwargs)
            metrics_tracker.end_task(success=True)
            return result
        except Exception as e:
            metrics_tracker.end_task(success=False, error=str(e))
            raise

    return wrapper


if __name__ == "__main__":
    # テスト実行
    tracker = MetricsTracker()
    tracker.start_session()

    # タスク実行をシミュレート
    tracker.start_task("test_task", parallel_count=3)
    tracker.track_tool_usage("mcp__github__get_issue")
    tracker.track_mode_usage("orchestration")
    time.sleep(0.1)
    tracker.end_task(success=True, tokens_used=150)

    # セッション終了
    summary = tracker.end_session()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # インサイト取得
    insights = tracker.get_performance_insights()
    print("\n=== Performance Insights ===")
    print(json.dumps(insights, indent=2, ensure_ascii=False))
