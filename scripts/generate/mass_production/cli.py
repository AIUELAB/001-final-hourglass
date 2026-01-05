#!/usr/bin/env python3
"""
大量生産CLI

コマンドラインインターフェース
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import DEFAULT_CONFIG, MASTER_CSV_PATH, MassProductionConfig
from .pipeline import DryRunPipeline, MassProductionPipeline, PipelineResult

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """引数パーサー作成"""
    parser = argparse.ArgumentParser(
        prog="mass-production",
        description="高品質エピソード大量生産システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（分析のみ）
  python -m scripts.generate.mass_production.cli --dry-run --target 100

  # 本番実行（100件候補）
  python -m scripts.generate.mass_production.cli --target 100

  # カテゴリ指定実行
  python -m scripts.generate.mass_production.cli --target 50 --category "科学・技術"

  # 並列数指定
  python -m scripts.generate.mass_production.cli --target 100 --workers 30

  # 詳細ログ
  python -m scripts.generate.mass_production.cli --target 100 --verbose
""",
    )

    # 基本オプション
    parser.add_argument(
        "--target",
        "-t",
        type=int,
        default=500,
        help="目標候補数（デフォルト: 500）",
    )

    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default=None,
        help="カテゴリフィルタ",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="ドライラン（生成せず分析のみ）",
    )

    parser.add_argument(
        "--analyze-only",
        "-a",
        action="store_true",
        help="候補分析のみ（LLM呼び出しなし）",
    )

    # 設定オプション
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        help=f"並列ワーカー数（デフォルト: {DEFAULT_CONFIG.generation.max_workers}）",
    )

    parser.add_argument(
        "--candidates-per-input",
        type=int,
        default=None,
        help=f"入力あたり生成候補数（デフォルト: {DEFAULT_CONFIG.generation.candidates_per_input}）",
    )

    parser.add_argument(
        "--min-factual-density",
        type=float,
        default=None,
        help=f"最小事実密度（デフォルト: {DEFAULT_CONFIG.quality.min_factual_density}）",
    )

    parser.add_argument(
        "--min-generation-quality",
        type=float,
        default=None,
        help=f"最小生成品質（デフォルト: {DEFAULT_CONFIG.quality.min_generation_quality}）",
    )

    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=None,
        help=f"重複判定類似度閾値（デフォルト: {DEFAULT_CONFIG.quality.max_similarity_threshold}）",
    )

    # パスオプション
    parser.add_argument(
        "--master-csv",
        type=str,
        default=None,
        help=f"マスターCSVパス（デフォルト: {MASTER_CSV_PATH}）",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="出力ディレクトリ",
    )

    # 出力オプション
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="JSON形式で出力",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログ出力",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="最小限の出力",
    )

    # LLMオプション
    parser.add_argument(
        "--llm-provider",
        type=str,
        default="anthropic",
        choices=["anthropic", "openai", "gemini", "mock"],
        help="LLMプロバイダー（デフォルト: anthropic）",
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLMモデル名",
    )

    return parser


def build_config(args: argparse.Namespace) -> MassProductionConfig:
    """引数から設定を構築"""
    config = DEFAULT_CONFIG

    # 生成設定
    if args.workers is not None:
        config.generation.max_workers = args.workers
    if args.candidates_per_input is not None:
        config.generation.candidates_per_input = args.candidates_per_input

    # 品質ゲート設定
    if args.min_factual_density is not None:
        config.quality.min_factual_density = args.min_factual_density
    if args.min_generation_quality is not None:
        config.quality.min_generation_quality = args.min_generation_quality
    if args.similarity_threshold is not None:
        config.quality.max_similarity_threshold = args.similarity_threshold

    return config


def create_llm_client(args: argparse.Namespace):
    """LLMクライアント作成"""
    try:
        from .llm_clients import create_llm_client as factory

        return factory(
            provider=args.llm_provider,
            model=args.llm_model,
        )
    except (ImportError, ValueError) as e:
        if args.llm_provider != "mock":
            logger.warning(f"LLMクライアント作成失敗: {e}, モックを使用")
        from .generator import MockLLMClient

        return MockLLMClient(delay=0.05)


def run_analyze_only(
    args: argparse.Namespace,
    config: MassProductionConfig,
    master_csv_path: Path,
) -> int:
    """分析のみ実行"""
    dry_run = DryRunPipeline(config=config, master_csv_path=master_csv_path)
    analysis = dry_run.analyze(target_count=args.target)

    if args.json:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    else:
        print("\n=== 候補分析結果 ===")
        print(f"候補数: {analysis['candidates']}")
        print(f"推定生成数: {analysis['expected_generated']}")
        print(f"推定品質通過: {analysis['expected_passed_gate']}")
        print(f"推定最終出力: {analysis['expected_final']}")

        print("\nカテゴリ分布:")
        for cat, count in sorted(analysis["category_distribution"].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        print("\n選択理由分布:")
        for reason, count in sorted(analysis["reason_distribution"].items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")

        print("\n設定:")
        print(f"  並列ワーカー: {analysis['config']['max_workers']}")
        print(f"  入力あたり候補: {analysis['config']['candidates_per_input']}")
        print(f"  事実密度閾値: {analysis['config']['quality_thresholds']['factual_density']}")
        print(f"  生成品質閾値: {analysis['config']['quality_thresholds']['generation_quality']}")

    return 0


def run_pipeline(
    args: argparse.Namespace,
    config: MassProductionConfig,
    master_csv_path: Path,
) -> int:
    """パイプライン実行"""
    llm = create_llm_client(args)

    pipeline = MassProductionPipeline(
        llm_client=llm,
        config=config,
        master_csv_path=master_csv_path,
    )

    def progress_callback(stage: str, completed: int, total: int):
        if not args.quiet:
            print(f"\r[{stage}] {completed}/{total}", end="", flush=True)

    result = pipeline.run(
        target_count=args.target,
        category_filter=args.category,
        progress_callback=progress_callback if not args.quiet else None,
        dry_run=args.dry_run,
    )

    print()  # 改行

    if args.json:
        output = {
            "stats": result.stats.to_dict(),
            "output_path": str(result.output_path) if result.output_path else None,
            "episode_count": len(result.episodes),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(result.stats.summary())

        if result.output_path:
            print(f"出力ファイル: {result.output_path}")

    return 0 if result.stats.episodes_final > 0 else 1


def main(argv: Optional[list] = None) -> int:
    """メインエントリーポイント"""
    parser = create_parser()
    args = parser.parse_args(argv)

    # ロギングレベル設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    # 設定構築
    config = build_config(args)
    master_csv_path = Path(args.master_csv) if args.master_csv else MASTER_CSV_PATH

    # マスターCSV存在確認
    if not master_csv_path.exists():
        logger.error(f"マスターCSVが見つかりません: {master_csv_path}")
        return 1

    # 実行
    try:
        if args.analyze_only:
            return run_analyze_only(args, config, master_csv_path)
        else:
            return run_pipeline(args, config, master_csv_path)
    except KeyboardInterrupt:
        logger.info("中断されました")
        return 130
    except Exception as e:
        logger.exception(f"エラー: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
