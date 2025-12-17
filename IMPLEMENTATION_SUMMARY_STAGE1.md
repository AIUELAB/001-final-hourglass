# Stage 1: collect-sources 実装完了サマリー

## 実装日時

2025-12-17

## 実装内容

エピソード収集パイプラインの Stage 1（情報源収集）を実装しました。

## 作成ファイル一覧

### コアファイル

1. **scripts/pipeline_collect_sources.py**
   - メインスクリプト（情報源収集パイプライン）
   - 手動CSV入力、API統合（Phase 2）、重複チェック、センシティブフィルター
   - コマンドライン: 661行

2. **src/models/episode_source.py**
   - EpisodeSourceデータモデル
   - source_id生成（MD5ハッシュ）、バリデーション、CSV保存・読み込み
   - コアロジック: 250行

3. **src/models/verified_source.py**
   - VerifiedSourceデータモデル（検証済みソース）
   - EpisodeSourceを継承、rejection_reason追加
   - 検証ロジック: 90行

4. **src/models/curated_episode.py**
   - CuratedEpisodeデータモデル（生成済みエピソード）
   - EPUP形式バリデーション、年齢範囲チェック
   - エピソード管理: 150行

5. **src/models/__init__.py**
   - モデルパッケージ初期化
   - EpisodeSource、VerifiedSource、CuratedEpisodeをエクスポート

### ドキュメント

6. **docs/PIPELINE_COLLECT_SOURCES.md**
   - Stage 1詳細ドキュメント
   - 使用方法、データモデル、エラーハンドリング、トラブルシューティング
   - 650行

7. **IMPLEMENTATION_SUMMARY_STAGE1.md**（このファイル）
   - 実装サマリー

### テスト

8. **tests/test_pipeline_collect_sources.py**
   - EpisodeSourceモデルのユニットテスト
   - 冪等性、バリデーション、CSV保存・読み込みのテスト
   - 200行

### サンプルデータ

9. **config/person_sources/sample_manual_sources.csv**
   - テスト用サンプルCSV
   - イチロー、山中伸弥、ドラえもんの3件

## 主要機能

### 実装済み（MVP）

1. **手動CSV入力**
   - person_name, source_url, raw_textから情報源を収集
   - センシティブフィルター適用（config/sensitive_keywords.yaml）
   - 冪等性保証（source_id MD5ハッシュ）

2. **データモデル**
   - EpisodeSource: 情報源管理
   - VerifiedSource: 検証済みソース管理
   - CuratedEpisode: 生成済みエピソード管理

3. **バリデーション**
   - URL形式検証（https://またはhttp://）
   - 必須フィールドチェック
   - person_type検証（REAL/FICTIONAL）
   - evidence_quality検証（A/B/C）
   - 文字数制限（著作権遵守：250文字）

4. **重複チェック**
   - 既存ソースとの重複を検出
   - source_id（MD5ハッシュ）ベースで判定
   - --check-duplicatesオプション

5. **エラーハンドリング**
   - graceful degradation（ライブラリ未インストール時も動作）
   - 詳細ログ出力（--verboseオプション）
   - スキップしたソースをskipped_sources.csvに記録

6. **センシティブフィルター**
   - 犯罪者、テロリスト、暴力団等を自動ブロック
   - 政治家、宗教家、実業家はレビュー必要
   - 許可リスト対応（ネルソン・マンデラ等）

### 今後実装予定（Phase 2）

1. **API統合**
   - Wikidata API（qwikidata）
   - Wikipedia API（wikipedia-api）
   - リトライ・レート制限対応（tenacity）

2. **検索クエリ生成**
   - API無し環境用フォールバック
   - 手動検索用クエリ一覧CSV出力（--generate-queriesオプション）

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

### コマンドラインオプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| --input | 入力CSVパス | 必須 |
| --output | 出力CSVパス | generated/episode_sources.csv |
| --mode | 収集モード（manual/api/hybrid） | manual |
| --sources | 使用するAPIソース（カンマ区切り） | - |
| --dry-run | ドライラン（ファイル書き込みなし） | True |
| --execute | 実際に実行 | False |
| --check-duplicates | 重複チェック対象CSV | - |
| --generate-queries | 検索クエリ一覧を生成 | False |
| --verbose | 詳細ログ出力 | False |

## 出力ファイル

1. **episode_sources.csv**
   - 収集した情報源
   - カラム: source_id, person_name, person_id, person_type, source_url, source_type, raw_text, context, evidence_quality, verification_status, collected_at, verified_at

2. **skipped_sources.csv**
   - スキップしたソース（センシティブ、エラー等）
   - カラム: person_name, source_url, skip_reason

3. **search_queries.csv**（--generate-queries指定時）
   - 手動検索用クエリ一覧
   - カラム: person_name, search_query

## データフロー

```
入力CSV（手動）
    ↓
センシティブフィルター
    ↓
EpisodeSource生成（source_id自動生成）
    ↓
重複チェック（--check-duplicates指定時）
    ↓
episode_sources.csv（出力）
skipped_sources.csv（出力）
```

## 冪等性保証

### source_id生成アルゴリズム

```python
composite_key = f"{person_name}||{source_url}"
hash_digest = hashlib.md5(composite_key.encode('utf-8')).hexdigest()
source_id = f"SRC-{hash_digest[:16]}"
```

同一の人物名+URLの組み合わせは同じsource_idを生成するため、重複インポートを防止できます。

## テスト

### ユニットテスト実行

```bash
# 全テスト実行
pytest tests/test_pipeline_collect_sources.py -v

# 特定のテストのみ実行
pytest tests/test_pipeline_collect_sources.py::TestEpisodeSource::test_generate_source_id -v
```

### テストカバレッジ

- source_id生成の冪等性
- 異なる入力で異なるsource_idが生成されることを確認
- EpisodeSource生成
- 不正なperson_type、evidence_quality、URL形式でエラーが発生することを確認
- 必須フィールド欠落でエラーが発生することを確認
- to_dict()、from_dict()メソッド
- CSV保存・読み込み
- 重複チェック

## 依存関係

### 必須ライブラリ

- pandas: CSV処理
- pyyaml: 設定ファイル読み込み（センシティブフィルター）

### オプショナルライブラリ（Phase 2実装予定）

- tenacity: リトライ・レート制限対応
- qwikidata: Wikidata API
- wikipedia-api: Wikipedia API

### Graceful Degradation

オプショナルライブラリが未インストールの場合も動作します:

```
WARNING: tenacity not installed. Retry functionality disabled.
WARNING: qwikidata not installed. Wikidata API disabled.
WARNING: wikipedia-api not installed. Wikipedia API disabled.
```

## 設定ファイル

### config/sensitive_keywords.yaml

センシティブフィルターの設定:

- sensitive_categories: 自動ブロック対象カテゴリ
- sensitive_keywords: 自動ブロック対象キーワード
- review_required_categories: レビュー必要カテゴリ
- allow_list: 許可リスト

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

## トラブルシューティング

### 問題: ライブラリが未インストール

**対処**:
```bash
pip install pandas pyyaml
```

オプショナル（Phase 2実装時）:
```bash
pip install tenacity qwikidata wikipedia-api
```

### 問題: 重複source_id

**対処**:
`--check-duplicates`を使用して自動スキップ:
```bash
python scripts/pipeline_collect_sources.py \
    --input new_sources.csv \
    --check-duplicates generated/episode_sources.csv \
    --execute
```

### 問題: URL形式エラー

**対処**:
URLは`https://`または`http://`で始まる必要があります。

## 次のステップ

### Stage 2: verify-sources（根拠品質検証）

実装予定:
- 根拠品質判定（A/B/C）
- センシティブ除外
- 重複除外
- PersonNameValidator適用

詳細: `docs/EPISODE_COLLECTION_PIPELINE.md`

## 関連ドキュメント

- 設計書: `docs/EPISODE_COLLECTION_PIPELINE.md`
- Stage 1詳細: `docs/PIPELINE_COLLECT_SOURCES.md`
- プロジェクト指示: `CLAUDE.md`

## 著作権・ライセンス

著作権遵守のため、以下を実施:

- raw_textは250文字以内に制限
- キーフレーズのみ抽出
- 長文引用は禁止

## 実装統計

- 総ファイル数: 9
- 総行数: 約2,000行
- コアロジック: 約1,200行
- ドキュメント: 約650行
- テスト: 約200行

## 品質保証

- デフォルトセーフ: --dry-runがデフォルト（誤操作防止）
- Fail-Fast原則: エラーは早期に顕在化
- 冪等性保証: source_id MD5ハッシュ
- センシティブフィルター: 自動ブロック + レビュー必要
- graceful degradation: ライブラリ未インストール時も動作

## 完了チェックリスト

- [x] EpisodeSourceデータモデル実装
- [x] 手動CSV入力実装
- [x] センシティブフィルター統合
- [x] 冪等性保証（source_id MD5ハッシュ）
- [x] 重複チェック機能
- [x] バリデーション（URL形式、必須フィールド等）
- [x] エラーハンドリング（graceful degradation）
- [x] ログ出力（通常、詳細）
- [x] ユニットテスト作成
- [x] サンプルデータ作成
- [x] ドキュメント作成（詳細、サマリー）
- [ ] API統合（Phase 2実装予定）
- [ ] 検索クエリ生成（Phase 2実装予定）
- [ ] リトライ機構（Phase 2実装予定）

## 備考

- 設計書 `docs/EPISODE_COLLECTION_PIPELINE.md` に基づき、Phase 1（MVP）の実装を完了
- API統合（Wikidata、Wikipedia）はPhase 2で実装予定
- 既存の `src/sensitive_filter.py` と `src/source_adapters/base.py` を活用
- 品質優先原則（Quality-First）に準拠：ダミーデータ・プレースホルダー禁止
