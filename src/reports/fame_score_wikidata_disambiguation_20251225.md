# Fame Score v3 - Wikidata同名曖昧性問題 分析レポート

**作成日時**: 2025-12-25
**対象**: PF632FA6 (ken), PBC21E64 (ONE)

---

## 1. 根本原因（確定）

### 問題: Wikidata検索で別エンティティを取得

`scripts/fame_score_v3/wikidata.py` の `search_wikidata()` 関数は:
- `wbsearchentities` API の **最初の結果のみ** を採用（`limit: 1`）
- **短い名前・一般語**で検索すると、別のエンティティがヒット

### 影響を受けた人物

| PERSON_ID | NAME | 現在sitelinks | 誤エンティティ | 正しいsitelinks |
|-----------|------|--------------|---------------|----------------|
| PF632FA6 | ken | 331 | Q114 (ケニア・国) | **12** (Q1361450) |
| PBC21E64 | ONE | 213 | Q199 (数字の1) | **19** (Q11237288) |
| PFF44570 | J | 152 | Q9773 (文字J) | **1** (Q1679012) |
| PD3F791F | Eve | 122 | Q830183 (聖書イブ) | **0** (Q56277106) |
| PA5CD967 | Ado | 55 | Q190012 | **3** (Q105966612) |
| P3943D87 | UA | 55 | Q503419 (大学) | **不明** |

### 正しい値との比較

| 人物 | 現在score | 正しいsitelinks反映後 | 差分 |
|------|----------|---------------------|------|
| ken | 713.34 | 約400-450 | -270程度 |
| ONE | 697.10 | 約400-450 | -250程度 |
| J.Bieber | 695.97 | 695.97 (正) | 0 |

→ **修正後、kenとONEはJustin Bieberより低くなり、ランキングが適正化**

---

## 2. 問題の発生メカニズム

```
入力: person_name = "ken"
    ↓
wbsearchentities(search="ken", limit=1)
    ↓
結果: [{"id": "Q114", "label": "Kenya", ...}]  ← ケニア（国）
    ↓
get_wikidata_metrics_by_id("Q114")
    ↓
sitelinks = 331 (ケニアは331言語版Wikipedia記事あり)
    ↓
fame_score計算でsitelinks=331を使用
    ↓
スコアが不当に高騰
```

---

## 3. 修正案

### 案A: 対象人物のみ手動修正（即時・低リスク）

影響を受けた6人物のみ、正しいWikidata IDを手動設定してスコア再計算。

**メリット**:
- 即時対応可能
- 他データへの影響なし

**デメリット**:
- 将来の新規人物追加時に再発リスク

### 案B: 検索ロジック改善（中期・根本対策）

1. **職業フィルタ追加**:
   - 検索結果から「human」かつ「musician/artist/actor」等の職業を持つエンティティを選択

2. **複数候補の検証**:
   - `limit: 5` で取得し、スコアリングで最適を選択
   - 国・文字・概念を除外

3. **手動マッピングテーブル**:
   - 曖昧名の正しいWikidata IDを事前定義

### 案C: 案A + 案B（推奨）

1. 即時: 影響6人物を手動修正
2. 中期: 検索ロジック改善 + 全件再スキャン

---

## 4. 再発防止

### 4.1 品質ゲート（新規追加）

検出ルール:
- sitelinks > 100 かつ 名前が5文字以下 → 警告
- 取得エンティティが「国」「文字」「数字」「概念」→ ブロック

### 4.2 検証スクリプト

- `scripts/validate_wikidata_entities.py` - エンティティタイプ検証
- 定期実行でミスマッチ検出

### 4.3 テスト追加

```python
def test_short_name_disambiguation():
    """短い名前で正しいエンティティを取得できること"""
    assert search_person("ken") != "Q114"  # ケニアでないこと
    assert search_person("ONE") != "Q199"  # 数字1でないこと
```

---

## 5. 承認待ちアクション

### 即時対応（承認後実施）

1. 以下6人物のsitelinks_countを正しい値に更新:
   - ken: 331 → 12
   - ONE: 213 → 19
   - J: 152 → 1
   - Eve: 122 → 0
   - Ado: 55 → 3
   - UA: 要確認

2. fame_score_v3を再計算

### ドライラン結果（予想）

| 人物 | 現在順位 | 予想順位 |
|------|---------|---------|
| ken | 109位 | 約1500-2000位 |
| ONE | 158位 | 約1500-2000位 |
| J | 約400位 | 約3000位以下 |
| Eve | 約600位 | 約3000位以下 |
| Ado | 約1000位 | 約3000位以下 |

---

## 6. 実施完了

### 修正結果

| 人物 | 修正前score | 修正後score | 修正後順位 |
|------|------------|------------|----------|
| ken | 713.34 | **430.73** | 1961位 |
| ONE | 697.10 | **425.19** | 2032位 |
| J | 620.42 | **393.19** | 2663位 |
| Eve | 548.62 | **365.46** | 3475位 |
| Ado | 433.97 | **355.30** | 3791位 |
| J.Bieber | 695.97 | 695.97 | **159位** |

✅ **全員がジャスティン・ビーバーより下位に修正完了**

### 追加ファイル

- `scripts/validate_wikidata_disambiguation.py` - 同名曖昧性検出
- `tests/test_fame_score_validation.py` - 回帰テスト追加（4テスト）

### テスト結果

```
14 passed
- TestWikidataDisambiguation::test_no_high_risk_short_names ✅
- TestWikidataDisambiguation::test_ken_not_using_kenya_entity ✅
- TestWikidataDisambiguation::test_one_not_using_number_entity ✅
- TestWikidataDisambiguation::test_ken_score_below_justin_bieber ✅
```
