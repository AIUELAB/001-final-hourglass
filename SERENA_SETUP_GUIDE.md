# Serena MCP Server セットアップガイド 🚀

## 設定完了！ ✅

filesystemサーバーからSerena MCPサーバーへの切り替えが完了しました。

## 変更内容

### 1. 追加されたサーバー
```json
"serena": {
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/oraios/serena",
    "serena-mcp-server",
    "--project",
    "/Users/admin/Documents/AIUELAB/001-final-hourglass"
  ],
  "env": {}
}
```

### 2. 無効化されたサーバー
- **filesystem** → `filesystem-disabled` (disabled: true)

### 3. その他の有効なサーバー
- ✅ **github** - GitHub統合
- ✅ **fetch** - Web取得
- ✅ **context7** - ドキュメント参照
- ✅ **brave-search** - Web検索
- ✅ **firecrawl** - Webスクレイピング
- ✅ **playwright** - ブラウザ自動化
- ✅ **ide** - VS Code統合
- ✅ **mermaid** - 図表生成

## 次のステップ

### 1. Claude Desktopを再起動
```bash
# macOSの場合
# Claudeアプリケーションを完全に終了してから再起動してください
```

### 2. Serenaの初回セットアップ
初回起動時、Serenaは以下を実行します：
- プロジェクトのインデックス作成
- 依存関係の解析
- LSP機能の初期化

### 3. Serenaの使い方

#### セマンティック検索
```
"calculate_sum関数の定義を探して"
"TODOコメントがある場所をすべて表示"
```

#### コードリファクタリング
```
"すべてのprint文をlogger.infoに置換"
"変数名fooをbarにリネーム"
```

#### シンボル操作
```
"クラスUserの定義にジャンプ"
"process_data関数の参照をすべて表示"
```

#### コード実行
```
"pytest tests/を実行"
"npm run buildを実行"
```

## Serenaの利点

### filesystemサーバーとの比較

| 機能 | filesystem | Serena |
|------|-----------|--------|
| ファイル読み書き | ✅ | ✅ |
| ディレクトリ操作 | ✅ | ✅ |
| **セマンティック検索** | ❌ | ✅ |
| **LSP機能** | ❌ | ✅ |
| **シンボル解析** | ❌ | ✅ |
| **コード実行** | ❌ | ✅ |
| **プロジェクトインデックス** | ❌ | ✅ |
| **多言語対応** | ❌ | ✅ |
| **リファクタリング** | ❌ | ✅ |

### サポート言語
- Python
- TypeScript/JavaScript
- Go
- Rust
- Java
- C#
- PHP
- その他多数

## トラブルシューティング

### Serenaが起動しない場合
```bash
# uvxが利用可能か確認
which uvx

# uvxがない場合はpipxでインストール
pip install pipx
pipx ensurepath

# または直接uvをインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 権限エラーの場合
```bash
# プロジェクトディレクトリの権限を確認
ls -la /Users/admin/Documents/AIUELAB/001-final-hourglass

# 必要に応じて権限を修正
chmod -R 755 /Users/admin/Documents/AIUELAB/001-final-hourglass
```

### filesystemに戻す場合
設定ファイルで以下を変更：
1. `"filesystem-disabled"` → `"filesystem"`
2. `"disabled": true` を削除
3. `"serena"` を削除またはdisabled: trueを追加

## バックアップ

設定のバックアップは以下に保存されています：
```
/Users/admin/Library/Application Support/Claude/claude_desktop_config.backup_*.json
```

## まとめ

Serenaへの切り替えにより、以下が可能になります：
- 🔍 より高度なコード検索
- 🛠️ インテリジェントなリファクタリング
- 📊 プロジェクト全体の理解
- ⚡ 効率的なコード操作

**重要**: Claude Desktopを再起動して変更を反映させてください。

---

設定日時: 2025年8月29日
バージョン: Serena MCP Server (latest)
