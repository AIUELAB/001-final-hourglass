# RCA-Kaizen: 5軸スコア欠損問題

**日付**: 2026-01-06
**報告者**: Claude Code
**影響**: ダッシュボードv10で「品質」「感情」スコアが「-」と表示

---

## 1. 問題概要

ダッシュボードv10のCSVモードで、5軸スコア（総合品質・感情インパクト）が「-」と表示される問題が発生。

**症状**:
- 品質スコア: 「-」
- 感情スコア: 「-」
- 他の7軸スコア: 正常表示

---

## 2. 5 Whys分析

| Why | 質問 | 回答 |
|-----|------|------|
| **Why 1** | なぜ「-」と表示されるか？ | `overall_quality` と `emotional_impact` が null |
| **Why 2** | なぜ null か？ | 埋め込みJSONに値が入っていない |
| **Why 3** | なぜ埋め込みJSONに値がないか？ | `update_dashboard_v10.py` がCSVから読み込んでいない |
| **Why 4** | なぜCSVから読み込まないか？ | **7軸スコアから計算する実装だった** |
| **Why 5** | なぜ計算が失敗するか？ | 7軸スコアが0の場合、`(0 and 0)` = False で None になる |

---

## 3. 根本原因

**Root Cause**: `update_dashboard_v10.py` の5軸スコア計算ロジック

```python
# 問題のコード（修正前）
episode["overall_quality"] = (mem + gen) / 2 if (mem and gen) else None
episode["emotional_impact"] = (emp + sur) / 2 if (emp and sur) else None
```

**問題点**:
1. CSVに `総合品質` と `感情インパクト` カラムが存在（97.7%充填済み）
2. しかし、`update_dashboard_v10.py` はこれを**無視**して7軸スコアから再計算
3. 7軸スコアが0の場合、`(0 and 0)` は Python で False と評価され None を返す

**データ確認結果**:
- CSVの `総合品質` 非空: 10,022件 / 10,260件 (97.7%)
- CSVの `感情インパクト` 非空: 10,022件 / 10,260件 (97.7%)

---

## 4. 改善策

### 4.1 即時対策（実施済み）

**修正ファイル**: `scripts/update_dashboard_v10.py`

```python
# 修正後のコード
# 総合品質: CSVから読み込み、なければ計算
csv_overall = row.get("総合品質", "")
if csv_overall and csv_overall.strip():
    episode["overall_quality"] = float(csv_overall)
else:
    episode["overall_quality"] = (mem + gen) / 2 if (mem and gen) else None

# 感情インパクト: CSVから読み込み、なければ計算
csv_emotional = row.get("感情インパクト", "")
if csv_emotional and csv_emotional.strip():
    episode["emotional_impact"] = float(csv_emotional)
else:
    episode["emotional_impact"] = (emp + sur) / 2 if (emp and sur) else None
```

### 4.2 再発防止策

1. **データソース優先度ルール**:
   - CSVに値がある場合は必ずCSVから読み込む
   - 計算によるフォールバックは最後の手段

2. **コードレビューチェックリスト追加**:
   - [ ] CSVカラムが存在する場合、計算で上書きしていないか確認
   - [ ] 条件式で `0` が False と評価される問題がないか確認

3. **データ同期テスト追加**:
   - 埋め込みJSONとCSVパースの結果が一致することを検証

---

## 5. 効果検証

**修正前**:
- 品質スコア: 「-」（null）
- 感情スコア: 「-」（null）

**修正後**:
- 品質スコア: 7.5（CSVから正しく読み込み）
- 感情スコア: 5.8（CSVから正しく読み込み）

---

## 6. 関連ファイル

| ファイル | 役割 |
|---------|------|
| `scripts/update_dashboard_v10.py` | 埋め込みJSON生成（修正済み） |
| `scripts/score/fill_empty_scores_19.py` | 総合品質/感情インパクトをCSVに書き込み |
| `preserved/episode_database_dashboard_v10.html` | ダッシュボードHTML |

---

## 7. 学習事項

**EPUP System への追加ルール**:

> **5軸スコア同期ルール**: 埋め込みJSONとCSVパースは同一のカラムを参照し、
> CSVに値がある場合は必ずその値を使用すること。計算による代替は
> CSVに値が存在しない場合のみ許可される。

---

## 8. ステータス

- [x] 根本原因特定
- [x] 即時対策実施
- [x] ダッシュボード更新
- [ ] コミット・プッシュ
