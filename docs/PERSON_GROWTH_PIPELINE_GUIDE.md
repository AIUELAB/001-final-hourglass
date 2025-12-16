# PERSON成長パイプライン使い方ガイド（MVP版）

## 📋 概要

**PERSON成長パイプライン**は、エピソードDB（`preserved/data/MASTER_EPISODES_CURRENT.csv`）に未収録の人物を継続的に追加するための運用システムです。

### MVP版の機能範囲

| 機能 | 実装状況 |
|------|---------|
| 候補収集 | ✅ 実装済み（config/person_sources/*.csv） |
| 正規化/検証 | ✅ 実装済み（PersonNameValidator統合） |
| 未収録判定 | ✅ 実装済み（重複検出ロジック） |
| レポート生成 | ✅ 実装済み（JSON形式） |
| エピソード生成 | ❌ 未実装（今後の拡張） |
| CSV自動更新 | ❌ 未実装（今後の拡張） |

---

## 🚀 クイックスタート

### 基本的な使い方

```bash
# 全ソースを分析（デフォルト）
python scripts/person_growth_pipeline.py --analyze

# 特定ソースのみ分析
python scripts/person_growth_pipeline.py --analyze --sources manual_list

# 件数制限
python scripts/person_growth_pipeline.py --analyze --limit 10

# レポート出力先を指定
python scripts/person_growth_pipeline.py --analyze --output reports/my_analysis.json
```

### 出力例

```
🚀 PERSON成長パイプライン（MVP版）開始
📂 ソースディレクトリ: config/person_sources
📄 マスターCSV: preserved/data/MASTER_EPISODES_CURRENT.csv

【ステップ1】候補収集
✅ 読み込み: manual_list.csv (10件)

【ステップ2】正規化/検証
✅ 正規化完了: 10 人
⚠️  検証エラー: 1 件

【ステップ3】未収録判定
📊 既存DB: 7192 人収録
🆕 未収録: 4 人
✅ 既収録: 6 人

【ステップ4】レポート生成
📄 レポート出力: reports/person_growth/person_growth_analysis_20251216_192935.json

============================================================
📊 PERSON成長パイプライン分析結果（MVP版）
============================================================
📌 候補人物数: 10 人
✅ 既収録: 6 人
🆕 未収録: 4 人 (40.0%)
⚠️  検証エラー: 1 件

📂 未収録人物のカテゴリ内訳:
  - 競走馬: 3人
  - 音楽: 1人

⚠️  検証エラー詳細（上位10件）:
  - YOASOBI: グループ名 'YOASOBI' が人物名として登録されています
============================================================

✅ 分析完了
```

---

## 📁 候補ソースの作成方法

### 1. CSVファイルの配置

候補人物をCSVファイルで用意し、`config/person_sources/` に配置します。

```
config/person_sources/
├── manual_list.csv        # 手動キュレーション
├── nhk_asadora.csv        # NHK朝ドラモデル人物
└── racehorses.csv         # 競走馬
```

### 2. 必須列

| 列名 | 必須 | 説明 | 例 |
|------|------|------|-----|
| `person_name` | ✅ | 人物名 | ナリタブライアン |
| `category` | ✅ | カテゴリ | 競走馬 |
| `person_type` | ✅ | REAL/FICTIONAL | REAL |
| `sub_category` | ⭕ | サブカテゴリ | クラシック三冠 |
| `description` | ⭕ | 説明 | 1990年代最強馬・無敗の三冠馬 |
| `birth_year` | ⭕ | 生年 | 1991 |
| `death_year` | ⭕ | 没年 | 1998 |
| `tier` | ⭕ | 知名度ティア | S+ |
| `source_name` | ⭕ | ソース名 | manual_list |
| `source_url` | ⭕ | 参照URL | （Wikipedia等） |
| `status` | ⭕ | ステータス | active |

### 3. サンプルCSV

```csv
person_name,category,sub_category,person_type,description,birth_year,death_year,tier,source_name,source_url,status
ナリタブライアン,競走馬,クラシック三冠,REAL,1990年代最強馬・無敗の三冠馬,1991,1998,S+,manual_list,,active
桜井和寿,音楽,J-POP,REAL,Mr.Childrenボーカル・シンガーソングライター,1970,,S,manual_list,,active
```

---

## 📊 レポートの読み方

### JSONレポート構造

```json
{
  "timestamp": "2025-12-16T19:29:35.822483",
  "summary": {
    "total_candidates": 10,
    "validation_errors": 1,
    "missing_persons": 4,
    "found_persons": 6,
    "missing_percentage": 40.0
  },
  "missing_persons": [
    {
      "person_name": "ナリタブライアン",
      "category": "競走馬",
      "person_type": "REAL",
      "source_file": "manual_list"
    }
  ],
  "found_persons": [
    {
      "person_name": "桜井和寿",
      "category": "音楽",
      "match_type": "exact",
      "match_confidence": 1.0
    }
  ],
  "validation_errors": [
    {
      "person_name": "YOASOBI",
      "source_file": "manual_list",
      "severity": "error",
      "message": "グループ名 'YOASOBI' が人物名として登録されています",
      "issue_type": "group_as_person"
    }
  ],
  "category_breakdown": {
    "競走馬": 3,
    "音楽": 1
  }
}
```

### 重複判定の種類

| match_type | 説明 | 信頼度 |
|-----------|------|--------|
| `exact` | 完全一致 | 1.0 |
| `normalized` | 正規化後一致（NFKC、小文字化、中点統一） | 0.95 |
| `similar` | 類似度≧0.85（SequenceMatcher） | 0.85-0.99 |

### 検証エラーの種類

| issue_type | 説明 | severity |
|-----------|------|---------|
| `group_as_person` | グループ名が人物名として登録 | error |
| `concatenated_name` | 連結名パターン（"グループ名・個人名"） | warning |
| `invalid_name` | 不正な人物名（道具名等） | error |
| `profession_prefix` | 職業接頭辞混入（"作家・三島由紀夫"） | warning |

---

## 🔧 運用フロー

### 定期実行（推奨）

1. **新しい候補ソースを追加**
   ```bash
   # 例: NHK朝ドラモデル人物を手動でCSV作成
   vim config/person_sources/nhk_asadora.csv
   ```

2. **分析実行**
   ```bash
   python scripts/person_growth_pipeline.py --analyze --sources nhk_asadora
   ```

3. **レポート確認**
   - `reports/person_growth/person_growth_analysis_*.json` を開く
   - `missing_persons` リストを確認
   - `validation_errors` があれば修正

4. **手動でエピソード生成**（MVP版では自動化なし）
   ```bash
   # 未収録人物のリストをテンプレートCSVに変換
   # 既存スクリプトを使用してエピソード生成
   python scripts/generate_episodes_by_age_range.py \
     --template templates/new_persons.csv \
     --output generated/new_episodes.csv \
     --min-age 30 --max-age 39
   ```

5. **マスターCSVにインポート**
   ```bash
   python scripts/import_generated_episodes.py \
     --source generated/new_episodes.csv \
     --master preserved/data/MASTER_EPISODES_CURRENT.csv
   ```

---

## ⚙️ コマンドラインオプション

### 必須オプション

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--analyze` | 分析モードを実行 | `--analyze` |

### オプショナル

| オプション | 説明 | デフォルト | 例 |
|-----------|------|-----------|-----|
| `--sources` | 処理対象ソース名（カンマ区切り） | 全て | `--sources manual_list,nhk_asadora` |
| `--limit` | 候補収集の最大件数 | 無制限 | `--limit 10` |
| `--output` | レポート出力先 | `reports/person_growth/person_growth_analysis_YYYYMMDD_HHMMSS.json` | `--output reports/my_report.json` |

---

## 🔍 トラブルシューティング

### Q1: 候補ソースが見つからない

```
⚠️  ソースCSVが見つかりません: config/person_sources/
```

**対処**:
- `config/person_sources/` ディレクトリが存在するか確認
- `.csv` 拡張子のファイルが配置されているか確認

### Q2: 必須列が不足している

```
❌ 必須列が不足しています: ['person_name', 'category']
```

**対処**:
- CSVファイルに `person_name`, `category`, `person_type` 列が含まれているか確認
- 列名のスペル・大文字小文字を確認

### Q3: マスターCSVが見つからない

```
⚠️  マスターCSVが見つかりません: preserved/data/MASTER_EPISODES_CURRENT.csv
```

**対処**:
- `preserved/data/MASTER_EPISODES_CURRENT.csv` が存在するか確認
- シンボリックリンクが壊れていないか確認
  ```bash
  python scripts/check_single_master.py
  ```

### Q4: 検証エラーが多数発生

```
⚠️  検証エラー: 15 件
```

**対処**:
- レポート内の `validation_errors` を確認
- `group_as_person`: グループ名が混入している場合、メンバー個人名に変更
- `profession_prefix`: 職業接頭辞を削除（例: "作家・三島由紀夫" → "三島由紀夫"）
- `invalid_name`: 道具名・アイテム名が混入している場合、削除

---

## 📚 関連ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| `docs/PERSON_GROWTH_DESIGN.md` | 設計書（処理フロー、再利用マップ、安全ガード） |
| `docs/PERSON_NAME_VALIDATION_WORKFLOW.md` | 人物名バリデーション詳細 |
| `config/category_taxonomy.json` | カテゴリ分類体系 |

---

## 🔮 今後の拡張（MVP版では未実装）

| 機能 | 説明 | 優先度 |
|------|------|--------|
| **エピソード生成統合** | 未収録人物の自動エピソード生成 | 高 |
| **CSV自動更新** | `--execute` フラグで自動インポート | 高 |
| **安全ガード** | 競走馬（min_age=3）、犯罪者（--allow-sensitive） | 中 |
| **カテゴリ制限** | `--categories` でカテゴリフィルタ | 中 |
| **優先度スコアリング** | 知名度ティア・トレンドスコアによる優先順位付け | 低 |
| **定期実行スクリプト** | cron/GitHub Actions統合 | 低 |

---

## 🎯 使い方のベストプラクティス

### ✅ 推奨

- **小規模バッチで実行**: 初回は `--limit 10` で動作確認
- **ソースを分離**: 競走馬、音楽家、俳優など、カテゴリごとに別CSVで管理
- **定期レビュー**: レポートの `validation_errors` を定期的に確認・修正
- **バックアップ**: 新規追加前に必ずマスターCSVをバックアップ

### ❌ 非推奨

- **大量一括追加**: 未検証のまま数百件を一括追加しない
- **グループ名の登録**: グループ名ではなくメンバー個人名を登録
- **道具名の登録**: 「大リーグ養成ギプス」等のアイテム名を登録しない
- **職業接頭辞**: 「作家・三島由紀夫」ではなく「三島由紀夫」を登録

---

## 📞 サポート

問題が発生した場合:
1. レポートファイル（JSON）を確認
2. `validation_errors` の内容を確認
3. 関連ドキュメントを参照
4. GitHubでIssueを作成

---

**更新履歴**:
- 2025-12-16: MVP版リリース（候補収集、正規化/検証、未収録判定、レポート生成）
