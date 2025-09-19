# n8n統合システム

## 概要

このシステムは、n8nワークフローエンジンとDockerコンテナを統合監視するWebアプリケーションです。

## ディレクトリ構造

```text
n8n_integration/
├── README.md                    # このファイル
├── config/
│   ├── n8n_config.py           # n8n設定管理
│   ├── docker_config.py        # Docker設定管理
│   └── app_config.py           # アプリケーション設定
├── services/
│   ├── n8n_service.py          # n8n API操作サービス
│   ├── docker_service.py       # Docker操作サービス
│   └── workflow_service.py     # ワークフロー管理サービス
├── models/
│   ├── workflow_model.py       # ワークフローデータモデル
│   ├── execution_model.py      # 実行履歴データモデル
│   └── container_model.py      # コンテナデータモデル
├── api/
│   ├── n8n_routes.py          # n8n APIルート
│   ├── docker_routes.py       # Docker APIルート
│   └── workflow_routes.py     # ワークフロー操作ルート
├── utils/
│   ├── n8n_helpers.py         # n8n操作ヘルパー
│   ├── docker_helpers.py      # Docker操作ヘルパー
│   └── validation.py          # データ検証
├── tests/
│   ├── test_n8n_service.py    # n8nサービステスト
│   ├── test_workflow_service.py # ワークフローサービステスト
│   └── test_docker_service.py # Dockerサービステスト
└── examples/
    ├── sample_workflows/       # サンプルワークフロー
    ├── automation_scripts/     # 自動化スクリプト
    └── integration_examples/   # 統合例
```

## 主要機能

### 1. n8nワークフロー管理

- ワークフローの作成・編集・削除
- ワークフローの有効化・無効化
- ワークフローの実行・スケジュール
- 実行履歴の監視・分析

### 2. Dockerコンテナ監視

- コンテナの起動・停止・再起動
- リソース使用量の監視
- ログの収集・表示
- ヘルスチェック

### 3. 統合機能

- ワークフローとコンテナの連携
- 自動化ルールの設定
- アラート・通知システム
- ダッシュボード表示

## 設定方法

### 1. 環境変数

```bash
export N8N_BASE_URL=http://localhost:5678
export N8N_API_KEY=your_api_key_here
export DOCKER_HOST=unix:///var/run/docker.sock
```

### 2. n8n接続設定

```python
# config/n8n_config.py
N8N_CONFIG = {
    'base_url': 'http://localhost:5678',
    'api_key': None,  # 環境変数から取得
    'timeout': 30,
    'retry_attempts': 3
}
```

## 使用方法

### 1. アプリケーション起動

```bash
python app.py
```

### 2. APIエンドポイント

- `GET /api/n8n/workflows` - ワークフロー一覧取得
- `POST /api/n8n/workflows/{id}/activate` - ワークフロー有効化
- `POST /api/n8n/workflows/{id}/execute` - ワークフロー実行
- `GET /api/n8n/executions` - 実行履歴取得

### 3. フロントエンド

- ブラウザで `http://localhost:5000` にアクセス
- サイドバーでセクション切り替え
- リアルタイム監視・操作

## 開発ガイド

### 1. 新機能追加

1. `services/` にサービスクラスを作成
2. `models/` にデータモデルを定義
3. `api/` にAPIルートを追加
4. フロントエンドUIを更新
5. テストを作成

### 2. テスト実行

```bash
python -m pytest tests/
```

### 3. コード品質チェック

```bash
flake8 n8n_integration/
mypy n8n_integration/
```

## トラブルシューティング

### よくある問題

1. **n8n接続エラー**: APIキーとベースURLを確認
2. **Docker接続エラー**: Dockerデーモンの起動状態を確認
3. **権限エラー**: 適切なユーザー権限を設定

### ログ確認

```bash
tail -f logs/app.log
```

## 今後の拡張予定

### 短期目標

- [ ] ワークフローエディタの統合
- [ ] スケジュール機能の強化
- [ ] 通知システムの改善

### 長期目標

- [ ] マルチテナント対応
- [ ] クラウド統合
- [ ] AI支援ワークフロー生成

## 貢献方法

1. このリポジトリをフォーク
2. 機能ブランチを作成
3. 変更をコミット
4. プルリクエストを作成

## ライセンス

MIT License
