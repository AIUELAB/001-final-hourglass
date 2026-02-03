#!/usr/bin/env python3
"""
Recalculate Fame Score v3

fame_score_v3が固定値（500.00）の実在人物について、
Wikidataから情報を再取得してスコアを再計算するスクリプト。

対象:
- fame_score_v3 = 500.00 の実在人物（person_type = REAL）
- 400.00（架空キャラ）は対象外（Wikidataがないため）

修復方針:
1. 対象レコードのmulti_lang_pv, sitelinks_countを確認
2. 値が0または欠損の場合は、person_nameからWikidata検索して取得を試みる
3. 取得できた場合は、scorer.pyの計算式でfame_score_v3を再計算
4. 取得できない場合は500.00のまま（ログに記録）

Usage:
    # 対象確認（ドライラン）
    python scripts/fix/recalculate_fame_score_v3.py --dry-run

    # 実行
    python scripts/fix/recalculate_fame_score_v3.py --execute

    # バッチサイズ指定
    python scripts/fix/recalculate_fame_score_v3.py --execute --batch-size 20
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.config import MASTER_CSV, LOGS_DIR
from scripts.sage.persistence.backup import create_pre_operation_backup
from scripts.fame_score_v3.scorer import FameSignals, calculate_fame_score
from scripts.fame_score_v3.wikidata import get_wikidata_info
from scripts.fame_score_v3.wikipedia_pv import get_multi_lang_pageviews

# ログ設定
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / f"recalculate_fame_score_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 定数
FIXED_SCORE_500 = 500.00
FIXED_SCORE_400 = 400.00  # 架空キャラ用（対象外）
BATCH_DELAY_SECONDS = 1.0  # バッチ間の待機時間
DEFAULT_BATCH_SIZE = 10  # デフォルトのバッチサイズ


def load_master_csv(csv_path: Path = MASTER_CSV) -> pd.DataFrame:
    """マスターCSVを読み込む"""
    logger.info(f"Loading: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    logger.info(f"Total episodes: {len(df)}")
    return df


def find_target_persons(df: pd.DataFrame) -> pd.DataFrame:
    """
    再計算対象の人物を抽出

    条件:
    - person_type = REAL
    - fame_score_v3 = 500.00（固定値）
    """
    # 人物単位でユニーク化
    persons = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
                "person_type": "first",
                "fame_score_v3": "first",
                "multi_lang_pv": "first",
                "sitelinks_count": "first",
            }
        )
        .reset_index()
    )

    # REAL人物でfame_score_v3 = 500.00のみ
    targets = persons[(persons["person_type"] == "REAL") & (persons["fame_score_v3"] == FIXED_SCORE_500)].copy()

    return targets


def analyze_targets(targets: pd.DataFrame) -> dict:
    """対象人物の分析"""
    stats = {
        "total_count": len(targets),
        "missing_pv": 0,  # multi_lang_pvが0または欠損
        "missing_sitelinks": 0,  # sitelinks_countが0または欠損
        "both_missing": 0,  # 両方欠損
        "has_data": 0,  # データあり（500固定はスコア計算ミスの可能性）
    }

    for _, row in targets.iterrows():
        pv = row.get("multi_lang_pv")
        sitelinks = row.get("sitelinks_count")

        pv_missing = bool(pd.isna(pv)) or pv == 0
        sitelinks_missing = bool(pd.isna(sitelinks)) or sitelinks == 0

        if pv_missing:
            stats["missing_pv"] += 1
        if sitelinks_missing:
            stats["missing_sitelinks"] += 1
        if pv_missing and sitelinks_missing:
            stats["both_missing"] += 1
        if not pv_missing and not sitelinks_missing:
            stats["has_data"] += 1

    return stats


def fetch_wikidata_signals(person_name: str) -> dict:
    """
    Wikidataから人物のシグナルを取得

    Returns:
        {
            "wikidata_id": str or None,
            "multi_lang_pv": int,
            "sitelinks": int,
            "inlinks": int,
            "success": bool,
        }
    """
    result = {
        "wikidata_id": None,
        "multi_lang_pv": 0,
        "sitelinks": 0,
        "inlinks": 0,
        "success": False,
    }

    try:
        # Wikidata情報を取得
        wikidata_info = get_wikidata_info(person_name, include_inlinks=False)
        wikidata_id = wikidata_info.get("wikidata_id")

        if not wikidata_id:
            logger.debug(f"Wikidata not found: {person_name}")
            return result

        result["wikidata_id"] = wikidata_id
        result["sitelinks"] = wikidata_info.get("sitelinks", 0)

        # Wikipedia多言語PVを取得
        pv_info = get_multi_lang_pageviews(person_name, wikidata_id=wikidata_id)
        result["multi_lang_pv"] = pv_info.get("total_pv", 0)

        # 成功判定（PVまたはsitelinksが取得できた）
        if result["multi_lang_pv"] > 0 or result["sitelinks"] > 0:
            result["success"] = True

    except Exception as e:
        logger.warning(f"Wikidata fetch error [{person_name}]: {e}")

    return result


def calculate_new_fame_score(person_id: str, multi_lang_pv: int, sitelinks: int, inlinks: int = 0) -> float:
    """fame_score_v3を計算"""
    signals = FameSignals(
        multi_lang_pv=multi_lang_pv,
        sitelinks=sitelinks,
        inlinks=inlinks,
    )
    fame_score = calculate_fame_score(signals, person_id, person_type="REAL")
    return fame_score.score


def run_dry_run(_df: pd.DataFrame, targets: pd.DataFrame) -> None:
    """ドライラン：対象確認のみ"""
    print("\n" + "=" * 70)
    print("fame_score_v3 再計算 - ドライラン（対象確認）")
    print("=" * 70)

    # 統計
    stats = analyze_targets(targets)

    print(f"\n対象人物数: {stats['total_count']} 人")
    print(f"  - multi_lang_pv欠損: {stats['missing_pv']} 人")
    print(f"  - sitelinks_count欠損: {stats['missing_sitelinks']} 人")
    print(f"  - 両方欠損: {stats['both_missing']} 人")
    print(f"  - データあり（スコア計算要確認）: {stats['has_data']} 人")

    # 上位10人のサンプル表示
    print("\n--- 対象人物サンプル（上位10人）---")
    sample = targets.head(10)
    for _, row in sample.iterrows():
        pv = row.get("multi_lang_pv", 0)
        pv_val = float(pv) if pv is not None and pd.notna(pv) else 0
        pv_str = f"{int(pv_val):,}" if pv_val > 0 else "N/A"
        sitelinks = row.get("sitelinks_count", 0)
        sitelinks_val = float(sitelinks) if sitelinks is not None and pd.notna(sitelinks) else 0
        sitelinks_str = f"{int(sitelinks_val)}" if sitelinks_val > 0 else "N/A"
        print(f"  {row['person_id']}: {row['person_name']} (PV: {pv_str}, sitelinks: {sitelinks_str})")

    # 推定原因
    print("\n--- 推定原因 ---")
    if stats["both_missing"] > stats["total_count"] * 0.5:
        print("  > 多くの人物でWikidata取得が失敗している可能性")
        print("  > 原因: API制限、人物名の表記揺れ、Wikidata未登録")
    elif stats["has_data"] > stats["total_count"] * 0.3:
        print("  > 一部の人物はデータがあるがスコアが500固定")
        print("  > 原因: 初期インポート時のスコア計算バグの可能性")
    else:
        print("  > Wikidata情報が未取得の状態で500がデフォルト設定された可能性")

    print("\n[DRY-RUN] --execute オプションで実行してください")
    print("=" * 70)


def run_execute(
    df: pd.DataFrame,
    targets: pd.DataFrame,
    csv_path: Path = MASTER_CSV,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    """実行：Wikidataから再取得してスコア再計算"""
    print("\n" + "=" * 70)
    print("fame_score_v3 再計算 - 実行モード")
    print("=" * 70)

    total_targets = len(targets)
    print(f"\n対象人物数: {total_targets} 人")
    print(f"バッチサイズ: {batch_size} 人")

    # バックアップ作成
    logger.info("Creating backup...")
    backup_info = create_pre_operation_backup("recalculate_fame_score_v3")
    if backup_info:
        logger.info(f"Backup created: {backup_info.path}")
    else:
        logger.warning("Backup creation failed, continuing anyway...")

    # 処理統計
    stats = {
        "processed": 0,
        "updated": 0,
        "skipped_no_wikidata": 0,
        "skipped_no_data": 0,
        "errors": 0,
    }

    # バッチ処理
    total_batches = (total_targets + batch_size - 1) // batch_size
    target_list = list(targets.itertuples(index=False))

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_targets)
        batch = target_list[start_idx:end_idx]

        print(f"\nバッチ {batch_idx + 1}/{total_batches} ({start_idx + 1}-{end_idx}/{total_targets})")

        for person in batch:
            person_id = getattr(person, "person_id", "")
            person_name = getattr(person, "person_name", "")
            stats["processed"] += 1

            try:
                # Wikidataから取得
                signals = fetch_wikidata_signals(person_name)

                if not signals["success"]:
                    stats["skipped_no_wikidata"] += 1
                    logger.info(f"  [SKIP] {person_name}: Wikidata not found")
                    continue

                # 新スコア計算
                new_score = calculate_new_fame_score(
                    person_id=person_id,
                    multi_lang_pv=signals["multi_lang_pv"],
                    sitelinks=signals["sitelinks"],
                    inlinks=signals["inlinks"],
                )

                # スコアが変わらない場合（データはあるが計算結果が500）
                if abs(new_score - FIXED_SCORE_500) < 0.01:
                    stats["skipped_no_data"] += 1
                    logger.info(
                        f"  [SKIP] {person_name}: Score unchanged "
                        f"(PV={signals['multi_lang_pv']}, sitelinks={signals['sitelinks']})"
                    )
                    continue

                # CSVを更新
                mask = df["person_id"] == person_id
                df.loc[mask, "fame_score_v3"] = new_score
                df.loc[mask, "multi_lang_pv"] = signals["multi_lang_pv"]
                df.loc[mask, "sitelinks_count"] = signals["sitelinks"]

                stats["updated"] += 1
                logger.info(
                    f"  [UPDATE] {person_name}: 500.00 -> {new_score:.2f} "
                    f"(PV={signals['multi_lang_pv']:,}, sitelinks={signals['sitelinks']})"
                )

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"  [ERROR] {person_name}: {e}")

        # バッチ間の待機（レート制限対策）
        if batch_idx < total_batches - 1:
            time.sleep(BATCH_DELAY_SECONDS)

    # CSV保存
    logger.info("\nSaving CSV...")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved: {csv_path}")

    # 結果サマリー
    print("\n" + "=" * 70)
    print("実行結果サマリー")
    print("=" * 70)
    print(f"処理人物数: {stats['processed']} 人")
    print(f"更新成功: {stats['updated']} 人")
    print(f"スキップ（Wikidata未発見）: {stats['skipped_no_wikidata']} 人")
    print(f"スキップ（スコア変化なし）: {stats['skipped_no_data']} 人")
    print(f"エラー: {stats['errors']} 人")
    print(f"\nログファイル: {LOG_FILE}")
    print("=" * 70)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="fame_score_v3固定値（500.00）を再計算")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライランモード（対象確認のみ）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実行モード（CSV更新）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"バッチサイズ（デフォルト: {DEFAULT_BATCH_SIZE}）",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    # CSVパスを決定
    csv_path = Path(args.csv)

    # CSVを読み込み
    df = load_master_csv(csv_path)

    # 対象人物を抽出
    targets = find_target_persons(df)

    if len(targets) == 0:
        print("\n対象人物が見つかりませんでした。")
        print("（fame_score_v3 = 500.00 かつ person_type = REAL の人物がいません）")
        return

    # モード分岐
    if args.dry_run:
        run_dry_run(df, targets)
    elif args.execute:
        run_execute(df, targets, csv_path=csv_path, batch_size=args.batch_size)
    else:
        parser.print_help()
        print("\n--dry-run または --execute を指定してください。")


if __name__ == "__main__":
    main()
