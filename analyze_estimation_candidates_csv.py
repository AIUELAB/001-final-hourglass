#!/usr/bin/env python3
"""
estimation_candidates_20250917_101830.csv 分析ツール
CSV Analysis Tool for Episode Candidate Selection

目的: CSVデータソースの有用性を評価
- A級/B級有名人の数
- fame_scoreの分布
- 日本人有名人の数
- category_based_candidate_selectorとの比較

Created: 2025-10-02
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


def analyze_csv(csv_path: str) -> Dict:
    """CSV分析を実行"""

    logger.info(f"📊 CSV分析開始: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    logger.info(f"総レコード数: {len(df)}")
    logger.info(f"カラム数: {len(df.columns)}")

    # ========================================
    # 1. score_category分析
    # ========================================
    logger.info("\n" + "="*60)
    logger.info("📊 score_category分析")
    logger.info("="*60)

    if 'score_category' in df.columns:
        category_counts = df['score_category'].value_counts()
        for cat, count in category_counts.items():
            logger.info(f"  {cat}: {count}名")

        # A級/B級の抽出
        high_fame = df[df['score_category'].isin(['A級(国民的有名人)', 'B級(分野内での有名人)'])]
        logger.info(f"\n✅ A級/B級合計: {len(high_fame)}名")
    else:
        logger.warning("score_categoryカラムが見つかりません")
        high_fame = pd.DataFrame()

    # ========================================
    # 2. fame_score分析
    # ========================================
    logger.info("\n" + "="*60)
    logger.info("📈 fame_score分析")
    logger.info("="*60)

    if 'fame_score' in df.columns:
        logger.info(f"fame_score統計:")
        logger.info(f"  最大値: {df['fame_score'].max():.0f}")
        logger.info(f"  平均値: {df['fame_score'].mean():.0f}")
        logger.info(f"  中央値: {df['fame_score'].median():.0f}")
        logger.info(f"  最小値: {df['fame_score'].min():.0f}")

        # Top 50
        top_50 = df.nlargest(50, 'fame_score')
        logger.info(f"\n🏆 fame_score Top 10:")
        for i, row in top_50.head(10).iterrows():
            name_ja = row.get('person_name_ja', row.get('person_name', 'N/A'))
            fame = row['fame_score']
            category = row.get('score_category', 'N/A')
            logger.info(f"  {name_ja} ({fame:.0f}点, {category})")
    else:
        logger.warning("fame_scoreカラムが見つかりません")
        top_50 = pd.DataFrame()

    # ========================================
    # 3. 日本人有名人の抽出
    # ========================================
    logger.info("\n" + "="*60)
    logger.info("🇯🇵 日本人有名人の分析")
    logger.info("="*60)

    # 日本語名がある = 日本人と推測
    if 'person_name_ja' in df.columns:
        japanese = df[df['person_name_ja'].notna() & (df['person_name_ja'] != '')]
        logger.info(f"日本語名あり: {len(japanese)}名")

        # 日本人でfame_scoreが高い人
        if 'fame_score' in df.columns:
            japanese_top = japanese.nlargest(30, 'fame_score')
            logger.info(f"\n🏆 日本人 fame_score Top 30:")
            for i, row in japanese_top.iterrows():
                name_ja = row['person_name_ja']
                fame = row['fame_score']
                category = row.get('score_category', 'N/A')
                cat = row.get('category', 'N/A')
                logger.info(f"  {name_ja} ({fame:.0f}点, {category}, {cat})")
    else:
        japanese = pd.DataFrame()

    # ========================================
    # 4. category_based_candidate_selectorとの比較
    # ========================================
    logger.info("\n" + "="*60)
    logger.info("🔍 現在の26人リストとの比較")
    logger.info("="*60)

    # 現在のハードコードリスト
    hardcoded_names = [
        "イチロー", "大谷翔平", "羽生結弦", "本田圭佑", "錦織圭", "久保建英",
        "八村塁", "渡辺雄太", "北島康介", "高橋尚子",
        "松下幸之助", "本田宗一郎", "稲盛和夫", "孫正義", "堀江貴文", "前澤友作",
        "新垣結衣", "綾瀬はるか", "北野武", "宮崎駿", "松本人志", "ダウンタウン",
        "村上春樹", "手塚治虫", "黒澤明", "坂本龍一",
        "安倍晋三", "小泉純一郎", "菅義偉"
    ]

    if 'person_name_ja' in df.columns:
        found_in_csv = []
        not_found = []

        for name in hardcoded_names:
            matches = df[df['person_name_ja'].str.contains(name, na=False)]
            if len(matches) > 0:
                found_in_csv.append(name)
            else:
                not_found.append(name)

        logger.info(f"✅ CSV内に存在: {len(found_in_csv)}/26名")
        logger.info(f"❌ CSV内に不在: {len(not_found)}/26名")

        if not_found:
            logger.info(f"\n不在リスト: {', '.join(not_found)}")

    # ========================================
    # 5. CSV活用の推奨事項
    # ========================================
    logger.info("\n" + "="*60)
    logger.info("💡 CSV活用の推奨事項")
    logger.info("="*60)

    recommendations = []

    if len(high_fame) > 26:
        recommendations.append(f"✅ A級/B級が{len(high_fame)}名存在 → ハードコードリストより豊富")
    else:
        recommendations.append(f"⚠️ A級/B級が{len(high_fame)}名のみ → ハードコードリストの方が充実")

    if 'fame_score' in df.columns and df['fame_score'].max() > 0:
        recommendations.append("✅ fame_scoreが利用可能 → 定量的な選定が可能")
    else:
        recommendations.append("❌ fame_scoreが利用不可 → 定量的選定は困難")

    if len(japanese) > 100:
        recommendations.append(f"✅ 日本人データが{len(japanese)}名 → 十分なデータ量")
    else:
        recommendations.append(f"⚠️ 日本人データが{len(japanese)}名 → データ量が限定的")

    for rec in recommendations:
        logger.info(f"  {rec}")

    # 結論
    logger.info("\n" + "="*60)
    logger.info("📋 結論")
    logger.info("="*60)

    if len(high_fame) > 26 and 'fame_score' in df.columns:
        logger.info("✅ このCSVは有用です！")
        logger.info("   推奨: CSVベースの候補選定システムを実装")
        logger.info("   理由: より多くの有名人データと定量的スコアが利用可能")
    elif len(high_fame) > 10:
        logger.info("⚠️ このCSVは補助的に有用です")
        logger.info("   推奨: 現在のハードコードリストを補完する目的で使用")
    else:
        logger.info("❌ このCSVは現状では利用価値が低いです")
        logger.info("   推奨: 現在のcategory_based_candidate_selectorを継続使用")

    # 結果をまとめて返す
    return {
        'total_records': len(df),
        'high_fame_count': len(high_fame),
        'japanese_count': len(japanese),
        'top_50_count': len(top_50),
        'hardcoded_found': len(found_in_csv) if 'person_name_ja' in df.columns else 0,
        'recommendations': recommendations
    }


def main():
    """メイン処理"""
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/estimation_candidates_20250917_101830.csv"

    if not Path(csv_path).exists():
        logger.error(f"❌ CSVファイルが見つかりません: {csv_path}")
        return

    results = analyze_csv(csv_path)

    # JSON形式でも出力
    output_json = "csv_analysis_results.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"\n💾 分析結果を保存: {output_json}")


if __name__ == "__main__":
    main()
