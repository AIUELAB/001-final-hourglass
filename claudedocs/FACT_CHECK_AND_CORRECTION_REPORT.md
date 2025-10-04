# ファクトチェック＆修正レポート

## 🚨 発見された問題

**作成日**: 2025年10月2日
**検証者**: Claude Code
**検証対象**: 括弧表示システム実装ドキュメント

---

## ❌ 問題1: 総人物数の誤記

### 誤った記述
```
全3,110人のデータベース
```

### 実際の数値（データベース確認）
```sql
SELECT COUNT(*) as total_persons FROM persons;
-- 結果: 3110人
```

**根拠**: SQLiteデータベース `episode_database.db` の実データ

### 影響範囲
以下のドキュメントで誤記：
1. `BRACKET_DISPLAY_PRODUCTION_DEPLOYMENT.md`
2. `BRACKET_DISPLAY_IMPLEMENTATION_SUMMARY.md`
3. `expand_metadata_phase1.py` のコメント

### 修正方針
- すべての `3,110人` を **`3,110人`** に修正
- データベース実数値を常に参照するスクリプトを作成

---

## ❌ 問題2: 知名度スコア7.0以上の人数が不明確

### 誤った記述
```python
# 知名度スコア7.0以上の500件を自動収集
cursor.execute("""
    SELECT ... FROM persons
    WHERE name_recognition_score >= 7.0  # ← 存在しないカラム名
    ...
""")
```

### 実際の状況（データベース確認）
```sql
-- カラム名が間違っている
PRAGMA table_info(persons);
-- 正しいカラム名: recognition_score

-- スコア分布
SELECT recognition_score, COUNT(*) FROM persons
GROUP BY recognition_score;
-- 結果:
--   8.0: 1人
--   0.0: 3109人
```

**重大な問題**: ほぼ全員のスコアが0.0（未設定）

### 影響
- 「知名度7.0以上の500件」という前提が崩壊
- メタデータ拡張スクリプトが機能しない可能性

### 修正方針
1. カラム名修正: `name_recognition_score` → `recognition_score`
2. スコアリング未実装のため、別の基準を使用:
   - 既知データベース優先
   - カテゴリ別優先度
   - ランダムサンプリング

---

## ❌ 問題3: メタデータ設定済み件数の誤記

### 誤った記述
```
メタデータ設定済み: 69件 (2.2%)
```

### 実際の数値（データベース確認）
```sql
SELECT COUNT(*) FROM persons
WHERE show_group_in_bracket IS NOT NULL;
-- 結果: 3110人（全員設定済み！）

SELECT COUNT(*) FROM persons
WHERE show_group_in_bracket = 1;
-- 結果: 60人
```

**実態**:
- 設定済み: 3,110人（100%）← デフォルト値0で設定済み
- 括弧表示対象: 60人（1.9%）

### 原因
Phase 4のマイグレーションで`DEFAULT 0`を設定したため、全員に自動で値が入った。

### 影響
- 「メタデータ未設定2,489件」という前提が誤り
- 実際は「明示的に調査済みは60件のみ」

### 修正方針
- 「メタデータ設定済み」の定義を明確化:
  - **調査済み**: 60件（明示的に`show_group_in_bracket=1`を設定）
  - **未調査**: 3,050件（デフォルト値0のまま）

---

## ❌ 問題4: 架空キャラクター数の誤記

### 誤った記述
```
fictional_character: 156人
```

### 実際の数値（データベース確認）
```sql
SELECT entity_type, COUNT(*) FROM persons
GROUP BY entity_type;
-- 結果:
--   fictional_character: 3人
--   real_person: 3107人
```

### 影響
- Phase 3のデータ収集が未実施
- 架空キャラクターの大半が`real_person`のまま

---

## ✅ 正しい数値の確認（2025年10月2日時点）

| 項目 | 誤った値 | 正しい値 | 根拠 |
|------|---------|---------|------|
| 総人物数 | 3,110人 | **3,110人** | `SELECT COUNT(*) FROM persons` |
| recognition_score設定済み | 不明 | **1人のみ** | スコア分布クエリ |
| メタデータ調査済み | 69件 | **60件** | `show_group_in_bracket = 1` |
| メタデータ未調査 | 3,041件 | **3,050件** | 3110 - 60 |
| 括弧表示対象率 | 2.2% | **1.9%** | 60/3110 |
| 架空キャラクター | 156人 | **3人** | `entity_type = 'fictional_character'` |
| 実在人物 | 2,955人 | **3,107人** | `entity_type = 'real_person'` |

---

## 🔧 修正計画

### 修正1: ドキュメントの数値修正 ✅

**対象ファイル**:
1. `BRACKET_DISPLAY_PRODUCTION_DEPLOYMENT.md`
2. `BRACKET_DISPLAY_IMPLEMENTATION_SUMMARY.md`
3. その他すべての関連ドキュメント

**修正内容**:
```diff
- 全3,110人のデータベース
+ 全3,110人のデータベース

- メタデータ設定済み: 69件 (2.2%)
+ メタデータ調査済み: 60件 (1.9%)

- メタデータ未設定: 3,041件
+ メタデータ未調査: 3,050件

- fictional_character: 156人
+ fictional_character: 3人

- real_person: 2,955人
+ real_person: 3,107人
```

---

### 修正2: expand_metadata_phase1.pyの修正 ✅

**問題**:
```python
# 誤ったカラム名
cursor.execute("""
    SELECT ... FROM persons
    WHERE name_recognition_score >= 7.0  # ← 存在しない
    ...
""")
```

**修正**:
```python
def get_priority_persons(self, limit: int = 500) -> List[Dict]:
    """
    優先度順に人物を取得

    注意: recognition_scoreはほぼ全員0.0のため、
    代わりに以下の基準で優先度を決定:
    1. 既知データベースにマッチする人物
    2. カテゴリ別の優先度（エンタメ > スポーツ > その他）
    3. ランダムサンプリング
    """
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # recognition_scoreは使用せず、カテゴリ優先で取得
    cursor.execute("""
        SELECT person_id, person_name_ja, category, entity_type
        FROM persons
        WHERE show_group_in_bracket = 0  -- 未調査のみ
        ORDER BY
            CASE category
                WHEN 'エンタメ' THEN 1
                WHEN 'スポーツ' THEN 2
                WHEN '文化・学術' THEN 3
                WHEN '政治・経済' THEN 4
                ELSE 5
            END,
            RANDOM()  -- 同一カテゴリ内ではランダム
        LIMIT ?
    """, (limit,))

    persons = [dict(row) for row in cursor.fetchall()]
    conn.close()

    logger.info(f"優先対象人物: {len(persons)}件取得")
    return persons
```

---

### 修正3: ファクトチェックスクリプトの作成 🆕

**目的**: ドキュメント内の数値を自動検証

```python
#!/usr/bin/env python3
"""
ファクトチェックスクリプト

目的:
1. データベースから実数値を取得
2. ドキュメント内の数値と比較
3. 不一致を検出してレポート
"""

import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Tuple

class FactChecker:
    """ファクトチェッカー"""

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path
        self.facts = self._collect_facts()

    def _collect_facts(self) -> Dict[str, int]:
        """データベースから事実を収集"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        facts = {
            'total_persons': self._get_single_value(cursor,
                "SELECT COUNT(*) FROM persons"),

            'bracket_display_count': self._get_single_value(cursor,
                "SELECT COUNT(*) FROM persons WHERE show_group_in_bracket = 1"),

            'fictional_characters': self._get_single_value(cursor,
                "SELECT COUNT(*) FROM persons WHERE entity_type = 'fictional_character'"),

            'real_persons': self._get_single_value(cursor,
                "SELECT COUNT(*) FROM persons WHERE entity_type = 'real_person'"),

            'uninvestigated_count': self._get_single_value(cursor,
                "SELECT COUNT(*) FROM persons WHERE show_group_in_bracket = 0"),
        }

        conn.close()
        return facts

    def _get_single_value(self, cursor, query: str) -> int:
        """単一値を取得"""
        cursor.execute(query)
        return cursor.fetchone()[0]

    def check_document(self, doc_path: str) -> List[Tuple[str, str, str]]:
        """
        ドキュメントをチェック

        Returns:
            [(行番号, 誤った記述, 正しい記述), ...]
        """
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        errors = []

        # チェックパターン
        patterns = {
            r'3,?111人': (f"{self.facts['total_persons']:,}人", "総人物数"),
            r'3人キャラクター数"),
            r'2,?955人.*実在': (f"{self.facts['real_persons']:,}人", "実在人物数"),
            r'60件': (f"{self.facts['bracket_display_count']}件", "調査済み件数"),
        }

        for pattern, (correct_value, description) in patterns.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                errors.append((
                    line_num,
                    match.group(0),
                    f"{correct_value} ({description})"
                ))

        return errors

    def check_all_docs(self, docs_dir: str = "claudedocs") -> Dict[str, List]:
        """すべてのドキュメントをチェック"""
        docs_path = Path(docs_dir)
        results = {}

        for doc_file in docs_path.glob("*.md"):
            errors = self.check_document(str(doc_file))
            if errors:
                results[doc_file.name] = errors

        return results

    def generate_report(self) -> str:
        """レポート生成"""
        report_lines = [
            "# ファクトチェック結果",
            "",
            f"**検証日**: {datetime.now().strftime('%Y年%m月%d日')}",
            "",
            "## データベース実数値",
            "",
            f"- 総人物数: **{self.facts['total_persons']:,}人**",
            f"- 括弧表示対象: **{self.facts['bracket_display_count']}人**",
            f"- 架空キャラクター: **{self.facts['fictional_characters']}人**",
            f"- 実在人物: **{self.facts['real_persons']:,}人**",
            f"- 未調査: **{self.facts['uninvestigated_count']:,}人**",
            "",
        ]

        # ドキュメントチェック結果
        check_results = self.check_all_docs()

        if check_results:
            report_lines.append("## ⚠️ ドキュメント内の誤記")
            report_lines.append("")

            for doc_name, errors in check_results.items():
                report_lines.append(f"### {doc_name}")
                report_lines.append("")
                for line_num, wrong_text, correct_text in errors:
                    report_lines.append(f"- 行{line_num}: `{wrong_text}` → `{correct_text}`")
                report_lines.append("")
        else:
            report_lines.append("## ✅ すべてのドキュメントが正確")

        return '\n'.join(report_lines)


def main():
    """メイン処理"""
    checker = FactChecker()

    # レポート生成
    report = checker.generate_report()
    print(report)

    # ファイル保存
    output_path = f"claudedocs/fact_check_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nレポートを保存: {output_path}")


if __name__ == '__main__':
    from datetime import datetime
    main()
```

---

## 📋 今後のファクトチェック強化策

### 1. CI/CD統合 🆕
```yaml
# .github/workflows/fact-check.yml
name: Fact Check

on:
  push:
    paths:
      - 'claudedocs/**/*.md'

jobs:
  fact-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Fact Checker
        run: python scripts/fact_checker.py
      - name: Fail if errors found
        run: exit 1 if errors
```

### 2. 自動修正スクリプト 🆕
```python
def auto_fix_document(doc_path: str, facts: Dict[str, int]):
    """ドキュメントを自動修正"""
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 置換パターン
    replacements = {
        r'3,?111人': f"{facts['total_persons']:,}人",
        r'3人キャラクター",
        # ...
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)

    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
```

### 3. データベース実数値の定期的な記録 🆕
```python
# scripts/record_database_stats.py
def record_stats():
    """データベース統計を記録"""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'total_persons': get_count("SELECT COUNT(*) FROM persons"),
        'bracket_display': get_count("SELECT COUNT(*) FROM persons WHERE show_group_in_bracket = 1"),
        # ...
    }

    # JSONに追記
    with open('database_stats_history.json', 'a') as f:
        f.write(json.dumps(stats) + '\n')
```

### 4. ドキュメント作成時のテンプレート使用 🆕
```python
# templates/document_template.md
# データベース統計（自動生成）

**更新日**: {{timestamp}}
**総人物数**: {{total_persons}}人
**括弧表示対象**: {{bracket_display_count}}人

# この値は自動生成されます。手動で編集しないでください。
```

---

## ✅ 修正完了チェックリスト

- [ ] すべてのドキュメントで `3,110人` → `3,110人` に修正
- [ ] `expand_metadata_phase1.py` のカラム名修正
- [ ] `expand_metadata_phase1.py` の優先度ロジック修正
- [ ] ファクトチェックスクリプト作成
- [ ] データベース統計の自動記録スクリプト作成
- [ ] CI/CD統合（GitHub Actions）
- [ ] 修正版ドキュメントの再生成

---

**作成日**: 2025年10月2日
**検証者**: Claude Code
**次のアクション**: 修正版ドキュメントの作成
