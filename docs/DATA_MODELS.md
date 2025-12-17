# エピソード収集パイプライン - データモデル仕様書

## 概要

このドキュメントは、エピソード収集パイプラインで使用する3つの主要データモデルの仕様を定義します。

- **EpisodeSource**: 情報源管理（episode_sources.csv）
- **VerifiedSource**: 検証済み情報源（verified_sources.csv）
- **CuratedEpisode**: 生成済みエピソード（curated_episodes.csv）

## データモデル階層

```
EpisodeSource（基底クラス）
    ↓ 継承
VerifiedSource（検証機能追加）
    ↓ 変換
CuratedEpisode（エピソード生成）
```

---

## EpisodeSource

### 概要

情報源を管理する基底データモデル。episode_sources.csvの行を表現します。

### フィールド

| フィールド名 | 型 | 必須 | デフォルト | 説明 |
|-------------|---|------|----------|------|
| `source_id` | str | - | 自動生成 | ソースID（MD5ハッシュ、SRC-{16桁}） |
| `person_name` | str | ✅ | - | 人物名 |
| `person_id` | str | ✅ | - | 人物ID（P{8桁英数}） |
| `person_type` | str | ✅ | - | 人物タイプ（REAL/FICTIONAL） |
| `source_url` | str | ✅ | - | 情報源URL |
| `source_type` | str | ✅ | - | ソースタイプ（wikidata/wikipedia/manual） |
| `raw_text` | str | ✅ | - | 抽出テキスト（250文字以内推奨） |
| `context` | str | - | None | 文脈情報 |
| `evidence_quality` | str | ✅ | "C" | 根拠品質（A/B/C） |
| `verification_status` | str | ✅ | "unverified" | 検証ステータス（verified/unverified/rejected） |
| `collected_at` | datetime | ✅ | 現在時刻 | 収集日時 |
| `verified_at` | datetime | - | None | 検証日時 |

### 主要メソッド

#### `generate_source_id(person_name: str, source_url: str) -> str`

ソースIDをMD5ハッシュで生成（冪等性保証）。

```python
source_id = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
# 結果: "SRC-a3f5b9c2d4e6f8a0"
```

#### `validate()`

データバリデーション実行。

チェック項目:
- 必須フィールド存在確認
- URL形式検証
- person_type値検証（REAL/FICTIONAL）
- evidence_quality値検証（A/B/C）
- verification_status値検証
- raw_text文字数制限（250文字以内推奨、著作権遵守）

#### `is_duplicate(source_id: str, csv_path: Path) -> bool`

既存ソースとの重複チェック。

```python
is_dup = EpisodeSource.is_duplicate("SRC-abc123", Path("episode_sources.csv"))
# 結果: True（重複） or False（新規）
```

#### `save_to_csv(sources: List[EpisodeSource], csv_path: Path, append: bool = False)`

CSV保存（UTF-8 BOM、Excel対応）。

```python
EpisodeSource.save_to_csv(sources, Path("episode_sources.csv"), append=True)
```

#### `load_from_csv(csv_path: Path) -> List[EpisodeSource]`

CSV読み込み。

```python
sources = EpisodeSource.load_from_csv(Path("episode_sources.csv"))
```

### 使用例

```python
from src.models.episode_source import EpisodeSource
from pathlib import Path

# 1. インスタンス生成
source = EpisodeSource(
    person_name="イチロー",
    person_id="P001ABC12",
    person_type="REAL",
    source_url="https://ja.wikipedia.org/wiki/イチロー",
    source_type="wikipedia",
    raw_text="2004年シーズン262安打記録",
    context="年齢31歳時の業績"
)

# 2. source_idは自動生成される
print(source.source_id)  # SRC-a3f5b9c2d4e6f8a0

# 3. CSV保存
sources = [source]
EpisodeSource.save_to_csv(sources, Path("generated/episode_sources.csv"))

# 4. CSV読み込み
loaded_sources = EpisodeSource.load_from_csv(Path("generated/episode_sources.csv"))

# 5. 重複チェック
is_duplicate = EpisodeSource.is_duplicate(
    source.source_id,
    Path("generated/episode_sources.csv")
)
```

---

## VerifiedSource

### 概要

検証済み情報源を管理するデータモデル。EpisodeSourceを継承し、検証機能とA/B/C品質判定ロジックを追加します。

### 追加フィールド

| フィールド名 | 型 | 必須 | デフォルト | 説明 |
|-------------|---|------|----------|------|
| `verifier_notes` | str | - | None | 検証者ノート |

（その他のフィールドはEpisodeSourceから継承）

### 品質判定基準

| 品質 | 定義 | ドメイン例 |
|-----|------|----------|
| **A** | 一次情報（公式サイト、学術論文、自伝等） | .go.jp, .ac.jp, .edu, ndl.go.jp |
| **B** | 二次情報2件以上で裏付けあり | wikipedia.org, britannica.com |
| **C** | 未検証（単一ソース、出典不明） | 上記以外 |

### 主要メソッド

#### `auto_judge_quality() -> str`

URL/source_typeから自動品質判定。

```python
source = VerifiedSource(
    person_name="テスト",
    person_id="P001ABC12",
    person_type="REAL",
    source_url="https://www.mext.go.jp/test",  # .go.jp
    source_type="manual",
    raw_text="テストテキスト"
)
# 自動判定: evidence_quality = "A"
```

#### `mark_verified(verifier_notes: Optional[str] = None)`

検証済みとしてマーク。

```python
source.mark_verified("品質A確認済み")
# verification_status = "verified"
# verified_at = 現在時刻
# verifier_notes = "品質A確認済み"
```

#### `mark_rejected(reason: str)`

却下としてマーク。

```python
source.mark_rejected("センシティブキーワード検出")
# verification_status = "rejected"
# verified_at = 現在時刻
# verifier_notes = "センシティブキーワード検出"
```

#### `filter_by_quality(sources: List[VerifiedSource], min_quality: str = "B") -> List[VerifiedSource]`

品質でフィルタリング。

```python
# B品質以上のみ抽出
filtered = VerifiedSource.filter_by_quality(sources, min_quality="B")
```

#### `filter_verified(sources: List[VerifiedSource]) -> List[VerifiedSource]`

検証済みソースのみ抽出。

```python
verified = VerifiedSource.filter_verified(sources)
```

### 使用例

```python
from src.models.verified_source import VerifiedSource
from pathlib import Path

# 1. インスタンス生成（自動品質判定）
source = VerifiedSource(
    person_name="イチロー",
    person_id="P001ABC12",
    person_type="REAL",
    source_url="https://ja.wikipedia.org/wiki/イチロー",  # B品質
    source_type="wikipedia",
    raw_text="2004年シーズン262安打記録"
)

print(source.evidence_quality)  # B（自動判定）

# 2. 検証マーク
source.mark_verified("Wikipedia記事確認済み")

# 3. CSV保存
sources = [source]
VerifiedSource.save_to_csv(sources, Path("generated/verified_sources.csv"))

# 4. 品質フィルタリング
all_sources = VerifiedSource.load_from_csv(Path("generated/verified_sources.csv"))
high_quality = VerifiedSource.filter_by_quality(all_sources, min_quality="B")

# 5. 検証済みフィルタリング
verified = VerifiedSource.filter_verified(all_sources)
```

---

## CuratedEpisode

### 概要

EPUP形式に変換された未マージエピソードを管理するデータモデル。MASTER_EPISODES_CURRENT.csvとの互換性を保証します。

### フィールド

| フィールド名 | 型 | 必須 | デフォルト | 説明 |
|-------------|---|------|----------|------|
| `episode_id` | str | - | "" | エピソードID（未採番は空、マージ時に正式採番） |
| `person_id` | str | ✅ | - | 人物ID（P{8桁英数}） |
| `person_name` | str | ✅ | - | 正規化済み人物名 |
| `age` | int | ✅ | - | 年齢（0-150） |
| `episode_text` | str | ✅ | - | エピソード本文（EPUP形式） |
| `source_id` | str | ✅ | - | 根拠ソースID（EpisodeSourceのsource_id） |
| `source_url` | str | ✅ | - | 根拠URL |
| `evidence_quality` | str | ✅ | - | 根拠品質（A/B/C） |
| `validation_status` | str | ✅ | "pending" | バリデーション結果（pending/passed/failed/review） |
| `validation_issues` | str | - | None | 検出された問題（JSON形式） |
| `generated_at` | datetime | ✅ | 現在時刻 | 生成日時 |
| `person_type` | str | ✅ | "REAL" | 人物タイプ（REAL/FICTIONAL） |
| `category` | str | - | None | カテゴリ |
| `episode_type` | str | - | None | エピソードタイプ |

### 主要メソッド

#### `validate()`

データバリデーション実行。

チェック項目:
- 必須フィールド存在確認
- age範囲検証（0-150）
- evidence_quality値検証（A/B/C）
- validation_status値検証
- person_type値検証（REAL/FICTIONAL）
- episode_text基本フォーマット検証（「あなたと同じ」形式）

#### `mark_passed()`

バリデーション合格としてマーク。

```python
episode.mark_passed()
# validation_status = "passed"
# validation_issues = None
```

#### `mark_failed(issues: str)`

バリデーション不合格としてマーク。

```python
episode.mark_failed('[{"type": "format_violation"}]')
# validation_status = "failed"
# validation_issues = '[...]'
```

#### `mark_review(reason: str)`

レビュー必要としてマーク。

```python
episode.mark_review("evidence_quality_C")
# validation_status = "review"
# validation_issues = "evidence_quality_C"
```

#### `to_master_format() -> dict`

MASTER_EPISODES_CURRENT.csv互換形式に変換。

```python
master_data = episode.to_master_format()
# マスターCSV互換の辞書（全フィールド含む）
```

#### `filter_by_status(episodes: List[CuratedEpisode], status: str) -> List[CuratedEpisode]`

バリデーションステータスでフィルタリング。

```python
passed = CuratedEpisode.filter_by_status(episodes, "passed")
```

#### `filter_by_quality(episodes: List[CuratedEpisode], min_quality: str = "B") -> List[CuratedEpisode]`

根拠品質でフィルタリング。

```python
high_quality = CuratedEpisode.filter_by_quality(episodes, min_quality="B")
```

### 使用例

```python
from src.models.curated_episode import CuratedEpisode
from pathlib import Path

# 1. インスタンス生成
episode = CuratedEpisode(
    person_id="P001ABC12",
    person_name="イチロー",
    age=31,
    episode_text="あなたと同じ31歳のとき、イチローは2004年シーズンに262安打を記録した。",
    source_id="SRC-abc123def456",
    source_url="https://ja.wikipedia.org/wiki/イチロー",
    evidence_quality="B",
    person_type="REAL",
    category="スポーツ",
    episode_type="転機"
)

# 2. バリデーション結果マーク
episode.mark_passed()

# 3. CSV保存
episodes = [episode]
CuratedEpisode.save_to_csv(episodes, Path("generated/curated_episodes.csv"))

# 4. マスター形式変換
master_data = episode.to_master_format()
print(master_data["source"])  # "COLLECTION_PIPELINE"
print(master_data["fact_check_result"])  # "確認済み"（B品質）

# 5. フィルタリング
all_episodes = CuratedEpisode.load_from_csv(Path("generated/curated_episodes.csv"))
passed = CuratedEpisode.filter_by_status(all_episodes, "passed")
high_quality = CuratedEpisode.filter_by_quality(all_episodes, min_quality="B")
```

---

## CSVスキーマ定義

JSONスキーマファイルは `config/schemas/` に配置されています。

### ファイル一覧

| ファイル名 | 説明 |
|----------|------|
| `episode_sources_schema.json` | episode_sources.csv のスキーマ |
| `verified_sources_schema.json` | verified_sources.csv のスキーマ |
| `curated_episodes_schema.json` | curated_episodes.csv のスキーマ |
| `review_queue_schema.json` | review_queue.csv のスキーマ |

### バリデーション例

```python
import json
import jsonschema
import pandas as pd

# スキーマ読み込み
with open("config/schemas/episode_sources_schema.json") as f:
    schema = json.load(f)

# CSV読み込み
df = pd.read_csv("generated/episode_sources.csv", encoding="utf-8-sig")

# 各行をバリデーション
for idx, row in df.iterrows():
    data = row.to_dict()
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print(f"Row {idx}: {e.message}")
```

---

## テスト実行

```bash
# 全テスト実行
pytest tests/models/ -v

# 特定モデルのテスト
pytest tests/models/test_episode_source.py -v
pytest tests/models/test_verified_source.py -v
pytest tests/models/test_curated_episode.py -v

# カバレッジ付き実行
pytest tests/models/ --cov=src.models --cov-report=html
```

---

## データフロー

```
【Stage 1: collect-sources】
    ↓
episode_sources.csv (EpisodeSource)
    ↓
【Stage 2: verify-sources】
    ↓
verified_sources.csv (VerifiedSource, A/B品質のみ)
    ↓
【Stage 3: curate-episodes】
    ↓
curated_episodes.csv (CuratedEpisode, EPUP形式)
    ↓
【Stage 4: validate-and-merge】
    ↓
MASTER_EPISODES_CURRENT.csv (マージ統合)
```

---

## 冪等性保証

### source_id生成

同一の `person_name` + `source_url` の組み合わせは、常に同じ `source_id` を生成します。

```python
# 何度実行しても同じIDを生成
source_id1 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
source_id2 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
assert source_id1 == source_id2  # True
```

### 重複除外

CSV保存時に `source_id` で重複除外を自動実行します。

```python
# append=True でも重複は除外される
EpisodeSource.save_to_csv(sources, Path("episode_sources.csv"), append=True)
```

---

## エラーハンドリング

### バリデーションエラー

```python
try:
    source = EpisodeSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="INVALID",  # 不正な値
        source_url="https://example.com",
        source_type="manual",
        raw_text="テストテキスト"
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

### CSV読み込みエラー

```python
sources = EpisodeSource.load_from_csv(Path("nonexistent.csv"))
# 結果: [] (空リスト、例外は発生しない)
```

### 行単位のエラー

CSV読み込み時に個別行のエラーは警告ログ出力後、スキップされます。

```python
# ログ出力例:
# ERROR: Failed to load row: Invalid person_type: INVALID
```

---

## 既存システムとの統合

### SensitiveFilter統合

```python
from src.sensitive_filter import SensitiveFilter
from src.models.episode_source import EpisodeSource

filter = SensitiveFilter()

# センシティブチェック（統合準備完了、実装は別途）
# is_sensitive = filter.check_text(source.raw_text)
```

### PersonNameValidator統合

```python
from src.validators.person_name_validator import PersonNameValidator

validator = PersonNameValidator()

# 人物名バリデーション（統合準備完了、実装は別途）
# issues = validator.validate(source.person_name)
```

### MASTER_EPISODES_CURRENT.csv互換性

`CuratedEpisode.to_master_format()` が全フィールドを生成し、マスターCSVへの直接マージが可能です。

```python
# マスター形式に変換
master_data = episode.to_master_format()

# 既存マスターに追加
df_master = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")
df_new = pd.DataFrame([master_data])
df_merged = pd.concat([df_master, df_new], ignore_index=True)
df_merged.to_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", index=False, encoding="utf-8-sig")
```

---

## 次のステップ

1. **Stage 1実装**: `scripts/collect_sources.py` でEpisodeSource生成
2. **Stage 2実装**: `scripts/verify_sources.py` でVerifiedSource検証
3. **Stage 3実装**: `scripts/curate_episodes.py` でCuratedEpisode生成
4. **Stage 4実装**: `scripts/validate_and_merge.py` でマージ統合

詳細は `docs/EPISODE_COLLECTION_PIPELINE.md` を参照してください。

---

**作成日**: 2025-12-17
**バージョン**: 1.0
**ステータス**: データモデル実装完了
