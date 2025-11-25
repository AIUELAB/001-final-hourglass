# Phase 7: LLM改善システム APIリファレンス

**バージョン**: 1.0.0
**最終更新**: 2025-10-02

---

## 📚 目次

1. [RULE_182: LLM改善エンジン](#rule_182-llm改善エンジン)
2. [RULE_183: 統合改善インターフェース](#rule_183-統合改善インターフェース)
3. [コスト管理](#コスト管理)
4. [エラーハンドリング](#エラーハンドリング)
5. [型定義](#型定義)

---

## RULE_182: LLM改善エンジン

### improve_episode_with_llm()

LLMを使用してエピソードを改善する。

```python
def improve_episode_with_llm(
    episode_text: str,
    evaluation_result: Union[Dict, EpisodeEvaluationResult],
    person_context: Dict[str, Any],
    provider: str = "mock",
    use_fallback: bool = True
) -> Tuple[str, Dict[str, Any]]
```

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `episode_text` | str | ✅ | - | 元のエピソードテキスト |
| `evaluation_result` | Dict/Object | ✅ | - | RULE_179評価結果 |
| `person_context` | Dict | ✅ | - | 人物コンテキスト |
| `provider` | str | ❌ | "mock" | LLMプロバイダー |
| `use_fallback` | bool | ❌ | True | フォールバック有効化 |

#### プロバイダー

- `"openai"`: OpenAI GPT-4
- `"anthropic"`: Anthropic Claude-3.5-Sonnet
- `"mock"`: テスト用（APIキー不要）

#### person_context構造

```python
{
    "person_name": str,      # 必須: 人物名
    "birth_year": int,       # 推奨: 生年
    "category": str,         # 推奨: カテゴリ
    "age": int              # オプション: 年齢
}
```

#### 戻り値

```python
(
    improved_text: str,      # 改善後のエピソード
    summary: Dict[str, Any]  # 改善サマリー
)
```

#### summaryの構造

```python
{
    "improved": bool,              # 改善実施フラグ
    "method": str,                 # "llm", "fallback_rule180", etc.
    "provider": str,               # プロバイダー名（LLM使用時）
    "issues_count": int,           # 検出問題数
    "validation": Dict,            # 検証結果
    "processing_time": float,      # 処理時間（秒）
    "original_score": float,       # 元のスコア（オプション）
    "final_score": float          # 最終スコア（オプション）
}
```

#### 使用例

```python
from rules.rule_182_llm_improvement_engine import improve_episode_with_llm
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated

# 評価
evaluation = evaluate_episode_integrated(
    episode_id="EP_001",
    person_name="大谷翔平",
    episode_text="あなたと同じ28歳のとき、素晴らしい業績を残した。",
    database_age=28,
    birth_year=1994
)

# LLMで改善
improved_text, summary = improve_episode_with_llm(
    episode_text="あなたと同じ28歳のとき、素晴らしい業績を残した。",
    evaluation_result=evaluation,
    person_context={
        "person_name": "大谷翔平",
        "birth_year": 1994,
        "category": "プロ野球選手"
    },
    provider="openai",
    use_fallback=True
)

print(f"Method: {summary['method']}")
print(f"Improved: {improved_text}")
```

---

## RULE_183: 統合改善インターフェース

### improve_episode_auto()

**推奨関数** - Auto戦略で自動改善

```python
def improve_episode_auto(
    episode_id: str,
    person_name: str,
    episode_text: str,
    database_age: int,
    person_context: Dict[str, Any],
    llm_provider: str = "openai"
) -> Tuple[str, Dict[str, Any]]
```

#### パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `episode_id` | str | ✅ | - | エピソードID |
| `person_name` | str | ✅ | - | 人物名 |
| `episode_text` | str | ✅ | - | エピソードテキスト |
| `database_age` | int | ✅ | - | データベース年齢 |
| `person_context` | Dict | ✅ | - | 人物コンテキスト |
| `llm_provider` | str | ❌ | "openai" | LLMプロバイダー |

#### 戦略選択ロジック

```python
if score >= 70:
    return "none"          # 改善不要
elif score >= 60:
    return "rule180"       # パターンベース
else:
    return "rule182"       # LLM（予算内の場合）
```

#### 使用例

```python
from rules.unified_improvement_interface import improve_episode_auto

improved_text, summary = improve_episode_auto(
    episode_id="EP_001",
    person_name="イチロー",
    episode_text="あなたと同じ30歳のとき、イチローは活躍した。",
    database_age=30,
    person_context={
        "person_name": "イチロー",
        "birth_year": 1973,
        "category": "プロ野球選手"
    },
    llm_provider="openai"
)
```

---

### UnifiedImprovementInterface

統合改善インターフェースクラス

#### improve_episode_unified()

戦略を指定して改善

```python
def improve_episode_unified(
    self,
    episode_id: str,
    person_name: str,
    episode_text: str,
    database_age: int,
    person_context: Dict[str, Any],
    strategy_mode: str = "auto",
    llm_provider: str = "openai"
) -> Tuple[str, Dict[str, Any]]
```

#### strategy_mode

| 値 | 説明 | 用途 |
|----|------|------|
| `"auto"` | 自動選択（推奨） | 通常運用 |
| `"force_pattern"` | RULE_180のみ | 高速処理 |
| `"force_llm"` | RULE_182のみ | 高品質優先 |
| `"hybrid"` | 両方実行して比較 | 品質保証 |

#### 使用例

```python
from rules.unified_improvement_interface import get_unified_interface

interface = get_unified_interface()

# Hybrid戦略
improved_text, summary = interface.improve_episode_unified(
    episode_id="EP_001",
    person_name="羽生結弦",
    episode_text="...",
    database_age=25,
    person_context={...},
    strategy_mode="hybrid",
    llm_provider="openai"
)

if summary['method'] == 'hybrid_llm_win':
    print(f"LLM優位: +{summary['score_improvement']:.1f}点")
```

---

### get_statistics()

統計情報を取得

```python
def get_statistics(self) -> Dict[str, Any]
```

#### 戻り値

```python
{
    "total_improvements": int,    # 総改善数
    "rule180_count": int,         # RULE_180使用回数
    "rule182_count": int,         # RULE_182使用回数
    "hybrid_count": int,          # Hybrid使用回数
    "skipped_count": int,         # スキップ回数
    "fallback_count": int,        # フォールバック回数
    "cost_usage": float,          # 使用コスト（USD）
    "cost_limit": float,          # コスト上限（USD）
    "remaining_budget": float     # 残予算（USD）
}
```

#### 使用例

```python
interface = get_unified_interface()

# 改善実行後
stats = interface.get_statistics()

print(f"総改善: {stats['total_improvements']}件")
print(f"LLM: {stats['rule182_count']}件")
print(f"コスト: ${stats['cost_usage']:.3f}")
print(f"残予算: ${stats['remaining_budget']:.2f}")
```

---

## コスト管理

### CostManager

LLM使用コストを管理

```python
class CostManager:
    def __init__(self, daily_limit_usd: float = 5.0)
```

#### パラメータ

| 名前 | 型 | デフォルト | 説明 |
|------|-----|----------|------|
| `daily_limit_usd` | float | 5.0 | 日次上限（USD） |

#### メソッド

##### can_use_llm()

LLM使用可能かチェック

```python
def can_use_llm(self, estimated_cost: float = 0.02) -> bool
```

##### record_usage()

使用記録

```python
def record_usage(self, cost: float, episode_id: str = "")
```

##### get_remaining_budget()

残予算取得

```python
def get_remaining_budget(self) -> float
```

##### reset_daily()

日次リセット

```python
def reset_daily(self)
```

#### 使用例

```python
from rules.unified_improvement_interface import (
    get_unified_interface,
    CostManager
)

# コスト管理設定
interface = get_unified_interface(reset=True)
interface.cost_manager = CostManager(daily_limit_usd=10.0)

# 予算チェック
if interface.cost_manager.can_use_llm():
    # LLM使用
    improved_text, summary = improve_episode_auto(...)
else:
    print("予算超過 - パターンベースのみ使用")

# 統計確認
print(f"使用額: ${interface.cost_manager.daily_usage:.2f}")
print(f"残額: ${interface.cost_manager.get_remaining_budget():.2f}")
```

---

## エラーハンドリング

### 例外

#### LLM関連エラー

```python
try:
    improved_text, summary = improve_episode_with_llm(
        ...,
        provider="openai"
    )
except openai.AuthenticationError as e:
    print("APIキーエラー")
except openai.RateLimitError as e:
    print("レート制限エラー")
except Exception as e:
    print(f"その他のエラー: {e}")
```

#### フォールバック

```python
# use_fallback=Trueの場合、エラー時に自動的にRULE_180使用
improved_text, summary = improve_episode_with_llm(
    ...,
    use_fallback=True  # 推奨
)

if "fallback" in summary['method']:
    print("LLM失敗 → RULE_180で改善")
```

### エラーメッセージ

| エラー | 原因 | 対処 |
|--------|------|------|
| `No API key provided` | APIキー未設定 | 環境変数設定 |
| `Rate limit exceeded` | API制限超過 | 時間を置く |
| `コスト上限到達` | 予算超過 | 上限を増やす or リセット |
| `文字数制約違反` | LLM出力不適切 | フォールバック発動 |

---

## 型定義

### EpisodeEvaluationResult

```python
class EpisodeEvaluationResult:
    episode_id: str
    person_name: str
    passed: bool
    total_score: float

    # 各ルールの評価結果
    age_selection: Dict[str, Any]
    social_impact: Dict[str, Any]
    temporal_consistency: Dict[str, Any]
    negative_evaluation: Optional[Dict[str, Any]]
    fictional_character: Optional[Dict[str, Any]]
    abstract_detection: Dict[str, Any]

    # 品質ゲート
    quality_gates: Dict[str, bool]

    # 改善提案
    improvements: List[str]

    # メタデータ
    evaluation_timestamp: str
```

### PersonContext

```python
PersonContext = TypedDict('PersonContext', {
    'person_name': str,          # 必須
    'birth_year': int,           # 推奨
    'category': str,             # 推奨
    'age': NotRequired[int],     # オプション
    'entity_type': NotRequired[str]  # オプション
})
```

### ImprovementSummary

```python
ImprovementSummary = TypedDict('ImprovementSummary', {
    'improved': bool,
    'method': str,
    'provider': NotRequired[str],
    'issues_count': NotRequired[int],
    'validation': NotRequired[Dict],
    'processing_time': NotRequired[float],
    'original_score': NotRequired[float],
    'final_score': NotRequired[float],
    'score_improvement': NotRequired[float]
})
```

---

## ベストプラクティス

### 1. Auto戦略を優先

```python
# ✅ 推奨
improved_text, summary = improve_episode_auto(...)

# ❌ 非推奨（特別な理由がない限り）
improved_text, summary = improve_episode_with_llm(..., use_fallback=False)
```

### 2. コスト管理を設定

```python
# ✅ 推奨
interface = get_unified_interface(reset=True)
interface.cost_manager = CostManager(daily_limit_usd=10.0)

# ❌ 非推奨（予算超過リスク）
# デフォルト設定のまま大量実行
```

### 3. 統計を定期的に確認

```python
# ✅ 推奨
stats = interface.get_statistics()
if stats['cost_usage'] > stats['cost_limit'] * 0.8:
    print("⚠️ 予算80%到達")
```

### 4. フォールバックを有効化

```python
# ✅ 推奨
improve_episode_with_llm(..., use_fallback=True)

# ❌ 非推奨（失敗リスク）
improve_episode_with_llm(..., use_fallback=False)
```

---

## パフォーマンスチューニング

### 処理速度最適化

```python
# 大量処理の場合
for episode in episodes:
    if episode_score < 60:
        # 低スコアのみLLM使用
        improved_text, summary = improve_episode_auto(...)
    else:
        # 高スコアはスキップ or パターンのみ
        pass
```

### コスト最適化

```python
# Anthropic（安価）を優先試行
try:
    improved_text, summary = improve_episode_auto(
        ...,
        llm_provider="anthropic"  # $0.004/件
    )
except:
    # フォールバックでOpenAI
    improved_text, summary = improve_episode_auto(
        ...,
        llm_provider="openai"  # $0.021/件
    )
```

---

## バージョン履歴

| バージョン | 日付 | 変更内容 |
|----------|------|---------|
| 1.0.0 | 2025-10-02 | 初版リリース |

---

## サポート

- **ドキュメント**: `PHASE7_*.md`
- **クイックスタート**: `PHASE7_QUICK_START.md`
- **完了レポート**: `PHASE7_COMPLETION_REPORT.md`
- **コード**: `rules/rule_182_*.py`, `rules/unified_*.py`

---

**APIリファレンス v1.0.0 - Phase 7 LLM改善システム**
