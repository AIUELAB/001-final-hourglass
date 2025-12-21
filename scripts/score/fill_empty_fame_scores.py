#!/usr/bin/env python3
"""
空白の有名度スコア（fame_score, episode_fame_score）を補完するスクリプト

対象: fame_score / episode_fame_score が空白のエピソードのみ
方法:
  - fame_score: 人物の知名度に基づくスコア（カテゴリ・Wikipedia等を参照）
  - episode_fame_score: calculate_episode_fame_v2のロジックを使用
"""

import sys
from pathlib import Path

# backendモジュールをインポートするためのパス追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from datetime import datetime

import pandas as pd

# カテゴリ別キーワード辞書をインポート
from app.utils.keyword_dictionaries import calculate_keyword_score

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    PROJECT_ROOT
    / "preserved"
    / "data"
    / f"MASTER_EPISODES_CURRENT_backup_before_fame_fill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


# ====== 人物有名度（fame_score）の推定ロジック ======

# 有名人物のベーススコア（手動定義）
FAMOUS_PERSON_SCORES = {
    # 世界的有名人（9.0-10.0）
    "スティーブ・ジョブズ": 9.5,
    "ウォルト・ディズニー": 9.5,
    "トーマス・エジソン": 9.5,
    "アルベルト・アインシュタイン": 9.8,
    "マイケル・ジャクソン": 9.5,
    "ビートルズ": 9.5,
    "ビル・ゲイツ": 9.3,
    "イーロン・マスク": 9.0,
    "オプラ・ウィンフリー": 8.5,
    "J・K・ローリング": 8.8,
    # 日本の有名人（8.0-9.5）
    "本田宗一郎": 8.8,
    "松下幸之助": 8.7,
    "宮崎駿": 9.0,
    "手塚治虫": 8.8,
    "イチロー": 9.0,
    "大谷翔平": 9.2,
    "黒澤明": 8.8,
    "坂本龍馬": 8.5,
    "織田信長": 8.8,
    "豊臣秀吉": 8.5,
    "徳川家康": 8.5,
    "福沢諭吉": 8.3,
    "夏目漱石": 8.3,
    "野口英世": 8.2,
    "羽生結弦": 8.5,
    "浅田真央": 8.3,
}

# カテゴリ別のデフォルトfame_score
CATEGORY_DEFAULT_FAME = {
    "経営・ビジネス": 7.0,
    "スポーツ": 7.0,
    "漫画・アニメ": 6.5,
    "映画・音楽": 7.0,
    "科学・技術": 6.5,
    "政治・社会": 7.0,
    "文学・思想": 6.5,
    "歴史・軍事": 7.0,
    "芸能・エンタメ": 6.5,
    "その他": 6.0,
}


def estimate_fame_score(person_name: str, category: str) -> float:
    """
    人物の有名度スコアを推定

    Args:
        person_name: 人物名
        category: カテゴリ

    Returns:
        fame_score (1.0-10.0)
    """
    # 1. 手動定義されている有名人はそのスコアを使用
    if person_name in FAMOUS_PERSON_SCORES:
        return FAMOUS_PERSON_SCORES[person_name]

    # 2. カテゴリ別デフォルト値
    base_score = CATEGORY_DEFAULT_FAME.get(category, 6.0)

    return round(base_score, 1)


# ====== エピソード有名度（episode_fame_score）の計算ロジック ======


def calculate_episode_fame_score_v2(row: pd.Series) -> float:
    """
    エピソードの有名度スコアを算出（v2 - カテゴリ別対応）

    Args:
        row: エピソードの行データ

    Returns:
        スコア (40.0-100.0)
    """
    import re

    score = 50.0  # ベーススコア

    episode_text = str(row.get("episode_text", ""))
    episode_type = str(row.get("episode_type", ""))
    category = str(row.get("category", ""))

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

    # 2. カテゴリ別キーワードスコア
    keyword_result = calculate_keyword_score(episode_text, category)
    keyword_bonus = keyword_result["total"]
    score += keyword_bonus

    # 3. 数値データの具体性（+8点）
    specificity_bonus = 0

    # 大きな数値（100以上）が含まれる場合
    large_numbers = re.findall(r"\d{3,}", episode_text.replace(",", ""))
    if large_numbers:
        specificity_bonus += 5

    # 年号（19xx, 20xx）が含まれる場合
    year_pattern = re.findall(r"(19|20)\d{2}年", episode_text)
    if year_pattern:
        specificity_bonus += 3

    score += min(specificity_bonus, 8)

    # 4. 固有名詞（カタカナ）の存在（+2点/個、最大+6点）
    katakana_pattern = r"[ァ-ヴー]{3,}"
    katakana_words = re.findall(katakana_pattern, episode_text)
    proper_noun_bonus = min(len(katakana_words) * 2, 6)
    score += proper_noun_bonus

    # 5. 晩年エピソードボーナス
    if any(kw in episode_text for kw in ["最期", "逝去", "死去", "他界"]):
        score += 5

    # 正規化（40-100点）
    final_score = min(100, max(40, score))

    return round(final_score, 1)


def fill_empty_fame_scores(dry_run: bool = True):
    """
    空白のfame_score/episode_fame_scoreを補完

    Args:
        dry_run: Trueの場合、実際の保存は行わない
    """
    print("=" * 80)
    print("📊 空白有名度スコア補完ツール")
    print("=" * 80)
    print()

    # CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # 空白データの特定
    print("Step 2: 空白データの特定...")

    # fame_scoreが空白の行
    empty_fame = df[df["fame_score"].isna() | (df["fame_score"].astype(str).str.strip() == "")]
    print(f"  fame_score空白: {len(empty_fame)}件")

    # episode_fame_scoreが空白の行
    empty_ep_fame = df[df["episode_fame_score"].isna() | (df["episode_fame_score"].astype(str).str.strip() == "")]
    print(f"  episode_fame_score空白: {len(empty_ep_fame)}件")
    print()

    if len(empty_fame) == 0 and len(empty_ep_fame) == 0:
        print("✅ 空白データはありません。処理を終了します。")
        return

    # 空白データのサンプル表示
    print("Step 3: 空白データのサンプル:")
    for idx, row in empty_fame.head(10).iterrows():
        print(f"  [{row['episode_id']}] {row['person_name']} ({row['category']})")
    print()

    # スコア算出
    print("Step 4: スコア算出中...")

    filled_count = 0
    results = []

    for idx in df.index:
        row = df.loc[idx]
        updated = False
        fame_score = None
        ep_fame_score = None

        # fame_scoreが空白なら補完
        current_fame = row.get("fame_score")
        if pd.isna(current_fame) or str(current_fame).strip() == "":
            fame_score = estimate_fame_score(row["person_name"], row["category"])
            df.at[idx, "fame_score"] = fame_score
            updated = True

        # episode_fame_scoreが空白なら補完
        current_ep_fame = row.get("episode_fame_score")
        if pd.isna(current_ep_fame) or str(current_ep_fame).strip() == "":
            ep_fame_score = calculate_episode_fame_score_v2(row)
            df.at[idx, "episode_fame_score"] = ep_fame_score
            updated = True

        if updated:
            filled_count += 1
            results.append(
                {
                    "episode_id": row["episode_id"],
                    "person_name": row["person_name"],
                    "fame_score": fame_score,
                    "episode_fame_score": ep_fame_score,
                }
            )

    print(f"  ✅ {filled_count}件のスコアを補完")
    print()

    # 補完結果のサンプル表示
    print("Step 5: 補完結果のサンプル:")
    for r in results[:10]:
        fame_str = f"{r['fame_score']:.1f}" if r["fame_score"] else "-"
        ep_fame_str = f"{r['episode_fame_score']:.1f}" if r["episode_fame_score"] else "-"
        print(f"  [{r['episode_id']}] {r['person_name']}")
        print(f"    fame_score: {fame_str}, episode_fame_score: {ep_fame_str}")
    print()

    if dry_run:
        print("=" * 80)
        print("🔍 Dry Run モード - 実際の保存は行いません")
        print("   保存するには --save オプションを付けて実行してください")
        print("=" * 80)
    else:
        # バックアップ作成
        print("Step 6: バックアップ作成中...")
        original_df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        original_df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
        print()

        # 保存
        print("Step 7: CSVファイル保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ 保存完了: {CSV_PATH}")
        print()

        print("=" * 80)
        print(f"✅ {filled_count}件の空白スコアを補完しました！")
        print("=" * 80)

    return {"filled_count": filled_count, "results": results}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="空白の有名度スコアを補完")
    parser.add_argument("--save", action="store_true", help="実際にCSVに保存する（デフォルトはdry run）")

    args = parser.parse_args()

    fill_empty_fame_scores(dry_run=not args.save)


if __name__ == "__main__":
    main()
