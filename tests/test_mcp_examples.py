#!/usr/bin/env python3
"""mcp_examples テスト"""

import sys
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_examples import MAX_TITLE_LENGTH, GitHubIssue, SearchResult


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
        from mcp_examples import MCPDataProcessor

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
