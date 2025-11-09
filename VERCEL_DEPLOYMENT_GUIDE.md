# Vercel デプロイ手順書 - 最期の砂時計

## 📋 目次

1. [前提条件](#前提条件)
2. [Vercelアカウント作成](#vercelアカウント作成)
3. [フロントエンドのデプロイ](#フロントエンドのデプロイ)
4. [環境変数の設定](#環境変数の設定)
5. [デプロイ確認](#デプロイ確認)
6. [トラブルシューティング](#トラブルシューティング)

## 前提条件

### 必要なもの

- Gitリポジトリ（GitHub、GitLab、Bitbucket）
- Vercelアカウント（無料プランで開始可能）
- バックエンドがデプロイ済み（Railway推奨）
- バックエンドのURL取得済み

### 確認事項

```bash
# プロジェクトルートで以下を確認
ls frontend/
# src/, package.json, vite.config.ts, .env.example が存在すること

# ビルドが成功することを確認
cd frontend
npm run build
# dist/ ディレクトリが作成されること

# バックエンドURLの確認
echo $BACKEND_URL
# https://your-backend.railway.app のような形式
```

## Vercelアカウント作成

### 1. サインアップ

1. [Vercel](https://vercel.com) にアクセス
2. 「Sign Up」をクリック
3. GitHubアカウントで認証
   - または、GitLab / Bitbucket で認証
   - または、メールアドレスでサインアップ

### 2. 無料プラン（Hobby）

- **無料プラン特典**:
  - 100GB 帯域幅/月
  - 無制限のデプロイ
  - 自動HTTPS
  - プレビューデプロイ（Pull Request毎）
- クレジットカード登録不要
- 個人プロジェクトに最適

## フロントエンドのデプロイ

### ステップ1: 新規プロジェクト作成

1. Vercelダッシュボードで「New Project」をクリック
2. 「Import Git Repository」を選択
3. リポジトリを選択
   - **リポジトリ名**: `001-final-hourglass`
   - **ブランチ**: `main` （またはデプロイ対象ブランチ）

### ステップ2: ビルド設定

Vercelは自動的に設定を検出しますが、以下を確認・設定してください：

**Framework Preset**:
- Vite を選択（自動検出される場合が多い）

**Root Directory**:
```
frontend
```

**Build Command**:
```bash
npm run build
```

**Output Directory**:
```
dist
```

**Install Command**:
```bash
npm install
```

**Node.js Version**:
```
18.x
```

### ステップ3: 環境変数の設定（ビルド前）

「Environment Variables」セクションで設定：

| 変数名 | 値 | 環境 |
|--------|-----|------|
| `VITE_API_BASE_URL` | `https://your-backend.railway.app/api` | Production, Preview, Development |
| `VITE_APP_NAME` | `最期の砂時計` | All |
| `VITE_APP_VERSION` | `1.0.0` | All |

**重要**: `VITE_API_BASE_URL` は必ず Railway の URL に置き換えてください

### ステップ4: デプロイ実行

1. 「Deploy」ボタンをクリック
2. ビルドログを確認
   ```
   ✓ Building...
   ✓ Installing dependencies (npm install)
   ✓ Running build command (npm run build)
   ✓ Collecting build output
   ✓ Deployment successful
   ```

3. デプロイURLを取得
   ```
   https://your-app.vercel.app
   ```

### デプロイ完了後の自動処理

Vercelは以下を自動的に実行します：

- **HTTPS証明書の発行**（Let's Encrypt）
- **CDN配信**（世界中のエッジロケーション）
- **ビルドキャッシュ**（次回以降のデプロイを高速化）

## 環境変数の設定

### 必須の環境変数

Vercelダッシュボード → Settings → Environment Variables で設定：

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `VITE_API_BASE_URL` | `https://your-backend.railway.app/api` | バックエンドAPIのベースURL |
| `VITE_APP_NAME` | `最期の砂時計` | アプリケーション名 |
| `VITE_APP_VERSION` | `1.0.0` | バージョン番号 |

### オプションの環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `VITE_ENABLE_ANALYTICS` | `false` | アナリティクス有効化（将来の機能拡張用） |
| `VITE_SENTRY_DSN` | `https://...` | エラートラッキング（Sentry使用時） |
| `VITE_API_TIMEOUT` | `30000` | APIタイムアウト（ミリ秒） |

### 環境別の設定

Vercelでは以下の環境を個別に設定可能：

- **Production**: 本番環境（mainブランチ）
- **Preview**: プレビュー環境（Pull Request毎）
- **Development**: 開発環境（ローカル実行時）

**設定例**:
```
環境: Production
変数名: VITE_API_BASE_URL
値: https://your-backend.railway.app/api

環境: Preview
変数名: VITE_API_BASE_URL
値: https://your-backend-staging.railway.app/api
```

### 環境変数更新後の再デプロイ

1. 環境変数を追加・変更
2. 「Redeploy」ボタンをクリック（自動的に再デプロイされる場合もあり）
3. または、新しいコミットをプッシュして再デプロイ

## デプロイ確認

### 1. デプロイステータス確認

Vercelダッシュボードで以下を確認：

- **Status**: Ready（緑色のチェックマーク）
- **Build Time**: 通常30秒〜2分程度
- **Domains**: `your-app.vercel.app` が表示される

### 2. アプリケーション動作確認

デプロイURLにアクセス：

```bash
# ブラウザで開く
https://your-app.vercel.app

# または curlで確認
curl -I https://your-app.vercel.app
```

**期待される表示**:
- トップページ（キャラクター一覧）
- ナビゲーションバー
- データが正しく表示される

### 3. 各ページの動作確認

ブラウザで以下のページを確認：

**トップページ（/）**
- キャラクター一覧が表示される
- ページネーションが機能する
- 各キャラクターカードが正しくレンダリングされる

**統計ページ（/statistics）**
- 総キャラクター数が表示される
- ジャンル分布グラフが表示される
- 性別分布円グラフが表示される

**キャラクター詳細ページ（/characters/:id）**
- 詳細情報が表示される
- エピソードが表示される
- 画像が正しく表示される

**検索・フィルター機能**
- 名前検索が機能する
- ジャンルフィルターが機能する
- 性別フィルターが機能する

### 4. API接続確認

ブラウザの開発者ツールを開いて確認：

```javascript
// コンソールで実行
fetch('https://your-backend.railway.app/api/statistics/summary')
  .then(res => res.json())
  .then(data => console.log(data))
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

### 5. パフォーマンス確認

Vercelダッシュボード → Analytics で確認：

- **Page Load Time**: 通常1秒以内
- **Time to First Byte (TTFB)**: 通常200ms以内
- **Largest Contentful Paint (LCP)**: 通常2.5秒以内

## トラブルシューティング

### ビルドエラー: 依存関係のインストール失敗

**症状**:
```
Error: Cannot find module 'xxx'
```

**解決策**:

1. **package.json の確認**
   ```bash
   # ローカルで確認
   cd frontend
   npm install
   npm run build
   ```

2. **package-lock.json のコミット**
   ```bash
   git add frontend/package-lock.json
   git commit -m "Add package-lock.json"
   git push
   ```

3. **Node.jsバージョンの確認**
   - Vercel Settings → General → Node.js Version
   - 18.x を選択

### ビルドエラー: TypeScript型エラー

**症状**:
```
TS2322: Type 'xxx' is not assignable to type 'yyy'
```

**解決策**:

1. **ローカルでビルドを確認**
   ```bash
   cd frontend
   npm run build
   ```

2. **型定義の修正**
   - 必要に応じて型アサーションを追加
   - または `tsconfig.json` の設定を調整

3. **ビルドコマンドの変更**
   - Vercel Settings → Build & Development Settings
   - Build Command: `npm run build --no-type-check` （型チェックをスキップ）

### ビルドエラー: Vite設定エラー

**症状**:
```
Error: Failed to load config from /vercel/.../vite.config.ts
```

**解決策**:

1. **vite.config.ts の確認**
   ```typescript
   import { defineConfig } from 'vite'
   import react from '@vitejs/plugin-react'

   export default defineConfig({
     plugins: [react()],
     // ... その他の設定
   })
   ```

2. **依存関係の確認**
   ```bash
   npm install vite @vitejs/plugin-react --save-dev
   ```

### 起動エラー: ページが表示されない（404エラー）

**症状**:
- トップページは表示されるが、`/statistics` などが404エラー

**解決策**:

**vercel.json を作成**:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

これにより、すべてのルートが `index.html` にリダイレクトされ、React Routerが正しく機能します。

### API接続エラー: CORSエラー

**症状**:
```
Access to fetch at 'https://backend.railway.app/api/...' from origin 'https://your-app.vercel.app' has been blocked by CORS policy
```

**解決策**:

1. **バックエンドのCORS設定を確認**
   - Railway → Variables
   - `CORS_ORIGINS` に Vercel の URL を追加
   ```
   CORS_ORIGINS=https://your-app.vercel.app,https://your-app-*.vercel.app
   ```

2. **バックエンドを再デプロイ**
   - CORS設定変更後は必ず再デプロイ

### API接続エラー: Network Error

**症状**:
```
Network Error
Failed to fetch
```

**解決策**:

1. **環境変数の確認**
   - Vercel → Settings → Environment Variables
   - `VITE_API_BASE_URL` が正しいURLか確認

2. **バックエンドの稼働確認**
   ```bash
   curl https://your-backend.railway.app/docs
   ```

3. **HTTPS を確認**
   - `http://` ではなく `https://` を使用

### プレビューデプロイが失敗する

**症状**:
- Pull Request のプレビューデプロイが失敗

**解決策**:

1. **環境変数の設定**
   - Preview 環境にも環境変数を設定
   - または Production 環境の変数を Preview にもコピー

2. **ブランチ設定の確認**
   - Vercel Settings → Git
   - Production Branch を確認

### カスタムドメイン設定

**独自ドメインを使いたい場合**:

1. Vercel → Settings → Domains
2. 「Add Domain」をクリック
3. ドメイン名を入力（例: `saigo-no-sunadokei.com`）
4. DNSレコードを設定
   - Aレコード: `76.76.21.21`
   - または CNAMEレコード: `cname.vercel-dns.com`
5. DNS伝播を待つ（最大48時間）

## まとめ

### デプロイ完了チェックリスト

- [ ] Vercelプロジェクト作成完了
- [ ] フロントエンドのデプロイ成功
- [ ] 環境変数の設定完了（特に `VITE_API_BASE_URL`）
- [ ] トップページにアクセス可能
- [ ] 統計ページのグラフが正しく表示
- [ ] APIからデータが正しく取得できる
- [ ] 検索・フィルター機能が動作
- [ ] React Routerのルーティングが正しく機能

### 次のステップ

1. **パフォーマンス最適化**
   - Vercel Analytics で読み込み速度を確認
   - 画像の最適化（WebP形式、遅延読み込み）
   - コード分割の改善

2. **監視とエラートラッキング**
   - Sentry などのエラートラッキングツールを導入
   - Vercel Analytics でユーザー行動を分析

3. **継続的デプロイ**
   - Git プッシュで自動デプロイ
   - プレビューデプロイで Pull Request をレビュー

## リソース

- [Vercel Documentation](https://vercel.com/docs)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [React Router with Vercel](https://vercel.com/guides/deploying-react-with-vercel)

---

**注意**: Vercel の無料プラン（Hobby）は個人プロジェクト用です。商用利用の場合は Pro プラン（$20/月）へのアップグレードを検討してください。
