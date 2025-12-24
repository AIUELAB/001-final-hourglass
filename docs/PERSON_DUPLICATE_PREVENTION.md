# PERSON ID 重複防止 運用ガイド

**作成日**: 2025-12-24
**ステータス**: 運用中

---

## 1. 概要

同一人物に複数のPERSON IDが付与される問題を防止するための運用ガイド。

### 根本原因（2025-12-24特定）

PERSON IDは `person_name` の文字列ハッシュから生成されるため、表記ゆれがあると異なるIDが生成される。

| パターン | 例 | 結果 |
|----------|-----|------|
| 旧字体/新字体 | 關智一 / 関智一 | 別ID |
| 英語/カタカナ | HIKAKIN / ヒカキン | 別ID |
| 旧漢字/常用漢字 | 黒澤明 / 黒沢明 | 別ID |
| フルネーム/略称 | チャーリー・チャップリン / チャップリン | 別ID |

---

## 2. 品質ゲート

### 2.1 新規PERSON登録時チェック

```bash
# 単一人物チェック
python scripts/validate_new_person.py --name "人物名"

# CSVからバッチチェック
python scripts/validate_new_person.py --csv new_persons.csv
```

**ステータス**:
- `OK`: 登録可能
- `DUPLICATE_CANDIDATE`: 重複の可能性高（既存IDへ統合推奨）
- `WARNING`: 類似人物あり（要確認）
- `EXISTS`: 既にID存在

### 2.2 定期スキャン

```bash
# 重複候補検出
python scripts/detect_person_id_duplicates.py

# 詳細分析（クラスター生成）
python scripts/analyze_person_duplicates.py
```

---

## 3. 統合作業フロー

### 3.1 準備

```bash
# 1. 分析実行
python scripts/analyze_person_duplicates.py

# 2. マッピング生成
python scripts/generate_merge_mapping.py

# 3. ドライラン
python scripts/merge_person_ids.py --dry-run
```

### 3.2 承認・実行

```bash
# 承認後のみ実行
python scripts/merge_person_ids.py --execute

# 整合性確認
python scripts/verify_person_merge.py
```

### 3.3 ロールバック

```bash
# バックアップから復元
cp preserved/data/MASTER_EPISODES_CURRENT.backup_YYYYMMDD.csv \
   preserved/data/MASTER_EPISODES_CURRENT.csv
```

---

## 4. 例外ルール

以下のケースは意図的に分離を維持:

| 本名 | 芸名/別名義 | 理由 |
|------|-------------|------|
| 森田一義 | タモリ | 本名/芸名として分離 |

**例外追加手順**:
1. `scripts/generate_merge_mapping.py` の `EXCEPTIONS` に追加
2. `docs/EPUP_RULES.md` に根拠を記載

---

## 5. スクリプト一覧

| スクリプト | 用途 |
|-----------|------|
| `validate_new_person.py` | 新規登録時の類似チェック |
| `detect_person_id_duplicates.py` | 既知パターン検出 |
| `analyze_person_duplicates.py` | クラスター分析 |
| `generate_merge_mapping.py` | 統合マッピング生成 |
| `merge_person_ids.py` | 統合実行 |

---

## 6. レポート保存場所

- 分析結果: `src/reports/person_duplicate_analysis_*.txt`
- 統合マッピング: `src/reports/person_merge_mapping.json`
- 統合結果: `src/reports/person_merge_result_*.json`
- バックアップ: `preserved/data/MASTER_EPISODES_CURRENT.backup_*.csv`

---

## 7. 連絡先

問題発生時は `logs/session_*.txt` を確認し、必要に応じてバックアップから復元。
