# Serena MCP操作委譲（コンテキスト節約）

Serena MCP操作をサブエージェントに委譲して実行します。
親セッションのコンテキストを圧迫せずにセマンティックコード操作が可能です。

## 使用方法

```
/serena <操作内容>
```

## 例

```
/serena クラスUserServiceを検索
/serena 関数generate_episodeの参照を探す
/serena src/ディレクトリの構造を表示
/serena パターン"def test_"を検索
```

## 実行指示

以下のTask toolを使用してサブエージェントに委譲してください：

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Serena MCPを使用して以下の操作を実行してください。

    プロジェクト: 001-final-hourglass
    操作: $ARGUMENTS

    利用可能なツール:
    - mcp__serena__find_symbol: シンボル検索
    - mcp__serena__find_referencing_symbols: 参照検索
    - mcp__serena__get_symbols_overview: ファイルのシンボル一覧
    - mcp__serena__search_for_pattern: パターン検索
    - mcp__serena__list_dir: ディレクトリ一覧
    - mcp__serena__read_file: ファイル読み込み

    結果を簡潔にまとめて返してください。
```

## メリット

- 親セッションのコンテキスト消費: 0
- Serena MCP（~20kトークン）の定義が親に不要
- 操作完了後、結果のみ返却
