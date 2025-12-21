# Serena MCP操作委譲（ハイブリッドアプローチ）

Serena MCPの**特定操作パターンのみ**サブエージェントに委譲します。
高頻度コア機能は直接実行し、低頻度・バッチ操作のみ委譲してコンテキストを節約。

## ハイブリッド判断基準

| 条件 | 判断 |
|------|------|
| 単一ファイル・単一シンボル操作 | **直接実行**（このスキル不要） |
| 複数ファイル横断検索 | **委譲推奨** |
| メモリ操作（read/write） | **委譲推奨** |
| リファクタリング（rename等） | **委譲推奨** |
| 即時応答必要（編集中） | **直接実行** |

## バッチ操作コマンド

### `/serena memory` - メモリ操作一括
```
/serena memory list          # 全メモリ一覧
/serena memory read ファイル名  # メモリ読み込み
/serena memory write 内容     # メモリ書き込み
```

### `/serena search-all パターン` - 大規模横断検索
```
/serena search-all "def test_"        # テスト関数を全ファイルから検索
/serena search-all "import pandas" src/  # 特定ディレクトリ内検索
```

### `/serena refactor 旧名 新名` - リファクタリング
```
/serena refactor UserService AuthService  # クラス名変更 + 全参照更新
/serena refactor old_func new_func        # 関数名変更 + 全参照更新
```

### `/serena overview ディレクトリ` - 構造分析
```
/serena overview src/           # src/以下の全シンボル構造
/serena overview scripts/ depth=2  # 深さ2まで分析
```

## 単体操作（従来互換）

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
    - mcp__serena__rename_symbol: シンボル名変更
    - mcp__serena__list_memories: メモリ一覧
    - mcp__serena__read_memory: メモリ読み込み
    - mcp__serena__write_memory: メモリ書き込み

    結果を簡潔にまとめて返してください。
```

## 効果

- **選択的節約**: 委譲時のみ~5-10kトークン節約
- **レイテンシ維持**: コア編集機能は直接実行で高速
- **バッチ効率化**: 複数操作を一度に委譲
- 親セッションのコンテキスト消費: 委譲操作時は0

## 直接実行すべき操作（このスキル不要）

以下はレイテンシ優先のため、Serena MCPを直接使用：
- `find_symbol` - 単発シンボル検索
- `replace_symbol_body` - シンボル置換
- `read_file` - ファイル読み込み
- `replace_content` - コンテンツ置換
- `get_symbols_overview` - 単一ファイル構造確認
