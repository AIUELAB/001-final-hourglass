# 超総合スコア（Super Total Score）設計書

**作成日**: 2026-01-05
**目的**: 複数の既存スコアを統合し「ユーザーが最も読みたい真のエピソード」を順位付け

---

## 1. リポジトリ調査結果

### 1.1 7軸/5軸の正規定義ファイル

| 定義 | ファイル | 内容 |
|------|----------|------|
| 7軸フィールド名 | `backend/app/utils/score_calculator.py` | `SEVEN_AXIS_FIELDS` |
| 5軸統合版定義 | `backend/app/utils/score_calculator.py` | `FIVE_AXIS_COMPOSITION` |
| 7軸重み | `scripts/score/episode_fame_v6/config.py` | `LLM_WEIGHTS` |

### 1.2 使うべき列名とスケール一覧

| 列名 | 分類 | スケール | 実測範囲 | 非空件数 |
|------|------|----------|----------|----------|
| 記憶性スコア | 7軸 | 0-10 | 6.0-9.0 | 10,252 |
| 共感性スコア | 7軸 | 0-10 | 5.0-9.2 | 10,252 |
| 意外性スコア | 7軸 | 0-10 | 5.0-8.7 | 10,252 |
| 生成品質スコア | 7軸 | 0-10 | 5.0-9.0 | 10,252 |
| 教育的価値 | 7軸 | 0-10 | 5.0-9.0 | 10,252 |
| ストーリー品質 | 7軸 | 0-10 | 5.8-8.5 | 10,252 |
| 事実密度 | 7軸 | 0-10 | 4.8-10.0 | 10,252 |
| 総合品質 | 5軸統合 | 0-10 | 5.5-9.0 | 10,252 |
| 感情インパクト | 5軸統合 | 0-10 | 5.0-7.7 | 10,252 |
| composite_score_5axis | 5軸総合 | 0-10 | 5.8-8.5 | 10,252 |
| celebrity_score_v2 | 人物有名度 | 0-1000 | 88-959 | 10,252 |
| episode_fame_v6 | EP有名度 | 0-100 | 27-117 | 10,252 |

### 1.3 既存「超総合」相当の実装

**`episode_fame_v6`** が最も近い概念：

```
episode_fame_v6 =
    person_fame × 0.30 (celebrity_score_v2 + sitelinks)
  + llm_quality × 0.25 (7軸加重平均)
  + historical_impact × 0.20 (キーワード + タイプ)
  + pv_signal × 0.15 (Wikipedia PV)
  + episode_bonus × 0.10 (エピソード数飽和)
  - penalty (ペナルティキーワード)
  - retrospective_penalty (回顧・抽象ペナルティ)
```

**課題**:
1. 0-100スケールで粒度が粗い
2. 事実密度・生成品質の「足切り」ゲートがない
3. 品質が低いのに有名だからで上位に来るリスク

---

## 2. 「超総合」設計案（推奨案）

### 2.1 設計方針

1. **ゲートファースト**: 品質基準を満たさないものは事前に足切り
2. **正規化統一**: 全スコアを0-1に正規化してから統合
3. **二重計上回避**: 7軸と5軸は7軸を主とし、5軸は使用しない
4. **出力スケール**: 0-1,000,000（百万）

### 2.2 正規化方法

**ロバストスケーリング**（中央値・四分位範囲ベース）を採用

```python
def robust_normalize(value, median, iqr):
    """
    ロバスト正規化（外れ値に強い）
    - median: 中央値
    - iqr: 四分位範囲（Q3 - Q1）
    """
    if iqr == 0:
        return 0.5
    z = (value - median) / iqr
    # シグモイド変換で0-1にマッピング
    return 1 / (1 + math.exp(-z))
```

**採用理由**:
- 外れ値（celebrity_score_v2の極端な値など）に強い
- 新規エピソード追加時に既存ランキングが大きく揺れない
- パーセンタイルクリップより滑らかな分布

### 2.3 ゲート/ペナルティ設計

```
┌─────────────────────────────────────────────────────────┐
│  HARD GATE（足切り）                                    │
├─────────────────────────────────────────────────────────┤
│  事実密度 < 6.0  →  スコア = 0（除外）                 │
│  生成品質スコア < 6.0  →  スコア = 0（除外）          │
│  verification_status = "rejected"  →  スコア = 0       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  SOFT PENALTY（減点）                                   │
├─────────────────────────────────────────────────────────┤
│  事実密度 6.0-7.0  →  乗数 0.85                        │
│  生成品質 6.0-7.0  →  乗数 0.85                        │
│  回顧・抽象パターン  →  乗数 0.80-0.95                  │
│  他者参照パターン  →  乗数 0.90                        │
└─────────────────────────────────────────────────────────┘
```

### 2.4 最終計算式

```
super_total_score = gate_check(episode) × (
    0.35 × celebrity_fame_norm      # 人物有名度
  + 0.30 × episode_fame_norm        # エピソード有名度
  + 0.25 × quality_score_norm       # 品質スコア（7軸加重平均）
  + 0.10 × historical_impact_norm   # 歴史的インパクト
) × penalty_multiplier × 1,000,000
```

### 2.5 重み案と根拠

| コンポーネント | 重み | 根拠 |
|----------------|------|------|
| celebrity_fame | 35% | 「誰の話か」が読者の関心の最大要因 |
| episode_fame | 30% | エピソード自体の認知度（Wikipediaヒット等） |
| quality_score | 25% | 読みやすさ・教訓の深さ |
| historical_impact | 10% | 偉業キーワード（ノーベル賞等）のブースト |

**7軸→quality_score の加重平均**:
```python
QUALITY_WEIGHTS = {
    "記憶性スコア": 0.25,      # 最重要: 記憶に残るか
    "意外性スコア": 0.18,      # 興味を引くか
    "ストーリー品質": 0.15,    # 読みやすさ
    "教育的価値": 0.15,        # 学びがあるか
    "事実密度": 0.12,          # 具体性（ゲート済み）
    "共感性スコア": 0.10,      # 感情的響き
    "生成品質スコア": 0.05,    # 文章品質（ゲート済み）
}
```

---

## 3. 代替案

### 3.1 案B: 学習toランキング（Learning to Rank）

**概要**: ユーザー行動データから重みを学習

```
入力: 特徴ベクトル [celebrity, episode_fame, 7軸, ...]
出力: ペアワイズ比較による順位予測
モデル: LightGBM Ranker / XGBoost Ranker
```

| 項目 | 内容 |
|------|------|
| 採用条件 | クリック/滞在時間データが10,000件以上 |
| メリット | ユーザー嗜好を直接反映 |
| デメリット | 初期は学習データ不足、コールドスタート問題 |
| 運用コスト | 中〜高（再学習パイプライン必要） |

### 3.2 案C: AHP（階層分析法）

**概要**: 専門家の一対比較から重みを導出

```
有名度 vs 品質 → 3:1 (有名度がやや重要)
品質 vs 歴史的 → 2:1
...
→ 固有ベクトルから重み算出
```

| 項目 | 内容 |
|------|------|
| 採用条件 | 複数の評価者による一致した判断 |
| メリット | 理論的に整合性が保証される |
| デメリット | 主観的、評価者のバイアス |
| 運用コスト | 低（一度決めれば固定） |

### 3.3 案D: ハイブリッド（推奨案 + 学習）

**概要**: 初期は推奨案で運用、データ蓄積後に学習で微調整

```
Phase 1: ルールベース（本設計案）
Phase 2: A/Bテストで重み調整
Phase 3: 学習モデルで重み最適化
```

| 項目 | 内容 |
|------|------|
| 採用条件 | 段階的に行動データを収集 |
| メリット | 初期から動作、後から改善可能 |
| デメリット | 設計の複雑化 |
| 運用コスト | 中（フェーズごとに増加） |

---

## 4. 新エピソード追加時の運用設計

### 4.1 正規化パラメータ

**固定方式**（推奨）:
- 初回計算時にmedian/IQRを保存
- 新規エピソードは既存パラメータで正規化
- 月次で再計算、閾値超過時のみ更新

```python
NORMALIZATION_PARAMS = {
    "version": "v1.0.0",
    "computed_at": "2026-01-05",
    "celebrity_score_v2": {"median": 513.9, "iqr": 280.5},
    "episode_fame_v6": {"median": 63.9, "iqr": 22.1},
    ...
}
```

### 4.2 バージョニング設計

```
/configs/super_total_score/
├── v1.0.0.json          # 初期重み・閾値
├── v1.1.0.json          # ゲート調整
├── v2.0.0.json          # 学習導入後
└── current -> v1.0.0.json
```

**変更履歴の記録項目**:
- 変更日時
- 変更理由
- 影響範囲（再計算が必要なエピソード数）
- 承認者

---

## 5. 小さな数値例

### 例1: 大谷翔平「二刀流MVP」エピソード

```
入力:
  celebrity_score_v2 = 850 (top 10%)
  episode_fame_v6 = 95
  記憶性スコア = 8.5
  意外性スコア = 8.0
  事実密度 = 9.5
  生成品質スコア = 8.0
  ...

Step 1: ゲートチェック
  事実密度 9.5 >= 6.0 ✓
  生成品質 8.0 >= 6.0 ✓
  → PASS

Step 2: 正規化（ロバスト）
  celebrity_norm = sigmoid((850 - 513.9) / 280.5) = 0.83
  episode_fame_norm = sigmoid((95 - 63.9) / 22.1) = 0.87
  quality_norm = 7軸加重平均 / 10 = 0.81

Step 3: 統合
  raw = 0.35×0.83 + 0.30×0.87 + 0.25×0.81 + 0.10×0.90
    = 0.29 + 0.26 + 0.20 + 0.09 = 0.84

Step 4: ペナルティ
  回顧パターンなし → 乗数 1.0

Step 5: スケーリング
  super_total = 0.84 × 1.0 × 1,000,000 = 840,000
```

### 例2: 無名人物「曖昧な回想」エピソード

```
入力:
  celebrity_score_v2 = 120 (bottom 20%)
  episode_fame_v6 = 35
  記憶性スコア = 6.0
  事実密度 = 5.5  ← ゲートに引っかかる
  生成品質スコア = 6.5
  episode_text = "人生を振り返り、静かな日々を送っていた"

Step 1: ゲートチェック
  事実密度 5.5 < 6.0 ✗
  → REJECT (スコア = 0)
```

---

## 6. 実装案（Python）

```python
"""
超総合スコア算出モジュール

使用方法:
    from super_total_scorer import SuperTotalScorer

    scorer = SuperTotalScorer(all_episodes)
    score, explanation = scorer.calculate(episode_row)
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class SuperTotalConfig:
    """設定"""
    # ゲート閾値
    min_factual_density: float = 6.0
    min_generation_quality: float = 6.0

    # 重み
    weight_celebrity: float = 0.35
    weight_episode_fame: float = 0.30
    weight_quality: float = 0.25
    weight_historical: float = 0.10

    # 出力スケール
    output_scale: int = 1_000_000


@dataclass
class ScoreResult:
    """算出結果"""
    score: float
    passed_gate: bool
    gate_reason: Optional[str]
    breakdown: dict
    penalties: list


class SuperTotalScorer:
    """超総合スコア算出器"""

    # 7軸重み
    QUALITY_WEIGHTS = {
        "記憶性スコア": 0.25,
        "意外性スコア": 0.18,
        "ストーリー品質": 0.15,
        "教育的価値": 0.15,
        "事実密度": 0.12,
        "共感性スコア": 0.10,
        "生成品質スコア": 0.05,
    }

    def __init__(self, all_episodes: list, config: SuperTotalConfig = None):
        self.config = config or SuperTotalConfig()
        self._compute_normalization(all_episodes)

    def _compute_normalization(self, episodes: list):
        """正規化パラメータを計算"""
        def stats(values):
            arr = np.array([v for v in values if v is not None and not np.isnan(v)])
            if len(arr) == 0:
                return 0, 1
            return np.median(arr), np.percentile(arr, 75) - np.percentile(arr, 25)

        celeb = [self._safe_float(e.get("celebrity_score_v2")) for e in episodes]
        fame = [self._safe_float(e.get("episode_fame_v6")) for e in episodes]

        self.celeb_median, self.celeb_iqr = stats(celeb)
        self.fame_median, self.fame_iqr = stats(fame)

    def _safe_float(self, val, default=None) -> Optional[float]:
        """安全な型変換"""
        if val is None or val == "":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def _robust_normalize(self, value: float, median: float, iqr: float) -> float:
        """ロバスト正規化（シグモイド）"""
        if iqr == 0 or value is None:
            return 0.5
        z = (value - median) / iqr
        return 1 / (1 + math.exp(-z))

    def _check_gate(self, row: dict) -> Tuple[bool, Optional[str]]:
        """ゲートチェック"""
        fact = self._safe_float(row.get("事実密度"), 0)
        gen = self._safe_float(row.get("生成品質スコア"), 0)

        if fact < self.config.min_factual_density:
            return False, f"事実密度 {fact:.1f} < {self.config.min_factual_density}"
        if gen < self.config.min_generation_quality:
            return False, f"生成品質 {gen:.1f} < {self.config.min_generation_quality}"

        status = row.get("verification_status", "")
        if status == "rejected":
            return False, "verification_status = rejected"

        return True, None

    def _calc_quality_score(self, row: dict) -> float:
        """7軸加重平均"""
        total_weight = 0
        weighted_sum = 0

        for field, weight in self.QUALITY_WEIGHTS.items():
            val = self._safe_float(row.get(field))
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight

        if total_weight == 0:
            return 0.5
        return (weighted_sum / total_weight) / 10  # 0-1に正規化

    def _calc_penalty(self, row: dict) -> Tuple[float, list]:
        """ペナルティ乗数を計算"""
        penalties = []
        multiplier = 1.0

        # 事実密度ソフトペナルティ
        fact = self._safe_float(row.get("事実密度"), 10)
        if 6.0 <= fact < 7.0:
            multiplier *= 0.85
            penalties.append(f"事実密度ソフトペナルティ ({fact:.1f})")

        # 生成品質ソフトペナルティ
        gen = self._safe_float(row.get("生成品質スコア"), 10)
        if 6.0 <= gen < 7.0:
            multiplier *= 0.85
            penalties.append(f"生成品質ソフトペナルティ ({gen:.1f})")

        # 回顧パターン（簡易チェック）
        text = row.get("episode_text", "")
        if "人生を振り返" in text or "静かな日々を送" in text:
            multiplier *= 0.80
            penalties.append("回顧・抽象パターン")

        return multiplier, penalties

    def calculate(self, row: dict) -> ScoreResult:
        """超総合スコアを計算"""
        # ゲートチェック
        passed, reason = self._check_gate(row)
        if not passed:
            return ScoreResult(
                score=0,
                passed_gate=False,
                gate_reason=reason,
                breakdown={},
                penalties=[]
            )

        # 正規化
        celeb_norm = self._robust_normalize(
            self._safe_float(row.get("celebrity_score_v2"), 0),
            self.celeb_median, self.celeb_iqr
        )
        fame_norm = self._robust_normalize(
            self._safe_float(row.get("episode_fame_v6"), 0),
            self.fame_median, self.fame_iqr
        )
        quality_norm = self._calc_quality_score(row)

        # 歴史的インパクト（episode_fame_v6の一部を再利用）
        historical_norm = self._safe_float(row.get("episode_importance_score"), 50) / 100

        # 統合
        raw = (
            self.config.weight_celebrity * celeb_norm
            + self.config.weight_episode_fame * fame_norm
            + self.config.weight_quality * quality_norm
            + self.config.weight_historical * historical_norm
        )

        # ペナルティ
        penalty_mult, penalties = self._calc_penalty(row)

        # 最終スコア
        final = raw * penalty_mult * self.config.output_scale

        return ScoreResult(
            score=round(final, 0),
            passed_gate=True,
            gate_reason=None,
            breakdown={
                "celebrity_norm": round(celeb_norm, 3),
                "fame_norm": round(fame_norm, 3),
                "quality_norm": round(quality_norm, 3),
                "historical_norm": round(historical_norm, 3),
                "raw_score": round(raw, 4),
                "penalty_multiplier": round(penalty_mult, 2),
            },
            penalties=penalties
        )
```

---

## 7. 検証方法

### 7.1 期待する上位の性質

| 順位帯 | 期待される性質 |
|--------|----------------|
| Top 50 | ノーベル賞・世界初・オリンピック金メダル等を含む |
| Top 100 | 事実密度 >= 7.0、生成品質 >= 7.0 |
| Top 500 | 有名人物（celebrity_score >= 500）が80%以上 |

### 7.2 重み調整手順

1. **初期設定**: 本設計の推奨重みで全エピソード計算
2. **サンプリング**: Top 100 / 下位100 / ランダム100を抽出
3. **人手評価**: 「読みたい度」1-5で評価
4. **相関分析**: スコアと人手評価の相関係数を計算
5. **重み微調整**: 低相関コンポーネントの重みを増減

### 7.3 失敗パターンと対策

| パターン | 原因 | 対策 |
|----------|------|------|
| 扇情的だが事実薄い | 意外性は高いが事実密度が低い | 事実密度ゲート (< 6.0 = 除外) |
| 有名人のつまらないEP | celebrity高だけで上位 | quality重みを25%確保 |
| 無名人の偉業が埋もれる | celebrity低で下位に | historical_impactで偉業キーワードをブースト |
| 回顧・抽象的なEP | 具体的イベントがない | 回顧パターンペナルティ |

---

## 8. 追加で分かると精度が上がる情報

1. **ユーザー行動データ**: クリック率、滞在時間、保存率
2. **A/Bテスト結果**: 上位表示時のエンゲージメント差
3. **評価者コメント**: なぜこのエピソードを「読みたい」と思ったか
4. **人物カテゴリ**: 「偉人」「芸能人」「アスリート」などによる嗜好差

**仮定で進めた点**:
- 「偉業」エピソードを優先する方針（ユーザー要求より）
- 事実密度6.0未満を除外（厳格な足切り）
- 初期重みは経験則ベース（後から調整可能）

---

## 9. 検証結果と調整案

### 9.1 初期設計の検証結果

**全体Top 30**:
1. アインシュタイン: 1,187,505
2-3. エルヴィス・プレスリー: 1,091,236 / 1,085,085
4-5. ジミ・ヘンドリックス: 1,077,742 / 1,070,414
6. バラク・オバマ: 1,067,253
...
30. 阿部詩（オリンピック金メダル）: 1,005,104

**大谷翔平の順位**:
- 「50-50達成」エピソード: 813,569（Top 100内だがTop 30外）

**偉業キーワード含むTop 5**:
1. 阿部詩（オリンピック金メダル）: 1,005,104
2. ヤン・ルカン（ノーベル賞）: 996,788
3. 大谷翔平（史上初50-50）: 813,569
4. アインシュタイン（ノーベル賞）: 776,344
5. 大江健三郎（ノーベル賞）: 761,185

### 9.2 問題点

| 問題 | 原因 | 影響 |
|------|------|------|
| 音楽アーティストが上位独占 | celebrity_scoreが高い傾向 | 偉業エピソードが埋もれる |
| 大谷翔平がTop30外 | episode_fameが相対的に低い | ユーザー期待との乖離 |
| ノーベル賞エピソードが分散 | historical_impact重み10%と低い | 偉業の優先度不足 |

### 9.3 調整案（v1.1.0 候補）

**案A: 偉業キーワードダイレクトブースト**

```python
# 偉業キーワードに+5〜10%のダイレクトブースト
ACHIEVEMENT_BOOST = {
    "ノーベル賞": 0.10,
    "世界初": 0.08,
    "史上初": 0.08,
    "オリンピック金メダル": 0.08,
    "50本塁打": 0.05,
    "二刀流": 0.05,
}

# 計算式に追加
raw = (base_score) × (1 + achievement_boost)
```

**案B: historical_impact重みアップ**

```python
# 現行
weight_historical = 0.10

# 調整案
weight_historical = 0.20  # 10% → 20%
weight_celebrity = 0.30   # 35% → 30%（減）
```

**案C: celebrity_scoreの上限キャップ**

```python
# celebrity_normの上限を0.85に
celebrity_norm = min(0.85, robust_normalize(celeb_score))
```

### 9.4 推奨：案A + 案B の組み合わせ

理由:
- 偉業キーワードに明示的なブーストで「偉業優先」を実現
- historical_impact重み増加で偉業の底上げ
- celebrity上限キャップは人物多様性を損なうリスクあり（見送り）

**調整後の期待効果**:
- 大谷翔平「50-50達成」: 813,569 → 約950,000（Top 30 入り）
- ノーベル賞エピソード: 全体的に+10-15%

---

## 10. 次のステップ

1. **v1.1.0 実装**: 案A + 案B の重み調整を実装
2. **A/Bテスト**: 調整前後でTop 50の人物多様性を比較
3. **ユーザーフィードバック**: 「読みたい度」評価を収集
4. **学習準備**: 行動データ収集パイプラインの設計

---

**作成完了**: 2026-01-05
**設計書パス**: `src/reports/super_total_score_design.md`
**実装パス**: `scripts/score/super_total_scorer.py`
