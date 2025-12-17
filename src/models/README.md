# エピソード収集パイプライン - データモデル

## 概要

このディレクトリには、エピソード収集パイプラインで使用する3つの主要データモデルが含まれています。

## モデル一覧

### EpisodeSource (`episode_source.py`)

情報源を管理する基底データモデル。

- **CSV**: `episode_sources.csv`
- **用途**: Stage 1（情報源収集）で生成
- **主な機能**:
  - source_id自動生成（MD5ハッシュ、冪等性保証）
  - URL形式バリデーション
  - CSV保存・読み込み
  - 重複チェック

### VerifiedSource (`verified_source.py`)

検証済み情報源を管理するデータモデル。EpisodeSourceを継承。

- **CSV**: `verified_sources.csv`
- **用途**: Stage 2（根拠品質検証）で生成
- **主な機能**:
  - A/B/C品質自動判定
  - 検証マーク（mark_verified/mark_rejected）
  - 品質フィルタリング
  - 検証済みフィルタリング

### CuratedEpisode (`curated_episode.py`)

生成済みエピソードを管理するデータモデル。

- **CSV**: `curated_episodes.csv`
- **用途**: Stage 3（エピソード生成）で生成
- **主な機能**:
  - EPUP形式バリデーション
  - バリデーション結果マーク（mark_passed/mark_failed/mark_review）
  - MASTER_EPISODES_CURRENT.csv互換形式変換
  - ステータス・品質フィルタリング

## クイックスタート

```python
from src.models import EpisodeSource, VerifiedSource, CuratedEpisode
from pathlib import Path

# 1. 情報源作成
source = EpisodeSource(
    person_name="イチロー",
    person_id="P001ABC12",
    person_type="REAL",
    source_url="https://ja.wikipedia.org/wiki/イチロー",
    source_type="wikipedia",
    raw_text="2004年シーズン262安打記録",
)

# 2. CSV保存
EpisodeSource.save_to_csv([source], Path("episode_sources.csv"))

# 3. 検証済みソース作成
verified = VerifiedSource.from_dict(source.to_dict())
verified.mark_verified("Wikipedia記事確認済み")

# 4. エピソード生成
episode = CuratedEpisode(
    person_id=source.person_id,
    person_name=source.person_name,
    age=31,
    episode_text="あなたと同じ31歳のとき、イチローは...",
    source_id=source.source_id,
    source_url=source.source_url,
    evidence_quality=verified.evidence_quality,
)

# 5. バリデーション合格マーク
episode.mark_passed()

# 6. マスター形式変換
master_data = episode.to_master_format()
```

## デモ実行

```bash
python examples/demo_data_models.py
```

## テスト実行

```bash
# 全テスト
pytest tests/models/ -v

# 特定モデル
pytest tests/models/test_episode_source.py -v

# カバレッジ付き
pytest tests/models/ --cov=src.models --cov-report=html
```

## ドキュメント

詳細な仕様は以下を参照してください。

- **データモデル仕様書**: `docs/DATA_MODELS.md`
- **パイプライン設計書**: `docs/EPISODE_COLLECTION_PIPELINE.md`
- **CSVスキーマ定義**: `config/schemas/`

## フィールド対応表

### EpisodeSource → VerifiedSource

| EpisodeSource | VerifiedSource | 説明 |
|--------------|----------------|------|
| すべてのフィールド | 継承 | EpisodeSourceを継承 |
| - | `verifier_notes` | 検証者ノート（追加） |

### VerifiedSource → CuratedEpisode

| VerifiedSource | CuratedEpisode | 説明 |
|---------------|----------------|------|
| `source_id` | `source_id` | 根拠ソースID |
| `source_url` | `source_url` | 根拠URL |
| `evidence_quality` | `evidence_quality` | 根拠品質 |
| `person_id` | `person_id` | 人物ID |
| `person_name` | `person_name` | 人物名 |
| `person_type` | `person_type` | 人物タイプ |
| - | `age` | 年齢（新規） |
| - | `episode_text` | エピソード本文（新規） |
| - | `validation_status` | バリデーション結果（新規） |

### CuratedEpisode → MASTER_EPISODES_CURRENT.csv

`CuratedEpisode.to_master_format()` で全フィールドを自動生成。

## 設計原則

### 1. 冪等性保証

同一ソースの重複インポートを防止するため、`source_id` を MD5 ハッシュで生成します。

```python
source_id = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
# 結果: "SRC-a3f5b9c2d4e6f8a0"（常に同じ値）
```

### 2. デフォルトセーフ

- `evidence_quality`: デフォルト "C"（未検証）
- `verification_status`: デフォルト "unverified"
- `validation_status`: デフォルト "pending"

### 3. Fail-Fast

バリデーション失敗時は即座に `ValueError` を発生させます。

```python
try:
    source = EpisodeSource(person_type="INVALID")  # ValueError発生
except ValueError as e:
    print(f"Validation error: {e}")
```

### 4. UTF-8 BOM必須

CSV保存時は `encoding='utf-8-sig'` を使用し、Excel互換性を保証します。

## データフロー

```
【Stage 1: collect-sources】
    ↓
EpisodeSource (episode_sources.csv)
    ↓
【Stage 2: verify-sources】
    ↓
VerifiedSource (verified_sources.csv, A/B品質のみ)
    ↓
【Stage 3: curate-episodes】
    ↓
CuratedEpisode (curated_episodes.csv, EPUP形式)
    ↓
【Stage 4: validate-and-merge】
    ↓
MASTER_EPISODES_CURRENT.csv (マージ統合)
```

## バリデーションルール

### EpisodeSource

- 必須フィールド: `person_name`, `person_id`, `source_url`, `raw_text`
- URL形式: `^https?://.+`
- `person_type`: `REAL` or `FICTIONAL`
- `evidence_quality`: `A`, `B`, `C`
- `verification_status`: `verified`, `unverified`, `rejected`
- `raw_text`: 250文字以内推奨（著作権遵守）

### VerifiedSource

EpisodeSourceのバリデーションに加えて:

- 自動品質判定（URL/ドメインベース）
- A品質: `.go.jp`, `.ac.jp`, `.edu`, `ndl.go.jp`
- B品質: `wikipedia.org`, `britannica.com`
- C品質: 上記以外

### CuratedEpisode

- 必須フィールド: `person_id`, `person_name`, `age`, `episode_text`, `source_id`, `source_url`
- age範囲: 0-150
- `episode_text`: 「あなたと同じ」で開始推奨
- `validation_status`: `pending`, `passed`, `failed`, `review`

## エラーハンドリング

### CSV読み込みエラー

ファイルが存在しない場合は空リストを返します（例外は発生しません）。

```python
sources = EpisodeSource.load_from_csv(Path("nonexistent.csv"))
# 結果: [] (空リスト)
```

### 行単位のエラー

個別行のバリデーションエラーは警告ログ出力後、スキップされます。

```python
# ログ出力例:
# ERROR: Failed to load row: Invalid person_type: INVALID
```

## 今後の拡張

### Phase 1 (MVP)

- [x] EpisodeSource実装
- [x] VerifiedSource実装
- [x] CuratedEpisode実装
- [x] CSVスキーマ定義
- [x] ユニットテスト

### Phase 2 (統合)

- [ ] SensitiveFilter統合
- [ ] PersonNameValidator統合
- [ ] fact_checker統合
- [ ] episode_validator統合

### Phase 3 (最適化)

- [ ] バッチ処理最適化
- [ ] キャッシュ機構実装
- [ ] パフォーマンステスト

## トラブルシューティング

### ValueError: Invalid URL format

URLが `http://` または `https://` で始まっているか確認してください。

```python
# NG
source_url = "www.example.com"

# OK
source_url = "https://www.example.com"
```

### ValueError: Invalid person_type

`person_type` は `REAL` または `FICTIONAL` のみ許可されます。

```python
# NG
person_type = "PERSON"

# OK
person_type = "REAL"
```

### raw_text長さ警告

250文字を超える場合、著作権遵守のため警告ログが出力されます。

```python
# 警告が出る
raw_text = "x" * 300

# 推奨
raw_text = "キーフレーズのみ抽出（250文字以内）"
```

## 関連リソース

- **設計書**: `docs/EPISODE_COLLECTION_PIPELINE.md`
- **データモデル仕様書**: `docs/DATA_MODELS.md`
- **CSVスキーマ**: `config/schemas/`
- **テストコード**: `tests/models/`
- **デモスクリプト**: `examples/demo_data_models.py`

---

**作成日**: 2025-12-17
**バージョン**: 1.0
**メンテナ**: AIUELAB
