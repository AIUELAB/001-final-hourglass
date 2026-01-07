#!/usr/bin/env python3
"""
SAGE CLI - Smart Adaptive Generation Engine

高品質エピソード生成システムのコマンドラインインターフェース。
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

from scripts.sage.adapters import Candidate
from scripts.sage.config import LOGS_DIR, MASTER_CSV, Strategy, HybridConfig
from scripts.sage.orchestrator import HybridOrchestrator, create_orchestrator
from scripts.sage.async_orchestrator import AsyncOrchestrator, AsyncConfig

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    """引数をパース"""
    parser = argparse.ArgumentParser(
        description="SAGE - Smart Adaptive Generation Engine",
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

    parser.add_argument(
        "--mock",
        action="store_true",
        help="モックアダプターを使用（API不要でテスト）",
    )

    # Phase 8: 最適化オプション
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="非同期並列処理を有効化（3-4倍高速化）",
    )

    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="非同期処理の同時実行数 (default: 10)",
    )

    parser.add_argument(
        "--fictional",
        action="store_true",
        help="架空キャラを含める（デフォルトはREALのみ）",
    )

    # Phase 9: Batch API オプション
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch API モード（50%%コスト削減、結果は後で取得）",
    )

    parser.add_argument(
        "--batch-submit",
        type=int,
        metavar="COUNT",
        help="バッチリクエストを送信（件数を指定）",
    )

    parser.add_argument(
        "--batch-status",
        type=str,
        metavar="BATCH_ID",
        help="バッチステータスを確認",
    )

    parser.add_argument(
        "--batch-results",
        type=str,
        metavar="BATCH_ID",
        help="バッチ結果を取得",
    )

    parser.add_argument(
        "--batch-list",
        action="store_true",
        help="保留中のバッチジョブをリスト",
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

    # Phase 8: 設定作成
    config = HybridConfig(
        strategy=Strategy(args.strategy),
        dry_run=dry_run,
        target_count=args.target,
        use_mock=args.mock,
        fictional_enabled=args.fictional,  # デフォルトFalse = REALのみ
        async_enabled=args.use_async,
        max_concurrent=args.max_concurrent,
    )

    # オーケストレータ作成（非同期 or 同期）
    if args.use_async:
        async_config = AsyncConfig(max_concurrent=args.max_concurrent)
        orchestrator = AsyncOrchestrator(config, async_config)
        logger.info(f"非同期モード有効: max_concurrent={args.max_concurrent}")
    else:
        orchestrator = HybridOrchestrator(config)

    # Phase 9: Batch API 処理
    if args.batch_list:
        from scripts.sage.batch_processor import BatchProcessor

        processor = BatchProcessor(config)
        jobs = processor.list_pending_jobs()
        print(f"\n保留中のバッチジョブ ({len(jobs)}件):")
        for job in jobs:
            print(f"  {job['batch_id']} - {job['request_count']}件 - {job['created_at']}")
        return

    if args.batch_status:
        import asyncio
        from scripts.sage.batch_processor import BatchProcessor

        processor = BatchProcessor(config)
        job = asyncio.run(processor.check_status(args.batch_status))
        print(f"\nバッチステータス: {args.batch_status}")
        print(f"  状態: {job.status}")
        print(f"  成功: {job.succeeded_count}/{job.request_count}")
        print(f"  失敗: {job.failed_count}")
        return

    if args.batch_results:
        import asyncio
        from scripts.sage.batch_processor import BatchProcessor

        processor = BatchProcessor(config)
        results = asyncio.run(processor.get_results(args.batch_results))
        print(f"\nバッチ結果 ({len(results)}件):")
        for r in results:
            status = "成功" if r.get("text") else f"失敗: {r.get('error', 'unknown')}"
            print(f"  {r['custom_id']}: {status}")
        return

    if args.batch_submit or (args.batch and args.execute):
        # Phase 9: Batch API統合（50%コスト削減）
        import asyncio

        from scripts.sage.batch_processor import BatchProcessor, create_batch_request

        # --execute --batch の場合は args.target を使用
        batch_count = args.batch_submit if args.batch_submit else args.target

        processor = BatchProcessor(config)

        # 候補を取得（--person指定時はそれを使用）
        if args.person:
            batch_candidates = find_candidates_by_name(orchestrator, args.person, args.age)
        else:
            batch_candidates = orchestrator.get_recommended_candidates(batch_count)
        if not batch_candidates:
            logger.error("バッチ用の候補が見つかりません")
            return

        # プロンプトビルダーを取得（EPGENの本格的なプロンプト）
        try:
            from scripts.generate.mass_production.generator import (
                GenerationInput,
                create_prompt_builder,
            )

            prompt_builder = create_prompt_builder(compact=config.use_compact_prompt)
        except ImportError:
            logger.warning("プロンプトビルダーが見つかりません。簡易プロンプトを使用します。")
            prompt_builder = None
            GenerationInput = None

        # Phase 5: 象徴的業績マスターデータをロード（Batch用）
        iconic_data = {}
        try:
            import json
            from pathlib import Path

            iconic_path = Path(__file__).parent.parent.parent / "preserved" / "data" / "iconic_achievements_master.json"
            if iconic_path.exists():
                with open(iconic_path, encoding="utf-8") as f:
                    iconic_data = json.load(f).get("persons", {})
                logger.info(f"象徴的業績データ読み込み: {len(iconic_data)}名")
        except Exception as e:
            logger.warning(f"象徴的業績データ読み込み失敗: {e}")

        def get_iconic_context(person_name: str, age: int) -> str:
            """象徴的業績コンテキストを取得（Batch用）"""
            person_data = iconic_data.get(person_name)
            if not person_data:
                return ""

            matches = []
            for ep in person_data.get("required_episodes", []):
                ep_age = ep.get("age", 0)
                if abs(ep_age - age) <= 2:  # ±2歳でマッチ
                    achievement = ep.get("achievement", "")
                    year = ep.get("year", "")
                    keywords = ", ".join(ep.get("keywords", []))
                    matches.append(f"- {achievement}（{year}年） キーワード: {keywords}")

            if not matches:
                return ""

            return (
                "【象徴的業績ガイド】この年齢に関連する重要な出来事:\n"
                + "\n".join(matches)
                + "\n上記の具体的な事実を盛り込んだエピソードを生成してください。"
            )

        # バッチリクエストを作成
        requests = []
        iconic_count = 0
        for c in batch_candidates:
            # Phase 5: 象徴的コンテキストを取得
            iconic_context = get_iconic_context(c.person_name, c.age)
            if iconic_context:
                iconic_count += 1

            if prompt_builder and GenerationInput:
                # EPGENの本格的なプロンプト
                gen_input = GenerationInput(
                    person_id=c.person_id,
                    person_name=c.person_name,
                    age=c.age,
                    category=c.category,
                    birth_year=getattr(c, "birth_year", None),
                    death_year=getattr(c, "death_year", None),
                )
                prompt = prompt_builder.build(gen_input)
                # Phase 5: 象徴的コンテキストをプロンプトに注入
                if iconic_context:
                    prompt = f"{iconic_context}\n\n{prompt}"
            else:
                # フォールバック: 簡易プロンプト
                base_prompt = f"{c.person_name}の{c.age}歳時のエピソードを生成してください。カテゴリ: {c.category}"
                prompt = f"{iconic_context}\n\n{base_prompt}" if iconic_context else base_prompt

            req = create_batch_request(
                person_name=c.person_name,
                age=c.age,
                category=c.category,
                prompt=prompt,
                model=config.generation_model,
            )
            requests.append(req)

        # バッチ送信
        job = asyncio.run(processor.submit_batch(requests))
        print("\n" + "=" * 60)
        print("Batch API 送信完了（50%コスト削減モード）")
        print("=" * 60)
        print(f"バッチID: {job.batch_id}")
        print(f"リクエスト数: {job.request_count}")
        print(f"ステータス: {job.status}")
        print(f"プロンプト: {'EPGEN本格版' if prompt_builder else '簡易版'}")
        print(f"象徴的コンテキスト注入: {iconic_count}/{len(batch_candidates)}件")
        print("\n結果を取得するには:")
        print(f"  python scripts/sage/cli.py --batch-status {job.batch_id}")
        print(f"  python scripts/sage/cli.py --batch-results {job.batch_id}")
        print("\n注意: 結果は通常2-24時間後に取得可能になります。")
        return

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
    print(f"\n{'=' * 60}")
    print("SAGE - Smart Adaptive Generation Engine")
    print(f"{'=' * 60}")
    print(f"戦略: {args.strategy}")
    print(f"候補数: {len(candidates)}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print(f"処理: {'非同期' if args.use_async else '同期'}")
    print(f"架空キャラ: {'含む' if args.fictional else '除外'}")
    print(f"{'=' * 60}\n")

    # Phase 8: 非同期/同期の切り替え
    if args.use_async:
        run = orchestrator.run_sync(candidates, dry_run=dry_run)
    else:
        run = orchestrator.run(candidates, dry_run=dry_run)

    # 結果出力
    if args.json:
        print(json.dumps(run.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("実行結果")
        print(f"{'=' * 60}")
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
