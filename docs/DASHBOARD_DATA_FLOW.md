# ダッシュボード v10 データフロー図

## 概要

ダッシュボードには **2つのデータソース** があり、両方を同期させる必要がある。

---

## データフロー

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MASTER_EPISODES_CURRENT.csv                       │
│                    (preserved/data/)                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────┐                    ┌───────────────────────────┐
│ update_dashboard_ │                    │ ブラウザ直接CSVパース      │
│ v10.py            │                    │ (PapaParse)               │
│                   │                    │                           │
│ EMBEDDED_EPISODE_ │                    │ loadEpisodesFromCSV()     │
│ DATA を更新       │                    │ 行738-822                 │
└───────────────────┘                    └───────────────────────────┘
        │                                           │
        ▼                                           ▼
┌───────────────────┐                    ┌───────────────────────────┐
│ 埋め込みJSON      │                    │ CSVパースオブジェクト      │
│ (静的)            │                    │ (動的)                    │
│                   │                    │                           │
│ ※ブラウザが       │  ← 優先度 →      │ ※APIサーバー未稼働時に    │
│   キャッシュ      │                    │   こちらが使われる        │
└───────────────────┘                    └───────────────────────────┘
        │                                           │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ renderEpisode   │
                    │ Table()         │
                    │                 │
                    │ テンプレート    │
                    │ 行262-380       │
                    └─────────────────┘
```

---

## 重要: 3箇所の同期

新しいフィールドを追加する際は、**必ず以下の3箇所を同時に更新**:

| # | ファイル | 更新箇所 | 説明 |
|---|----------|----------|------|
| 1 | `scripts/update_dashboard_v10.py` | `load_csv_data()` 内の episode dict | 埋め込みJSONに含めるフィールド |
| 2 | `preserved/episode_database_dashboard_v10.html` | CSVパース return オブジェクト (行738-822) | CSVから読み込むフィールド |
| 3 | `preserved/episode_database_dashboard_v10.html` | renderEpisodeTable テンプレート | 表示用HTML |

---

## フィールド追加チェックリスト

新しいフィールドを追加する際は、以下をすべて確認:

### Step 1: データ追加
- [ ] CSVにフィールドが存在するか確認
- [ ] `update_dashboard_v10.py` の `load_csv_data()` にフィールド追加
- [ ] ダッシュボードのCSVパース部分にフィールド追加

### Step 2: 表示追加
- [ ] 翻訳が必要か確認（英語→日本語）
- [ ] 翻訳関数を追加（必要な場合）
- [ ] テンプレートに表示コード追加

### Step 3: ソート追加（必要な場合）
- [ ] `handleSort()` にソートロジック追加
- [ ] sortable-label を追加

### Step 4: 検証
- [ ] `python scripts/update_dashboard_v10.py` 実行
- [ ] ブラウザでハードリフレッシュ (Cmd+Shift+R)
- [ ] 埋め込みデータ/CSVパース両方で表示確認

---

## 翻訳が必要なフィールド一覧

| フィールド | 値の例 | 翻訳関数 |
|-----------|--------|----------|
| episode_type | TURNING_POINT, ACHIEVEMENT | getTypeLabel() |
| person_type | REAL, FICTIONAL | entityLabel変数 |
| category | ARTIST, ATHLETE | categoryValue変数 |

### getTypeLabel() マッピング
```javascript
{
    'TURNING_POINT': '転機',
    'ACHIEVEMENT': '達成',
    'CHALLENGE': '挑戦',
    'INNOVATION': '革新',
    'FOUNDING': '創業',
    'FAILURE': '失敗',
    'COMEBACK': '復帰',
    'FAMILY': '家族',
    'CAREER': 'キャリア',
    'LEGACY': 'レガシー'
}
```

---

## 過去のインシデント

### 2026-01-06: generation_timestamp 表示不具合
- **現象**: 作成日が全て「記録無し」
- **原因**: CSVパース部分に `generation_timestamp` が含まれていなかった
- **修正**: 行821に `generation_timestamp: r['generation_timestamp'] || ''` 追加

### 2026-01-06: episode_type 翻訳不具合
- **現象**: タイプが英語のまま表示
- **原因**: `getTypeLabel()` 関数がなく、直接表示していた
- **修正**: `getTypeLabel()` 関数追加、テンプレート修正

---

## 検証コマンド

```bash
# フィールドが両方のソースに存在するか確認
python scripts/validation/verify_dashboard_fields.py

# ダッシュボード更新
python scripts/update_dashboard_v10.py
```
