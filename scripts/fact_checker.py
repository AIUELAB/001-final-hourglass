#!/usr/bin/env python3
"""
ファクトチェックスクリプト

目的:
1. データベースから実数値を取得
2. ドキュメント内の数値と比較
3. 不一致を検出してレポート
4. 自動修正（オプション）
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List


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
            "total_persons": self._get_single_value(cursor, "SELECT COUNT(*) FROM persons"),
            "bracket_display_count": self._get_single_value(
                cursor, "SELECT COUNT(*) FROM persons WHERE show_group_in_bracket = 1"
            ),
            "fictional_characters": self._get_single_value(
                cursor, "SELECT COUNT(*) FROM persons WHERE entity_type = 'fictional_character'"
            ),
            "real_persons": self._get_single_value(
                cursor, "SELECT COUNT(*) FROM persons WHERE entity_type = 'real_person'"
            ),
            "uninvestigated_count": self._get_single_value(
                cursor, "SELECT COUNT(*) FROM persons WHERE show_group_in_bracket = 0"
            ),
            "recognition_score_set": self._get_single_value(
                cursor, "SELECT COUNT(*) FROM persons WHERE recognition_score > 0"
            ),
        }

        # 計算値
        facts["bracket_display_rate"] = round((facts["bracket_display_count"] / facts["total_persons"]) * 100, 1)

        conn.close()

        print("=" * 80)
        print("データベース実数値（ファクト）")
        print("=" * 80)
        for key, value in facts.items():
            print(f"{key}: {value:,}" if isinstance(value, int) else f"{key}: {value}")
        print("=" * 80)

        return facts

    def _get_single_value(self, cursor, query: str) -> int:
        """単一値を取得"""
        cursor.execute(query)
        return cursor.fetchone()[0]

    def check_document(self, doc_path: str) -> List[Dict]:
        """
        ドキュメントをチェック

        Returns:
            [{
                'line_num': int,
                'wrong_text': str,
                'correct_text': str,
                'description': str
            }, ...]
        """
        with open(doc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        errors = []

        # チェックパターン（正規表現 → 正しい値）
        patterns = [
            # 総人物数
            {
                "pattern": r"3,?111人",
                "correct": f"{self.facts['total_persons']:,}人",
                "description": "総人物数",
                "exclude": ["計算", "例"],  # この文字が含まれる行は除外
            },
            # 架空キャラクター
            {
                "pattern": r"156人.*架空",
                "correct": f"{self.facts['fictional_characters']}人",
                "description": "架空キャラクター数",
                "exclude": [],
            },
            # 実在人物
            {
                "pattern": r"2,?955人.*実在",
                "correct": f"{self.facts['real_persons']:,}人",
                "description": "実在人物数",
                "exclude": [],
            },
            # メタデータ調査済み
            {
                "pattern": r"69件.*メタデータ",
                "correct": f"{self.facts['bracket_display_count']}件",
                "description": "メタデータ調査済み件数",
                "exclude": [],
            },
            # 未調査
            {
                "pattern": r"3,?041件.*未",
                "correct": f"{self.facts['uninvestigated_count']:,}件",
                "description": "未調査件数",
                "exclude": [],
            },
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                exclude_words = pattern_info["exclude"]

                # 除外ワードチェック
                if any(word in line for word in exclude_words):
                    continue

                match = re.search(pattern, line)
                if match:
                    errors.append(
                        {
                            "line_num": line_num,
                            "line_content": line.strip(),
                            "wrong_text": match.group(0),
                            "correct_text": pattern_info["correct"],
                            "description": pattern_info["description"],
                        }
                    )

        return errors

    def check_all_docs(self, docs_dir: str = "claudedocs") -> Dict[str, List]:
        """すべてのドキュメントをチェック"""
        docs_path = Path(docs_dir)

        if not docs_path.exists():
            print(f"警告: {docs_dir} ディレクトリが存在しません")
            return {}

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
            f"**検証日**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            "",
            "## 📊 データベース実数値（ソース・オブ・トゥルース）",
            "",
            "| 項目 | 値 |",
            "|------|-----|",
            f"| 総人物数 | **{self.facts['total_persons']:,}人** |",
            f"| 括弧表示対象 | **{self.facts['bracket_display_count']}人** ({self.facts['bracket_display_rate']}%) |",
            f"| 未調査 | **{self.facts['uninvestigated_count']:,}人** |",
            f"| 架空キャラクター | **{self.facts['fictional_characters']}人** |",
            f"| 実在人物 | **{self.facts['real_persons']:,}人** |",
            f"| recognition_score設定済み | **{self.facts['recognition_score_set']}人** |",
            "",
            "---",
            "",
        ]

        # ドキュメントチェック結果
        check_results = self.check_all_docs()

        if check_results:
            report_lines.append("## ⚠️ ドキュメント内の誤記")
            report_lines.append("")
            report_lines.append(f"**検出件数**: {sum(len(errors) for errors in check_results.values())}件")
            report_lines.append("")

            for doc_name, errors in check_results.items():
                report_lines.append(f"### {doc_name}")
                report_lines.append("")
                for error in errors:
                    report_lines.append(f"- **行{error['line_num']}**: {error['description']}")
                    report_lines.append(f"  - 誤: `{error['wrong_text']}`")
                    report_lines.append(f"  - 正: `{error['correct_text']}`")
                    report_lines.append(f"  - 内容: {error['line_content'][:80]}...")
                    report_lines.append("")
        else:
            report_lines.append("## ✅ すべてのドキュメントが正確")
            report_lines.append("")
            report_lines.append("検証したドキュメント内で数値の誤記は検出されませんでした。")

        return "\n".join(report_lines)

    def auto_fix_documents(self, docs_dir: str = "claudedocs", dry_run: bool = True):
        """
        ドキュメントを自動修正

        Args:
            docs_dir: ドキュメントディレクトリ
            dry_run: True = 修正内容を表示のみ、False = 実際に修正
        """
        check_results = self.check_all_docs(docs_dir)

        if not check_results:
            print("✅ 修正が必要なドキュメントはありません")
            return

        for doc_name, errors in check_results.items():
            doc_path = Path(docs_dir) / doc_name

            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 修正を適用
            fixed_content = content
            for error in errors:
                fixed_content = fixed_content.replace(error["wrong_text"], error["correct_text"])

            if dry_run:
                print(f"\n📄 {doc_name}:")
                print(f"  修正箇所: {len(errors)}件")
                for error in errors:
                    print(f"  - 行{error['line_num']}: {error['wrong_text']} → {error['correct_text']}")
            else:
                # 実際に保存
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                print(f"✅ 修正完了: {doc_name} ({len(errors)}箇所)")

    def save_stats_history(self, output_path: str = "database_stats_history.jsonl"):
        """データベース統計を履歴として保存"""
        stats = {"timestamp": datetime.now().isoformat(), **self.facts}

        # JSONL形式で追記
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats, ensure_ascii=False) + "\n")

        print(f"📊 統計を保存: {output_path}")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="ファクトチェックスクリプト")
    parser.add_argument("--db", default="episode_database.db", help="データベースパス")
    parser.add_argument("--fix", action="store_true", help="自動修正を実行（デフォルトはdry-run）")
    parser.add_argument("--save-history", action="store_true", help="統計履歴を保存")

    args = parser.parse_args()

    # ファクトチェッカー初期化
    checker = FactChecker(db_path=args.db)

    # レポート生成
    report = checker.generate_report()
    print("\n" + report)

    # ファイル保存
    output_path = f"claudedocs/fact_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📝 レポートを保存: {output_path}")

    # 自動修正
    if args.fix:
        print("\n" + "=" * 80)
        print("自動修正を実行中...")
        print("=" * 80)
        checker.auto_fix_documents(dry_run=False)
    else:
        print("\n" + "=" * 80)
        print("自動修正プレビュー（dry-run）")
        print("=" * 80)
        checker.auto_fix_documents(dry_run=True)
        print("\n実際に修正するには --fix オプションを使用してください")

    # 統計履歴を保存
    if args.save_history:
        checker.save_stats_history()


if __name__ == "__main__":
    main()
