# 有名エピソードランキング v2 設計案

作成日: 2026-01-02
ステータス: **承認待ち**

---

## 1. 現状の問題（Phase A 調査結果）

| バージョン | Top100多様性 | 主要問題 |
|-----------|-------------|----------|
| v1 | 87人/100件 | テック偏重、感銘度無視 |
| v2 | 65人/100件 | 同一人物集中（偏差制御未実装） |
| v4 | 57人/100件 | 壊滅的集中（北斎20件/100件） |

**結論**: 現行v2/v4は「同一人物制限」が未実装のため機能していない。

---

## 2. 特徴量定義

### 2.1 使用する特徴量

| 特徴量 | 取得元 | キャッシュ | 更新頻度 |
|--------|--------|-----------|----------|
| **人物PV** | Wikipedia pageviews API | `preserved/cache/pv_cache.json` | 月次 or 手動 |
| **sitelinks** | Wikidata API (既存) | CSVカラム `sitelinks_count` | 既存データ使用 |
| **celebrity_score_v2** | 既存算出済み | CSVカラム | 既存データ使用 |
| **LLM品質** | 7軸スコア (既存) | CSVカラム | 既存データ使用 |
| **エピソード数** | CSV集計 | - | 既存データ使用 |
| **Google検索** | ★有料★ 要承認 | `preserved/cache/google_cache.json` | キャッシュ優先 |

### 2.2 取得が必要な新規データ

- **Wikipedia PV**: 約2,000人物分（無料API、レート制限あり）
- **Google検索**: ★有料★ 約2,000クエリ × $0.005 = $10程度

**★Google検索APIについて**: 既存の `fame_score_v3` で一部キャッシュ済み。追加取得は要承認。

---

## 3. 重み案（3パターン比較）

### 案A: バランス重視（推奨）

```python
WEIGHTS = {
    "person_fame": 0.30,      # celebrity_score_v2 + sitelinks
    "llm_quality": 0.25,      # LLM 7軸加重平均
    "historical_impact": 0.20, # キーワード + タイプボーナス
    "pv_signal": 0.15,        # Wikipedia PV (月間)
    "episode_bonus": 0.10,    # エピソード数飽和ボーナス
}
```

| メリット | デメリット |
|---------|-----------|
| ✅ 多様なシグナルでバランス良い | ⚠️ PV取得に時間がかかる |
| ✅ LLM品質で内容も評価 | ⚠️ 重みの最適化に試行錯誤必要 |

---

### 案B: 既存データ最大活用（低コスト）

```python
WEIGHTS = {
    "celebrity_score_v2": 0.40, # 既存の人物スコア
    "llm_quality": 0.30,        # LLM 7軸
    "historical_impact": 0.20,  # キーワード
    "sitelinks_norm": 0.10,     # sitelinks正規化
}
```

| メリット | デメリット |
|---------|-----------|
| ✅ 追加API呼び出し不要 | ⚠️ PVシグナルなし |
| ✅ 即座に実装可能 | ⚠️ celebrity_score_v2依存が強い |

---

### 案C: 感銘度特化

```python
WEIGHTS = {
    "llm_quality": 0.45,        # LLM 7軸（記憶性・意外性重視）
    "historical_impact": 0.30,  # キーワード + アンカー補正
    "person_fame": 0.15,        # celebrity_score_v2
    "diversity_bonus": 0.10,    # 多様性ボーナス（少ないカテゴリ優遇）
}
```

| メリット | デメリット |
|---------|-----------|
| ✅ 感動的エピソード優先 | ⚠️ 無名人物が上がりすぎる可能性 |
| ✅ カテゴリバランス改善 | ⚠️ diversity_bonusの設計が複雑 |

---

## 4. 必須制約（全案共通）

### 4.1 同一人物制限（Top N bias control）

```python
BIAS_CONTROL = {
    "top_20": 1,   # Top20内: 同一人物max 1件
    "top_50": 2,   # Top50内: 同一人物max 2件
    "top_100": 3,  # Top100内: 同一人物max 3件
}
```

**実装方法**: ソート後に後処理で制限適用。超過分は次点に置換。

### 4.2 正規化（外れ値抑制）

```python
# すべての特徴量を0-1スケールに正規化
def normalize(values):
    # log変換 + percentile clip (1-99%)
    log_values = np.log1p(values)
    p1, p99 = np.percentile(log_values, [1, 99])
    clipped = np.clip(log_values, p1, p99)
    return (clipped - p1) / (p99 - p1)
```

### 4.3 品質ゲート

```python
# 以下の条件でランキング対象外
EXCLUSION_RULES = [
    "person_type == 'FICTIONAL' and cultural_impact_score < 6.0",
    "episode_text contains メタ表現",
    "age < 0 or age > death_year",
]
```

---

## 5. v1温存・v2併存の実装方針

### 5.1 カラム構成

```
既存（温存）:
  episode_fame_score      # v1オリジナル
  episode_fame_v2         # 既存v2（問題あり）
  episode_fame_score_v4   # 既存v4（問題あり）

新規追加:
  episode_fame_v6         # 新v2スコア（本提案）
  episode_fame_tier_v6    # 新v2ティア
  episode_fame_v6_updated_at
```

### 5.2 ロールバック手順

```bash
# v6を無効化してv1に戻す場合
# 1. ダッシュボード設定変更
#    update_dashboard_v10.py の fame_score 参照先を episode_fame_score に変更
# 2. CSVのv6カラムは削除せず保持（比較用）
```

---

## 6. 承認待ちポイント

### ★確認事項★

1. **重み案の選択**: A/B/C のどれを採用しますか？
   - **推奨: 案A（バランス重視）**

2. **Google検索API使用**:
   - 想定クエリ数: 約500件（未キャッシュ分）
   - 最大コスト: $2.50 (500 × $0.005)
   - キャッシュ方針: 取得後は永続保存、同一キー再取得なし
   - **使用しますか？** (Yes/No)

3. **Wikipedia PV取得**:
   - 約2,000人物 × 1リクエスト = 2,000リクエスト
   - 無料API（レート制限: 100/分）
   - 所要時間: 約20分
   - **使用しますか？** (Yes/No)

4. **新カラム名**: `episode_fame_v6` でよいですか？

---

## 7. 次ステップ（承認後）

1. **C. 検証設計**: アンカー集合（期待Top10）の定義
2. **D. 実装**: v6スコア算出スクリプト作成
3. **ドライラン**: 差分・件数・外れ値確認
4. **本番適用**: 承認後にCSV更新
5. **E. 再発防止**: 監視・回帰テスト追加
