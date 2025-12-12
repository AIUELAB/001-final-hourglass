#!/usr/bin/env python3
"""
全欠損スコアを一括補完するスクリプト

対象:
  - 教育的価値、ストーリー品質、事実密度（ヒューリスティックベース）
  - fame_score（人物有名度）
  - episode_fame_score（エピソード有名度）
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


# ====== 7軸スコア算出ロジック ======


def calculate_storytelling_quality(episode_text: str, episode_type: str) -> float:
    """ストーリー品質スコアを算出（1-10点）"""
    if pd.isna(episode_text) or not episode_text:
        return 5.0

    episode_text = str(episode_text)
    score = 5.2

    text_length = len(episode_text)
    if text_length > 250:
        score += 1.5
    elif text_length > 180:
        score += 1.0
    elif text_length > 120:
        score += 0.5

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
    ]
    story_count = sum(1 for elem in story_elements if elem in episode_text)
    score += min(story_count * 0.3, 1.5)

    has_quotes = "「" in episode_text or "」" in episode_text
    if has_quotes:
        score += 0.5

    return min(max(score, 1.0), 10.0)


def calculate_factual_density(episode_text: str, episode_type: str) -> float:
    """事実密度スコアを算出（1-10点）"""
    if pd.isna(episode_text) or not episode_text:
        return 5.0

    episode_text = str(episode_text)
    score = 5.0

    # 数値の存在（年、人数、金額など）
    numbers = re.findall(r"\d+", episode_text)
    if len(numbers) >= 3:
        score += 1.5
    elif len(numbers) >= 1:
        score += 0.8

    # 固有名詞（「」で囲まれた言葉、作品名など）
    proper_nouns = re.findall(r"「[^」]+」", episode_text)
    score += min(len(proper_nouns) * 0.3, 1.5)

    # 年月日表現
    date_patterns = re.findall(r"\d{4}年|\d+月\d+日|\d+歳", episode_text)
    score += min(len(date_patterns) * 0.4, 1.2)

    # 具体的な場所
    place_keywords = ["大学", "高校", "会社", "東京", "アメリカ", "映画", "作品", "本"]
    place_count = sum(1 for kw in place_keywords if kw in episode_text)
    score += min(place_count * 0.2, 1.0)

    return min(max(score, 1.0), 10.0)


def calculate_educational_value(episode_text: str, episode_type: str) -> float:
    """教育的価値スコアを算出（1-10点）"""
    if pd.isna(episode_text) or not episode_text:
        return 5.0

    episode_text = str(episode_text)
    score = 5.0

    # 教訓・学びの要素
    educational_keywords = [
        "学ん",
        "教訓",
        "気づ",
        "理解",
        "発見",
        "重要",
        "大切",
        "努力",
        "忍耐",
        "継続",
        "挑戦",
        "失敗",
        "成功",
        "経験",
        "知識",
        "技術",
        "スキル",
        "能力",
        "成長",
        "発展",
    ]
    edu_count = sum(1 for kw in educational_keywords if kw in episode_text)
    score += min(edu_count * 0.4, 2.0)

    # 歴史的・社会的意義
    significance_keywords = [
        "歴史",
        "初めて",
        "世界",
        "革命",
        "発明",
        "創造",
        "新しい",
        "記録",
        "達成",
        "貢献",
        "影響",
        "変革",
        "時代",
    ]
    sig_count = sum(1 for kw in significance_keywords if kw in episode_text)
    score += min(sig_count * 0.5, 2.0)

    # エピソードタイプによる調整
    episode_type = str(episode_type) if episode_type else ""
    if "ACHIEVEMENT" in episode_type.upper():
        score += 0.5
    if "TURNING_POINT" in episode_type.upper():
        score += 0.3

    return min(max(score, 1.0), 10.0)


# ====== fame_score推定ロジック ======

FAMOUS_PERSON_SCORES = {
    "スティーブ・ジョブズ": 9.5,
    "ウォルト・ディズニー": 9.5,
    "トーマス・エジソン": 9.5,
    "アルベルト・アインシュタイン": 9.8,
    "マイケル・ジャクソン": 9.5,
    "ビートルズ": 9.5,
    "ビル・ゲイツ": 9.3,
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
}

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


def estimate_fame_score(person_name: str, category: str, person_type: str = None) -> float:
    """人物の有名度スコアを推定"""
    if pd.isna(person_name):
        return 6.0

    person_name = str(person_name)

    # 手動定義されている有名人
    if person_name in FAMOUS_PERSON_SCORES:
        return FAMOUS_PERSON_SCORES[person_name]

    # カテゴリ別デフォルト値
    category = str(category) if pd.notna(category) else "その他"
    base_score = CATEGORY_DEFAULT_FAME.get(category, 6.0)

    # 架空キャラクターは少し低めに
    if person_type and "FICTIONAL" in str(person_type).upper():
        base_score -= 0.5

    return base_score


def calculate_episode_fame_score(episode_text: str, person_name: str, category: str) -> float:
    """エピソードの有名度スコアを算出"""
    if pd.isna(episode_text) or not episode_text:
        return 5.0

    episode_text = str(episode_text)
    base_score = 5.0

    # 歴史的重要性
    historical_keywords = [
        "初めて",
        "世界記録",
        "史上",
        "歴史的",
        "革命",
        "発明",
        "オリンピック",
        "ノーベル賞",
        "アカデミー賞",
        "受賞",
        "金メダル",
        "記録更新",
        "達成",
        "偉業",
        "伝説",
    ]
    hist_count = sum(1 for kw in historical_keywords if kw in episode_text)
    base_score += min(hist_count * 0.8, 3.0)

    # 社会的影響
    impact_keywords = [
        "影響",
        "貢献",
        "変革",
        "社会",
        "世界",
        "国際",
        "文化",
        "時代",
        "革新",
        "先駆者",
    ]
    impact_count = sum(1 for kw in impact_keywords if kw in episode_text)
    base_score += min(impact_count * 0.5, 2.0)

    return min(max(base_score, 1.0), 10.0)


def fill_all_missing_scores():
    """全欠損スコアを補完"""
    print("=" * 60)
    print("📊 全欠損スコア一括補完")
    print("=" * 60)

    # CSV読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    total = len(df)
    print(f"総レコード数: {total}")
    print()

    # 補完カウンター
    counts = {
        "教育的価値": 0,
        "ストーリー品質": 0,
        "事実密度": 0,
        "fame_score": 0,
        "episode_fame_score": 0,
    }

    # 1. 教育的価値の補完
    print("【1】教育的価値の補完...")
    mask = df["教育的価値"].isna()
    for idx in df[mask].index:
        text = df.loc[idx, "episode_text"]
        ep_type = df.loc[idx, "episode_type"]
        df.loc[idx, "教育的価値"] = calculate_educational_value(text, ep_type)
        counts["教育的価値"] += 1
    print(f"  → {counts['教育的価値']}件補完")

    # 2. ストーリー品質の補完
    print("【2】ストーリー品質の補完...")
    mask = df["ストーリー品質"].isna()
    for idx in df[mask].index:
        text = df.loc[idx, "episode_text"]
        ep_type = df.loc[idx, "episode_type"]
        df.loc[idx, "ストーリー品質"] = calculate_storytelling_quality(text, ep_type)
        counts["ストーリー品質"] += 1
    print(f"  → {counts['ストーリー品質']}件補完")

    # 3. 事実密度の補完
    print("【3】事実密度の補完...")
    mask = df["事実密度"].isna()
    for idx in df[mask].index:
        text = df.loc[idx, "episode_text"]
        ep_type = df.loc[idx, "episode_type"]
        df.loc[idx, "事実密度"] = calculate_factual_density(text, ep_type)
        counts["事実密度"] += 1
    print(f"  → {counts['事実密度']}件補完")

    # 4. fame_scoreの補完
    print("【4】fame_scoreの補完...")
    mask = df["fame_score"].isna()
    for idx in df[mask].index:
        name = df.loc[idx, "person_name"]
        cat = df.loc[idx, "category"]
        p_type = df.loc[idx, "person_type"] if "person_type" in df.columns else None
        df.loc[idx, "fame_score"] = estimate_fame_score(name, cat, p_type)
        counts["fame_score"] += 1
    print(f"  → {counts['fame_score']}件補完")

    # 5. episode_fame_scoreの補完
    print("【5】episode_fame_scoreの補完...")
    mask = df["episode_fame_score"].isna()
    for idx in df[mask].index:
        text = df.loc[idx, "episode_text"]
        name = df.loc[idx, "person_name"]
        cat = df.loc[idx, "category"]
        df.loc[idx, "episode_fame_score"] = calculate_episode_fame_score(text, name, cat)
        counts["episode_fame_score"] += 1
    print(f"  → {counts['episode_fame_score']}件補完")

    # 保存
    print()
    print("💾 CSVファイルを保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    # サマリー
    print()
    print("=" * 60)
    print("✅ 補完完了サマリー")
    print("=" * 60)
    for field, count in counts.items():
        print(f"  {field}: {count}件")
    print(f"  合計: {sum(counts.values())}件")
    print()

    # 残存欠損チェック
    print("【残存欠損チェック】")
    for col in ["教育的価値", "ストーリー品質", "事実密度", "fame_score", "episode_fame_score"]:
        remaining = df[col].isna().sum()
        print(f"  {col}: {remaining}件")


if __name__ == "__main__":
    fill_all_missing_scores()
