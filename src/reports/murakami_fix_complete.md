# 村上春樹エピソード有名度問題 完了報告

**完了日**: 2026-01-03

---

## 1. 現状分析（修正前）

| 順位 | episode_id | v6スコア | 本文 |
|------|------------|---------|------|
| 1 | EP-000000340 | 79.24 | スランプ地獄 |
| 2 | EP-000002037 | 77.83 | ノルウェイの森1000万部 ⭐ |

**問題**: 社会的影響度が最大級の「ノルウェイの森1000万部」が1位になっていなかった。

---

## 2. 原因究明

### 根本原因（3点）

| # | 原因 | ファイル | 詳細 |
|---|------|---------|------|
| 1 | episode_count不整合 | CSV | EP-000000340だけ15、他は5（実際は5が正しい） |
| 2 | episode_type日英不整合 | config.py | TYPE_BONUSが英語のみ、CSVは日本語 |
| 3 | HISTORICAL_KEYWORDS不足 | config.py | 「万部」「ベストセラー」等がなかった |

### 寄与分解（修正前）

```
EP-000000340（スランプ地獄）: 79.24点
  episode_bonus: 100.0 x 10% = 10.00 ← 不正なepisode_count=15

EP-000002037（ノルウェイの森）: 77.83点
  episode_bonus: 81.5 x 10% = 8.15 ← 正しいepisode_count=5
  historical_impact: 53.0 ← タイプボーナス未適用、キーワードなし
```

---

## 3. 改善内容

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `scripts/score/episode_fame_v6/config.py` | TYPE_MAPPING追加、HISTORICAL_KEYWORDS拡充 |
| `scripts/score/episode_fame_v6/scorer.py` | TYPE_MAPPING使用 |
| `preserved/data/MASTER_EPISODES_CURRENT.csv` | episode_count正規化、v6再計算 |

### 追加コード

```python
# config.py
TYPE_MAPPING = {
    "達成": "ACHIEVEMENT",
    "転機": "TURNING_POINT",
    "挑戦": "CHALLENGE",
    ...
}

# Tier2追加キーワード
"ミリオンセラー", "ベストセラー", "大ヒット", "万部", ...
```

---

## 4. 適用結果（修正後）

### 村上春樹の順位

| 順位 | episode_id | v6スコア | 差分 | 本文 |
|------|------------|---------|------|------|
| **1** | EP-000002037 | **84.43** | **+6.60** | ノルウェイの森1000万部 ⭐ |
| 2 | EP-000001453 | 82.93 | +5.40 | ノルウェイの森後の海外移住 |
| 3 | EP-000002038 | 79.63 | +3.00 | 海辺のカフカ |
| 4 | EP-000000340 | 78.39 | -0.85 | スランプ地獄 |
| 5 | EP-000001882 | 78.24 | +1.00 | 早稲田入学 |

### 全体Top20でのEP-000002037の順位: **18位**

---

## 5. 再発防止（EPUP）

### 実装した機能

| 機能 | ファイル | 説明 |
|------|---------|------|
| 逆転検出 | `scripts/validation/detect_score_inversions.py` | 同一人物内で客観イベントが低順位な候補を検出 |
| 回帰テスト | `tests/test_episode_fame_v6_inversions.py` | 7テスト（村上春樹順位、TYPE_MAPPING、KEYWORDS等） |
| レポート | `src/reports/score_inversions.md` | 現在の逆転候補203件をリスト化 |

### 確認コマンド

```bash
# 回帰テスト
pytest tests/test_episode_fame_v6_inversions.py -v

# 逆転検出
python scripts/validation/detect_score_inversions.py

# 品質チェック
python scripts/validation/check_episode_quality.py
```

---

## 6. 受け入れ基準 達成状況

| # | 基準 | 状態 |
|---|------|------|
| 1 | EP-000002037が最上位になっていない理由を説明 | ✅ 寄与分解で特定 |
| 2 | スコア仕様が一貫 | ✅ TYPE_MAPPING, KEYWORDS拡充 |
| 3 | EP-000002037が適切に上位化 | ✅ 村上春樹内1位（84.43点） |
| 4 | 他人物の逆転スキャン | ✅ 203件検出、レポート化 |
| 5 | 監視・品質ゲート・回帰テスト | ✅ 7テスト通過 |

---

## 7. 今後の課題

- 逆転候補203件の精査・チューニング
- 朝永振一郎のノーベル賞エピソード等の個別対応検討
