#!/usr/bin/env python3
"""
新規有名人自動発見バッチスクリプト

定期的に新規有名人を発見・追加するためのバッチスクリプト。
GitHub Actions または cron から実行。

使用例:
    # dry-run
    python scripts/batch/discover_persons.py

    # 実際に追加
    python scripts/batch/discover_persons.py --execute

    # Wikidata戦略のみ
    python scripts/batch/discover_persons.py --strategy wikidata --execute
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.person_discovery_engine import (
    DiscoveryConfig,
    DiscoveryStrategy,
    PersonDiscoveryEngine,
)

logger = logging.getLogger(__name__)


def parse_args():
    """引数をパース"""
    parser = argparse.ArgumentParser(
        description="新規有名人自動発見バッチスクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--strategy",
        type=str,
        choices=["wikidata", "llm", "web_search", "combined"],
        default="combined",
        help="発見戦略（default: combined）",
    )

    parser.add_argument(
        "--min-sitelinks",
        type=int,
        default=30,
        help="最小sitelinks数（default: 30）",
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        default=10,
        help="最大発見候補数（default: 10）",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際にCSVに追加（指定しない場合はdry-run）",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを出力",
    )

    return parser.parse_args()


def main():
    """メイン処理"""
    args = parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    dry_run = not args.execute

    print("=" * 60)
    print("新規有名人自動発見バッチ")
    print("=" * 60)
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"戦略: {args.strategy}")
    print(f"最小sitelinks: {args.min_sitelinks}")
    print(f"最大候補数: {args.max_candidates}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print("=" * 60)
    print()

    # 設定
    config = DiscoveryConfig(
        strategy=DiscoveryStrategy(args.strategy),
        min_sitelinks=args.min_sitelinks,
        max_candidates=args.max_candidates,
        dry_run=dry_run,
    )

    # エンジン作成・実行
    engine = PersonDiscoveryEngine(config)

    try:
        report = engine.run(dry_run=dry_run)
    except Exception as e:
        logger.error(f"発見エラー: {e}")
        print(f"\n❌ エラー: {e}")
        sys.exit(1)

    # 結果表示
    print()
    print("=" * 60)
    print("結果サマリー")
    print("=" * 60)
    print(f"発見候補数: {report.discovered_count}")
    print(f"追加数: {report.added_count}")
    print(f"スキップ数: {report.skipped_count}")

    if report.candidates:
        print("\n追加候補:")
        for c in report.candidates:
            status = "✓" if any(r["name"] == c["name"] and r["success"] for r in report.results) else "✗"
            print(f"  {status} {c['name']} ({c['category']}) sitelinks={c['sitelinks']}")

    # レポート保存
    report_path = engine.save_report(report)
    print(f"\nレポート保存: {report_path}")

    # GitHub Actions用出力
    if "GITHUB_OUTPUT" in __import__("os").environ:
        output_file = Path(__import__("os").environ["GITHUB_OUTPUT"])
        with open(output_file, "a") as f:
            f.write(f"discovered_count={report.discovered_count}\n")
            f.write(f"added_count={report.added_count}\n")
            f.write(f"report_path={report_path}\n")

    # 終了コード
    if report.added_count > 0 or dry_run:
        print("\n✅ 完了")
        sys.exit(0)
    else:
        print("\n⚠️ 追加候補なし")
        sys.exit(0)


if __name__ == "__main__":
    main()
