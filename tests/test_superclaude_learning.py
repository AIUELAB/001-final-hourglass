#!/usr/bin/env python3
"""superclaude_learning テスト"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from superclaude_learning import LearningEntry, Pattern, ProjectKnowledge


class TestPattern:
    """Patternのテスト"""

    def test_init(self):
        """初期化テスト"""
        pattern = Pattern(pattern_id="p1", pattern_type="error_fix", context="test context", solution="test solution")
        assert pattern.pattern_id == "p1"
        assert pattern.pattern_type == "error_fix"
        assert pattern.success_rate == 0.0
        assert pattern.usage_count == 0

    def test_with_tags(self):
        """タグ付きパターン"""
        pattern = Pattern(
            pattern_id="p2", pattern_type="optimization", context="ctx", solution="sol", tags=["python", "performance"]
        )
        assert len(pattern.tags) == 2


class TestProjectKnowledge:
    """ProjectKnowledgeのテスト"""

    def test_init(self):
        """初期化テスト"""
        knowledge = ProjectKnowledge(project_path="/path/to/project", project_id="proj1")
        assert knowledge.project_path == "/path/to/project"
        assert knowledge.project_id == "proj1"
        assert knowledge.dependencies == []
        assert knowledge.test_commands == []

    def test_with_conventions(self):
        """規約付き"""
        knowledge = ProjectKnowledge(project_path="/path", project_id="p1", conventions={"naming": "snake_case"})
        assert "naming" in knowledge.conventions


class TestLearningEntry:
    """LearningEntryのテスト"""

    def test_init(self):
        """初期化テスト"""
        entry = LearningEntry(
            entry_id="e1",
            timestamp="2025-01-01",
            session_id="s1",
            entry_type="success",
            context={"key": "value"},
            action="test action",
            result="test result",
            outcome="success",
        )
        assert entry.entry_id == "e1"
        assert entry.entry_type == "success"
        assert entry.context["key"] == "value"
        assert entry.outcome == "success"
        assert entry.confidence == 0.0
        assert entry.reusable is False
