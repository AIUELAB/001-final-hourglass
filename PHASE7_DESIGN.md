# Phase 7 設計書: LLM改善提案システム

**作成日時**: 2025-10-02
**目的**: ルールベース改善（RULE_180）をLLMによる高度な改善提案で補完

---

## 🎯 Phase 7 の目標

### 主要目標
RULE_180のパターンマッチング型改善を、LLMによる文脈理解型改善で強化し、より自然で高品質なエピソード改善を実現する。

### 具体的成果物
1. **RULE_182**: LLM改善エンジン
2. ルールベースとLLMのハイブリッド改善システム
3. 改善品質の比較評価レポート

---

## 📊 現状の課題（RULE_180の限界）

### パターンマッチング型の限界

#### 1. 文脈を無視した置換
```
❌ 悪い例:
元: "多くの人々に影響を与えた"
RULE_180: "3つの人々に影響を与えた"  # 不自然

✅ LLMなら:
"100万人以上の観客を魅了した" # 文脈に合った具体化
```

#### 2. 意味の損失
```
❌ 悪い例:
元: "素晴らしい業績を残した"
RULE_180: "業績を残した"  # 「素晴らしい」を単に削除

✅ LLMなら:
"史上最年少でノーベル賞を受賞した" # 事実で置き換え
```

#### 3. 複雑な時系列矛盾
```
❌ RULE_180では対応不可:
"18歳でオリンピック金メダル、同じ年にノーベル賞も受賞"
# 両方とも個別には可能だが、同時は極めて稀

✅ LLMなら:
時系列的・論理的整合性を考慮した修正が可能
```

---

## 🏗️ システムアーキテクチャ

### ハイブリッドアプローチ

```
┌─────────────────────────────────────────┐
│      エピソード評価（RULE_179）          │
│  - 問題検出                             │
│  - 重大度判定                           │
│  - 改善候補領域の特定                    │
└────────────┬────────────────────────────┘
             │
             ▼
     ┌───────────────────┐
     │  改善戦略選択      │
     └───────┬───────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────┐      ┌──────────┐
│RULE_180 │      │RULE_182  │
│ルール   │      │LLM改善   │
│ベース   │      │エンジン  │
└────┬────┘      └─────┬────┘
     │                  │
     └────────┬─────────┘
              │
              ▼
      ┌──────────────┐
      │ 改善結果統合  │
      │ - 品質検証   │
      │ - 最適解選択 │
      └──────┬───────┘
             │
             ▼
      ┌──────────────┐
      │最終改善文    │
      └──────────────┘
```

### 改善戦略マトリクス

| 問題タイプ | RULE_180 | RULE_182 (LLM) | 推奨 |
|-----------|---------|---------------|------|
| 単純な年齢矛盾 | ✅ 高速 | ✅ 正確 | RULE_180 |
| 複雑な時系列矛盾 | ❌ 困難 | ✅ 可能 | RULE_182 |
| センセーショナル表現 | ✅ パターン対応 | ✅ 文脈考慮 | ハイブリッド |
| 抽象表現具体化 | ⚠️ 機械的 | ✅ 自然 | RULE_182 |
| 事実誤認 | ❌ 不可能 | ✅ 可能 | RULE_182 |
| 文章の流暢性 | ❌ 不可能 | ✅ 可能 | RULE_182 |

---

## 🤖 RULE_182: LLM改善エンジン設計

### 主要機能

#### 1. 問題分析プロンプト
```python
def analyze_issues_with_llm(episode_text: str, evaluation_result: Dict) -> List[Issue]:
    """
    LLMに評価結果を提示し、改善が必要な箇所を分析させる

    プロンプト:
    あなたはエピソード品質管理の専門家です。
    以下のエピソードと評価結果を分析し、改善が必要な箇所を特定してください。

    エピソード: {episode_text}

    評価結果:
    - 時系列整合性: {temporal_issues}
    - ネガティブ表現: {negative_issues}
    - 抽象表現: {abstract_issues}

    各問題について以下を出力してください:
    1. 問題箇所（引用）
    2. 問題の種類
    3. 重大度（CRITICAL/WARNING/INFO）
    4. 改善方針
    """
```

#### 2. 改善生成プロンプト
```python
def generate_improvement_with_llm(
    episode_text: str,
    issues: List[Issue],
    person_context: Dict
) -> str:
    """
    特定された問題を修正したエピソードを生成

    プロンプト:
    以下のエピソードを改善してください。

    元のエピソード: {episode_text}

    人物情報:
    - 名前: {person_name}
    - 生年: {birth_year}
    - 職業: {category}

    改善すべき問題:
    {issues}

    改善ガイドライン:
    1. 元の意図を保持
    2. 具体的な事実に基づく
    3. 客観的な表現を使用
    4. 時系列的に整合性を保つ
    5. 150-250文字を維持

    改善後のエピソードのみを出力してください。
    """
```

#### 3. 品質検証プロンプト
```python
def validate_improvement_with_llm(
    original: str,
    improved: str,
    evaluation_result: Dict
) -> Dict:
    """
    改善結果が元の問題を解決しているか検証

    プロンプト:
    以下の改善結果を評価してください。

    元のエピソード: {original}
    改善後: {improved}

    元の問題:
    {evaluation_issues}

    以下の観点で評価してください:
    1. 問題が解決されているか（Yes/No）
    2. 元の意図が保持されているか（1-10点）
    3. 文章の自然さ（1-10点）
    4. 事実の正確性（1-10点）
    5. 総合評価（1-10点）
    """
```

### LLMプロバイダー対応

```python
class LLMProvider:
    """LLMプロバイダーの抽象基底クラス"""

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4を使用"""
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3  # 低めで安定した出力
        )
        return response.choices[0].message.content

class AnthropicProvider(LLMProvider):
    """Anthropic Claude-3.5-Sonnetを使用"""
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
```

---

## 🔄 改善フロー

### ハイブリッド改善プロセス

```
1. 評価（RULE_179）
   └─ 問題検出: CRITICAL=3, WARNING=2

2. 戦略選択
   ├─ 単純な問題 → RULE_180（パターンマッチング）
   │   例: "18歳" → "25歳"（最年少記録基準）
   │
   └─ 複雑な問題 → RULE_182（LLM）
       例: 文脈を考慮した具体化

3. 並行実行
   ┌──────────────┐  ┌──────────────┐
   │ RULE_180     │  │ RULE_182     │
   │ 結果A        │  │ 結果B        │
   └──────┬───────┘  └──────┬───────┘
          │                 │
          └────────┬────────┘
                   │
4. 品質評価
   ├─ 結果Aの再評価（RULE_179）
   ├─ 結果Bの再評価（RULE_179）
   └─ LLMによる総合評価

5. 最適解選択
   └─ スコアが高い方を採用
       または両方の良い部分を組み合わせ
```

---

## 📈 評価指標

### 改善品質メトリクス

```python
@dataclass
class ImprovementQualityMetrics:
    """改善品質メトリクス"""

    # 問題解決度
    issues_resolved: int          # 解決した問題数
    issues_remaining: int         # 残存問題数
    resolution_rate: float        # 解決率（%）

    # 品質維持
    intent_preservation: float    # 元の意図保持度（0-10）
    fluency_score: float         # 文章の自然さ（0-10）
    factual_accuracy: float      # 事実正確性（0-10）

    # スコア変化
    score_before: float          # 改善前スコア
    score_after: float           # 改善後スコア
    score_improvement: float     # スコア向上幅

    # 効率性
    processing_time: float       # 処理時間（秒）
    llm_tokens_used: int        # LLMトークン使用量
    cost_estimate: float        # コスト推定（USD）
```

### 比較評価項目

| 項目 | RULE_180 | RULE_182 | 評価基準 |
|-----|---------|---------|---------|
| 問題解決率 | 計測 | 計測 | 高いほど良い |
| 意図保持度 | 計測 | 計測 | 10点満点 |
| 文章自然さ | 計測 | 計測 | 10点満点 |
| 処理速度 | 計測 | 計測 | 速いほど良い |
| コスト | 無料 | 計測 | 安いほど良い |
| スコア向上幅 | 計測 | 計測 | 大きいほど良い |

---

## 🎨 プロンプト設計原則

### 1. Few-Shot Examples

良い改善例を含めて学習させる:

```
以下は良い改善例です:

例1:
元: "素晴らしい業績を残した"
改善: "ノーベル物理学賞を受賞した"
理由: 抽象表現を具体的な事実に置き換え

例2:
元: "多くの人々に影響を与えた"
改善: "累計視聴者数1億人を超えるYouTuberとして活躍した"
理由: 具体的な数値と職業を明記

例3:
元: "悪質な犯罪で糾弾された"
改善: "横領事件で逮捕され、懲役5年の判決を受けた"
理由: センセーショナルな表現を事実に置き換え
```

### 2. Chain-of-Thought

段階的な思考プロセスを促す:

```
以下の手順で改善してください:

Step 1: 問題箇所の特定
- どこに問題があるか引用してください

Step 2: 問題の分析
- なぜ問題なのか説明してください

Step 3: 改善方針の決定
- どのように修正すべきか方針を示してください

Step 4: 改善案の生成
- 具体的な改善案を提示してください

Step 5: 検証
- 改善案が問題を解決しているか確認してください
```

### 3. Constraints

明確な制約条件:

```
制約条件:
1. 文字数: 150-250文字を維持
2. 主語: "あなたと同じ{age}歳のとき" を保持
3. 事実性: Wikipedia等で検証可能な事実のみ使用
4. 客観性: 主観的評価を避ける
5. 具体性: 抽象表現を具体的な数値・固有名詞に置き換える
```

---

## 🔒 品質保証

### LLM出力の検証

```python
def validate_llm_output(
    original: str,
    improved: str,
    constraints: Dict
) -> Tuple[bool, List[str]]:
    """
    LLM出力が制約条件を満たすか検証

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # 1. 文字数チェック
    if not (150 <= len(improved) <= 250):
        errors.append(f"文字数制約違反: {len(improved)}文字")

    # 2. 主語の保持チェック
    pattern = r"あなたと同じ\d+歳のとき"
    if not re.search(pattern, improved):
        errors.append("主語が保持されていません")

    # 3. 禁止表現チェック
    forbidden = ["素晴らしい", "優れた", "悪質な", "卑劣な"]
    for word in forbidden:
        if word in improved:
            errors.append(f"禁止表現が含まれています: {word}")

    # 4. RULE_179による再評価
    result = evaluate_episode_integrated(
        episode_id="validation",
        person_name=constraints["person_name"],
        episode_text=improved,
        database_age=constraints["age"]
    )

    if not result.passed:
        errors.append(f"品質基準未達: スコア{result.total_score}")

    return len(errors) == 0, errors
```

### フォールバック戦略

```python
def improve_with_fallback(
    episode_text: str,
    evaluation: Dict,
    max_attempts: int = 3
) -> str:
    """
    フォールバック戦略付き改善

    1. LLM改善を試行
    2. 検証失敗 → ルールベース改善
    3. それでも失敗 → 元のテキストを返す
    """
    for attempt in range(max_attempts):
        # LLM改善
        improved = llm_engine.improve(episode_text, evaluation)

        # 検証
        is_valid, errors = validate_llm_output(improved, constraints)

        if is_valid:
            return improved

        logger.warning(f"LLM改善失敗（試行{attempt+1}）: {errors}")

    # フォールバック: ルールベース
    logger.info("ルールベース改善にフォールバック")
    improved, _ = rule_based_engine.improve(episode_text, evaluation)

    return improved
```

---

## 💰 コスト管理

### トークン使用量推定

```python
# GPT-4の場合
COST_PER_1K_INPUT_TOKENS = 0.03   # USD
COST_PER_1K_OUTPUT_TOKENS = 0.06  # USD

# Claude-3.5-Sonnetの場合
COST_PER_1K_INPUT_TOKENS = 0.003  # USD
COST_PER_1K_OUTPUT_TOKENS = 0.015 # USD

def estimate_cost(
    episode_count: int,
    avg_episode_length: int = 200,
    provider: str = "anthropic"
) -> float:
    """
    処理コストを推定

    Args:
        episode_count: エピソード数
        avg_episode_length: 平均エピソード長（文字数）
        provider: 'openai' or 'anthropic'

    Returns:
        推定コスト（USD）
    """
    # 1エピソードあたりの推定トークン数
    input_tokens = avg_episode_length * 1.5  # 日本語は1.5倍換算
    output_tokens = avg_episode_length * 1.2  # 改善後も同程度

    if provider == "openai":
        cost_per_episode = (
            (input_tokens / 1000) * 0.03 +
            (output_tokens / 1000) * 0.06
        )
    else:  # anthropic
        cost_per_episode = (
            (input_tokens / 1000) * 0.003 +
            (output_tokens / 1000) * 0.015
        )

    return cost_per_episode * episode_count

# 19件のエピソード改善コスト
print(f"OpenAI: ${estimate_cost(19, provider='openai'):.2f}")
print(f"Anthropic: ${estimate_cost(19, provider='anthropic'):.2f}")
```

---

## 📋 実装タスク

### Phase 7.2: RULE_182実装

- [ ] `LLMProvider` 基底クラス
- [ ] `OpenAIProvider` 実装
- [ ] `AnthropicProvider` 実装
- [ ] プロンプトテンプレート設計
- [ ] `LLMImprovementEngine` クラス
  - [ ] `analyze_issues()` メソッド
  - [ ] `generate_improvement()` メソッド
  - [ ] `validate_improvement()` メソッド
- [ ] 出力検証ロジック
- [ ] フォールバック機構

### Phase 7.3: プロンプト最適化

- [ ] Few-Shot Examples収集
- [ ] Chain-of-Thought設計
- [ ] 制約条件定義
- [ ] テストケースでの検証
- [ ] プロンプト反復改善

### Phase 7.4: 統合

- [ ] RULE_179との連携
- [ ] RULE_180とのハイブリッド化
- [ ] RULE_181へのLLM結果追加
- [ ] 統合テスト

### Phase 7.5: 比較評価

- [ ] RULE_180 vs RULE_182の比較
- [ ] 品質メトリクス計測
- [ ] コスト分析
- [ ] 推奨使用ケース決定

---

## 🎯 成功基準

| 指標 | 目標値 |
|-----|--------|
| 問題解決率 | >90% |
| 意図保持度 | >8.0/10 |
| 文章自然さ | >8.5/10 |
| スコア向上幅 | 平均+10点以上 |
| 処理時間 | <10秒/エピソード |
| コスト | <$1.00/19エピソード |

---

**Phase 7 設計完了**

次: RULE_182の実装に進みます。
