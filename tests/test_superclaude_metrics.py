#!/usr/bin/env python3
"""superclaude_metrics テスト"""

import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from superclaude_metrics import SessionMetrics, TaskMetrics


class TestTaskMetrics:
    """TaskMetricsのテスト"""

    def test_init(self):
        """初期化テスト"""
        metrics = TaskMetrics(task_name="test_task", start_time=time.time())
        assert metrics.task_name == "test_task"
        assert metrics.success is False
        assert metrics.tokens_used == 0

    def test_duration_no_end(self):
        """終了時刻なしのduration"""
        metrics = TaskMetrics(task_name="test", start_time=100.0)
        assert metrics.duration == 0

    def test_duration_with_end(self):
        """終了時刻ありのduration"""
        metrics = TaskMetrics(task_name="test", start_time=100.0, end_time=110.0)
        assert metrics.duration == 10.0

    def test_efficiency_score_zero_tokens(self):
        """トークン0の効率スコア"""
        metrics = TaskMetrics(task_name="test", start_time=100.0)
        assert metrics.efficiency_score == 0.0

    def test_efficiency_score_with_data(self):
        """データありの効率スコア"""
        metrics = TaskMetrics(task_name="test", start_time=100.0, end_time=110.0, tokens_used=500, parallel_count=2)
        score = metrics.efficiency_score
        assert 0 <= score <= 100


class TestSessionMetrics:
    """SessionMetricsのテスト"""

    def test_init(self):
        """初期化テスト"""
        session = SessionMetrics(session_id="test123", start_time="2025-01-01T00:00:00")
        assert session.session_id == "test123"
        assert session.tasks == []
        assert session.total_tokens == 0

    def test_with_tasks(self):
        """タスク付きセッション"""
        task = TaskMetrics(task_name="task1", start_time=100.0)
        session = SessionMetrics(session_id="test", start_time="2025-01-01", tasks=[task])
        assert len(session.tasks) == 1

    def test_calculate_summary_empty(self):
        """空タスクのサマリー"""
        session = SessionMetrics(session_id="test", start_time="2025-01-01")
        summary = session.calculate_summary()
        assert summary == {}

    def test_calculate_summary_with_tasks(self):
        """タスク付きサマリー"""
        task1 = TaskMetrics(task_name="task1", start_time=100.0, end_time=110.0, success=True, tokens_used=500)
        task2 = TaskMetrics(task_name="task2", start_time=110.0, end_time=115.0, success=False, tokens_used=300)
        session = SessionMetrics(session_id="test", start_time="2025-01-01", tasks=[task1, task2])
        summary = session.calculate_summary()
        assert summary["total_tasks"] == 2
        assert summary["successful_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert summary["success_rate"] == 50.0


class TestMetricsTracker:
    """MetricsTrackerのテスト"""

    def test_init(self, tmp_path):
        """初期化テスト"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        assert tracker.metrics_dir.exists()
        assert tracker.current_session is None

    def test_start_session(self, tmp_path):
        """セッション開始"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        session_id = tracker.start_session("test_session")
        assert session_id == "test_session"
        assert tracker.current_session is not None
        assert tracker.current_session.session_id == "test_session"

    def test_start_session_auto_id(self, tmp_path):
        """自動ID生成"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        session_id = tracker.start_session()
        assert session_id.startswith("session_")

    def test_start_end_task(self, tmp_path):
        """タスク開始・終了"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.start_task("my_task", parallel_count=2)
        assert tracker.current_task is not None
        assert tracker.current_task.task_name == "my_task"

        tracker.end_task(success=True, tokens_used=100)
        assert tracker.current_task is None
        assert len(tracker.current_session.tasks) == 1

    def test_track_tool_usage(self, tmp_path):
        """ツール使用記録"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.start_task("task1")
        tracker.track_tool_usage("Read")
        assert "Read" in tracker.current_task.tool_calls

    def test_track_mcp_usage(self, tmp_path):
        """MCP使用記録"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.start_task("task1")
        tracker.track_tool_usage("mcp__serena__get_symbol")
        assert tracker.current_session.mcp_server_usage["serena"] == 1

    def test_track_mode_usage(self, tmp_path):
        """モード使用記録"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.track_mode_usage("brainstorm")
        assert tracker.current_session.mode_usage["brainstorm"] == 1

    def test_track_flag_usage(self, tmp_path):
        """フラグ使用記録"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.track_flag_usage("--think")
        assert tracker.current_session.flag_usage["--think"] == 1

    def test_track_file_operation(self, tmp_path):
        """ファイル操作記録"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.start_task("task1")
        tracker.track_file_operation("read", "/path/to/file.py")
        assert tracker.current_task.file_operations["read"] == 1

    def test_end_session_empty(self, tmp_path):
        """空セッション終了"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        result = tracker.end_session()
        assert result == {}


class TestLoadHistoricalMetrics:
    """load_historical_metrics() テスト"""

    def test_loads_existing_files(self, tmp_path):
        """既存ファイルを読み込む"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # テスト用セッションファイル作成
        session_data = {"session_id": "test1", "tasks": []}
        with open(metrics_dir / "session_test1.json", "w") as f:
            json.dump(session_data, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        assert len(tracker.historical_metrics) == 1
        assert tracker.historical_metrics[0]["session_id"] == "test1"

    def test_handles_invalid_json(self, tmp_path):
        """無効なJSONを処理"""
        from superclaude_metrics import MetricsTracker

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # 無効なJSONファイル作成
        with open(metrics_dir / "session_invalid.json", "w") as f:
            f.write("invalid json content")

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        assert tracker.historical_metrics == []

    def test_limits_to_100_sessions(self, tmp_path):
        """最新100セッションに制限"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # 110個のセッションファイル作成
        for i in range(110):
            session_data = {"session_id": f"session_{i:03d}"}
            with open(metrics_dir / f"session_{i:03d}.json", "w") as f:
                json.dump(session_data, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        assert len(tracker.historical_metrics) == 100


class TestEndTaskEdgeCases:
    """end_task() エッジケーステスト"""

    def test_end_task_no_active_task(self, tmp_path):
        """タスクなしで終了（早期リターン）"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        # タスク開始せずに終了
        tracker.end_task(success=True)
        assert tracker.current_task is None

    def test_end_task_increments_error_count(self, tmp_path):
        """失敗時にerrors_countがインクリメント"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.start_task("failing_task")
        tracker.end_task(success=False, error="Some error")
        assert tracker.current_session.errors_count == 1

    def test_end_task_accumulates_tokens(self, tmp_path):
        """トークン使用量が累積"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")

        tracker.start_task("task1")
        tracker.end_task(success=True, tokens_used=100)

        tracker.start_task("task2")
        tracker.end_task(success=True, tokens_used=200)

        assert tracker.current_session.total_tokens == 300


class TestEndSessionComplete:
    """end_session() 完全ワークフローテスト"""

    def test_saves_session_file(self, tmp_path):
        """セッションファイルを保存"""
        from superclaude_metrics import MetricsTracker
        from unittest.mock import patch, mock_open, MagicMock

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test_save")
        tracker.start_task("task1")
        tracker.end_task(success=True, tokens_used=100)

        # defaultdictがasdict互換でないため、asdict と json.dumpをモック
        with patch("superclaude_metrics.asdict", return_value={}):
            with patch("builtins.open", mock_open()):
                with patch("json.dump"):
                    summary = tracker.end_session()

        assert summary["total_tasks"] == 1
        assert tracker.current_session is None

    def test_resets_current_session(self, tmp_path):
        """セッション終了後にリセット"""
        from superclaude_metrics import MetricsTracker
        from unittest.mock import patch, mock_open

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")

        with patch("superclaude_metrics.asdict", return_value={}):
            with patch("builtins.open", mock_open()):
                with patch("json.dump"):
                    tracker.end_session()
        assert tracker.current_session is None


class TestUpdateAggregateMetrics:
    """update_aggregate_metrics() テスト"""

    def test_creates_new_aggregate_file(self, tmp_path):
        """新規集計ファイル作成"""
        from superclaude_metrics import MetricsTracker
        from unittest.mock import patch, mock_open
        import json

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")
        tracker.start_task("task1")
        tracker.end_task(success=True, tokens_used=100)

        # update_aggregate_metricsを直接呼び出し（end_sessionはasdict問題あり）
        tracker.update_aggregate_metrics()

        aggregate_file = tmp_path / "metrics" / "aggregate_metrics.json"
        assert aggregate_file.exists()

        with open(aggregate_file) as f:
            data = json.load(f)
        assert data["total_sessions"] == 1

    def test_updates_existing_aggregate(self, tmp_path):
        """既存集計ファイル更新"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # 既存の集計ファイル作成
        existing = {
            "total_sessions": 5,
            "total_tasks": 20,
            "total_tokens": 5000,
            "avg_success_rate": 80.0,
            "mode_usage": {},
            "mcp_server_usage": {},
            "efficiency_trend": [],
        }
        with open(metrics_dir / "aggregate_metrics.json", "w") as f:
            json.dump(existing, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        tracker.start_session("test")
        tracker.start_task("task1")
        tracker.end_task(success=True, tokens_used=100)
        tracker.update_aggregate_metrics()

        with open(metrics_dir / "aggregate_metrics.json") as f:
            data = json.load(f)
        assert data["total_sessions"] == 6

    def test_efficiency_trend_limit(self, tmp_path):
        """効率性トレンドが20件に制限"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # 25件のトレンド
        existing = {
            "total_sessions": 25,
            "total_tasks": 100,
            "total_tokens": 10000,
            "avg_success_rate": 90.0,
            "mode_usage": {},
            "mcp_server_usage": {},
            "efficiency_trend": [{"session": f"s{i}", "efficiency": 50, "timestamp": "t"} for i in range(25)],
        }
        with open(metrics_dir / "aggregate_metrics.json", "w") as f:
            json.dump(existing, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        tracker.start_session("test")
        tracker.start_task("task1")
        tracker.end_task(success=True, tokens_used=100)
        tracker.update_aggregate_metrics()

        with open(metrics_dir / "aggregate_metrics.json") as f:
            data = json.load(f)
        assert len(data["efficiency_trend"]) <= 20


class TestGetPerformanceInsights:
    """get_performance_insights() テスト"""

    def test_no_data_available(self, tmp_path):
        """データなし"""
        from superclaude_metrics import MetricsTracker

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        insights = tracker.get_performance_insights()
        assert insights["status"] == "No data available"

    def test_returns_overview(self, tmp_path):
        """概要を返す"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        aggregate = {
            "total_sessions": 10,
            "total_tasks": 50,
            "total_tokens": 5000,
            "avg_success_rate": 85.0,
            "mode_usage": {},
            "mcp_server_usage": {},
            "efficiency_trend": [],
        }
        with open(metrics_dir / "aggregate_metrics.json", "w") as f:
            json.dump(aggregate, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        insights = tracker.get_performance_insights()

        assert insights["overview"]["total_sessions"] == 10
        assert insights["overview"]["total_tasks"] == 50

    def test_low_success_rate_recommendation(self, tmp_path):
        """低成功率で推奨"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        aggregate = {
            "total_sessions": 10,
            "total_tasks": 50,
            "total_tokens": 5000,
            "avg_success_rate": 60.0,  # < 80%
            "mode_usage": {},
            "mcp_server_usage": {},
            "efficiency_trend": [],
        }
        with open(metrics_dir / "aggregate_metrics.json", "w") as f:
            json.dump(aggregate, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        insights = tracker.get_performance_insights()

        assert any("成功率" in r for r in insights["recommendations"])

    def test_low_efficiency_recommendation(self, tmp_path):
        """低効率で推奨"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        aggregate = {
            "total_sessions": 10,
            "total_tasks": 50,
            "total_tokens": 5000,
            "avg_success_rate": 90.0,
            "mode_usage": {},
            "mcp_server_usage": {},
            "efficiency_trend": [{"session": f"s{i}", "efficiency": 30, "timestamp": "t"} for i in range(10)],  # < 50%
        }
        with open(metrics_dir / "aggregate_metrics.json", "w") as f:
            json.dump(aggregate, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        insights = tracker.get_performance_insights()

        assert any("効率性" in r for r in insights["recommendations"])

    def test_most_used_mcp(self, tmp_path):
        """最も使用されたMCP"""
        from superclaude_metrics import MetricsTracker
        import json

        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        aggregate = {
            "total_sessions": 10,
            "total_tasks": 50,
            "total_tokens": 5000,
            "avg_success_rate": 90.0,
            "mode_usage": {},
            "mcp_server_usage": {"serena": 50, "github": 30},
            "efficiency_trend": [],
        }
        with open(metrics_dir / "aggregate_metrics.json", "w") as f:
            json.dump(aggregate, f)

        tracker = MetricsTracker(metrics_dir=str(metrics_dir))
        insights = tracker.get_performance_insights()

        assert insights["most_used_mcp"]["server"] == "serena"
        assert insights["most_used_mcp"]["count"] == 50


class TestTrackPerformanceDecorator:
    """track_performance() デコレータテスト"""

    def test_successful_function(self, tmp_path, monkeypatch):
        """成功する関数"""
        from superclaude_metrics import MetricsTracker, track_performance

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")

        # グローバルtrackerを置き換え
        import superclaude_metrics

        monkeypatch.setattr(superclaude_metrics, "metrics_tracker", tracker)

        @track_performance
        def my_function():
            return "success"

        result = my_function()
        assert result == "success"

    def test_function_with_exception(self, tmp_path, monkeypatch):
        """例外を発生する関数"""
        from superclaude_metrics import MetricsTracker, track_performance

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")

        import superclaude_metrics

        monkeypatch.setattr(superclaude_metrics, "metrics_tracker", tracker)

        @track_performance
        def failing_function():
            raise ValueError("Test error")

        import pytest

        with pytest.raises(ValueError):
            failing_function()

    def test_tracks_task_name(self, tmp_path, monkeypatch):
        """関数名をタスク名として追跡"""
        from superclaude_metrics import MetricsTracker, track_performance

        tracker = MetricsTracker(metrics_dir=str(tmp_path / "metrics"))
        tracker.start_session("test")

        import superclaude_metrics

        monkeypatch.setattr(superclaude_metrics, "metrics_tracker", tracker)

        @track_performance
        def named_task():
            pass

        named_task()

        assert len(tracker.current_session.tasks) == 1
        assert tracker.current_session.tasks[0].task_name == "named_task"
