#!/usr/bin/env python3
"""mcp_examples テスト"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_examples import (
    MAX_TITLE_LENGTH,
    GitHubIssue,
    MCPDataProcessor,
    MCPOrchestrator,
    SearchResult,
    main,
)


class TestGitHubIssue:
    """GitHubIssueのテスト"""

    def test_create_issue(self):
        """Issue作成"""
        issue = GitHubIssue(
            number=1, title="Test Issue", state="open", created_at=datetime.now(), author="testuser", labels=["bug"]
        )
        assert issue.number == 1
        assert issue.title == "Test Issue"
        assert issue.state == "open"
        assert issue.author == "testuser"
        assert len(issue.labels) == 1

    def test_issue_with_body(self):
        """本文付きIssue"""
        issue = GitHubIssue(
            number=2,
            title="Test",
            state="closed",
            created_at=datetime.now(),
            author="user",
            labels=[],
            body="Issue body content",
        )
        assert issue.body == "Issue body content"

    def test_issue_without_body(self):
        """本文なしIssue"""
        issue = GitHubIssue(number=3, title="Test", state="open", created_at=datetime.now(), author="user", labels=[])
        assert issue.body is None


class TestSearchResult:
    """SearchResultのテスト"""

    def test_create_result(self):
        """検索結果作成"""
        result = SearchResult(
            title="Test Result", url="https://example.com", snippet="This is a test snippet", source="web"
        )
        assert result.title == "Test Result"
        assert result.url == "https://example.com"
        assert result.snippet == "This is a test snippet"
        assert result.source == "web"


class TestConstants:
    """定数のテスト"""

    def test_max_title_length(self):
        """MAX_TITLE_LENGTH定数"""
        assert MAX_TITLE_LENGTH == 50


class TestMCPDataProcessor:
    """MCPDataProcessorのテスト"""

    def test_init(self):
        """初期化テスト"""
        from mcp_examples import MCPDataProcessor

        processor = MCPDataProcessor()
        assert processor is not None

    def test_process_github_issues_empty(self):
        """空のIssueリスト処理"""
        from mcp_examples import MCPDataProcessor

        processor = MCPDataProcessor()
        result = processor.process_github_issues([])
        assert result == []

    def test_process_github_issues_valid(self):
        """有効なIssueデータ処理"""
        from mcp_examples import MCPDataProcessor

        processor = MCPDataProcessor()
        issues_data = [
            {
                "number": 1,
                "title": "Test Issue",
                "state": "open",
                "created_at": "2025-01-01T00:00:00Z",
                "user": {"login": "testuser"},
                "labels": [{"name": "bug"}],
                "body": "Test body",
            }
        ]
        result = processor.process_github_issues(issues_data)
        assert len(result) == 1
        assert result[0].number == 1
        assert result[0].title == "Test Issue"

    def test_process_github_issues_missing_fields(self):
        """フィールド欠損のIssueデータ処理"""
        from mcp_examples import MCPDataProcessor

        processor = MCPDataProcessor()
        issues_data = [
            {
                "number": 2,
                "title": "Minimal Issue",
                "state": "closed",
            }
        ]
        result = processor.process_github_issues(issues_data)
        assert len(result) == 1

    def test_process_search_results_empty(self):
        """空の検索結果処理"""
        from mcp_examples import MCPDataProcessor

        processor = MCPDataProcessor()
        result = processor.process_search_results({})
        assert result == []

    def test_process_search_results_brave(self):
        """Brave Search形式の検索結果処理"""
        processor = MCPDataProcessor()
        search_data = {
            "web": {
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://example.com",
                        "description": "Test description",
                    }
                ]
            }
        }
        result = processor.process_search_results(search_data)
        assert len(result) == 1
        assert result[0].title == "Test Result"

    def test_process_search_results_firecrawl(self):
        """Firecrawl形式の検索結果処理"""
        processor = MCPDataProcessor()
        search_data = {
            "data": [
                {
                    "title": "Firecrawl Result",
                    "url": "https://firecrawl.example.com",
                    "content": "Firecrawl content here " * 20,  # 200+ characters
                }
            ]
        }
        result = processor.process_search_results(search_data)
        assert len(result) == 1
        assert result[0].title == "Firecrawl Result"
        assert result[0].source == "Firecrawl"
        assert len(result[0].snippet) <= 200

    @patch("mcp_examples.console")
    def test_display_github_issues(self, mock_console):
        """GitHubのIssue表示"""
        processor = MCPDataProcessor()
        issues = [
            GitHubIssue(
                number=1,
                title="Test Issue",
                state="open",
                created_at=datetime.now(),
                author="testuser",
                labels=["bug"],
            )
        ]
        processor.display_github_issues(issues)
        mock_console.print.assert_called_once()

    @patch("mcp_examples.console")
    def test_display_github_issues_long_title(self, mock_console):
        """長いタイトルのIssue表示"""
        processor = MCPDataProcessor()
        long_title = "A" * 100  # MAX_TITLE_LENGTH (50) を超える
        issues = [
            GitHubIssue(
                number=1,
                title=long_title,
                state="open",
                created_at=datetime.now(),
                author="testuser",
                labels=[],
            )
        ]
        processor.display_github_issues(issues)
        mock_console.print.assert_called_once()

    @patch("mcp_examples.console")
    def test_display_github_issues_no_labels(self, mock_console):
        """ラベルなしのIssue表示"""
        processor = MCPDataProcessor()
        issues = [
            GitHubIssue(
                number=1,
                title="No Labels",
                state="closed",
                created_at=datetime.now(),
                author="user",
                labels=[],
            )
        ]
        processor.display_github_issues(issues)
        mock_console.print.assert_called_once()

    @patch("mcp_examples.console")
    def test_display_search_results(self, mock_console):
        """検索結果表示"""
        processor = MCPDataProcessor()
        results = [
            SearchResult(
                title="Test Result",
                url="https://example.com",
                snippet="Test snippet",
                source="Brave Search",
            )
        ]
        processor.display_search_results(results)
        assert mock_console.print.call_count >= 1

    @pytest.mark.asyncio
    async def test_process_file_operations_existing_file(self):
        """既存ファイルの処理"""
        processor = MCPDataProcessor()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            result = await processor.process_file_operations([temp_path])
            assert temp_path in result
            assert result[temp_path] == "Test content"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_process_file_operations_not_found(self):
        """存在しないファイルの処理"""
        processor = MCPDataProcessor()
        result = await processor.process_file_operations(["/nonexistent/path/file.txt"])
        assert "/nonexistent/path/file.txt" in result
        assert result["/nonexistent/path/file.txt"] == "File not found"

    def test_generate_markdown_report_with_issues(self):
        """GitHubIssues含むレポート生成"""
        processor = MCPDataProcessor()
        issues = [
            GitHubIssue(
                number=1,
                title="Open Issue",
                state="open",
                created_at=datetime.now(),
                author="user",
                labels=[],
            ),
            GitHubIssue(
                number=2,
                title="Closed Issue",
                state="closed",
                created_at=datetime.now(),
                author="user",
                labels=[],
            ),
        ]
        data = {"github_issues": issues}
        report = processor.generate_markdown_report(data)
        assert "# MCP Data Analysis Report" in report
        assert "GitHub Issues Summary" in report
        assert "Total Issues: 2" in report
        assert "Open Issues: 1" in report

    def test_generate_markdown_report_with_search(self):
        """検索結果含むレポート生成"""
        processor = MCPDataProcessor()
        results = [
            SearchResult("Result 1", "https://a.com", "Snippet 1", "Brave Search"),
            SearchResult("Result 2", "https://b.com", "Snippet 2", "Firecrawl"),
        ]
        data = {"search_results": results}
        report = processor.generate_markdown_report(data)
        assert "Search Results Summary" in report
        assert "Total Results: 2" in report

    def test_generate_markdown_report_with_files(self):
        """ファイル処理結果含むレポート生成"""
        processor = MCPDataProcessor()
        data = {"files_processed": ["src/main.py", "tests/test_main.py"]}
        report = processor.generate_markdown_report(data)
        assert "Files Processed" in report
        assert "`src/main.py`" in report

    def test_generate_markdown_report_empty(self):
        """空データのレポート生成"""
        processor = MCPDataProcessor()
        report = processor.generate_markdown_report({})
        assert "# MCP Data Analysis Report" in report
        assert "Generated at" in report


class TestMCPOrchestrator:
    """MCPOrchestratorのテスト"""

    def test_init(self):
        """初期化テスト"""
        orchestrator = MCPOrchestrator()
        assert orchestrator is not None
        assert orchestrator.processor is not None

    def test_analyze_github_repository(self):
        """リポジトリ分析"""
        orchestrator = MCPOrchestrator()
        result = orchestrator.analyze_github_repository("owner", "repo")
        assert result["repository"] == "owner/repo"
        assert "timestamp" in result
        assert "stats" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) >= 2

    def test_research_topic(self):
        """トピックリサーチ"""
        orchestrator = MCPOrchestrator()
        result = orchestrator.research_topic("Test Topic")
        assert result["topic"] == "Test Topic"
        assert "timestamp" in result
        assert "sources" in result
        assert "summary" in result
        assert "key_points" in result
        assert len(result["key_points"]) >= 3

    @patch("mcp_examples.console")
    def test_display_analysis(self, mock_console):
        """分析結果表示"""
        orchestrator = MCPOrchestrator()
        analysis = {"key": "value", "nested": {"data": 123}}
        orchestrator.display_analysis(analysis)
        assert mock_console.print.call_count >= 1


class TestMain:
    """main関数のテスト"""

    @patch("mcp_examples.console")
    def test_main_executes(self, mock_console):
        """main関数が正常に実行される"""
        main()
        assert mock_console.print.call_count > 0

    @patch("mcp_examples.console")
    def test_main_processes_sample_data(self, mock_console):
        """main関数がサンプルデータを処理する"""
        main()
        # console.print が複数回呼ばれることを確認
        assert mock_console.print.call_count >= 5
