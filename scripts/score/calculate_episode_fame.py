#!/usr/bin/env python3
"""
エピソード有名度スコア算出スクリプト

各エピソードの内容・重要性に基づいて有名度を算出
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    Path(__file__).parent.parent
    / f"MASTER_EPISODES_CURRENT_backup_before_episode_fame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def calculate_episode_fame_score(row: pd.Series) -> float:
    """
    エピソードの有名度スコアを算出（0-100点）

    評価基準：
    - エピソードタイプ
    - キーワード（ギネス、世界初、代表作など）
    - 作品の知名度
    - 社会的影響

    注意: キーワードボーナスは事実密度≥5.0の場合のみ最大効果を発揮
    """
    score = 50.0  # ベーススコア
    keyword_bonus_total = 0.0  # キーワードボーナス累計

    episode_text = str(row.get("episode_text", "")).lower()
    episode_type = str(row.get("episode_type", ""))

    # 事実密度を取得（キーワードボーナス条件に使用）
    fact_density = 0.0
    try:
        fact_density = float(row.get("事実密度", 0) or 0)
    except (ValueError, TypeError):
        fact_density = 0.0

    # キーワードボーナス係数（事実密度に応じて0.5-1.0）
    keyword_multiplier = 1.0 if fact_density >= 5.0 else 0.5

    # エピソードタイプによる補正
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
    score += type_scores.get(episode_type, 5)

    # 超有名キーワード（+10点×係数、上限10点）
    ultra_famous_keywords = [
        "ギネス",
        "guinness",
        "guinness world records",
        "世界記録",
        "world record",
        "仮面ライダー",
        "kamen rider",
        "国民的",
        "national",
        "社会現象",
        "social phenomenon",
    ]
    for keyword in ultra_famous_keywords:
        if keyword in episode_text:
            keyword_bonus_total += 10 * keyword_multiplier
            break

    # 有名作品・キーワード（+8点×係数、上限8点）
    famous_keywords = [
        "サイボーグ009",
        "cyborg 009",
        "世界初",
        "world first",
        "世界で初めて",
        "日本初",
        "japan first",
        "代表作",
        "masterpiece",
        "金字塔",
        "milestone",
        "伝説",
        "legend",
    ]
    for keyword in famous_keywords:
        if keyword in episode_text:
            keyword_bonus_total += 8 * keyword_multiplier
            break

    # キーワードボーナス上限適用（最大+15点）
    score += min(keyword_bonus_total, 15.0)

    # 影響力キーワード（+5-10点）
    impact_keywords = [
        "影響",
        "influence",
        "impact",
        "文化",
        "culture",
        "革命",
        "revolution",
        "先駆者",
        "pioneer",
        "創造",
        "creation",
        "半世紀",
        "50年",
    ]
    impact_count = sum(1 for keyword in impact_keywords if keyword in episode_text)
    score += min(impact_count * 3, 10)

    # 数値データ（具体性）
    if "770作品" in episode_text or "500巻" in episode_text or "128,000" in episode_text:
        score += 8  # 具体的な記録

    # 固有名詞（作品名・組織名など）
    proper_nouns = [
        "週刊少年マガジン",
        "週刊少年ジャンプ",
        "週刊少年サンデー",
        "トキワ荘",
        "wikipedia",
        "ウィキペディア",
    ]
    noun_count = sum(1 for noun in proper_nouns if noun in episode_text)
    score += min(noun_count * 2, 6)

    # 個人的・私的なエピソードはペナルティ
    personal_keywords = ["姉", "家族", "個人的", "personal", "病", "入院"]
    personal_count = sum(1 for keyword in personal_keywords if keyword in episode_text)
    if personal_count >= 2:
        score -= 15  # 個人的なエピソードは有名度が低い

    # 最期・晩年のエピソード
    if "最期" in episode_text or "逝去" in episode_text or "死" in episode_text:
        score += 5  # 晩年エピソードはやや有名

    # 正規化（40-100点）
    final_score = min(100, max(40, score))

    return round(final_score, 1)


def calculate_episode_importance_score(row: pd.Series) -> float:
    """
    エピソード重要度スコアを算出（0-100点）

    評価基準：
    - エピソード有名度
    - composite_score（7軸スコア）
    - エピソードタイプ
    """
    episode_fame = calculate_episode_fame_score(row)

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


def main():
    print("=" * 80)
    print("📊 エピソード有名度スコア算出")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: P596E029（石ノ森章太郎）のエピソードを抽出
    print("Step 2: P596E029（石ノ森章太郎）のエピソードを抽出中...")
    target_df = df[df["person_id"] == "P596E029"].copy()
    print(f"  対象エピソード: {len(target_df)}件")
    print()

    # Step 3: 各エピソードの有名度を算出
    print("Step 3: エピソード有名度算出中...")
    print()

    results = []

    for idx, row in target_df.iterrows():
        episode_id = row["episode_id"]
        age = row["age"]
        episode_type = row["episode_type"]

        # エピソード有名度を算出
        episode_fame = calculate_episode_fame_score(row)

        # エピソード重要度を算出
        episode_importance = calculate_episode_importance_score(row)

        # 結果を保存
        results.append(
            {
                "index": idx,
                "episode_id": episode_id,
                "age": age,
                "episode_type": episode_type,
                "episode_fame_score": episode_fame,
                "episode_importance_score": episode_importance,
            }
        )

        # エピソードテキストの抜粋
        episode_text_short = str(row["episode_text"])[:80] + "..."

        print(f"【{episode_id}】 {age}歳")
        print(f"  タイプ: {episode_type}")
        print(f"  エピソード: {episode_text_short}")
        print(f"  → エピソード有名度: {episode_fame:.1f}点")
        print(f"  → エピソード重要度: {episode_importance:.2f}点")
        print()

    # Step 4: CSVに反映するか確認
    print("=" * 80)
    print("Step 4: CSVファイルへの反映")
    print("=" * 80)
    print()

    print("算出されたスコア:")
    for r in results:
        print(
            f"  {r['episode_id']}: fame={r['episode_fame_score']:.1f}, importance={r['episode_importance_score']:.2f}"
        )
    print()

    update = input("CSVファイルに反映しますか？ (y/N): ")

    if update.lower() == "y":
        print()
        print("Step 5: バックアップ作成中...")
        df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
        print()

        print("Step 6: スコア反映中...")

        # CSVファイルにカラムを追加（存在しない場合）
        if "episode_fame_score" not in df.columns:
            df["episode_fame_score"] = None
        if "episode_importance_score" not in df.columns:
            df["episode_importance_score"] = None

        # スコアを反映
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
    else:
        print()
        print("ℹ️  CSVへの反映はキャンセルされました")


if __name__ == "__main__":
    main()
