# RCA: エピソードTop20独占問題
**日付**: 2026-02-03
**分類**: データ品質 / スコアリング不整合
**重大度**: High

---

## 1. 概要

エピソードデータベースのTop20ランキングにおいて、特定人物のエピソードが過度に集中する問題が発生。マザー・テレサが4件（20%）を占有し、ジミー・カーター3件、トーマス・マン2件、ネルソン・マンデラ2件と、上位20件中11件が4人の人物で占められている。

根本原因は `fame_score_v3` と `celebrity_score_v2` が同一人物の全エピソードで固定値となり、エピソード固有の価値が反映されていないこと。

---

## 2. 事象詳細

### 2.1 マザー・テレサ4件独占

| EP ID | 年齢 | super_total_score | episode_fame_v6 | fame_score_v3 |
|-------|------|-------------------|-----------------|---------------|
| EP-260111081947753 | 71 | 841,474 | 92.9 | 789.08 |
| EP-260111081947754 | 72 | 844,953 | 95.07 | 789.08 |
| EP-260111081947756 | 73 | 840,529 | 93.72 | 789.08 |
| EP-260111081947758 | 74 | 842,680 | 93.63 | 789.08 |

**観察**:
- 4件全てで `fame_score_v3 = 789.08` が固定
- `episode_fame_v6` は92.9〜95.07と正常に変動
- 年齢71〜74歳の連続4年間がTop20に入る異常事態

### 2.2 Top20重複状況

| 人物名 | Top20内件数 | 占有率 |
|--------|-------------|--------|
| マザー・テレサ | 4件 | 20% |
| ジミー・カーター | 3件 | 15% |
| トーマス・マン | 2件 | 10% |
| ネルソン・マンデラ | 2件 | 10% |
| **合計** | **11件** | **55%** |

4人で過半数を占有し、多様性が著しく損なわれている。

### 2.3 大谷翔平問題（8件全て固定値）

| 指標 | 状態 |
|------|------|
| fame_score_v3 | 683.44（8件全て固定） |
| celebrity_score_v2 | 821.26（8件全て固定） |
| episode_fame_v6 | 80.34〜106.41（正常変動） |
| 最高スコア | 770,334（Top20圏外） |

**問題点**:
- `fame_score_v3` が全年齢で同一値のため、エピソード間の差別化が不十分
- 実際には2023年WBC優勝など突出した業績があるが、スコアに反映されていない

---

## 3. 根本原因分析（5 Whys）

### Why 1: なぜマザー・テレサが4件もTop20に入るのか？
→ `fame_score_v3` が全エピソードで789.08に固定され、人物の知名度がそのままスコアに直結しているため。

### Why 2: なぜ fame_score_v3 が固定されるのか？
→ `scripts/sage/process_batch_results.py:313-321` で、同一 `person_id` の最初の行から値をコピーする実装になっているため。

```python
# 問題のコード（概念）
if person_id in person_scores:
    row['fame_score_v3'] = person_scores[person_id]  # 全行に同じ値
```

### Why 3: なぜエピソード固有の知名度計算がないのか？
→ Wikidataシグナル（sitelinks_count, statements_count等）から動的に計算する `_fill_wikidata_fields()` が `csv_writer.py` に存在しないため。

### Why 4: なぜ同一人物の独占を防ぐロジックがないのか？
→ 設計時に「多様性確保」の要件が考慮されておらず、品質ゲートが個別エピソードの妥当性のみをチェックしているため。

### Why 5: なぜ置換モードでゲートがバイパスされるのか？
→ `is_replacement_candidate=True` 時に生成前チェック（same_age_duplicate等）をスキップする実装があり、品質担保が不完全なため。

---

## 4. 既存ゲートが効かなかった理由

| ゲート | 想定機能 | 効かなかった理由 |
|--------|----------|------------------|
| same_age_duplicate_gate | 同一年齢重複防止 | 異なる年齢（71,72,73,74歳）なので検出対象外 |
| FictionalQualityGate | 架空キャラ品質検証 | 実在人物のため対象外 |
| dashboard_completeness_gate | フィールド欠損検出 | fame_score_v3は「値がある」ので欠損扱いにならない |
| SafeCSVWriter | 書き込み前検証 | スコア値の妥当性（固定かどうか）はチェック対象外 |

**根本的な問題**: 「スコアの多様性」「ランキングの偏り」を検出するゲートが存在しない。

---

## 5. 影響範囲

### 5.1 データ影響
- **Top20の55%が4人に独占**: ユーザー体験の多様性低下
- **大谷翔平等の人気人物が圏外**: 期待されるエピソードが上位に表示されない
- **fame_score_v3固定**: 全person_idで同様の問題が発生している可能性

### 5.2 ビジネス影響
- ダッシュボード閲覧時の「飽き」を誘発
- 特定人物のファンには有利、他のファンには不利な偏り
- データ品質への信頼低下

### 5.3 技術的影響
- `super_total_score` の計算式に `fame_score_v3` が寄与しすぎている
- エピソード固有の価値（episode_fame_v6）の影響が相対的に小さい

---

## 6. 恒久対策

### 6.1 短期対策（即時実施）

| 対策 | 内容 | 優先度 |
|------|------|--------|
| Top20多様性ゲート追加 | 同一person_idは最大2件までに制限 | P0 |
| fame_score_v3動的計算 | エピソード年齢時点のWikidataシグナルを反映 | P0 |
| ダッシュボード表示修正 | 同一人物の連続表示を防ぐシャッフルロジック | P1 |

### 6.2 中期対策（1週間以内）

| 対策 | 内容 | 優先度 |
|------|------|--------|
| スコア計算式見直し | episode_fame_v6の重み増加、fame_score_v3の重み減少 | P1 |
| 置換モードゲート復活 | is_replacement_candidate時も品質チェックを実施 | P1 |
| 既存データ再計算 | 全エピソードのfame_score_v3を再計算 | P2 |

### 6.3 長期対策（設計改善）

| 対策 | 内容 |
|------|------|
| Wikidataシグナル履歴取得 | 過去時点のsitelinks_count等を推定するロジック |
| A/Bテスト | スコア計算式の複数バリエーションを検証 |
| 多様性指標の導入 | Top100の人物分散度をKPIとして監視 |

---

## 7. 対策ファイル一覧

| ファイル | 修正内容 |
|----------|----------|
| `scripts/sage/process_batch_results.py` | fame_score_v3の動的計算ロジック追加（L313-321） |
| `scripts/sage/persistence/csv_writer.py` | `_fill_wikidata_fields()` メソッド追加 |
| `scripts/validation/top20_diversity_gate.py` | 新規作成：同一person_id制限チェック |
| `preserved/episode_database_dashboard_v11.html` | 表示時の多様性シャッフル追加 |
| `src/utils/score_calculator.py` | super_total_score計算式の重み調整 |

---

## 8. 検証手順

### 8.1 対策前確認
```bash
# Top20の人物分布を確認
python -c "
import pandas as pd
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv')
top20 = df.nlargest(20, 'super_total_score')
print(top20['person_name'].value_counts())
"
```

### 8.2 対策後確認
```bash
# 多様性ゲートの実行
python scripts/validation/top20_diversity_gate.py

# fame_score_v3の変動確認
python -c "
import pandas as pd
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv')
person = df[df['person_name'] == '大谷翔平']
print(person[['age', 'fame_score_v3', 'episode_fame_v6']].to_string())
"
```

---

## 9. 参考：理想的なTop20構成

| 指標 | 現状 | 目標 |
|------|------|------|
| ユニーク人物数 | 9人 | 15人以上 |
| 最多出現人物 | 4件（20%） | 2件（10%）以下 |
| 人物多様性指数 | 0.45 | 0.75以上 |

---

**作成者**: Claude Code (RCA自動生成)
**レビュー**: 要
**ステータス**: 対策立案完了、実装待ち
