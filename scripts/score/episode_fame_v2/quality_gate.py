"""
品質ゲート（QualityGate）

低品質エピソードを検出し、減点または除外する
"""

import re
from typing import Optional

from .config import QUALITY_GATE, QUALITY_LLM_WEIGHTS


def check_specificity(text: str) -> dict:
    """
    具体性チェック（固有名詞・数値表現の有無）

    Args:
        text: エピソード本文

    Returns:
        {
            "pass": bool,
            "proper_noun_count": int,
            "number_count": int,
            "penalty": float (0-1, 1=ペナルティなし)
        }
    """
    if not text:
        return {
            "pass": False,
            "proper_noun_count": 0,
            "number_count": 0,
            "penalty": QUALITY_GATE["no_specificity_penalty"],
        }

    # 固有名詞パターン（カタカナ連続、漢字固有名詞など）
    katakana_pattern = r"[ァ-ヴー]{3,}"  # 3文字以上のカタカナ
    year_pattern = r"\d{4}年"
    age_pattern = r"\d{1,3}歳"
    number_pattern = r"\d+[万億兆]?[円ドル]?"

    proper_nouns = len(re.findall(katakana_pattern, text))
    years = len(re.findall(year_pattern, text))
    ages = len(re.findall(age_pattern, text))
    numbers = len(re.findall(number_pattern, text))

    # 年・年齢は除外した数値カウント
    pure_numbers = numbers - years - ages

    total_proper_nouns = proper_nouns
    total_numbers = pure_numbers + years  # 年は数値としてカウント

    min_proper_nouns = QUALITY_GATE["min_proper_nouns"]
    min_numbers = QUALITY_GATE["min_numbers"]

    is_pass = total_proper_nouns >= min_proper_nouns

    # ペナルティ計算
    if not is_pass and total_proper_nouns < min_proper_nouns:
        penalty = QUALITY_GATE["no_specificity_penalty"]
    else:
        penalty = 1.0

    return {
        "pass": is_pass,
        "proper_noun_count": total_proper_nouns,
        "number_count": total_numbers,
        "penalty": penalty,
    }


def check_meta_expressions(text: str) -> dict:
    """
    メタ表現チェック（「あなたと同じ～歳」など）

    Args:
        text: エピソード本文

    Returns:
        {
            "has_meta": bool,
            "matched_patterns": list,
            "penalty": float (0-1, 1=ペナルティなし)
        }
    """
    if not text:
        return {
            "has_meta": False,
            "matched_patterns": [],
            "penalty": 1.0,
        }

    matched = []
    for pattern in QUALITY_GATE["meta_patterns"]:
        matches = re.findall(pattern, text)
        if matches:
            matched.extend(matches)

    has_meta = len(matched) > 0
    penalty = 1.0 - QUALITY_GATE["meta_penalty"] if has_meta else 1.0

    return {
        "has_meta": has_meta,
        "matched_patterns": matched,
        "penalty": penalty,
    }


def check_age_contradiction(
    text: str,
    episode_age: Optional[int] = None,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
) -> dict:
    """
    年齢/年矛盾チェック

    Args:
        text: エピソード本文
        episode_age: エピソードの年齢
        birth_year: 誕生年
        death_year: 死亡年（存命なら None）

    Returns:
        {
            "has_contradiction": bool,
            "details": str,
            "exclude": bool
        }
    """
    # 基本チェック（詳細なロジックは別モジュールに委譲）
    has_contradiction = False
    details = ""

    if episode_age is not None:
        if episode_age < 0 or episode_age > 130:
            has_contradiction = True
            details = f"Invalid age: {episode_age}"

        if death_year and birth_year:
            max_age = death_year - birth_year
            if episode_age > max_age:
                has_contradiction = True
                details = f"Age {episode_age} exceeds lifespan ({max_age})"

    exclude = has_contradiction and QUALITY_GATE["age_contradiction_exclude"]

    return {
        "has_contradiction": has_contradiction,
        "details": details,
        "exclude": exclude,
    }


def calculate_quality_score(
    llm_scores: dict,
    text: str,
    episode_age: Optional[int] = None,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
) -> dict:
    """
    品質スコアを計算（LLM 7軸ベース + 品質ゲート適用）

    Args:
        llm_scores: LLM 7軸スコア dict
        text: エピソード本文
        episode_age: エピソードの年齢
        birth_year: 誕生年
        death_year: 死亡年

    Returns:
        {
            "total": 0-100のスコア,
            "raw_score": ペナルティ前のスコア,
            "penalty_factor": 適用されたペナルティ係数,
            "exclude": 除外フラグ,
            "gates": {各ゲートの結果}
        }
    """
    # LLM重み付けスコア計算
    raw_score = 0.0
    for key, weight in QUALITY_LLM_WEIGHTS.items():
        score = llm_scores.get(key, 0) or 0
        raw_score += score * weight

    # 0-10スケールを0-100にスケール
    raw_score = raw_score * 10

    # 品質ゲートチェック
    specificity = check_specificity(text)
    meta = check_meta_expressions(text)
    age = check_age_contradiction(text, episode_age, birth_year, death_year)

    # ペナルティ計算
    penalty_factor = specificity["penalty"] * meta["penalty"]

    # 除外判定
    exclude = age["exclude"]

    # 最終スコア
    final_score = raw_score * penalty_factor if not exclude else 0.0

    return {
        "total": round(final_score, 2),
        "raw_score": round(raw_score, 2),
        "penalty_factor": round(penalty_factor, 2),
        "exclude": exclude,
        "gates": {
            "specificity": specificity,
            "meta": meta,
            "age": age,
        },
    }


def apply_quality_gate(episodes: list) -> list:
    """
    エピソードリストに品質ゲートを適用し、除外フラグを設定

    Args:
        episodes: エピソードのリスト（dict形式）

    Returns:
        除外フラグ付きのエピソードリスト
    """
    result = []
    for ep in episodes:
        text = ep.get("episode_content", "") or ""
        llm_scores = {
            "memorability": ep.get("memorability", 0),
            "storytelling_quality": ep.get("storytelling_quality", 0),
            "factual_density": ep.get("factual_density", 0),
            "educational_value": ep.get("educational_value", 0),
            "empathy": ep.get("empathy", 0),
        }

        quality = calculate_quality_score(
            llm_scores=llm_scores,
            text=text,
            episode_age=ep.get("age"),
            birth_year=ep.get("birth_year"),
            death_year=ep.get("death_year"),
        )

        ep["quality_score"] = quality["total"]
        ep["quality_exclude"] = quality["exclude"]
        ep["quality_penalty"] = quality["penalty_factor"]
        ep["quality_gates"] = quality["gates"]

        result.append(ep)

    return result
