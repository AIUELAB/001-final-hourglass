# トラブルシューティングガイド

GitHub MCP統合に関する一般的な問題と解決策を説明します。

## 📋 目次

1. [MCP接続の問題](#mcp接続の問題)
2. [認証エラー](#認証エラー)
3. [環境変数の問題](#環境変数の問題)
4. [Git操作の問題](#git操作の問題)
5. [パフォーマンスの問題](#パフォーマンスの問題)
6. [デバッグ方法](#デバッグ方法)

---

## MCP接続の問題

### 問題1: "Failed to connect" エラー

**症状**:
```bash
claude mcp list
# github: npx @modelcontextprotocol/server-github - ✗ Failed to connect
```

**原因と解決策**:

#### 原因1: 環境変数が設定されていない

```bash
# 確認方法
launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN

# 出力が空の場合 → 環境変数が未設定
```

**解決策**:
```bash
# 1. トークンをKeychainから読み込み
launchctl setenv GITHUB_PERSONAL_ACCESS_TOKEN "$(~/.github-token-loader.sh)"

# 2. 確認
launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN
# 出力: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 3. Claude Desktopを再起動
killall Claude && sleep 5 && open -a Claude
```

#### 原因2: LaunchAgentが読み込まれていない

```bash
# 確認方法
launchctl list | grep com.anthropic.claude.env

# 何も表示されない場合 → LaunchAgentが未読み込み
```

**解決策**:
```bash
# LaunchAgentを読み込み
launchctl load ~/Library/LaunchAgents/com.anthropic.claude.env.plist

# 確認
launchctl list | grep com.anthropic.claude.env
# 出力: -    0    com.anthropic.claude.env
```

#### 原因3: トークンの権限不足

**確認方法**:
```bash
# GitHub APIで権限をテスト
gh auth status

# または
curl -H "Authorization: token $(launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN)" \
  https://api.github.com/user
```

**解決策**:
1. GitHubで新しいトークンを生成（[GITHUB_MCP_SETUP.md](./GITHUB_MCP_SETUP.md) Step 2参照）
2. 必要な権限を付与:
   - Contents: Read and write
   - Issues: Read and write
   - Pull requests: Read and write

#### 原因4: Claude Desktop内部統合

**注意**: Claude DesktopがGitHub Copilot APIと統合している場合、以下のように表示されることがあります：

```
github: https://api.githubcopilot.com/mcp/ (HTTP) - ✗ Failed to connect
```

これは**正常な動作**です。GitHub MCPの機能はGitHub CLI (`gh`)経由で利用できます。

**回避策**:
```bash
# GitHub CLIで操作可能
gh repo view AIUELAB/001-final-hourglass
gh issue list
gh pr list
```

---

### 問題2: MCPサーバーが起動しない

**症状**:
```bash
# エラーログに以下が表示される
Error: Cannot find module '@modelcontextprotocol/server-github'
```

**原因**: npmパッケージが見つからない

**解決策**:
```bash
# 1. Node.jsのバージョン確認
node --version
# 必須: v18以降

# 2. npxキャッシュをクリア
npx clear-npx-cache

# 3. パッケージを手動インストール（テスト）
npx -y @modelcontextprotocol/server-github --help

# 4. Claude Desktopを再起動
killall Claude && sleep 5 && open -a Claude
```

---

### 問題3: プロジェクト固有設定が反映されない

**症状**:
`.claude/claude_code_config.json`の設定が無視される

**原因**: 設定ファイルのJSONフォーマットエラー

**解決策**:
```bash
# JSON構文の検証
jq empty .claude/claude_code_config.json

# エラーがある場合、修正箇所が表示される
# 例: parse error: Expected separator between values at line 12
```

**よくあるエラー**:
```json
// ❌ 末尾のカンマ
{
  "mcpServers": {
    "github": { ... },  // ← 最後の要素にカンマは不要
  }
}

// ✅ 正しい形式
{
  "mcpServers": {
    "github": { ... }
  }
}
```

---

## 認証エラー

### 問題4: SSH接続エラー

**症状**:
```bash
git fetch origin
# Permission denied (publickey).
# fatal: Could not read from remote repository.
```

**原因と解決策**:

#### 原因1: SSH鍵がGitHubに登録されていない

**確認方法**:
```bash
# 公開鍵を表示
cat ~/.ssh/id_ed25519.pub

# GitHubで確認
# https://github.com/settings/keys
```

**解決策**:
1. 公開鍵をコピー: `pbcopy < ~/.ssh/id_ed25519.pub`
2. GitHubに登録: Settings → SSH and GPG keys → New SSH key
3. 接続テスト: `ssh -T git@github.com`

#### 原因2: SSH-Agentに鍵が追加されていない

**確認方法**:
```bash
ssh-add -l
# The agent has no identities. ← 鍵が未登録
```

**解決策**:
```bash
# SSH-Agentを起動
eval "$(ssh-agent -s)"

# 鍵を追加
ssh-add ~/.ssh/id_ed25519

# 確認
ssh-add -l
# 256 SHA256:... your_email@example.com (ED25519)
```

#### 原因3: SSH設定が正しくない

**確認方法**:
```bash
cat ~/.ssh/config | grep -A3 "Host github.com"
```

**期待される設定**:
```
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
```

**解決策**:
```bash
# 設定を追加
cat >> ~/.ssh/config << 'EOF'
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
EOF
```

---

### 問題5: トークン認証エラー（GitHub API）

**症状**:
```bash
gh api /user
# gh: Bad credentials (HTTP 401)
```

**原因と解決策**:

#### 原因1: トークンが期限切れ

**確認方法**:
```bash
# GitHubでトークンの状態を確認
# https://github.com/settings/tokens
# Expired: YYYY-MM-DD と表示される
```

**解決策**:
1. 期限切れトークンを削除
2. 新しいトークンを生成（[GITHUB_MCP_SETUP.md](./GITHUB_MCP_SETUP.md) Step 2参照）
3. Keychainを更新:
   ```bash
   security delete-generic-password -a "$USER" -s "github-personal-access-token"
   security add-generic-password -a "$USER" -s "github-personal-access-token" -w "NEW_TOKEN"
   ```

#### 原因2: トークンが無効化された

**確認方法**:
```bash
# GitHubで確認
# https://github.com/settings/tokens
# Revoked または Not found と表示される
```

**解決策**:
新しいトークンを生成（上記と同じ手順）

---

## 環境変数の問題

### 問題6: 環境変数が永続化されない

**症状**:
```bash
# 再起動後に環境変数が消える
launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN
# (出力なし)
```

**原因**: LaunchAgentが正しく設定されていない

**解決策**:
```bash
# 1. LaunchAgentファイルの確認
cat ~/Library/LaunchAgents/com.anthropic.claude.env.plist

# 2. 構文エラーの検証
plutil -lint ~/Library/LaunchAgents/com.anthropic.claude.env.plist

# 3. LaunchAgentを再読み込み
launchctl unload ~/Library/LaunchAgents/com.anthropic.claude.env.plist
launchctl load ~/Library/LaunchAgents/com.anthropic.claude.env.plist

# 4. ログアウト/ログインで完全テスト
```

---

### 問題7: 環境変数がClaude Codeで認識されない

**症状**:
Claude Code内で`${GITHUB_PERSONAL_ACCESS_TOKEN}`が展開されない

**原因**: Claude Desktopが環境変数を認識していない

**解決策**:
```bash
# 1. 環境変数をグローバルに設定
launchctl setenv GITHUB_PERSONAL_ACCESS_TOKEN "$(~/.github-token-loader.sh)"

# 2. すべてのClaude関連プロセスを終了
killall Claude
pkill -f "Claude Code"

# 3. 5秒待機
sleep 5

# 4. Claude Desktopを再起動
open -a Claude
```

---

## Git操作の問題

### 問題8: Git remoteがHTTPSのまま

**症状**:
```bash
git remote -v
# origin  https://github.com/AIUELAB/001-final-hourglass.git (fetch)
```

**リスク**: トークン漏洩の可能性

**解決策**:
```bash
# SSHに変更
git remote set-url origin git@github.com:AIUELAB/001-final-hourglass.git

# 確認
git remote -v
# origin  git@github.com:AIUELAB/001-final-hourglass.git (fetch)
# origin  git@github.com:AIUELAB/001-final-hourglass.git (push)
```

---

### 問題9: Git操作が非常に遅い

**症状**:
`git fetch`や`git push`に30秒以上かかる

**原因と解決策**:

#### 原因1: SSH接続のタイムアウト

**解決策**:
```bash
# ~/.ssh/configに追加
cat >> ~/.ssh/config << 'EOF'
Host github.com
  ServerAliveInterval 60
  ServerAliveCountMax 3
  TCPKeepAlive yes
EOF
```

#### 原因2: HTTPSプロキシの問題

**確認方法**:
```bash
git config --global --get http.proxy
git config --global --get https.proxy
```

**解決策**:
```bash
# プロキシ設定を削除
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## パフォーマンスの問題

### 問題10: MCPサーバーの応答が遅い

**症状**:
GitHub操作に10秒以上かかる

**原因と解決策**:

#### 原因1: ネットワーク遅延

**確認方法**:
```bash
# GitHub APIのレスポンスタイムを測定
time curl -s https://api.github.com/zen
```

**解決策**:
- VPN接続を一時的に無効化
- ネットワーク接続を確認

#### 原因2: レート制限

**確認方法**:
```bash
# レート制限の状態を確認
gh api rate_limit | jq '.resources.core'
```

**解決策**:
```json
{
  "limit": 5000,        // 1時間あたりの上限
  "used": 4999,         // 使用済み
  "remaining": 1,       // 残り
  "reset": 1700000000   // リセット時刻（Unix timestamp）
}
```

リセット時刻まで待機するか、操作頻度を減らす

---

## デバッグ方法

### デバッグレベル1: 基本確認

```bash
# 1. Node.js環境
node --version    # v18以降
npm --version

# 2. GitHub CLI
gh --version      # v2.0以降

# 3. 環境変数
launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN

# 4. SSH接続
ssh -T git@github.com

# 5. Git設定
git config --list --show-origin | grep -E "(user|remote)"
```

---

### デバッグレベル2: 詳細ログ

#### MCP接続のデバッグ

```bash
# Claude Desktopのログを確認
tail -f ~/Library/Logs/Claude/claude.ai-web.log | grep -i "mcp\|github"
```

#### GitHub API呼び出しのデバッグ

```bash
# GitHub CLIの詳細ログ
GH_DEBUG=1 gh repo view AIUELAB/001-final-hourglass

# curlで直接API呼び出し
curl -v -H "Authorization: token $(launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN)" \
  https://api.github.com/repos/AIUELAB/001-final-hourglass
```

#### SSH接続のデバッグ

```bash
# 詳細なSSH接続ログ
ssh -vvv git@github.com
```

---

### デバッグレベル3: システムレベル

#### プロセスの確認

```bash
# Claude関連プロセス
ps aux | grep -i claude

# MCP関連プロセス
ps aux | grep -E "(npx|@modelcontextprotocol)"
```

#### ネットワーク接続の確認

```bash
# GitHub APIへの接続
nc -zv api.github.com 443

# SSH接続
nc -zv github.com 22
```

#### Keychain Accessの確認

```bash
# GUI確認
open -a "Keychain Access"
# 検索: "github-personal-access-token"

# CLI確認
security find-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -g
```

---

## よくある質問（FAQ）

### Q1: MCP設定を変更したが反映されない

**A**: Claude Desktopの完全再起動が必要です：
```bash
killall Claude && sleep 5 && open -a Claude
```

### Q2: SSH鍵のパスフレーズを忘れた

**A**: 新しい鍵を生成してください：
```bash
# 古い鍵をバックアップ
mv ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.old
mv ~/.ssh/id_ed25519.pub ~/.ssh/id_ed25519.pub.old

# 新しい鍵を生成
ssh-keygen -t ed25519 -C "your_email@example.com"

# GitHubに登録（[GITHUB_MCP_SETUP.md](./GITHUB_MCP_SETUP.md) Step 1参照）
```

### Q3: トークンの期限が近づいている

**A**: 期限切れ30日前に新トークンを生成することを推奨：
1. 新トークンを生成
2. Keychainを更新
3. 動作確認後、旧トークンを削除

### Q4: 複数のGitHubアカウントを使い分けたい

**A**: SSH設定で複数アカウントを設定：
```bash
# ~/.ssh/config
Host github.com-work
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_work

Host github.com-personal
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_personal

# リポジトリごとにremoteを設定
git remote set-url origin git@github.com-work:company/repo.git
```

---

## エラーコード一覧

| エラーコード | 説明 | 対処法 |
|----------|------|-------|
| 401 | 認証失敗 | トークンの確認・再生成 |
| 403 | アクセス拒否 | 権限の確認・拡張 |
| 404 | リソース未検出 | URLとリポジトリ名の確認 |
| 422 | バリデーションエラー | リクエストパラメータの確認 |
| 429 | レート制限超過 | 待機またはトークンのアップグレード |
| 500 | サーバーエラー | GitHub Status確認 |

---

## 緊急時の連絡先

- **GitHub Status**: https://www.githubstatus.com/
- **GitHub Support**: https://support.github.com/
- **Claude Support**: https://support.anthropic.com/

---

## 関連ドキュメント

- [GITHUB_MCP_SETUP.md](./GITHUB_MCP_SETUP.md) - セットアップガイド
- [SECURITY.md](./SECURITY.md) - セキュリティガイドライン
- [MCP公式ドキュメント](https://modelcontextprotocol.io/)
- [GitHub CLI Manual](https://cli.github.com/manual/)

---

## 更新履歴

- **2025-11-20**: 初版作成
  - MCP接続の問題と解決策
  - 認証エラーのトラブルシューティング
  - 環境変数とGit操作の問題
  - デバッグ方法の体系化
