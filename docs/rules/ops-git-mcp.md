# 運用・自動化ルール (Git/MCP)

## 🔄 GitHub操作自動委譲ルール（コンテキスト節約）

**GitHub操作は `/gh` サブエージェントに自動委譲してコンテキストを節約**

### 委譲対象操作

| 操作カテゴリ | 委譲コマンド例 | 節約効果 |
|-------------|---------------|---------|
| **コミット履歴** | `/gh list_commits 5件` | ~2k tokens |
| **Issue管理** | `/gh list_issues open` | ~3k tokens |
| **PR管理** | `/gh list_pull_requests` | ~3k tokens |
| **ファイル取得** | `/gh get_file_contents README.md` | ~2k tokens |
| **バッチ操作** | `/gh batch-status` | ~5k tokens |

### 自動委譲トリガー

以下の状況で自動的に `/gh` に委譲：
- ユーザーがGitHub操作を要求した場合
- タスク完了時のコミット提案時
- PR作成・レビュー時
- Issue確認・更新時

### バッチ操作（推奨）

| コマンド | 実行内容 |
|---------|---------|
| `/gh batch-status` | git status + 最新5コミット + 未プッシュ確認 |
| `/gh batch-review` | open Issues + open PRs + 最新レビュー |

### 効果

- **コンテキスト節約**: ~15kトークン（7.5%削減）
- **結果のみ返却**: 詳細なAPI定義が不要に
- **責務分離**: Git/GitHub操作を専門エージェントに分離

### MCPプロファイル連携

GitHub MCPを完全無効化して `/gh` 委譲のみで運用する場合：
```bash
python scripts/switch_mcp_profile.py minimal-no-gh
```

---

## 🔄 Serena操作ハイブリッド委譲ルール（コンテキスト節約）

**Serena MCPは高頻度コア機能のため、特定操作パターンのみ委譲**

### 委譲対象（低頻度・バッチ操作）

| 操作パターン | 委譲コマンド | 節約効果 |
|-------------|-------------|---------|
| **メモリ操作** | `/serena memory list` | ~3k tokens |
| **大規模検索** | `/serena search パターン 全ファイル` | ~5k tokens |
| **リファクタリング** | `/serena refactor クラス名変更` | ~8k tokens |
| **構造分析** | `/serena analyze src/ディレクトリ` | ~5k tokens |

### 直接実行（委譲しない）

以下はレイテンシ優先のため直接実行：
- `find_symbol` - 単発シンボル検索
- `replace_symbol_body` - シンボル置換
- `read_file` - ファイル読み込み
- `replace_content` - コンテンツ置換
- `get_symbols_overview` - ファイル構造確認

### バッチ操作（推奨）

| コマンド | 実行内容 |
|---------|---------|
| `/serena memory` | list_memories + 関連memory読み込み |
| `/serena search-all パターン` | 複数ディレクトリ横断検索 |
| `/serena refactor 旧名 新名` | rename_symbol + 全参照更新 |
| `/serena overview ディレクトリ` | 再帰的シンボル構造分析 |

### 判断基準

| 条件 | 判断 |
|------|------|
| 単一ファイル・単一シンボル操作 | **直接実行** |
| 複数ファイル横断検索 | **委譲推奨** |
| メモリ操作（read/write） | **委譲推奨** |
| リファクタリング（rename等） | **委譲推奨** |
| 即時応答必要（編集中） | **直接実行** |

### 効果

- **選択的節約**: 必要な操作のみ~5-10kトークン節約
- **レイテンシ維持**: コア編集機能は直接実行で高速
- **バッチ効率化**: 複数操作を一度に委譲

---

## 🎯 スラッシュコマンド（Skills）

### 品質・分析系
- `/pdca` - 品質分析・改善提案
- `/codex-analyze` - AI協調分析
- `/kairos` - 機会検出
- `/rca` - 根本原因分析

### MCP管理系
- `/mcp-profile` - プロファイル切替（minimal/web/scraping/full）
- `/enable-web` - Web MCP一時有効化

### コンテキスト節約系（MCP委譲）
- `/gh` - GitHub操作を委譲（~15kトークン節約）
- `/serena` - Serena操作を委譲（~20kトークン節約）
- `/desktop` - Desktop Commander操作を委譲（~3kトークン節約）
- `/memory` - Memory操作を委譲（~2.5kトークン節約）
- `/obsidian` - Obsidian操作を委譲（~2kトークン節約）
- `/delegate` - 任意MCP操作を委譲（汎用）

**使い方**: `/gh コミット履歴を5件表示` → サブエージェントが実行 → 結果のみ返却

### 開発系
`/fix-errors`, `/refactor`, `/test`, `/review`, `/optimize`

---

## 🔧 MCPサーバー

### 有効（常時）
- **ide** - IDE統合
- **context7** - ライブラリドキュメント

### 無効化済み（必要時に有効化）
- playwright, firecrawl, brave-search, fetch

プロファイル切替: `python scripts/switch_mcp_profile.py [minimal|web|scraping|full]`

---

## 🔀 Git/MCP運用フロー

### 日常の標準フロー（main直接push）

```bash
# 作業開始
git pull origin main

# 作業完了後
git status              # 変更確認
git add .               # ステージ
git commit -m "type: 説明"
git push origin main
```

### コミットメッセージ形式

| type | 用途 |
|------|------|
| `fix:` | バグ修正 |
| `feat:` | 新機能 |
| `docs:` | ドキュメント |
| `chore:` | 雑務・設定変更 |
| `style:` | フォーマット |

### MCP GitHub活用

| 操作 | MCPツール |
|------|----------|
| 履歴確認 | `mcp__github__list_commits` |
| Issue作成 | `mcp__github__create_issue` |
| Issue一覧 | `mcp__github__list_issues` |
| ファイル確認 | `mcp__github__get_file_contents` |

**重要**: MCP操作後は必ず `git pull origin main` でローカル同期

### トラブル対処

| エラー | 対処 |
|--------|------|
| non-fast-forward | `git pull --rebase origin main` |
| コンフリクト | 手動解決 → `git add` → `git rebase --continue` |

詳細: `docs/GIT_MCP_WORKFLOW.md`

---

## 開発コマンド

```bash
ruff format src tests      # フォーマット
ruff check src tests --fix # リント
pytest tests --cov=src     # テスト
mypy src                   # 型チェック
```
