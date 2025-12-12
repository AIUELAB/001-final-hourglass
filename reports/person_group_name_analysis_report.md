# 人物名・グループ名混在問題 分析レポート

**作成日**: 2025-12-10
**作成者**: データクレンジング担当エンジニア

---

## 1. 問題の要約

### 1.1 発生している問題

人物マスタ（MASTER_EPISODES_CURRENT.csv）において、`person_name`フィールドにグループ名と個人名が混在して登録されているレコードが存在する。

**具体例（P03BE1BC）**:
- 現状の`person_name`: 「水溜りボンド・トミー」
- 期待される形:
  - `person_name`: 「トミー」
  - `group_name`: 「水溜りボンド」
  - `is_group_member`: True

### 1.2 問題の分類

| カテゴリ | 問題点 | 影響度 |
|---------|--------|--------|
| データモデリング | person_nameとgroup_nameの責務が曖昧 | 高 |
| 表示仕様・UI | 一貫性のない名前表示 | 中 |
| EPUPシステム | エピソード生成時の名前の扱いが不統一 | 中 |

---

## 2. 原因候補とその検討

### 2.1 根本原因

1. **テンプレート作成時の入力ミス**
   - 手動でテンプレートCSVを作成する際に、「グループ名・個人名」形式で入力してしまっている

2. **バリデーションの欠如**
   - エピソード生成スクリプト（`generate_episodes_from_template.py`）で、`person_name`フィールドのバリデーションが行われていない
   - グループ名と個人名の分離ロジックがない

3. **グループマスタの不完全さ**
   - 「水溜りボンド」「兄者弟者」などのYouTubeグループがGROUP_ENTITIESに未登録だった

### 2.2 副次的原因

- `llm_group_fill.py`はgroup_nameの補完を行うが、person_nameの正規化は行わない
- EPUPエンジン（`backend/app/services/epup_engine.py`）はエラー検出・修正を自動化するが、名前フォーマットの問題は検出対象外

---

## 3. データ・スキーマ・コードの現状分析

### 3.1 データスキーマ（CSVカラム）

```
person_id, person_name, episode_count, age, category, episode_text,
episode_type, group_name, is_group_member, person_type, ...
```

- `person_name`: 人物の名前（個人名であるべき）
- `group_name`: 所属グループ名
- `is_group_member`: グループメンバーかどうか（True/False/null）

### 3.2 関連ファイル

| ファイル | 役割 |
|----------|------|
| `src/group_master.py` | グループ所属判定モジュール |
| `scripts/generate_episodes_from_template.py` | テンプレートからエピソード生成 |
| `scripts/llm_group_fill.py` | LLMによるグループ情報補完 |
| `src/validators/person_name_validator.py` | 人物名バリデーター |
| `backend/app/services/epup_engine.py` | EPUP自動実行エンジン |

### 3.3 検出された問題パターン

| パターン | 検出件数 | 例 |
|----------|----------|-----|
| スペース区切り（グループ名 個人名） | 3件 | QuizKnock 伊沢拓司 |
| 中点区切り（グループ名・個人名） | 4件 | 水溜りボンド・トミー |

---

## 4. 修正ロジックと実装案

### 4.1 作成した修正スクリプト

**`scripts/fix_person_group_name_contamination.py`**

機能:
- グループ名・個人名混在パターンの自動検出
- 信頼度ベースの修正提案
- オプションでLLMによる曖昧ケース検証
- ドライラン/実行モード切替

使用方法:
```bash
# ドライラン（検出のみ）
python scripts/fix_person_group_name_contamination.py --dry-run

# 実行（修正を適用）
python scripts/fix_person_group_name_contamination.py --execute

# LLM検証付き
python scripts/fix_person_group_name_contamination.py --use-llm --execute
```

### 4.2 バリデーター拡張

**`src/validators/person_name_validator.py`** を拡張:

- `validate_before_episode_generation()`: 生成前検証API
- `get_canonical_info()`: 正規化された人物情報取得
- 除外パターン対応（オードリー・ヘプバーン等）

### 4.3 グループマスタ更新

**`src/group_master.py`** に追加:

```python
# GROUP_MEMBER_MAP
"トミー": "水溜りボンド",
"カンタ": "水溜りボンド",
"兄者": "兄者弟者",
"弟者": "兄者弟者",

# GROUP_ENTITIES
"水溜りボンド",
"兄者弟者",
```

---

## 5. EPUPシステムの評価と改善ポイント

### 5.1 現状の成果

| 指標 | 値 | 評価 |
|------|-----|------|
| 総エピソード数 | 13,335件 | - |
| フォーマット準拠率 | 97.0% | 良好 |
| group_name設定率 | 6.0% | 低い |
| is_group_member設定率 | 29.0% | 改善必要 |
| メタ表現含むエピソード | 34件 | 要修正 |
| composite_score平均 | 602.1 | 良好 |

### 5.2 EPUPの貢献

**うまく機能している点**:
- フォーマット準拠率97%（「あなたと同じN歳のとき」形式）
- 品質スコアの安定した付与
- エピソードタイプの分類（TURNING_POINT, ACHIEVEMENT等）

**構造的な設計ミス・運用ミス**:
- 人物名の正規化がエピソード生成パイプラインに組み込まれていない
- グループマスタのカバレッジが低い（7,271ユニーク人物が未カバー）
- LLM補完が事後処理であり、生成時の検証がない

### 5.3 改善ポイント

1. **生成時バリデーション統合**: `generate_episodes_from_template.py`に`validate_before_episode_generation()`を組み込む
2. **グループマスタ拡充**: YouTubeグループ、VTuberグループのカバレッジ向上
3. **定期クリーンアップ**: `fix_person_group_name_contamination.py`を定期実行

---

## 6. 再発防止策と今後の運用方針

### 6.1 データ登録時のバリデーションルール

```python
# テンプレートCSV読み込み時
for row in template_rows:
    is_valid, message, fix = validate_before_episode_generation(
        row["person_name"],
        row.get("person_type", "REAL"),
        row.get("group_name")
    )
    if not is_valid:
        if fix:
            row["person_name"] = fix["person_name"]
            row["group_name"] = fix.get("group_name", "")
            row["is_group_member"] = fix.get("is_group_member", "")
        else:
            logger.warning(f"スキップ: {row['person_name']} - {message}")
            continue
```

### 6.2 エピソード生成時のチェック

```python
# generate_episode() 内
canonical_info = validator.get_canonical_info(person_name)
if canonical_info["needs_correction"]:
    person_name = canonical_info["canonical_name"]
    group_name = canonical_info["group_name"]
    is_group_member = canonical_info["is_group_member"]
```

### 6.3 定期的なデータクオリティチェック

| チェック項目 | 頻度 | 担当 |
|--------------|------|------|
| グループ名混在検出 | 週次 | `fix_person_group_name_contamination.py --dry-run` |
| GROUP_MEMBER_MAP同期 | 週次 | `sync_group_from_master.py` |
| EPUP評価 | 週次 | `evaluate_epup_effectiveness.py` |

### 6.4 ルールベース＋LLMハイブリッドチェックフロー

```
┌─────────────────┐
│ 人物名入力      │
└────────┬────────┘
         ▼
┌─────────────────┐
│ ルールベース検証│ ← GROUP_ENTITIES / GROUP_MEMBER_MAP
└────────┬────────┘
         │
    ┌────┴────┐
    │ 問題あり │
    └────┬────┘
         ▼
┌─────────────────┐
│ 信頼度判定      │
└────────┬────────┘
         │
    ┌────┴─────────────┐
    │ 信頼度 >= 0.9    │ → 自動修正
    └────┬─────────────┘
         │
    ┌────┴─────────────┐
    │ 0.7 <= 信頼度    │ → LLM検証 → 修正/スキップ
    └────┬─────────────┘
         │
    ┌────┴─────────────┐
    │ 信頼度 < 0.7     │ → 手動レビュー
    └──────────────────┘
```

---

## 7. 結論

### 7.1 EPUPは成果を出しているか？

**評価: 部分的に成果を出している（B評価）**

- **良い点**: フォーマット準拠率97%、品質スコアの安定運用、エピソードタイプ分類
- **課題**: 人物名の正規化が不十分、グループ情報のカバレッジが低い

### 7.2 今後のアクション

1. **即時対応**: `fix_person_group_name_contamination.py --execute` で検出された7件を修正
2. **短期対応**: 生成スクリプトにバリデーション統合
3. **中期対応**: グループマスタの拡充（YouTube、VTuber、K-POP等）
4. **継続対応**: 週次でのデータクオリティチェック自動化

---

## 付録: 検出された問題レコード一覧

| person_name | パターン | 修正案（person_name） | 修正案（group_name） |
|-------------|----------|----------------------|---------------------|
| 水溜りボンド・トミー | 中点区切り | トミー | 水溜りボンド |
| 水溜りボンド カンタ | スペース区切り | カンタ | 水溜りボンド |
| 兄者弟者・兄者 | 中点区切り | 兄者 | 兄者弟者 |
| ビートルズ ジョン・レノン | スペース区切り | ジョン・レノン | ビートルズ |
| 千原兄弟・千原浩史 | 中点区切り | 千原浩史 | 千原兄弟 |
| QuizKnock 伊沢拓司 | スペース区切り | 伊沢拓司 | QuizKnock |
| Fischer's シルクロード | スペース区切り | シルクロード | Fischer's |
