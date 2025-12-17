# Stage 1: collect-sources - 情報源収集パイプライン

## 概要

エピソード収集パイプラインの第1ステージ。人物リストから関連情報源を収集し、`episode_sources.csv`に出力します。

## 機能

### 実装済み機能（MVP）

1. **手動CSV入力**
   - 人物名、ソースURL、テキストを手動で入力
   - センシティブフィルター適用
   - 冪等性保証（source_id MD5ハッシュ）

2. **重複チェック**
   - 既存ソースとの重複を検出
   - source_id（MD5ハッシュ）ベースで判定

3. **バリデーション**
   - URL形式検証
   - 必須フィールドチェック
   - person_type検証（REAL/FICTIONAL）
   - 文字数制限（著作権遵守：250文字）

4. **エラーハンドリング**
   - graceful degradation（ライブラリ未インストール時も動作）
   - 詳細ログ出力
   - スキップしたソースをCSV記録

### 今後実装予定（Phase 2）

1. **API統合**
   - Wikidata API（qwikidata）
   - Wikipedia API（wikipedia-api）
   - リトライ・レート制限対応（tenacity）

2. **検索クエリ生成**
   - API無し環境用フォールバック
   - 手動検索用クエリ一覧CSV出力

## データモデル

### EpisodeSource

情報源を表現するデータクラス。

| カラム名 | 型 | 必須 | 説明 |
|---------|---|-----|------|
| source_id | str | ✅ | ソースID（MD5ハッシュ、自動生成） |
| person_name | str | ✅ | 人物名 |
| person_id | str | ✅ | 人物ID（既存 or 新規） |
| person_type | str | ✅ | 人物タイプ（REAL/FICTIONAL） |
| source_url | str | ✅ | 情報源URL |
| source_type | str | ✅ | ソースタイプ（wikidata/wikipedia/manual） |
| raw_text | str | ✅ | 抽出テキスト（250文字以内） |
| context | str | - | 文脈情報 |
| evidence_quality | str | ✅ | 根拠品質（A/B/C） |
| verification_status | str | ✅ | 検証ステータス（verified/unverified/rejected） |
| collected_at | datetime | ✅ | 収集日時 |
| verified_at | datetime | - | 検証日時 |

### 根拠品質定義

| 品質 | 定義 | 例 |
|-----|------|---|
| **A** | 一次情報 | 公式サイト、学術論文、自伝、インタビュー記録 |
| **B** | 二次情報2件以上で裏付けあり | Wikipedia + 新聞記事2件 |
| **C** | 未検証 | 単一ソース、出典不明 |

## 使用方法

### 基本コマンド

```bash
# ドライラン（デフォルト、ファイル書き込みなし）
python scripts/pipeline_collect_sources.py \
    --input config/person_sources/sample_manual_sources.csv \
    --output generated/episode_sources.csv \
    --mode manual

# 本番実行（ファイル書き込み）
python scripts/pipeline_collect_sources.py \
    --input config/person_sources/sample_manual_sources.csv \
    --output generated/episode_sources.csv \
    --mode manual \
    --execute
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--input` | 入力CSVパス | 必須 |
| `--output` | 出力CSVパス | generated/episode_sources.csv |
| `--mode` | 収集モード（manual/api/hybrid） | manual |
| `--sources` | 使用するAPIソース（カンマ区切り） | - |
| `--dry-run` | ドライラン（ファイル書き込みなし） | True |
| `--execute` | 実際に実行 | False |
| `--check-duplicates` | 重複チェック対象CSV | - |
| `--generate-queries` | 検索クエリ一覧を生成 | False |
| `--verbose` | 詳細ログ出力 | False |

### 入力CSVフォーマット

#### 手動CSV（--mode manual）

```csv
person_name,person_id,person_type,source_url,raw_text,context,category,description,evidence_quality
イチロー,P001,REAL,https://ja.wikipedia.org/wiki/イチロー,2004年シーズン262安打記録,年齢31歳時の業績,スポーツ,元プロ野球選手,B
```

必須カラム:
- person_name
- source_url
- raw_text

推奨カラム:
- person_id（新規の場合は空でOK）
- person_type（デフォルト: REAL）
- evidence_quality（デフォルト: C）

#### API用CSV（--mode api）※Phase 2実装予定

```csv
person_name,birth_year,person_type
イチロー,1973,REAL
山中伸弥,1962,REAL
```

## 出力ファイル

### episode_sources.csv

収集した情報源。

```csv
source_id,person_name,person_id,person_type,source_url,source_type,raw_text,context,evidence_quality,verification_status,collected_at,verified_at
SRC-a3f5b9c2d4e6f8a0,イチロー,P001,REAL,https://ja.wikipedia.org/wiki/イチロー,manual,2004年シーズン262安打記録,年齢31歳時の業績,B,unverified,2025-12-17T14:00:00,
```

### skipped_sources.csv

スキップしたソース（センシティブ、エラー等）。

```csv
person_name,source_url,skip_reason
テスト太郎,https://example.com,sensitive_category: 犯罪者
```

### search_queries.csv（--generate-queries指定時）

手動検索用クエリ一覧。

```csv
person_name,search_query
イチロー,"イチロー" 逸話 エピソード
イチロー,"イチロー" 自伝 回想
```

## 冪等性保証

### source_id生成

```python
import hashlib

def generate_source_id(person_name: str, source_url: str) -> str:
    composite_key = f"{person_name}||{source_url}"
    hash_digest = hashlib.md5(composite_key.encode('utf-8')).hexdigest()
    return f"SRC-{hash_digest[:16]}"
```

同一の人物名+URLの組み合わせは同じsource_idを生成するため、重複インポートを防止できます。

### 重複チェック

```bash
python scripts/pipeline_collect_sources.py \
    --input new_sources.csv \
    --output generated/episode_sources.csv \
    --mode manual \
    --check-duplicates generated/episode_sources.csv \
    --execute
```

既存の`episode_sources.csv`と照合し、重複するsource_idをスキップします。

## センシティブフィルター

`src/sensitive_filter.py`を使用して、以下をフィルタリング:

- **自動ブロック**: 犯罪者、テロリスト、暴力団等
- **レビュー必要**: 政治家、宗教家、実業家
- **許可リスト**: ネルソン・マンデラ、マハトマ・ガンジー等

詳細: `config/sensitive_keywords.yaml`

## エラーハンドリング

### Graceful Degradation

ライブラリが未インストールの場合も動作:

```
WARNING: tenacity not installed. Retry functionality disabled.
WARNING: qwikidata not installed. Wikidata API disabled.
WARNING: wikipedia-api not installed. Wikipedia API disabled.
```

### リトライ（Phase 2実装予定）

tenacityライブラリを使用:

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_from_wikipedia(person_name: str):
    ...
```

API Rate Limit時に指数バックオフでリトライ。

## ログ出力

### 通常ログ

```
2025-12-17 14:00:00 [INFO] Collecting sources from CSV: config/person_sources/sample_manual_sources.csv
2025-12-17 14:00:01 [INFO] Collected 3 sources from CSV, skipped 0
2025-12-17 14:00:01 [INFO] Statistics:
2025-12-17 14:00:01 [INFO]   Collected: 3
2025-12-17 14:00:01 [INFO]   Skipped: 0
```

### 詳細ログ（--verbose）

```
2025-12-17 14:00:00 [DEBUG] Processing row 0: イチロー
2025-12-17 14:00:00 [DEBUG] source_id: SRC-a3f5b9c2d4e6f8a0
2025-12-17 14:00:00 [DEBUG] Sensitive check: False
```

## 統計情報

実行後に表示される統計:

```
============================================================
Statistics:
  Collected: 3
  Skipped: 0
============================================================
```

## トラブルシューティング

### 問題: ライブラリが未インストール

**症状**:
```
WARNING: tenacity not installed. Retry functionality disabled.
```

**対処**:
```bash
pip install tenacity qwikidata wikipedia-api
```

### 問題: 重複source_id

**症状**:
```
DEBUG: Duplicate source_id: SRC-a3f5b9c2d4e6f8a0
```

**対処**:
同一の人物名+URLが既に登録されています。`--check-duplicates`を使用して自動スキップ。

### 問題: URL形式エラー

**症状**:
```
ERROR: Invalid URL format: example.com
```

**対処**:
URLは`https://`または`http://`で始まる必要があります。

## テスト

### サンプルCSV

`config/person_sources/sample_manual_sources.csv`が提供されています:

```csv
person_name,person_id,person_type,source_url,raw_text,context,category,description,evidence_quality
イチロー,P001,REAL,https://ja.wikipedia.org/wiki/イチロー,2004年シーズン262安打記録,年齢31歳時の業績,スポーツ,元プロ野球選手,B
山中伸弥,P002,REAL,https://ja.wikipedia.org/wiki/山中伸弥,2012年にiPS細胞の研究でノーベル賞受賞,年齢50歳時の業績,科学・技術,医学者,A
ドラえもん,P003,FICTIONAL,https://ja.wikipedia.org/wiki/ドラえもん,未来から来た22世紀のネコ型ロボット,キャラクター設定,架空キャラクター,藤子作品,C
```

### 実行例

```bash
# 1. ドライラン
python scripts/pipeline_collect_sources.py \
    --input config/person_sources/sample_manual_sources.csv \
    --output generated/episode_sources_test.csv \
    --mode manual \
    --verbose

# 2. 本番実行
python scripts/pipeline_collect_sources.py \
    --input config/person_sources/sample_manual_sources.csv \
    --output generated/episode_sources_test.csv \
    --mode manual \
    --execute

# 3. 結果確認
head -5 generated/episode_sources_test.csv
```

## 次のステップ

Stage 2に進む: `scripts/pipeline_verify_sources.py`

1. 根拠品質判定（A/B/C）
2. センシティブ除外
3. 重複除外
4. PersonNameValidator適用

詳細: `docs/EPISODE_COLLECTION_PIPELINE.md`

## 関連ファイル

- スクリプト: `scripts/pipeline_collect_sources.py`
- モデル: `src/models/episode_source.py`
- フィルター: `src/sensitive_filter.py`
- 設定: `config/sensitive_keywords.yaml`
- サンプル: `config/person_sources/sample_manual_sources.csv`

## ライセンス・著作権

著作権遵守のため、以下を実施:

- raw_textは250文字以内に制限
- キーフレーズのみ抽出
- 長文引用は禁止

## 更新履歴

- 2025-12-17: MVP実装完了（手動CSV、センシティブフィルター、冪等性保証）
- Phase 2予定: API統合、検索クエリ生成、リトライ機構
