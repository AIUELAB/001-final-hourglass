# データ・ダッシュボード運用ルール

## 📊 CSVファイル規約

- **UTF-8 BOM必須**: `encoding='utf-8-sig'`
- Excel対応必須

---

## 📁 マスターCSV運用ルール（単一マスター原則）

### 正規マスター（唯一の実ファイル）

```
preserved/data/MASTER_EPISODES_CURRENT.csv  ← 正規マスター（実ファイル）
```

### シンボリックリンク構造

```
data/MASTER_EPISODES_CURRENT.csv
    ↓ シンボリックリンク
preserved/data/MASTER_EPISODES_CURRENT.csv
```

### 運用ルール

| 操作 | 使用パス |
|------|----------|
| **編集（Claude/スクリプト）** | `preserved/data/MASTER_EPISODES_CURRENT.csv` |
| **読み込み（ダッシュボード）** | `data/MASTER_EPISODES_CURRENT.csv`（リンク経由） |
| **整合性チェック** | `python scripts/check_single_master.py` |

### 絶対禁止

- ❌ `data/MASTER_EPISODES_CURRENT.csv` に実ファイルを作成
- ❌ シンボリックリンクを削除して実ファイルに置換
- ❌ `preserved/data/` 以外の場所にマスターCSVを複製

### 整合性チェック（定期実行推奨）

```bash
python scripts/check_single_master.py
```

チェック項目:
1. 正規マスターの存在確認
2. シンボリックリンクの正常性
3. 二重マスター（実ファイル重複）の検出

---

## 📊 ダッシュボード運用ルール（単一正規版原則）

### 正規ダッシュボード（唯一の最新版）

```
preserved/episode_database_dashboard_v7.html  ← 正規版
```

### 運用ルール

| 操作 | 使用パス |
|------|----------|
| **編集・閲覧** | `preserved/episode_database_dashboard_v*.html` |
| **バージョンアップ** | preserved/ に新バージョンを作成 |
| **旧バージョン** | `archive/dashboards/` に保存 |

### 絶対禁止

- ❌ ルート直下にダッシュボードHTMLを作成
- ❌ preserved/ 以外の場所でダッシュボードを編集
- ❌ 同一バージョンの複数コピーを保持

### バージョンアップ手順

**🔴 重要：バージョンアップはユーザーからの明示的な指示があった時のみ実行**

1. **ユーザーからの明示的な指示を待つ**
2. preserved/ に新バージョンを作成（例: v8.html）
3. 旧バージョンを archive/dashboards/ に移動
4. ファイル名・title・h1のバージョン番号を同期

### ダッシュボードアクセス方法

**✅ 正しい方法（HTTPサーバー経由）：**

```bash
# プロジェクトルートで実行
# プロジェクト定義のポート範囲: 8000-8082
python -m http.server 8082  # ダッシュボード用推奨ポート

# 起動メッセージで実際のポート番号を確認
# 例: Serving HTTP on 0.0.0.0 port 8082 (http://0.0.0.0:8082/) ...

# ブラウザでアクセス
http://localhost:8082/preserved/episode_database_dashboard_v8.html
```

**プロジェクト定義のポート範囲：**

| ポート | 用途 | 優先度 |
|--------|------|--------|
| **8082** | HTTPサーバー（ダッシュボード配信） | ✅ 推奨 |
| **8081** | HTTPサーバー代替 | ⭕ 推奨 |
| **8080** | HTTPサーバー代替 | ⭕ 推奨 |
| **8000** | FastAPI バックエンド | ⚠️ API用に予約 |

**注意：** 8000番はFastAPI用に予約されているため避ける。ダッシュボードは8082番を使用。

**詳細参照：** `docs/EPISODE_DB_STARTUP_GUIDE.md` - ポート番号の詳細仕様

**❌ 禁止方法（file://プロトコル）：**

```text
file:///Users/.../episode_database_dashboard_v8.html
→ CORS制限によりCSVファイル読み込み不可
```

### 整合性チェック（定期実行推奨）

```bash
python scripts/check_single_dashboard.py
```

チェック項目:
1. preserved/ に正規ダッシュボードが1つのみ存在
2. ルート直下にダッシュボードなし
3. archive/dashboards/ の存在確認

---

## 🔢 バージョン同期ルール（EPUP）

**ファイル名のバージョンとUI表示は必ず同期させる**

| 変更対象 | 同時更新必須 |
|----------|-------------|
| ファイル名 `*_v6.html` | `<title>`, `<h1>` のバージョン表記 |
| ダッシュボード新規作成 | ファイル名・title・h1すべて同一バージョン |

```html
<!-- ファイル: episode_database_dashboard_v6.html -->
<title>エピソードメインデータベース v6</title>
<h1>📊 エピソードメインデータベース v6</h1>
```

**チェックリスト（バージョンアップ時）:**
- [ ] ファイル名のバージョン番号
- [ ] `<title>`タグのバージョン番号
- [ ] `<h1>`タグのバージョン番号
- [ ] 関連ドキュメントの参照更新

---

## 🔄 セッション復元

Cursor再起動後: `前回のセッションを復元してください`

記録ファイル: `.session/current_session.json`, `.session/STATUS.md`
