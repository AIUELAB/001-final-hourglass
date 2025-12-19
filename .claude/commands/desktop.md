# Desktop Commander操作委譲（コンテキスト節約）

Desktop Commander MCP操作をサブエージェントに委譲して実行します。
ファイル操作、ターミナル実行、差分編集などが可能です。

## 使用方法

```
/desktop <操作内容>
```

## 例

```
/desktop カレントディレクトリのファイル一覧
/desktop "hello.py"を作成してprint('Hello')を書く
/desktop ターミナルでpython --versionを実行
/desktop large_file.txtの100-200行目を表示
/desktop config.jsonの"debug": falseを"debug": trueに変更
```

## 実行指示

以下のTask toolを使用してサブエージェントに委譲してください：

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Desktop Commander MCPを使用して以下の操作を実行してください。

    操作: $ARGUMENTS

    利用可能なツール:
    - execute_command: ターミナルコマンド実行
    - read_file: ファイル読み込み
    - write_file: ファイル書き込み
    - edit_block: ブロック編集（差分）
    - search_files: ファイル検索
    - list_directory: ディレクトリ一覧

    結果を簡潔にまとめて返してください。
```

## Desktop Commanderの特徴

| 機能 | 説明 |
|------|------|
| **長時間コマンド** | タイムアウトなしで実行可能 |
| **差分編集** | edit_blockで部分的な変更 |
| **ファイル監視** | 変更検出 |
| **プロセス管理** | バックグラウンド実行・停止 |

## メリット

- 親セッションのコンテキスト消費: 0
- Bashの代替として強力な機能
- 操作完了後、結果のみ返却
