# EPUP ダッシュボード状態確認

エピソードデータベースダッシュボード v6 の状態を確認し、問題があれば自動修復します。

## 確認項目

1. **HTTPサーバー (port:8082)**
   - preserved/ ディレクトリを配信中か確認
   - 停止していれば起動

2. **APIサーバー (port:8000)**
   - /api/stats/summary エンドポイント確認
   - /api/data/version エンドポイント確認

3. **ヒートマップデータ**
   - preserved/heatmap_data.json の存在確認
   - 24時間以上古い場合は再生成

4. **CSVデータ**
   - data/MASTER_EPISODES_CURRENT.csv の存在確認

## 実行コマンド

```bash
./scripts/start_dashboard.sh --check
```

## 自動修復

問題が見つかった場合:

```bash
./scripts/start_dashboard.sh
```

## ダッシュボードURL

http://localhost:8082/episode_database_dashboard_v6.html

## 関連ファイル

- scripts/start_dashboard.sh - 統合起動スクリプト
- scripts/generate_heatmap_data.py - ヒートマップデータ生成
- preserved/episode_database_dashboard_v6.html - ダッシュボード本体
