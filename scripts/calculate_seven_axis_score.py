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
    ストーリー品質スコアを算出（改善版v2）（1-10点）

    評価基準：
    - ストーリーの構成: 起承転結があるか
    - 感情の描写: 感情が伝わるか
    - 臨場感: 場面が想像できるか
    - 引き込む力: 続きが気になるか
    - ペナルティ要素追加
    """
    score = 3.0  # ベーススコア（下方修正）

    # テキストの長さ
    text_length = len(episode_text)
    if text_length > 280:
        score += 2.0
    elif text_length > 220:
        score += 1.5
    elif text_length > 180:
        score += 1.0
    elif text_length > 140:
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
        "感謝",
        "誇り",
    ]
    emotion_count = sum(1 for kw in emotion_keywords if kw in episode_text)
    score += min(emotion_count * 0.6, 2.5)

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
        "決断",
        "冒険",
        "奇跡",
        "運命",
    ]
    story_count = sum(1 for elem in story_elements if elem in episode_text)
    score += min(story_count * 0.4, 2.0)

    # 具体的な描写（固有名詞、数値、引用）
    quote_count = episode_text.count("「")
    has_numbers = bool(re.search(r"\d+", episode_text))
    if quote_count >= 2:
        score += 1.0
    elif quote_count >= 1:
        score += 0.5
    if has_numbers:
        score += 0.5

    # エピソードタイプによる調整
    type_weights = {
        "ACHIEVEMENT": 0.9,
        "TURNING_POINT": 1.15,
        "CHALLENGE": 1.1,
        "FAMILY": 1.2,
        "GROWTH": 1.15,
        "FAILURE": 1.1,
        "COMEBACK": 1.15,
        "INNOVATION": 1.0,
        "FOUNDING": 1.0,
    }
    if episode_type in type_weights:
        score *= type_weights[episode_type]

    # ペナルティ要素
    # 感情・ストーリー要素がない
    if emotion_count == 0 and story_count == 0:
        score -= 1.5

    # テキストが短すぎる
    if text_length < 100:
        score -= 1.0

    return round(min(max(score, 1.0), 10.0), 2)


def calculate_factual_density(episode_text: str, episode_type: str) -> float:
    """
    事実密度スコアを算出（改善版v3）（1-10点）

    評価基準：
    - 具体的な数値データ: 年号、数量、記録など（年齢は除外）
    - 固有名詞: 人名、地名、作品名など
    - 検証可能な事実: 記録、受賞、出来事など
    - 情報の密度: 単位文字数あたりの情報量
    - ペナルティ要素強化
    """
    score = 3.0  # ベーススコア

    # 数値データの存在（年号、数量、スコアなど）※年齢の"歳"は除く
    # 年号パターン (19XX年, 20XX年)
    year_count = len(re.findall(r"(19|20)\d{2}年", episode_text))
    # 具体的な数値（3桁以上の数字、または単位付き）
    specific_numbers = len(re.findall(r"\d{3,}|[\d.]+[万億千百%km時分秒位回勝敗本冊枚円ドル]", episode_text))

    score += min(year_count * 0.4, 1.5)
    score += min(specific_numbers * 0.3, 1.5)

    # 固有名詞の推定（カタカナ4文字以上、より厳格に）
    katakana_words = re.findall(r"[ァ-ヴー]{4,}", episode_text)
    katakana_count = len(katakana_words)
    score += min(katakana_count * 0.3, 1.5)

    # 具体的な事実を示すキーワード（「年」「歳」を除外）
    high_fact_keywords = [
        "記録",
        "達成",
        "受賞",
        "獲得",
        "認定",
        "登録",
        "ギネス",
        "優勝",
        "金メダル",
        "銀メダル",
        "銅メダル",
        "世界一",
        "日本一",
    ]
    medium_fact_keywords = [
        "史上初",
        "世界初",
        "日本初",
        "前人未到",
        "第一号",
        "発表",
        "発売",
        "公開",
        "出版",
        "創設",
    ]

    high_fact_count = sum(1 for kw in high_fact_keywords if kw in episode_text)
    medium_fact_count = sum(1 for kw in medium_fact_keywords if kw in episode_text)

    score += min(high_fact_count * 0.5, 1.5)
    score += min(medium_fact_count * 0.3, 1.0)

    # 引用や具体的な発言（複数の引用がある場合のみ加点）
    quote_count = episode_text.count("「")
    if quote_count >= 3:
        score += 0.8
    elif quote_count >= 2:
        score += 0.4

    # エピソードタイプによる調整（倍率を緩やかに）
    type_weights = {
        "ACHIEVEMENT": 1.1,
        "TURNING_POINT": 0.95,
        "CHALLENGE": 1.0,
        "FAMILY": 0.9,
        "INNOVATION": 1.1,
        "FOUNDING": 1.1,
        "GROWTH": 0.95,
        "FAILURE": 0.95,
        "COMEBACK": 1.0,
    }
    if episode_type in type_weights:
        score *= type_weights[episode_type]

    # テキストの長さに対する情報量（密度）- より厳格に
    text_length = len(episode_text)
    total_facts = year_count + specific_numbers + katakana_count + high_fact_count + medium_fact_count
    if text_length > 0:
        info_density = total_facts / (text_length / 100)
        if info_density > 4.0:
            score += 0.8
        elif info_density > 3.0:
            score += 0.5
        elif info_density > 2.0:
            score += 0.3

    # ペナルティ要素（強化）
    # 具体的な数値・年号がない
    if year_count == 0 and specific_numbers == 0:
        score -= 1.5
    elif year_count + specific_numbers <= 1:
        score -= 0.5

    # 固有名詞がほとんどない
    if katakana_count == 0:
        score -= 0.8

    # 事実キーワードがない
    if high_fact_count == 0 and medium_fact_count == 0:
        score -= 1.0

    # テキストが短すぎる
    if text_length < 150:
        score -= 0.5

    return round(min(max(score, 1.0), 10.0), 2)


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
