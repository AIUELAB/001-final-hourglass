# Phase 2 設計書（調整版）

## 📋 現状分析

### データ構造の実態

| 指標 | 値 |
|------|-----|
| 総エピソード数 | 1,962件 |
| ユニーク人物数 | 1,781人 |
| **平均エピソード数/人** | **1.1件** |
| 最大エピソード数 | 5件 |
| 7件以上の人物 | **0人** |

### 重要な発見

当初の設計（各人物につき7つのハイライトを選定）は、**現在のデータ構造には適用できません**。

- ほとんどの人物（1,781人）が1件のエピソードのみ
- 複数エピソードを持つ人物は少数
- 最大でも5件のエピソード

---

## 🎯 Phase 2 調整後の目標

### 新しいアプローチ

**「各人物の最も重要なエピソードをハイライトとして選定」**

#### 実装方針

1. **単一エピソードの人物（1,600人以上）**
   - そのエピソードを自動的にハイライトとする
   - `is_highlight = True`

2. **複数エピソードの人物（約180人）**
   - `episode_importance_score`を基準に最も重要なエピソードを選定
   - 複数選定も可能（最大3件まで）

3. **ハイライト選定基準**
   - `episode_importance_score`（既存フィールド）
   - `composite_score`（品質スコア）
   - `episode_type`（ACHIEVEMENT > TURNING_POINT > その他）

---

## 🔧 実装内容

### 1. データベーススキーマ拡張

```csv
# 新規フィールド
is_highlight,highlight_rank,highlight_selection_method
```

#### フィールド定義

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `is_highlight` | BOOLEAN | このエピソードがハイライトかどうか |
| `highlight_rank` | INTEGER | ハイライト内での順位（1-3） |
| `highlight_selection_method` | TEXT | 選定方法（auto_single, importance_based, manual） |

### 2. 選定アルゴリズム

#### ケース1: 単一エピソード

```python
if episode_count == 1:
    is_highlight = True
    highlight_rank = 1
    highlight_selection_method = "auto_single"
```

#### ケース2: 複数エピソード（2-5件）

```python
if 2 <= episode_count <= 5:
    # episode_importance_scoreでソート
    sorted_episodes = episodes.sort_values('episode_importance_score', ascending=False)

    # TOP3を選定（エピソード数が3未満の場合は全て）
    top_n = min(3, len(sorted_episodes))

    for rank, episode in enumerate(sorted_episodes.head(top_n), 1):
        episode['is_highlight'] = True
        episode['highlight_rank'] = rank
        episode['highlight_selection_method'] = "importance_based"
```

### 3. 重要度スコアの計算

`episode_importance_score`が欠損している場合の代替計算：

```python
def calculate_importance_fallback(episode):
    """代替重要度スコア計算"""
    score = 0.0

    # 品質スコア（40%）
    if 'composite_score' in episode and not pd.isna(episode['composite_score']):
        score += episode['composite_score'] * 0.4

    # エピソードタイプ（30%）
    type_weights = {
        'ACHIEVEMENT': 30,
        'TURNING_POINT': 25,
        'CHALLENGE': 20,
        'INNOVATION': 20,
        'FOUNDING': 18,
        'FAMILY': 15,
        'GROWTH': 15,
        'FAILURE': 10,
        'COMEBACK': 10
    }
    episode_type = episode.get('episode_type', '')
    score += type_weights.get(episode_type, 10)

    # 記憶性・共感性・意外性（30%）
    if '記憶性スコア' in episode:
        score += episode.get('記憶性スコア', 0) * 0.1
    if '共感性スコア' in episode:
        score += episode.get('共感性スコア', 0) * 0.1
    if '意外性スコア' in episode:
        score += episode.get('意外性スコア', 0) * 0.1

    return score
```

---

## 📊 期待される結果

### ハイライト統計（推定）

| カテゴリ | 人物数 | ハイライト数 | 選定方法 |
|---------|-------|-------------|---------|
| 単一エピソード | ~1,600人 | 1,600件 | auto_single |
| 2-3エピソード | ~150人 | 300-450件 | importance_based |
| 4-5エピソード | ~30人 | 90-150件 | importance_based |
| **合計** | **1,781人** | **~2,000件** | - |

### ハイライト比率

- 全エピソードの約100%がハイライトになる見込み
- これは現在のデータ構造（1人あたり平均1.1件）を反映

---

## 🚀 実装ステップ

### Step 1: フィールド追加

```python
df['is_highlight'] = False
df['highlight_rank'] = None
df['highlight_selection_method'] = None
```

### Step 2: 単一エピソード人物の処理

```python
single_episode_persons = df.groupby('person_id').filter(lambda x: len(x) == 1)
df.loc[single_episode_persons.index, 'is_highlight'] = True
df.loc[single_episode_persons.index, 'highlight_rank'] = 1
df.loc[single_episode_persons.index, 'highlight_selection_method'] = 'auto_single'
```

### Step 3: 複数エピソード人物の処理

```python
for person_id in multi_episode_persons:
    person_episodes = df[df['person_id'] == person_id]

    # 重要度スコアでソート
    sorted_eps = person_episodes.sort_values('episode_importance_score', ascending=False)

    # TOP3を選定
    top_n = min(3, len(sorted_eps))
    for rank, (idx, episode) in enumerate(sorted_eps.head(top_n).iterrows(), 1):
        df.at[idx, 'is_highlight'] = True
        df.at[idx, 'highlight_rank'] = rank
        df.at[idx, 'highlight_selection_method'] = 'importance_based'
```

---

## 💡 将来の拡張

### エピソード数が増加した場合

各人物のエピソード数が7件以上になった場合：

1. `lifetime_highlight_selector.py`を活用
2. 年齢スロットとの連携
3. 7つのスロット全てにハイライトエピソードを配置

---

## ✅ 実装判断

**このPhase 2設計で進めてよろしいですか？**

または、以下の代替案も検討できます：

### 代替案A: 全エピソードをハイライト
- 現時点では全エピソードを`is_highlight = True`
- 将来的にエピソード数が増えた際に選定ロジックを実装

### 代替案B: Phase 2を延期
- データが充実するまでPhase 2の実装を保留
- 他の改善（不足カテゴリ補強、架空キャラクター追加）を優先

---

**作成者**: Claude Code
**最終更新**: 2025-11-25
**バージョン**: 1.0
