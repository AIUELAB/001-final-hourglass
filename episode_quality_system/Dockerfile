# マルチステージビルドで軽量化
FROM python:3.11-slim as builder

# 作業ディレクトリ設定
WORKDIR /build

# システムパッケージのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ランタイムステージ
FROM python:3.11-slim

# セキュリティ: 非rootユーザーの作成
RUN useradd -m -u 1000 episodeuser && \
    mkdir -p /app /logs /data && \
    chown -R episodeuser:episodeuser /app /logs /data

# 作業ディレクトリ設定
WORKDIR /app

# Pythonパッケージをコピー
COPY --from=builder --chown=episodeuser:episodeuser /root/.local /home/episodeuser/.local

# アプリケーションファイルをコピー
COPY --chown=episodeuser:episodeuser unified_episode_factory_v2.py .
COPY --chown=episodeuser:episodeuser optimized_validation_system.py .
COPY --chown=episodeuser:episodeuser expanded_episode_templates.py .
COPY --chown=episodeuser:episodeuser mandatory_pipeline.py .
COPY --chown=episodeuser:episodeuser auto_fact_injector.py .
COPY --chown=episodeuser:episodeuser complete_person_facts.json .
COPY --chown=episodeuser:episodeuser health_check_server.py .

# 環境変数設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/episodeuser/.local/bin:${PATH}" \
    EPISODE_FACTORY_ENV=production \
    VALIDATION_MODE=optimized \
    MIN_QUALITY_SCORE=70.0 \
    MAX_ATTEMPTS=5 \
    USE_CACHE=true \
    LOG_LEVEL=INFO

# ヘルスチェック設定
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# ユーザー切り替え
USER episodeuser

# ポート公開
EXPOSE 8000 9090

# デフォルトコマンド
CMD ["python3", "health_check_server.py", "--port", "8000"]