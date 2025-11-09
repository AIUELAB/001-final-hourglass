# Railway デプロイ手順書 - 最期の砂時計

## 📋 目次

1. [前提条件](#前提条件)
2. [Railwayアカウント作成](#railwayアカウント作成)
3. [バックエンドのデプロイ](#バックエンドのデプロイ)
4. [環境変数の設定](#環境変数の設定)
5. [デプロイ確認](#デプロイ確認)
6. [トラブルシューティング](#トラブルシューティング)

## 前提条件

### 必要なもの

- Gitリポジトリ（GitHub、GitLab、Bitbucket）
- Railwayアカウント（無料プランで開始可能）
- プロジェクトがGitにプッシュ済み

### 確認事項

```bash
# プロジェクトルートで以下を確認
ls backend/
# app/, requirements.txt, .env.example が存在すること

# Gitリポジトリの確認
git remote -v
# origin が設定されていること
```

## Railwayアカウント作成

### 1. サインアップ

1. [Railway](https://railway.app) にアクセス
2. 「Start a New Project」をクリック
3. GitHubアカウントで認証
   - または、メールアドレスでサインアップ

### 2. 無料プラン

- **$5クレジット/月**（無料枠）
- クレジットカード登録不要でスタート可能
- 小規模プロジェクトに十分な容量

## バックエンドのデプロイ

### ステップ1: 新規プロジェクト作成

1. Railwayダッシュボードで「New Project」をクリック
2. 「Deploy from GitHub repo」を選択
3. リポジトリを選択
   - **リポジトリ名**: `001-final-hourglass`
   - **ブランチ**: `main` （またはデプロイ対象ブランチ）

### ステップ2: ビルド設定

Railwayは自動的に以下を検出します：

**検出される設定**:
```yaml
言語: Python
フレームワーク: FastAPI (uvicornで起動)
ルートディレクトリ: backend/
依存関係: requirements.txt
```

**カスタム設定が必要な場合**:

`railway.toml` を作成（オプション）:

```toml
[build]
builder = "NIXPACKS"
buildCommand = "cd backend && pip install -r requirements.txt"

[deploy]
startCommand = "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

または `Procfile` を作成:

```
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### ステップ3: デプロイ実行

1. 「Deploy」ボタンをクリック
2. ビルドログを確認
   ```
   ✓ Building...
   ✓ Installing dependencies
   ✓ Starting application
   ✓ Deployment successful
   ```

3. デプロイURLを取得
   ```
   https://your-backend-production.up.railway.app
   ```

## 環境変数の設定

### 必須の環境変数

Railwayダッシュボード → Variables タブで設定：

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `ENVIRONMENT` | `production` | 本番環境であることを明示 |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | フロントエンドのURL（カンマ区切りで複数可） |
| `PORT` | `8000` | ポート番号（自動設定される場合あり） |
| `HOST` | `0.0.0.0` | すべてのネットワークインターフェースで待ち受け |

### オプションの環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `SECRET_KEY` | `your-secret-key` | セッション管理用（将来の機能拡張用） |
| `LOG_LEVEL` | `INFO` | ログレベル |
| `CSV_DATA_PATH` | `./data/final_characters.csv` | データファイルパス |
| `DATABASE_URL` | `sqlite:///./characters.db` | データベースURL |

### 設定手順

1. Railwayダッシュボード → プロジェクト選択
2. 「Variables」タブをクリック
3. 「New Variable」で1つずつ追加

**例**:
```
変数名: ENVIRONMENT
値: production
[Add]をクリック
```

4. すべての変数を追加後、自動的に再デプロイされます

### CORS設定の重要性

**複数のフロントエンドURLを許可する場合**:

```
CORS_ORIGINS=https://your-app.vercel.app,https://your-app-preview.vercel.app,https://your-app.netlify.app
```

- カンマ区切りで複数のURLを指定
- スペースは入れない
- 本番URLとプレビューURLを両方含める

## デプロイ確認

### 1. デプロイステータス確認

Railwayダッシュボードで以下を確認：

- **Status**: Active（緑色）
- **Replicas**: 1/1
- **Last Deploy**: 成功したタイムスタンプ

### 2. アプリケーション動作確認

デプロイURLにアクセス：

```bash
# ブラウザで開く
https://your-backend-production.up.railway.app/docs

# または curlで確認
curl https://your-backend-production.up.railway.app/docs
```

**期待される表示**:
- Swagger UI（FastAPI自動生成APIドキュメント）
- `/api/characters` などのエンドポイント一覧

### 3. APIエンドポイント確認

Swagger UIで以下のエンドポイントをテスト：

**GET /api/characters**
```bash
curl https://your-backend-production.up.railway.app/api/characters?page=1&per_page=10
```

**期待されるレスポンス**:
```json
{
  "items": [...],
  "total": 14000,
  "page": 1,
  "per_page": 10,
  "pages": 1400
}
```

**GET /api/statistics/summary**
```bash
curl https://your-backend-production.up.railway.app/api/statistics/summary
```

**期待されるレスポンス**:
```json
{
  "total_characters": 14000,
  "total_genres": 8,
  "female_count": 5000,
  "female_ratio": 35.7
}
```

### 4. ログ確認

Railwayダッシュボード → 「Logs」タブで確認：

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## トラブルシューティング

### ビルドエラー: 依存関係のインストール失敗

**症状**:
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解決策**:
1. `requirements.txt` のバージョン指定を確認
2. ローカルで `pip install -r backend/requirements.txt` が成功するか確認
3. Python バージョンを明示的に指定

`railway.toml` に追加:
```toml
[build]
pythonVersion = "3.11"
```

### 起動エラー: アプリケーションが起動しない

**症状**:
```
Error: Application failed to start
```

**解決策**:

1. **ルートディレクトリの確認**
   ```toml
   [deploy]
   startCommand = "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
   ```

2. **環境変数の確認**
   - `PORT` が設定されているか
   - `HOST` が `0.0.0.0` に設定されているか

3. **ログの確認**
   - Railwayのログで詳細なエラーメッセージを確認

### CORSエラー: フロントエンドから接続できない

**症状**:
```
Access to fetch has been blocked by CORS policy
```

**解決策**:

1. `CORS_ORIGINS` 環境変数を確認
   ```
   CORS_ORIGINS=https://your-app.vercel.app
   ```

2. フロントエンドのURLが正確か確認
   - `https://` を忘れずに
   - 末尾のスラッシュは不要
   - プレビューURLも含める場合はカンマ区切り

3. 再デプロイを実行
   - 環境変数変更後は自動的に再デプロイされる
   - または手動で「Redeploy」をクリック

### データベースファイルが見つからない

**症状**:
```
FileNotFoundError: [Errno 2] No such file or directory: './data/final_characters.csv'
```

**解決策**:

1. **ファイルの配置確認**
   ```bash
   # リポジトリに以下が含まれているか確認
   backend/data/final_characters.csv
   ```

2. **パスの修正**
   - 相対パスではなく絶対パスを使用
   - または環境変数で指定

3. **データベースの初期化**
   - アプリケーション起動時にCSVからデータベースを自動作成
   - `app/main.py` の `@app.on_event("startup")` を確認

### デプロイが遅い、または頻繁に失敗する

**症状**:
- デプロイに10分以上かかる
- タイムアウトエラーが発生

**解決策**:

1. **依存関係の最適化**
   ```bash
   # 不要なパッケージを削除
   pip freeze > requirements.txt
   # 必要なパッケージのみに絞る
   ```

2. **キャッシュの活用**
   - Railwayは依存関係を自動的にキャッシュ
   - `requirements.txt` を頻繁に変更しない

3. **リソース使用量の確認**
   - 無料プランの制限を確認
   - 必要に応じて有料プランにアップグレード

### Railway URL変更時の対応

**RailwayのURLが変更された場合**:

1. 新しいURLを確認
2. フロントエンドの環境変数を更新
   ```
   VITE_API_BASE_URL=https://new-backend-url.railway.app/api
   ```
3. フロントエンドを再デプロイ

## まとめ

### デプロイ完了チェックリスト

- [ ] Railwayプロジェクト作成完了
- [ ] バックエンドのデプロイ成功
- [ ] 環境変数の設定完了（特に `CORS_ORIGINS`）
- [ ] Swagger UIにアクセス可能
- [ ] APIエンドポイントが正常に動作
- [ ] ログにエラーがないことを確認
- [ ] フロントエンドから接続可能（CORS設定確認）

### 次のステップ

1. **フロントエンドのデプロイ**
   - Vercel または Netlify にデプロイ
   - `VITE_API_BASE_URL` に Railway の URL を設定

2. **カスタムドメインの設定**（オプション）
   - Railway で独自ドメインを設定
   - DNS 設定を更新

3. **監視とログ**
   - Railway のログを定期的に確認
   - エラーが発生した場合は即座に対応

## リソース

- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)

---

**注意**: Railway の無料プランは $5 クレジット/月です。使用量が超過する場合は有料プランへのアップグレードを検討してください。
