# IDEキャッシュクリア自動化ツール

このツールは、IDEのキャッシュを自動的にクリアして、削除済みファイルのエラー表示問題を解決します。

## 🚀 機能

- **自動IDE検出**: Cursor、VS Code、IntelliJ IDEA、PyCharmを自動検出
- **キャッシュクリア**: 各IDEのキャッシュディレクトリを自動削除
- **ファイル削除監視**: ファイル削除を監視し、自動的にキャッシュクリアを実行
- **IDE再起動**: オプションでIDEの自動再起動
- **ログ記録**: 詳細なログファイルを生成

## 📦 インストール

```bash
# 依存関係をインストール
pip install -r requirements.txt
```

## 🛠️ 使用方法

### 1. 手動キャッシュクリア

```bash
# 基本的なキャッシュクリア
python auto_cache_cleaner.py

# または個別スクリプト
python clear_ide_cache.py
```

### 2. ファイル削除監視モード

```bash
# 監視モードを開始（自動キャッシュクリア）
python auto_cache_cleaner.py --monitor

# 自動再起動付き監視モード
python auto_cache_cleaner.py --monitor --auto-restart
```

### 3. 個別スクリプト

```bash
# ファイル削除監視のみ
python file_deletion_monitor.py
```

## ⚙️ 設定

`monitor_config.json`で監視設定をカスタマイズできます：

```json
{
  "target_directories": [".", "src", "docs"],
  "auto_restart": false,
  "cleanup_cooldown": 30,
  "monitored_extensions": [".md", ".py", ".ts", ".tsx"],
  "excluded_directories": ["node_modules", ".git", "venv"]
}
```

## 📁 ファイル構成

```text
scripts/
├── auto_cache_cleaner.py      # 統合スクリプト
├── clear_ide_cache.py         # IDEキャッシュクリア
├── file_deletion_monitor.py    # ファイル削除監視
├── monitor_config.json        # 監視設定
├── requirements.txt           # 依存関係
└── README.md                  # このファイル
```

## 🔧 対応IDE

- **Cursor**: `~/Library/Application Support/Cursor/`
- **VS Code**: `~/Library/Application Support/Code/`
- **IntelliJ IDEA**: `~/Library/Caches/JetBrains/`
- **PyCharm**: `~/Library/Caches/PyCharm*/`

## 📊 ログファイル

- `ide_cache_clear.log`: キャッシュクリアのログ
- `file_deletion_monitor.log`: ファイル削除監視のログ
- `auto_cache_cleaner.log`: 統合ツールのログ

## ⚠️ 注意事項

1. **権限**: キャッシュディレクトリの削除には適切な権限が必要です
2. **IDE再起動**: 自動再起動時は作業中のファイルを保存してください
3. **監視モード**: 長時間の監視はシステムリソースを使用します
4. **クールダウン**: 連続したキャッシュクリアを防ぐため30秒のクールダウンがあります

## 🐛 トラブルシューティング

### 権限エラー

```bash
# スクリプトに実行権限を付与
chmod +x *.py
```

### 依存関係エラー

```bash
# 依存関係を再インストール
pip install --upgrade -r requirements.txt
```

### IDEが検出されない

- IDEが正しくインストールされているか確認
- アプリケーションフォルダにIDEが存在するか確認

## 🤝 貢献

バグ報告や機能要望は、ログファイルと共に報告してください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
