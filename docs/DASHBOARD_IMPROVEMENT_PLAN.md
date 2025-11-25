# ダッシュボード改善計画

**作成日**: 2025-11-26
**対象**: エピソードメインデータベース v6

## 現状分析

### 問題点

1. **ヒートマップデータ未生成** (解決済み)
   - `heatmap_data.json` が存在せず404エラー
   - → `scripts/generate_heatmap_data.py` で生成

2. **タイトル不整合** (解決済み)
   - HTML内タイトルが「v5」のまま
   - → 「v6 - 統合ダッシュボード」に修正

3. **サーバー起動の手動管理**
   - HTTPサーバー(8082)とAPIサーバー(8000)が必要
   - → `scripts/start_dashboard.sh` で統合管理

### 依存関係

```
ダッシュボードv6
├── HTTPサーバー (port:8082) - preserved/ 配信
│   ├── episode_database_dashboard_v6.html
│   ├── heatmap_data.json
│   └── data/MASTER_EPISODES_CURRENT.csv
├── APIサーバー (port:8000)
│   ├── /api/stats/summary
│   └── /api/data/version
└── CDN
    ├── Chart.js
    ├── PapaParse
    └── Plotly
```

## 実施済み改善

### Phase 1: 即時修正 ✅

1. **ヒートマップデータ生成スクリプト作成**
   - `scripts/generate_heatmap_data.py`
   - 年齢(14-75)×日(1-365)のマトリクス生成
   - カテゴリ別統計、充足率計算

2. **タイトル修正**
   - v5 → v6 - 統合ダッシュボード

3. **統合起動スクリプト作成**
   - `scripts/start_dashboard.sh`
   - サービス起動/停止/状態確認

### Phase 2: EPUP連携 ✅

1. **スラッシュコマンド追加**
   - `/epup-status` - ダッシュボード状態確認

## 今後の改善計画

### Phase 3: 堅牢性向上 (推奨)

1. **エラーハンドリング強化**
   - APIサーバーダウン時のフォールバック表示
   - CDN障害時のローカルライブラリ使用

2. **ヘルスチェック機能**
   - 定期的な依存サービス確認
   - 異常検知時の自動通知

3. **データ自動更新**
   - CSVファイル変更監視
   - ヒートマップデータ自動再生成

### Phase 4: パフォーマンス最適化

1. **データ圧縮**
   - ヒートマップデータのgzip圧縮
   - 差分更新対応

2. **キャッシュ戦略**
   - Service Worker導入
   - オフライン対応

### Phase 5: 監視・運用

1. **ログ収集**
   - アクセスログ
   - エラーログ

2. **アラート設定**
   - サービスダウン検知
   - データ更新失敗通知

## 運用手順

### 日常起動

```bash
# 状態確認
./scripts/start_dashboard.sh --check

# 起動
./scripts/start_dashboard.sh

# 停止
./scripts/start_dashboard.sh --stop
```

### データ更新

```bash
# ヒートマップデータ再生成
./venv/bin/python scripts/generate_heatmap_data.py --output preserved/heatmap_data.json

# CSVデータ更新後の反映
./scripts/start_dashboard.sh --generate
```

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| 404エラー | HTTPサーバー停止 | `./scripts/start_dashboard.sh` |
| ヒートマップ空白 | heatmap_data.json未生成 | `--generate` オプションで再生成 |
| API統計表示なし | APIサーバー停止 | バックエンド起動確認 |
| グラフ表示なし | CDN障害 | ブラウザキャッシュクリア |

## ファイル一覧

| ファイル | 用途 |
|----------|------|
| `preserved/episode_database_dashboard_v6.html` | ダッシュボード本体 |
| `preserved/heatmap_data.json` | ヒートマップデータ |
| `preserved/data/MASTER_EPISODES_CURRENT.csv` | エピソードCSV |
| `scripts/start_dashboard.sh` | 統合起動スクリプト |
| `scripts/generate_heatmap_data.py` | ヒートマップ生成 |
| `.claude/commands/epup-status.md` | 状態確認コマンド |

## アクセスURL

- **ダッシュボード**: http://localhost:8082/episode_database_dashboard_v6.html
- **API統計**: http://localhost:8000/api/stats/summary
- **バージョン情報**: http://localhost:8000/api/data/version
