# Session 20251223 - Phase 8: 団体名混入修正

## 概要
「団体名・個人名」連結パターン（例: "TKO・木下隆行"）の検出・修正・再発防止を実施。

## 検出された問題（5 person_id, 11エピソード）

| person_id | 修正前 | 修正後 | 件数 |
|-----------|--------|--------|------|
| P701305F | Valve・Gabe Newell | Gabe Newell | 3 |
| P1B7ED27 | ufotable・近藤光 | 近藤光 | 3 |
| P6549FEE | TKO・木下隆行 | 木下隆行 | 2 |
| PB1672E7 | TKO・木本武宏 | 木本武宏 | 2 |
| P4FE85EF | TMN・木根尚登 | 木根尚登 | 1 |

## 除外（誤検出）
- `OG・アヌノビー`: "OG"はニックネーム（NBAプレイヤー OG Anunoby）、団体名ではない

## 根本原因
TKO, TMN, ufotable, Valve, WIT STUDIOが`GROUP_ENTITIES`に未登録だったため、既存の品質ゲートで検出できなかった。

## 対応内容
1. **データ修正**: 11レコードのperson_name修正
2. **GROUP_ENTITIES追加** (Phase 8):
   ```python
   "TKO",  # お笑いコンビ
   "TMN",  # 音楽グループ
   "ufotable",  # アニメスタジオ
   "Valve",  # ゲーム会社
   "WIT STUDIO",  # アニメスタジオ
   ```
3. **バリデータ強化**: `src/validators/group_contamination_validator.py`で連結パターン検出

## 再発防止パターン
検出すべきパターン: `^{GROUP_NAME}[・/／]`
- GROUP_ENTITIESに登録された団体名で始まり、区切り文字「・」「/」「／」が続く場合は混入

## 検証結果
- 混入チェック: ✅ PASS (0件)
- テスト: 14ケース全パス

## 教訓
1. 新しい団体名パターン発見時は即座にGROUP_ENTITIESに追加
2. 連結パターンは区切り文字のバリエーションに注意（・/／）
3. 略称（TMN=TM NETWORK）も別途登録が必要

## 関連ファイル
- `src/group_master/entities.py` - GROUP_ENTITIES
- `src/validators/group_contamination_validator.py` - バリデータ
- `src/reports/group_individual_contamination_20251223.json` - 検出レポート
