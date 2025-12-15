# 人物名バリデーションワークフロー完全ガイド

## 目次

1. [概要](#概要)
2. [PersonNameValidator API リファレンス](#personnamevalidator-api-リファレンス)
3. [normalize_person_names.py 全パターン詳細](#normalize_person_namespy-全パターン詳細)
4. [ALIAS_KEYWORDS 拡張手順](#alias_keywords-拡張手順)
5. [エピソード生成時の統合フロー](#エピソード生成時の統合フロー)
6. [トラブルシューティング](#トラブルシューティング)

## 概要

人物名バリデーションシステムは、誤った人物名（別名・通称・組織名混入など）を検出・修正する機構です。

### アーキテクチャ

```text
エピソード生成
    ↓
PersonNameValidator（生成前チェック）
    ↓
normalize_person_names.py（生成後の一括修正）
    ↓
merge_normalized_duplicates.py（person_id統合）
```

### 主要コンポーネント

| コンポーネント | 役割 | 実行タイミング |
|-------------|------|-------------|
| **PersonNameValidator** | 人物名の事前チェック | エピソード生成前 |
| **normalize_person_names.py** | 一括正規化処理 | 定期実行（週次/月次） |
| **ALIAS_KEYWORDS** | 別名→正規表記マッピング | 随時更新 |
| **merge_normalized_duplicates.py** | person_id統合 | 正規化後 |

## PersonNameValidator API リファレンス

### validate(person_name: str) → list[ValidationIssue]

**用途**: 単一の人物名をバリデーション

**検出される問題タイプ**:

- `GROUP_AS_PERSON`: グループ名が人物名として登録
- `CONCATENATED_NAME`: グループ名＋個人名の連結
- `ORG_TITLE_CONTAMINATION`: 組織名・肩書き混入
- `VARIANT_NAME`: 別名・通称の使用

**使用例**:

```python
from src.validators.person_name_validator import get_validator

validator = get_validator()
issues = validator.validate("山中教授")

for issue in issues:
    print(f"{issue.severity.value}: {issue.message}")
    if issue.auto_fixable:
        print(f"  修正案: {issue.fixed_value}")
```

**戻り値**: `ValidationIssue` のリスト

```python
@dataclass
class ValidationIssue:
    issue_type: IssueType
    severity: Severity  # ERROR, WARNING, INFO
    person_name: str
    message: str
    suggestion: Optional[str]
    auto_fixable: bool
    fixed_value: Optional[str]
```

### validate_batch(person_names: list[str]) → dict

**用途**: 複数の人物名を一括バリデーション

**戻り値**:

```python
{
    "total": 検証数,
    "valid": 問題なし数,
    "invalid": 問題あり数,
    "issues": 問題リスト,
    "auto_fixable": 自動修正可能数,
}
```

**使用例**:

```python
import pandas as pd
from src.validators.person_name_validator import get_validator

df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')
validator = get_validator()

results = validator.validate_batch(df['person_name'].dropna().unique())
print(f"総数: {results['total']}")
print(f"問題あり: {results['invalid']}")
print(f"自動修正可能: {results['auto_fixable']}")
```

### auto_fix(person_name: str) → tuple[str, Optional[ValidationIssue]]

**用途**: 人物名を自動修正

**戻り値**: `(修正後の名前, 修正した問題)` のタプル

**使用例**:

```python
validator = get_validator()
fixed_name, issue = validator.auto_fix("山中教授")

if issue:
    print(f"修正: {issue.person_name} → {fixed_name}")
else:
    print("修正不要")
```

### validate_before_episode_generation(person_name, person_type, group_name) → tuple[bool, str, Optional[dict]]

**用途**: エピソード生成前の簡易チェック

**戻り値**: `(is_valid, message, suggested_fix)`

**使用例**:

```python
from src.validators.person_name_validator import validate_before_episode_generation

is_valid, message, suggested_fix = validate_before_episode_generation(
    person_name="山中教授",
    person_type="REAL",
    group_name=None
)

if not is_valid:
    print(f"❌ {message}")
    if suggested_fix:
        person_name = suggested_fix["person_name"]
        print(f"✅ 修正: {person_name}")
```

## normalize_person_names.py 全パターン詳細

### 1. ALIAS（別名・通称）

**実装場所**: L1253-1276 `_match_alias()`

**検出例**:

- 「山中教授」 → 「山中伸弥」
- 「ホリエモン」 → 「堀江貴文」
- 「マンデラ」 → 「ネルソン・マンデラ」

**信頼度**: 1.0（完全一致）

**拡張方法**:

```python
# scripts/normalize_person_names.py L199-204
ALIAS_KEYWORDS = {
    "山中教授": "山中伸弥",
    "マンデラ": "ネルソン・マンデラ",
    "ホリエモン": "堀江貴文",
    # ここに新しい別名を追加
}
```

### 2. DESCRIPTION_PREFIX（説明文プレフィックス）

**実装場所**: L689-705 `_match_description_prefix()`

**検出例**:

- 「日本人実業家の稲盛和夫」 → 「稲盛和夫」
- 「アメリカの俳優トム・クルーズ」 → 「トム・クルーズ」
- 「ノーベル賞受賞者山中伸弥」 → 「山中伸弥」

**パターン**:

```python
DESCRIPTION_PATTERNS = [
    r"^日本人[実業家|俳優|作家|...]の(.+)$",
    r"^アメリカの[俳優|歌手|...](.+)$",
    r"^ノーベル賞受賞者(.+)$",
]
```

**信頼度**: 0.95

### 3. AFFILIATION_TITLE（会社・所属＋肩書き）

**実装場所**: L707-793 `_match_affiliation_title()`

**検出例**:

- 「楽天創業者三木谷浩史」 → 「三木谷浩史」
- 「ソニー元会長出井伸之」 → 「出井伸之」
- 「維新松井一郎」 → 「松井一郎」

**パターン**:

```python
AFFILIATION_TITLE_PATTERNS = [
    (r"^([\u4E00-\u9FFF]+)(創業者|CEO|会長|社長)(.+)$", 1, 3),
    (r"^([\u4E00-\u9FFF]{2,4})(元)?会長(.+)$", 1, 3),
]
```

**信頼度**: 0.95

### 4. ORG_PERSON（組織名＋人物名）

**実装場所**: L795-829 `_match_org_person()`

**検出例**:

- 「辻調 辻芳樹」 → 「辻芳樹」
- 「東大 養老孟司」 → 「養老孟司」

**パターン**: `^([^\s]+)\s+(.+)$` （組織名と人物名の間にスペース）

**信頼度**: 0.90

### 5. OCCUPATION_PREFIX（職業プレフィックス）

**実装場所**: L831-900 `_match_occupation_prefix()`

**検出例**:

- 「声優野沢雅子」 → 「野沢雅子」
- 「お笑い・とんねるず石橋貴明」 → 「石橋貴明」
- 「歌手宇多田ヒカル」 → 「宇多田ヒカル」

**パターン**:

```python
OCCUPATION_PATTERNS = [
    r"^声優(.+)$",
    r"^お笑い[・・](.*?)(.+)$",
    r"^歌手(.+)$",
]
```

**信頼度**: 0.90

### 6-7. GROUP_MEMBER / GROUP_PREFIX（グループ名混入）

**実装場所**: L1061-1228 `_match_group_patterns()`

**検出例**:

- 「乃木坂46齋藤飛鳥」 → 「齋藤飛鳥」
- 「AKB48指原莉乃」 → 「指原莉乃」
- 「欅坂46平手友梨奈」 → 「平手友梨奈」

**パターン**: 7種類のグループ名検出ロジック

**信頼度**: 0.95

### 8. RIKISHI_SHIKONA（力士本名混入）

**実装場所**: L963-1014 `_match_rikishi_shikona()`

**検出例**:

- 「千代の富士貢」 → 「千代の富士」
- 「朝青龍明徳」 → 「朝青龍」

**パターン**: 力士の四股名パターン（漢字＋本名）

**信頼度**: 0.90

### 9. ORDINAL_ARTIST（代数表記）

**実装場所**: L1016-1059 `_match_ordinal_artist()`

**検出例**:

- 「十四代酒井田柿右衛門」 → 「酒井田柿右衛門」
- 「五代目坂東玉三郎」 → 「坂東玉三郎」

**パターン**: `^(十?[一二三四五六七八九十]+代目?)(.+)$`

**信頼度**: 0.85

## ALIAS_KEYWORDS 拡張手順

### Step 1: 新しい別名を発見

エピソードDBで不適切な人物名を発見した場合：

```bash
# CSVから特定の人物名を検索
python3 -c "
import pandas as pd
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')
print(df[df['person_name'].str.contains('○○', na=False)][['person_name', 'episode_id']])
"
```

### Step 2: ALIAS_KEYWORDS に追加

**ファイル**: `scripts/normalize_person_names.py` L199-204

```python
ALIAS_KEYWORDS = {
    "山中教授": "山中伸弥",
    "マンデラ": "ネルソン・マンデラ",
    "ホリエモン": "堀江貴文",
    "新しい別名": "正規表記",  # ← 追加
}
```

### Step 3: 動作確認

```bash
# ドライラン
python scripts/normalize_person_names.py --dry-run

# レポート確認
cat reports/name_normalization_dryrun_*.json | jq '.pairs[] | select(.alias == "新しい別名")'
```

### Step 4: 実行

```bash
python scripts/normalize_person_names.py --execute
```

### Step 5: Git コミット

```bash
git add scripts/normalize_person_names.py preserved/data/MASTER_EPISODES_CURRENT.csv
git commit -m "feat: ALIAS_KEYWORDSに「新しい別名」→「正規表記」を追加"
git push origin main
```

## エピソード生成時の統合フロー

### 生成前チェック

```python
from src.validators.person_name_validator import validate_before_episode_generation

# エピソード生成リクエストを受け取った時点で実行
is_valid, message, suggested_fix = validate_before_episode_generation(
    person_name="山中教授",
    person_type="REAL",
    group_name=None
)

if not is_valid:
    print(f"❌ バリデーションエラー: {message}")
    if suggested_fix:
        print(f"✅ 修正案:")
        for key, value in suggested_fix.items():
            print(f"  {key}: {value}")
        # 修正案を使用してエピソード生成
        person_name = suggested_fix["person_name"]
```

### 生成後の一括修正

```bash
# 定期実行（週次または月次）
python scripts/normalize_person_names.py --dry-run --min-confidence 0.85

# レポート確認後、実行
python scripts/normalize_person_names.py --execute --min-confidence 0.85
```

### person_id 統合

```bash
# 正規化後に重複が発生した場合
python scripts/merge_normalized_duplicates.py --dry-run
python scripts/merge_normalized_duplicates.py --execute
```

## トラブルシューティング

### Q1: 誤検出が発生した場合

**問題**: 正しい人物名が誤って修正される

**対処**:

1. `src/validators/person_name_validator.py` の `EXCLUDE_PERSON_NAMES` に追加

   ```python
   EXCLUDE_PERSON_NAMES = {
       "オードリー・ヘプバーン",  # お笑いコンビ「オードリー」と区別
       "正しい人物名",  # ← 追加
   }
   ```

2. 正規化ロジックの調整（該当パターンの信頼度を下げる）

### Q2: 新しいパターンが必要な場合

**問題**: 既存の9パターンでカバーできない新しい誤表記

**対処**:

1. `scripts/normalize_person_names.py` に新しいメソッド追加

   ```python
   def _match_new_pattern(self, name: str) -> Optional[NormalizationResult]:
       """新しいパターンの検出"""
       pattern = r"^新パターン(.+)$"
       match = re.match(pattern, name)
       if match:
           return NormalizationResult(...)
   ```

2. `normalize()` メソッドに統合

### Q3: 信頼度の調整

**問題**: 自動修正される/されないの境界を変更したい

**対処**:

```bash
# 信頼度閾値を調整（デフォルト: 0.85）
python scripts/normalize_person_names.py --execute --min-confidence 0.90
```

### Q4: レポートの読み方

**ファイル**: `reports/name_normalization_dryrun_*.json`

```json
{
  "pairs": [
    {
      "original_name": "山中教授",
      "normalized_name": "山中伸弥",
      "pattern_type": "ALIAS",
      "confidence": 1.0,
      "requires_review": false,
      "affected_episodes": 2
    }
  ]
}
```

**フィールド説明**:

- `confidence`: 信頼度スコア（0.0-1.0）
- `requires_review`: 要レビューフラグ
- `affected_episodes`: 影響するエピソード数

### Q5: エピソード生成時にバリデーションが走らない

**問題**: 誤った人物名でエピソードが生成されてしまう

**対処**:

1. エピソード生成スクリプトに `validate_before_episode_generation()` を追加
2. EPUPの事前チェックリストを確認（`.claude/commands/epup.md`）

---

## 役職語・関係語の許容基準

**追加日**: 2025-12-16

エピソード生成時における役職語・敬称・関係語の使用について、以下の基準に従います。

### 許容（維持してよい）

| パターン | 例 | 理由 |
|---------|-----|------|
| **フルネーム + 役職語** | バーニー・サンダース上院議員 | 個人が特定でき、読みやすさが向上 |
| **フルネーム + 敬称** | 野沢雅子さん | 敬称は一般的に許容される |
| **フルネーム + 学術称号** | 日野原重明博士 | 学術称号は識別に有効 |

### 修正必要

| パターン | 例 | 問題 | 修正案 |
|---------|-----|------|--------|
| **関係語のみで個人不明** | 岸田文雄夫人 | 個人名が不明確 | 岸田裕子 |
| **姓のみ + 役職語** | サンダース上院議員 | 同姓別人と混同のリスク | バーニー・サンダース上院議員 |

### 判断基準

1. **個人が特定できるか**
   - フルネームが含まれている
   - または、エピソード本文に個人名が明記されている

2. **同姓別人と区別できるか**
   - 姓のみ+役職は避ける
   - フルネームで記載する

3. **読みやすさが向上するか**
   - 一般読者が理解しやすい
   - 正確性を損なわない

### 検出ツール

**事前チェック（エピソード生成時）**:

```python
from src.validators.person_name_validator import get_validator

validator = get_validator()
issues = validator.validate("岸田文雄夫人")

for issue in issues:
    print(f"{issue.severity.value}: {issue.message}")
    if issue.suggestion:
        print(f"  推奨: {issue.suggestion}")
```

**事後検出（バッチ検出）**:

```bash
# 全データで役職語・関係語を検出
python scripts/detect_person_name_issues.py --output reports/person_name_issues_YYYYMMDD.json
```

### 修正方法

**1. ALIAS_KEYWORDSに登録**:

新しい別名を発見した場合は `scripts/normalize_person_names.py` に追加：

```python
ALIAS_KEYWORDS = {
    "山中教授": "山中伸弥",
    "マンデラ": "ネルソン・マンデラ",
    "ホリエモン": "堀江貴文",
    "サンダース上院議員": "バーニー・サンダース上院議員",  # 追加例
    "岸田文雄夫人": "岸田裕子",  # 追加例
}
```

**2. 自動修正実行**:

```bash
# ドライラン（検出のみ）
python scripts/normalize_person_names.py --dry-run --pattern ALIAS

# 本番実行（自動修正）
python scripts/normalize_person_names.py --execute --pattern ALIAS
```

### チェックリスト（エピソード生成時）

- [ ] 人物名に役職語・関係語が含まれていないか確認
- [ ] 含まれている場合、フルネームで個人が特定できるか確認
- [ ] 関係語のみ（例: 〇〇夫人）の場合、エピソード本文から個人名を特定
- [ ] ALIAS_KEYWORDSに登録が必要な場合は追加

### PersonNameValidatorの検出ロジック

`src/validators/person_name_validator.py` の `_check_suffix_patterns()` メソッドで以下を検出：

| カテゴリ | 接尾辞 | 重大度 | アクション |
|---------|--------|--------|----------|
| **関係** | 夫人 | ERROR | 本文から個人名を特定して修正 |
| **役職（姓のみ）** | 議員、社長、CEO等 | WARNING | フルネームに変更を推奨 |
| **敬称** | 氏、さん、様等 | INFO | 維持可（確認推奨） |
| **学術** | 博士、教授等 | INFO | 維持可（識別明確であれば） |

---

## 関連ドキュメント

- **CLAUDE.md**: 人物名表記ルール（L116-187）
- **.claude/commands/epup.md**: EPUPワークフロー
- **scripts/normalize_person_names.py**: 正規化エンジン（1440行）
- **src/validators/person_name_validator.py**: バリデーター（500行超）
- **scripts/detect_person_name_issues.py**: 包括的検出エンジン（380行）
- **scripts/merge_person_aliases.py**: 人物名統合スクリプト（430行）
