#!/usr/bin/env python3
"""
埋め草（フィラー）エピソード検出モジュール

具体性に欠ける一般論的なエピソードを検出する共通ロジック。
生成時のブロック、既存データのスキャン、品質監視で使用。

判定基準:
- 具体性スコア <= 1 (年/数値/作品名/イベントキーワードが1つ以下)
- 抽象フレーズ >= 2 (「後進の育成」「情熱を注」等が2つ以上)

使用例:
    from scripts.validation.filler_detector import is_filler, FillerAnalysis

    # 単純な判定
    if is_filler(episode_text):
        print("埋め草です")

    # 詳細分析
    analysis = FillerAnalysis(episode_text)
    print(f"具体性: {analysis.specificity_score}")
    print(f"抽象度: {analysis.filler_count}")
    print(f"埋め草: {analysis.is_filler}")
"""

import re
from dataclasses import dataclass
from typing import List

# 抽象フレーズリスト（埋め草の兆候）
FILLER_PHRASES = [
    # 育成・継承系
    "後進の育成",
    "次世代の育成",
    "次世代に伝え",
    "若手選手",
    "助言者として",
    # 情熱・貢献系
    "情熱を注",
    "社会に貢献",
    "還元する",
    "経験を活かし",
    "業界の発展",
    "野球界への貢献",
    "功績を残",
    # 継続系（具体的イベントなしに活動継続を示唆）
    "続けていました",
    "行っていました",
    "取り組んでいました",
    "貫いていました",
    "活動を続けて",
    "挑戦を続けて",
    "精力的に活動",
    "第一線で活躍",
    "創作活動を行",
    # 状態描写（具体性なし）
    "円熟期",
    "円熟の",
    "境地にあり",
    "生涯現役",
    "なお現役",
    # 抽象的姿勢
    "姿勢を",
    "信念を",
    "ペースで",
    "体現し",
    "示していました",
    "教えてくれます",
    # 役職・地位（エピソードとして薄い）
    "球団経営",
    "取締役会長",
]

# 捏造パターン（架空の出来事を示唆）- 高temperatureで生成された創作
FABRICATION_PATTERNS = [
    "養蜂業",
    "農業を始め",
    "突然現役引退",
    "周囲の猛反対を押し切",
    "衝撃的な告白",
    "過疎地域で",
    "限界集落",
]

# LLM拒否メッセージパターン
REFUSAL_PATTERNS = [
    "記述することはできません",
    "生成することはできません",
    "お伝えすることはできません",
    "作成することができません",
    "申し訳ございません",
    "という年齢には到達しておりません",
    "姿を見ることはできませんでした",
    "想像するならば",
    "もし〜まで生きていたならば",
    "歳で生涯を閉じたため",
    "歳で亡くなったため",
    "歳でこの世を去ったため",
]

# 具体性を示すパターン
SPECIFICITY_PATTERNS = {
    "year": r"(19|20)\d{2}年",  # 西暦年
    "number": r"\d+[本回度件位番勝敗万億個年日月%]",  # 数値記録
    "work_title": r"『[^』]+』",  # 作品名
    "event": r"(受賞|優勝|達成|記録|就任|引退|完成|公開|発表|死去|誕生|デビュー|発売|創設|設立|開催)",
}


@dataclass
class FillerAnalysis:
    """埋め草分析結果"""

    text: str
    specificity_score: int  # 0-4
    filler_count: int  # 抽象フレーズの出現数
    is_filler: bool  # 埋め草判定
    matched_filler_phrases: List[str]  # マッチした抽象フレーズ
    matched_specificity: List[str]  # マッチした具体性要素

    def __init__(self, text: str):
        self.text = text
        self.specificity_score = calc_specificity_score(text)
        self.filler_count = count_filler_phrases(text)
        self.matched_filler_phrases = get_matched_filler_phrases(text)
        self.matched_specificity = get_matched_specificity(text)
        self.is_filler = self.specificity_score <= 1 and self.filler_count >= 2


def calc_specificity_score(text: str) -> int:
    """
    具体性スコアを算出（0-4）

    スコア要素:
    - 西暦年の記載 (19xx年/20xx年)
    - 数値記録 (〇本/〇回/〇度等)
    - 作品名 (『〇〇』)
    - イベントキーワード (受賞/優勝/達成/記録等)

    Args:
        text: エピソード本文

    Returns:
        0-4のスコア（4が最も具体的）
    """
    if not text:
        return 0

    score = 0
    for pattern in SPECIFICITY_PATTERNS.values():
        if re.search(pattern, text):
            score += 1
    return score


def count_filler_phrases(text: str) -> int:
    """
    抽象フレーズの出現数をカウント

    Args:
        text: エピソード本文

    Returns:
        抽象フレーズの出現数
    """
    if not text:
        return 0
    return sum(1 for phrase in FILLER_PHRASES if phrase in text)


def get_matched_filler_phrases(text: str) -> List[str]:
    """
    マッチした抽象フレーズを取得

    Args:
        text: エピソード本文

    Returns:
        マッチしたフレーズのリスト
    """
    if not text:
        return []
    return [phrase for phrase in FILLER_PHRASES if phrase in text]


def get_matched_specificity(text: str) -> List[str]:
    """
    マッチした具体性要素を取得

    Args:
        text: エピソード本文

    Returns:
        マッチした具体性要素のリスト（例: ["year", "number"]）
    """
    if not text:
        return []
    return [name for name, pattern in SPECIFICITY_PATTERNS.items() if re.search(pattern, text)]


def count_fabrication_patterns(text: str) -> int:
    """捏造パターンの出現数をカウント"""
    if not text:
        return 0
    return sum(1 for pattern in FABRICATION_PATTERNS if pattern in text)


def is_refusal_message(text: str) -> bool:
    """
    LLM拒否メッセージかどうかを判定

    Args:
        text: エピソード本文

    Returns:
        True: 拒否メッセージ, False: 正常なエピソード
    """
    if not text:
        return False

    # 文頭チェック（申し訳〜で始まる場合は即アウト）
    if text.strip().startswith("申し訳"):
        return True

    # 拒否パターンをチェック
    for pattern in REFUSAL_PATTERNS:
        if pattern in text:
            return True

    return False


def is_filler(text: str) -> bool:
    """
    埋め草エピソードかどうかを判定

    判定基準:
    1. LLM拒否メッセージである（即アウト）
    2. 捏造パターンが含まれている（即アウト）
    3. または、具体性スコア == 0 かつ 抽象フレーズ >= 2
       ※ spec=1（年/数値/作品名/イベントのいずれか1つあり）は埋め草としない

    Args:
        text: エピソード本文

    Returns:
        True: 埋め草, False: 埋め草ではない
    """
    if not text:
        return False

    # 拒否メッセージは即アウト
    if is_refusal_message(text):
        return True

    # 捏造パターンは即アウト
    if count_fabrication_patterns(text) > 0:
        return True

    specificity = calc_specificity_score(text)
    filler_count = count_filler_phrases(text)
    # 具体性が0（年/数値/作品名/イベントなし）かつ抽象フレーズ多数の場合のみ埋め草
    return specificity == 0 and filler_count >= 2


def check_episode_limit(person_episodes_count: int, limit: int = 5) -> bool:
    """
    エピソード数制限をチェック

    Args:
        person_episodes_count: 現在のエピソード数
        limit: 制限数（デフォルト5）

    Returns:
        True: 制限内, False: 制限超過
    """
    return person_episodes_count < limit


# テスト用
if __name__ == "__main__":
    # テストケース
    test_cases = [
        # 埋め草の例
        (
            "55歳のとき、王貞治は球団経営に携わりながら後進の育成に情熱を注いでいた。"
            "若手選手の指導に力を入れ、次世代に伝えることに尽力した。",
            True,
        ),
        # 具体的なエピソード
        (
            "37歳のとき、王貞治は1977年シーズンに756号本塁打を達成し、"
            "ハンク・アーロンの記録を抜いて世界新記録を樹立した。",
            False,
        ),
        # 境界ケース（具体性あり + 抽象フレーズ1つ）
        (
            "40歳のとき、1980年に引退を発表。後進の育成に転じた。",
            False,
        ),
    ]

    print("=== 埋め草判定テスト ===\n")
    for text, expected in test_cases:
        analysis = FillerAnalysis(text)
        result = "✅" if analysis.is_filler == expected else "❌"
        print(f"{result} 期待: {expected}, 結果: {analysis.is_filler}")
        print(f"   具体性: {analysis.specificity_score}, 抽象度: {analysis.filler_count}")
        print(f"   具体性要素: {analysis.matched_specificity}")
        print(f"   抽象フレーズ: {analysis.matched_filler_phrases}")
        print(f"   テキスト: {text[:50]}...")
        print()
