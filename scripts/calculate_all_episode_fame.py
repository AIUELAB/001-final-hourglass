#!/usr/bin/env python3
"""
全エピソードの有名度スコア算出スクリプト

各エピソードの内容・重要性に基づいて有名度を算出
"""

from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    Path(__file__).parent.parent
    / f"MASTER_EPISODES_CURRENT_backup_before_all_episode_fame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def calculate_episode_fame_score(row: pd.Series) -> float:
    """
    エピソードの有名度スコアを算出（0-100点）

    評価基準：
    - エピソードタイプ
    - キーワード（ギネス、世界初、代表作など）
    - 作品の知名度
    - 社会的影響
    """
    score = 50.0  # ベーススコア

    episode_text = str(row.get("episode_text", "")).lower()
    episode_type = str(row.get("episode_type", ""))

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

    # 超有名キーワード（+15-20点）
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
        "ノーベル賞",
        "nobel prize",
        "オリンピック",
        "olympic",
        "世界大戦",
        "world war",
    ]
    for keyword in ultra_famous_keywords:
        if keyword in episode_text:
            score += 18
            break

    # 有名作品・キーワード（+10-15点）
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
        "革命",
        "revolution",
        "創業",
        "founding",
        "発明",
        "invention",
    ]
    for keyword in famous_keywords:
        if keyword in episode_text:
            score += 12
            break

    # 影響力キーワード（+5-10点）
    impact_keywords = [
        "影響",
        "influence",
        "impact",
        "文化",
        "culture",
        "先駆者",
        "pioneer",
        "創造",
        "creation",
        "半世紀",
        "50年",
        "記録",
        "record",
        "受賞",
        "award",
        "栄誉",
        "honor",
    ]
    impact_count = sum(1 for keyword in impact_keywords if keyword in episode_text)
    score += min(impact_count * 3, 10)

    # 数値データ（具体性）
    import re

    # 大きな数字（1000以上）があれば具体性が高い
    numbers = re.findall(r"\d{4,}", episode_text)
    if numbers:
        score += 8

    # 固有名詞（作品名・組織名など）
    proper_nouns = [
        "週刊少年マガジン",
        "週刊少年ジャンプ",
        "週刊少年サンデー",
        "トキワ荘",
        "wikipedia",
        "ウィキペディア",
        "東京大学",
        "harvard",
        "mit",
        "nasa",
        "un",
        "国連",
    ]
    noun_count = sum(1 for noun in proper_nouns if noun in episode_text)
    score += min(noun_count * 2, 6)

    # 個人的・私的なエピソードはペナルティ
    personal_keywords = ["姉", "家族", "個人的", "personal", "病", "入院", "日記", "手紙"]
    personal_count = sum(1 for keyword in personal_keywords if keyword in episode_text)
    if personal_count >= 2:
        score -= 15  # 個人的なエピソードは有名度が低い

    # 最期・晩年のエピソード
    if "最期" in episode_text or "逝去" in episode_text or "死去" in episode_text:
        score += 5  # 晩年エピソードはやや有名

    # 正規化（40-100点）
    final_score = min(100, max(40, score))

    return round(final_score, 1)


def calculate_episode_importance_score(row: pd.Series, episode_fame: float) -> float:
    """
    エピソード重要度スコアを算出（0-100点）

    評価基準：
    - エピソード有名度
    - composite_score（7軸スコア）
    - エピソードタイプ
    """
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
    print("📊 全エピソードの有名度スコア算出")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: 既存のスコアを確認
    print("Step 2: 既存スコア確認中...")
    existing_count = df["episode_fame_score"].notna().sum()
    print(f"  既存スコアあり: {existing_count}件")
    print(f"  既存スコアなし: {len(df) - existing_count}件")
    print()

    # Step 3: 全エピソードの有名度を算出
    print("Step 3: 全エピソード有名度算出中...")
    print()

    # バックアップ作成
    print("  バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # カラムを追加（存在しない場合）
    if "episode_fame_score" not in df.columns:
        df["episode_fame_score"] = None
    if "episode_importance_score" not in df.columns:
        df["episode_importance_score"] = None

    # 各エピソードの有名度を算出
    for idx, row in df.iterrows():
        # エピソード有名度を算出
        episode_fame = calculate_episode_fame_score(row)

        # エピソード重要度を算出
        episode_importance = calculate_episode_importance_score(row, episode_fame)

        # データフレームに保存
        df.at[idx, "episode_fame_score"] = episode_fame
        df.at[idx, "episode_importance_score"] = episode_importance

        # 100件ごとに進捗表示
        if (idx + 1) % 100 == 0:
            print(f"  処理中: {idx + 1:,} / {len(df):,} 件 ({(idx + 1) / len(df) * 100:.1f}%)")

    print(f"  ✅ 全{len(df):,}件の算出完了")
    print()

    # Step 4: 統計情報
    print("=" * 80)
    print("Step 4: 統計情報")
    print("=" * 80)
    print()

    print("エピソード有名度スコア:")
    print(f"  平均: {df['episode_fame_score'].mean():.1f}点")
    print(f"  中央値: {df['episode_fame_score'].median():.1f}点")
    print(f"  最小: {df['episode_fame_score'].min():.1f}点")
    print(f"  最大: {df['episode_fame_score'].max():.1f}点")
    print()

    print("エピソード重要度スコア:")
    print(f"  平均: {df['episode_importance_score'].mean():.2f}点")
    print(f"  中央値: {df['episode_importance_score'].median():.2f}点")
    print(f"  最小: {df['episode_importance_score'].min():.2f}点")
    print(f"  最大: {df['episode_importance_score'].max():.2f}点")
    print()

    # スコア分布
    print("エピソード有名度の分布:")
    print(f"  90点以上: {(df['episode_fame_score'] >= 90).sum()}件")
    print(f"  80-89点: {((df['episode_fame_score'] >= 80) & (df['episode_fame_score'] < 90)).sum()}件")
    print(f"  70-79点: {((df['episode_fame_score'] >= 70) & (df['episode_fame_score'] < 80)).sum()}件")
    print(f"  60-69点: {((df['episode_fame_score'] >= 60) & (df['episode_fame_score'] < 70)).sum()}件")
    print(f"  60点未満: {(df['episode_fame_score'] < 60).sum()}件")
    print()

    # Step 5: CSVに保存
    print("Step 5: CSVファイルへの保存")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    print("=" * 80)
    print("✅ 全エピソードの有名度算出が完了しました！")
    print("=" * 80)


if __name__ == "__main__":
    main()
