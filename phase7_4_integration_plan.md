# Phase 7.4: RULE_179-181統合計画

## 🎯 統合目標

RULE_182（LLM改善エンジン）をRULE_179-181（評価・改善・レポートパイプライン）に統合し、ハイブリッド改善システムを構築する。

---

## 📊 現状分析

### 既存システム（Phase 6）

```
RULE_179: 統合評価パイプライン
  ↓ (評価結果)
RULE_180: パターンベース自動改善
  ↓ (改善後テキスト)
RULE_181: 品質レポート生成
```

### 新システム（Phase 7統合後）

```
RULE_179: 統合評価パイプライン
  ↓ (評価結果)
改善方法選択ロジック
  ├─ 簡単な問題 → RULE_180 (パターンベース)
  └─ 複雑な問題 → RULE_182 (LLM) → フォールバック → RULE_180
      ↓ (改善後テキスト)
RULE_181: 品質レポート生成（LLM使用記録含む）
```

---

## 🔧 統合設計

### 1. 改善方法選択ロジック

#### スコアベース選択
```python
def select_improvement_method(evaluation_result):
    score = evaluation_result.total_score

    if score >= 70:
        # 高スコア: 改善不要
        return "none"
    elif score >= 60:
        # 中スコア: パターンベースで十分
        return "rule180"
    else:
        # 低スコア: LLMで高品質改善
        return "rule182"
```

#### 問題タイプベース選択
```python
def select_by_issue_type(evaluation_result):
    issues = analyze_issues(evaluation_result)

    # 複雑な問題タイプ
    complex_types = ["時系列矛盾", "文脈的矛盾"]

    has_complex = any(i["type"] in complex_types for i in issues)

    if has_complex:
        return "rule182"  # LLM
    else:
        return "rule180"  # パターン
```

### 2. 統合インターフェース

#### ユニファイド改善API
```python
def improve_episode_unified(
    episode_text: str,
    evaluation_result: EpisodeEvaluationResult,
    person_context: Dict[str, Any],
    strategy: str = "auto",  # "auto", "rule180", "rule182", "hybrid"
    llm_provider: str = "openai"
) -> Tuple[str, Dict[str, Any]]:
    """
    統合改善API

    Args:
        strategy: 改善戦略
            - "auto": スコアと問題タイプから自動選択
            - "rule180": RULE_180のみ使用
            - "rule182": RULE_182のみ使用（フォールバックあり）
            - "hybrid": 両方試して良い方を選択
    """
```

### 3. ハイブリッド戦略

両方の改善を実行し、品質の高い方を採用：

```python
def hybrid_improvement(episode_text, evaluation_result, person_context):
    # RULE_180で改善
    text_180, summary_180 = improve_with_rule180(...)
    score_180 = evaluate(text_180).total_score

    # RULE_182で改善
    text_182, summary_182 = improve_with_rule182(...)
    score_182 = evaluate(text_182).total_score

    # 高スコアを採用
    if score_182 > score_180:
        return text_182, {**summary_182, "method": "hybrid_llm_win"}
    else:
        return text_180, {**summary_180, "method": "hybrid_rule180_win"}
```

---

## 📝 実装タスク

### タスク1: 統合インターフェースの作成

**ファイル**: `rules/unified_improvement_interface.py`

**内容**:
- `select_improvement_method()` - 自動選択ロジック
- `improve_episode_unified()` - 統合改善API
- `improve_episode_hybrid()` - ハイブリッド改善

### タスク2: RULE_181の拡張

**ファイル**: `rules/rule_181_quality_report_generator.py`

**追加内容**:
- LLM使用統計（成功/失敗/フォールバック）
- コスト情報（トークン数、推定費用）
- 改善方法内訳（RULE_180 vs RULE_182）

### タスク3: 統合テストスクリプト

**ファイル**: `test_unified_improvement.py`

**テスト内容**:
- 各戦略モードのテスト
- スコア範囲別の改善テスト
- ハイブリッド戦略の有効性検証

---

## 🎨 拡張RULE_181レポート例

```markdown
# エピソード評価レポート

## 改善サマリー

| 改善方法 | 件数 | 平均スコア向上 | 成功率 |
|---------|-----|--------------|--------|
| RULE_180 | 15件 | +5.2点 | 100% |
| RULE_182 (LLM) | 5件 | +16.8点 | 80% |
| フォールバック | 1件 | +4.0点 | 100% |

## LLM使用統計

- 総使用回数: 5回
- 成功: 4回 (80%)
- フォールバック: 1回 (20%)
- 総トークン数: 2,750トークン
- 推定コスト: $0.11

## 戦略別結果

### Auto戦略
- スコア60未満 → RULE_182使用: 5件
- スコア60-70 → RULE_180使用: 10件
- スコア70以上 → 改善スキップ: 5件
```

---

## 🔐 安全性とコスト管理

### コスト上限設定

```python
class CostManager:
    def __init__(self, daily_limit_usd=5.0):
        self.daily_limit = daily_limit_usd
        self.daily_usage = 0.0

    def can_use_llm(self, estimated_cost):
        return (self.daily_usage + estimated_cost) <= self.daily_limit
```

### フォールバック保証

- LLM失敗時は必ずRULE_180にフォールバック
- ネットワークエラー、API制限でも処理継続
- 部分的失敗でも全体処理は完遂

---

## 📊 期待される効果

### 品質向上

- 低スコアエピソード（60点未満）の改善幅: +15点以上
- 中スコアエピソード（60-70点）の安定改善: +5点
- 全体平均スコア: 70点 → 80点以上

### コスト最適化

- 全エピソードLLM使用: $2.00/100件
- Auto戦略（選択的使用）: $0.50/100件
- コスト削減率: 75%

### 処理効率

- RULE_180: 即時（<1秒）
- RULE_182: 3-5秒
- Hybrid: 6-10秒（最高品質保証）

---

## ✅ 完了条件

1. ✅ 統合インターフェースの実装完了
2. ✅ 3つの戦略モードすべてが動作
3. ✅ RULE_181がLLM統計を含むレポート生成
4. ✅ 統合テストで全モード検証
5. ✅ ドキュメント完備

---

## 🚀 次のステップ

Phase 7.4完了後:
- Phase 7.5: 大規模比較評価（20件以上）
- Phase 7完了レポート作成
- 本番環境への段階的展開
