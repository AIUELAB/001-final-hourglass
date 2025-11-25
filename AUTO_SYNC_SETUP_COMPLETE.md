# 🚀 Ultra Think 自動同期システム設定完了

## ✅ 自動同期監視システムが構築されました

### 📋 セットアップ内容

#### 1. **auto_sync_watcher.py** - メイン監視プログラム
- `ultra_think_*.csv`ファイルの変更を監視
- 変更検知後、5秒のクールダウン後に自動同期
- ハッシュチェックで実際の変更のみを検知
- 自動バックアップ機能（最大5世代保持）

#### 2. **auto_sync_config.json** - 設定ファイル
```json
{
  "watch_patterns": ["ultra_think_*.csv"],     // 監視対象
  "sync_cooldown": 5,                          // クールダウン時間（秒）
  "sync_script": "direct_sync.py",             // 同期スクリプト
  "auto_backup": true,                         // 自動バックアップ
  "max_backups": 5                             // バックアップ世代数
}
```

#### 3. **start_auto_sync.sh** - 起動スクリプト
- 3つの実行モードを提供
- 依存関係の自動チェック
- プロセス管理機能

### 🎯 使い方

#### 起動方法

```bash
# 起動スクリプトを実行
./start_auto_sync.sh

# 実行モードを選択:
# 1) フォアグラウンド - ログを表示（開発時推奨）
# 2) バックグラウンド - デーモン化（本番推奨）
# 3) テストモード - 1分間のテスト実行
```

#### 直接実行

```bash
# フォアグラウンドで実行
python auto_sync_watcher.py

# バックグラウンドで実行
nohup python auto_sync_watcher.py > auto_sync_watcher.log 2>&1 &
```

### 📝 動作フロー

1. **ファイル監視開始**
   - `ultra_think_*.csv`の変更を監視

2. **変更検知**
   - ファイルの作成、編集、移動を検知
   - ハッシュ値で実際の変更を確認

3. **デバウンス処理**
   - 5秒間の変更をまとめて処理
   - 連続した変更を効率的に処理

4. **自動バックアップ**
   - `backups/`ディレクトリに保存
   - 最大5世代を自動管理

5. **同期実行**
   - `direct_sync.py`を自動実行
   - Google Sheetsを更新

6. **通知**
   - 成功時: Glass.aiff音
   - エラー時: Sosumi.aiff音

### 📂 ファイル構成

```
001-final-hourglass/
├── auto_sync_watcher.py      # 監視プログラム
├── auto_sync_config.json     # 設定ファイル
├── start_auto_sync.sh        # 起動スクリプト
├── direct_sync.py            # 同期実行スクリプト
├── auto_sync_log.json        # 実行ログ
└── backups/                  # バックアップディレクトリ
    └── backup_*.csv          # 自動バックアップ
```

### 🔧 カスタマイズ

#### クールダウン時間の変更
`auto_sync_config.json`の`sync_cooldown`を編集（秒単位）

#### 監視パターンの変更
`watch_patterns`に追加のパターンを設定可能

#### バックアップ設定
- `auto_backup`: true/false でON/OFF
- `max_backups`: 保持する世代数

### 📊 ログ確認

```bash
# 実行ログを確認
cat auto_sync_log.json | jq .

# リアルタイムログ（バックグラウンド実行時）
tail -f auto_sync_watcher.log
```

### 🛑 停止方法

```bash
# フォアグラウンド実行時
Ctrl+C

# バックグラウンド実行時
pkill -f auto_sync_watcher.py

# PIDファイルを使用
kill $(cat auto_sync_watcher.pid)
```

### ⚡ クイックスタート

```bash
# 1. 起動
./start_auto_sync.sh
# モード1を選択（フォアグラウンド）

# 2. CSVファイルを編集
# 任意のultra_think_*.csvファイルを編集して保存

# 3. 自動同期を確認
# 5秒後に自動的にGoogle Sheetsと同期

# 4. ブラウザで確認
# 自動的にブラウザが開きGoogle Sheetsが表示される
```

### 🎉 セットアップ完了！

**これで、CSVファイルを編集するたびに自動的にGoogle Sheetsと同期されます。**

キャッシュクリアと完全置換により、常に最新のデータが反映されます。

---

作成日: 2025-08-31
Ultra Think 自動同期システム v2.0
