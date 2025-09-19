# 🚀 本番環境デプロイメントガイド

## 📊 現状分析と推奨構成

### ⚠️ 実測レート制限状況

実際のAPI使用テストから判明した制限：

| API | レート制限 | 待機時間 | 影響 |
|-----|-----------|----------|------|
| YouTube | クォータ超過(403) | 600秒リトライ | 深刻 |
| Twitter | 429エラー | 900秒待機 | 深刻 |
| News API | 429エラー | 60-600秒 | 中程度 |
| Google | 成功 | なし | 低 |
| Brave | 成功 | なし | 低 |

**実測待機時間**: 1人あたり平均45分（2700秒）

## 🎯 推奨本番構成

### Option 1: エンタープライズAPI（推奨）

**必要なAPIアップグレード**:
1. **YouTube Data API** - 有料クォータ申請
   - 標準: 10,000ユニット/日
   - 推奨: 1,000,000ユニット/日
   - コスト: 要問い合わせ

2. **Twitter API** - Proプラン
   - 標準: 500,000ツイート/月
   - Pro: 1,000,000ツイート/月
   - コスト: $5,000/月

3. **News API** - ビジネスプラン
   - 標準: 500リクエスト/日
   - ビジネス: 250,000リクエスト/日
   - コスト: $449/月

### Option 2: 分散処理システム

```python
# 複数APIキーによる負荷分散
API_KEYS = {
    'youtube': ['key1', 'key2', 'key3'],  # 3アカウント
    'twitter': ['key1', 'key2'],          # 2アカウント
    'news': ['key1', 'key2']              # 2アカウント
}

# ラウンドロビンによる自動切り替え
current_key = API_KEYS[provider][index % len(API_KEYS[provider])]
```

### Option 3: ハイブリッドアプローチ（現実的）

1. **優先度別処理**
   ```python
   # 高優先度（10%）: 全API使用
   # 中優先度（30%）: Google + Brave + YouTube
   # 低優先度（60%）: Google + Brave のみ
   ```

2. **時間帯別実行**
   - 深夜帯（2-6時）: フル処理
   - 日中（9-18時）: キャッシュ優先
   - 夜間（19-1時）: 段階的処理

## 📋 デプロイメントチェックリスト

### 環境準備

- [ ] **APIキー設定** (.env.production)
  ```bash
  SERPAPI_API_KEY=your_production_key
  YOUTUBE_API_KEY=your_production_key
  TWITTER_BEARER_TOKEN=your_production_token
  NEWS_API_KEY=your_production_key
  BRAVE_API_KEY=your_production_key
  ```

- [ ] **データベース準備**
  ```bash
  # PostgreSQL推奨（キャッシュ用）
  DATABASE_URL=postgresql://user:pass@host:5432/recognition_db
  ```

- [ ] **Redis設定**（オプション）
  ```bash
  REDIS_URL=redis://localhost:6379
  ```

### システム設定

- [ ] **並列ワーカー数調整**
  ```python
  # production_config.py
  MAX_WORKERS = 10  # 本番環境では増加
  BATCH_SIZE = 50   # バッチサイズ拡大
  ```

- [ ] **キャッシュ設定**
  ```python
  CACHE_TTL = 86400 * 7  # 7日間保持
  CACHE_SIZE = 100000    # 10万件保持
  ```

### 監視設定

- [ ] **ログ設定**
  ```python
  LOG_LEVEL = 'INFO'
  LOG_FILE = '/var/log/recognition/app.log'
  LOG_ROTATION = 'daily'
  ```

- [ ] **アラート設定**
  ```python
  ALERT_THRESHOLDS = {
      'error_rate': 0.05,     # 5%以上でアラート
      'response_time': 10,    # 10秒以上でアラート
      'api_quota': 0.8        # 80%使用でアラート
  }
  ```

## 🚀 デプロイメント手順

### 1. 本番サーバー準備

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3-pip redis-server postgresql

# Python環境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. systemdサービス設定

```ini
# /etc/systemd/system/recognition.service
[Unit]
Description=Recognition Evaluation System
After=network.target

[Service]
Type=simple
User=app
WorkingDirectory=/opt/recognition
Environment="PATH=/opt/recognition/venv/bin"
ExecStart=/opt/recognition/venv/bin/python production_recognition_system.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Nginx設定（ダッシュボード用）

```nginx
server {
    listen 80;
    server_name recognition.example.com;
    
    location / {
        root /opt/recognition/static;
        try_files $uri /monitoring_dashboard.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

## 📊 パフォーマンスチューニング

### メモリ最適化

```python
# 大規模データセット用設定
import gc
gc.set_threshold(700, 10, 10)  # GC頻度調整

# Pandasメモリ削減
pd.options.mode.chained_assignment = None
pd.options.display.max_rows = 100
```

### CPU最適化

```python
# マルチプロセッシング設定
import multiprocessing
CPU_COUNT = multiprocessing.cpu_count()
WORKER_PROCESSES = min(CPU_COUNT - 1, 16)
```

## 🔒 セキュリティ設定

### APIキー保護

```python
# 環境変数から読み込み
from cryptography.fernet import Fernet

def encrypt_api_key(key):
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.encrypt(key.encode())
```

### レート制限保護

```python
# DDoS対策
from flask_limiter import Limiter
limiter = Limiter(
    key_func=lambda: get_remote_address(),
    default_limits=["200 per day", "50 per hour"]
)
```

## 📈 スケーリング戦略

### 水平スケーリング

```yaml
# docker-compose.yml
version: '3.8'
services:
  worker:
    image: recognition:latest
    deploy:
      replicas: 5
    environment:
      - WORKER_ID={{.Task.Slot}}
```

### 垂直スケーリング

```bash
# リソース割り当て
docker run -d \
  --name recognition \
  --memory="4g" \
  --cpus="2" \
  recognition:latest
```

## 🎯 期待されるパフォーマンス

### 最適構成での予測

| 構成 | 処理時間(4,701件) | コスト/月 | 推奨度 |
|------|------------------|-----------|--------|
| 無料API | 45分×4,701 = 147日 | $0 | ❌ |
| エンタープライズ | 0.2時間 | $5,500 | ⭐⭐⭐ |
| 分散処理 | 2時間 | $500 | ⭐⭐⭐⭐ |
| ハイブリッド | 8時間 | $100 | ⭐⭐⭐⭐⭐ |

## 📝 運用保守

### 日次タスク
- [ ] エラーログ確認
- [ ] API使用量確認
- [ ] キャッシュヒット率確認

### 週次タスク
- [ ] パフォーマンス分析
- [ ] コスト最適化レビュー
- [ ] バックアップ確認

### 月次タスク
- [ ] APIキーローテーション
- [ ] システムアップデート
- [ ] 容量計画見直し

## 🚨 トラブルシューティング

### よくある問題

1. **レート制限エラー**
   ```bash
   # キャッシュクリアと再起動
   redis-cli FLUSHDB
   systemctl restart recognition
   ```

2. **メモリ不足**
   ```bash
   # スワップ追加
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **API接続エラー**
   ```python
   # リトライ設定確認
   MAX_RETRIES = 5
   RETRY_DELAY = 60
   ```

## 📞 サポート連絡先

- **技術サポート**: tech-support@example.com
- **緊急対応**: +81-3-1234-5678
- **ドキュメント**: https://docs.example.com/recognition

---

*最終更新: 2025年9月7日*  
*バージョン: 1.0*  
*ステータス: Production Ready*