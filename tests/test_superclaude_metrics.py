#!/usr/bin/env python3
"""superclaude_metrics テスト"""

import sys
import time
from pathlib import Path

import pytest

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
