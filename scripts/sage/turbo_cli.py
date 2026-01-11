"""
SAGE Turbo CLI

Batch APIを使用したエピソード生成のCLI。

使用例:
    # バッチ送信（100件）
    python -m scripts.sage.turbo_cli submit --count 100

    # 進捗バー付き監視（おすすめ）
    python -m scripts.sage.turbo_cli watch --batch-id <batch_id>

    # ステータス確認（1回のみ）
    python -m scripts.sage.turbo_cli status --batch-id <batch_id>

    # 保留中のジョブ一覧
    python -m scripts.sage.turbo_cli list

    # 結果取得
    python -m scripts.sage.turbo_cli retrieve --batch-id <batch_id>
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.turbo_engine import TurboEngine, TurboConfig
from scripts.sage.batch_processor import BatchProcessor
from scripts.sage.config import Strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_submit(args):
    """バッチジョブを送信"""
    # Phase 21統合: --sonnet指定時はHaiku無効
    use_haiku = not getattr(args, "sonnet", False)
    model_name = "Haiku" if use_haiku else "Sonnet"

    logger.info("=== SAGE Turbo Batch Submit ===")
    fictional_enabled = getattr(args, "fictional", False)

    logger.info(f"件数: {args.count}")
    logger.info(f"モデル: {model_name} (Phase 21統合)")
    logger.info(f"架空キャラ: {'有効' if fictional_enabled else '無効'} (Phase 27)")
    logger.info(f"dry-run: {args.dry_run}")

    config = TurboConfig(
        dry_run=args.dry_run,
        use_mock=args.mock,
        fictional_enabled=fictional_enabled,
    )

    engine = TurboEngine(config)
    batch_id = engine.submit_batch_job(count=args.count, use_haiku=use_haiku)

    if batch_id:
        logger.info("")
        logger.info("✓ バッチ送信成功!")
        logger.info(f"  batch_id: {batch_id}")
        logger.info("")
        logger.info("結果取得コマンド:")
        logger.info(f"  python -m scripts.sage.turbo_cli retrieve --batch-id {batch_id}")
        logger.info("")
        logger.info("ステータス確認:")
        logger.info(f"  python -m scripts.sage.turbo_cli status --batch-id {batch_id}")
    else:
        logger.error("バッチ送信に失敗しました")
        return 1

    return 0


def cmd_status(args):
    """バッチジョブのステータスを確認"""
    if not args.batch_id:
        logger.error("--batch-id を指定してください")
        return 1

    logger.info(f"=== Batch Status: {args.batch_id} ===")

    config = TurboConfig(dry_run=True)
    engine = TurboEngine(config)
    status = engine.check_batch_status(args.batch_id)

    print(json.dumps(status, indent=2, ensure_ascii=False))

    if status.get("status") == "ended":
        logger.info("")
        logger.info("✓ 処理完了! 結果取得コマンド:")
        logger.info(f"  python -m scripts.sage.turbo_cli retrieve --batch-id {args.batch_id}")

    return 0


def cmd_list(args):
    """保留中のジョブを一覧表示"""
    logger.info("=== Pending Batch Jobs ===")

    processor = BatchProcessor()
    jobs = processor.list_pending_jobs()

    if not jobs:
        logger.info("保留中のジョブはありません")
        return 0

    for job in jobs:
        print(f"  - {job.get('batch_id', 'N/A')}")
        print(f"    created_at: {job.get('created_at', 'N/A')}")
        print(f"    request_count: {job.get('request_count', 0)}")
        print()

    return 0


def cmd_watch(args):
    """バッチジョブの進捗をリアルタイム表示"""
    if not args.batch_id:
        logger.error("--batch-id を指定してください")
        return 1

    config = TurboConfig(dry_run=True)
    engine = TurboEngine(config)

    interval = args.interval
    bar_width = 40

    print(f"\n🔄 バッチ監視開始: {args.batch_id}")
    print(f"   更新間隔: {interval}秒 (Ctrl+C で終了)\n")

    try:
        while True:
            status = engine.check_batch_status(args.batch_id)

            total = status.get("request_count", 0)
            succeeded = status.get("succeeded_count", 0)
            failed = status.get("failed_count", 0)
            expired = status.get("expired_count", 0)
            canceled = status.get("canceled_count", 0)
            completed = succeeded + failed + expired + canceled

            if total > 0:
                progress = completed / total
                filled = int(bar_width * progress)
                bar = "█" * filled + "░" * (bar_width - filled)
                pct = progress * 100

                # 進捗バー表示
                status_icon = "✓" if status.get("status") == "ended" else "⏳"
                print(f"\r  {status_icon} [{bar}] {pct:5.1f}% ({completed}/{total})", end="", flush=True)

                # 詳細（失敗があれば表示）
                if failed > 0 or expired > 0:
                    print(f" | ❌{failed} ⏰{expired}", end="", flush=True)

            # 完了チェック
            if status.get("status") == "ended":
                print("\n\n✅ 処理完了!")
                print(f"   成功: {succeeded}件")
                if failed > 0:
                    print(f"   失敗: {failed}件")
                print("\n結果取得コマンド:")
                print(f"   python -m scripts.sage.turbo_cli retrieve --batch-id {args.batch_id} --write")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⚠️  監視を中断しました")
        return 0

    return 0


def cmd_retrieve(args):
    """バッチ結果を取得して処理"""
    if not args.batch_id:
        logger.error("--batch-id を指定してください")
        return 1

    logger.info(f"=== Batch Retrieve: {args.batch_id} ===")

    config = TurboConfig(
        dry_run=args.dry_run,
    )

    engine = TurboEngine(config)

    # Phase 23: --write オプションで本番書き込み
    write_to_csv = getattr(args, "write", False)
    if write_to_csv:
        logger.info("⚠️  本番書き込みモード: マスターCSVに追記します")

    result = engine.retrieve_batch_results(
        args.batch_id,
        wait=args.wait,
        write_to_csv=write_to_csv,
    )

    if result:
        logger.info("")
        logger.info("=== 処理結果 ===")
        logger.info(f"  accepted: {result.accepted_count}")
        logger.info(f"  rejected: {result.rejected_count}")
        logger.info(f"  dry_run: {result.dry_run}")
        if write_to_csv:
            logger.info("  write_to_csv: True (マスターCSVに書き込み済み)")
        logger.info("")
        logger.info(f"詳細は src/reports/logs/batch_jobs/{args.batch_id}_processed.json を参照")
    else:
        logger.info("結果はまだ準備できていません (--wait で待機可能)")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="SAGE Turbo Batch API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # submit
    submit_parser = subparsers.add_parser("submit", help="バッチジョブを送信")
    submit_parser.add_argument("--count", type=int, default=100, help="生成件数 (default: 100)")
    submit_parser.add_argument("--dry-run", action="store_true", default=True, help="ドライラン (default: True)")
    submit_parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="実際にCSVに書き込む")
    submit_parser.add_argument("--mock", action="store_true", help="モックモード（API不使用）")
    submit_parser.add_argument(
        "--haiku",
        action="store_true",
        default=True,
        help="Haikuモデル使用（Phase 21統合、デフォルト有効）",
    )
    submit_parser.add_argument("--sonnet", action="store_true", help="Sonnetモデル使用（Haikuより高品質だが高コスト）")
    submit_parser.add_argument(
        "--fictional",
        action="store_true",
        help="Phase 27: 架空キャラ・動物を候補に含める（デフォルト: REALのみ）",
    )

    # status
    status_parser = subparsers.add_parser("status", help="ステータス確認")
    status_parser.add_argument("--batch-id", required=True, help="バッチID")

    # watch (進捗バー付き監視)
    watch_parser = subparsers.add_parser("watch", help="進捗バー付きでバッチを監視")
    watch_parser.add_argument("--batch-id", required=True, help="バッチID")
    watch_parser.add_argument("--interval", type=int, default=5, help="更新間隔（秒、default: 5）")

    # list
    list_parser = subparsers.add_parser("list", help="保留中ジョブ一覧")

    # retrieve
    retrieve_parser = subparsers.add_parser("retrieve", help="結果取得")
    retrieve_parser.add_argument("--batch-id", required=True, help="バッチID")
    retrieve_parser.add_argument("--wait", action="store_true", help="完了まで待機")
    retrieve_parser.add_argument("--dry-run", action="store_true", default=True, help="ドライラン (default: True)")
    retrieve_parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="実際にCSVに書き込む")
    retrieve_parser.add_argument("--write", action="store_true", help="Phase 23: マスターCSVに書き込み（本番モード）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "submit": cmd_submit,
        "status": cmd_status,
        "watch": cmd_watch,
        "list": cmd_list,
        "retrieve": cmd_retrieve,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
