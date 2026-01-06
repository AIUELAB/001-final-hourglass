#!/usr/bin/env python3
"""
Hybrid Generator CLI

ハイブリッドエピソード生成システムのコマンドラインインターフェース。
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.hybrid_generator.adapters import Candidate
from scripts.hybrid_generator.config import LOGS_DIR, MASTER_CSV, Strategy
from scripts.hybrid_generator.orchestrator import HybridOrchestrator, create_orchestrator

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    """引数をパース"""
    parser = argparse.ArgumentParser(
        description="ハイブリッドエピソード生成システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # dry-runで10件生成
  python cli.py --strategy epgen_first --target 10 --dry-run

  # 実際に1件生成
  python cli.py --strategy epgen_first --target 1 --execute

  # 推奨候補を表示
  python cli.py --recommend 10

  # A/B比較モード
  python cli.py --strategy ab_compare --target 5 --dry-run
        """,
    )

    parser.add_argument(
        "--strategy",
        type=str,
        default="epgen_first",
        choices=["epgen_first", "legacy_first", "ab_compare"],
        help="生成戦略 (default: epgen_first)",
    )

    parser.add_argument(
        "--target",
        type=int,
        default=10,
        help="目標生成数 (default: 10)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="dry-runモード（実際に書き込まない）",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に書き込む（--dry-runを無効化）",
    )

    parser.add_argument(
        "--recommend",
        type=int,
        default=0,
        help="推奨候補を表示（件数を指定）",
    )

    parser.add_argument(
        "--person",
        type=str,
        nargs="+",
        help="特定の人物名を指定して生成",
    )

    parser.add_argument(
        "--age",
        type=int,
        help="年齢を指定（--personと併用）",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを出力",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="結果をJSON形式で出力",
    )

    return parser.parse_args()


def find_candidates_by_name(orchestrator: HybridOrchestrator, names: list[str], age: int = None) -> list[Candidate]:
    """
    人物名から候補を検索

    Args:
        orchestrator: オーケストレータ
        names: 人物名リスト
        age: 年齢（オプション）

    Returns:
        list[Candidate]: 候補リスト
    """
    import pandas as pd

    candidates = []
    master_df = orchestrator.master_df

    for name in names:
        # 名前で検索
        matches = master_df[master_df["person_name"].str.contains(name, na=False)]

        if matches.empty:
            logger.warning(f"人物が見つかりません: {name}")
            continue

        # 最初のマッチを使用
        row = matches.iloc[0]
        person_id = row["person_id"]
        person_name = row["person_name"]
        category = row.get("category", "その他")
        person_type = row.get("person_type", "REAL")
        birth_year = row.get("birth_year")
        death_year = row.get("death_year")

        # 年齢を決定
        if age is not None:
            selected_age = age
        else:
            # 既存の年齢を除外して選定
            existing_ages = set(matches["age"].dropna().astype(int))
            available_ages = [a for a in [30, 35, 40, 45, 50] if a not in existing_ages]
            selected_age = available_ages[0] if available_ages else 40

        candidates.append(
            Candidate(
                person_id=person_id,
                person_name=person_name,
                age=selected_age,
                category=category,
                person_type=person_type,
                birth_year=int(birth_year) if not pd.isna(birth_year) else None,
                death_year=int(death_year) if death_year and not pd.isna(death_year) else None,
            )
        )

    return candidates


def main():
    """メイン処理"""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # dry-runフラグの処理
    dry_run = not args.execute

    # オーケストレータ作成
    orchestrator = create_orchestrator(
        strategy=args.strategy,
        dry_run=dry_run,
        target_count=args.target,
    )

    # 推奨候補の表示
    if args.recommend > 0:
        candidates = orchestrator.get_recommended_candidates(args.recommend)
        print(f"\n推奨候補 ({len(candidates)}件):")
        print("-" * 60)
        for c in candidates:
            print(f"  {c.person_name} ({c.age}歳) - {c.category}")
        return

    # 候補を決定
    if args.person:
        candidates = find_candidates_by_name(orchestrator, args.person, args.age)
        if not candidates:
            logger.error("有効な候補が見つかりません")
            return
    else:
        candidates = orchestrator.get_recommended_candidates(args.target)

    if not candidates:
        logger.error("候補が見つかりません")
        return

    # 実行
    print(f"\n{'='*60}")
    print("ハイブリッドエピソード生成")
    print(f"{'='*60}")
    print(f"戦略: {args.strategy}")
    print(f"候補数: {len(candidates)}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print(f"{'='*60}\n")

    run = orchestrator.run(candidates, dry_run=dry_run)

    # 結果出力
    if args.json:
        print(json.dumps(run.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print("実行結果")
        print(f"{'='*60}")
        print(f"実行ID: {run.run_id}")
        print(f"生成数: {run.generated_count}")
        print(f"採用数: {run.accepted_count}")
        print(f"棄却数: {run.rejected_count}")
        print(f"採用率: {run.accepted_count / run.generated_count * 100:.1f}%" if run.generated_count > 0 else "N/A")

        if run.write_result:
            print("\n書き込み結果:")
            print(f"  追加: {run.write_result.added_count}件")
            print(f"  スキップ: {run.write_result.skipped_count}件")
            if run.write_result.backup_path:
                print(f"  バックアップ: {run.write_result.backup_path}")
            if run.write_result.diff_log_path:
                print(f"  差分ログ: {run.write_result.diff_log_path}")

        if run.results:
            print("\n採用エピソード:")
            for r in run.results[:5]:  # 最大5件表示
                score = r.evaluation.super_total_score if r.evaluation else 0
                print(f"  - {r.candidate.person_name} ({r.candidate.age}歳): {score:.0f}")

        if run.rejections and args.verbose:
            print("\n棄却理由:")
            for rej in run.rejections[:10]:  # 最大10件表示
                print(f"  - {rej['person_name']}: {rej['reason']} - {rej['message']}")

    # ログパス
    log_path = LOGS_DIR / f"run_{run.run_id}.json"
    print(f"\n詳細ログ: {log_path}")


if __name__ == "__main__":
    main()
