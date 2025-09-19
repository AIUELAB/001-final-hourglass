# 最新データベースCSV出力レポート

## ファイル情報
- **入力JSON**: database_cleaned_20250824_195241.json
- **出力CSV**: latest_database_20250824_200047.csv
- **出力日時**: 2025-08-24 20:00:47

## データ統計
- **総レコード数**: 12,363件
- **Grade分布**:
  - Grade A: 16件 (0.1%)
  - Grade B: 59件 (0.5%)
  - Grade C: 30件 (0.2%)
  - Grade D: 21件 (0.2%)
  - Grade E: 3件 (0.0%)
  - Grade H: 1件 (0.0%)
  - Grade I: 6件 (0.0%)
  - Grade J: 6件 (0.0%)
  - Grade N: 21件 (0.2%)
  - Grade N/A: 7件 (0.1%)
  - Grade O: 298件 (2.4%)
  - Grade P: 640件 (5.2%)
  - Grade Q: 1,280件 (10.4%)
  - Grade R: 1,321件 (10.7%)
  - Grade S: 1,227件 (9.9%)
  - Grade T: 1,048件 (8.5%)
  - Grade U: 1,788件 (14.5%)
  - Grade V: 2,730件 (22.1%)
  - Grade Y: 1,861件 (15.1%)


## カラム構成（21列）
1. **基本情報**: id, person_name, person_name_ja, person_name_display
2. **日付情報**: birth_date, death_date, birth_year
3. **属性情報**: nationality, occupation
4. **カテゴリ**: main_category, subcategory
5. **参照情報**: wikidata_id, description
6. **評価情報**: impact_score, japanese_relevance, grade, advanced_grade
7. **メタ情報**: data_source, created_at, name_display_type, is_criminal

## 品質保証
- ✅ UTF-8 BOM付き（Excel文字化け防止）
- ✅ Grade順・影響度順でソート
- ✅ 仕様書準拠のカラム構造
- ✅ 不適切な表示名は削除済み

---
*CSV出力完了*
