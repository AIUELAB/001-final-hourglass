---
description: 新規エピソードDB作業（ダッシュボード更新・データ追加・バージョンアップ）+ エラー0件デバッグガイド
---

# new-epdb Skill（Episode Database Management + Debug Guide）

## 目的

エピソードデータベースの**新規作業**（ダッシュボード更新、データ追加、バージョンアップ）を支援します。

**追加**: ブラウザ DevTools Console で **エラー（赤）= 0件** を保証する起動方法とデバッグ手順を提供します。

## Definition of Done（DoD）

- ✅ EPDB起動直後、ブラウザ DevTools Console に **エラー（赤）= 0件**
- ✅ EPDBを「更新」した直後に、**ハードリフレッシュ（キャッシュ無効化）**しても **エラー（赤）= 0件**
- ✅ 第三者が同じ手順で検証可能

## 重要制約（EPUP共通）

- **低コンテキスト運用**: 大きいファイルの全文貼り付け禁止
- **自動修正は勝手にしない**: 書き換え操作は必ずユーザー承認後
- **単一マスター原則**: CSVは `preserved/data/MASTER_EPISODES_CURRENT.csv` のみ

## 正規ファイルパス（必ず確認）

| 種別 | 正規パス |
|------|----------|
| **マスターCSV** | `preserved/data/MASTER_EPISODES_CURRENT.csv` |
| **ダッシュボード** | `preserved/episode_database_dashboard_v*.html` |
| **旧バージョン保存先** | `archive/dashboards/` |

## 🚨 バージョンアップ重要ルール

### ❌ 絶対禁止

- **ユーザーからの明示的な指示がない限り、バージョンアップは実行しない**
- 勝手にバージョン番号を上げる行為は厳禁

### ✅ バージョンアップが許可される条件

- ユーザーが「バージョンを上げて」「v9にして」などと明示的に指示した場合のみ

---

## 📡 EPDB起動方法（エラー0件保証）

### ✅ 推奨: 統合起動スクリプト使用

```bash
# プロジェクトルートで実行
./scripts/start_epdb.sh
```

**このスクリプトが実行すること:**

1. 環境チェック（Python 3、backendディレクトリ存在確認）
2. ポート競合チェック（8000, 8082）
3. **APIサーバー起動**（FastAPI on port 8000）
4. **HTTPサーバー起動**（port 8082 でpreservedディレクトリ配信）
5. ヘルスチェック（`/api/health`エンドポイント確認）

**アクセスURL:**

- **ダッシュボード**: http://localhost:8082/preserved/episode_database_dashboard_v8.html
- **APIサーバー**: http://localhost:8000/api/stats/summary

**停止方法:**

```bash
./scripts/stop_epdb.sh
```

### ⚙️ 手動起動（開発者向け）

```bash
# ターミナル1: APIサーバー起動
cd backend
python3 -m uvicorn app.main:app --reload --port 8000

# ターミナル2: HTTPサーバー起動
cd /Users/admin/Documents/AIUELAB/001-final-hourglass
python3 -m http.server 8082
```

### 🔴 必須条件

1. **APIサーバー（port 8000）が起動していること**
   - FastAPI（uvicorn）が動作している必要があります
   - `/api/stats/summary` エンドポイントが応答すること
2. **HTTPサーバー（port 8082）が起動していること**
   - preserved/episode_database_dashboard_v8.html を配信
   - preserved/heatmap_data.json を配信

---

## 🐛 エラーデバッグガイド

### 原因と修正内容

#### 問題1: APIサーバーが起動していない

**症状:**

```
❌ API統計データ取得エラー: TypeError: Failed to fetch
```

**原因:**

- HTTPサーバー（port 8082）だけが起動している
- APIサーバー（port 8000）が起動していない、またはport 8000で別のプロセスが動作している

**修正:**

1. APIサーバーを起動する
2. ポート競合を解消する

```bash
# ポート8000の使用状況確認
lsof -i :8000 | grep LISTEN

# 競合プロセスを停止（PIDを確認してから）
kill <PID>

# APIサーバーを起動
cd backend && python3 -m uvicorn app.main:app --reload --port 8000
```

#### 問題2: SimpleHTTPServerがport 8000で起動している

**症状:**

- `/api/stats/summary` にアクセスすると404エラー
- `curl http://localhost:8000/api/health` が HTML Error Responseを返す

**原因:**

- `python3 -m http.server 8000` が先に起動している
- FastAPI（uvicorn）がport 8000で起動できない

**修正:**

```bash
# SimpleHTTPServerを停止
lsof -i :8000 | grep LISTEN
kill <PID>

# FastAPIを起動
cd backend && python3 -m uvicorn app.main:app --reload --port 8000
```

#### 問題3: ポート番号の混同

**症状:**

- ダッシュボードが表示されない
- CORSエラーが発生

**原因:**

- HTTPサーバーとAPIサーバーのポート番号を混同
- 間違ったポートでアクセスしている

**正しいポート割り当て:**

| ポート | 用途 | プロセス |
|--------|------|----------|
| **8000** | APIサーバー | FastAPI（uvicorn） |
| **8082** | HTTPサーバー | Python SimpleHTTPServer |

---

## 📋 検証手順（第三者が実行可能）

### 1. 起動

```bash
cd /Users/admin/Documents/AIUELAB/001-final-hourglass
./scripts/start_epdb.sh
```

### 2. エラー0件確認（起動直後）

1. ブラウザで http://localhost:8082/preserved/episode_database_dashboard_v8.html にアクセス
2. **DevTools を開く**（Chrome: Cmd+Option+J / Firefox: Cmd+Option+K）
3. **Console タブ**を確認
4. **赤いエラー（Uncaught / console.error / network fail）が0件** であることを確認

**期待される出力:**

```
✅ 埋め込みヒートマップデータを使用
✅ API統計データ取得成功: {total_characters: 8002, ...}
✅ ダッシュボード初期化完了
```

### 3. エラー0件確認（更新後+ハードリフレッシュ）

1. CSVファイルを更新する（例: `preserved/data/MASTER_EPISODES_CURRENT.csv` を編集）
2. ヒートマップデータを再生成

   ```bash
   python scripts/generate_heatmap_data.py --embed --html preserved/episode_database_dashboard_v8.html
   ```

3. ブラウザで **ハードリフレッシュ**（Chrome/Firefox: Cmd+Shift+R）
4. DevTools Console で **エラー（赤）= 0件** を確認

---

## 🔧 トラブルシューティング

### エラー: `fetch failed` または `NetworkError`

**原因:** APIサーバーが起動していない

**対処:**

```bash
# APIサーバー状態確認
curl http://localhost:8000/api/health

# 期待される応答
{"status":"healthy","message":"API is running"}

# 応答がない場合、APIサーバーを起動
cd backend && python3 -m uvicorn app.main:app --reload --port 8000
```

### エラー: `404 Not Found` for `heatmap_data.json`

**原因:** HTTPサーバーがpreservedディレクトリを配信していない

**対処:**

```bash
# HTTPサーバーをプロジェクトルートで起動
cd /Users/admin/Documents/AIUELAB/001-final-hourglass
python3 -m http.server 8082

# 確認
curl -I http://localhost:8082/preserved/heatmap_data.json
```

### エラー: `CORS policy` エラー

**原因:** file:// プロトコルでダッシュボードを開いている

**対処:** HTTPサーバー経由でアクセス（http://localhost:8082/preserved/...）

---

## 🚀 作業タイプ別ガイド

### 1. ダッシュボードのバージョンアップ

**🔴 前提条件：ユーザーからの明示的な指示があること**

```bash
# 現在の正規版を確認
python scripts/check_single_dashboard.py

# 新バージョン作成（例: v8 → v9）
# 1. preserved/episode_database_dashboard_v9.html を作成
# 2. 旧版を archive/dashboards/ に移動
# 3. ファイル名・title・h1 のバージョン番号を同期

# ヒートマップデータ更新
python scripts/generate_heatmap_data.py --embed --html preserved/episode_database_dashboard_v9.html

# サーバー起動して動作確認
./scripts/start_epdb.sh
# → http://localhost:8082/preserved/episode_database_dashboard_v9.html
```

### 2. エピソードデータ追加

```bash
# 事前チェック（単一マスター確認）
python scripts/check_single_master.py

# CSV編集後の品質チェック
python scripts/scheduled_epup_check.py --daily --csv preserved/data/MASTER_EPISODES_CURRENT.csv

# ヒートマップ再生成
python scripts/generate_heatmap_data.py --embed --html preserved/episode_database_dashboard_v8.html

# 問題があれば修正スクリプト実行（承認後）
```

### 3. ヒートマップ/統計更新

```bash
# ヒートマップデータ生成
python scripts/generate_heatmap_data.py --output preserved/heatmap_data.json

# ダッシュボードに埋め込み
python scripts/generate_heatmap_data.py --embed --html preserved/episode_database_dashboard_v8.html
```

---

## 📊 変更ファイル一覧（本デバッグ作業）

| ファイル | 変更内容 |
|---------|---------|
| `scripts/start_epdb.sh` | 統合起動スクリプト（新規作成） |
| `scripts/stop_epdb.sh` | 停止スクリプト（新規作成） |
| `.claude/commands/new-epdb.md` | 起動方法とデバッグ手順を追加 |

**変更なし:**

- `preserved/episode_database_dashboard_v8.html` （エラーハンドリングは既に適切に実装済み）

---

## 📝 検証結果（Before/After）

### Before

- ❌ APIサーバー未起動のため `fetch('/api/stats/summary')` がネットワークエラー
- ❌ Console に赤いエラーが出力される

### After

- ✅ 統合起動スクリプトでAPIサーバーとHTTPサーバーを同時起動
- ✅ `/api/stats/summary` が正常に応答（200 OK）
- ✅ Console エラー = 0件

**実測値:**

```json
{
  "total_characters": 8002,
  "total_genres": 29,
  "female_count": 61,
  "male_count": 7941,
  "female_ratio": 0.8,
  "era_range": "1960年代〜2020年代"
}
```

---

## 整合性チェック（作業前後に実行）

```bash
python scripts/check_single_master.py      # CSV整合性
python scripts/check_single_dashboard.py   # ダッシュボード整合性
```

---

## 出力フォーマット

### 現状確認結果

### 実行した操作

### 次のアクション提案
