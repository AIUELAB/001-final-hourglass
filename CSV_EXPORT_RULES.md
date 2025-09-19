# CSV エクスポートルール

## 厳守事項

### 1. カラム名の変更禁止
- **元のカラム名は絶対に変更しない**
- impact_score を「有名度スコア」に変更 → ❌ 禁止
- grade を「Grade」に変更 → ❌ 禁止

### 2. カラム順序の維持
- 元の仕様書のカラム順序を維持する
- 1-17: 元のカラム（id〜created_at）
- 18以降: 新規追加カラム

### 3. 新規カラムの追加方法
- 必要な場合のみ、末尾に追加
- 英語表記で統一（birth_year等）
- 元のカラムと混在させない

## 元の仕様書カラム定義

| カラム名 | 説明 |
|---------|------|
| id | 人物ID |
| person_name | 原語表記 |
| person_name_ja | 日本語名 |
| person_name_display | 表示用短縮名 |
| birth_date | 生誕日 |
| death_date | 死亡日 |
| nationality | 国籍 |
| occupation | 職業 |
| main_category | メインカテゴリ |
| subcategory | サブカテゴリ |
| wikidata_id | WikidataID |
| description | 説明 |
| impact_score | 影響度スコア |
| japanese_relevance | 日本関連度 |
| grade | グレード |
| data_source | データソース |
| created_at | 作成日時 |

## データマッピング規則

- preferred_display_name → person_name_display
- fame_score → impact_score
- advanced_grade → grade（元のgradeを更新）
- original_name → person_name

## 違反防止チェックリスト

- [ ] カラム名を勝手に変更していないか？
- [ ] カラム順序を維持しているか？
- [ ] 新規カラムは末尾に追加したか？
- [ ] 元の仕様書を確認したか？

---

*このルールは厳守すること。違反は二度手間を生む。*
*記録日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
