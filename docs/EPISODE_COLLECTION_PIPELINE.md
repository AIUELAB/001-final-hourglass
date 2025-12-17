# 有名人エピソード収集パイプライン - システム設計書

## 目次

1. [概要](#概要)
2. [システムアーキテクチャ](#システムアーキテクチャ)
3. [データモデル](#データモデル)
4. [パイプライン仕様](#パイプライン仕様)
5. [品質ゲート](#品質ゲート)
6. [実装計画](#実装計画)
7. [技術選定](#技術選定)
8. [運用ガイドライン](#運用ガイドライン)

---

## 概要

### 目的

有名人エピソードの「収集→検証→整理→再利用」パイプラインを設計し、**量と質を両立**しながら継続的に増やせるシステムを構築する。

### 設計原則

1. **品質優先**: ダミーデータ・プレースホルダーは絶対禁止（Fail-Fast）
2. **冪等性保証**: 同一ソースの重複インポートを防止
3. **段階的品質評価**: A（一次情報）/ B（二次情報2+）/ C（未検証）
4. **既存システム統合**: 既存バリデータ・品質監視を完全流用
5. **デフォルトセーフ**: --dry-run（変更なし）がデフォルト

### スコープ

- **対象**: 実在人物・架空キャラクター（person_type: REAL/FICTIONAL）
- **除外**: センシティブ人物（犯罪者等）
- **著作権遵守**: 長文引用禁止、キーフレーズのみ許可

---

## システムアーキテクチャ

### 全体図

```
┌─────────────────────────────────────────────────────────────────┐
│                      情報源（Source Layer）                        │
├─────────────────────────────────────────────────────────────────┤
│  1. Wikidata API    2. Wikipedia API    3. 手動CSV入力            │
│     └─基本情報取得     └─構造化データ抽出     └─キュレーション         │
└─────────┬───────────────────────┬───────────────────┬───────────┘
          │                       │                   │
          v                       v                   v
┌─────────────────────────────────────────────────────────────────┐
│         Stage 1: collect-sources（情報源収集）                     │
├─────────────────────────────────────────────────────────────────┤
│  入力: person_name, birth_year, person_type                      │
│  処理: ・API経由で関連情報を検索                                     │
│       ・検索クエリ生成（{name} + 逸話/回想/自伝/インタビュー等）         │
│       ・手動CSV（source_url, raw_text, context）のインポート          │
│  出力: episode_sources.csv（中間ファイル）                          │
└─────────┬───────────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────────┐
│         Stage 2: verify-sources（根拠品質検証）                     │
├─────────────────────────────────────────────────────────────────┤
│  入力: episode_sources.csv                                       │
│  処理: ・根拠品質判定（A/B/C）                                       │
│       ・重複除外（source_url MD5ハッシュ）                           │
│       ・センシティブ除外（ブラックリスト照合）                           │
│  出力: verified_sources.csv + rejected_sources.csv               │
└─────────┬───────────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────────┐
│         Stage 3: curate-episodes（エピソード生成）                  │
├─────────────────────────────────────────────────────────────────┤
│  入力: verified_sources.csv                                      │
│  処理: ・LLM経由で「あなたと同じ〜」形式に変換                          │
│       ・EPUP品質ルール適用（メタ表現禁止、年齢境界等）                   │
│       ・PersonNameValidator適用（人物名正規化）                      │
│  出力: curated_episodes.csv（未マージ状態）                         │
└─────────┬───────────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────────┐
│         Stage 4: validate-and-merge（品質ゲート+統合）              │
├─────────────────────────────────────────────────────────────────┤
│  入力: curated_episodes.csv                                      │
│  処理: 【品質ゲート】                                               │
│       1. episode_validator（CRITICAL即reject）                   │
│       2. fact_checker（high/critical→review_queue）              │
│       3. 重複検出（detect-only、レポート化）                         │
│       4. 根拠品質C→review_queue（マスター統合せず）                   │
│  出力: MASTER_EPISODES_CURRENT.csv + review_queue.csv            │
└─────────┬───────────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────────┐
│         Stage 5: report（統計・比較分析）                           │
├─────────────────────────────────────────────────────────────────┤
│  入力: マージ前後のMASTER_EPISODES_CURRENT.csv                     │
│  処理: ・Before/After比較（件数、person_id数、品質スコア平均）          │
│       ・KPI計算（scheduled_epup_check統合）                        │
│       ・根拠品質別内訳（A/B/C）                                      │
│  出力: reports/collection_pipeline_YYYYMMDD_HHMMSS.json          │
└─────────────────────────────────────────────────────────────────┘
```

### データフロー

```
[Wikidata/Wikipedia API]
        ↓
    Raw Sources ──┐
                  ├→ episode_sources.csv（全収集）
[手動CSV]          │
        ↓         │
    Manual CSV ──┘

episode_sources.csv
        ↓
    【品質判定】
        ├→ verified_sources.csv（A/B品質）
        └→ rejected_sources.csv（C品質 or センシティブ）

verified_sources.csv
        ↓
    【LLM生成】
        ↓
    curated_episodes.csv

curated_episodes.csv
        ↓
    【品質ゲート】
        ├→ MASTER_EPISODES_CURRENT.csv（合格）
        └→ review_queue.csv（要レビュー）
```

### 既存システムとの統合ポイント

| 既存コンポーネント | 統合箇所 | 役割 |
|-------------------|---------|------|
| `scripts/episode_validator.py` | Stage 4 | フォーマット・整合性検証（CRITICAL即reject） |
| `src/validators/person_name_validator.py` | Stage 3 & 4 | 人物名正規化（別名・職業接頭辞除去） |
| `scripts/normalize_person_names.py` | Stage 3 | 9パターン自動正規化 |
| `scripts/merge_duplicate_persons.py` | Stage 4（事後） | 重複検出（detect-only） |
| `src/fact_checker.py` | Stage 4 | 事実確認（ハルシネーション検出） |
| `scripts/scheduled_epup_check.py` | Stage 5 | KPI計算・品質監視 |
| `preserved/data/MASTER_EPISODES_CURRENT.csv` | Stage 4（出力） | マスターDB統合 |

---

## データモデル

### episode_sources.csv（中間ファイル）

根拠情報を管理する中間ファイル。

| カラム名 | 型 | 必須 | 説明 | 例 |
|---------|---|-----|------|---|
| source_id | str | ✅ | ソースID（MD5ハッシュ） | `SRC-a3f5b9...` |
| person_name | str | ✅ | 人物名 | `イチロー` |
| person_id | str | ✅ | 人物ID（既存 or 新規） | `P001` |
| person_type | str | ✅ | 人物タイプ | `REAL`, `FICTIONAL` |
| source_url | str | ✅ | 情報源URL | `https://ja.wikipedia.org/wiki/...` |
| source_type | str | ✅ | ソースタイプ | `wikidata`, `wikipedia`, `manual` |
| raw_text | str | ✅ | 抽出テキスト（キーフレーズのみ） | `2004年シーズン262安打記録` |
| context | str | - | 文脈情報 | `年齢31歳時の業績` |
| evidence_quality | str | ✅ | 根拠品質 | `A`, `B`, `C` |
| verification_status | str | ✅ | 検証ステータス | `verified`, `unverified`, `rejected` |
| collected_at | datetime | ✅ | 収集日時 | `2025-12-17T14:00:00` |
| verified_at | datetime | - | 検証日時 | `2025-12-17T14:30:00` |

**根拠品質定義:**

| 品質 | 定義 | 例 |
|-----|------|---|
| **A** | 一次情報（公式サイト、学術論文、自伝、インタビュー記録） | 本人ブログ、公式伝記、学術論文 |
| **B** | 二次情報2件以上で裏付けあり | Wikipedia + 新聞記事2件 |
| **C** | 未検証（単一ソース、出典不明） | 出典不明のブログ記事1件 |

### verified_sources.csv（検証済み）

品質AまたはBの検証済みソース。

- **スキーマ**: episode_sources.csvと同一
- **フィルタ**: `evidence_quality IN ('A', 'B') AND verification_status = 'verified'`

### rejected_sources.csv（却下）

品質Cまたはセンシティブで却下されたソース。

- **スキーマ**: episode_sources.csv + `rejection_reason`
- **フィルタ**: `evidence_quality = 'C' OR verification_status = 'rejected'`

### curated_episodes.csv（生成済みエピソード）

EPUP形式に変換された未マージエピソード。

| カラム名 | 型 | 必須 | 説明 | 例 |
|---------|---|-----|------|---|
| episode_id | str | ✅ | エピソードID（未採番は空） | `EP-TEMP-001` |
| person_id | str | ✅ | 人物ID | `P001` |
| person_name | str | ✅ | 正規化済み人物名 | `イチロー` |
| age | int | ✅ | 年齢 | `31` |
| episode_text | str | ✅ | エピソード本文 | `あなたと同じ31歳のとき...` |
| source_id | str | ✅ | 根拠ソースID | `SRC-a3f5b9...` |
| source_url | str | ✅ | 根拠URL | `https://ja.wikipedia.org/...` |
| evidence_quality | str | ✅ | 根拠品質 | `A`, `B`, `C` |
| validation_status | str | ✅ | バリデーション結果 | `pending`, `passed`, `failed`, `review` |
| validation_issues | str | - | 検出された問題（JSON） | `[{"type": "format_violation", ...}]` |
| generated_at | datetime | ✅ | 生成日時 | `2025-12-17T15:00:00` |

### review_queue.csv（レビュー待ち）

品質ゲートで要レビューと判定されたエピソード。

- **スキーマ**: curated_episodes.csv + `review_reason`, `priority`
- **トリガー**:
  - `evidence_quality = 'C'`（未検証根拠）
  - `fact_checker.severity IN ('high', 'critical')`（事実確認失敗）
  - `episode_validator.severity = 'CRITICAL'`（フォーマット違反）

### MASTER_EPISODES_CURRENT.csv拡張列

既存マスターCSVに以下の列を追加。

| カラム名 | 型 | 説明 | 例 |
|---------|---|------|---|
| source_url | str | 根拠URL | `https://ja.wikipedia.org/...` |
| verification_status | str | 検証ステータス | `verified`, `unverified` |
| evidence_quality | str | 根拠品質 | `A`, `B`, `C` |

**マイグレーション戦略:**

- 既存エピソードは `evidence_quality = 'C'`, `verification_status = 'unverified'` をデフォルト値とする
- 新規追加エピソードのみ適切な値を設定

---

## パイプライン仕様

### Stage 1: collect-sources（情報源収集）

#### 入力

- `input.csv`: 人物リスト（person_name, birth_year, person_type）
- または CLI引数: `--person-name "イチロー" --birth-year 1973 --person-type REAL`

#### 処理フロー

1. **Wikidata検索**
   - クエリ: `{person_name}` + 出身地/職業フィルタ
   - 取得: Wikidata ID, 関連プロパティ（P569生年月日、P570没年月日等）

2. **Wikipedia検索**
   - クエリ: Wikidata IDまたは人物名
   - 取得: セクション別テキスト（「経歴」「業績」「エピソード」等）
   - 抽出: キーフレーズのみ（著作権遵守：250文字以内）

3. **検索クエリ生成**（API無し環境向け）
   - 出力: `search_queries.csv`（手動検索用）
   - クエリ例:
     - `"{person_name}" 逸話 エピソード`
     - `"{person_name}" {age}歳 業績`
     - `"{person_name}" 自伝 回想`

4. **手動CSVインポート**
   - フォーマット: `person_name, source_url, raw_text, context`
   - バリデーション: URLフォーマット、文字数制限

5. **source_id生成**
   - アルゴリズム: `MD5(person_name + source_url)`
   - 目的: 冪等性保証（重複検出）

#### 出力

- `generated/episode_sources.csv`
- `generated/search_queries.csv`（API無し環境用）

#### エラーハンドリング

| エラー | 対処 |
|--------|-----|
| API Rate Limit | リトライ（指数バックオフ）or スキップ |
| 人物名なし（Wikidata） | ログ出力 + スキップ |
| 著作権違反（長文） | 250文字でトリミング + 警告ログ |

---

### Stage 2: verify-sources（根拠品質検証）

#### 入力

- `generated/episode_sources.csv`

#### 処理フロー

1. **重複除外**
   - 既存source_idとの照合（MD5ハッシュ）
   - 重複の場合: スキップ + ログ出力

2. **品質判定**
   - **A判定**: URL正規表現マッチ（公式サイト・学術ドメイン）
     ```python
     A_DOMAINS = [
         r'\.go\.jp$',          # 政府公式
         r'\.ac\.jp$',          # 学術機関
         r'\.edu$',             # 教育機関
         r'\.org/wiki/',        # Wikipedia（一部）
         r'ndl\.go\.jp',        # 国会図書館
     ]
     ```
   - **B判定**: 同一エピソードで2件以上のソース確認
   - **C判定**: 上記以外（単一ソース、出典不明）

3. **センシティブ除外**
   - ブラックリスト照合: `config/blacklist_names.json`
   - センシティブキーワード検出: `犯罪`, `容疑`, `逮捕` 等

4. **PersonNameValidator適用**
   - 別名・通称の正規化（`ALIAS_KEYWORDS`）
   - 職業接頭辞除去（`PROFESSION_KEYWORDS`）

#### 出力

- `generated/verified_sources.csv`（品質A/B）
- `generated/rejected_sources.csv`（品質C + 却下理由）
- `reports/source_verification_YYYYMMDD_HHMMSS.json`

---

### Stage 3: curate-episodes（エピソード生成）

#### 入力

- `generated/verified_sources.csv`

#### 処理フロー

1. **LLM生成プロンプト**
   ```
   以下の情報から「あなたと同じ{age}歳のとき、{person_name}は」形式で
   100-300文字のエピソードを生成してください。

   【情報】
   人物: {person_name}
   年齢: {age}
   根拠: {raw_text}
   文脈: {context}

   【禁止事項】
   - メタ表現（「架空の」「フィクション」等）
   - プレースホルダー（TODO, [...]等）
   - 年齢境界違反（没年を超える年齢設定）

   【person_type別方針】
   - REAL: 事実ベースで慎重に生成
   - FICTIONAL: 作品世界内の視点でフィクション生成
   ```

2. **EPUP品質ルール適用**（CLAUDE.mdルール準拠）
   - メタ表現禁止（架空キャラ）
   - 年齢境界チェック（birth_year ~ death_year範囲内）
   - 人物名正規化（PersonNameValidator）

3. **年齢推定ロジック**
   - Wikipedia年代情報からage抽出
   - 不明の場合: 代表的年齢（30, 40, 50歳）から選択

4. **episode_id採番**
   - 形式: `EP-TEMP-{連番}`（マージ時に正式採番）

#### 出力

- `generated/curated_episodes.csv`
- `logs/episode_generation_YYYYMMDD_HHMMSS.log`

#### エラーハンドリング

| エラー | 対処 |
|--------|-----|
| LLM生成失敗 | リトライ3回 → スキップ + エラーログ |
| フォーマット違反 | 再生成1回 → 失敗なら却下 |
| 年齢境界違反 | 却下 + rejected_sources.csvに記録 |

---

### Stage 4: validate-and-merge（品質ゲート+統合）

#### 入力

- `generated/curated_episodes.csv`

#### 処理フロー（品質ゲート）

```python
def quality_gate_check(episode: Dict) -> Tuple[bool, str]:
    """
    品質ゲート：4段階チェック

    Returns:
        (合格/不合格, ステータス)
        ステータス: 'passed', 'failed', 'review'
    """
    issues = []

    # 1. episode_validator（CRITICAL即reject）
    validation_result = episode_validator.validate_episode(episode)
    critical_issues = [i for i in validation_result if i.severity == 'CRITICAL']
    if critical_issues:
        return (False, 'failed')

    # 2. fact_checker（high/critical→review_queue）
    fact_report = fact_checker.check_episode(
        person_id=episode['person_id'],
        person_name=episode['person_name'],
        episode_text=episode['episode_text'],
        birth_year=episode.get('birth_year')
    )
    high_violations = [v for v in fact_report.violations
                       if v.severity in ('high', 'critical')]
    if high_violations:
        return (False, 'review')

    # 3. 重複検出（detect-only）
    duplicate_check = detect_duplicates(episode['episode_text'])
    if duplicate_check['is_duplicate']:
        issues.append(f"重複エピソード: {duplicate_check['original_id']}")
        return (False, 'review')

    # 4. 根拠品質C→review_queue
    if episode['evidence_quality'] == 'C':
        return (False, 'review')

    return (True, 'passed')
```

#### マージ処理

1. **バックアップ作成**
   - `preserved/data/MASTER_EPISODES_CURRENT_backup_YYYYMMDD_HHMMSS.csv`

2. **person_id統合**
   - 既存person_idとの照合（name正規化後）
   - 新規人物: 新規person_id採番

3. **episode_id採番**
   - 既存最大ID + 1から連番
   - 形式: `EP-{9桁ゼロパディング}`

4. **デフォルト値設定**
   - `fact_check_result`: `verified` or `unverified`（fact_checkerスコアベース）
   - `source`: `COLLECTION_PIPELINE`
   - `generation_timestamp`: 現在時刻

5. **CSV書き込み**
   - エンコーディング: `utf-8-sig`（BOM付き）
   - ソート: `person_id`, `age` 順

#### 出力

- `preserved/data/MASTER_EPISODES_CURRENT.csv`（更新）
- `generated/review_queue.csv`（要レビュー）
- `preserved/data/MASTER_EPISODES_CURRENT_backup_*.csv`（バックアップ）

---

### Stage 5: report（統計・比較分析）

#### 入力

- マージ前後のMASTER_EPISODES_CURRENT.csv

#### 処理フロー

1. **Before/After比較**
   ```python
   comparison = {
       "before": {
           "total_episodes": 5000,
           "unique_persons": 1200,
           "avg_quality_score": 7.8,
       },
       "after": {
           "total_episodes": 5500,
           "unique_persons": 1350,
           "avg_quality_score": 7.9,
       },
       "diff": {
           "episodes_added": 500,
           "persons_added": 150,
           "quality_improvement": 0.1,
       }
   }
   ```

2. **根拠品質別内訳**
   - A品質件数・割合
   - B品質件数・割合
   - C品質件数・割合（review_queue内訳）

3. **KPI計算**（`scheduled_epup_check.py`統合）
   - グループ名混入率
   - 組織名・肩書き混入率
   - 英字別名検出率
   - メタ表現検出率

4. **品質ゲート統計**
   - 合格率
   - 不合格理由別内訳
   - レビュー待ち件数

#### 出力

- `reports/collection_pipeline_YYYYMMDD_HHMMSS.json`
- コンソール出力（サマリー）

---

## 品質ゲート

### 品質基準マトリクス

| チェック項目 | ツール | CRITICAL条件 | WARNING条件 | 処理 |
|-------------|--------|-------------|------------|------|
| **フォーマット** | episode_validator | 「あなたと同じ」形式違反 | 文字数不足 | CRITICAL→reject |
| **人物名整合性** | episode_validator | 本文に人物名なし | - | CRITICAL→reject |
| **年齢整合性** | episode_validator | 本文と登録年齢不一致 | - | CRITICAL→reject |
| **メタ表現** | episode_validator | 架空キャラに「実在しない」等 | - | CRITICAL→reject |
| **事実確認** | fact_checker | 時代錯誤、年代不整合 | ハルシネーションパターン | high/critical→review |
| **重複** | merge_duplicate_persons | - | 重複検出 | review_queueへ |
| **人物名正規化** | PersonNameValidator | ブラックリスト該当 | 別名・職業接頭辞 | ERROR→reject, WARNING→auto-fix |
| **根拠品質** | カスタムロジック | - | evidence_quality='C' | review_queueへ |

### 合格条件

エピソードがマスターDBに統合される条件：

1. **すべてのCRITICALエラーがゼロ**
2. **fact_checker.severity != 'critical'**
3. **evidence_quality IN ('A', 'B')**
4. **重複なし**

### 不合格時の処理

| ステータス | 処理 | 保存先 |
|-----------|------|--------|
| `failed` | 即座に却下 | `rejected_sources.csv` |
| `review` | レビュー待ちキューに追加 | `review_queue.csv` |
| `passed` | マスターDBに統合 | `MASTER_EPISODES_CURRENT.csv` |

---

## 実装計画

### Phase 1: MVP（基盤構築）

**目標**: 手動CSVインポート + 品質ゲート検証

#### 実装スコープ

1. **データモデル構築**
   - `episode_sources.csv`, `verified_sources.csv`, `curated_episodes.csv` スキーマ定義
   - MASTER_EPISODES_CURRENT.csvマイグレーション（新列追加）

2. **Stage 1実装（手動CSVのみ）**
   - `scripts/collect_sources.py`
   - 入力: 手動CSV（`person_name, source_url, raw_text, context`）
   - 出力: `episode_sources.csv`
   - 冪等性保証（source_id MD5ハッシュ）

3. **Stage 2実装**
   - `scripts/verify_sources.py`
   - 品質判定ロジック（A/B/C）
   - センシティブ除外
   - PersonNameValidator統合

4. **Stage 4実装（品質ゲートのみ）**
   - `scripts/validate_and_merge.py`
   - 既存バリデータ統合（episode_validator, fact_checker）
   - review_queue.csv生成
   - --dry-runモード実装

5. **Stage 5実装**
   - `scripts/generate_collection_report.py`
   - Before/After比較
   - 品質ゲート統計

#### 成果物

- 5つのスクリプト（collect, verify, curate, validate, report）
- データモデル定義（CSV/JSONスキーマ）
- テストスイート（pytest）

#### 期間

2週間

---

### Phase 2: 自動化拡張（API統合）

**目標**: Wikidata/Wikipedia API統合 + LLM生成自動化

#### 実装スコープ

1. **Wikidata API統合**
   - ライブラリ: `qwikidata`
   - 人物検索・基本情報取得

2. **Wikipedia API統合**
   - ライブラリ: `wikipedia-api`
   - セクション別テキスト抽出
   - 著作権遵守（250文字制限）

3. **Stage 3実装**
   - `scripts/curate_episodes.py`
   - LLM経由エピソード生成
   - EPUP品質ルール適用
   - 年齢推定ロジック

4. **検索クエリ生成**
   - API無し環境用フォールバック
   - `search_queries.csv`出力

5. **リトライ・レート制限対応**
   - 指数バックオフ実装
   - キャッシュ機構（API応答）

#### 成果物

- API統合スクリプト
- LLM生成パイプライン
- キャッシュ機構

#### 期間

3週間

---

### Phase 3: 運用改善（モニタリング・最適化）

**目標**: review_queue管理UI + KPI監視統合 + 継続的改善

#### 実装スコープ

1. **review_queue管理UI**
   - Web UI（Streamlit or Flask）
   - レビュー承認/却下ワークフロー
   - バッチ承認機能

2. **KPI監視統合**
   - `scheduled_epup_check.py`への統合
   - 日次チェック項目追加:
     - 根拠品質別割合（A/B/C）
     - 品質ゲート合格率
     - review_queue滞留件数

3. **パフォーマンス最適化**
   - バッチ処理並列化
   - API応答キャッシュ
   - 重複検出高速化（Bloom Filter検討）

4. **ドキュメント整備**
   - 運用ガイド
   - トラブルシューティング
   - API設定手順

#### 成果物

- review_queue管理UI
- KPI監視ダッシュボード
- 運用ドキュメント

#### 期間

2週間

---

## 技術選定

### 推奨ライブラリ

| 用途 | ライブラリ | バージョン | 理由 |
|-----|-----------|----------|------|
| **Wikidata API** | `qwikidata` | 0.4.2+ | 構造化データ取得、Pythonic API |
| **Wikipedia API** | `wikipedia-api` | 0.6.0+ | セクション別取得、言語対応 |
| **LLM統合** | `anthropic` | 既存 | 既存コードベースと統合 |
| **CSV処理** | `pandas` | 既存 | 既存コードベースと統合 |
| **ハッシュ** | `hashlib` | 標準ライブラリ | MD5生成（冪等性） |
| **リトライ** | `tenacity` | 8.0+ | 指数バックオフ実装 |
| **Web UI** | `streamlit` | 1.29+ | 迅速なUI構築 |

### 冪等性実装方法

#### source_id生成

```python
import hashlib

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

#### 重複チェック

```python
def is_duplicate_source(source_id: str, existing_sources_csv: str) -> bool:
    """
    既存ソースとの重複をチェック

    Args:
        source_id: 検証対象のソースID
        existing_sources_csv: 既存ソースCSVパス

    Returns:
        True: 重複, False: 新規
    """
    df = pd.read_csv(existing_sources_csv, encoding='utf-8-sig')
    return source_id in df['source_id'].values
```

### バックアップ戦略

#### 自動バックアップ

```python
from datetime import datetime
from pathlib import Path
import shutil

def create_backup(csv_path: Path) -> Path:
    """
    マスターCSVの自動バックアップ

    Args:
        csv_path: バックアップ対象CSVパス

    Returns:
        バックアップファイルパス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{csv_path.stem}_backup_{timestamp}{csv_path.suffix}"
    backup_path = csv_path.parent / backup_name

    shutil.copy2(csv_path, backup_path)
    print(f"✅ バックアップ作成: {backup_path}")

    return backup_path
```

#### ロールバック機能

```python
def rollback_to_backup(master_csv: Path, backup_csv: Path):
    """
    バックアップからロールバック

    Args:
        master_csv: マスターCSVパス
        backup_csv: バックアップCSVパス
    """
    if not backup_csv.exists():
        raise FileNotFoundError(f"バックアップが見つかりません: {backup_csv}")

    shutil.copy2(backup_csv, master_csv)
    print(f"🔄 ロールバック完了: {backup_csv} → {master_csv}")
```

---

## 運用ガイドライン

### 基本コマンド

#### Stage 1: 情報源収集

```bash
# 手動CSV（MVP）
python scripts/collect_sources.py \
    --input manual_sources.csv \
    --output generated/episode_sources.csv \
    --dry-run

# API経由（Phase 2）
python scripts/collect_sources.py \
    --person-name "イチロー" \
    --birth-year 1973 \
    --person-type REAL \
    --sources wikidata,wikipedia \
    --output generated/episode_sources.csv \
    --dry-run
```

#### Stage 2: 根拠検証

```bash
python scripts/verify_sources.py \
    --input generated/episode_sources.csv \
    --output generated/verified_sources.csv \
    --rejected generated/rejected_sources.csv \
    --dry-run
```

#### Stage 3: エピソード生成

```bash
python scripts/curate_episodes.py \
    --input generated/verified_sources.csv \
    --output generated/curated_episodes.csv \
    --llm-model claude-sonnet-4-5 \
    --dry-run
```

#### Stage 4: 品質ゲート+統合

```bash
# ドライラン（変更なし）
python scripts/validate_and_merge.py \
    --input generated/curated_episodes.csv \
    --master preserved/data/MASTER_EPISODES_CURRENT.csv \
    --review-queue generated/review_queue.csv \
    --dry-run

# 本番実行（バックアップ→統合）
python scripts/validate_and_merge.py \
    --input generated/curated_episodes.csv \
    --master preserved/data/MASTER_EPISODES_CURRENT.csv \
    --review-queue generated/review_queue.csv \
    --execute
```

#### Stage 5: レポート生成

```bash
python scripts/generate_collection_report.py \
    --before preserved/data/MASTER_EPISODES_CURRENT_backup_YYYYMMDD_HHMMSS.csv \
    --after preserved/data/MASTER_EPISODES_CURRENT.csv \
    --output reports/collection_pipeline_YYYYMMDD_HHMMSS.json
```

### ワークフロー例

#### 新規50人分のエピソードを収集

```bash
# 1. 人物リスト準備
# input_persons.csv:
# person_name,birth_year,person_type
# イチロー,1973,REAL
# HIKAKIN,1989,REAL
# ...

# 2. 情報源収集（API経由）
python scripts/collect_sources.py \
    --input input_persons.csv \
    --sources wikidata,wikipedia \
    --output generated/episode_sources.csv \
    --dry-run

# 3. 根拠検証
python scripts/verify_sources.py \
    --input generated/episode_sources.csv \
    --output generated/verified_sources.csv \
    --dry-run

# 4. エピソード生成
python scripts/curate_episodes.py \
    --input generated/verified_sources.csv \
    --output generated/curated_episodes.csv \
    --dry-run

# 5. 品質ゲート（ドライラン）
python scripts/validate_and_merge.py \
    --input generated/curated_episodes.csv \
    --dry-run

# 6. レポート確認
cat reports/collection_pipeline_*.json

# 7. 問題なければ本番実行
python scripts/validate_and_merge.py \
    --input generated/curated_episodes.csv \
    --execute

# 8. KPI確認
python scripts/scheduled_epup_check.py --daily
```

### トラブルシューティング

| 問題 | 原因 | 対処 |
|------|------|-----|
| **APIレート制限** | Wikidata/Wikipedia API制限 | `--retry-limit 5 --backoff-factor 2` 設定 |
| **重複source_id** | 同一ソースの再インポート | `--skip-duplicates` フラグ使用 |
| **CRITICAL多発** | 生成品質低下 | LLMプロンプト見直し、`--temperature 0.5` 設定 |
| **review_queue肥大化** | 品質C多発 | ソース選定基準見直し、A/B品質優先 |
| **マージ失敗** | person_id重複 | `--force-new-person-id` フラグで新規採番 |

### モニタリング

#### 日次チェックリスト

- [ ] `scheduled_epup_check.py --daily` 実行
- [ ] 根拠品質別割合（A: >30%, B: >50%, C: <20%）
- [ ] 品質ゲート合格率（>80%）
- [ ] review_queue滞留件数（<100件）

#### 週次レビュー

- [ ] `scheduled_epup_check.py --weekly` 実行
- [ ] review_queue手動レビュー（優先度順）
- [ ] rejected_sources.csv分析（却下理由別）
- [ ] API使用量確認（レート制限警告）

---

## 付録

### A. API設定手順

#### Wikidata API

```bash
pip install qwikidata

# テスト
python -c "
from qwikidata.sparql import return_sparql_query_results
query = '''
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5.
  ?item rdfs:label 'イチロー'@ja.
  SERVICE wikibase:label { bd:serviceParam wikibase:language 'ja'. }
}
LIMIT 1
'''
results = return_sparql_query_results(query)
print(results)
"
```

#### Wikipedia API

```bash
pip install wikipedia-api

# テスト
python -c "
import wikipediaapi
wiki = wikipediaapi.Wikipedia('ja')
page = wiki.page('イチロー')
print(page.title)
print(page.summary[:200])
"
```

### B. スキーマ移行SQL

既存MASTER_EPISODES_CURRENT.csvに新列を追加するPandasスクリプト：

```python
import pandas as pd

# 既存CSV読み込み
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')

# 新列追加（デフォルト値）
df['source_url'] = ''
df['verification_status'] = 'unverified'
df['evidence_quality'] = 'C'

# 保存
df.to_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', index=False, encoding='utf-8-sig')
print(f"✅ 新列追加完了: {len(df)}件")
```

### C. 設定ファイル例

#### config/collection_pipeline.yaml

```yaml
# 収集パイプライン設定

data_paths:
  master_csv: "preserved/data/MASTER_EPISODES_CURRENT.csv"
  episode_sources: "generated/episode_sources.csv"
  verified_sources: "generated/verified_sources.csv"
  curated_episodes: "generated/curated_episodes.csv"
  review_queue: "generated/review_queue.csv"
  rejected_sources: "generated/rejected_sources.csv"
  reports_dir: "reports/"

api_config:
  wikidata:
    enabled: true
    retry_limit: 5
    backoff_factor: 2
    timeout: 30
  wikipedia:
    enabled: true
    language: "ja"
    max_text_length: 250

quality_gate:
  min_evidence_quality: "B"  # A or B
  max_fact_check_severity: "medium"  # low, medium, high, critical
  reject_duplicates: true
  reject_blacklist: true

llm_config:
  model: "claude-sonnet-4-5"
  temperature: 0.7
  max_tokens: 500
  retry_limit: 3

validation:
  enable_episode_validator: true
  enable_fact_checker: true
  enable_person_name_validator: true
  enable_duplicate_detection: true

output:
  default_mode: "dry-run"  # dry-run or execute
  backup_on_merge: true
  report_format: "json"  # json or csv
```

---

## まとめ

本設計書では、**量と質を両立**する有名人エピソード収集パイプラインの包括的なアーキテクチャを提示しました。

### 設計の強み

1. **既存資産の完全流用**: episode_validator, fact_checker, PersonNameValidator等を統合
2. **段階的品質評価**: A/B/C品質による根拠信頼性の可視化
3. **冪等性保証**: source_id MD5ハッシュによる重複防止
4. **デフォルトセーフ**: --dry-runによるリスク回避
5. **Phase分割実装**: MVP→自動化→運用改善の段階的展開

### 次のステップ

1. **Phase 1 MVP実装** (2週間)
   - 5つのスクリプト作成（collect, verify, curate, validate, report）
   - データモデル構築
   - テストスイート整備

2. **Phase 2 API統合** (3週間)
   - Wikidata/Wikipedia API実装
   - LLM生成パイプライン構築
   - リトライ・キャッシュ機構実装

3. **Phase 3 運用改善** (2週間)
   - review_queue管理UI構築
   - KPI監視統合
   - ドキュメント整備

---

**作成日**: 2025-12-17
**バージョン**: 1.0
**ステータス**: 設計完了（実装待ち）
