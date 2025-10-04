# 🚀 AI協調分析システム自動起動完全ガイド

## 📋 概要

このガイドでは、Claude CodeまたはCursorでプロジェクトを開いた際に、AI協調分析システムと統合MCP管理システムを**自動的に起動**する方法を説明します。

## 🎯 実現内容

✅ **Claude Code起動時**: 自動でシステム稼働
✅ **Cursor起動時**: 自動でシステム稼働
✅ **ターミナルでcd**: ディレクトリ移動でも自動起動
✅ **重複起動防止**: 既に起動済みの場合はスキップ
✅ **状態管理**: PIDファイルで稼働状態を追跡
✅ **自動再起動**: プロセス異常終了時の自動復旧（オプション）

## 🔧 セットアップ方法（3つのアプローチ）

### 方法1: direnv（最も確実・推奨⭐⭐⭐⭐⭐）

**対応環境**: Claude Code、Cursor、通常のターミナル全て

#### 1-1. direnvのインストール

```bash
# Homebrewでインストール
brew install direnv

# シェル設定に追加
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc  # Bashの場合
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc    # Zshの場合

# 設定を反映
source ~/.bashrc  # または source ~/.zshrc
```

#### 1-2. プロジェクトでdirenvを有効化

```bash
cd /Users/admin/Documents/AIUELAB/001-final-hourglass

# .envrcファイルを許可（初回のみ）
direnv allow .
```

#### 1-3. 動作確認

```bash
# プロジェクトディレクトリを一旦出る
cd ~

# 再度プロジェクトディレクトリに入る
cd /Users/admin/Documents/AIUELAB/001-final-hourglass

# 自動起動メッセージが表示されればOK
```

**✅ メリット**:
- Claude Code、Cursor、ターミナルすべてで動作
- 軽量で高速
- プロジェクトごとに独立した設定

**⚠️ 注意点**:
- 初回セットアップが必要
- `.envrc`ファイルを変更した場合は`direnv allow .`を再実行

---

### 方法2: VS Code/Cursor Task（Cursor推奨⭐⭐⭐⭐）

**対応環境**: Cursorのみ（VS Codeでも動作）

#### 2-1. セットアップ（自動完了済み）

`.vscode/tasks.json`は既に設定済みです。

#### 2-2. 動作確認

```bash
# Cursorでプロジェクトを開く
cursor .

# または VS Code
code .
```

**プロジェクトを開くと自動的に起動タスクが実行されます**

#### 2-3. 手動でタスク実行（確認用）

1. Cursorで `Cmd+Shift+P`（macOS）または`Ctrl+Shift+P`（Windows/Linux）
2. 「Tasks: Run Task」を選択
3. 「🚀 AI協調分析システム起動」を選択

**✅ メリット**:
- Cursor専用で統合度が高い
- GUIで簡単に管理
- タスクランナーとして使いやすい

**⚠️ 注意点**:
- Cursor/VS Codeでしか動作しない
- Claude Codeでは使用不可

---

### 方法3: 手動起動（フォールバック）

いずれの自動起動方法も使えない場合の代替案

```bash
# プロジェクトルートで実行
./scripts/unified_startup.sh
```

---

## 🎛️ システム管理コマンド

### 状態確認

```bash
./scripts/check_ai_collaboration_status.sh
```

**出力例**:
```
╔═══════════════════════════════════════════════════════════╗
║   🔍 AI協調分析システム状態確認                         ║
╚═══════════════════════════════════════════════════════════╝

📊 サービス状態:
✅ Serena MCP Server - 稼働中 (PID: 12345)
✅ Codex MCP Server - 稼働中 (PID: 12346)
✅ 自動同期システム - 稼働中 (PID: 12347)

📋 総合判定:
✅ AI協調分析システムは正常に稼働しています
```

### システム停止

```bash
./scripts/stop_ai_collaboration.sh
```

### システム再起動

```bash
./scripts/restart_ai_collaboration.sh
```

---

## 📊 起動されるサービス一覧

| サービス | 説明 | ポート | ダッシュボード |
|---------|------|-------|--------------|
| **Serena MCP** | 高度なコード操作サーバー | 8000 | http://127.0.0.1:24282/dashboard/index.html |
| **Codex MCP** | AI協調分析エンジン | 8765 | http://localhost:8765 |
| **自動同期** | Google Sheetsとのデータ同期 | - | - |
| **リアルタイム監視** | ファイル変更監視 | - | - |
| **ファクトチェッカー** | ドキュメント誤記検出 | - | - |

---

## 🔍 トラブルシューティング

### 問題1: direnvが動作しない

**症状**: ディレクトリに入っても何も起こらない

**解決方法**:
```bash
# direnvが正しくインストールされているか確認
direnv version

# シェル設定を確認
cat ~/.zshrc | grep direnv

# .envrcを再許可
direnv allow .
```

### 問題2: プロセスが重複起動される

**症状**: 同じサービスが複数起動している

**解決方法**:
```bash
# すべて停止
./scripts/stop_ai_collaboration.sh

# PIDディレクトリをクリーンアップ
rm -rf .pids

# 再起動
./scripts/unified_startup.sh
```

### 問題3: Cursorでタスクが実行されない

**症状**: プロジェクトを開いてもタスクが実行されない

**解決方法**:
1. Cursor設定で「Tasks: Auto Run」が有効か確認
2. `.vscode/tasks.json`が存在するか確認
3. 手動でタスクを実行してエラーメッセージを確認

### 問題4: ポートが既に使用されている

**症状**: `Address already in use`エラー

**解決方法**:
```bash
# ポート8000を使用しているプロセスを確認
lsof -i :8000

# プロセスを停止
kill -9 <PID>

# または統合スクリプトで停止
./scripts/stop_ai_collaboration.sh
```

---

## 🎨 カスタマイズ

### 起動時に実行するサービスを変更

`startup_config.json`を編集：

```json
{
  "serena_settings": {
    "auto_start_serena": true  // falseで無効化
  },
  "codex_settings": {
    "auto_start_codex": true   // falseで無効化
  },
  "advanced_features": {
    "enable_real_time_monitoring": true  // ファイル監視
  }
}
```

### 起動遅延の設定

`.envrc`または`unified_startup.sh`でスリープ時間を調整：

```bash
# 起動確認待機時間（デフォルト3秒）
sleep 3  # → sleep 5 に変更
```

---

## 📝 ログファイル

| ファイル | 説明 | 場所 |
|---------|------|------|
| `.unified_startup.log` | 統合起動ログ | プロジェクトルート |
| `.direnv_startup.log` | direnv起動ログ | プロジェクトルート |
| `sync_log.json` | 同期履歴 | プロジェクトルート |
| `.pids/*.pid` | プロセスIDファイル | `.pids/` |

### ログ確認方法

```bash
# 統合起動ログ
tail -f .unified_startup.log

# direnv起動ログ
tail -f .direnv_startup.log

# 同期ログ
cat sync_log.json | python3 -m json.tool
```

---

## 🚀 ベストプラクティス

### 推奨セットアップ（ハイブリッド方式）

1. **direnvをメイン**として使用（全環境対応）
2. **Cursor Taskをサブ**として設定（Cursor専用の追加機能）
3. **手動起動スクリプト**を常備（緊急時用）

### セットアップ順序

```bash
# 1. direnvセットアップ
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
direnv allow .

# 2. 動作確認
./scripts/check_ai_collaboration_status.sh

# 3. Cursorでプロジェクトを開く
cursor .
```

---

## 🔐 セキュリティ考慮事項

### PIDファイルの管理

- `.pids/`ディレクトリは`.gitignore`に追加済み
- プロセス終了時に自動削除
- 古いPIDファイルは起動時にクリーンアップ

### 環境変数の分離

- `.envrc`はプロジェクト固有の環境変数を設定
- システム全体への影響なし
- ディレクトリを出ると設定が無効化

---

## 📞 サポート

### 動作確認チェックリスト

- [ ] direnvがインストールされている
- [ ] `.envrc`が許可されている（`direnv allow .`実行済み）
- [ ] `.vscode/tasks.json`が存在する
- [ ] スクリプトに実行権限がある（`chmod +x scripts/*.sh`）
- [ ] Python3が利用可能
- [ ] 必要なPythonパッケージがインストール済み

### 問題報告

問題が解決しない場合は、以下の情報を添えて報告してください：

```bash
# システム情報
uname -a
python3 --version
direnv version

# ログ出力
tail -20 .unified_startup.log
./scripts/check_ai_collaboration_status.sh
```

---

## 🎉 まとめ

このガイドに従うことで、以下が実現できます：

✅ **Claude Code/Cursor起動時の完全自動化**
✅ **重複起動の完全防止**
✅ **マルチレイヤー起動システムの構築**
✅ **統合管理による運用負荷の削減**
✅ **確実なプロセス追跡と状態管理**

**推奨設定**: direnv + Cursor Task のハイブリッド方式

---

## 📚 参考資料

- [direnv公式ドキュメント](https://direnv.net/)
- [VS Code Tasks](https://code.visualstudio.com/docs/editor/tasks)
- [Serena MCP Server](http://127.0.0.1:24282/dashboard/index.html)

---

**最終更新**: 2025年10月4日
**バージョン**: v3.0
**作成者**: AI協調分析システム開発チーム
