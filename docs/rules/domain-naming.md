# 命名・属性管理ルール

## 🔤 人物名表記ルール（名寄せ統合）

**正規表記（canonical name）を使用すること**

| 別名・通称 | 正規表記 | 理由 |
|-----------|---------|------|
| 山中教授 | 山中伸弥 | 個人名を明示 |
| マンデラ | ネルソン・マンデラ | フルネームで統一 |
| ホリエモン | 堀江貴文 | 本名を使用 |

**ルール**:
- エピソード生成時は**必ず正規表記**を使用
- 別名・通称は`ALIAS_KEYWORDS`に登録済み
- バリデーション: `PersonNameValidator`が自動検出
- 正規化: `normalize_person_names.py`が自動修正

**追加方法**:
新しい別名を発見した場合は以下に追加:
1. `scripts/normalize_person_names.py` - `ALIAS_KEYWORDS`辞書
2. `src/validators/person_name_validator.py` - `_check_alias_usage`メソッド（自動参照）

**検証コマンド**:
```bash
# 人物名バリデーション
python3 -c "
from src.validators.person_name_validator import get_validator
validator = get_validator()
issues = validator.validate('山中教授')
for issue in issues:
    print(f'{issue.severity.value}: {issue.message}')
"
```

### 実装パターン（normalize_person_names.py）

| パターン | 入力例 | 正規化後 | 信頼度 |
|---------|--------|---------|--------|
| **ALIAS** | 山中教授 | 山中伸弥 | 1.0 |
| **DESCRIPTION_PREFIX** | 日本人実業家の稲盛和夫 | 稲盛和夫 | 0.95 |
| **AFFILIATION_TITLE** | 楽天創業者三木谷浩史 | 三木谷浩史 | 0.95 |
| **ORG_PERSON** | 辻調 辻芳樹 | 辻芳樹 | 0.90 |
| **OCCUPATION_PREFIX** | 声優野沢雅子 | 野沢雅子 | 0.90 |
| **GROUP_MEMBER** | 乃木坂46齋藤飛鳥 | 齋藤飛鳥 | 0.95 |
| **GROUP_PREFIX** | AKB48指原莉乃 | 指原莉乃 | 0.95 |
| **RIKISHI_SHIKONA** | 千代の富士貢 | 千代の富士 | 0.90 |
| **ORDINAL_ARTIST** | 十四代酒井田柿右衛門 | 酒井田柿右衛門 | 0.85 |

### 使用方法

**検出のみ（ドライラン）**:
```bash
python scripts/normalize_person_names.py --dry-run
```

**自動修正実行**:
```bash
python scripts/normalize_person_names.py --execute --min-confidence 0.85
```

**特定パターンのみ検出**:
```bash
python scripts/normalize_person_names.py --dry-run --pattern ALIAS
```

**結果の確認**:
- レポート: `reports/name_normalization_dryrun_*.json`
- 自動修正: 信頼度 ≥ 0.85 かつ要レビューフラグなし
- 要確認: 信頼度 < 0.85 または複雑なパターン

**詳細**: `docs/PERSON_NAME_VALIDATION_WORKFLOW.md`（全9パターンの詳細説明）

---

## 🔤 職業接頭辞除去ルール（EPUP）

**人物表示名に職業を含めない**

| 誤り | 正規表記 | 理由 |
|------|---------|------|
| 浮世絵師・歌川国芳 | 歌川国芳 | 職業は不要 |
| 人間国宝・金重陶陽 | 金重陶陽 | 職業は不要 |
| 歌舞伎俳優・中村勘九郎 | 中村勘九郎 | 職業は不要 |
| 作家・三島由紀夫 | 三島由紀夫 | 職業は不要 |
| 俳優・三船敏郎 | 三船敏郎 | 職業は不要 |

### 検出・修正方法

**自動検出**:
```bash
# ドライラン（検出のみ）
python scripts/normalize_person_names.py --dry-run --min-confidence 0.85

# 本番実行（自動修正）
python scripts/normalize_person_names.py --execute --min-confidence 0.85
```

**バリデーション**（エピソード生成時）:
```bash
python3 -c "
from src.validators.person_name_validator import PersonNameValidator
validator = PersonNameValidator()
issues = validator.validate('浮世絵師・歌川国芳')
for issue in issues:
    print(f'{issue.severity.value}: {issue.message}')
"
```

### 対応職業

37種類の職業パターンを検出（`scripts/normalize_person_names.py` の `PROFESSION_KEYWORDS`）:
- 伝統芸能: 落語家、能楽師、歌舞伎俳優
- 美術: 浮世絵師、画家、彫刻家、写真家
- 文学: 作家、小説家、詩人、劇作家
- 音楽: 音楽家、指揮者、ピアニスト、バイオリニスト
- その他: 建築家、映画監督、声優、漫画家、etc.

### チェックリスト（エピソード生成時）

- [ ] 人物名に職業接頭辞（職業・人名）が含まれていないか
- [ ] 新しい職業パターンを発見した場合、`PROFESSION_KEYWORDS` に追加したか
- [ ] `normalize_person_names.py --dry-run` で検証したか
- [ ] バリデーターでエラーが出ないか確認したか

### 再発防止（Phase 8実装済み）

- **予防**: `PersonNameValidator._check_profession_prefix()` で事前検出
- **修正**: `normalize_person_names.py` で自動正規化（信頼度 0.90）
- **監視**: 日次EPUP品質チェック（組織名・肩書き混入率 KPI）
- **テスト**: `tests/test_person_name_normalization.py` で回帰テスト

---

## 🔤 英字別名誤登録防止ルール（EPUP）

**芸名・表記名として正当な英字人物名（YOSHIKI, HIKAKIN等）は維持しつつ、誤った英字別名（"Mackenyu"等）を自動検出・修正する**

### 基本原則

| 種別 | 例 | 扱い |
|------|-----|------|
| **芸名・表記名（英字維持）** | YOSHIKI, HIKAKIN, Ayase, hyde | ✅ 英字のまま維持 |
| **誤った英字別名（修正）** | Mackenyu（新田真剣佑の別名） | ❌ 正規表記に変換 |

### 芸名 vs 別名の判別基準

#### ✅ 芸名・表記名（維持）

| 判定基準 | 例 | 理由 |
|---------|-----|------|
| KEEP_ENGLISH_NAMESリスト登録 | YOSHIKI, HIKAKIN, hyde | 公式芸名として登録済み |
| GROUP_MEMBER_MAP登録 | Ayase（YOASOBI） | グループメンバーとして登録済み |
| SOLO_ARTISTS登録 | Ado, Eve, Vaundy | ソロアーティストとして登録済み |
| オフィシャル英字表記 | ONE OK ROCK, X JAPAN | 公式英字バンド名 |

#### ❌ 誤った英字別名（修正）

| 判定基準 | 例 | 理由 |
|---------|-----|------|
| 日本人俳優・実業家の英字別名 | Mackenyu（新田真剣佑） | 芸名ではなく別名表記 |
| KEEP_ENGLISH_NAMESに未登録 | 上記に該当しない英字表記 | 公式芸名として認識されていない |
| エピソード本文に日本語名混在 | 父・真田広之と共演 | 日本語名が正規表記 |

### 検出ツール

#### 事前チェック（エピソード生成時）

```bash
# PersonNameValidator を使用
python3 -c "
from src.validators.person_name_validator import get_validator
validator = get_validator()
issues = validator.validate('Mackenyu')
for issue in issues:
    print(f'{issue.severity.value}: {issue.message}')
"
# 出力: warning: 別名「Mackenyu」が使用されています
# 推奨: 正規表記「新田真剣佑」を使用してください
```

#### 事後検出（バッチ検出）

```bash
# detect_english_names.py を使用
python scripts/detect_english_names.py

# 出力:
# - to_translate.csv: 日本語化対象（西洋人名・日本人ローマ字表記）
# - keep_english.csv: 英語名維持対象（芸名）
# - review_required.csv: レビュー必要（要確認）
```

### 修正方法

#### 1. ALIAS_KEYWORDSに登録

新しい別名を発見した場合：

**ファイル**: `scripts/normalize_person_names.py`

```python
ALIAS_KEYWORDS = {
    "山中教授": "山中伸弥",
    "マンデラ": "ネルソン・マンデラ",
    "ホリエモン": "堀江貴文",
    "Mackenyu": "新田真剣佑",  # 例
    # 今後発見された別名をここに追加
}
```

#### 2. 自動修正実行

```bash
# ドライラン（検出のみ）
python scripts/normalize_person_names.py --dry-run --pattern ALIAS

# 本番実行（自動修正）
python scripts/normalize_person_names.py --execute --pattern ALIAS
```

#### 3. 日次KPIで確認

```bash
# 英字別名検出率を確認（KPI追加後）
python scripts/scheduled_epup_check.py --daily
```

### 運用フロー

#### 新しい英字人物名を発見した場合

1. **芸名か別名かを判定**
   - 公式サイト・Wikipediaで確認
   - オフィシャルな英字表記か？

2. **芸名の場合**
   ```bash
   # KEEP_ENGLISH_NAMESに追加
   # ファイル: scripts/detect_english_names.py
   # extract_keep_english_names() の additional_keep に追加
   ```

3. **別名の場合**
   ```bash
   # ALIAS_KEYWORDSに登録
   # ファイル: scripts/normalize_person_names.py
   ALIAS_KEYWORDS["英字別名"] = "正規表記"
   ```

4. **修正実行**
   ```bash
   python scripts/normalize_person_names.py --execute --pattern ALIAS
   ```

5. **日次チェックで確認**
   ```bash
   python scripts/scheduled_epup_check.py --daily
   ```

### チェックリスト（エピソード生成時）

- [ ] 人物名が英字表記の場合、KEEP_ENGLISH_NAMESリストに登録されているか確認
- [ ] 未登録の場合、芸名か別名かを判定（公式サイト・Wikipedia確認）
- [ ] 別名の場合、ALIAS_KEYWORDSに登録したか
- [ ] `normalize_person_names.py --pattern ALIAS` で自動修正を実行したか

### 再発防止

**定期実行（推奨）**:
- 日次: `scheduled_epup_check.py --daily`（英字別名検出率を自動監視）
- 週次: `detect_english_names.py`（全英字人物名をレビュー）

**検出・修正フロー**:
1. 日次KPIで英字別名検出 → アラート発生
2. `detect_english_names.py` で review_required.csv 生成
3. レビューして芸名 or 別名を判定
4. 芸名なら KEEP_ENGLISH_NAMES 追加、別名なら ALIAS_KEYWORDS 追加
5. `normalize_person_names.py --execute` で一括修正
6. 日次KPIで修正完了を確認

---

## 🔗 グループ所属情報不整合検出ルール（EPUP）

**同一person_idでgroup_name/is_group_memberが不整合なエピソードを自動検出・修正する**

### 検出パターン

| パターン | 例 | 問題 |
|---------|-----|------|
| **group_name不整合** | 同一person_idで一部"YOASOBI"、一部"未登録" | ❌ グループ名が統一されていない |
| **is_group_member不整合** | 同一person_idで一部True、一部False | ❌ 所属フラグが統一されていない |
| **GROUP_MEMBER_MAP未反映** | MAPに登録済みなのにCSVに未反映 | ❌ マスター情報が同期されていない |

### 具体例（過去の誤り）

| person_id | person_name | 問題 | 修正前 | 修正後 |
|-----------|-------------|------|--------|--------|
| PC40E5B3 | 幾田りら | 一部エピソードのみgroup_name設定 | 1件="YOASOBI", 4件="未登録" | 全5件="YOASOBI" |
| P6E7E522 | 妹島和世 | is_group_memberが不統一 | 一部True、一部False | 全件True（SANAA所属） |

### 検出ツール

**日次自動チェック**:
```bash
# scheduled_epup_check.py の日次チェックで自動検出
python scripts/scheduled_epup_check.py --daily
```
- KPI「所属情報不整合率」で自動検出（target: 0%、WARNING: 0.5%超、CRITICAL: 1%超）
- レポート出力: `reports/epup_daily_YYYYMMDD_HHMMSS.json`

**詳細レポート生成**:
```bash
# 不整合の詳細一覧を出力
python3 << 'EOF'
import pandas as pd
from collections import defaultdict
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')
inconsistent = []
id_to_info = defaultdict(lambda: {"group_names": set(), "is_members": set()})
for _, row in df.iterrows():
    if pd.notna(row["person_id"]):
        person_id = str(row["person_id"])
        group_name = str(row["group_name"]) if pd.notna(row["group_name"]) else "未登録"
        is_member = str(row["is_group_member"]) if pd.notna(row["is_group_member"]) else "False"
        id_to_info[person_id]["group_names"].add(group_name)
        id_to_info[person_id]["is_members"].add(is_member)
for person_id, info in id_to_info.items():
    if len(info["group_names"]) > 1 or len(info["is_members"]) > 1:
        person_name = df[df["person_id"] == person_id]["person_name"].iloc[0]
        print(f'{person_id}: {person_name} - groups={list(info["group_names"])}, members={list(info["is_members"])}')
EOF
```

### 修正方法

**自動同期（推奨）**:
```bash
# ドライラン（変更内容確認）
python scripts/sync_group_from_master.py

# 本番実行（GROUP_MEMBER_MAPから一括同期）
python scripts/sync_group_from_master.py --execute
```
- GROUP_MEMBER_MAP（`src/group_master.py`）に基づき自動修正
- バックアップ自動作成
- 修正レポート出力: `reports/group_sync_YYYYMMDD_HHMMSS.json`

**マスター管理**:
新しい人物のグループ所属を登録する場合：
1. `src/group_master.py` の `GROUP_MEMBER_MAP` に追加
   ```python
   GROUP_MEMBER_MAP: Dict[str, str] = {
       "幾田りら": "YOASOBI",  # 例
       # ...
   }
   ```
2. `sync_group_from_master.py --execute` で全エピソードに反映

### チェックリスト（エピソード生成・インポート時）

- [ ] 新しい人物がグループ所属の場合、GROUP_MEMBER_MAPに登録したか
- [ ] 生成後に `sync_group_from_master.py` を実行したか
- [ ] 日次KPIで「所属情報不整合率」が0%になっているか確認したか
- [ ] GROUP_MEMBER_MAPとCSVの同期が取れているか

### 再発防止（運用定着）

**定期実行（推奨）**:
- 日次: `scheduled_epup_check.py --daily`（自動検出）
- 週次: `sync_group_from_master.py --execute`（予防的同期）

**検出・修正フロー**:
1. 日次KPIで不整合検出 → アラート発生
2. 詳細レポート生成で対象person_id特定
3. GROUP_MEMBER_MAPに未登録なら追加
4. `sync_group_from_master.py --execute` で一括修正
5. 日次KPIで修正完了を確認（不整合率=0%）
