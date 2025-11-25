# エピソードメインデータベース v3 起動ガイド

**最終更新**: 2025-11-22

このガイドでは、Cursor再起動後もエピソードメインデータベースv3を確実に起動する方法を説明します。

---

## 📋 目次

1. [クイックスタート（最速起動方法）](#クイックスタート)
2. [初回セットアップ](#初回セットアップ)
3. [日常的な起動手順](#日常的な起動手順)
4. [アクセス方法](#アクセス方法)
5. [トラブルシューティング](#トラブルシューティング)
6. [よくある質問](#よくある質問)
7. [詳細情報](#詳細情報)

---

## クイックスタート

### 最速起動方法（1コマンド）

```bash
./start-episode-db.sh
```

ブラウザで **http://localhost:8000/** にアクセス → 完了！

### 環境チェック（オプション）

```bash
./check-environment.sh
```

問題がある場合、このスクリプトが原因を特定します。

---

## 初回セットアップ

初めてエピソードメインデータベースv3を起動する場合の手順です。

### 1. 前提条件の確認

#### 必須

- **Python 3.8以上**
  ```bash
  python3 --version  # Python 3.8+ 必要
  ```

- **pip**（Pythonパッケージマネージャー）
  ```bash
  pip3 --version
  ```

#### オプション（React開発時のみ）

- **Node.js 18以上**
- **npm**

### 2. 依存関係のインストール

#### バックエンド（必須）

```bash
cd backend
pip install -r requirements.txt
```

**主な依存パッケージ**:
- FastAPI（Webフレームワーク）
- Uvicorn（HTTPサーバー）
- Pydantic（データバリデーション）
- python-dotenv（環境変数管理）

#### フロントエンド（React開発時のみ）

```bash
cd frontend
npm install
```

**注意**: HTMLダッシュボードv3を使用する場合、Node.jsは**不要**です。

### 3. データファイルの確認

以下のファイルがプロジェクトルートに存在することを確認：

```bash
ls -l MASTER_EPISODES_CURRENT.csv
```

**ファイルサイズ**: 約1.9MB（2,613件のエピソード）

### 4. 起動スクリプトの準備

```bash
# 実行権限の付与（初回のみ）
chmod +x start-episode-db.sh
chmod +x check-environment.sh
```

### 5. 初回起動

```bash
./start-episode-db.sh
```

---

## 日常的な起動手順

Cursor再起動後、毎回この手順で起動します。

### 方法1: 起動スクリプト使用（推奨）

```bash
./start-episode-db.sh
```

**メリット**:
- ポート競合を自動チェック
- ヘルスチェックで起動確認
- ブラウザ自動起動（macOS）
- エラー時の詳細ログ表示

### 方法2: 手動起動

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000
```

**メリット**:
- シンプル
- ログがターミナルに直接表示

**デメリット**:
- ポート競合チェックなし
- ターミナルを占有

### 方法3: バックグラウンド起動

```bash
cd backend
nohup python3 -m uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
```

**メリット**:
- ターミナルが解放される
- ログファイルに記録

**デメリット**:
- プロセス管理が必要

---

## アクセス方法

### ダッシュボード v3（推奨）

- **URL**: http://localhost:8000/
- **説明**: 最新のダッシュボード、すべての機能が利用可能
- **技術**: HTML + JavaScript（スタンドアローン）

### ダッシュボード v2

- **URL**: http://localhost:8000/v2
- **説明**: 旧バージョン、後方互換性のため維持

### API仕様書（開発者向け）

- **URL**: http://localhost:8000/docs
- **説明**: Swagger UI（対話的API仕様書）

### データバージョン確認

- **URL**: http://localhost:8000/api/data/version
- **説明**: CSV最終更新時刻を確認

### React開発サーバー（開発時のみ）

- **URL**: http://localhost:5175/
- **起動**: `cd frontend && npm run dev`
- **説明**: ホットリロード付き開発環境

---

## トラブルシューティング

### 問題1: ポート8000が既に使用中

#### 症状

```
Address already in use: port 8000
```

#### 解決方法

**方法A: 既存プロセスを確認**

```bash
lsof -i :8000
```

**方法B: プロセスを停止**

```bash
# PIDを確認
lsof -i :8000 | grep LISTEN

# プロセスを停止
kill <PID>
```

**方法C: 別ポートで起動**

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8001
```

アクセス: http://localhost:8001/

### 問題2: Python依存関係エラー

#### 症状

```
ModuleNotFoundError: No module named 'fastapi'
```

#### 解決方法

```bash
cd backend
pip install -r requirements.txt
```

**個別インストール**:
```bash
pip install fastapi uvicorn[standard]
```

### 問題3: CSVファイルが見つからない

#### 症状

```
⚠️  CSV未検出: MASTER_EPISODES_CURRENT.csv
```

#### 解決方法

CSVファイルの場所を確認：

```bash
find /Users/admin/Documents/AIUELAB/001-final-hourglass -name "MASTER_EPISODES_CURRENT.csv"
```

プロジェクトルートに配置：

```bash
ls -l /Users/admin/Documents/AIUELAB/001-final-hourglass/MASTER_EPISODES_CURRENT.csv
```

### 問題4: データベースが古い

#### 症状

新しいCSVデータが反映されない

#### 解決方法

**方法A: APIエンドポイント経由**

```bash
curl -X POST http://localhost:8000/api/data/refresh
```

**方法B: データベース削除**

```bash
cd backend
rm characters.db
# サーバー再起動で自動再構築
```

### 問題5: ブラウザで表示されない

#### チェックリスト

- [ ] サーバーが起動している
  ```bash
  curl http://localhost:8000/api/health
  ```

- [ ] ポート8000でリッスンしている
  ```bash
  lsof -i :8000
  ```

- [ ] ブラウザのキャッシュをクリア
  - macOS: `Cmd + Shift + R`（スーパーリロード）

- [ ] ログを確認
  ```bash
  tail -f backend.log
  ```

### 問題6: 起動が遅い

#### 原因

- 大量のデータインポート
- ポート競合チェック
- ヘルスチェック待機

#### 解決方法

`--reload`オプションを外して本番モードで起動：

```bash
cd backend
python3 -m uvicorn app.main:app --port 8000
```

---

## よくある質問

### Q1: Cursor再起動するたびに起動が必要？

**A**: はい。バックグラウンドプロセスとして起動しているため、Cursor終了時に停止します。

**解決策**: システム起動時の自動起動設定（launchd）を使用することで、常時稼働させることも可能です（高度な設定）。

### Q2: フロントエンド（React）の起動は必要？

**A**: **不要**です。HTMLダッシュボードv3はバックエンド経由で提供されるため、Reactの起動は不要です。

Reactは**開発時のみ**必要です：
```bash
cd frontend && npm run dev
```

### Q3: どのブラウザで動作しますか？

**A**: 以下のモダンブラウザで動作確認済みです：

- Google Chrome 90+
- Safari 14+
- Firefox 88+
- Microsoft Edge 90+

### Q4: データの自動更新は？

**A**: 30秒ごとにデータベース更新をチェックし、自動的に最新データを表示します（ダッシュボードv3のみ）。

手動更新も可能：
```bash
curl -X POST http://localhost:8000/api/data/refresh
```

### Q5: ログファイルはどこ？

**A**: プロジェクトルートの `backend.log` に記録されます。

リアルタイム表示：
```bash
tail -f backend.log
```

### Q6: 複数の環境で同時に起動できる？

**A**: 可能ですが、ポート番号を変更する必要があります。

```bash
# 環境1: ポート8000
python3 -m uvicorn app.main:app --port 8000

# 環境2: ポート8001
python3 -m uvicorn app.main:app --port 8001
```

---

## 詳細情報

### プロジェクト構成

```
/Users/admin/Documents/AIUELAB/001-final-hourglass/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPIアプリケーション
│   │   ├── database.py          # SQLiteデータベースロジック
│   │   ├── models.py            # Pydanticモデル定義
│   │   └── utils/
│   │       └── csv_loader.py    # CSVインポート機能
│   ├── characters.db            # SQLiteデータベース（自動生成）
│   └── requirements.txt         # Python依存関係
│
├── frontend/                    # React開発環境（オプション）
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
│
├── preserved/
│   ├── episode_database_dashboard_v2.html
│   └── episode_database_dashboard_v3.html  # デフォルトダッシュボード
│
├── MASTER_EPISODES_CURRENT.csv  # マスターデータ（2,613件）
├── start-episode-db.sh          # 起動スクリプト
└── check-environment.sh         # 環境チェックスクリプト
```

### 技術スタック

| コンポーネント | 技術 | バージョン |
|---------------|------|-----------|
| バックエンド | FastAPI | 0.121.0+ |
| HTTPサーバー | Uvicorn | latest |
| データベース | SQLite3 | 3.x |
| フロントエンド（開発） | React | 19.1.1 |
| ビルドツール（開発） | Vite | 7.1.7 |
| ダッシュボード | HTML/JS | - |

### 環境変数

バックエンドは `.env` ファイルを読み込みますが、**必須の環境変数はありません**。
すべてデフォルト値で動作します。

**オプション設定**:

```env
# CORS設定（複数起源を許可）
CORS_ORIGINS=http://localhost:5173,http://localhost:5175
```

### ポート番号

| ポート | 用途 | 必須 |
|--------|------|------|
| 8000 | FastAPI バックエンド | ✅ |
| 5173 | Vite デフォルトポート | ❌ |
| 5175 | Vite 代替ポート | ❌ |

### データフロー

```
MASTER_EPISODES_CURRENT.csv
    ↓ (起動時 or /api/data/refresh)
backend/characters.db (SQLite)
    ↓ (FastAPI REST API)
ダッシュボード v3 (HTML/JS)
    ↓ (30秒ごと自動更新チェック)
最新データ表示
```

### API エンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|---------|------|
| `/` | GET | ダッシュボード v3 |
| `/v2` | GET | ダッシュボード v2 |
| `/v3` | GET | ダッシュボード v3（明示的） |
| `/api/health` | GET | ヘルスチェック |
| `/api/data/version` | GET | CSVバージョン情報 |
| `/api/data/refresh` | POST | 強制データ再読み込み |
| `/api/characters` | GET | キャラクター一覧 |
| `/api/characters/{id}` | GET | 特定キャラクター |
| `/api/stats/summary` | GET | 統計サマリー |
| `/docs` | GET | Swagger UI |

### 開発者向け情報

#### ログレベル

```bash
# 詳細ログ
uvicorn app.main:app --log-level debug

# 標準ログ（デフォルト）
uvicorn app.main:app --log-level info
```

#### ホットリロード

```bash
# 有効（開発推奨）
uvicorn app.main:app --reload

# 無効（本番推奨）
uvicorn app.main:app
```

#### 外部アクセス許可

```bash
# ローカルのみ（デフォルト）
uvicorn app.main:app --host 127.0.0.1

# すべてのネットワークインターフェイス
uvicorn app.main:app --host 0.0.0.0
```

---

## サポート

### 関連ドキュメント

- [プロジェクトREADME](../README.md)
- [トラブルシューティング](./TROUBLESHOOTING.md)
- [Phase 6 データ分析レポート](./PHASE6_DATA_ANALYSIS_REPORT.md)
- [データ拡充ロードマップ](./DATA_EXPANSION_ROADMAP.md)

### 問題報告

問題が解決しない場合:

1. `./check-environment.sh` で環境確認
2. `backend.log` でログ確認
3. GitHubでIssue作成

---

**最終更新**: 2025-11-22
**バージョン**: v3.0
**著者**: Claude Code（開発環境セットアップ担当）
