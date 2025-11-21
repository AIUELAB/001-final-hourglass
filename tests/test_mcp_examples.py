#!/usr/bin/env python3
"""mcp_examples テスト"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

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
