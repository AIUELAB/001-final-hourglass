#!/usr/bin/env python3
"""superclaude_learning テスト"""

import sys
from pathlib import Path


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

    def test_get_project_id(self):
        """プロジェクトID生成"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            id1 = system.get_project_id("/path/to/project")
            id2 = system.get_project_id("/path/to/project")
            id3 = system.get_project_id("/different/path")
            assert id1 == id2
            assert id1 != id3
            assert len(id1) == 12

    def test_learn_from_success(self):
        """成功事例学習"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            context = {"session_id": "test", "tool": "pytest"}
            entry_id = system.learn_from_success(context, "pytest tests/", "All passed")
            assert entry_id.startswith("entry_")

    def test_learn_project_convention(self):
        """プロジェクト規約学習"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            system.learn_project_convention("/test/project", "test_command", "pytest")
            knowledge = system.get_project_knowledge("/test/project")
            assert knowledge is not None
            assert knowledge.conventions["test_command"] == "pytest"

    def test_get_learning_stats(self):
        """学習統計取得"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            stats = system.get_learning_stats()
            assert "total_patterns" in stats
            assert "total_projects" in stats

    def test_learn_from_error_without_solution(self):
        """解決策なしのエラー学習"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            context = {"session_id": "test", "error_type": "ImportError"}
            entry_id = system.learn_from_error(context, "ModuleNotFoundError")
            assert entry_id.startswith("error_")

    def test_learn_from_error_with_solution(self):
        """解決策ありのエラー学習"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            context = {"session_id": "test", "error_type": "ImportError"}
            entry_id = system.learn_from_error(context, "ModuleNotFoundError", "pip install module")
            assert entry_id.startswith("error_")

    def test_learn_from_error_updates_project(self):
        """エラー学習でプロジェクト更新"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            context = {"session_id": "test", "project_path": "/test/project"}
            system.learn_from_error(context, "SyntaxError", "fix syntax")
            project_id = system.get_project_id("/test/project")
            assert project_id in system.projects_cache
            assert len(system.projects_cache[project_id].common_errors) == 1

    def test_learn_frequent_operation_new(self):
        """新規操作の頻度学習"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            system.learn_frequent_operation("/test/project", {"command": "git status"})
            knowledge = system.get_project_knowledge("/test/project")
            assert len(knowledge.frequent_operations) == 1
            assert knowledge.frequent_operations[0]["count"] == 1

    def test_learn_frequent_operation_increment(self):
        """既存操作のカウント増加"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            system.learn_frequent_operation("/test/project", {"command": "git status"})
            system.learn_frequent_operation("/test/project", {"command": "git status"})
            knowledge = system.get_project_knowledge("/test/project")
            assert knowledge.frequent_operations[0]["count"] == 2

    def test_learn_frequent_operation_sorting(self):
        """頻度操作のソート確認"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            for _ in range(3):
                system.learn_frequent_operation("/test/project", {"command": "cmd1"})
            for _ in range(5):
                system.learn_frequent_operation("/test/project", {"command": "cmd2"})
            knowledge = system.get_project_knowledge("/test/project")
            assert knowledge.frequent_operations[0]["command"] == "cmd2"

    def test_get_similar_patterns_empty(self):
        """空パターンリスト"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            patterns = system.get_similar_patterns({"tool": "pytest"})
            assert patterns == []

    def test_get_project_knowledge_nonexistent(self):
        """存在しないプロジェクト"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            knowledge = system.get_project_knowledge("/nonexistent")
            assert knowledge is None

    def test_suggest_solution_no_patterns(self):
        """パターンなしで解決策提案"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            suggestion = system.suggest_solution({"error": "test"})
            assert suggestion is None

    def test_get_project_shortcuts_empty(self):
        """空ショートカット"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            shortcuts = system.get_project_shortcuts("/nonexistent")
            assert shortcuts == {}

    def test_get_project_shortcuts_with_data(self):
        """データありショートカット"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            project_id = system.get_project_id("/test/project")
            knowledge = ProjectKnowledge(
                project_path="/test/project",
                project_id=project_id,
                test_commands=["pytest"],
                build_commands=["make build"],
                custom_aliases={"t": "pytest"},
            )
            system.projects_cache[project_id] = knowledge
            shortcuts = system.get_project_shortcuts("/test/project")
            assert shortcuts["test"] == "pytest"
            assert shortcuts["build"] == "make build"
            assert shortcuts["aliases"]["t"] == "pytest"

    def test_extract_tags_file_path(self):
        """ファイルパスからタグ抽出"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            tags = system._extract_tags({"file_path": "/test/file.py"})
            assert "py" in tags

    def test_extract_tags_tool(self):
        """ツール名からタグ抽出"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            tags = system._extract_tags({"tool": "pytest"})
            assert "pytest" in tags

    def test_extract_tags_error_type(self):
        """エラータイプからタグ抽出"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            tags = system._extract_tags({"error_type": "ImportError"})
            assert "ImportError" in tags

    def test_calculate_similarity_invalid_json(self):
        """無効JSONの類似度計算"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            pattern = Pattern(
                pattern_id="test",
                pattern_type="error",
                context="invalid json",
                solution="fix",
            )
            similarity = system._calculate_similarity({"key": "value"}, pattern)
            assert similarity == 0.0

    def test_extract_pattern_low_confidence(self):
        """低confidence時のパターン抽出"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            entry = LearningEntry(
                entry_id="e1",
                timestamp="2025-01-01",
                session_id="s1",
                entry_type="error",
                context={},
                action="test",
                result="result",
                outcome="failure",
                confidence=0.5,
                reusable=True,
            )
            pattern = system._extract_pattern(entry)
            assert pattern is None

    def test_extract_pattern_not_reusable(self):
        """非再利用可能時のパターン抽出"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            entry = LearningEntry(
                entry_id="e1",
                timestamp="2025-01-01",
                session_id="s1",
                entry_type="success",
                context={},
                action="test",
                result="result",
                outcome="success",
                confidence=0.9,
                reusable=False,
            )
            pattern = system._extract_pattern(entry)
            assert pattern is None

    def test_extract_pattern_creates_new(self):
        """新規パターン作成"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            entry = LearningEntry(
                entry_id="e1",
                timestamp="2025-01-01",
                session_id="s1",
                entry_type="success",
                context={"tool": "pytest"},
                action="pytest tests/",
                result="passed",
                outcome="success",
                confidence=0.9,
                reusable=True,
            )
            pattern = system._extract_pattern(entry)
            assert pattern is not None
            assert pattern.pattern_type == "success"

    def test_load_patterns_with_existing_files(self):
        """既存パターンファイルの読み込み"""
        import json
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            patterns_dir = Path(tmpdir) / "patterns"
            patterns_dir.mkdir(parents=True)
            pattern_data = {
                "pattern_id": "existing123",
                "pattern_type": "error_fix",
                "context": "{}",
                "solution": "fix",
                "success_rate": 0.8,
                "usage_count": 3,
                "last_used": "",
                "tags": [],
                "metadata": {},
            }
            with open(patterns_dir / "existing123.json", "w") as f:
                json.dump(pattern_data, f)
            system = LearningSystem(learning_dir=tmpdir)
            assert "existing123" in system.patterns_cache

    def test_load_patterns_handles_invalid_json(self):
        """無効JSONファイルの処理"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            patterns_dir = Path(tmpdir) / "patterns"
            patterns_dir.mkdir(parents=True)
            with open(patterns_dir / "invalid.json", "w") as f:
                f.write("not valid json")
            system = LearningSystem(learning_dir=tmpdir)
            assert "invalid" not in system.patterns_cache

    def test_load_project_knowledge_with_existing_files(self):
        """既存プロジェクト知識の読み込み"""
        import json
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            projects_dir = Path(tmpdir) / "projects"
            projects_dir.mkdir(parents=True)
            knowledge_data = {
                "project_path": "/test/project",
                "project_id": "proj123",
                "conventions": {"style": "pep8"},
                "dependencies": [],
                "common_errors": [],
                "file_patterns": {},
                "test_commands": [],
                "build_commands": [],
                "frequent_operations": [],
                "custom_aliases": {},
                "last_updated": "",
            }
            with open(projects_dir / "proj123.json", "w") as f:
                json.dump(knowledge_data, f)
            system = LearningSystem(learning_dir=tmpdir)
            assert "proj123" in system.projects_cache

    def test_save_and_load_roundtrip(self):
        """保存・読み込み往復テスト"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system1 = LearningSystem(learning_dir=tmpdir)
            system1.learn_project_convention("/test/project", "indent", "4")
            system1.learn_project_convention("/test/project", "line_length", "88")
            system2 = LearningSystem(learning_dir=tmpdir)
            knowledge = system2.get_project_knowledge("/test/project")
            assert knowledge.conventions["indent"] == "4"
            assert knowledge.conventions["line_length"] == "88"

    def test_stats_with_high_confidence_patterns(self):
        """高confidence パターン統計"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            pattern = Pattern(
                pattern_id="high1",
                pattern_type="error_fix",
                context="{}",
                solution="fix",
                success_rate=0.9,
                usage_count=5,
            )
            system.patterns_cache["high1"] = pattern
            stats = system.get_learning_stats()
            assert stats["high_confidence_patterns"] == 1

    def test_update_project_errors_limit(self):
        """プロジェクトエラーリスト上限"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            for i in range(25):
                context = {"session_id": "test", "project_path": "/test/project"}
                system.learn_from_error(context, f"Error {i}", f"Solution {i}")
            knowledge = system.get_project_knowledge("/test/project")
            assert len(knowledge.common_errors) == 20  # 上限20

    def test_frequent_operations_limit(self):
        """頻出操作の上限"""
        import tempfile

        from superclaude_learning import LearningSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            system = LearningSystem(learning_dir=tmpdir)
            for i in range(25):
                system.learn_frequent_operation("/test/project", {"command": f"cmd{i}"})
            knowledge = system.get_project_knowledge("/test/project")
            assert len(knowledge.frequent_operations) == 20  # 上限20
