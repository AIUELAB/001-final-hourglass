# EPUP Same-Age Duplicate Prevention (同一年齢重複防止)

## 原則
**1人1年齢1エピソード**: 同一人物（person_id）× 同一年齢（age）で複数エピソードは禁止

## インシデント
- 日付: 2026-01-08
- 発見: comprehensive_episode_checker で512グループの重複検出
- 影響: 1,466エピソードが重複状態
- 原因: バッチ生成時に同一年齢チェックなしで複数バージョン生成

## 解決策
1. **削除**: composite_score最高のエピソードを残し、956件削除
2. **最終結果**: 13,934 → 12,978エピソード、0件の問題

## 実装した再発防止メカニズム

### 1. SAGE Orchestrator (生成前チェック)
ファイル: `scripts/sage/orchestrator.py`
- Step 2.5 に事前チェック追加
- API呼び出し前に重複検出
- 既存エピソードあり → RejectionReason.SAME_AGE_DUPLICATE で拒否

### 2. SafeCSVWriter (書き込み時チェック)
ファイル: `scripts/sage/persistence/csv_writer.py`
- `_check_duplicate()` メソッドを強化
- 戻り値: `tuple[bool, str]` （重複フラグ + 理由）
- 詳細ログ出力: `EPUP違反: 同一人物×同一年齢のエピソード既存`

### 3. Same-Age Duplicate Gate (検証ゲート)
ファイル: `scripts/validation/same_age_duplicate_gate.py`
- 類似度閾値: 60%
- 重大度分類: critical (90%+), high (75-89%), medium (60-74%)
- Exit code 1 = CRITICAL/HIGH重複検出

### 4. Comprehensive Episode Checker
ファイル: `scripts/validation/comprehensive_episode_checker.py`
- `_check_same_age_duplicates()` で全件チェック
- person_id + age でグループ化し複数件検出

### 5. CLAUDE.md ドキュメント
- EPUPルールテーブルに明記
- 詳細セクション追加

## 検証コマンド
```bash
# 重複チェック
python scripts/validation/same_age_duplicate_gate.py

# 全件検証
python scripts/validation/comprehensive_episode_checker.py --verbose

# 重複解決
python scripts/validation/same_age_duplicate_resolver.py --dry-run
```

## 重複発見時のアクション
1. `same_age_duplicate_gate.py` で検出
2. `same_age_duplicate_resolver.py --dry-run` で確認
3. `same_age_duplicate_resolver.py` で実行（composite_score最高を残す）

## 関連ファイル
- scripts/sage/orchestrator.py
- scripts/sage/persistence/csv_writer.py
- scripts/sage/gates/duplicate.py
- scripts/validation/same_age_duplicate_gate.py
- scripts/validation/same_age_duplicate_resolver.py
- scripts/validation/comprehensive_episode_checker.py
