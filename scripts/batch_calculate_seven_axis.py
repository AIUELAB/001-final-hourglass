#!/usr/bin/env python3
"""
全エピソードの7軸スコア一括算出スクリプト

ストーリー品質と事実密度を全エピソードに対して算出
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    Path(__file__).parent.parent
    / f"MASTER_EPISODES_CURRENT_backup_before_seven_axis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def calculate_storytelling_quality(episode_text: str, episode_type: str) -> float:
    """ストーリー品質スコアを算出（1-10点）"""
    score = 5.0

    # テキストの長さ
    text_length = len(episode_text)
    if text_length > 250:
        score += 1.5
    elif text_length > 180:
        score += 1.0
    elif text_length > 120:
        score += 0.5

    # 感情表現
    emotion_keywords = [
        "感動",
        "喜び",
        "悲しみ",
        "怒り",
        "驚き",
        "恐怖",
        "不安",
        "希望",
        "愛",
        "絆",
        "友情",
        "憧れ",
        "葛藤",
        "苦悩",
        "決意",
        "勇気",
        "涙",
        "笑顔",
        "喪失",
        "再会",
        "別れ",
        "出会い",
    ]
    emotion_count = sum(1 for kw in emotion_keywords if kw in episode_text)
    score += min(emotion_count * 0.5, 2.0)

    # ストーリー要素
    story_elements = [
        "夢",
        "目標",
        "挑戦",
        "困難",
        "克服",
        "達成",
        "転機",
        "出発",
        "帰還",
        "変化",
        "成長",
        "学び",
        "試練",
        "突破",
        "革命",
        "改革",
    ]
    story_count = sum(1 for elem in story_elements if elem in episode_text)
    score += min(story_count * 0.3, 1.5)

    # 具体的な描写
    has_quotes = "「" in episode_text or "」" in episode_text
    has_numbers = bool(re.search(r"\d+", episode_text))
    if has_quotes:
        score += 0.5
    if has_numbers:
        score += 0.3

    # エピソードタイプによる調整
    type_weights = {
        "ACHIEVEMENT": 0.8,
        "TURNING_POINT": 1.2,
        "CHALLENGE": 1.1,
        "FAMILY": 1.3,
        "GROWTH": 1.2,
        "成長": 1.2,
        "FAILURE": 1.1,
        "COMEBACK": 1.2,
    }
    if episode_type in type_weights:
        score *= type_weights[episode_type]

    return min(max(score, 1.0), 10.0)


def calculate_factual_density(episode_text: str, episode_type: str) -> float:
    """事実密度スコアを算出（1-10点）"""
    score = 5.0

    # 数値データ
    numbers = re.findall(r"\d+", episode_text)
    number_count = len(numbers)
    score += min(number_count * 0.4, 2.5)

    # 固有名詞（カタカナ語）
    katakana_words = re.findall(r"[ァ-ヴー]{3,}", episode_text)
    score += min(len(katakana_words) * 0.3, 1.5)

    # 具体的な事実キーワード
    fact_keywords = [
        "記録",
        "達成",
        "受賞",
        "獲得",
        "認定",
        "登録",
        "ギネス",
        "初",
        "最",
        "第一号",
        "世界",
        "日本",
        "史上",
        "前人未到",
    ]
    fact_count = sum(1 for kw in fact_keywords if kw in episode_text)
    score += min(fact_count * 0.4, 2.0)

    # 引用や具体的な発言
    if "「" in episode_text and "」" in episode_text:
        score += 0.5

    # エピソードタイプによる調整
    type_weights = {
        "ACHIEVEMENT": 1.3,
        "TURNING_POINT": 0.9,
        "CHALLENGE": 1.1,
        "FAMILY": 0.8,
        "INNOVATION": 1.2,
        "FOUNDING": 1.2,
    }
    if episode_type in type_weights:
        score *= type_weights[episode_type]

    # 情報密度
    text_length = len(episode_text)
    if text_length > 0:
        info_density = (number_count + len(katakana_words) + fact_count) / (text_length / 50)
        if info_density > 2.0:
            score += 0.5
        elif info_density > 1.5:
            score += 0.3

    return min(max(score, 1.0), 10.0)


def batch_calculate():
    """全エピソードの7軸スコアを一括算出"""

    print("=" * 80)
    print("📊 全エピソードの7軸スコア一括算出")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: バックアップ作成
    print("Step 2: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 3: 現状確認
    print("Step 3: 現状確認中...")

    # ストーリー品質の確認（数値でないものをカウント）
    storytelling_needs_calc = 0
    for val in df["ストーリー品質"]:
        if pd.isna(val):
            storytelling_needs_calc += 1
        else:
            try:
                float(val)
            except (ValueError, TypeError):
                storytelling_needs_calc += 1

    # 事実密度の確認
    factual_needs_calc = df["事実密度"].isna().sum()

    print(f"  ストーリー品質の算出が必要: {storytelling_needs_calc:,}件")
    print(f"  事実密度の算出が必要: {factual_needs_calc:,}件")
    print()

    # Step 4: 一括算出
    print("Step 4: 7軸スコア一括算出中...")

    storytelling_updated = 0
    factual_updated = 0

    for idx, row in df.iterrows():
        episode_text = str(row["episode_text"])
        episode_type = str(row["episode_type"])

        # ストーリー品質の算出
        current_storytelling = row["ストーリー品質"]
        needs_storytelling = False

        if pd.isna(current_storytelling):
            needs_storytelling = True
        else:
            try:
                float(current_storytelling)
            except (ValueError, TypeError):
                needs_storytelling = True

        if needs_storytelling:
            storytelling_score = calculate_storytelling_quality(episode_text, episode_type)
            df.at[idx, "ストーリー品質"] = storytelling_score
            storytelling_updated += 1

        # 事実密度の算出
        if pd.isna(row["事実密度"]):
            factual_score = calculate_factual_density(episode_text, episode_type)
            df.at[idx, "事実密度"] = factual_score
            factual_updated += 1

        # 進捗表示（100件ごと）
        if (idx + 1) % 100 == 0:
            print(f"    進捗: {idx + 1:,}/{len(df):,}件処理完了...")

    print("  ✅ 算出完了")
    print(f"    - ストーリー品質: {storytelling_updated:,}件更新")
    print(f"    - 事実密度: {factual_updated:,}件更新")
    print()

    # Step 5: 7軸スコアの統計
    print("Step 5: 7軸スコア統計")

    axes = [
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
    ]

    complete_count = 0
    for _, row in df.iterrows():
        all_complete = True
        for axis in axes:
            if pd.isna(row[axis]):
                all_complete = False
                break
            try:
                float(row[axis])
            except (ValueError, TypeError):
                all_complete = False
                break
        if all_complete:
            complete_count += 1

    print(f"  7軸すべて揃っているエピソード: {complete_count:,}件 ({complete_count / len(df) * 100:.1f}%)")
    print()

    # 各軸の統計
    for axis in axes:
        numeric_values = []
        for val in df[axis]:
            if pd.notna(val):
                try:
                    numeric_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if numeric_values:
            avg = sum(numeric_values) / len(numeric_values)
            print(f"  {axis:15s}: 平均 {avg:.2f} ({len(numeric_values):,}件設定済み)")

    print()

    # Step 6: CSVファイル保存
    print("Step 6: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # サマリー
    print("=" * 80)
    print("✅ 7軸スコア一括算出が完了しました！")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 総エピソード数: {len(df):,}件")
    print(f"  - ストーリー品質更新: {storytelling_updated:,}件")
    print(f"  - 事実密度更新: {factual_updated:,}件")
    print(f"  - 7軸完全設定: {complete_count:,}件 ({complete_count / len(df) * 100:.1f}%)")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print()


if __name__ == "__main__":
    batch_calculate()
