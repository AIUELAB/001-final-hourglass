#!/usr/bin/env python3
"""
エピソード有名度スコア算出スクリプト（v2 - カテゴリ別キーワード対応版）

各エピソードの内容・重要性に基づいて有名度を算出
カテゴリ別のキーワード辞書を使用して分野バイアスを軽減
"""

import sys
from pathlib import Path

# backendモジュールをインポートするためのパス追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from datetime import datetime
from typing import Dict, Tuple

import pandas as pd

# カテゴリ別キーワード辞書をインポート
from app.utils.keyword_dictionaries import calculate_keyword_score, get_all_keywords_for_category, normalize_category
from app.utils.score_calculator import calculate_composite_score

CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    PROJECT_ROOT / f"MASTER_EPISODES_CURRENT_backup_before_fame_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def calculate_episode_fame_score_v2(row: pd.Series) -> Tuple[float, Dict]:
    """
    エピソードの有名度スコアを算出（v2 - カテゴリ別対応）

    Args:
        row: エピソードの行データ

    Returns:
        (スコア, 詳細情報の辞書)

    評価基準：
    - エピソードタイプ（+5〜15点）
    - カテゴリ別キーワードマッチ
    - 数値データの具体性
    - 固有名詞の存在
    """
    score = 50.0  # ベーススコア

    episode_text = str(row.get("episode_text", ""))
    episode_type = str(row.get("episode_type", ""))
    category = str(row.get("category", ""))

    details = {
        "base_score": 50.0,
        "type_bonus": 0,
        "keyword_bonus": 0,
        "specificity_bonus": 0,
        "penalty": 0,
        "final_score": 0,
        "matched_keywords": [],
    }

    # 1. エピソードタイプによる補正
    type_scores = {
        "ACHIEVEMENT": 15,  # 達成・偉業
        "TURNING_POINT": 12,  # 転機
        "INNOVATION": 14,  # 革新
        "FOUNDING": 13,  # 創業・設立
        "CHALLENGE": 8,  # 挑戦
        "FAMILY": 5,  # 家族（個人的）
        "GROWTH": 7,  # 成長
        "FAILURE": 6,  # 失敗
        "COMEBACK": 10,  # 復活
    }
    type_bonus = type_scores.get(episode_type, 5)
    score += type_bonus
    details["type_bonus"] = type_bonus

    # 2. カテゴリ別キーワードスコア
    keyword_result = calculate_keyword_score(episode_text, category)
    keyword_bonus = keyword_result["total"]
    score += keyword_bonus
    details["keyword_bonus"] = keyword_bonus
    details["matched_keywords"] = keyword_result["matched_ultra_famous"] + keyword_result["matched_famous"]

    # 3. 数値データの具体性（+8点）
    specificity_bonus = 0
    import re

    # 大きな数値（100以上）が含まれる場合
    large_numbers = re.findall(r"\d{3,}", episode_text.replace(",", ""))
    if large_numbers:
        specificity_bonus += 5

    # 年号（19xx, 20xx）が含まれる場合
    year_pattern = re.findall(r"(19|20)\d{2}年", episode_text)
    if year_pattern:
        specificity_bonus += 3

    score += min(specificity_bonus, 8)
    details["specificity_bonus"] = min(specificity_bonus, 8)

    # 4. 固有名詞（カタカナ）の存在（+2点/個、最大+6点）
    katakana_pattern = r"[ァ-ヴー]{3,}"
    katakana_words = re.findall(katakana_pattern, episode_text)
    proper_noun_bonus = min(len(katakana_words) * 2, 6)
    score += proper_noun_bonus
    details["specificity_bonus"] += proper_noun_bonus

    # 5. ペナルティ（個人的エピソード）
    if keyword_result["personal_count"] >= 2:
        details["penalty"] = keyword_result["personal_penalty"]

    # 6. 晩年エピソードボーナス
    if any(kw in episode_text for kw in ["最期", "逝去", "死去", "他界"]):
        score += 5

    # 正規化（40-100点）
    final_score = min(100, max(40, score))
    details["final_score"] = round(final_score, 1)

    return round(final_score, 1), details


def calculate_episode_importance_score_v2(row: pd.Series) -> float:
    """
    エピソード重要度スコアを算出（v2）

    評価基準：
    - エピソード有名度（60%）
    - composite_score（7軸スコア）（40%）
    """
    episode_fame, _ = calculate_episode_fame_score_v2(row)

    # composite_scoreを取得（7軸スコアの平均）
    composite = row.get("composite_score")
    if pd.notna(composite):
        try:
            composite_normalized = float(composite) * 10  # 0-100点に正規化
        except (ValueError, TypeError):
            composite_normalized = 50.0
    else:
        composite_normalized = 50.0

    # エピソード重要度 = 有名度60% + 品質40%
    importance = (episode_fame * 0.6) + (composite_normalized * 0.4)

    return round(importance, 2)


def process_all_episodes(dry_run: bool = True) -> Dict:
    """
    全エピソードの有名度スコアを処理

    Args:
        dry_run: Trueの場合、実際の保存は行わない

    Returns:
        処理結果の統計情報
    """
    print("=" * 80)
    print("📊 エピソード有名度スコア算出 v2（カテゴリ別キーワード対応）")
    print("=" * 80)
    print()

    # CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # カテゴリ分布を表示
    print("Step 2: カテゴリ分布の確認...")
    category_counts = df["category"].value_counts()
    print("  主要カテゴリ:")
    for cat, count in category_counts.head(10).items():
        normalized = normalize_category(cat)
        print(f"    {cat} → {normalized}: {count:,}件")
    print()

    # スコア算出
    print("Step 3: エピソード有名度算出中...")

    results = []
    score_distribution = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "40-49": 0}

    for idx, row in df.iterrows():
        fame_score, details = calculate_episode_fame_score_v2(row)
        importance_score = calculate_episode_importance_score_v2(row)

        results.append(
            {
                "index": idx,
                "episode_fame_score": fame_score,
                "episode_importance_score": importance_score,
                "details": details,
            }
        )

        # 分布を更新
        if fame_score >= 90:
            score_distribution["90-100"] += 1
        elif fame_score >= 80:
            score_distribution["80-89"] += 1
        elif fame_score >= 70:
            score_distribution["70-79"] += 1
        elif fame_score >= 60:
            score_distribution["60-69"] += 1
        elif fame_score >= 50:
            score_distribution["50-59"] += 1
        else:
            score_distribution["40-49"] += 1

        if (idx + 1) % 500 == 0:
            print(f"  処理中... {idx + 1:,}/{len(df):,}件")

    print(f"  ✅ 算出完了: {len(results):,}件")
    print()

    # スコア分布を表示
    print("Step 4: スコア分布:")
    for range_name, count in score_distribution.items():
        pct = (count / len(results)) * 100
        bar = "█" * int(pct / 2)
        print(f"  {range_name}点: {count:,}件 ({pct:.1f}%) {bar}")
    print()

    # サンプル表示
    print("Step 5: サンプル結果（最初の5件）:")
    for i, r in enumerate(results[:5]):
        idx = r["index"]
        row = df.iloc[idx]
        print(f"  [{row['episode_id']}] {row['person_name']} ({row['age']}歳)")
        print(f"    カテゴリ: {row['category']}")
        print(f"    有名度: {r['episode_fame_score']:.1f}点")
        print(f"    重要度: {r['episode_importance_score']:.2f}点")
        if r["details"]["matched_keywords"]:
            print(f"    マッチキーワード: {', '.join(r['details']['matched_keywords'][:3])}")
        print()

    if dry_run:
        print("=" * 80)
        print("🔍 Dry Run モード - 実際の保存は行いません")
        print("   保存するには --save オプションを付けて実行してください")
        print("=" * 80)
    else:
        # バックアップ作成
        print("Step 6: バックアップ作成中...")
        df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
        print()

        # スコア反映
        print("Step 7: スコア反映中...")
        if "episode_fame_score" not in df.columns:
            df["episode_fame_score"] = None
        if "episode_importance_score" not in df.columns:
            df["episode_importance_score"] = None

        for r in results:
            df.at[r["index"], "episode_fame_score"] = r["episode_fame_score"]
            df.at[r["index"], "episode_importance_score"] = r["episode_importance_score"]

        # 保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ 保存完了: {CSV_PATH}")
        print()

        print("=" * 80)
        print("✅ エピソード有名度の算出と反映が完了しました！")
        print("=" * 80)

    return {"total_processed": len(results), "score_distribution": score_distribution}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="エピソード有名度スコア算出（v2 - カテゴリ別キーワード対応）")
    parser.add_argument("--save", action="store_true", help="実際にCSVに保存する（デフォルトはdry run）")
    parser.add_argument("--sample", type=str, help="特定のperson_idのみ処理")

    args = parser.parse_args()

    if args.sample:
        # 特定のperson_idのみ処理
        print(f"サンプルモード: {args.sample}")
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        target_df = df[df["person_id"] == args.sample]

        if target_df.empty:
            print(f"  ⚠️ person_id '{args.sample}' が見つかりません")
            return

        print(f"  対象エピソード: {len(target_df)}件")
        print()

        for idx, row in target_df.iterrows():
            fame_score, details = calculate_episode_fame_score_v2(row)
            importance_score = calculate_episode_importance_score_v2(row)

            print(f"【{row['episode_id']}】 {row['age']}歳")
            print(f"  タイプ: {row['episode_type']}")
            print(f"  カテゴリ: {row['category']}")
            episode_short = str(row["episode_text"])[:80] + "..."
            print(f"  エピソード: {episode_short}")
            print(f"  → 有名度: {fame_score:.1f}点")
            print(
                f"     内訳: base={details['base_score']}, type={details['type_bonus']}, "
                f"keyword={details['keyword_bonus']}, spec={details['specificity_bonus']}"
            )
            if details["matched_keywords"]:
                print(f"     マッチ: {', '.join(details['matched_keywords'])}")
            print(f"  → 重要度: {importance_score:.2f}点")
            print()
    else:
        # 全件処理
        process_all_episodes(dry_run=not args.save)


if __name__ == "__main__":
    main()
