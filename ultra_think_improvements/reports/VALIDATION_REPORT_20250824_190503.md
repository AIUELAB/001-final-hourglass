# CSV検証レポート

## ファイル情報
- **CSVファイル**: `final_correct_20250824_190503.csv`
- **生成日時**: 2025-08-24 19:05:03
- **総レコード数**: 12,370件

## display_name 品質
- **正常**: 12,335件 (99.7%)
- **問題あり**: 35件 (0.3%)

## サンプルデータ（上位10件）

| ID | person_name_display | grade | impact_score |
|----|-------------------|-------|--------------|
| person_10418 | アインシュタイン | A | 95 |
| person_08274 | アルフレッド・アインシュタイン | A | 95 |
| person_03157 | アルベルト・アインシュタイン | A | 95 |
| person_10473 | シェイクスピア | A | 95 |
| person_10420 | ダーウィン | A | 95 |
| person_07930 | チャールズ・ダーウィン | A | 95 |
| person_08981 | ニュートン | A | 95 |
| person_10419 | ニュートン | A | 95 |
| person_09890 | フレデリック・ニュートン | A | 95 |
| person_05863 | ブルーノ Schl アインシュタイン | A | 95 |

## カラム構造確認

✅ 元の仕様書カラム（1-17）:
- id, person_name, person_name_ja, person_name_display
- birth_date, death_date, nationality, occupation
- main_category, subcategory, wikidata_id, description
- impact_score, japanese_relevance, grade
- data_source, created_at

✅ 追加カラム（18-21）:
- birth_year: 生誕年
- advanced_grade: A-Z詳細グレード
- name_display_type: 芸名/歴史的人物
- is_criminal: 犯罪者フラグ

---
*検証完了*
