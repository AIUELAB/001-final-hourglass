# Pipeline Stage 2: verify-sources - 実装ドキュメント

## 概要

`scripts/pipeline_verify_sources.py` は、エピソード収集パイプラインのStage 2として、
情報源の品質検証と振り分けを行います。

## 機能

### 1. 根拠品質判定（A/B/C）

| 品質 | 定義 | 判定基準 |
|-----|------|---------|
| **A** | 一次情報 | ・公式ドメイン（.go.jp, .ac.jp, .edu等）<br>・学術論文（doi.org, scholar.google等）<br>・キーワード（自伝、公式インタビュー等） |
| **B** | 二次情報2+ | ・Wikipedia + 参照文献あり |
| **C** | 未検証 | ・単一ソース、出典不明 |

### 2. 重複除外

- **source_id**: `MD5(person_name + source_url)` で生成
- 既存 `verified_sources.csv` との照合により重複を検出
- 重複の場合は `rejected_sources.csv` に振り分け

### 3. センシティブ除外

#### ブラックリスト照合

- `config/blacklist_names.json` に基づく
- 名前の完全一致とパターンマッチ（正規表現）

#### センシティブフィルタ統合

- `src/sensitive_filter.py` を使用
- `config/sensitive_keywords.yaml` の設定に基づく
- センシティブカテゴリ・キーワード検出

### 4. 品質ゲート

検証済み（verified）として扱われる条件：

1. 重複なし
2. ブラックリストに該当しない
3. センシティブでない
4. **evidence_quality が 'A' または 'B'**

上記条件を満たさない場合は `rejected_sources.csv` に振り分け。

## 使用方法

### 基本コマンド

```bash
# ドライラン（デフォルト）
python scripts/pipeline_verify_sources.py \
    --input generated/episode_sources.csv \
    --output-verified generated/verified_sources.csv \
    --output-rejected generated/rejected_sources.csv \
    --dry-run

# 本番実行
python scripts/pipeline_verify_sources.py \
    --input generated/episode_sources.csv \
    --output-verified generated/verified_sources.csv \
    --output-rejected generated/rejected_sources.csv \
    --execute
```

### コマンドライン引数

| 引数 | デフォルト | 説明 |
|-----|----------|------|
| `--input` | `generated/episode_sources.csv` | 入力CSV（情報源リスト） |
| `--output-verified` | `generated/verified_sources.csv` | 検証済みCSV（A/B品質） |
| `--output-rejected` | `generated/rejected_sources.csv` | 却下CSV（C品質・センシティブ等） |
| `--dry-run` | True | ドライラン（変更なし） |
| `--execute` | False | 本番実行（ファイル書き込み） |

## 入力CSVフォーマット

### episode_sources.csv

| カラム名 | 型 | 必須 | 説明 |
|---------|---|-----|------|
| source_id | str | - | ソースID（空の場合は自動生成） |
| person_name | str | ✅ | 人物名 |
| person_id | str | ✅ | 人物ID |
| person_type | str | ✅ | 人物タイプ（REAL/FICTIONAL） |
| source_url | str | ✅ | 情報源URL |
| source_type | str | ✅ | ソースタイプ（wikidata/wikipedia/manual） |
| raw_text | str | ✅ | 抽出テキスト |
| context | str | - | 文脈情報 |
| category | str | - | カテゴリ |
| description | str | - | 人物説明 |

## 出力CSVフォーマット

### verified_sources.csv（検証済み）

入力CSVの全カラム + 以下：

| カラム名 | 型 | 説明 |
|---------|---|------|
| source_id | str | ソースID（MD5ハッシュ） |
| evidence_quality | str | 根拠品質（'A' or 'B'） |
| verification_status | str | 検証ステータス（'verified'） |
| verified_at | datetime | 検証日時 |

### rejected_sources.csv（却下）

入力CSVの全カラム + 以下：

| カラム名 | 型 | 説明 |
|---------|---|------|
| source_id | str | ソースID（MD5ハッシュ） |
| evidence_quality | str | 根拠品質（'A', 'B', 'C'） |
| verification_status | str | 検証ステータス（'rejected'） |
| verified_at | datetime | 検証日時 |
| rejection_reason | str | 却下理由 |

### 却下理由（rejection_reason）

| 理由 | 説明 |
|-----|------|
| `duplicate_source_id` | 既存ソースとの重複 |
| `blacklist_match: {name}` | ブラックリスト名前の完全一致 |
| `blacklist_pattern: {pattern}` | ブラックリストパターンマッチ |
| `sensitive_category: {category}` | センシティブカテゴリ該当 |
| `sensitive_keyword: {keyword}` | センシティブキーワード検出 |
| `quality_C_unverified` | C品質（未検証ソース） |

## 統計レポート

### reports/source_verification_YYYYMMDD_HHMMSS.json

```json
{
  "timestamp": "2025-12-17T21:46:51.303770",
  "input_file": "/path/to/episode_sources.csv",
  "output_verified": "/path/to/verified_sources.csv",
  "output_rejected": "/path/to/rejected_sources.csv",
  "statistics": {
    "total_sources": 7,
    "duplicates": 0,
    "blacklisted": 2,
    "sensitive": 0,
    "quality_A": 3,
    "quality_B": 1,
    "quality_C": 3,
    "verified": 4,
    "rejected": 3
  }
}
```

## 品質判定ロジック詳細

### A品質（一次情報）

#### ドメインパターン

```python
A_QUALITY_DOMAINS = [
    r'\.go\.jp$',          # 政府公式
    r'\.ac\.jp$',          # 学術機関
    r'\.edu$',             # 教育機関
    r'ndl\.go\.jp',        # 国会図書館
    r'\.gov$',             # 政府系
    r'doi\.org',           # 学術論文DOI
    r'researchgate\.net',  # 研究者プラットフォーム
    r'scholar\.google',    # Google Scholar
]
```

#### キーワードパターン

```python
A_QUALITY_KEYWORDS = [
    '自伝',
    '回想録',
    '公式インタビュー',
    '公式伝記',
    '学術論文',
    '研究論文',
    '博士論文',
    '公式講演',
    '公式サイト',
]
```

### B品質（二次情報2+）

- **Wikipedia + 参照文献あり**
  - URL に `wikipedia.org` を含む
  - raw_text に「出典」または「参照」を含む

### C品質（未検証）

- A/B品質に該当しない全てのソース

## 冪等性保証

### source_id生成アルゴリズム

```python
def generate_source_id(person_name: str, source_url: str) -> str:
    """
    ソースIDをMD5ハッシュで生成

    Args:
        person_name: 人物名
        source_url: ソースURL

    Returns:
        source_id (例: SRC-a3f5b9c2d4e6f8a0)
    """
    composite_key = f"{person_name}||{source_url}"
    hash_digest = hashlib.md5(composite_key.encode('utf-8')).hexdigest()
    return f"SRC-{hash_digest[:16]}"
```

### 重複検出

- 既存 `verified_sources.csv` を読み込み
- 生成した source_id が既存リストに存在するかチェック
- 重複の場合は `rejected_sources.csv` に振り分け（`rejection_reason: duplicate_source_id`）

## エラーハンドリング

### 必須カラムチェック

```python
required_cols = ['person_name', 'source_url', 'raw_text', 'person_type', 'source_type']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")
```

### ファイル存在チェック

- 入力ファイル（episode_sources.csv）が存在しない場合はエラー終了
- 既存verified_sources.csvが存在しない場合は警告ログのみ（初回実行時）

### エンコーディング

- 全CSVファイルは `utf-8-sig` で読み書き（BOM付きUTF-8）
- Excel対応を保証

## 統合コンポーネント

### 1. SensitiveFilter

**ファイル**: `src/sensitive_filter.py`

**設定ファイル**: `config/sensitive_keywords.yaml`

**役割**:
- センシティブカテゴリ検出
- センシティブキーワード検出
- レビュー必要カテゴリ検出
- 許可リスト判定

**使用方法**:
```python
from src.sensitive_filter import SensitiveFilter
from src.source_adapters.base import PersonCandidate

filter = SensitiveFilter()
candidate = PersonCandidate(person_name="テスト太郎", category="犯罪者")
is_sensitive, reason = filter.is_sensitive(candidate)
```

### 2. Blacklist

**ファイル**: `config/blacklist_names.json`

**フォーマット**:
```json
{
  "blacklist": [
    {
      "name": "大リーグ養成ギプス",
      "reason": "ドラえもんの秘密道具",
      "detected_date": "2025-12-15",
      "episode_id": "EP-000003828"
    }
  ],
  "patterns": [
    "テスト.*",
    "架空.*",
    "ダミー.*"
  ]
}
```

**役割**:
- 道具名・アイテム名の誤登録防止
- テストデータの除外
- 架空キャラクターの不適切な登録防止

## テスト方法

### 1. ドライラン（変更なし）

```bash
python scripts/pipeline_verify_sources.py --dry-run
```

- ファイル書き込みなし
- 統計情報のみ出力
- デフォルトモード

### 2. 本番実行

```bash
python scripts/pipeline_verify_sources.py --execute
```

- verified_sources.csv 書き込み
- rejected_sources.csv 書き込み
- 統計レポート（JSON）書き込み

### 3. テストデータ

**サンプル**: `generated/episode_sources.csv`

```csv
source_id,person_name,person_id,person_type,source_url,source_type,raw_text,context,evidence_quality,verification_status,collected_at,verified_at,category,description
,イチロー,P001,REAL,https://ja.wikipedia.org/wiki/イチロー,wikipedia,2004年シーズン262安打記録を達成。出典: メジャーリーグ公式記録,年齢31歳時の業績,,,2025-12-17T10:00:00,,スポーツ,プロ野球選手
,山中伸弥,P002,REAL,https://www.kyoto-u.ac.jp/ja/research/yamanka,wikidata,iPS細胞を世界で初めて作製。,年齢40歳時の業績,,,2025-12-17T10:05:00,,科学・技術,京都大学教授
,羽生結弦,P006,REAL,https://ndl.go.jp/athletes/hanyu,wikidata,2014年ソチ冬季五輪金メダル。,年齢23歳時の業績,,,2025-12-17T10:25:00,,スポーツ,フィギュアスケート選手
```

### 4. 期待される出力

| 人物名 | 品質 | 振り分け | 理由 |
|-------|-----|---------|------|
| イチロー | B | verified | Wikipedia + 参照文献 |
| 山中伸弥 | A | verified | 学術ドメイン (.ac.jp) |
| 羽生結弦 | A | verified | 国会図書館 (ndl.go.jp) |
| テスト太郎 | C | rejected | ブラックリストパターン（テスト.*） |
| 大リーグ養成ギプス | C | rejected | ブラックリスト名前一致 |

## トラブルシューティング

### Q1. A/B品質が検出されない

**原因**: URL判定パターンまたはキーワードが不足

**対処**:
1. `A_QUALITY_DOMAINS` にドメインパターンを追加
2. `A_QUALITY_KEYWORDS` にキーワードを追加

### Q2. 重複検出が動作しない

**原因**: source_idが正しく生成されていない

**対処**:
1. `generate_source_id()` 関数の動作確認
2. `person_name` と `source_url` の値を確認

### Q3. センシティブ検出が動作しない

**原因**: `config/sensitive_keywords.yaml` が読み込めない

**対処**:
1. ファイル存在確認: `config/sensitive_keywords.yaml`
2. YAML形式の検証
3. `SensitiveFilter` 初期化ログを確認

### Q4. ブラックリスト検出が動作しない

**原因**: `config/blacklist_names.json` が読み込めない

**対処**:
1. ファイル存在確認: `config/blacklist_names.json`
2. JSON形式の検証
3. ブラックリスト読み込みログを確認

## 次のステップ

### Stage 3: curate-episodes（エピソード生成）

**入力**: `generated/verified_sources.csv`

**処理**:
- LLM経由で「あなたと同じ〜」形式に変換
- EPUP品質ルール適用
- PersonNameValidator適用

**出力**: `generated/curated_episodes.csv`

詳細は `docs/EPISODE_COLLECTION_PIPELINE.md` の Stage 3 を参照。

## 参考資料

- 設計書: `docs/EPISODE_COLLECTION_PIPELINE.md`
- SensitiveFilter: `src/sensitive_filter.py`
- Blacklist: `config/blacklist_names.json`
- センシティブキーワード: `config/sensitive_keywords.yaml`
- PersonCandidate: `src/source_adapters/base.py`

---

**作成日**: 2025-12-17
**バージョン**: 1.0
**ステータス**: 実装完了・動作確認済み
