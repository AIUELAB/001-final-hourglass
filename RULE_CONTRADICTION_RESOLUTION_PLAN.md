# ルール矛盾解決プラン

## 📊 検出された矛盾の概要

**総矛盾数**: 7件
- **HIGH重大度**: 4件
- **MEDIUM重大度**: 3件

---

## 🔴 HIGH優先度の矛盾

### 1. 文字数範囲の矛盾（3件）

#### 矛盾の詳細
| ルールID | 文字数範囲 | 更新日 | 優先度 |
|---------|-----------|--------|--------|
| FORMAT_001 | 180-250文字 | 不明 | HIGH |
| RULE_151 | 132-250文字 | 2025-09-22 | MEDIUM |
| RULE_160 | 132-250文字 | 2025-09-22 | MEDIUM |

#### 問題点
- FORMAT_001が最小180文字を要求
- RULE_151とRULE_160は2025-09-22に最小値を150→132に緩和
- **3つの異なる最小値基準が存在**: 180, 150, 132

#### 推奨解決策
**オプションA: RULE_151/160を優先（緩和基準）**
```python
# 統一基準: 132-250文字
MIN_LENGTH = 132  # 2025-09-22更新
MAX_LENGTH = 250
```

**理由**:
- RULE_151/160は明示的に「2025-09-22更新」と記載されており最新
- 150→132への緩和は意図的な設計変更と推定
- より多くのエピソードが基準を満たせる（柔軟性）

**オプションB: FORMAT_001を優先（厳格基準）**
```python
# 統一基準: 180-250文字
MIN_LENGTH = 180
MAX_LENGTH = 250
```

**理由**:
- より厳格な品質基準
- エピソードの情報量を確保
- FORMAT_001はHIGH優先度ルール

**推奨**: **オプションA（132-250文字）** - 最新の設計意図を尊重

#### 実装アクション
1. FORMAT_001の最小値を180→132に更新
2. RULE_151/160の説明に「標準基準」として明記
3. 古い150文字基準への参照をすべて削除

---

### 2. 説明文の欠如（20件のルール）

#### 影響を受けるルール
```
RULE_002, RULE_003, RULE_004, RULE_005, RULE_008,
RULE_009, RULE_017, RULE_098, RULE_099, RULE_107,
および10件以上
```

#### 問題点
- ルールの意図が不明確
- メンテナンス性の低下
- 新規開発者の理解困難

#### 推奨解決策

**段階的ドキュメント化計画**:

**フェーズ1**: pdca_guardian.pyから実装を分析して説明を自動生成
```python
# 例: RULE_002の実装から説明を推定
if "calibrated_score" in implementation:
    description = "calibrated_scoreフィールドの使用禁止チェック"
```

**フェーズ2**: 人間によるレビューと精緻化
- 自動生成された説明の検証
- 具体例の追加
- 関連ルールとの関係性の明記

**フェーズ3**: ドキュメント標準の確立
```python
@dataclass
class RuleDocumentation:
    purpose: str          # このルールの目的
    rationale: str        # なぜこのルールが必要か
    examples: List[str]   # 違反例と正しい例
    related_rules: List[str]  # 関連ルール
```

#### 実装アクション
1. `pdca_rule_doc_generator.py`の作成
2. 実装コードからの説明自動抽出
3. レビュー用ワークシートの生成
4. 段階的なドキュメント更新

---

## 🟡 MEDIUM優先度の矛盾

### 3. グループ名チェックの優先度不一致

#### 矛盾の詳細
| ルールID | 説明 | 優先度 | カテゴリ |
|---------|------|--------|----------|
| ENTITY_TYPE_001 | グループ名が個人として登録されていないかチェック | CRITICAL (1) | entity_type |
| RULE_154 | グループ名個人化チェック | MEDIUM (3) | data_quality |

#### 問題点
- 同じ目的（グループ名の個人化チェック）のルールが2つ存在
- 優先度が異なる（CRITICAL vs MEDIUM）
- カテゴリも異なる（entity_type vs data_quality）

#### 推奨解決策

**ルール統合**:
```python
# 統合後のルール定義
ENTITY_TYPE_001 = {
    'rule_id': 'ENTITY_TYPE_001',
    'name': 'グループ名個人化チェック',
    'description': '''
        グループ名が個人（person）として誤って登録されていないかチェック。
        グループはperson_nameに使用せず、person_name_displayで表記すること。

        【チェック項目】
        1. entity_type が 'person' でperson_nameにグループ名が使用されていないか
        2. person_name_display でグループ名を正しく表記しているか
        3. 複数人組のグループを個人として扱っていないか
    ''',
    'priority': 'CRITICAL',  # ENTITY_TYPE_001の優先度を維持
    'category': 'entity_type',  # より適切なカテゴリ
    'replaces': 'RULE_154',  # RULE_154を置き換え
    'related_rules': ['RULE_155', 'RULE_156']
}
```

#### 実装アクション
1. ENTITY_TYPE_001を強化版として統合
2. RULE_154を非推奨化（deprecated）
3. RULE_154への参照をENTITY_TYPE_001に置換
4. マイグレーションガイドの作成

---

### 4. 優先度の不一致（RULE_100 vs RULE_101）

#### 矛盾の詳細
| ルールID | 説明 | 優先度 |
|---------|------|--------|
| RULE_100 | すべてのエピソードとCSV出力に開発クレジットを付与 | HIGH (2) |
| RULE_101 | エピソード関連の違反タイプ（RULE_101-108） | MEDIUM (3) |

#### 問題点
- 内容的に関連性があるが優先度が異なる
- RULE_101がカテゴリヘッダーのような役割

#### 推奨解決策

**階層構造の明確化**:
```python
# RULE_100: 独立ルール（クレジット管理）
RULE_100 = {
    'priority': 'HIGH',
    'category': 'episode_content',
    'tags': ['credit', 'metadata']
}

# RULE_101: カテゴリヘッダー
RULE_101 = {
    'is_category_header': True,  # 新フィールド追加
    'sub_rules': ['RULE_102', 'RULE_103', ..., 'RULE_108'],
    'priority': 'INFORMATIONAL',  # 新優先度レベル
}
```

#### 実装アクション
1. `is_category_header`フィールドをRuleクラスに追加
2. INFORMATIONALレベルをRulePriorityに追加
3. カテゴリヘッダールールの特別扱いを実装

---

### 5. RULE_002 vs RULE_003の優先度不一致

#### 問題点
- 両ルールとも説明が「（説明なし）」
- 優先度が異なる（priority=2 vs priority=3）
- 実装内容が不明

#### 推奨解決策

**段階的アプローチ**:

1. **実装コードの分析**
   ```bash
   grep -B 5 -A 10 "RULE_002\|RULE_003" pdca_guardian.py
   ```

2. **目的の推定**
   - コードパターンから機能を推定
   - 変数名やコメントから意図を抽出

3. **ドキュメント化後に優先度を再評価**
   - 機能が判明してから適切な優先度を決定

#### 実装アクション
1. 問題点2（説明文の欠如）の解決と連動
2. 実装分析ツールでRULE_002/003の機能を特定
3. 特定後に優先度の妥当性を検証

---

## 📋 実装ロードマップ

### フェーズ1: 緊急対応（即座に実施）
- ✅ 文字数範囲の統一（132-250文字に統合）
- ✅ ENTITY_TYPE_001とRULE_154の統合

### フェーズ2: ドキュメント整備（1週間以内）
- 📝 説明なしルールの自動ドキュメント生成
- 📝 人間によるレビューと精緻化

### フェーズ3: 構造改善（2週間以内）
- 🏗️ カテゴリヘッダールールの実装
- 🏗️ 階層構造の明確化

### フェーズ4: 継続的改善（1ヶ月以内）
- 🔄 定期的な矛盾検出
- 🔄 ルールバージョン管理の強化

---

## 🛠️ 推奨実装ツール

### 1. `rule_auto_fixer.py`
矛盾を自動修正するツール
```python
class RuleAutoFixer:
    def fix_character_length_conflicts(self) -> None:
        """文字数範囲を132-250に統一"""

    def merge_duplicate_rules(self, source_id: str, target_id: str) -> None:
        """重複ルールを統合"""

    def add_missing_descriptions(self) -> None:
        """説明なしルールに自動生成説明を追加"""
```

### 2. `rule_validator.py`
継続的な矛盾検出
```python
class RuleValidator:
    def validate_priority_consistency(self) -> List[Issue]:
        """優先度の一貫性をチェック"""

    def validate_completeness(self) -> List[Issue]:
        """ドキュメントの完全性をチェック"""

    def validate_no_duplicates(self) -> List[Issue]:
        """重複ルールがないかチェック"""
```

### 3. `rule_migration_guide_generator.py`
変更の影響範囲を可視化
```python
class MigrationGuideGenerator:
    def generate_impact_report(self, old_rule_id: str, new_rule_id: str) -> str:
        """ルール変更の影響範囲レポート生成"""
```

---

## ✅ 成功基準

### 矛盾解決の完了条件
- [ ] 文字数範囲の矛盾が0件
- [ ] 優先度の不一致が0件
- [ ] すべてのルールに説明が存在
- [ ] カテゴリヘッダーが明確に区別される
- [ ] 重複ルールが0件

### 品質基準
- [ ] すべてのルールにバージョン情報
- [ ] すべてのルールに具体例
- [ ] 関連ルールが正しくリンク
- [ ] ドキュメントが最新状態

---

## 📊 期待される改善効果

### 定量的効果
- **矛盾検出**: 7件 → 0件（100%削減）
- **ドキュメント率**: 72% → 100%（+28ポイント）
- **ルール重複**: 2件 → 0件（100%削減）

### 定性的効果
- ルール適用の一貫性向上
- 新規開発者のオンボーディング時間短縮
- メンテナンスコストの削減
- 品質ゲートの信頼性向上
