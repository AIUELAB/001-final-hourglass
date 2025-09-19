# 🚀 Claude Code 自動承認モード & 高速モード

このプロジェクトにはClaude Codeの自動承認モードと高速モードが実装されています。

## ✅ 現在の設定状態

- **自動承認モード**: 有効
  - `~/.claude/auto-mode-status`: 🟢 AUTO-ACCEPT
  - 環境変数 `CLAUDE_SKIP_ALL_PERMISSIONS=true` 設定済み
  
- **高速モード**: 利用可能
  - 専用スクリプト: `scripts/claude-fast-mode.sh`
  
- **承認音**: 有効
  - 自動承認時に通知音が再生されます

## 🎯 機能

### 自動承認モード
- ファイル操作の確認プロンプトをスキップ
- 開発速度を大幅に向上
- バックグラウンドで承認音を再生

### 高速モード
- 権限確認を完全にスキップ
- Serena MCPサーバーの自動起動
- 並列処理の最適化
- 開発環境用に最適化された設定

## 📝 使い方

### 初回セットアップ
```bash
# 自動承認モードを有効化
./scripts/enable-auto-approval.sh

# 環境変数を現在のシェルに適用
source ~/.bashrc  # または ~/.zshrc
```

### 高速モードでClaude Codeを起動
```bash
# プロジェクトディレクトリで実行
./scripts/claude-fast-mode.sh
```

### 通常モードに戻す
```bash
# 自動承認モードを無効化
echo "🔴 DISABLED" > ~/.claude/auto-mode-status
unset CLAUDE_SKIP_ALL_PERMISSIONS
```

## 📁 関連ファイル

- `scripts/claude-fast-mode.sh` - 高速モード起動スクリプト
- `scripts/enable-auto-approval.sh` - 自動承認モード有効化スクリプト
- `scripts/play-approval-sound.sh` - 承認音再生スクリプト
- `auto_approval_config.json` - 設定ファイル
- `~/.claude/auto-mode-status` - ステータスファイル

## ⚠️ 注意事項

- **開発環境でのみ使用してください**
- 本番環境では通常モードを推奨します
- ファイル操作の確認がスキップされるため、慎重に使用してください

## 🔧 トラブルシューティング

### 自動承認が効かない場合
```bash
# ステータス確認
cat ~/.claude/auto-mode-status
echo $CLAUDE_SKIP_ALL_PERMISSIONS

# 再度有効化
./scripts/enable-auto-approval.sh
source ~/.bashrc
```

### Serenaが起動しない場合
```bash
# 手動起動
python3 scripts/start_serena_server.py

# プロセス確認
ps aux | grep serena-mcp-server
```

## 🔄 更新履歴

- 2025年8月30日: 初回実装
  - 自動承認モード
  - 高速モードスクリプト
  - 承認音機能