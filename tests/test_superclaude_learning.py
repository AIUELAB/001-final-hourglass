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

    def test_with_confidence(self):
        """confidence付きエントリ"""
        entry = LearningEntry(
            entry_id="e2",
            timestamp="2025-01-01",
            session_id="s2",
            entry_type="optimization",
            context={},
            action="optimize",
            result="faster",
            outcome="success",
            confidence=0.85,
            reusable=True,
        )
        assert entry.confidence == 0.85
        assert entry.reusable is True


class TestLearningSystem:
    """LearningSystemのテスト"""

    def test_init(self):
        """初期化テスト"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            assert system.learning_dir.exists()
            assert system.patterns_dir.exists()
            assert system.projects_dir.exists()

    def test_patterns_cache_init(self):
        """パターンキャッシュ初期化"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            assert isinstance(system.patterns_cache, dict)

    def test_projects_cache_init(self):
        """プロジェクトキャッシュ初期化"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            assert isinstance(system.projects_cache, dict)

    def test_directory_structure(self):
        """ディレクトリ構造テスト"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            assert (system.learning_dir / "patterns").exists()
            assert (system.learning_dir / "projects").exists()
            assert (system.learning_dir / "entries").exists()
            assert (system.learning_dir / "cache").exists()
