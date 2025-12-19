# Obsidian MCP操作委譲（コンテキスト節約）

Obsidian MCP操作をサブエージェントに委譲して実行します。
Obsidianボールトの読み書き・検索が可能です。

## 使用方法

```
/obsidian <操作内容>
```

## 例

```
/obsidian ボールト内のファイル一覧
/obsidian "プロジェクト計画.md"の内容を取得
/obsidian "AI"を含むノートを検索
/obsidian 新しいノート"会議メモ.md"を作成
/obsidian "daily/2025-01-15.md"に内容を追記
```

## 実行指示

以下のTask toolを使用してサブエージェントに委譲してください：

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Obsidian MCPを使用して以下の操作を実行してください。

    ボールト: /Users/admin/Documents/Obsidian
    操作: $ARGUMENTS

    利用可能なツール:
    - list_files_in_vault: ボールト内ファイル一覧
    - list_files_in_dir: ディレクトリ内ファイル一覧
    - get_file_contents: ファイル内容取得
    - search: ボールト全体検索
    - create_note: 新規ノート作成
    - append_content: 内容追記
    - patch_content: 内容更新
    - delete_file: ファイル削除

    結果を簡潔にまとめて返してください。
```

## ボールト設定

| 項目 | 値 |
|------|-----|
| **パス** | `/Users/admin/Documents/Obsidian` |
| **形式** | Markdown (.md) |

## 活用例

| ユースケース | コマンド例 |
|-------------|-----------|
| **デイリーノート確認** | `/obsidian daily/今日のノートを表示` |
| **プロジェクトメモ作成** | `/obsidian projects/に新規ノート作成` |
| **アイデア検索** | `/obsidian "エピソード"を検索` |
| **会議メモ追記** | `/obsidian meetings/に追記` |

## メリット

- 親セッションのコンテキスト消費: 0
- Obsidianの知識ベースとAIを連携
- ノートの自動生成・更新
