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

## 作業タイプ別ガイド

### 1. ダッシュボードのバージョンアップ
```bash
# 現在の正規版を確認
python scripts/check_single_dashboard.py

# 新バージョン作成（例: v7 → v8）
# 1. preserved/episode_database_dashboard_v8.html を作成
# 2. 旧版を archive/dashboards/ に移動
# 3. ファイル名・title・h1 のバージョン番号を同期

# ヒートマップデータ更新
python scripts/generate_heatmap_data.py --embed --html preserved/episode_database_dashboard_v8.html
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
