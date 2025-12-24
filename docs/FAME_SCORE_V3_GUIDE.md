# Fame Score v3 運用ガイド

## 概要

Fame Score v3は多言語Wikipedia PVとWikidataを活用した有名人度スコアリングシステムです。

### スコア計算式

| シグナル | 重み（Phase 1） | 重み（Phase 2） | 説明 |
|----------|-----------------|-----------------|------|
| 多言語Wikipedia PV | 50% | 40% | 10言語（ja,en,zh,ko,es,fr,de,ru,pt,it）の合計PV |
| Wikidata言語版数 | 30% | 25% | 何言語のWikipediaに記事があるか |
| Wikidata被リンク数 | 20% | 15% | 他のWikidata項目からの参照数 |
| Google検索ヒット数 | - | 20% | Google検索結果の概算件数 |

---

## Phase 1: 基本シグナル（無料）

### 初回実行

```bash
# ドライラン（変更なし、効果確認のみ）
python scripts/update_fame_scores_v3.py --dry-run

# 本番実行（全人物を処理）
python scripts/update_fame_scores_v3.py --execute
```

### 処理時間の目安

- 約7,000人物 → 約3-4時間（API制限による）
- キャッシュ済みデータは即時反映

---

## Phase 2: Google検索追加（有料オプション）

### APIキー設定

```bash
# Google Custom Search API
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_CSE_ID="your_cse_id"

# または Bing Search API（代替）
export BING_API_KEY="your_api_key"
```

### コスト試算

| API | 無料枠 | 超過料金 | 月間試算（3日更新） |
|-----|--------|----------|---------------------|
| Google Custom Search | 100クエリ/日 | $5/1000クエリ | 約$360/月 |
| Bing Search | 1000クエリ/月 | $7/1000クエリ | 約$50/月 |

### 使用方法

APIキーを設定すると自動的にPhase 2の重み配分が適用されます。

---

## Phase 3: 自動更新パイプライン

### スケジューラー管理

```bash
# 3日毎の自動更新を開始
./scripts/manage_fame_scheduler.sh start

# 自動更新を停止
./scripts/manage_fame_scheduler.sh stop

# 状態確認
./scripts/manage_fame_scheduler.sh status

# 今すぐ差分更新を実行
./scripts/manage_fame_scheduler.sh run-now

# ドライラン（更新対象の確認のみ）
./scripts/manage_fame_scheduler.sh dry-run
```

### 差分更新の対象

1. **新規人物**: 前回処理以降に追加されたperson_id
2. **期限切れ**: キャッシュのupdated_atが30日以上前

### ログファイル

```
src/reports/logs/
├── fame_update_stdout.log    # 標準出力
├── fame_update_stderr.log    # エラー出力
└── fame_update_YYYYMMDD_HHMMSS.log  # 実行ログ
```

---

## キャッシュデータベース

```
data/cache/fame_score.db
```

### スキーマ

| カラム | 型 | 説明 |
|--------|-----|------|
| person_id | TEXT | 人物ID（主キー） |
| person_name | TEXT | 人物名 |
| wikidata_id | TEXT | Wikidata ID |
| multi_lang_pv | INTEGER | 多言語PV合計 |
| sitelinks | INTEGER | 言語版数 |
| inlinks | INTEGER | 被リンク数 |
| pv_by_lang | TEXT | 言語別PV（JSON） |
| fame_score_v3 | REAL | スコア |
| fame_rank_v3 | INTEGER | 順位 |
| updated_at | TEXT | 更新日時 |

### キャッシュ確認

```bash
sqlite3 data/cache/fame_score.db "SELECT COUNT(*) FROM fame_cache WHERE multi_lang_pv IS NOT NULL"
```

---

## トラブルシューティング

### API制限エラー

```
[WARNING] Google API rate limit exceeded
```

→ REQUEST_INTERVAL を増やす（デフォルト: 1秒）

### Wikidata取得エラー

```
[WARNING] データ取得エラー: 人物名 - timeout
```

→ タイムアウト値を増やすか、後で再実行

### キャッシュの強制更新

```bash
python scripts/update_fame_scores_incremental.py --force-all
```

---

## ファイル構成

```
scripts/
├── update_fame_scores_v3.py           # Phase 1: 初回全更新
├── update_fame_scores_incremental.py  # Phase 3: 差分更新
├── manage_fame_scheduler.sh           # スケジューラー管理
└── fame_score_v3/
    ├── __init__.py
    ├── scorer.py           # スコア計算
    ├── wikidata.py         # Wikidata API
    ├── wikipedia_pv.py     # Wikipedia PV API
    └── google_search.py    # Phase 2: Google検索
```
