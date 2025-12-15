---
description: 新規エピソードDB作業（ダッシュボード更新・データ追加・バージョンアップ）
---

# new-epdb Skill（Episode Database Management）

## 目的
エピソードデータベースの**新規作業**（ダッシュボード更新、データ追加、バージョンアップ）を支援します。

## 重要制約（EPUP共通）
- **低コンテキスト運用**: 大きいファイルの全文貼り付け禁止
- **自動修正は勝手にしない**: 書き換え操作は必ずユーザー承認後
- **単一マスター原則**: CSVは `preserved/data/MASTER_EPISODES_CURRENT.csv` のみ

## 正規ファイルパス（必ず確認）

| 種別 | 正規パス |
|------|----------|
| **マスターCSV** | `preserved/data/MASTER_EPISODES_CURRENT.csv` |
| **ダッシュボード** | `preserved/episode_database_dashboard_v*.html` |
| **旧バージョン保存先** | `archive/dashboards/` |

## 🚨 バージョンアップ重要ルール

### ❌ 絶対禁止
- **ユーザーからの明示的な指示がない限り、バージョンアップは実行しない**
- 勝手にバージョン番号を上げる行為は厳禁

### ✅ バージョンアップが許可される条件
- ユーザーが「バージョンを上げて」「v9にして」などと明示的に指示した場合のみ

## 📡 ダッシュボードアクセス方法

### ✅ 正しい方法（HTTPサーバー経由）

```bash
# プロジェクトルートで実行
# プロジェクト定義のポート範囲: 8000-8082（推奨）
python -m http.server 8082  # ダッシュボード用推奨ポート
# または
python -m http.server 8081  # 代替ポート
python -m http.server 8080  # 代替ポート

# 起動メッセージで実際のポート番号を確認
# 例: Serving HTTP on 0.0.0.0 port 8082 (http://0.0.0.0:8082/) ...

# ブラウザでアクセス（実際のポート番号を使用）
http://localhost:8082/preserved/episode_database_dashboard_v8.html
```

**プロジェクト定義のポート範囲：**

| ポート | 用途 | 優先度 |
|--------|------|--------|
| **8082** | HTTPサーバー（ダッシュボード配信） | ✅ 推奨 |
| **8081** | HTTPサーバー代替 | ⭕ 推奨 |
| **8080** | HTTPサーバー代替 | ⭕ 推奨 |
| **8000** | FastAPI バックエンド | ⚠️ API用に予約 |

**注意事項：**

- **8000番はFastAPI用に予約されているため避ける**
- 8082番が推奨（ダッシュボード専用）
- 使用中の場合は8081, 8080を使用
- 起動時のメッセージで実際のポート番号を必ず確認

**詳細参照：** `docs/EPISODE_DB_STARTUP_GUIDE.md` - ポート番号の詳細仕様

### ❌ 禁止方法（file://プロトコル）

```text
file:///Users/.../episode_database_dashboard_v8.html
→ CORS制限によりCSVファイル読み込み不可
→ JavaScriptの機能が制限され、ダッシュボードが正常に動作しない
```

**理由：**

- CORS（Cross-Origin Resource Sharing）制限
- fetch API制限
- ローカルファイルアクセス制限

## 作業タイプ別ガイド

### 1. ダッシュボードのバージョンアップ

**🔴 前提条件：ユーザーからの明示的な指示があること**

```bash
# 現在の正規版を確認
python scripts/check_single_dashboard.py

# 新バージョン作成（例: v7 → v8）
# 1. preserved/episode_database_dashboard_v8.html を作成
# 2. 旧版を archive/dashboards/ に移動
# 3. ファイル名・title・h1 のバージョン番号を同期

# ヒートマップデータ更新
python scripts/generate_heatmap_data.py --embed --html preserved/episode_database_dashboard_v8.html

# HTTPサーバー起動して動作確認
python -m http.server 8082  # ダッシュボード用推奨ポート
# 起動メッセージでポート番号を確認してブラウザでアクセス
# → http://localhost:8082/preserved/episode_database_dashboard_v8.html
```

### 2. エピソードデータ追加
```bash
# 事前チェック（単一マスター確認）
python scripts/check_single_master.py

# CSV編集後の品質チェック
python scripts/scheduled_epup_check.py --daily --csv preserved/data/MASTER_EPISODES_CURRENT.csv

# 問題があれば修正スクリプト実行（承認後）
```

### 3. ヒートマップ/統計更新
```bash
# ヒートマップデータ生成
python scripts/generate_heatmap_data.py --output preserved/heatmap_data.json

# ダッシュボードに埋め込み
python scripts/generate_heatmap_data.py --embed
```

## 整合性チェック（作業前後に実行）
```bash
python scripts/check_single_master.py      # CSV整合性
python scripts/check_single_dashboard.py   # ダッシュボード整合性
```

## 出力フォーマット
### 現状確認結果
### 実行した操作
### 次のアクション提案
