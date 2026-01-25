#!/usr/bin/env python3
"""
Stage 3: curate-episodes - エピソード生成（LLM統合）

verified_sources.csvからA/B品質のソースを読み込み、
EPUP形式（「あなたと同じ{age}歳のとき、...」）のエピソードに変換します。

Input: generated/verified_sources.csv
Output: generated/curated_episodes.csv
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from anthropic import Anthropic

from src.models.curated_episode import CuratedEpisode

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# デフォルトパス
PROJECT_ROOT = Path(__file__).parent.parent
VERIFIED_SOURCES_PATH = PROJECT_ROOT / "generated" / "verified_sources.csv"
CURATED_EPISODES_PATH = PROJECT_ROOT / "generated" / "curated_episodes.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def extract_age_from_context(context: str) -> Optional[int]:
    """
    contextフィールドから年齢を抽出

    Args:
        context: contextフィールドの文字列

    Returns:
        抽出された年齢、見つからない場合はNone

    Examples:
        >>> extract_age_from_context("年齢31歳時の業績")
        31
        >>> extract_age_from_context("年齢40歳時の業績")
        40
        >>> extract_age_from_context("作品設定")
        None
    """
    # NaN対策: floatの場合は空文字列に変換
    if not isinstance(context, str):
        context = ""

    # パターン1: 年齢XX歳時
    match = re.search(r"年齢(\d+)歳", context)
    if match:
        return int(match.group(1))

    # パターン2: XX歳のとき
    match = re.search(r"(\d+)歳のとき", context)
    if match:
        return int(match.group(1))

    # パターン3: XX歳時
    match = re.search(r"(\d+)歳時", context)
    if match:
        return int(match.group(1))

    return None


def convert_to_epup_format(
    person_name: str,
    person_type: str,
    age: int,
    raw_text: str,
    context: str,
    evidence_quality: str,
    api_key: str,
    model: str = "claude-sonnet-4-5-20250929",
) -> str:
    """
    LLMを使用してraw_textをEPUP形式に変換

    Args:
        person_name: 人物名
        person_type: 人物タイプ（REAL/FICTIONAL）
        age: 年齢
        raw_text: 元テキスト
        context: コンテキスト
        evidence_quality: 根拠品質（A/B）
        api_key: Anthropic API key
        model: 使用するモデル

    Returns:
        EPUP形式のエピソード本文

    Raises:
        Exception: API呼び出し失敗時
    """
    client = Anthropic(api_key=api_key)

    # プロンプト作成
    system_prompt = """あなたはエピソードライターです。
与えられた情報を「あなたと同じ{age}歳のとき、{person_name}は...」形式に変換してください。

重要なルール：
1. 必ず「あなたと同じ」で始める
2. 事実を正確に保つ
3. 簡潔に（2-3文で完結）
4. メタ的表現を避ける（「このキャラクターは架空です」等は書かない）
5. 架空キャラクターの場合も作品世界内の視点で書く
6. 敬称は基本的に省略（「さん」「氏」等は不要）
7. 読者に語りかける自然な文体
"""

    if person_type == "FICTIONAL":
        user_prompt = f"""人物名: {person_name}（架空キャラクター）
年齢: {age}歳
情報: {raw_text}
コンテキスト: {context}

この情報を「あなたと同じ{age}歳のとき、{person_name}は...」形式のエピソードに変換してください。
架空キャラクターですが、作品世界内の視点で自然なエピソードとして記述してください。
メタ的な説明（「架空のキャラクターです」等）は絶対に含めないでください。"""
    else:
        user_prompt = f"""人物名: {person_name}（実在人物）
年齢: {age}歳
情報: {raw_text}
コンテキスト: {context}

この情報を「あなたと同じ{age}歳のとき、{person_name}は...」形式のエピソードに変換してください。
事実に基づいた正確な記述を心がけてください。"""

    try:
        # Claude API呼び出し
        response = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=0.3,  # 低温度で事実性を重視
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        episode_text = response.content[0].text.strip()

        # 基本バリデーション
        if not episode_text.startswith("あなたと同じ"):
            logger.warning(f"Episode does not start with 'あなたと同じ': {episode_text[:50]}")
            # 修正を試みる
            if f"{age}歳のとき" in episode_text:
                episode_text = f"あなたと同じ{episode_text}"

        return episode_text

    except Exception as e:
        logger.error(f"LLM conversion failed for {person_name}: {e}")
        raise


def process_verified_sources(
    input_csv: Path,
    output_csv: Path,
    api_key: str,
    dry_run: bool = True,
    max_sources: Optional[int] = None,
) -> Dict[str, any]:
    """
    verified_sources.csvを処理してcurated_episodes.csvを生成

    Args:
        input_csv: 入力CSV（verified_sources.csv）
        output_csv: 出力CSV（curated_episodes.csv）
        api_key: Anthropic API key
        dry_run: True=ドライラン（ファイル書き込みなし）
        max_sources: 処理する最大ソース数（Noneで全件）

    Returns:
        統計情報の辞書
    """
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Processing verified sources...")
    logger.info(f"Input: {input_csv}")
    logger.info(f"Output: {output_csv}")

    # 入力CSV読み込み
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    logger.info(f"Loaded {len(df)} verified sources")

    # max_sources制限
    if max_sources and len(df) > max_sources:
        logger.info(f"Limiting to first {max_sources} sources")
        df = df.head(max_sources)

    # 統計
    stats = {
        "total_sources": len(df),
        "successful": 0,
        "failed": 0,
        "age_extraction_failed": 0,
        "llm_conversion_failed": 0,
    }

    curated_episodes: List[CuratedEpisode] = []

    for idx, row in df.iterrows():
        source_id = row["source_id"]
        person_name = row["person_name"]
        person_id = row["person_id"]
        person_type = row.get("person_type", "REAL")
        raw_text = row["raw_text"]
        context = row.get("context", "")
        evidence_quality = row["evidence_quality"]
        source_url = row["source_url"]
        category = row.get("category", "")

        logger.info(f"Processing [{idx + 1}/{len(df)}]: {person_name} ({source_id})")

        # 年齢抽出
        age = extract_age_from_context(context)
        if age is None:
            logger.warning(f"  ⚠️  Age extraction failed from context: '{context}'")
            stats["age_extraction_failed"] += 1
            stats["failed"] += 1
            continue

        logger.info(f"  → Age extracted: {age}歳")

        # LLM変換
        try:
            episode_text = convert_to_epup_format(
                person_name=person_name,
                person_type=person_type,
                age=age,
                raw_text=raw_text,
                context=context,
                evidence_quality=evidence_quality,
                api_key=api_key,
            )
            logger.info(f"  ✅ Episode generated: {episode_text[:60]}...")

            # CuratedEpisode作成
            curated = CuratedEpisode(
                person_id=person_id,
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                source_id=source_id,
                source_url=source_url,
                evidence_quality=evidence_quality,
                person_type=person_type,
                category=category if pd.notna(category) else None,
                validation_status="pending",  # Stage 4でバリデーション
            )

            curated_episodes.append(curated)
            stats["successful"] += 1

        except Exception as e:
            logger.error(f"  ❌ LLM conversion failed: {e}")
            stats["llm_conversion_failed"] += 1
            stats["failed"] += 1
            continue

    # 出力CSV保存
    if not dry_run and curated_episodes:
        logger.info(f"Saving {len(curated_episodes)} curated episodes to {output_csv}")
        CuratedEpisode.save_to_csv(curated_episodes, output_csv, append=False)
        logger.info("✅ Curated episodes saved successfully")
    elif dry_run:
        logger.info(f"[DRY-RUN] Would save {len(curated_episodes)} episodes to {output_csv}")

    # 統計レポート保存
    if not dry_run:
        report_path = REPORTS_DIR / f"episode_curation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "input_csv": str(input_csv),
                    "output_csv": str(output_csv),
                    "statistics": stats,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Report saved: {report_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 3: Convert verified sources to EPUP format episodes")
    parser.add_argument(
        "--input",
        type=Path,
        default=VERIFIED_SOURCES_PATH,
        help="Input CSV path (verified_sources.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CURATED_EPISODES_PATH,
        help="Output CSV path (curated_episodes.csv)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no file writes)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute mode (write files)",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        help="Maximum number of sources to process",
    )

    args = parser.parse_args()

    # API key取得
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("❌ ANTHROPIC_API_KEY is required")
        logger.error("   Set via --api-key or ANTHROPIC_API_KEY environment variable")
        return 1

    # dry_run判定
    dry_run = not args.execute if not args.dry_run else True

    print("=" * 80)
    print("🔧 Stage 3: curate-episodes - エピソード生成（LLM統合）")
    print("=" * 80)
    print()

    try:
        stats = process_verified_sources(
            input_csv=args.input,
            output_csv=args.output,
            api_key=api_key,
            dry_run=dry_run,
            max_sources=args.max_sources,
        )

        # 統計表示
        print()
        print("📊 統計:")
        print(f"  総ソース数: {stats['total_sources']}")
        print(f"  成功: {stats['successful']}")
        print(f"  失敗: {stats['failed']}")
        if stats["age_extraction_failed"] > 0:
            print(f"    - 年齢抽出失敗: {stats['age_extraction_failed']}")
        if stats["llm_conversion_failed"] > 0:
            print(f"    - LLM変換失敗: {stats['llm_conversion_failed']}")
        print()

        if dry_run:
            print("ℹ️  ドライランモードで実行しました")
            print("   実際にファイルを書き込むには --execute を指定してください")
        else:
            print("✅ 完了")

        print("=" * 80)
        return 0

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
