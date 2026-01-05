#!/usr/bin/env python3
"""
超総合スコア再計算スクリプト（v1.2.0+対応）

変更点:
- 科学史キーワード追加（特殊相対性理論、E=mc²等）
- TURNING_POINT_MANUALブースト追加（+8%）
- v2.0.0: --config引数でJSON設定ファイル指定可能
"""

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from scripts.score.super_total_scorer import SuperTotalConfig, SuperTotalScorer

CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def parse_args():
    parser = argparse.ArgumentParser(description="超総合スコア再計算")
    parser.add_argument(
        "--config",
        type=Path,
        help="設定JSONファイルパス（例: configs/super_total_score/v2.0.0.json）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にCSVを更新せず、結果のみ表示",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("超総合スコア再計算")
    print("=" * 60)

    # 設定読み込み
    if args.config:
        config_path = PROJECT_ROOT / args.config if not args.config.is_absolute() else args.config
        if not config_path.exists():
            print(f"❌ エラー: 設定ファイルが見つかりません: {config_path}")
            sys.exit(1)
        config = SuperTotalConfig.from_json(config_path)
        print(f"\n設定ファイル: {config_path}")
    else:
        config = SuperTotalConfig()  # デフォルト設定
        print("\n設定: デフォルト（v1.2.0）")

    print(f"バージョン: {config.version}")
    print(
        f"重み: celebrity={config.weight_celebrity}, episode_fame={config.weight_episode_fame}, "
        f"quality={config.weight_quality}, historical={config.weight_historical}"
    )
    print(f"偉業ブースト乗数: {config.achievement_boost_multiplier}")

    # 正規化パラメータ保存パス
    norm_params_path = PROJECT_ROOT / f"preserved/data/super_total_norm_params_{config.version}.json"

    # データ読み込み
    print("\n1. データ読み込み中...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    episodes = df.to_dict("records")
    print(f"   読み込み完了: {len(episodes):,}件")

    # スコアラー初期化
    print("\n2. スコアラー初期化中...")
    scorer = SuperTotalScorer(episodes, config=config)
    print("   正規化パラメータ:")
    print(
        f"     celebrity_score_v2: median={scorer.norm_params.celebrity_median:.1f}, iqr={scorer.norm_params.celebrity_iqr:.1f}"
    )
    print(f"     episode_fame_v6: median={scorer.norm_params.fame_median:.1f}, iqr={scorer.norm_params.fame_iqr:.1f}")
    print(
        f"     episode_importance: median={scorer.norm_params.importance_median:.1f}, iqr={scorer.norm_params.importance_iqr:.1f}"
    )

    # 保存
    scorer.save_normalization_params(norm_params_path)
    print(f"   正規化パラメータ保存: {norm_params_path}")

    # 全エピソード再計算
    print("\n3. 全エピソード再計算中...")
    passed_count = 0
    failed_count = 0
    new_scores = []

    for i, ep in enumerate(episodes):
        result = scorer.calculate(ep)
        if result.passed_gate:
            new_scores.append(result.score)
            passed_count += 1
        else:
            new_scores.append(0)
            failed_count += 1

        if (i + 1) % 2000 == 0:
            print(f"   処理中: {i + 1:,}/{len(episodes):,}")

    print(f"   完了: {passed_count:,}件通過, {failed_count:,}件ゲート不通過")

    # スコア更新
    df["super_total_score"] = new_scores

    # Top 20表示（v2.0.0比較用）
    print("\n4. Top 20確認:")
    df_sorted = df.copy()
    df_sorted["super_total_score"] = pd.to_numeric(df_sorted["super_total_score"], errors="coerce")
    top20 = df_sorted.nlargest(20, "super_total_score")
    for i, (_, row) in enumerate(top20.iterrows(), 1):
        name = row.get("person_name", "?")
        age = row.get("age", "?")
        score = row.get("super_total_score", 0)
        print(f"   {i:2}. {name}（{age}歳）: {float(score):,.0f}")

    # 参照対象の人物確認（v2.0.0最適化確認用）
    print("\n5. 参照ランキング対象者の順位:")
    reference_persons = ["大谷翔平", "イチロー", "孫正義", "羽生結弦", "スティーブ・ジョブズ"]
    df_sorted = df_sorted.sort_values("super_total_score", ascending=False).reset_index(drop=True)
    for person in reference_persons:
        person_df = df_sorted[df_sorted["person_name"] == person]
        if not person_df.empty:
            best_idx = person_df.index[0]
            best_row = person_df.iloc[0]
            best_age = best_row.get("age", "?")
            best_score = best_row.get("super_total_score", 0)
            rank = best_idx + 1
            print(f"   {person}（{best_age}歳）: {rank}位 ({float(best_score):,.0f})")
        else:
            print(f"   {person}: 見つかりません")

    if args.dry_run:
        print("\n⚠️ ドライラン: CSVは更新されません")
    else:
        # CSV保存
        print("\n6. CSV保存中...")
        df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
        print(f"   保存完了: {CSV_PATH}")

    print("\n" + "=" * 60)
    print(f"完了 (config: {config.version})")


if __name__ == "__main__":
    main()
