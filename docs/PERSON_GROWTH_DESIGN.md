# PERSON成長パイプライン設計書

## 📋 概要

エピソードDBに未収録PERSONを継続的に追加し、PERSON総数を増やす恒久運用できる仕組み。

**目的**: PERSON追加 = 最低1本のエピソード追加

**ゴール**: 1コマンドで候補収集→正規化/検証→未収録判定→追加（生成+統合）→品質チェック→レポートが完結

---

## 🔄 既存機構の流用マップ（二重実装禁止）

| 処理ステップ | 既存機構 | 流用方法 |
|-------------|---------|---------|
| **人物名バリデーション** | `src/validators/person_name_validator.py` | `PersonNameValidator.validate()` を直接呼び出し |
| **人物名正規化** | `scripts/normalize_person_names.py` | `PersonNameNormalizer.normalize()` を流用 |
| **重複統合** | `scripts/merge_duplicate_persons.py` | `normalize_name()`, `remove_honorifics()`, 類似度計算を流用 |
| **別名統合** | `scripts/merge_person_aliases.py` | 別名辞書・類似判定ロジックを流用 |
| **エピソード検証** | `scripts/episode_validator.py` | 統合後に `--master` モードで実行 |
| **品質チェック** | `episode_quality_system/template_blocker.py` | テンプレート検出・ブロック |
| **ハルシネーション検出** | `src/fact_checker.py` | ファクトチェックAPI呼び出し |
| **EPUP品質監視** | `scripts/scheduled_epup_check.py` | 統合後KPI確認 |
| **自動監視** | `scripts/epup_auto_watch.py` | 定期実行の参考設計 |
| **有名人インポート** | `scripts/import_from_yumeilist.py` | 名寄せ、ギャップ分析、プレースホルダー検出を流用 |
| **グループ情報補完** | `src/group_master.py` | `GROUP_MEMBER_MAP`, `SOLO_ARTISTS` を参照 |
| **グループ同期** | `scripts/sync_group_from_master.py` | グループ情報の自動補完 |

---

## 🏗️ アーキテクチャ

### 処理フロー（6ステップ）

```
[1. 候補収集] → [2. 正規化/検証] → [3. 未収録判定] → [4. エピソード生成+統合] → [5. 追加後検証] → [6. レポート]
     ↓              ↓                  ↓                  ↓                      ↓              ↓
  複数ソース      名寄せ・         既存DBとの        品質ゲート付き        CRITICAL        JSON/CSV
  から収集        バリデー         強い名寄せ        エピソード生成        エラー判定      集計レポート
                  ション
```

### 1. 候補収集（Candidate Collection）

**入力**:
- `config/person_sources/*.csv`（複数ソース）
  - yumeilist.csv
  - manual_list.csv
  - nhk_asadora_models.csv
  - racehorse_list.csv
  - crime_educational.csv（要明示フラグ）

**共通スキーマ**:
```csv
person_name,category,sub_category,person_type,description,birth_year,death_year,tier,source_name,source_url,status
```

**処理**:
1. 各ソースCSVを読み込み
2. 共通スキーマに変換
3. プレースホルダー検出（`is_placeholder()`を流用）
4. カテゴリマッピング（`config/category_taxonomy.json`参照）

**流用**:
- `import_from_yumeilist.py` の `is_placeholder()`, `normalize_name()`

---

### 2. 正規化/検証（Normalization & Validation）

**処理**:
1. **人物名正規化**
   - `PersonNameNormalizer.normalize()`（`scripts/normalize_person_names.py`）
   - 肩書除去、所属除去、力士四股名正規化

2. **人物名バリデーション**
   - `PersonNameValidator.validate()`（`src/validators/person_name_validator.py`）
   - ERRORが出る候補は自動投入しない
   - WARNINGは要レビューリストに追加

3. **グループ情報補完**
   - `GROUP_MEMBER_MAP`（`src/group_master.py`）から `group_name`, `is_group_member` を自動補完

**出力**:
- 正規化済み候補リスト
- スキップリスト（理由：`invalid_name`, `blacklist`, `auto_fix_failed`）

**流用**:
- `src/validators/person_name_validator.py`
- `scripts/normalize_person_names.py`
- `src/group_master.py`

---

### 3. 未収録判定（Deduplication & Gap Analysis）

**処理**:
1. **既存DB読み込み**
   - `preserved/data/MASTER_EPISODES_CURRENT.csv`
   - ユニークな `person_name` リスト抽出

2. **強い名寄せ**（3段階）
   - **Lv1: 完全一致** - `person_name == candidate_name`
   - **Lv2: 正規化一致** - `normalize_name(person_name) == normalize_name(candidate_name)`
   - **Lv3: 類似一致** - `SequenceMatcher.ratio() >= 0.85`（`merge_duplicate_persons.py`の閾値）

3. **別名辞書チェック**
   - `merge_person_aliases.py`の別名辞書を参照
   - 既知の別名ならスキップ

**出力**:
- 未収録候補リスト（`missing_persons`）
- スキップリスト（理由：`db_hit`, `alias_hit`, `duplicate_suspect`）

**流用**:
- `scripts/merge_duplicate_persons.py` の `normalize_name()`, `SequenceMatcher`
- `scripts/merge_person_aliases.py` の別名辞書
- `import_from_yumeilist.py` の `find_in_db()`

---

### 4. エピソード生成+統合（Episode Generation & Integration）

**処理**:
1. **エピソード生成**
   - 既存の生成パイプラインを流用
   - `scripts/generate_episodes_by_age_range.py`（Phase 5-2で作成済み）
   - 年齢範囲は候補の `birth_year`, `death_year` から自動計算

2. **品質ゲート**
   - `PersonNameValidator`で再検証
   - `template_blocker.py`でテンプレート検出
   - `fact_checker.py`でハルシネーション検出

3. **統合**
   - バックアップ作成（`MASTER_EPISODES_CURRENT.csv.bak_YYYYMMDD_HHMMSS`）
   - 新規エピソードを追加（`pd.concat()`）
   - episode_id, person_id を生成

**出力**:
- 更新後のマスターCSV（dry-runの場合は書き込まない）
- 追加エピソードのリスト

**流用**:
- `scripts/generate_episodes_by_age_range.py`
- `episode_quality_system/template_blocker.py`
- `src/fact_checker.py`

---

### 5. 追加後検証（Post-Addition Validation）

**処理**:
1. **エピソード検証**
   - `scripts/episode_validator.py --master`を実行
   - CRITICALエラーが出たら統合をロールバック

2. **EPUP品質チェック**
   - `scripts/scheduled_epup_check.py --daily`を実行
   - KPI悪化がないか確認

3. **重複最終チェック**
   - `scripts/merge_duplicate_persons.py --detect-only`を実行
   - 重複疑いがあればレポートに追加

**出力**:
- 検証結果（pass/fail）
- CRITICALエラーがある場合はロールバック

**流用**:
- `scripts/episode_validator.py`
- `scripts/scheduled_epup_check.py`
- `scripts/merge_duplicate_persons.py`

---

### 6. レポート生成（Reporting）

**出力形式**:
- JSON: `reports/person_growth_YYYYMMDD_HHMMSS.json`
- CSV: `reports/person_growth_YYYYMMDD_HHMMSS_changes.csv`

**レポート内容**:
```json
{
  "timestamp": "2025-12-16T20:00:00",
  "mode": "dry-run / execute",
  "summary": {
    "total_candidates": 500,
    "added": 30,
    "skipped": 470
  },
  "skip_reasons": {
    "db_hit": 300,
    "duplicate_suspect": 50,
    "invalid_name": 40,
    "blacklist": 20,
    "placeholder": 60
  },
  "category_breakdown": {
    "音楽": 10,
    "スポーツ": 8,
    "科学・技術": 5,
    "競走馬": 7
  },
  "added_persons": [
    {"person_name": "ナリタブライアン", "category": "競走馬", "episode_count": 1},
    ...
  ],
  "review_required": [
    {"person_name": "○○", "reason": "VALIDATION_WARNING"},
    ...
  ],
  "validation_results": {
    "episode_validator": "PASS",
    "epup_check": "PASS",
    "duplicate_check": "PASS"
  }
}
```

---

## 🛡️ 安全ガード（非人間/犯罪者）

### 競走馬（非人間エンティティ）

**person_type**: `REAL`（既存互換）

**カテゴリ**: `競走馬`（新規カテゴリ）

**年齢範囲の調整**:
- 競走馬は3歳/4歳が重要
- 既存の生成パイプラインは年齢下限5歳
- **対策**: カテゴリが`競走馬`の場合、min_age=3を許容する特例を追加

**実装**:
```python
if candidate['category'] == '競走馬':
    min_age = 3  # 競走馬特例
else:
    min_age = 5  # デフォルト
```

---

### 犯罪者（教訓目的）

**追加条件**:
- `--allow-sensitive` フラグが必須（デフォルトOFF）
- `config/person_sources/crime_educational.csv`から読み込み

**禁止事項**（自動スキップ）:
1. 未成年事件（加害者・被害者とも）
2. 個人情報漏洩リスク
3. 残虐詳細・模倣リスクのある手口説明
4. 裁判係属中

**ブラックリスト**:
- `src/validators/person_name_validator.py`の`BLACKLIST_NAMES`に登録
- バリデーション時に自動スキップ

**レビューフロー**:
1. 犯罪者候補は自動投入しない
2. 必ず`review_required`リストに追加
3. 人間がレビュー後、手動で承認

**実装**:
```python
if candidate['source_name'] == 'crime_educational':
    if not args.allow_sensitive:
        skip('sensitive_content_disabled')
    elif is_blacklisted(candidate['person_name']):
        skip('blacklist')
    else:
        # 自動投入せず、要レビューに追加
        review_required.append(candidate)
```

---

## 💾 データ構造

### 候補ソースCSV（共通スキーマ）

**必須列**:
```csv
person_name,category,person_type,birth_year
```

**推奨列**:
```csv
sub_category,description,death_year,tier,source_name,source_url,status
```

**例**:
```csv
person_name,category,sub_category,person_type,description,birth_year,death_year,tier,source_name,source_url,status
ナリタブライアン,競走馬,クラシック三冠,REAL,1990年代最強馬,1991,1998,S+,manual_list,,active
桜井和寿,音楽,J-POP,REAL,Mr.Children ボーカル,1970,,S,manual_list,,active
```

---

### カテゴリ分類（`config/category_taxonomy.json`）

```json
{
  "categories": [
    "音楽", "スポーツ", "芸術・文化", "科学・技術", "政治・社会",
    "ビジネス", "エンターテイメント", "映画・演劇", "文学",
    "医学・健康", "学術・研究", "競走馬", "動物", "歴史人物"
  ],
  "mappings": {
    "J-POP": "音楽",
    "競馬": "競走馬",
    "クラシック三冠": "競走馬"
  }
}
```

---

## 🔧 CLI インターフェース

### 基本コマンド

```bash
# 分析のみ（CSV書き込みなし）
python scripts/person_growth_pipeline.py --analyze

# dry-run（変更プレビュー）
python scripts/person_growth_pipeline.py --sources yumeilist,manual_list --limit 50

# 本番実行
python scripts/person_growth_pipeline.py --sources yumeilist,manual_list --limit 50 --execute

# 競走馬・犯罪者を含む実行
python scripts/person_growth_pipeline.py --sources racehorse_list,crime_educational --allow-sensitive --execute
```

### 引数

| 引数 | 説明 | デフォルト |
|------|------|-----------|
| `--analyze` | 候補差分と統計のみ出力 | False |
| `--sources` | ソース指定（カンマ区切り） | all |
| `--limit` | 追加PERSON上限 | 無制限 |
| `--execute` | 実行フラグ | False（dry-run） |
| `--allow-sensitive` | 犯罪者追加を許可 | False |
| `--output` | レポート出力先 | `reports/person_growth_YYYYMMDD_HHMMSS.json` |
| `--csv` | マスターCSVパス | `preserved/data/MASTER_EPISODES_CURRENT.csv` |
| `--threshold` | 類似度閾値 | 0.85 |

---

## 🔄 冪等性の保証

### 重複防止の3層防御

1. **候補収集時**: プレースホルダー除外
2. **未収録判定時**: 強い名寄せ（完全一致・正規化一致・類似一致）
3. **統合後**: `merge_duplicate_persons.py --detect-only`で最終確認

### 同じ入力での再実行

```bash
# 1回目: 30人追加
python scripts/person_growth_pipeline.py --sources manual_list --limit 30 --execute
# Added: 30 persons

# 2回目: 同じコマンド
python scripts/person_growth_pipeline.py --sources manual_list --limit 30 --execute
# Added: 0 persons (All candidates already exist in DB)
```

**理由**: 未収録判定で既存DBと照合するため、同じ人物は追加されない。

---

## 📊 永続運用

### 定期実行（推奨）

```bash
# 毎週日曜日に自動実行（dry-run）
0 3 * * 0 cd /path/to/project && python scripts/person_growth_pipeline.py --sources yumeilist --limit 50 >> logs/person_growth.log 2>&1
```

### 上限設定

**全体上限**: `--limit`で指定

**カテゴリ別上限**（実装予定）:
```python
CATEGORY_LIMITS = {
    "音楽": 10,
    "スポーツ": 10,
    "競走馬": 5,
    "その他": 25
}
```

### 暴走防止

- デフォルトは dry-run（`--execute`が必須）
- バックアップ自動作成
- CRITICALエラー時は自動ロールバック
- 実行ログ・レポートを必ず残す

---

## 📝 実装ファイル

### 新規作成

| ファイル | 役割 |
|---------|------|
| `scripts/person_growth_pipeline.py` | メインパイプライン |
| `config/person_sources/manual_list.csv` | 手動候補リスト |
| `config/person_sources/nhk_asadora_models.csv` | 朝ドラモデル人物 |
| `config/person_sources/racehorse_list.csv` | 競走馬リスト |
| `config/person_sources/crime_educational.csv` | 犯罪者（教訓目的） |
| `config/category_taxonomy.json` | カテゴリ分類 |
| `docs/PERSON_GROWTH_GUIDE.md` | 運用ガイド |

### 既存流用（変更なし）

| ファイル | 流用内容 |
|---------|---------|
| `src/validators/person_name_validator.py` | バリデーション |
| `scripts/normalize_person_names.py` | 正規化 |
| `scripts/merge_duplicate_persons.py` | 重複検出 |
| `scripts/merge_person_aliases.py` | 別名統合 |
| `scripts/episode_validator.py` | エピソード検証 |
| `scripts/scheduled_epup_check.py` | EPUP品質監視 |
| `scripts/generate_episodes_by_age_range.py` | エピソード生成 |
| `episode_quality_system/template_blocker.py` | テンプレート検出 |
| `src/fact_checker.py` | ハルシネーション検出 |
| `src/group_master.py` | グループ情報 |

---

## ✅ 実装チェックリスト

- [ ] 既存機構の流用マップ完成
- [ ] person_growth_pipeline.py の骨格実装
- [ ] 候補ソース受け皿（config/person_sources/*.csv）作成
- [ ] 共通スキーマ定義
- [ ] カテゴリ分類JSON作成
- [ ] 6ステップの処理フロー実装
- [ ] 安全ガード（競走馬・犯罪者）実装
- [ ] dry-run / execute モード実装
- [ ] レポート生成実装
- [ ] 冪等性テスト
- [ ] 運用ガイド作成
- [ ] Git コミット

---

**設計完了日**: 2025-12-16
**設計者**: Claude Sonnet 4.5
