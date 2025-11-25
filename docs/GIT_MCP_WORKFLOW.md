# Git/MCP 運用ワークフロー

このドキュメントでは、MCP GitHubサーバーを活用したGit運用の標準フローを説明します。

## 概要

- **ブランチ戦略**: main直接push（シンプル運用）
- **リモート**: origin (github.com:AIUELAB/001-final-hourglass)
- **MCP GitHub**: 積極活用（25ツール許可済み）

---

## 日常の標準フロー

### 1. 作業開始

```bash
git pull origin main
```

### 2. 作業完了後

```bash
# 変更確認
git status

# ステージング
git add .

# コミット
git commit -m "type: 説明"

# プッシュ
git push origin main
```

---

## コミットメッセージ形式

### 基本形式

```
type: 簡潔な説明

詳細な説明（任意）

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### タイプ一覧

| type | 用途 | 例 |
|------|------|-----|
| `fix:` | バグ修正 | `fix: ログインエラーを修正` |
| `feat:` | 新機能 | `feat: ユーザー検索機能を追加` |
| `docs:` | ドキュメント | `docs: README更新` |
| `chore:` | 雑務・設定 | `chore: 依存関係更新` |
| `style:` | フォーマット | `style: コードフォーマット統一` |
| `refactor:` | リファクタリング | `refactor: 認証ロジック整理` |
| `test:` | テスト | `test: ユニットテスト追加` |

---

## MCP GitHub活用ガイド

### 利用可能なツール

#### ファイル操作
| ツール | 用途 |
|--------|------|
| `mcp__github__get_file_contents` | ファイル内容取得 |
| `mcp__github__create_or_update_file` | ファイル作成/更新 |
| `mcp__github__push_files` | 複数ファイル一括push |

#### コミット・ブランチ
| ツール | 用途 |
|--------|------|
| `mcp__github__list_commits` | コミット履歴確認 |
| `mcp__github__create_branch` | ブランチ作成 |

#### Issue管理
| ツール | 用途 |
|--------|------|
| `mcp__github__create_issue` | Issue作成 |
| `mcp__github__list_issues` | Issue一覧 |
| `mcp__github__get_issue` | Issue詳細 |
| `mcp__github__update_issue` | Issue更新 |
| `mcp__github__add_issue_comment` | コメント追加 |

#### PR管理
| ツール | 用途 |
|--------|------|
| `mcp__github__create_pull_request` | PR作成 |
| `mcp__github__list_pull_requests` | PR一覧 |
| `mcp__github__merge_pull_request` | PRマージ |

### MCP操作の注意点

1. **MCP操作後は必ずローカル同期**
   ```bash
   git pull origin main
   ```

2. **ファイル更新時はSHA必須**
   - `get_file_contents` でSHAを取得
   - `create_or_update_file` でSHAを指定

3. **MCPとローカル操作を混ぜない**
   - 一つのタスクは一つの方法で完結

---

## MCP操作とローカルCLIの使い分け

| 操作 | 推奨 | 理由 |
|------|------|------|
| 変更確認 | ローカル `git status` | リアルタイム状態把握 |
| ステージ・コミット | ローカル `git add/commit` | 確実・シンプル |
| プッシュ | ローカル `git push` | 確実・シンプル |
| 履歴確認 | MCP `list_commits` | Claude統合で見やすい |
| Issue管理 | MCP | Claude統合で効率的 |
| ファイル内容確認 | MCP `get_file_contents` | リモート最新版を直接確認 |

---

## トラブルシューティング

### non-fast-forward エラー

**症状**: pushが拒否される
```
! [rejected] main -> main (non-fast-forward)
```

**原因**: リモートに新しいコミットがある

**対処**:
```bash
git pull --rebase origin main
git push origin main
```

### マージコンフリクト

**症状**: pullやrebase時にコンフリクト発生

**対処**:
1. コンフリクトファイルを手動編集
2. `git add <ファイル>`
3. `git rebase --continue` または `git merge --continue`

### 認証エラー

**症状**: permission denied

**対処**:
1. SSH鍵確認: `ssh -T git@github.com`
2. トークン確認: Keychain設定を確認

### 緊急リセット（ローカル変更破棄）

```bash
git fetch origin
git reset --hard origin/main
```

**注意**: 未コミットの変更は全て失われます

---

## 禁止事項

| 操作 | リスク |
|------|--------|
| `git push --force` | 履歴破壊 |
| mainでの`git reset --hard` | コミット消失 |
| `.git`フォルダの手動編集 | リポジトリ破損 |
| 認証情報のコミット | セキュリティ漏洩 |

---

## クイックリファレンス

```
┌─────────────────────────────────────────────────┐
│          日常Git運用チェックリスト               │
├─────────────────────────────────────────────────┤
│                                                 │
│  【作業開始】                                    │
│  □ git pull origin main                        │
│                                                 │
│  【作業完了】                                    │
│  □ git status                                  │
│  □ git add .                                   │
│  □ git commit -m "type: 説明"                  │
│  □ git push origin main                        │
│                                                 │
│  【MCP操作後】                                   │
│  □ git pull origin main（同期必須）            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md) - プロジェクト設定
- [GITHUB_MCP_SETUP.md](./GITHUB_MCP_SETUP.md) - MCP設定詳細
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - トラブル対処
