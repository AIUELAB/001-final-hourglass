# 団体名混入防止ガイド

## 概要

エピソードの主語（`person_name`）に団体・グループ名が混入することを防止するための運用ガイドです。

## 問題の定義

**団体名混入**とは、以下のようなデータがマスターCSVに登録されている状態を指します：

| 問題パターン | 例 | 正しい形 |
|-------------|---|---------|
| 団体名がそのまま登録 | `person_name = "Metallica"` | 個別メンバー名で登録 |
| グループ名+個人名の連結 | `person_name = "ビートルズ・ジョン・レノン"` | `person_name = "ジョン・レノン"` |
| 組織名サフィックス | `person_name = "東京交響楽団"` | 個人名で登録 |

## 品質ゲート

### 1. 登録前バリデーション

新規エピソード生成時に自動的に検証されます：

```
scripts/pipeline/pipeline_layer1_generate.py
  └── validate_person_name() → 失敗時は拒否
  └── is_group_entity() → 団体名なら拒否
```

### 2. バッチ検証スクリプト

```bash
# 通常実行（レポート保存あり）
python scripts/batch/check_group_contamination.py

# CIモード（1件でも検出でexit 1）
python scripts/batch/check_group_contamination.py --strict

# 特定CSVを検証
python scripts/batch/check_group_contamination.py --csv path/to/file.csv
```

### 3. テスト

```bash
# バリデータのテスト
pytest tests/test_group_contamination_validator.py -v
```

## 運用手順

### 日次チェック

```bash
python scripts/batch/check_group_contamination.py
```

- 結果: `src/reports/group_contamination_check_YYYYMMDD_HHMMSS.json`
- ステータス: `PASS` または `FAIL`

### 問題検出時の対応

1. **レポート確認**
   ```bash
   cat src/reports/group_contamination_check_*.json | jq '.issues'
   ```

2. **修正方針の決定**
   - 削除: エピソードを削除
   - 置換: 代表メンバー名に置換

3. **修正実施**
   ```bash
   # 例: person_name を修正
   python scripts/fix/fix_person_group_name_contamination.py --execute
   ```

4. **再検証**
   ```bash
   python scripts/batch/check_group_contamination.py --strict
   ```

## 新規団体の追加

新しい団体をシステムに認識させる場合：

1. **`src/group_master/entities.py`** の `GROUP_ENTITIES` に追加
2. **`src/group_master/members.py`** の `GROUP_MEMBER_MAP` にメンバー追加
3. **テスト実行**
   ```bash
   pytest tests/test_group_contamination_validator.py -v
   ```

## 除外パターン

グループ名と同名だが正当な個人名（例：女優「オードリー・ヘプバーン」とお笑いコンビ「オードリー」）は、除外パターンとして登録されています：

```python
# src/validators/group_contamination_validator.py
EXCLUDE_PERSON_NAMES = {
    "オードリー・ヘプバーン",
    "オードリー・タトゥ",
    ...
}
```

新しい除外パターンが必要な場合は、このセットに追加してください。

## ファイル構成

```
src/validators/
  └── group_contamination_validator.py  # バリデータ本体

scripts/batch/
  └── check_group_contamination.py      # 定期チェックスクリプト

tests/
  └── test_group_contamination_validator.py  # テスト

src/reports/
  └── group_contamination_check_*.json  # チェックレポート
```

## トラブルシューティング

### Q: 誤検出が発生した場合
A: `EXCLUDE_PERSON_NAMES` に除外パターンを追加してください。

### Q: 新しい団体名パターンが検出されない場合
A: `GROUP_ENTITIES` に団体名を追加するか、サフィックスパターンを追加してください。

### Q: CIでFAILになった場合
A: レポートを確認し、問題のあるデータを修正してから再実行してください。

## 関連ドキュメント

- `docs/PERSON_NAME_VALIDATION_WORKFLOW.md` - 人物名バリデーション全体
- `docs/EPISODE_DB_STARTUP_GUIDE.md` - エピソードDB運用ガイド
