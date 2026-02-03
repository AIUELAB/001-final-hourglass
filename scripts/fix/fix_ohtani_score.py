#!/usr/bin/env python3
"""
大谷翔平のfame_score_v3を修正するスクリプト

背景:
- 大谷翔平のfame_score_v3が683.44で全8件固定
- イチロー（638.98）よりも世界的知名度が高いはずだが、スコアが低い
- 推定値として780を設定（2023年MVP満票・50-50達成等の偉業を考慮）

修正内容:
1. fame_score_v3を適切な推定値に修正

注意:
- super_total_scoreはfame_score_v3に直接依存しません
- super_total_scoreは celebrity_score_v2, episode_fame_v6 等に依存します
- Top100入りには episode_fame_v6 の向上が必要です

使用方法:
    python scripts/fix/fix_ohtani_score.py --dry-run  # 変更前後を表示
    python scripts/fix/fix_ohtani_score.py --execute  # 実行
"""

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# パス設定
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"

# 大谷翔平のperson_id
OHTANI_PERSON_ID = "P5C4FB25"

# Wikidataシグナル（scorer_japan.pyのテストデータより）
OHTANI_WIKIDATA_SIGNALS = {
    "wikipedia_pv_ja": 261588,
    "multi_lang_pv": 5452838,
    "sitelinks": 37,
}

# 正規化パラメータ（scorer.pyより）
MAX_PV = 10_000_000
MAX_SITELINKS = 200
MAX_INLINKS = 100_000

# 重み（Phase 1: Google検索なし）
WEIGHTS = {
    "multi_lang_pv": 0.50,
    "sitelinks": 0.30,
    "inlinks": 0.20,
}

# 推定fame_score_v3
# 背景:
#   - イチロー: 638.98（メジャーリーグ殿堂入り）
#   - 大谷翔平は2023年にMVP満票・50-50達成・WBC優勝MVP等の偉業を達成
#   - 現在MLB最高の日本人選手として世界的知名度
#   - 推定値として780を設定（イチローを大幅に上回る評価）
ESTIMATED_FAME_SCORE_V3 = 780.0


def normalize_pv(pv: int) -> float:
    """PVを0-1に正規化（対数スケール）"""
    if pv <= 0:
        return 0.0
    return math.log1p(pv) / math.log1p(MAX_PV)


def normalize_sitelinks(count: int) -> float:
    """言語版数を0-1に正規化（線形スケール）"""
    if count <= 0:
        return 0.0
    return min(count / MAX_SITELINKS, 1.0)


def normalize_inlinks(count: int) -> float:
    """被リンク数を0-1に正規化（対数スケール）"""
    if count <= 0:
        return 0.0
    return math.log1p(count) / math.log1p(MAX_INLINKS)


def calculate_fame_score_v3(
    multi_lang_pv: int,
    sitelinks: int,
    inlinks: int = 5000,  # 大谷翔平の推定inlinks
) -> float:
    """
    fame_score_v3を計算

    Args:
        multi_lang_pv: 多言語Wikipedia合計PV
        sitelinks: 言語版数
        inlinks: 被リンク数（推定値使用）

    Returns:
        fame_score_v3（0-1000スケール）
    """
    norm_pv = normalize_pv(multi_lang_pv)
    norm_sitelinks = normalize_sitelinks(sitelinks)
    norm_inlinks = normalize_inlinks(inlinks)

    raw = WEIGHTS["multi_lang_pv"] * norm_pv + WEIGHTS["sitelinks"] * norm_sitelinks + WEIGHTS["inlinks"] * norm_inlinks

    # 0-1000スケーリング
    score = min(max(raw * 1000, 0), 1000)
    return round(score, 2)


def main():
    parser = argparse.ArgumentParser(description="大谷翔平のfame_score_v3を修正")
    parser.add_argument("--dry-run", action="store_true", help="変更前後を表示（実行しない）")
    parser.add_argument("--execute", action="store_true", help="実際に修正を実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        print("\n--dry-run または --execute を指定してください")
        sys.exit(1)

    print("=" * 80)
    print("📊 大谷翔平スコア修正スクリプト")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: 大谷翔平のエピソードを抽出
    print("Step 2: 大谷翔平のエピソードを抽出中...")
    ohtani_mask = df["person_id"] == OHTANI_PERSON_ID
    ohtani_df = df[ohtani_mask].copy()
    print(f"  ✅ 対象エピソード: {len(ohtani_df)}件")
    print()

    if len(ohtani_df) == 0:
        print("❌ 大谷翔平のエピソードが見つかりません")
        sys.exit(1)

    # Step 3: fame_score_v3を設定
    print("Step 3: fame_score_v3を設定中...")

    # 計算による値（参考）
    calculated_fame_score = calculate_fame_score_v3(
        multi_lang_pv=OHTANI_WIKIDATA_SIGNALS["multi_lang_pv"],
        sitelinks=OHTANI_WIKIDATA_SIGNALS["sitelinks"],
        inlinks=5000,
    )

    # 推定値を採用（ユーザー要件: 750〜800程度が妥当）
    new_fame_score = ESTIMATED_FAME_SCORE_V3

    print("  📊 Wikidataシグナル:")
    print(f"      multi_lang_pv: {OHTANI_WIKIDATA_SIGNALS['multi_lang_pv']:,}")
    print(f"      sitelinks: {OHTANI_WIKIDATA_SIGNALS['sitelinks']}")
    print(f"  📊 計算による値（参考）: {calculated_fame_score:.2f}")
    print(f"  📊 採用する推定値: {new_fame_score:.2f}")
    print("      (理由: イチロー638.98を上回る世界的知名度、MVP満票・50-50達成等)")
    print()

    # Step 4: 変更前後を表示
    print("Step 4: 変更前後の比較...")

    changes = []
    for idx, row in ohtani_df.iterrows():
        episode_id = row["episode_id"]
        age = row["age"]
        old_fame = row.get("fame_score_v3", 0)
        current_super = row.get("super_total_score", 0)

        changes.append(
            {
                "idx": idx,
                "episode_id": episode_id,
                "age": age,
                "old_fame": old_fame,
                "new_fame": new_fame_score,
                "current_super": current_super,
            }
        )

        print(f"  📝 {episode_id} (年齢: {age}歳)")
        print(f"      fame_score_v3: {old_fame:.2f} → {new_fame_score:.2f} ({new_fame_score - float(old_fame):+.2f})")
        print(f"      super_total_score: {float(current_super):,.0f}（変更なし）")
        print()

    # Step 5: 参考情報
    print("Step 5: 参考情報...")
    top100_threshold = df["super_total_score"].astype(float).nlargest(100).iloc[-1]
    max_super = max(float(c["current_super"]) for c in changes)
    print(f"  📊 現在のTop100ボーダー: {top100_threshold:,.0f}")
    print(f"  📊 大谷翔平の最高スコア: {max_super:,.0f}")
    print()
    print("  ℹ️  注意: super_total_scoreは以下に依存します:")
    print("      - celebrity_score_v2（人物有名度）")
    print("      - episode_fame_v6（エピソード有名度）")
    print("      - 7軸品質スコア")
    print("      - episode_importance_score（歴史的インパクト）")
    print("      fame_score_v3は直接影響しません。")
    print()

    if args.dry_run:
        print("=" * 80)
        print("🔍 ドライラン完了（変更は適用されていません）")
        print("  実行するには --execute オプションを使用してください")
        print("=" * 80)
        sys.exit(0)

    # Step 6: バックアップ作成
    print("Step 6: バックアップ作成中...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = (
        BACKUP_DIR / f"MASTER_EPISODES_CURRENT_backup_before_ohtani_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"  ✅ バックアップ作成: {backup_path}")
    print()

    # Step 7: 修正を適用（fame_score_v3のみ）
    print("Step 7: 修正を適用中...")
    for change in changes:
        idx = change["idx"]
        df.at[idx, "fame_score_v3"] = change["new_fame"]
        # super_total_scoreは変更しない（依存関係がないため）

    print(f"  ✅ {len(changes)}件のエピソードのfame_score_v3を更新")
    print()

    # Step 8: CSVファイル保存
    print("Step 8: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 9: 検証
    print("Step 9: 修正結果の検証...")
    df_verify = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    verify_df = df_verify[df_verify["person_id"] == OHTANI_PERSON_ID]

    all_ok = True
    for _, row in verify_df.iterrows():
        episode_id = row["episode_id"]
        fame = row["fame_score_v3"]
        super_score = row["super_total_score"]

        is_correct = abs(fame - new_fame_score) < 0.01
        status = "✅" if is_correct else "❌"
        print(f"  {status} {episode_id}: fame={fame:.2f}, super={super_score:,.0f}")

        if not is_correct:
            all_ok = False

    print()

    # サマリー
    print("=" * 80)
    if all_ok:
        print("✅ 大谷翔平のスコア修正が完了しました！")
    else:
        print("⚠️  一部のエピソードで修正が完了しませんでした")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 修正件数: {len(changes)}件")
    print(f"  - fame_score_v3: 683.44 → {new_fame_score:.2f}")
    print(f"  - バックアップ: {backup_path}")
    print()


if __name__ == "__main__":
    main()
