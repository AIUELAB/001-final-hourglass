---
description: MCPプロファイルを切り替える（コンテキスト最適化）
---

# MCPプロファイル切り替え

現在利用可能なMCPプロファイル:

## 📋 プロファイル一覧

### 1. minimal（最小構成）
- **説明**: コンテキスト節約優先
- **用途**: 通常の開発作業、コード編集、ファイル操作
- **コンテキスト消費**: 3.0k
- **Free space予測**: 53.8k (26.9%)
- **含まれるMCP**: serena, codex, context7, ide

### 2. web（Web検索・URL取得）
- **説明**: Web検索・URL取得
- **用途**: Web検索、URLコンテンツ取得、簡単な情報収集
- **コンテキスト消費**: 7.9k
- **Free space予測**: 48.9k (24.5%)
- **含まれるMCP**: minimal + fetch, brave-search

### 3. scraping（Webスクレイピング）
- **説明**: Webスクレイピング・ブラウザ自動化
- **用途**: Webスクレイピング、サイト全体のクロール、ブラウザ自動化、スクリーンショット
- **コンテキスト消費**: 30.0k
- **Free space予測**: 26.8k (13.4%)
- **含まれるMCP**: web + firecrawl, playwright

### 4. full（全機能有効）
- **説明**: すべてのMCP機能が有効
- **用途**: すべてのMCP機能が必要な複雑なタスク
- **コンテキスト消費**: 30.8k
- **Free space予測**: 26.0k (13.0%)
- **含まれるMCP**: すべて

---

## 🎯 推奨されるプロファイル

あなたのタスクに応じて、以下のプロファイルを推奨します：

- **通常の開発作業**: `minimal`
- **Web検索が必要**: `web`
- **Webスクレイピングが必要**: `scraping`
- **すべての機能が必要**: `full`

---

## 📝 使用方法

プロファイルを切り替えるには、以下のコマンドを実行してください：

```bash
python scripts/switch_mcp_profile.py <profile_name>
```

**例**:
```bash
# Web検索が必要な場合
python scripts/switch_mcp_profile.py web

# Webスクレイピングが必要な場合
python scripts/switch_mcp_profile.py scraping

# 通常作業に戻る場合
python scripts/switch_mcp_profile.py minimal
```

---

## 📊 現在のプロファイル確認

```bash
python scripts/switch_mcp_profile.py --current
```

---

## 💡 推奨プロファイル検索

タスク内容から推奨プロファイルを自動提案：

```bash
python scripts/switch_mcp_profile.py --recommend "Web検索したい"
```

---

## ⚠️ 注意事項

- プロファイル切り替え後、**Claude Code/Cursorを再起動**してください
- 再起動しないと設定が反映されません
- バックアップは自動作成されます（`~/.claude.json.backup_phase18c_*`）

---

## 🔄 よくある使い方

### シナリオ1: 通常作業 → Web検索 → 通常作業に戻る

```bash
# 1. Web検索プロファイルに切り替え
python scripts/switch_mcp_profile.py web

# 2. Claude Code再起動

# 3. Web検索を実施

# 4. 作業完了後、minimalに戻す
python scripts/switch_mcp_profile.py minimal

# 5. Claude Code再起動
```

### シナリオ2: プロファイル一覧を確認してから選択

```bash
# 1. 利用可能なプロファイルを確認
python scripts/switch_mcp_profile.py --list

# 2. 適切なプロファイルを選択
python scripts/switch_mcp_profile.py <profile_name>

# 3. Claude Code再起動
```

---

次に切り替えたいプロファイルを教えてください！
