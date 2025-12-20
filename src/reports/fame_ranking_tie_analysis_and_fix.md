# 有名人度ランキング同率問題 - 原因分析と修正案

## 問題の概要

- **現象**: 1位が83人発生（同率）
- **影響**: ランキングとして機能していない
- **ユニーク率**: 31.74%（7,668人中2,434種類のスコア）

---

## 1. 根本原因分析

### 1.1 問題のコード箇所

**ファイル**: `scripts/fame_score_v2.py`
**関数**: `calculate_fame_score_v2()` (Lines 224-262)

```python
# Line 238: PVスコアの計算
pv_score = min(50.0, math.log10(max(1, monthly_pv)) * 10)
```

### 1.2 なぜ同率が発生するか

| PV | log10(PV) | log10(PV) × 10 | min(50, ...) | wiki_bonus | 合計 |
|----|-----------|----------------|--------------|------------|------|
| 100,000 | 5.00 | 50.00 | **50.00** | 15 | **65.00** |
| 200,000 | 5.30 | 53.01 | **50.00** | 15 | **65.00** |
| 500,000 | 5.70 | 56.99 | **50.00** | 15 | **65.00** |
| 1,000,000 | 6.00 | 60.00 | **50.00** | 15 | **65.00** |

**結論**: `min(50.0, ...)` のキャップにより、PV ≥ 100,000 の人物は全員 **65.0点** に集約される。

### 1.3 1位同率83人の実態

| 人物名 | Wikipedia PV | スコア |
|--------|-------------|--------|
| 小泉八雲 | 643,849 | 65.00 |
| 細田守 | 319,794 | 65.00 |
| 田中雄士 | 315,316 | 65.00 |
| 目黒蓮 | 243,495 | 65.00 |
| ... | ... | 65.00 |
| 禰豆子 | 100,577 | 65.00 |

**PV比率**: 最大/最小 = 6.4倍 → 同一スコア

---

## 2. 改善案比較

### 方針A: スコア計算式の修正（キャップ撤廃/緩和）

| 項目 | 内容 |
|------|------|
| 概要 | `min(50.0, ...)` を撤廃し、スコアの上限を拡大 |
| メリット | スコア自体がユニークになりやすい |
| デメリット | スコアが100点を超える可能性（0-100正規化が崩れる） |
| 影響範囲 | `fame_score_v2` 列の値が変更される |

### 方針B: score と rank を分離（推奨）

| 項目 | 内容 |
|------|------|
| 概要 | 表示用 `fame_score_v2` はそのまま、並び順用 `fame_rank` を新設 |
| メリット | 既存スコアを変更せず、ランキングのみ改善 |
| デメリット | 新しい列を追加する必要がある |
| 影響範囲 | 新規列追加のみ、既存データ不変 |

**タイブレーカー優先順位**:
1. `fame_score_v2` (降順) - 基本スコア
2. `wikipedia_pv` (降順) - 同点時はPV高い方が上位
3. `person_id` (昇順) - 完全一致時はID順で一意化

---

## 3. 推奨結論

**方針B（score/rank分離）を推奨**

理由:
1. 既存の `fame_score_v2` 値を変更しない（後方互換性）
2. スコアは「表示・説明用」、ランクは「並び順用」と役割分離
3. タイブレーカーにより同率を実質0に抑制
4. 将来的なスコア計算式変更にも対応しやすい

---

## 4. 実装差分案

### 4.1 新規スクリプト: `scripts/calculate_fame_rank.py`

```python
def calculate_fame_rank(df: pd.DataFrame) -> pd.DataFrame:
    """
    fame_rank を計算して追加

    タイブレーカー:
    1. fame_score_v2 (DESC)
    2. wikipedia_pv (DESC)
    3. person_id (ASC)
    """
    # 人物単位でユニーク化
    person_df = df.groupby('person_id').agg({
        'person_name': 'first',
        'fame_score_v2': 'first',
        'wikipedia_pv': 'first'
    }).reset_index()

    # ソート（タイブレーカー適用）
    person_df = person_df.sort_values(
        by=['fame_score_v2', 'wikipedia_pv', 'person_id'],
        ascending=[False, False, True]
    ).reset_index(drop=True)

    # ランク付与（1始まり）
    person_df['fame_rank'] = range(1, len(person_df) + 1)

    # 元DFにマージ
    rank_map = person_df.set_index('person_id')['fame_rank']
    df['fame_rank'] = df['person_id'].map(rank_map)

    return df
```

### 4.2 CSV列追加

| 列名 | 型 | 説明 |
|------|-----|------|
| `fame_rank` | int | 有名人度順位（1始まり、同率なし） |

### 4.3 品質ゲートスクリプト

```python
def check_fame_ranking_quality(df: pd.DataFrame) -> dict:
    """ランキング品質チェック"""
    person_ranks = df.groupby('person_id')['fame_rank'].first()

    return {
        "total_persons": len(person_ranks),
        "unique_ranks": person_ranks.nunique(),
        "unique_ratio": person_ranks.nunique() / len(person_ranks),
        "first_place_count": (person_ranks == 1).sum(),
        "max_tie_size": person_ranks.value_counts().max(),
        "is_valid": person_ranks.nunique() == len(person_ranks)
    }
```

---

## 5. 影響範囲

| 対象 | 影響 |
|------|------|
| `preserved/data/MASTER_EPISODES_CURRENT.csv` | `fame_rank` 列追加 |
| `scripts/fame_score_v2.py` | `fame_rank` 計算ロジック追加 |
| ダッシュボード | `fame_rank` 列を表示に使用（オプション） |

### ロールバック手順

1. `fame_rank` 列を削除
2. CSVを保存

```python
df.drop(columns=['fame_rank'], inplace=True)
df.to_csv(path, encoding='utf-8-sig', index=False)
```

---

## 6. 改善結果（2024-12-20 実施）

### Phase 1: fame_rank 列追加
| 指標 | 修正前 | 修正後 |
|------|--------|--------|
| 1位人数（rank） | N/A | **1人** ✅ |
| 同率最大サイズ（rank） | N/A | **1** ✅ |
| ユニーク率（rank） | N/A | **100%** ✅ |

### Phase 2: スコアキャップ撤廃（Line 238）
| 指標 | 修正前 | 修正後 |
|------|--------|--------|
| 最高スコア | 65.00 | **73.09** |
| 最高スコア同率人数 | 83人 | **1人** ✅ |
| スコアユニーク率 | 31.74% | **32.60%** |
| ランキング機能 | 破綻 | **正常** ✅ |

### 修正後 Top 10
| 順位 | 人物名 | スコア | PV |
|------|--------|--------|-----|
| 1 | 小泉八雲 | 73.09 | 643,849 |
| 2 | 高市早苗 | 71.53 | 449,490 |
| 3 | 井上拓真 | 70.38 | 345,446 |
| 4 | 北川景子 | 70.32 | 340,429 |
| 5 | 細田守 | 70.05 | 319,794 |
| 6 | 田中雄士 | 69.99 | 315,316 |
| 7 | 宮崎あおい | 69.68 | 293,781 |
| 8 | 宮﨑あおい | 69.68 | 293,781 |
| 9 | 井上尚弥 | 69.16 | 260,832 |
| 10 | 藤本万梨乃 | 69.01 | 251,949 |

---

## 7. 結論

**「1位が83人」の原因は、`scripts/fame_score_v2.py` Line 238 の `min(50.0, ...)` キャップにより、PV ≥ 100,000 の人物が全員同一スコア（65.00点）に集約されていたため。**

**解決策**:
1. **Phase 1**: `fame_rank` 列を新設し、タイブレーカー（score→PV→ID）で一意な順位を付与
2. **Phase 2**: スコア計算のキャップを撤廃し、高PV帯でもスコアの差を保持

**結果**: 1位人数=1、ランキングユニーク率=100%、品質ゲートPASSED
