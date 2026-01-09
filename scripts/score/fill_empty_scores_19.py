#!/usr/bin/env python3
"""19件の空スコアエピソードを補完するスクリプト

7軸スコア（記憶性・共感性・意外性・生成品質・educational_value・story_quality・factual_density）と
5軸スコア（総合品質・感情インパクト・composite_score_5axis）を補完する。

LLMを使わず、テキスト分析ベースで高速に処理。
"""

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"


# ====== 7軸スコア算出ロジック（テキスト分析ベース） ======


def calculate_memorability(text: str) -> float:
    """memorability_score: 印象的なキーワード、具体的エピソード"""
    if not text:
        return 6.0
    score = 6.0

    # 印象的なキーワード
    memorable_words = [
        "初めて",
        "史上",
        "歴史",
        "最年少",
        "最高",
        "伝説",
        "偉業",
        "革命",
        "衝撃",
        "記録",
        "達成",
        "快挙",
        "前人未到",
        "金メダル",
        "世界一",
    ]
    count = sum(1 for w in memorable_words if w in text)
    score += min(count * 0.5, 2.0)

    # 数値の存在（具体性）
    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 3:
        score += 0.5

    return min(max(score, 6.0), 9.0)


def calculate_empathy(text: str) -> float:
    """empathy_score: 感情的キーワード、人間味"""
    if not text:
        return 5.5
    score = 5.5

    emotion_words = [
        "感動",
        "涙",
        "喜び",
        "悲しみ",
        "苦悩",
        "葛藤",
        "希望",
        "夢",
        "愛",
        "絆",
        "家族",
        "友情",
        "勇気",
        "決意",
        "覚悟",
        "情熱",
        "挫折",
        "再起",
    ]
    count = sum(1 for w in emotion_words if w in text)
    score += min(count * 0.4, 2.0)

    # 引用やセリフ
    if "「" in text:
        score += 0.3

    return min(max(score, 5.0), 9.0)


def calculate_surprise(text: str) -> float:
    """surprise_score: 逆転・予想外の展開"""
    if not text:
        return 5.5
    score = 5.5

    surprise_words = [
        "驚き",
        "意外",
        "予想外",
        "逆転",
        "まさか",
        "突然",
        "急",
        "衝撃",
        "奇跡",
        "転機",
        "一変",
        "急展開",
        "番狂わせ",
    ]
    count = sum(1 for w in surprise_words if w in text)
    score += min(count * 0.5, 2.0)

    return min(max(score, 5.0), 8.5)


def calculate_generation_quality(text: str) -> float:
    """generation_quality_score: 文章の長さ・構成"""
    if not text:
        return 7.0
    score = 7.0

    # 文章の長さ
    text_len = len(text)
    if text_len >= 200:
        score += 1.0
    elif text_len >= 150:
        score += 0.5

    # 文の完成度（句点の数）
    sentence_count = text.count("。")
    if sentence_count >= 3:
        score += 0.5

    return min(max(score, 7.0), 9.0)


def calculate_educational_value(text: str) -> float:
    """educational_value: 学びのキーワード"""
    if not text:
        return 5.5
    score = 5.5

    edu_words = [
        "学",
        "教訓",
        "努力",
        "成長",
        "挑戦",
        "克服",
        "知識",
        "技術",
        "経験",
        "発見",
        "革新",
        "貢献",
        "影響",
        "歴史",
    ]
    count = sum(1 for w in edu_words if w in text)
    score += min(count * 0.3, 1.5)

    # 歴史的・社会的意義
    if any(w in text for w in ["初めて", "世界", "記録", "達成"]):
        score += 0.5

    return min(max(score, 5.0), 8.5)


def calculate_storytelling(text: str) -> float:
    """story_quality: 物語性"""
    if not text:
        return 6.5
    score = 6.5

    # 文章の長さ
    if len(text) >= 200:
        score += 0.5

    # 物語要素
    story_elements = [
        "夢",
        "目標",
        "挑戦",
        "困難",
        "克服",
        "達成",
        "転機",
        "出発",
        "変化",
        "成長",
    ]
    count = sum(1 for elem in story_elements if elem in text)
    score += min(count * 0.3, 1.5)

    return min(max(score, 6.0), 8.5)


def calculate_factual_density(text: str) -> float:
    """factual_density: 具体的情報の密度"""
    if not text:
        return 8.0
    score = 8.0

    # 数値
    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 4:
        score += 1.5
    elif len(numbers) >= 2:
        score += 0.8

    # 年号
    years = re.findall(r"\d{4}年", text)
    if years:
        score += 0.5

    return min(max(score, 8.0), 10.0)


def fill_empty_scores():
    """空スコアエピソードを補完"""
    print("=" * 60)
    print("📊 19件空スコアエピソード補完スクリプト")
    print("=" * 60)
    print()

    # CSV読み込み
    rows = []
    fieldnames = None
    empty_episodes = []

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            # 空スコア判定
            if not row.get("memorability_score", "").strip():
                empty_episodes.append(row)
            rows.append(row)

    print(f"総エピソード数: {len(rows):,}")
    print(f"空スコアエピソード: {len(empty_episodes)}件")
    print()

    if not empty_episodes:
        print("✅ 補完対象なし")
        return

    # スコア補完
    print("📝 スコア補完中...")
    updated_count = 0

    for row in rows:
        if not row.get("memorability_score", "").strip():
            text = row.get("episode_text", "")
            ep_id = row["episode_id"]
            person = row["person_name"]

            # 7軸スコア算出
            memorability = calculate_memorability(text)
            empathy = calculate_empathy(text)
            surprise = calculate_surprise(text)
            gen_quality = calculate_generation_quality(text)
            edu_value = calculate_educational_value(text)
            storytelling = calculate_storytelling(text)
            factual = calculate_factual_density(text)

            # 5軸スコア算出
            overall_quality = (memorability + gen_quality) / 2
            emotional_impact = (empathy + surprise) / 2
            composite_5axis = (overall_quality + emotional_impact + edu_value + storytelling + factual) / 5

            # 更新
            row["memorability_score"] = f"{memorability:.1f}"
            row["empathy_score"] = f"{empathy:.1f}"
            row["surprise_score"] = f"{surprise:.1f}"
            row["generation_quality_score"] = f"{gen_quality:.1f}"
            row["educational_value"] = f"{edu_value:.1f}"
            row["story_quality"] = f"{storytelling:.1f}"
            row["factual_density"] = f"{factual:.1f}"
            row["総合品質"] = f"{overall_quality:.2f}"
            row["感情インパクト"] = f"{emotional_impact:.2f}"
            row["composite_score_5axis"] = f"{composite_5axis:.2f}"
            row["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(
                f"  ✅ {ep_id}: {person} - 記憶{memorability:.1f} 共感{empathy:.1f} 意外{surprise:.1f} 品質{gen_quality:.1f} 教育{edu_value:.1f} 物語{storytelling:.1f} 事実{factual:.1f}"
            )
            print(f"     → 総合品質{overall_quality:.2f} 感情{emotional_impact:.2f} 5axis{composite_5axis:.2f}")
            updated_count += 1

    print()

    # 保存
    print("💾 CSVファイル保存中...")
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # サマリー
    print("=" * 60)
    print("✅ 補完完了")
    print("=" * 60)
    print(f"  補完件数: {updated_count}件")
    print()


if __name__ == "__main__":
    fill_empty_scores()
