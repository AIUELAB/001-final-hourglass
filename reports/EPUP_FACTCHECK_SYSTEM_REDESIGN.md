# EPUP ファクトチェックシステム 包括的改善設計書

**作成日**: 2025-12-10
**分析者**: ファクトチェック設計責任者 / データ品質・安全性レビュー担当

---

## エグゼクティブサマリー

### 発見された深刻な問題

| 問題カテゴリ | 深刻度 | 影響範囲 | 即座の対応 |
|-------------|--------|----------|-----------|
| 生年DB×フェイルオープン設計 | 🔴 Critical | 未知の人物全て | 必須 |
| 事実密度スコア未活用 | 🔴 Critical | 4,029件 (30.7%) | 必須 |
| 意外性必須プロンプト | 🟠 High | 全新規生成 | 推奨 |
| ファクトチェック層の欠落 | 🔴 Critical | 12,554件 (95%+) | 必須 |

### 現状の数値

```
総エピソード数:     13,120件
ファクトチェック済み:   325件 ( 2.5%)
未チェック:        12,554件 (95.7%)
事実密度<4.0:       4,029件 (30.7%)
高リスク（低スコア+低密度）: 1,028件 ( 7.8%)
```

---

## 第1章: 問題詳細分析

### 1.1 生年データベース × フェイルオープン設計

#### 現状コード分析

**ファイル**: `src/birth_year_database.py`

```python
# 行66-70: 問題のあるフェイルオープン設計
def get_birth_year(person_name: str) -> Optional[int]:
    if person_name in BIRTH_YEARS:
        return BIRTH_YEARS[person_name]
    # partial match...
    return None  # ← 不明な人物はNoneを返す

def validate_episode_age(...):
    birth_year = get_birth_year(person_name)
    if birth_year is None:
        return True, f"WARN: 生年データなし（{person_name}）"  # ← フェイルオープン！
```

**ファイル**: `scripts/detect_and_delete_future_episodes.py`

```python
# 行66-67: 不明な人物はスキップ
birth_year = get_birth_year(person_name)
if birth_year is None:
    continue  # ← 黙ってスキップ（危険）
```

#### 根本的問題

1. **カバレッジ不足**: 約380人のみ登録 → 未登録者は全てスルー
2. **フェイルオープン**: 未知=許可という危険な設計思想
3. **EP-000018事例**: 桜井日奈子(1997年生)の66歳(2063年!)エピソードが生成・保存された

#### 推奨される改善

**A. フェイルセーフ設計への移行**

```python
def validate_episode_age(person_name: str, age: int) -> tuple[bool, str]:
    birth_year = get_birth_year(person_name)

    if birth_year is None:
        # フェイルセーフ: 不明な人物は追加検証を要求
        if age >= 60:
            return False, f"BLOCK: 高齢エピソード（{age}歳）で生年データなし"
        elif age <= 10:
            return False, f"BLOCK: 幼少期エピソード（{age}歳）で生年データなし"
        else:
            return True, f"WARN: 生年データなし（要手動確認）"

    # 既存の検証ロジック
    current_year = datetime.now().year
    episode_year = birth_year + age
    if episode_year > current_year:
        return False, f"BLOCK: 未来エピソード（{episode_year}年）"

    return True, "OK"
```

**B. 動的生年取得層の追加**

```python
def get_birth_year_with_fallback(person_name: str) -> tuple[Optional[int], str]:
    # 1. ローカルDB
    if person_name in BIRTH_YEARS:
        return BIRTH_YEARS[person_name], "local_db"

    # 2. Wikipedia API（オプション）
    birth_year = fetch_from_wikipedia(person_name)
    if birth_year:
        # キャッシュに追加
        BIRTH_YEARS[person_name] = birth_year
        return birth_year, "wikipedia"

    # 3. LLMに問い合わせ
    birth_year = ask_llm_for_birth_year(person_name)
    if birth_year:
        return birth_year, "llm_estimate"

    return None, "unknown"
```

---

### 1.2 事実密度スコアの未活用

#### 現状分析

**事実密度スコア分布（13,120件）**

```
スコア帯    件数     割合      状態
0-2      1,011    7.7%     🔴 極めて低品質
2-3      1,355   10.3%     🔴 低品質
3-4      1,663   12.7%     🟠 要改善
4-5      2,114   16.1%     🟡 標準下限
5-6      2,165   16.5%     🟢 標準
6-7      1,739   13.3%     🟢 良好
7-8      1,448   11.0%     🟢 高品質
8-10     1,618   12.3%     🟢 優秀
-------------------------------------------------
平均: 5.15 / 中央値: 5.05
```

#### 問題点

1. **品質ゲート不在**: `pipeline_layer2_evaluate.py`は`composite_score`のみ使用
2. **低品質の放置**: 事実密度 < 4.0 が 30.7% も存在
3. **高リスク群**: 低composite × 低事実密度 = 1,028件

#### 改善設計: 多層品質ゲート

**ファイル**: `scripts/pipeline_layer2_evaluate.py` への追加

```python
# 現状（単一ゲート）
LAYER2_CONFIG = {
    "auto_accept_threshold": 600,
    "rejection_threshold": 400,
}

# 改善案（多層ゲート）
QUALITY_GATES = {
    "composite_score": {
        "auto_accept": 600,
        "manual_review": 400,
        "auto_reject": 300,
    },
    "事実密度": {
        "required_minimum": 3.5,  # これ以下は自動リジェクト
        "preferred_minimum": 5.0,  # これ以下は警告
    },
    "意外性スコア": {
        "fiction_warning": 8.5,  # 高すぎる意外性は架空の可能性
    },
    "verifiability": {
        "required_minimum": 0.5,  # 検証可能性スコア
    }
}

def evaluate_episode(episode: Dict) -> EvaluationResult:
    # 多層ゲートチェック

    # Gate 1: 事実密度チェック（最優先）
    fact_density = float(episode.get("事実密度", 0))
    if fact_density < QUALITY_GATES["事実密度"]["required_minimum"]:
        return EvaluationResult(
            decision="REJECT",
            reason=f"事実密度不足: {fact_density:.1f} < 3.5"
        )

    # Gate 2: 意外性スコアの異常検知
    surprise_score = float(episode.get("意外性スコア", 0))
    if surprise_score > QUALITY_GATES["意外性スコア"]["fiction_warning"]:
        return EvaluationResult(
            decision="REVIEW",
            reason=f"意外性過多（架空の可能性）: {surprise_score:.1f}"
        )

    # Gate 3: 総合スコア
    composite = float(episode.get("composite_score", 0))
    if composite >= QUALITY_GATES["composite_score"]["auto_accept"]:
        return EvaluationResult(decision="ACCEPT", reason="高品質")
    elif composite < QUALITY_GATES["composite_score"]["auto_reject"]:
        return EvaluationResult(decision="REJECT", reason="低品質")
    else:
        return EvaluationResult(decision="REVIEW", reason="手動確認推奨")
```

---

### 1.3 「意外性必須」プロンプトの問題

#### 問題のあるプロンプト箇所

**ファイル**: `scripts/pipeline_layer1_generate.py` (行212-232)

```python
# 問題のあるプロンプト
prompt = f"""「{person_name}」（{category}）の{age}歳のときのエピソードを生成してください。

【意外性必須】以下のいずれかを必ず含めてください：
  - 一般的なイメージと正反対の行動や考え
  - 予想外の転機（挫折からの復活、意外な出会い）
  - 知られざる一面や葛藤
  - 時代を先取りした先見性
"""
```

**ファイル**: `scripts/improve_low_quality_episodes.py` (行91-96)

```python
axis_instructions = {
    "意外性スコア": """
【意外性を劇的に高めてください】
- 一般的なイメージと正反対の側面を追加
- 逆転のエピソード（例: 絶望的状況からの復活）
- 「誰もが驚いたことに」「実は〜」「周囲の予想に反して」などの表現を使用
"""
}
```

#### リスク分析

| リスク | 説明 | 発生確率 |
|--------|------|----------|
| 架空エピソード生成 | 「意外性」を満たすため存在しない出来事を創作 | 高 |
| 事実の誇張 | 実際の出来事を劇的に脚色 | 中〜高 |
| 時系列の改変 | ストーリー性のために年齢・時期を変更 | 中 |
| 人物像の歪曲 | 「正反対の行動」を強調し本来の人物像から乖離 | 中 |

#### 改善プロンプト設計

```python
# 改善版プロンプト（事実優先）
FACT_FIRST_PROMPT = """「{person_name}」（{category}）の{age}歳のときの事実に基づくエピソードを生成してください。

【最重要：事実性】
- 検証可能な事実のみを記述してください
- 具体的な年号、数値、固有名詞を含めてください
- 出典が確認できる業績・出来事を優先してください
- 「おそらく」「だったと言われている」などの推測表現は避けてください

【人物名】必ず「{person_name}」を使用（グループ名・略称禁止）

【形式】「あなたと同じ{age}歳のとき、{person_name}は〜」で開始

【品質基準】
- 具体的な数値（年号、記録、順位など）を2つ以上含める
- 事実として確認できる出来事を中心に構成
- 感情や葛藤の描写は事実に基づく範囲で

【禁止事項】
- 架空の出来事の創作
- 「意外にも」「実は」「知られざる」などの誇張表現
- 検証不可能な内面描写の過度な創作

【文字数】200-350文字程度
"""

# 意外性が必要な場合の安全な代替指示
SAFE_INTEREST_PROMPT = """
【興味深さの演出】（意外性の代わり）
- 時代背景を踏まえた文脈で興味を引く
- 具体的な数値・記録でインパクトを出す
- 事実の組み合わせで発見を促す
"""
```

---

### 1.4 自動ファクトチェック層の欠落

#### 現状

- `fact_checker.py` は**完成しているが統合されていない**
- 12,554件(95%+)が「未チェック」状態
- パイプラインにファクトチェック工程がない

#### 既存ファクトチェッカーの分析

**ファイル**: `fact_checker.py`

```python
class EpisodeFactChecker:
    def check_episode(self, person_name, age, episode_text, category) -> FactCheckResult:
        # LLMベースの事実確認
        # 返値: status, confidence, verification_sources, notes, corrections
```

**問題点**:
1. パイプラインに統合されていない
2. 高コスト（1件あたりLLM呼び出し1回）
3. バッチ処理に対応していない

#### 改善設計: 3層ファクトチェックアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    エピソード生成                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 高速ルールベースチェック（コスト: 0）              │
│  ├─ 生年検証（フェイルセーフ）                              │
│  ├─ フォーマット検証（名前一致など）                        │
│  ├─ 事実密度スコア閾値チェック                              │
│  └─ 禁止パターン検出（メタ表現、架空宣言など）              │
│                                                             │
│  → PASS: Layer 2へ / FAIL: 即リジェクト                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: 統計的異常検知（コスト: 低）                       │
│  ├─ 意外性スコア異常検知（> 8.5 → 架空の疑い）              │
│  ├─ 事実密度/意外性の逆相関チェック                         │
│  ├─ 類似エピソード重複検出                                  │
│  └─ カテゴリ別の典型パターン逸脱検出                        │
│                                                             │
│  → PASS: Layer 3へ / SUSPICIOUS: Layer 3で重点チェック      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: LLMファクトチェック（コスト: 高 → サンプリング）   │
│  ├─ 全量チェック対象:                                       │
│  │   ├─ Layer 2でSUSPICIOUS判定のもの                      │
│  │   ├─ 高齢(60+)エピソード                                │
│  │   └─ 新規人物のエピソード                               │
│  ├─ サンプリングチェック:                                   │
│  │   └─ 通常エピソードの10%をランダムサンプリング          │
│  └─ 既存fact_checker.pyを活用                               │
│                                                             │
│  → VERIFIED / NEEDS_REVIEW / FACTUAL_ERROR                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   品質ゲート判定                             │
│  ├─ ACCEPT: 本番CSVに追加                                   │
│  ├─ REVIEW: 手動確認キューに追加                            │
│  └─ REJECT: 破棄（再生成または削除）                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 第2章: 具体的実装計画

### 2.1 Phase 1: 緊急対応（既存データの品質向上）

#### タスク1.1: 低品質エピソードの特定と処理

```bash
# 実行コマンド
python scripts/detect_low_quality_episodes.py --threshold 3.5 --output reports/low_quality_candidates.csv
```

**対象**: 事実密度 < 3.5 のエピソード（約2,366件）

**処理方針**:
- 事実密度 < 2.0: 削除候補
- 事実密度 2.0-3.5: 改稿候補

#### タスク1.2: 未来エピソードの完全スキャン

```python
# scripts/comprehensive_future_scan.py
def scan_all_episodes_for_future():
    """全エピソードを再スキャン（LLM生年推定を使用）"""
    for episode in df.iterrows():
        person_name = episode['person_name']
        age = int(episode['age'])

        # ローカルDBになければLLMに問い合わせ
        birth_year, source = get_birth_year_with_fallback(person_name)

        if birth_year:
            episode_year = birth_year + age
            if episode_year > 2025:
                flag_as_future_episode(episode)
```

### 2.2 Phase 2: パイプライン改修

#### タスク2.1: `pipeline_layer2_evaluate.py` に多層ゲート追加

```python
# 追加するインポート
from fact_checker import EpisodeFactChecker
from src.birth_year_database import validate_episode_age

# 新しい評価関数
def multi_layer_evaluate(episode: Dict) -> EvaluationResult:
    """多層品質ゲート評価"""

    # Layer 1: ルールベース
    rule_result = rule_based_check(episode)
    if rule_result.decision == "REJECT":
        return rule_result

    # Layer 2: 統計的異常検知
    anomaly_result = anomaly_detection(episode)
    if anomaly_result.is_suspicious:
        episode['_requires_fact_check'] = True

    # Layer 3: LLMファクトチェック（必要な場合のみ）
    if episode.get('_requires_fact_check') or should_sample_check():
        fact_result = fact_checker.check_episode(
            episode['person_name'],
            episode['age'],
            episode['episode_text'],
            episode['category']
        )
        if fact_result.status == "事実誤認":
            return EvaluationResult(decision="REJECT", reason="事実誤認検出")

    # 最終判定
    return final_evaluation(episode)
```

#### タスク2.2: `pipeline_layer1_generate.py` のプロンプト改修

- 「意外性必須」→「事実優先」に変更
- 禁止表現リストを追加
- 生成時に事実密度の事前チェックを追加

### 2.3 Phase 3: 新規スクリプト作成

#### `scripts/integrated_fact_checker.py`（新規）

```python
#!/usr/bin/env python3
"""
統合ファクトチェッカー

3層ファクトチェックを実装し、パイプラインに組み込む
"""

class IntegratedFactChecker:
    def __init__(self):
        self.rule_checker = RuleBasedChecker()
        self.anomaly_detector = AnomalyDetector()
        self.llm_checker = EpisodeFactChecker(api_key)

    def check(self, episode: Dict) -> FactCheckResult:
        # Layer 1
        if not self.rule_checker.check(episode):
            return FactCheckResult(status="RULE_VIOLATION", ...)

        # Layer 2
        anomaly_score = self.anomaly_detector.score(episode)

        # Layer 3 (条件付き)
        if anomaly_score > 0.7 or self.should_full_check(episode):
            return self.llm_checker.check_episode(...)

        return FactCheckResult(status="PASS", ...)
```

---

## 第3章: 修正対象ファイル一覧

| ファイル | 修正内容 | 優先度 |
|----------|----------|--------|
| `src/birth_year_database.py` | フェイルセーフ設計への変更 | P0 |
| `scripts/pipeline_layer2_evaluate.py` | 多層品質ゲート追加 | P0 |
| `scripts/pipeline_layer1_generate.py` | プロンプト改修 | P1 |
| `scripts/improve_low_quality_episodes.py` | 意外性指示の削除 | P1 |
| `scripts/improve_existing_episodes.py` | 意外性指示の削除 | P1 |
| `scripts/integrated_fact_checker.py` | 新規作成 | P1 |
| `scripts/detect_low_quality_episodes.py` | 新規作成 | P2 |
| `scripts/comprehensive_future_scan.py` | 新規作成 | P2 |

---

## 第4章: 品質目標と検証計画

### 品質目標

| 指標 | 現状 | 目標 | 期限 |
|------|------|------|------|
| ファクトチェック済み率 | 2.5% | 50%以上 | 2週間 |
| 事実密度 < 3.5 の割合 | 18.0% | 5%以下 | 2週間 |
| 未来エピソード | 1件以上 | 0件 | 即時 |
| 高リスクエピソード | 1,028件 | 100件以下 | 2週間 |

### 検証計画

1. **Phase 1完了後**: `scripts/quality_audit.py` で全体品質レポート生成
2. **Phase 2完了後**: 新規生成10件でフルフロー検証
3. **継続監視**: 週次で品質指標をダッシュボードに表示

---

## 第5章: EPUPシステム総合評価

### 現状評価

| 項目 | スコア | 評価 |
|------|--------|------|
| フォーマット準拠率 | 97.0% | 🟢 良好 |
| 平均composite_score | 602.1 | 🟢 良好 |
| 名前-内容一致率 | 93.2% | 🟡 要改善 |
| ファクトチェック率 | 2.5% | 🔴 危機的 |
| 事実密度品質 | 69.3% (≥4.0) | 🟡 要改善 |

### 構造的課題

1. **生成偏重・検証軽視**: 生成パイプラインは充実しているが、検証層が弱い
2. **品質指標の分断**: 7軸スコアが計算されるが、ゲートとして活用されていない
3. **フェイルオープン文化**: 不明時に「通す」設計が随所に見られる
4. **LLMへの過信**: 生成されたエピソードの事実性をLLMに任せきり

### 総合評価: C（要大幅改善）

**良い点**:
- 高いフォーマット準拠率
- 7軸評価システムの存在
- fact_checker.pyの実装済み

**深刻な課題**:
- ファクトチェック率2.5%は許容不可
- 30.7%が低事実密度で本番稼働中
- フェイルオープン設計の危険性

---

## 付録: 即時実行コマンド

```bash
# 1. 低品質エピソードの検出
./venv/bin/python -c "
import pandas as pd
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')
low_quality = df[df['事実密度'] < 3.5]
print(f'低品質エピソード: {len(low_quality)}件')
low_quality[['episode_id', 'person_name', 'age', '事実密度', 'composite_score']].to_csv('reports/low_quality_candidates.csv', index=False)
"

# 2. 高リスクエピソードの抽出
./venv/bin/python -c "
import pandas as pd
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')
high_risk = df[(df['composite_score'] < 500) & (df['事実密度'] < 4.0)]
print(f'高リスクエピソード: {len(high_risk)}件')
high_risk[['episode_id', 'person_name', 'age', '事実密度', 'composite_score', 'episode_text']].to_csv('reports/high_risk_episodes.csv', index=False)
"

# 3. ファクトチェック状況の確認
./venv/bin/python -c "
import pandas as pd
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv', encoding='utf-8-sig')
print(df['fact_check_result'].fillna('未チェック').value_counts())
"
```

---

**文書終了**

作成: 2025-12-10
最終更新: 2025-12-10
