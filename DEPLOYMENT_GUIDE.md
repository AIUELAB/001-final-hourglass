# デプロイガイド - 最期の砂時計

本番環境へのデプロイ手順を説明します。

## 📋 目次

1. [前提条件](#前提条件)
2. [バックエンドのデプロイ（Railway）](#バックエンドのデプロイrailway)
3. [バックエンドのデプロイ（Render）](#バックエンドのデプロイrender)
4. [フロントエンドのデプロイ（Vercel）](#フロントエンドのデプロイvercel)
5. [フロントエンドのデプロイ（Netlify）](#フロントエンドのデプロイnetlify)
6. [環境変数の設定](#環境変数の設定)
7. [デプロイ後の確認](#デプロイ後の確認)

## 前提条件

- Node.js 18+ がインストール済み
- Python 3.11+ がインストール済み
- Git リポジトリが作成済み
- 各サービスのアカウント作成済み

## バックエンドのデプロイ（Railway）

### 1. Railwayプロジェクトの作成

1. [Railway](https://railway.app) にログイン
2. 「New Project」をクリック
3. 「Deploy from GitHub repo」を選択
4. リポジトリを選択

### 2. 環境変数の設定

Railwayダッシュボード > Variables で以下を設定：

```env
# 必須
ENVIRONMENT=production
CORS_ORIGINS=https://your-app.vercel.app,https://your-app.netlify.app

# オプション（デフォルト値が使用される）
PORT=8000
HOST=0.0.0.0
```

### 3. ビルド設定

Railway はデフォルトで以下を実行：

```bash
# インストール
pip install -r backend/requirements.txt

# 起動コマンド
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Procfile** を作成（オプション）：

```
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 4. デプロイURL確認

デプロイ完了後、Railway が提供する URL をコピー：
```
https://your-backend.railway.app
```

## バックエンドのデプロイ（Render）

### 1. Renderサービスの作成

1. [Render](https://render.com) にログイン
2. 「New +」→「Web Service」を選択
3. リポジトリを接続

### 2. ビルド設定

- **Name**: `saigo-no-sunadokei-backend`
- **Root Directory**: `backend`
- **Environment**: Python 3
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### 3. 環境変数の設定

Environment タブで設定：

```env
ENVIRONMENT=production
CORS_ORIGINS=https://your-app.vercel.app
PORT=8000
```

### 4. デプロイ

「Create Web Service」をクリックしてデプロイ開始

## フロントエンドのデプロイ（Vercel）

### 1. Vercelプロジェクトの作成

1. [Vercel](https://vercel.com) にログイン
2. 「New Project」をクリック
3. リポジトリをインポート

### 2. ビルド設定

- **Framework Preset**: Vite
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### 3. 環境変数の設定

Environment Variables で設定：

```env
VITE_API_BASE_URL=https://your-backend.railway.app/api
VITE_APP_NAME=最期の砂時計
VITE_APP_VERSION=1.0.0
```

### 4. デプロイ

「Deploy」をクリックしてデプロイ開始

デプロイURL例：
```
https://saigo-no-sunadokei.vercel.app
```

## フロントエンドのデプロイ（Netlify）

### 1. Netlifyサイトの作成

1. [Netlify](https://netlify.com) にログイン
2. 「Add new site」→「Import an existing project」
3. リポジトリを接続

### 2. ビルド設定

- **Base directory**: `frontend`
- **Build command**: `npm run build`
- **Publish directory**: `frontend/dist`

### 3. 環境変数の設定

Site settings > Environment variables で設定：

```env
VITE_API_BASE_URL=https://your-backend.railway.app/api
VITE_APP_NAME=最期の砂時計
```

### 4. デプロイ

「Deploy site」をクリック

## 環境変数の設定

### バックエンド（Railway/Render）

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `ENVIRONMENT` | 環境 | `production` |
| `CORS_ORIGINS` | 許可するオリジン（カンマ区切り） | `https://app.vercel.app,https://app.netlify.app` |
| `PORT` | ポート番号 | `8000` |
| `HOST` | ホスト | `0.0.0.0` |

### フロントエンド（Vercel/Netlify）

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `VITE_API_BASE_URL` | バックエンドAPIのURL | `https://backend.railway.app/api` |
| `VITE_APP_NAME` | アプリ名 | `最期の砂時計` |
| `VITE_APP_VERSION` | バージョン | `1.0.0` |

## デプロイ後の確認

### 1. バックエンドの動作確認

ブラウザで以下にアクセス：

```
https://your-backend.railway.app/docs
```

Swagger UIが表示されればOK

### 2. フロントエンドの動作確認

ブラウザで以下にアクセス：

```
https://your-app.vercel.app
```

アプリが正常に表示されればOK

### 3. API接続の確認

1. フロントエンドでキャラクター一覧ページを開く
2. データが正常に表示されることを確認
3. 検索・フィルター機能が動作することを確認
4. 統計ページでグラフが表示されることを確認

### 4. ログの確認

**Railway**:
- Dashboard > Deployments > Logs

**Render**:
- Dashboard > Service > Logs

**Vercel**:
- Dashboard > Deployments > Function Logs

**Netlify**:
- Dashboard > Deploys > Deploy log

## トラブルシューティング

### CORSエラーが発生する

**症状**: `Access to fetch has been blocked by CORS policy`

**解決策**:
1. バックエンドの`CORS_ORIGINS`環境変数にフロントエンドのURLを追加
2. バックエンドを再デプロイ

### APIに接続できない

**症状**: `Network Error` または `Failed to fetch`

**解決策**:
1. フロントエンドの`VITE_API_BASE_URL`が正しいか確認
2. バックエンドが正常に起動しているか確認
3. バックエンドのログを確認

### ビルドが失敗する

**症状**: デプロイ時にビルドエラー

**解決策**:
1. ローカルで`npm run build`が成功するか確認
2. Node.jsバージョンが一致しているか確認（package.json の engines）
3. 依存関係が正しくインストールされているか確認

### データベースが初期化されない

**症状**: キャラクターデータが表示されない

**解決策**:
1. CSVファイルが正しくデプロイされているか確認
2. バックエンドの起動ログを確認
3. 手動でデータベース初期化が必要な場合あり

## 継続的デプロイ（CD）

### GitHub Actions設定（オプション）

`.github/workflows/deploy.yml` を作成：

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        run: |
          # Railway CLI を使用したデプロイ
          npm install -g @railway/cli
          railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        run: |
          npm install -g vercel
          cd frontend
          vercel --prod
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
```

## セキュリティ推奨事項

1. **HTTPS必須**: すべての本番環境でHTTPSを使用
2. **環境変数の保護**: APIキーやシークレットは環境変数で管理
3. **CORS設定**: 必要最小限のオリジンのみ許可
4. **レート制限**: 本番環境ではレート制限を実装推奨
5. **ログ監視**: エラーログを定期的に確認

## 費用について

### 無料プラン（推奨）

- **Railway**: $5クレジット/月（無料枠）
- **Render**: 無料プラン（スリープあり）
- **Vercel**: Hobbyプラン（無料）
- **Netlify**: Starterプラン（無料）

### 有料プラン（スケール時）

- **Railway**: 従量課金（$0.000463/GB-hour）
- **Render**: $7/月〜
- **Vercel**: $20/月〜
- **Netlify**: $19/月〜

## まとめ

本番デプロイの完全なフローチャート：

```
1. ローカルでテスト実行
   ↓
2. Gitにプッシュ
   ↓
3. バックエンドをRailway/Renderにデプロイ
   ↓
4. フロントエンドをVercel/Netlifyにデプロイ
   ↓
5. 環境変数を設定
   ↓
6. デプロイ完了確認
   ↓
7. 動作テスト
```

質問やトラブルがあれば、各サービスのドキュメントを参照してください：

- [Railway Docs](https://docs.railway.app/)
- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [Netlify Docs](https://docs.netlify.com/)
