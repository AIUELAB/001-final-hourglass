# ダッシュボードデバッグ

Playwrightを使用してダッシュボードのDevTools情報を自動取得します。

## 実行内容

1. **コンソールログ取得** - JavaScript console.log/error/warning
2. **ネットワーク監視** - リクエスト/レスポンス、失敗したリクエスト
3. **JavaScript状態** - allEpisodes, filteredEpisodes等の変数
4. **DOM状態** - テーブル行数、結果件数
5. **スクリーンショット** - 全ページキャプチャ

## コマンド

```bash
# 基本デバッグ（ブラウザ表示あり）
./venv/bin/python scripts/dashboard_debug.py

# ヘッドレスモード（バックグラウンド）
./venv/bin/python scripts/dashboard_debug.py --headless

# 全機能（パフォーマンス・メモリ・Lighthouse）
./venv/bin/python scripts/dashboard_debug.py --full --headless

# パフォーマンス分析のみ
./venv/bin/python scripts/dashboard_debug.py --performance --headless

# メモリ分析のみ
./venv/bin/python scripts/dashboard_debug.py --memory --headless

# Lighthouse監査（簡易版）
./venv/bin/python scripts/dashboard_debug.py --lighthouse --headless

# 継続監視モード（30秒間隔）
./venv/bin/python scripts/dashboard_debug.py --watch --interval 30

# カスタムURL
./venv/bin/python scripts/dashboard_debug.py --url "http://localhost:8082/other_page.html"
```

## 出力先

- スクリーンショット: `logs/dashboard_debug/screenshot_YYYYMMDD_HHMMSS.png`
- レポート: `logs/dashboard_debug/debug_report_YYYYMMDD_HHMMSS.json`

## 取得可能な情報

| 項目 | DevToolsタブ | 取得内容 |
|------|-------------|----------|
| コンソール | Console | log/error/warning/info |
| ネットワーク | Network | リクエスト/レスポンス/ステータス |
| パフォーマンス | Performance | Web Vitals, リソースタイミング |
| メモリ | Memory | JSヒープ使用量, DOM統計 |
| 要素 | Elements | DOM状態, テーブル行数 |
| アプリケーション | Application | （対応予定） |
| Lighthouse | Lighthouse | アクセシビリティ, SEO, ベストプラクティス |

## 自動チェック項目

- ✅ CSVデータ読み込み成功
- ✅ JavaScript変数の状態
- ✅ テーブルレンダリング完了
- ⚠️ CORSエラー
- ❌ ネットワークエラー
