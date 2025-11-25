# ファクトチェック自動実行システム完全ガイド

**作成日**: 2025年10月2日
**目的**: ドキュメント内の数値誤記を自動検出・修正するシステムの構築完了報告

---

## 📋 実装完了したシステム

### 1. Git Pre-Commit Hook（Git commit時の自動チェック）

**ファイル**: `.git/hooks/pre-commit`

**動作タイミング**: `git commit` 実行時

**トリガー条件**: `claudedocs/` ディレクトリ配下の `.md` ファイルが変更されている場合

**動作**:
```bash
# claudedocs配下のMarkdownファイルが変更されているかチェック
if git diff --cached --name-only | grep -q "claudedocs/.*\.md"; then
    # ファクトチェッカーを自動実行
    python3 scripts/fact_checker.py

    # エラー検出時はコミットを中断
    if [ $? -ne 0 ]; then
        echo "❌ ファクトチェックで誤記が検出されました"
        echo "修正方法: python3 scripts/fact_checker.py --fix"
        exit 1  # コミット失敗
    fi
fi
```

**使用例**:
```bash
# Markdownファイルを編集してコミット
git add claudedocs/EXAMPLE.md
git commit -m "Update documentation"

# 自動的にファクトチェック実行
# 🔍 ファクトチェックを実行中...
# ❌ ファクトチェックで誤記が検出されました
#
# 修正方法:
#   1. 自動修正: python3 scripts/fact_checker.py --fix
#   2. 再ステージング: git add claudedocs/
#   3. 再コミット: git commit

# 修正後
python3 scripts/fact_checker.py --fix
git add claudedocs/
git commit -m "Update documentation"
# ✅ ファクトチェック完了（誤記なし）
```

---

### 2. GitHub Actions CI/CD（PR作成時の自動チェック）

**ファイル**: `.github/workflows/fact-check.yml`

**動作タイミング**:
- `push` イベント（`claudedocs/**/*.md` が変更された場合）
- `pull_request` イベント（`claudedocs/**/*.md` が変更された場合）

**ワークフロー**:
```yaml
jobs:
  fact-check:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Set up Python 3.11
      - Install dependencies
      - Run fact checker
      - Check for errors (失敗時はエラーメッセージ表示)
      - Upload report artifacts
```

**使用例**:
```bash
# プルリクエスト作成
git push origin feature/update-docs

# GitHub Actionsが自動実行
# ✅ ファクトチェック完了（誤記なし）
# または
# ❌ ファクトチェックで誤記が検出されました
#   → 修正方法: python3 scripts/fact_checker.py --fix
```

**成果物**:
- `fact_check_report_*.md` - ファクトチェック結果レポート
- `database_stats_history.jsonl` - データベース統計履歴
- 保存期間: 30日

---

### 3. Claude Code起動時の自動チェック

**ファイル**: `scripts/claude-startup-hook.sh`

**動作タイミング**: Claude Code起動時

**動作**:
```bash
# ファクトチェック自動実行
if [ -f "scripts/fact_checker.py" ]; then
    echo "🔍 ドキュメントのファクトチェック中..."
    python3 scripts/fact_checker.py > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "✅ ファクトチェック完了（誤記なし）"
    else
        echo "⚠️ ファクトチェックで誤記を検出"
        echo "  → 修正方法: python3 scripts/fact_checker.py --fix"
    fi
fi
```

**使用例**:
```bash
# Claude Code起動
# 🚀 Ultra Think起動フック開始
# ...（既存の自動処理）
# 🔍 ドキュメントのファクトチェック中...
# ✅ ファクトチェック完了（誤記なし）
# 🎉 Ultra Think起動フック完了
```

---

## 🎯 自動実行のタイミングまとめ

| タイミング | 実行場所 | トリガー条件 | 失敗時の動作 |
|----------|---------|------------|------------|
| **Git Commit前** | ローカル | `claudedocs/*.md` が変更 | コミット中断 |
| **PR作成時** | GitHub Actions | `claudedocs/*.md` が変更 | PRチェック失敗 |
| **Claude起動時** | ローカル | 常時実行 | 警告表示（処理継続） |

---

## 📊 検出・修正フロー

### 誤記検出時のフロー

```
1. ドキュメント編集
   ↓
2. Git commit または PR作成
   ↓
3. ファクトチェック自動実行
   ↓
4. 誤記検出
   ↓
5. エラーメッセージ表示:
   ❌ ファクトチェックで誤記が検出されました

   修正方法:
     1. 自動修正: python3 scripts/fact_checker.py --fix
     2. 再ステージング: git add claudedocs/
     3. 再コミット: git commit
   ↓
6. 自動修正実行
   python3 scripts/fact_checker.py --fix
   ↓
7. 再コミット
   git add claudedocs/
   git commit
   ↓
8. ✅ ファクトチェック完了（誤記なし）
```

---

## 🔧 手動実行コマンド

### 基本コマンド

```bash
# チェックのみ（ドライラン）
python3 scripts/fact_checker.py

# 自動修正実行
python3 scripts/fact_checker.py --fix

# 統計履歴保存
python3 scripts/fact_checker.py --save-history
```

### 実行結果例

```bash
$ python3 scripts/fact_checker.py

データベース実数値（ファクト）
total_persons: 3,110
bracket_display_count: 60
fictional_characters: 3
real_persons: 3,107
uninvestigated_count: 3,050
recognition_score_set: 1
bracket_display_rate: 1.9

⚠️ ドキュメント内の誤記
**検出件数**: 24件

### BRACKET_DISPLAY_PRODUCTION_DEPLOYMENT.md
- 行10: 3,111人 → 3,110人（総人物数）
- 行25: 69件 → 60件（調査済み件数）
...

$ python3 scripts/fact_checker.py --fix
✅ 修正完了: BRACKET_DISPLAY_PRODUCTION_DEPLOYMENT.md (6箇所)
✅ 修正完了: BRACKET_DISPLAY_IMPLEMENTATION_SUMMARY.md (3箇所)
...
```

---

## 📈 統計履歴の記録

### 履歴ファイル: `database_stats_history.jsonl`

**フォーマット**: JSONL（行区切りJSON）

**内容例**:
```jsonl
{"timestamp": "2025-10-02T12:00:00", "total_persons": 3110, "bracket_display_count": 60, ...}
{"timestamp": "2025-10-02T15:30:00", "total_persons": 3110, "bracket_display_count": 61, ...}
```

**活用方法**:
- データベース統計の時系列分析
- 括弧表示対象の増加傾向の把握
- 誤記の修正履歴の追跡

---

## ✅ 動作テスト

### 1. Git Pre-Commit Hookのテスト

```bash
# テスト用のMarkdownファイルを編集（誤った数値を含む）
echo "総人物数: 3,111人" > claudedocs/TEST.md

# コミット試行
git add claudedocs/TEST.md
git commit -m "Test fact check"

# 結果:
# 🔍 ファクトチェックを実行中...
# ❌ ファクトチェックで誤記が検出されました
# コミット失敗 ✅

# 修正
python3 scripts/fact_checker.py --fix
git add claudedocs/TEST.md
git commit -m "Test fact check"

# 結果:
# ✅ ファクトチェック完了（誤記なし）
# コミット成功 ✅
```

### 2. GitHub Actionsのテスト

```bash
# PRを作成してGitHub Actionsをトリガー
git push origin feature/test-fact-check

# GitHub上で確認:
# ✅ fact-check ジョブが成功
# または
# ❌ fact-check ジョブが失敗（エラーメッセージ表示）
```

### 3. Claude起動時のテスト

```bash
# Claude Codeを再起動
# 起動ログで確認:
# [2025-10-02 12:00:00] 🔍 ファクトチェック開始
# [2025-10-02 12:00:01] ✅ ファクトチェック完了
```

---

## 🚨 トラブルシューティング

### 問題: pre-commitフックが実行されない

**原因**: フックスクリプトに実行権限がない

**解決方法**:
```bash
chmod +x .git/hooks/pre-commit
```

### 問題: GitHub Actionsが失敗する

**原因**: `requirements.txt` に必要なパッケージがない

**解決方法**:
```bash
# 必要なパッケージを追加
pip install -r requirements.txt
git add requirements.txt
git commit -m "Add missing dependencies"
```

### 問題: Claude起動時のファクトチェックがスキップされる

**原因**: `scripts/fact_checker.py` が見つからない

**解決方法**:
```bash
# ファイルの存在確認
ls -l scripts/fact_checker.py

# 権限確認
chmod +x scripts/fact_checker.py
```

---

## 📚 関連ファイル

| ファイル | 役割 |
|---------|------|
| `scripts/fact_checker.py` | ファクトチェックのメインスクリプト |
| `.git/hooks/pre-commit` | Git commit時の自動実行フック |
| `.github/workflows/fact-check.yml` | GitHub Actions CI/CDワークフロー |
| `scripts/claude-startup-hook.sh` | Claude起動時の自動実行フック |
| `database_stats_history.jsonl` | データベース統計の履歴ファイル |
| `claudedocs/FACT_CHECK_AND_CORRECTION_REPORT.md` | 誤記の詳細報告書 |

---

## 🎉 今後の運用

### 定期的な確認

```bash
# 週次でファクトチェック実行
python3 scripts/fact_checker.py --save-history

# 履歴の確認
cat database_stats_history.jsonl | tail -10
```

### 統計の分析

```bash
# 括弧表示対象の増加傾向を確認
python3 -c "
import json
with open('database_stats_history.jsonl') as f:
    for line in f:
        data = json.loads(line)
        print(f\"{data['timestamp']}: {data['bracket_display_count']}件\")
"
```

---

**作成日**: 2025年10月2日
**システム名**: ファクトチェック自動実行システム
**ステータス**: ✅ 完全実装完了
**対象**: 全プロジェクトドキュメント
