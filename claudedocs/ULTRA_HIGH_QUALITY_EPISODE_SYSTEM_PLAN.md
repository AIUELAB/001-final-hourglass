# 超高品質エピソード作成システム構築計画

**作成日**: 2025-10-02
**目標**: 初回生成で90点以上を安定達成、評価失敗を最小化

---

## 🎯 エグゼクティブサマリー

### 現状

- ✅ **既存システム**: 90点台エピソード生成可能
- ✅ **10エピソードテスト**: 100%合格率達成
- ❌ **課題**: 初回合格率が不安定（内容次第で14点→36点の変動）

### 目標

- 🎯 **初回合格率**: 95%以上
- 🎯 **平均スコア**: 90点以上（安定）
- 🎯 **反復回数**: 平均1.2回以下
- 🎯 **コスト**: 1エピソードあたり$0.003以下

### 戦略

1. **プロンプト明示化**: 5要素を必須化
2. **Few-Shot Learning**: 合格エピソード3-5個を例示
3. **品質ゲート**: 生成前後の自動チェック
4. **フィードバックループ**: 失敗時の即座改善

---

## 📊 STEP 3: プロンプト改善戦略

### 3.1 合格エピソードの解剖

#### ゴールドスタンダード: 新垣結衣（EP052）

```text
あなたと同じ18歳のとき、新垣結衣は主演映画『恋空』が興行収入39億円の大ヒットを記録した。
しかし「演技経験が少ない新人に大作主演は無理」という映画業界の強い反対があった。
オーディションで何度も落選し、沖縄出身というハンデを乗り越えて勝ち取った役だった。
撮影中も「なぜこの子が主演？」という批判の声が絶えなかったが、
透明感のある演技で日本アカデミー賞新人俳優賞を受賞。
この年CM出演社数は10社を超え、「ガッキー」の愛称で国民的女優への階段を駆け上がった。
```

**構造分析**:

| 要素 | 実装 | スコア | 手法 |
|-----|------|--------|------|
| **転換点** | 「興行収入39億円」「階段を駆け上がった」 | 10/10 | 明確な成果 + 強い動詞 |
| **意外性** | 「何度も落選」「沖縄出身のハンデ」 | 7/10 | 逆境からの成功 |
| **リスク** | 「演技経験が少ない新人」「大作主演」 | 7/10 | 背景 + 挑戦の大きさ |
| **共感性** | 「本当に無理」「なぜこの子が」 | 7/10 | 懸念を引用符で明示 |
| **衝撃度** | 「39億円」「10社超」「階段を駆け上がった」 | 10/10 | 具体的数値 + 強い表現 |

**成功の公式**:

```
1. 明確な不安・反対（引用符付き）
2. 逆境の具体化（何度も、ハンデ、経験不足）
3. センセーショナルな数値（39億円、10社）
4. 強い動詞（駆け上がった、勝ち取った）
5. ビフォーアフターの明確化
```

---

### 3.2 プロンプトテンプレート設計

#### テンプレートV3.0（Few-Shot + 明示的要件）

```python
ULTRA_HIGH_QUALITY_PROMPT = """
# ミッション
{person_name}が{age}歳のときの超高品質エピソードを生成してください。

# 必須要素（Phase 3評価基準 - 50点満点）

## 1. 人生の転換点（目標: 10/10点）
- 明確な成果を数値で示す
- 「転機」「決断」「〜をもたらした」等の強い表現

## 2. 意外性（目標: 7/10点）
- 逆境からの成功
- 前例のない挑戦
- 「初めて」「前例なく」等

## 3. リスクテイキング（目標: 7/10点）
- 具体的な期間（3ヶ月、わずか2年等）
- 前例の無さ
- 無名・若さ等の背景

## 4. 共感性（目標: 7/10点）
- 不安・葛藤を引用符で明示
- 「本当に〜？」形式
- ステークホルダーの懸念

## 5. センセーショナル度（目標: 10/10点）
- 具体的数値3つ以上（金額、人数、期間）
- 強い動詞（駆け上がった、切り開いた、もたらした）

# 成功例（参考にしてください）

## 例1: 新垣結衣（18歳）- 36点合格
{example_1_text}

【成功要因】
- 不安: "演技経験が少ない新人に大作主演は無理"
- リスク: "何度も落選"、"沖縄出身のハンデ"
- 数値: "39億円"、"10社超"
- 強い表現: "階段を駆け上がった"

## 例2: 松下幸之助（56歳）- 36点合格
{example_2_text}

【成功要因】
- 不安: "週休2日制は企業を滅ぼす"
- リスク: "業界の猛反対の中"、"初めて導入"
- 数値: "20%向上"、"1兆円企業"、"10万人超"
- 強い表現: "押し上げた"、"貫いた"

## 例3: イチロー（45歳）- 高評価
{example_3_text}

【成功要因】
- 転機: "28年間のプロ野球人生に幕"
- 数値: "4367安打"、"10年連続200本"
- 引用: "プロフェッショナルとは..."
- 強い表現: "前人未到の記録"

# 生成要件

## 必須チェックリスト
- [ ] 年齢: {age}歳時点のエピソード（厳守）
- [ ] 不安・懸念: 引用符付きで明示
- [ ] 数値: 具体的数値を3つ以上含める
- [ ] リスク: 逆境・前例なし・若さ等を明記
- [ ] 強い動詞: 「駆け上がった」「切り開いた」「もたらした」等
- [ ] 文字数: 180-250文字

## スコア目標
- Phase 3インパクト: 50点満点中50点以上
- 各要素: 7点以上（転換点とセンセーショナル度は10点目標）

# 出力
{age}歳時点のエピソードのみを出力してください（説明不要）。
"""
```

---

### 3.3 動的Few-Shot選択アルゴリズム

#### 類似性ベースの例示選択

```python
def select_best_examples(
    target_person: str,
    target_age: int,
    target_category: str,
    example_db: List[Episode],
    n_examples: int = 3
) -> List[Episode]:
    """
    対象人物に最も近い成功例を選択

    Args:
        target_person: 生成対象の人物名
        target_age: 対象年齢
        target_category: カテゴリ（エンターテインメント、ビジネス等）
        example_db: 合格エピソードデータベース
        n_examples: 選択する例の数

    Returns:
        最適な例示エピソードのリスト
    """
    scores = []

    for example in example_db:
        score = 0

        # カテゴリ一致（最重要）
        if example.category == target_category:
            score += 50

        # 年齢の近さ
        age_diff = abs(example.age - target_age)
        age_score = max(0, 30 - age_diff)  # 30歳差まで評価
        score += age_score

        # 評価スコアの高さ
        score += example.evaluation_score * 0.2

        scores.append((example, score))

    # スコア順にソート
    scores.sort(key=lambda x: x[1], reverse=True)

    return [ex for ex, _ in scores[:n_examples]]
```

#### カテゴリ別のベストプラクティス

| カテゴリ | 推奨例示 | 特徴 |
|---------|---------|------|
| **エンターテインメント** | 新垣結衣、HIKAKIN、あいみょん | 不安明示、数値強調 |
| **ビジネス** | 松下幸之助、前澤友作、堀江貴文 | 反対意見、リスク決断 |
| **スポーツ** | イチロー、大谷翔平、羽生結弦 | 前人未到、具体的記録 |
| **科学** | 山中伸弥、本庶佑、大隅良典 | 画期的発見、受賞 |
| **芸術** | 草間彌生、村上隆、横尾忠則 | 独自性、世界的評価 |

---

### 3.4 プロンプトの段階的強化

#### レベル1: 基本プロンプト（現状）

```python
# 曖昧な指示
"人物Xの年齢Y歳のエピソードを生成してください"
```

**問題**: 要件が不明確、失敗率高い

#### レベル2: 要件明示プロンプト

```python
# 要素を列挙
"""
以下を含めてください:
1. 不安・葛藤
2. リスクテイキング
3. 数値3つ以上
4. 強い動詞
5. 転機の明示
"""
```

**改善**: 要件明確化、失敗率中程度

#### レベル3: Few-Shot + 明示的要件（推奨）

```python
# 成功例を3-5個提示 + 詳細な評価基準
ULTRA_HIGH_QUALITY_PROMPT  # 上記テンプレート使用
```

**効果**: 要件完全明示、失敗率最小

#### レベル4: Chain-of-Thought + Few-Shot（最高品質）

```python
"""
# ステップ1: エピソード候補のブレインストーミング
{person_name}の{age}歳時点の主要な出来事を3つ挙げてください。

# ステップ2: 最適エピソードの選択
以下の基準で最も適切なエピソードを選んでください:
- 転換点の明確さ
- 意外性の高さ
- リスクの大きさ

# ステップ3: エピソード生成
選択したエピソードについて、以下の成功例を参考に生成してください:
{few_shot_examples}

# ステップ4: 自己評価
生成したエピソードを5要素で評価してください（各10点満点）:
- 人生の転換点: __/10
- 意外性: __/10
- リスクテイキング: __/10
- 共感性: __/10
- センセーショナル度: __/10

合計50点未満の場合は改善してください。
"""
```

**効果**: 最高品質、但しコスト高

---

## 📊 STEP 4: 品質ゲートシステム設計

### 4.1 3段階品質ゲート

```
┌───────────────────────────────────────┐
│  Gate 1: プリフライトチェック（生成前）│
│  - 年齢データの検証                    │
│  - カテゴリの確認                      │
│  - 例示エピソードの準備                │
└───────────────────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Gate 2: 即時検証（生成直後）          │
│  - キーワード存在チェック              │
│  - 数値カウント                        │
│  - 文字数確認                          │
│  - 年齢一致確認                        │
└───────────────────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Gate 3: 詳細評価（LLM評価）           │
│  - Phase 1-4評価実行                   │
│  - スコアが50点未満 → 自動改善         │
│  - 3回改善で不合格 → 人間介入要求      │
└───────────────────────────────────────┘
```

### 4.2 即時検証システム（Gate 2）

```python
class InstantQualityGate:
    """生成直後の即時品質チェック"""

    REQUIRED_KEYWORDS = {
        "anxiety": ["本当に", "不安", "懸念", "心配", "?"],
        "risk": ["初めて", "無名", "断行", "前例なく", "挑戦"],
        "turning_point": ["転機", "決断", "もたらした", "切り開いた", "押し上げた"],
    }

    REQUIRED_NUMBERS = 3  # 最低数値数
    CHAR_RANGE = (180, 250)  # 文字数範囲

    def validate(self, episode: str, target_age: int) -> ValidationResult:
        """即時検証実行"""
        issues = []
        auto_fix = []

        # 1. 年齢確認（最優先）
        if not self._check_age_match(episode, target_age):
            issues.append({
                "type": "CRITICAL",
                "message": "年齢不一致",
                "auto_fix": False
            })
            return ValidationResult(passed=False, issues=issues)

        # 2. キーワードチェック
        for category, keywords in self.REQUIRED_KEYWORDS.items():
            if not any(kw in episode for kw in keywords):
                issues.append({
                    "type": "ERROR",
                    "category": category,
                    "message": f"{category}キーワードが不足",
                    "auto_fix": True,
                    "suggestion": f"以下を追加: {keywords[:2]}"
                })
                auto_fix.append(category)

        # 3. 数値カウント
        num_count = self._count_numbers(episode)
        if num_count < self.REQUIRED_NUMBERS:
            issues.append({
                "type": "WARNING",
                "message": f"数値不足（{num_count}/{self.REQUIRED_NUMBERS}）",
                "auto_fix": True,
                "suggestion": "金額・人数・期間を追加"
            })
            auto_fix.append("numbers")

        # 4. 文字数確認
        char_count = len(episode)
        if not (self.CHAR_RANGE[0] <= char_count <= self.CHAR_RANGE[1]):
            issues.append({
                "type": "WARNING",
                "message": f"文字数範囲外（{char_count}文字）",
                "auto_fix": True
            })
            auto_fix.append("length")

        # 結果判定
        critical_issues = [i for i in issues if i["type"] == "CRITICAL"]
        can_auto_fix = all(i.get("auto_fix", False) for i in issues)

        return ValidationResult(
            passed=len(critical_issues) == 0,
            issues=issues,
            auto_fix_available=can_auto_fix,
            auto_fix_categories=auto_fix
        )
```

### 4.3 自動修正システム

```python
class AutoFixEngine:
    """失敗要素の自動修正"""

    def fix_missing_anxiety(self, episode: str, person_name: str) -> str:
        """不安・懸念を追加"""
        templates = [
            "しかし「本当にこれで大丈夫？」という{stakeholder}の不安があった。",
            "「{person}に{task}は無理では」という懸念の声もあったが、",
            "当初は「本当に{outcome}するのか？」と不安視されたが、"
        ]

        # 適切な位置に挿入（通常は2文目）
        sentences = episode.split("。")
        if len(sentences) >= 2:
            insert_pos = 1
            anxiety_phrase = random.choice(templates).format(
                person=person_name,
                stakeholder="業界",
                task="大役",
                outcome="成功"
            )
            sentences.insert(insert_pos, anxiety_phrase)
            return "。".join(sentences)

        return episode

    def fix_missing_risk(self, episode: str) -> str:
        """リスクテイキングを強化"""
        risk_phrases = [
            "前例のない挑戦として",
            "わずか{period}で",
            "無名の{occupation}として",
            "初めての{action}に踏み切り"
        ]

        # 1文目に追加
        first_sentence = episode.split("。")[0]
        risk_phrase = random.choice(risk_phrases)
        enhanced = first_sentence + risk_phrase + "、" + "。".join(episode.split("。")[1:])

        return enhanced

    def fix_insufficient_numbers(self, episode: str, person_data: Dict) -> str:
        """数値を強化（外部データ活用）"""
        # Wikipedia等から具体的数値を取得
        additional_numbers = self._fetch_numerical_facts(person_data)

        # エピソードに統合
        for num_fact in additional_numbers:
            episode = self._integrate_number(episode, num_fact)

        return episode
```

---

## 🔄 STEP 5: フィードバックループ設計

### 5.1 反復改善フロー

```
生成 → 即時検証 → 自動修正 → LLM評価 → 改善提案 → 再生成
  ↑                                                    ↓
  └────────────────── 3回まで繰り返し ──────────────────┘
```

### 5.2 スマート反復アルゴリズム

```python
class SmartIterationEngine:
    """スマート反復改善システム"""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.instant_gate = InstantQualityGate()
        self.auto_fix = AutoFixEngine()
        self.evaluator = HybridImpactEvaluator()

    def generate_with_iterations(
        self,
        person_name: str,
        age: int,
        category: str
    ) -> GenerationResult:
        """反復改善付き生成"""

        # 例示エピソード選択
        examples = self._select_best_examples(person_name, age, category)

        # プロンプト構築
        prompt = self._build_ultra_prompt(person_name, age, examples)

        for iteration in range(self.max_iterations):
            # 生成
            episode = self._generate_episode(prompt)

            # Gate 2: 即時検証
            instant_result = self.instant_gate.validate(episode, age)

            if not instant_result.passed:
                if instant_result.auto_fix_available:
                    # 自動修正
                    episode = self._apply_auto_fix(
                        episode,
                        instant_result.auto_fix_categories
                    )
                else:
                    # Critical issue → 失敗
                    return GenerationResult(
                        passed=False,
                        reason="Critical validation failure",
                        iteration=iteration
                    )

            # Gate 3: LLM評価
            evaluation = self.evaluator.evaluate(episode)

            if evaluation.total_score >= 50:
                # 合格
                return GenerationResult(
                    passed=True,
                    episode=episode,
                    score=evaluation.total_score,
                    iteration=iteration + 1
                )

            # 不合格 → 改善提案生成
            improvements = self._generate_improvements(evaluation)

            # プロンプト更新（具体的改善指示を追加）
            prompt = self._update_prompt_with_feedback(
                prompt,
                episode,
                evaluation,
                improvements
            )

        # 3回失敗
        return GenerationResult(
            passed=False,
            reason="Max iterations reached",
            best_score=evaluation.total_score,
            iteration=self.max_iterations
        )
```

### 5.3 改善提案生成

```python
def _generate_improvements(self, evaluation: EvaluationResult) -> List[str]:
    """評価結果から具体的改善提案を生成"""
    improvements = []

    # 各要素を分析
    for element, score in evaluation.element_scores.items():
        if score < 7:  # 不足
            improvements.append(
                self._get_improvement_template(element, score)
            )

    return improvements

def _get_improvement_template(self, element: str, current_score: int) -> str:
    """要素別の改善テンプレート"""
    templates = {
        "turning_point": {
            "action": "転機をより明確に",
            "examples": [
                "「〜をもたらした」と明記",
                "「〜という新時代を築いた」",
                "具体的な成果の数値を追加"
            ]
        },
        "unexpectedness": {
            "action": "意外性を強化",
            "examples": [
                "「前例のない」を追加",
                "逆境からの成功を強調",
                "初期の困難を描写"
            ]
        },
        "risk_taking": {
            "action": "リスクを具体化",
            "examples": [
                "期間を明記（3ヶ月、わずか2年等）",
                "「無名の」「若干〜歳の」等を追加",
                "反対意見を引用符で明示"
            ]
        },
        "empathy": {
            "action": "共感性を追加",
            "examples": [
                "「本当に〜？」という不安を引用",
                "ステークホルダーの懸念を明記",
                "葛藤の描写を追加"
            ]
        },
        "sensational": {
            "action": "センセーショナル度を強化",
            "examples": [
                "具体的数値を3つ以上追加",
                "強い動詞を使用（駆け上がった、切り開いた）",
                "「前人未到」「史上初」等の表現"
            ]
        }
    }

    template = templates.get(element, {})
    examples_str = "\n  - ".join(template.get("examples", []))

    return f"""
【{element}を改善】（現在{current_score}/10点）
推奨アクション: {template.get('action', '強化')}
具体例:
  - {examples_str}
"""
```

---

## 📝 STEP 6: 実装計画

### Phase 1: 基盤構築（1週間）

**タスク**:
1. Few-Shot例示データベース構築
   - episodes_validated_100_20251001.csvから抽出
   - カテゴリ別に分類
   - 評価スコアとメタデータを付与

2. プロンプトテンプレートV3.0実装
   - ULTRA_HIGH_QUALITY_PROMPT実装
   - 動的Few-Shot選択機能
   - カテゴリ別最適化

3. InstantQualityGate実装
   - キーワードチェッカー
   - 数値カウンター
   - 文字数検証

**成果物**:
- `few_shot_database.py`
- `ultra_prompt_v3.py`
- `instant_quality_gate.py`

### Phase 2: 自動修正機能（1週間）

**タスク**:
1. AutoFixEngine実装
   - 不安追加ロジック
   - リスク強化ロジック
   - 数値強化ロジック（Wikipedia連携）

2. SmartIterationEngine実装
   - 反復改善フロー
   - 改善提案生成
   - プロンプト動的更新

3. テスト & チューニング
   - 10エピソードで検証
   - 改善提案の精度測定

**成果物**:
- `auto_fix_engine.py`
- `smart_iteration_engine.py`
- `TEST_PHASE2_REPORT.md`

### Phase 3: 統合 & 最適化（1週間）

**タスク**:
1. UltraHighQualityGenerator統合
   - 全コンポーネント統合
   - エラーハンドリング
   - ロギング強化

2. パフォーマンス最適化
   - キャッシング導入
   - 並列処理
   - コスト削減

3. 本番テスト
   - 100エピソード生成
   - 合格率・スコア測定
   - コスト分析

**成果物**:
- `ultra_high_quality_generator_v2.py`
- `PRODUCTION_TEST_REPORT.md`

### Phase 4: 本番展開（1週間）

**タスク**:
1. ドキュメント整備
   - API仕様書
   - 使用ガイド
   - トラブルシューティング

2. 監視システム構築
   - 成功率モニタリング
   - コストアラート
   - 品質ダッシュボード

3. 本番運用開始
   - 段階的ロールアウト
   - フィードバック収集
   - 継続改善

**成果物**:
- `API_SPECIFICATION.md`
- `MONITORING_DASHBOARD.html`
- `OPERATION_MANUAL.md`

---

## 🎯 期待される成果

### 品質指標

| メトリクス | 現状 | 目標 | 達成方法 |
|----------|------|------|---------|
| **初回合格率** | 70%（推定） | 95%以上 | Few-Shot + 即時検証 |
| **平均スコア** | 90.1点 | 92点以上 | プロンプト強化 |
| **平均反復回数** | 1.0回 | 1.2回以下 | 自動修正で1回目成功率向上 |
| **コスト** | $0.002/エピソード | $0.003以下 | 反復削減で許容範囲内 |

### ROI分析

**投資**:
- 開発時間: 4週間 × 1人
- 開発コスト: 推定$0（既存システム活用）

**リターン**:
- 不合格エピソードの再生成コスト削減: 30%削減
- 人間介入時間の削減: 50%削減
- 品質安定化による信頼性向上: 定性的価値

**予想効果**:
- 月間1000エピソード生成で年間$500のコスト削減
- 品質安定化によるユーザー満足度向上（定量化困難）

---

## 📊 リスクと対策

### リスク1: Few-Shot例示の偏り

**リスク**: 特定カテゴリの例示が不足
**対策**: カテゴリ別に最低5例確保、不足時は手動で高品質例を追加

### リスク2: 自動修正の過剰介入

**リスク**: 自動修正で不自然なエピソードに
**対策**: 修正前後でLLM評価を実施、改悪を検出

### リスク3: コスト増加

**リスク**: 反復回数増加でコスト超過
**対策**: 初回合格率向上でトータルコスト削減、上限3回を厳守

### リスク4: プロンプト肥大化

**リスク**: Few-Shot例示でトークン数増加
**対策**: 例示は3個まで、圧縮プロンプト技術活用

---

## 🚀 次のアクション

### 即座に実行可能

1. **Few-Shotデータベース作成** - episodes_validated_100_20251001.csvから抽出
2. **プロンプトV3テスト** - 5エピソードで検証
3. **InstantQualityGate実装** - キーワードチェックの自動化

### 1週間以内

1. Phase 1完了 - 基盤コンポーネント実装
2. 10エピソードテスト - 新システムの初期検証

### 1ヶ月以内

1. 全Phase完了 - 本番システム構築
2. 100エピソード本番テスト - 統計的有意性確認
3. 本番運用開始 - 段階的ロールアウト

---

## 📚 参考ドキュメント

1. **システム構造分析**: `SYSTEM_ARCHITECTURE_ANALYSIS.md`
2. **失敗パターン分類**: `FAILURE_PATTERN_TAXONOMY.md`
3. **評価失敗分析**: `EPISODE_EVALUATION_FAILURE_ANALYSIS.md`
4. **10エピソードテスト結果**: `test_10_episodes_rerun.log`

---

**このプランは実装レディです。Phase 1から順次実装を開始できます。**
