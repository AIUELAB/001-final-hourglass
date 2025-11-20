# GitHub MCP セットアップガイド

このガイドでは、GitHub MCPサーバーのセットアップ手順と設定方法を説明します。

## 📋 目次

1. [前提条件](#前提条件)
2. [セットアップ手順](#セットアップ手順)
3. [設定ファイルの詳細](#設定ファイルの詳細)
4. [動作確認](#動作確認)
5. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 必須環境

- **macOS**: 10.15以降（Catalina以降）
- **Node.js**: v18以降
- **Claude Desktop**: 最新版
- **Claude Code**: 最新版
- **GitHub CLI**: v2.0以降（`brew install gh`）

### 必須アカウント

- GitHubアカウント（2FA有効化推奨）
- GitHub Personal Access Token（後述の権限が必要）

---

## セットアップ手順

### Step 1: SSH鍵の生成と登録

#### 1.1 SSH鍵ペアの生成

```bash
# ed25519形式で鍵を生成（最もセキュア）
ssh-keygen -t ed25519 -C "your_email@example.com"

# デフォルトの保存場所: ~/.ssh/id_ed25519
# パスフレーズ設定を推奨
```

#### 1.2 SSH設定ファイルの作成

```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
EOF
```

#### 1.3 公開鍵をGitHubに登録

```bash
# 公開鍵をクリップボードにコピー
pbcopy < ~/.ssh/id_ed25519.pub

# GitHubにアクセス:
# Settings → SSH and GPG keys → New SSH key
# タイトル: "MacBook Claude Code"
# Key: ペースト
```

#### 1.4 SSH接続の確認

```bash
# GitHub host keyの追加
ssh-keyscan github.com >> ~/.ssh/known_hosts

# 接続テスト
ssh -T git@github.com
# 成功メッセージ: "Hi USERNAME! You've successfully authenticated..."
```

---

### Step 2: GitHub Personal Access Tokenの生成

#### 2.1 トークンの生成

1. GitHubにアクセス: [Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. "Generate new token"をクリック
3. トークン設定:
   - **Token name**: `Claude Code MCP - MacBook`
   - **Expiration**: 90 days（推奨）
   - **Repository access**: "Only select repositories" → 対象リポジトリを選択
   - **Permissions**:
     - **Repository permissions**:
       - Contents: Read and write
       - Issues: Read and write
       - Pull requests: Read and write
       - Metadata: Read-only（自動選択）

4. "Generate token"をクリック
5. **トークンを安全にコピー**（再表示不可）

#### 2.2 トークンの安全な保存（macOS Keychain）

```bash
# Keychainに保存（暗号化）
security add-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -w "ghp_YOUR_TOKEN_HERE"

# 保存確認
security find-generic-password \
  -a "$USER" \
  -s "github-personal-access-token" \
  -w
```

---

### Step 3: 環境変数の永続化

#### 3.1 トークン読み込みスクリプトの作成

```bash
cat > ~/.github-token-loader.sh << 'EOF'
#!/bin/bash
security find-generic-password -a "$USER" -s "github-personal-access-token" -w 2>/dev/null
EOF

chmod +x ~/.github-token-loader.sh
```

#### 3.2 LaunchAgentの作成

```bash
cat > ~/Library/LaunchAgents/com.anthropic.claude.env.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.anthropic.claude.env</string>
    <key>ProgramArguments</key>
    <array>
        <string>sh</string>
        <string>-c</string>
        <string>launchctl setenv GITHUB_PERSONAL_ACCESS_TOKEN "$($HOME/.github-token-loader.sh)"</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
```

#### 3.3 LaunchAgentの読み込み

```bash
# LaunchAgentを読み込み
launchctl load ~/Library/LaunchAgents/com.anthropic.claude.env.plist

# 即座に環境変数を設定
launchctl setenv GITHUB_PERSONAL_ACCESS_TOKEN "$(~/.github-token-loader.sh)"

# 確認
launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN
```

---

### Step 4: MCP設定の追加

#### 4.1 グローバル設定（Claude Desktop）

**ファイル**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

#### 4.2 プロジェクト固有設定（Claude Code）

**ファイル**: `.claude/claude_code_config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      },
      "disabled": false
    }
  }
}
```

#### 4.3 Claude Desktopの再起動

```bash
# Claude Desktopを完全終了
killall Claude

# 5秒待機
sleep 5

# Claude Desktopを起動
open -a Claude
```

---

### Step 5: Git Remoteの設定

#### 5.1 既存のHTTPS接続をSSHに変更

```bash
# 現在のremote確認
git remote -v

# SSHに変更
git remote set-url origin git@github.com:USERNAME/REPOSITORY.git

# 確認
git remote -v
# 出力例:
# origin  git@github.com:AIUELAB/001-final-hourglass.git (fetch)
# origin  git@github.com:AIUELAB/001-final-hourglass.git (push)
```

#### 5.2 接続テスト

```bash
# SSH接続テスト
git fetch origin

# 成功すれば設定完了
```

---

## 設定ファイルの詳細

### MCP設定の構造

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",                                    // Node.js実行コマンド
      "args": ["-y", "@modelcontextprotocol/server-github"], // MCPサーバーパッケージ
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"  // 環境変数参照
      },
      "disabled": false  // サーバーの有効/無効
    }
  }
}
```

### 環境変数の優先順位

1. **LaunchAgent** - `launchctl setenv` で設定
2. **シェル環境変数** - `.zshrc`, `.bashrc` 等
3. **インライン設定** - MCP設定内の`env`セクション

---

## 動作確認

### MCP接続状態の確認

```bash
# Claude CodeでMCPサーバーの状態を確認
claude mcp list

# 期待される出力:
# github: npx @modelcontextprotocol/server-github - ✓ Connected
```

**注意**: Claude DesktopのGitHub Copilot統合により、`https://api.githubcopilot.com/mcp/`として表示される場合があります。これは正常な動作です。

### GitHub CLI経由での動作確認

```bash
# リポジトリ情報の取得
gh repo view AIUELAB/001-final-hourglass

# Issueの一覧
gh issue list

# 最新のコミット
gh api repos/AIUELAB/001-final-hourglass/commits | jq -r '.[0].commit.message'

# ブランチ一覧
gh api repos/AIUELAB/001-final-hourglass/branches | jq -r '.[].name'
```

---

## トラブルシューティング

詳細は[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)を参照してください。

### よくある問題

#### 1. MCP接続失敗

**症状**: `claude mcp list`で"Failed to connect"

**原因**:
- 環境変数が設定されていない
- トークンの権限不足
- Claude Desktopが再起動されていない

**解決策**:
```bash
# 環境変数の確認
launchctl getenv GITHUB_PERSONAL_ACCESS_TOKEN

# 環境変数が空の場合
launchctl setenv GITHUB_PERSONAL_ACCESS_TOKEN "$(~/.github-token-loader.sh)"

# Claude Desktopを再起動
killall Claude && sleep 5 && open -a Claude
```

#### 2. SSH認証エラー

**症状**: `Permission denied (publickey)`

**原因**:
- SSH鍵がGitHubに登録されていない
- SSH設定が正しくない

**解決策**:
```bash
# 公開鍵を再確認
cat ~/.ssh/id_ed25519.pub

# GitHubのSSH鍵設定ページで確認
# https://github.com/settings/keys

# SSH接続テスト
ssh -T git@github.com
```

#### 3. トークン期限切れ

**症状**: API操作が401エラーを返す

**解決策**:
1. 新しいトークンを生成（Step 2参照）
2. Keychainを更新:
   ```bash
   security delete-generic-password -a "$USER" -s "github-personal-access-token"
   security add-generic-password -a "$USER" -s "github-personal-access-token" -w "NEW_TOKEN"
   ```
3. LaunchAgentを再読み込み:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.anthropic.claude.env.plist
   launchctl load ~/Library/LaunchAgents/com.anthropic.claude.env.plist
   ```

---

## バックアップと復元

### 設定のバックアップ

```bash
# 自動バックアップスクリプト
bash scripts/backup-mcp-config.sh

# バックアップ先: .claude/backups/
# - claude_desktop_config_YYYYMMDD_HHMMSS.json
# - claude_code_config_YYYYMMDD_HHMMSS.json
# - com.anthropic.claude.env_YYYYMMDD_HHMMSS.plist
```

### 設定の復元

```bash
# 利用可能なバックアップを確認
bash scripts/restore-mcp-config.sh

# 特定のタイムスタンプで復元
bash scripts/restore-mcp-config.sh 20251120_075906
```

---

## セキュリティベストプラクティス

1. **トークンの最小権限**: 必要な権限のみを付与
2. **有効期限設定**: 90日以内を推奨
3. **定期的なローテーション**: 期限切れ前に新トークンを生成
4. **平文保存禁止**: Keychain等の暗号化ストレージを使用
5. **2FA有効化**: GitHubアカウントで2要素認証を有効化

---

## 関連ドキュメント

- [SECURITY.md](./SECURITY.md) - セキュリティガイドライン
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - 詳細なトラブルシューティング
- [MCP公式ドキュメント](https://modelcontextprotocol.io/)
- [GitHub CLI ドキュメント](https://cli.github.com/manual/)

---

## 更新履歴

- **2025-11-20**: 初版作成
  - SSH認証の設定手順
  - トークン管理のベストプラクティス
  - MCP設定の詳細説明
