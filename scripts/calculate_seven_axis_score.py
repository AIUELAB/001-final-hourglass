#!/usr/bin/env python3
"""
7軸スコア算出スクリプト

エピソードの7軸スコア（記憶性、共感性、意外性、生成品質、教育的価値、ストーリー品質、事実密度）を算出
"""

import re
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"


def calculate_storytelling_quality(episode_text: str, episode_type: str) -> float:
    """
    ストーリー品質スコアを算出（1-10点）

    評価基準：
    - ストーリーの構成: 起承転結があるか
    - 感情の描写: 感情が伝わるか
    - 臨場感: 場面が想像できるか
    - 引き込む力: 続きが気になるか
    """
    # LLM検証で-2.18のバイアスあり → ベーススコアを上方修正（2回目調整）
    score = 5.2  # ベーススコア（2回目調整済み）

    # テキストの長さ（長いほどストーリー性が高い傾向）
    text_length = len(episode_text)
    if text_length > 250:
        score += 1.5
    elif text_length > 180:
        score += 1.0
    elif text_length > 120:
        score += 0.5

    # 感情表現の存在
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

    # ストーリー要素の存在
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

    # 具体的な描写（固有名詞、数値、引用）
    has_quotes = "「" in episode_text or "」" in episode_text
    has_numbers = bool(re.search(r"\d+", episode_text))
    if has_quotes:
        score += 0.5
    if has_numbers:
        score += 0.3

    # エピソードタイプによる調整
    type_weights = {
        "ACHIEVEMENT": 0.8,  # 達成系は事実重視でストーリー性は中程度
        "TURNING_POINT": 1.2,  # 転機はストーリー性が高い
        "CHALLENGE": 1.1,
        "FAMILY": 1.3,  # 家族系は感情描写が豊か
        "GROWTH": 1.2,
        "FAILURE": 1.1,
        "COMEBACK": 1.2,
    }
    if episode_type in type_weights:
        score *= type_weights[episode_type]

    return min(max(score, 1.0), 10.0)


def calculate_factual_density(episode_text: str, episode_type: str) -> float:
    """
    事実密度スコアを算出（1-10点）

    評価基準：
    - 具体的な数値データ: 年号、数量、年齢など
    - 固有名詞: 人名、地名、作品名など
    - 検証可能な事実: 記録、受賞、出来事など
    - 情報の密度: 単位文字数あたりの情報量
    """
    # LLM検証で-0.58のバイアスあり → ベーススコアを微調整（最終調整）
    score = 2.8  # ベーススコア（最終調整済み）

    # 数値データの存在（年号、数量、年齢、スコアなど）
    numbers = re.findall(r"\d+", episode_text)
    number_count = len(numbers)
    score += min(number_count * 0.4, 2.5)

    # 固有名詞の推定（カタカナ、漢字名詞）
    # カタカナ語（人名、地名、作品名）
    katakana_words = re.findall(r"[ァ-ヴー]{3,}", episode_text)
    score += min(len(katakana_words) * 0.3, 1.5)

    # 具体的な事実を示すキーワード
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
        "〜年",
        "〜月",
        "〜日",
        "〜歳",
    ]
    fact_count = sum(1 for kw in fact_keywords if kw in episode_text)
    score += min(fact_count * 0.4, 2.0)

    # 引用や具体的な発言
    if "「" in episode_text and "」" in episode_text:
        score += 0.5

    # 検証可能な情報（Wikipedia, 受賞歴など）
    verification_keywords = ["Wikipedia", "公式", "発表", "報道", "記事", "文献"]
    if any(kw in episode_text for kw in verification_keywords):
        score += 0.5

    # エピソードタイプによる調整
    type_weights = {
        "ACHIEVEMENT": 1.3,  # 達成系は事実密度が高い
        "TURNING_POINT": 0.9,
        "CHALLENGE": 1.1,
        "FAMILY": 0.8,  # 家族系は感情重視で事実は少なめ
        "INNOVATION": 1.2,
        "FOUNDING": 1.2,
    }
    if episode_type in type_weights:
        score *= type_weights[episode_type]

    # テキストの長さに対する情報量（密度）
    text_length = len(episode_text)
    info_density = (number_count + len(katakana_words) + fact_count) / (text_length / 50)
    if info_density > 2.0:
        score += 0.5
    elif info_density > 1.5:
        score += 0.3

    return min(max(score, 1.0), 10.0)


def calculate_seven_axis_score(episode_id: str):
    """指定されたエピソードの7軸スコアを算出"""

    # CSVファイル読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # エピソード取得
    episode = df[df["episode_id"] == episode_id]
    if episode.empty:
        print(f"❌ エピソードID '{episode_id}' が見つかりませんでした")
        return

    row = episode.iloc[0]

    print("=" * 80)
    print(f"📊 7軸スコア算出: {episode_id}")
    print("=" * 80)
    print()

    # 基本情報
    print("【基本情報】")
    print(f"  人物名: {row['person_name']}")
    print(f"  年齢: {row['age']}歳")
    print(f"  カテゴリ: {row['category']}")
    print(f"  エピソードタイプ: {row['episode_type']}")
    print()

    # エピソードテキスト
    print("【エピソードテキスト】")
    episode_text = str(row["episode_text"])
    print(f"  {episode_text[:200]}...")
    print()

    # 既存の7軸スコア
    print("【既存の7軸スコア】")
    axis_scores = {
        "記憶性スコア": row.get("記憶性スコア"),
        "共感性スコア": row.get("共感性スコア"),
        "意外性スコア": row.get("意外性スコア"),
        "生成品質スコア": row.get("生成品質スコア"),
        "教育的価値": row.get("教育的価値"),
        "ストーリー品質": row.get("ストーリー品質"),
        "事実密度": row.get("事実密度"),
    }

    for axis, score in axis_scores.items():
        if pd.notna(score):
            try:
                score_value = float(score)
                print(f"  {axis:15s}: {score_value:.1f}")
            except (ValueError, TypeError):
                print(f"  {axis:15s}: {score} (数値変換不可)")
        else:
            print(f"  {axis:15s}: （未設定）")
    print()

    # 新規算出が必要なスコア
    print("【新規算出】")

    # ストーリー品質
    storytelling_score = calculate_storytelling_quality(episode_text, str(row["episode_type"]))
    print(f"  ストーリー品質: {storytelling_score:.1f}")

    # 事実密度
    factual_density = calculate_factual_density(episode_text, str(row["episode_type"]))
    print(f"  事実密度: {factual_density:.1f}")
    print()

    # 総合スコア（7軸の平均）
    print("【7軸スコア統合】")

    # 既存スコアを取得（数値のみ）
    final_scores = {}
    for axis, score in axis_scores.items():
        if pd.notna(score):
            try:
                final_scores[axis] = float(score)
            except (ValueError, TypeError):
                pass

    # 新規算出スコアを追加
    final_scores["ストーリー品質"] = storytelling_score
    final_scores["事実密度"] = factual_density

    # 7軸すべてが揃っているか確認
    all_axes = [
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
    ]

    print("  全7軸スコア:")
    for i, axis in enumerate(all_axes, 1):
        score_val = final_scores.get(axis, None)
        if score_val is not None:
            print(f"    {i}. {axis:15s}: {score_val:.1f}")
        else:
            print(f"    {i}. {axis:15s}: （未設定）")

    # 平均スコア計算
    if len(final_scores) == 7:
        average_score = sum(final_scores.values()) / 7
        print()
        print(f"  📊 7軸平均スコア: {average_score:.2f}")
    else:
        print()
        print(f"  ⚠️  7軸のうち{len(final_scores)}軸のみ設定されています")

    print()
    print("=" * 80)
    print("✅ 7軸スコア算出完了")
    print("=" * 80)

    # CSVへの反映（オプション）
    print()
    update = input("CSVファイルに算出結果を反映しますか？ (y/N): ")
    if update.lower() == "y":
        df.loc[df["episode_id"] == episode_id, "ストーリー品質"] = storytelling_score
        df.loc[df["episode_id"] == episode_id, "事実密度"] = factual_density
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print("✅ CSVファイルを更新しました")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        episode_id = sys.argv[1]
    else:
        episode_id = "EP-001,713"

    calculate_seven_axis_score(episode_id)
