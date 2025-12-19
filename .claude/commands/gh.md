# GitHub操作委譲（コンテキスト節約）

GitHub MCP操作をサブエージェントに委譲して実行します。
親セッションのコンテキストを圧迫せずにGitHub操作が可能です。

## 使用方法

```
/gh <操作内容>
```

## 例

```
/gh コミット履歴を5件表示
/gh Issue #123の詳細を取得
/gh PRを作成（タイトル: バグ修正）
/gh リポジトリの統計情報
```

## 実行指示

以下のTask toolを使用してサブエージェントに委譲してください：

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    GitHub MCPを使用して以下の操作を実行してください。

    リポジトリ: aiuelab/001-final-hourglass
    操作: $ARGUMENTS

    利用可能なツール:
    - mcp__github__list_commits: コミット履歴
    - mcp__github__get_issue: Issue詳細
    - mcp__github__list_issues: Issue一覧
    - mcp__github__create_pull_request: PR作成
    - mcp__github__get_pull_request: PR詳細
    - mcp__github__search_code: コード検索

    結果を簡潔にまとめて返してください。
```

## メリット

- 親セッションのコンテキスト消費: 0
- GitHub MCP（~15kトークン）の定義が親に不要
- 操作完了後、結果のみ返却
