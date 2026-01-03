#!/usr/bin/env python3
"""
Pipeline Stage 2: verify-sources - 根拠品質検証

このスクリプトはepisode_sources.csvから根拠品質を検証し、
検証済み（A/B品質）と却下（C品質・センシティブ）に分類します。

品質判定基準:
- A（一次情報）: 公式サイト、学術論文、自伝、インタビュー記録
- B（二次情報2+）: 信頼できる二次情報が2つ以上で一致
- C（未検証）: 単一ソース、出典不明

使用方法:
    # ドライラン（デフォルト）
    python scripts/pipeline_verify_sources.py \\
        --input generated/episode_sources.csv \\
        --output-verified generated/verified_sources.csv \\
        --output-rejected generated/rejected_sources.csv \\
        --dry-run

    # 本番実行
    python scripts/pipeline_verify_sources.py \\
        --input generated/episode_sources.csv \\
        --output-verified generated/verified_sources.csv \\
        --output-rejected generated/rejected_sources.csv \\
        --execute

作成日: 2025-12-17
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# PYTHONPATH設定（プロジェクトルートを追加）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

from src.csv_path_resolver import get_project_root
from src.sensitive_filter import SensitiveFilter
from src.source_adapters.base import PersonCandidate

# ロガー設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# A品質判定用ドメインパターン
A_QUALITY_DOMAINS = [
    r"\.go\.jp",  # 政府公式
    r"\.ac\.jp",  # 学術機関
    r"\.edu",  # 教育機関
    r"ndl\.go\.jp",  # 国会図書館
    r"\.gov",  # 政府系
    r"doi\.org",  # 学術論文DOI
    r"researchgate\.net",  # 研究者プラットフォーム
    r"scholar\.google",  # Google Scholar
]

# B品質判定用（Wikipedia専用チェック）
# Wikipedia自体は信頼できるが、参照文献の有無で品質を判定

# A品質判定用キーワードパターン
A_QUALITY_KEYWORDS = [
    "自伝",
    "回想録",
    "公式インタビュー",
    "公式伝記",
    "学術論文",
    "研究論文",
    "博士論文",
    "公式講演",
    "公式サイト",
]


def generate_source_id(person_name: str, source_url: str) -> str:
    """
    ソースIDをMD5ハッシュで生成

    Args:
        person_name: 人物名
        source_url: ソースURL

    Returns:
        source_id (例: SRC-a3f5b9c2d4e6f8a0)
    """
    composite_key = f"{person_name}||{source_url}"
    hash_digest = hashlib.md5(composite_key.encode("utf-8")).hexdigest()
    return f"SRC-{hash_digest[:16]}"


def is_duplicate_source(source_id: str, existing_df: pd.DataFrame) -> bool:
    """
    既存ソースとの重複をチェック

    Args:
        source_id: 検証対象のソースID
        existing_df: 既存ソースDataFrame

    Returns:
        True: 重複, False: 新規
    """
    if existing_df is None or existing_df.empty:
        return False
    return source_id in existing_df["source_id"].values


def load_blacklist(blacklist_path: Path) -> Tuple[List[str], List[str]]:
    """
    ブラックリストを読み込み

    Args:
        blacklist_path: blacklist_names.jsonのパス

    Returns:
        (names, patterns): 名前リストとパターンリスト
    """
    try:
        with open(blacklist_path, encoding="utf-8") as f:
            data = json.load(f)
            names = [item["name"] for item in data.get("blacklist", [])]
            patterns = data.get("patterns", [])
            return names, patterns
    except FileNotFoundError:
        logger.warning(f"Blacklist not found: {blacklist_path}")
        return [], []
    except Exception as e:
        logger.error(f"Error loading blacklist: {e}")
        return [], []


def is_blacklisted(person_name: str, blacklist_names: List[str], blacklist_patterns: List[str]) -> Tuple[bool, str]:
    """
    ブラックリストに該当するかチェック

    Args:
        person_name: 人物名
        blacklist_names: ブラックリスト名前リスト
        blacklist_patterns: ブラックリスト正規表現パターン

    Returns:
        (is_blacklisted, reason)
    """
    # 名前の完全一致
    if person_name in blacklist_names:
        return True, f"blacklist_match: {person_name}"

    # パターンマッチ
    for pattern in blacklist_patterns:
        if re.search(pattern, person_name):
            return True, f"blacklist_pattern: {pattern}"

    return False, ""


def judge_evidence_quality(source_url: str, raw_text: str, context: str) -> str:
    """
    根拠品質を判定（A/B/C）

    Args:
        source_url: ソースURL
        raw_text: 抽出テキスト
        context: 文脈情報

    Returns:
        evidence_quality: 'A', 'B', 'C'
    """
    # A品質: URLドメインチェック
    for domain_pattern in A_QUALITY_DOMAINS:
        if re.search(domain_pattern, source_url, re.IGNORECASE):
            logger.debug(f"A quality (domain): {source_url}")
            return "A"

    # A品質: キーワードチェック（日本語は大文字小文字変換なし）
    combined_text = f"{raw_text} {context}"
    for keyword in A_QUALITY_KEYWORDS:
        if keyword in combined_text:
            logger.debug(f"A quality (keyword): {keyword}")
            return "A"

    # B品質: Wikipedia + 参照文献があれば（簡易判定）
    if "wikipedia.org" in source_url.lower() and ("出典" in raw_text or "参照" in raw_text):
        logger.debug("B quality: Wikipedia with references")
        return "B"

    # C品質: それ以外（単一ソース、出典不明）
    logger.debug(f"C quality: {source_url}")
    return "C"


def verify_sources(input_csv: Path, output_verified: Path, output_rejected: Path, dry_run: bool = True) -> Dict:
    """
    根拠品質検証メイン処理

    Args:
        input_csv: 入力CSV (episode_sources.csv)
        output_verified: 検証済みCSV (verified_sources.csv)
        output_rejected: 却下CSV (rejected_sources.csv)
        dry_run: ドライラン（変更なし）

    Returns:
        統計情報の辞書
    """
    project_root = get_project_root()

    # 入力ファイル読み込み
    logger.info(f"Reading input: {input_csv}")
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    logger.info(f"Total sources: {len(df)}")

    # 必須カラムチェック
    required_cols = ["person_name", "source_url", "raw_text", "person_type", "source_type"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # 既存verified_sources.csvを読み込み（重複チェック用）
    existing_verified_df = None
    if output_verified.exists():
        logger.info(f"Loading existing verified sources: {output_verified}")
        existing_verified_df = pd.read_csv(output_verified, encoding="utf-8-sig")
        logger.info(f"Existing verified sources: {len(existing_verified_df)}")

    # ブラックリスト読み込み
    blacklist_path = project_root / "config" / "blacklist_names.json"
    blacklist_names, blacklist_patterns = load_blacklist(blacklist_path)
    logger.info(f"Blacklist loaded: {len(blacklist_names)} names, {len(blacklist_patterns)} patterns")

    # センシティブフィルタ初期化
    sensitive_filter = SensitiveFilter()

    # 統計情報
    stats = {
        "total_sources": len(df),
        "duplicates": 0,
        "blacklisted": 0,
        "sensitive": 0,
        "quality_A": 0,
        "quality_B": 0,
        "quality_C": 0,
        "verified": 0,
        "rejected": 0,
    }

    verified_rows = []
    rejected_rows = []

    # 処理ループ
    for idx, row in df.iterrows():
        person_name = str(row["person_name"])
        source_url = str(row["source_url"])
        raw_text = str(row.get("raw_text", ""))
        context = str(row.get("context", ""))
        person_type = str(row.get("person_type", "REAL"))
        source_type = str(row.get("source_type", "manual"))

        # source_id生成（存在しない場合）
        if pd.isna(row.get("source_id")) or row.get("source_id") == "":
            source_id = generate_source_id(person_name, source_url)
        else:
            source_id = str(row["source_id"])

        rejection_reason = None

        # 1. 重複除外
        if is_duplicate_source(source_id, existing_verified_df):
            logger.info(f"Duplicate source: {source_id} ({person_name})")
            stats["duplicates"] += 1
            rejection_reason = "duplicate_source_id"

        # 2. ブラックリスト除外
        if rejection_reason is None:
            is_bl, bl_reason = is_blacklisted(person_name, blacklist_names, blacklist_patterns)
            if is_bl:
                logger.warning(f"Blacklisted: {person_name} - {bl_reason}")
                stats["blacklisted"] += 1
                rejection_reason = bl_reason

        # 3. センシティブ除外
        if rejection_reason is None:
            candidate = PersonCandidate(
                person_name=person_name,
                category=row.get("category"),
                description=row.get("description"),
                person_type=person_type,
            )
            is_sens, sens_reason = sensitive_filter.is_sensitive(candidate)
            if is_sens:
                logger.warning(f"Sensitive: {person_name} - {sens_reason}")
                stats["sensitive"] += 1
                rejection_reason = sens_reason

        # 4. 品質判定
        evidence_quality = judge_evidence_quality(source_url, raw_text, context)
        stats[f"quality_{evidence_quality}"] += 1

        # 検証日時
        verified_at = datetime.now().isoformat()

        # 結果レコード作成
        result_row = row.to_dict()
        result_row["source_id"] = source_id
        result_row["evidence_quality"] = evidence_quality
        result_row["verified_at"] = verified_at

        # 5. verified vs rejected 振り分け
        if rejection_reason:
            # 却下
            result_row["verification_status"] = "rejected"
            result_row["rejection_reason"] = rejection_reason
            rejected_rows.append(result_row)
            stats["rejected"] += 1
        elif evidence_quality in ("A", "B"):
            # 検証済み（A/B品質のみ）
            result_row["verification_status"] = "verified"
            verified_rows.append(result_row)
            stats["verified"] += 1
        else:
            # C品質は却下
            result_row["verification_status"] = "rejected"
            result_row["rejection_reason"] = "quality_C_unverified"
            rejected_rows.append(result_row)
            stats["rejected"] += 1

    # DataFrame作成
    verified_df = pd.DataFrame(verified_rows)
    rejected_df = pd.DataFrame(rejected_rows)

    logger.info("=" * 60)
    logger.info("Verification Summary:")
    logger.info(f"  Total sources: {stats['total_sources']}")
    logger.info(f"  Duplicates: {stats['duplicates']}")
    logger.info(f"  Blacklisted: {stats['blacklisted']}")
    logger.info(f"  Sensitive: {stats['sensitive']}")
    logger.info(f"  Quality A: {stats['quality_A']}")
    logger.info(f"  Quality B: {stats['quality_B']}")
    logger.info(f"  Quality C: {stats['quality_C']}")
    logger.info(f"  Verified (A/B): {stats['verified']}")
    logger.info(f"  Rejected: {stats['rejected']}")
    logger.info("=" * 60)

    # ファイル書き込み
    if not dry_run:
        # 既存verified_sources.csvとマージ
        if existing_verified_df is not None and not existing_verified_df.empty:
            verified_df = pd.concat([existing_verified_df, verified_df], ignore_index=True)
            logger.info(f"Merged with existing verified sources: total {len(verified_df)}")

        output_verified.parent.mkdir(parents=True, exist_ok=True)
        output_rejected.parent.mkdir(parents=True, exist_ok=True)

        verified_df.to_csv(output_verified, index=False, encoding="utf-8-sig")
        logger.info(f"Verified sources written: {output_verified}")

        rejected_df.to_csv(output_rejected, index=False, encoding="utf-8-sig")
        logger.info(f"Rejected sources written: {output_rejected}")

        # 統計レポート出力
        report_dir = project_root / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"source_verification_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(input_csv),
            "output_verified": str(output_verified),
            "output_rejected": str(output_rejected),
            "statistics": stats,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Report written: {report_path}")
    else:
        logger.warning("DRY-RUN MODE: No files written. Use --execute to apply changes.")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Stage 2: verify-sources - 根拠品質検証",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（デフォルト）
  python scripts/pipeline_verify_sources.py \\
      --input generated/episode_sources.csv \\
      --output-verified generated/verified_sources.csv \\
      --output-rejected generated/rejected_sources.csv \\
      --dry-run

  # 本番実行
  python scripts/pipeline_verify_sources.py \\
      --input generated/episode_sources.csv \\
      --output-verified generated/verified_sources.csv \\
      --output-rejected generated/rejected_sources.csv \\
      --execute
        """,
    )

    project_root = get_project_root()

    parser.add_argument(
        "--input",
        type=Path,
        default=project_root / "generated" / "episode_sources.csv",
        help="入力CSV (episode_sources.csv)",
    )
    parser.add_argument(
        "--output-verified",
        type=Path,
        default=project_root / "generated" / "verified_sources.csv",
        help="検証済みCSV (verified_sources.csv)",
    )
    parser.add_argument(
        "--output-rejected",
        type=Path,
        default=project_root / "generated" / "rejected_sources.csv",
        help="却下CSV (rejected_sources.csv)",
    )

    # 実行モード（dry-runがデフォルト）
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run", dest="dry_run", action="store_true", default=True, help="ドライラン（変更なし、デフォルト）"
    )
    mode_group.add_argument("--execute", dest="dry_run", action="store_false", help="本番実行（ファイル書き込み）")

    args = parser.parse_args()

    # 入力ファイル存在チェック
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    # 実行モード表示
    mode = "DRY-RUN" if args.dry_run else "EXECUTE"
    logger.info("=" * 60)
    logger.info(f"Pipeline Stage 2: verify-sources ({mode})")
    logger.info("=" * 60)
    logger.info(f"Input: {args.input}")
    logger.info(f"Output verified: {args.output_verified}")
    logger.info(f"Output rejected: {args.output_rejected}")
    logger.info("=" * 60)

    try:
        stats = verify_sources(
            input_csv=args.input,
            output_verified=args.output_verified,
            output_rejected=args.output_rejected,
            dry_run=args.dry_run,
        )

        logger.info("Verification completed successfully.")
        return 0

    except Exception as e:
        logger.error(f"Error during verification: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
