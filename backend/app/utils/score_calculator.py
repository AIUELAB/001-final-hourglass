"""スコア計算の統一モジュール

composite_scoreや各種評価スコアの計算を一元管理
"""

import re
import unicodedata
from typing import Dict, List, Optional, Union

# 7軸スコアのフィールド名（日本語）
SEVEN_AXIS_FIELDS = [
    "memorability_score",  # memorability_score
    "empathy_score",  # empathy_score
    "surprise_score",  # surprise_score
    "generation_quality_score",  # generation_quality_score
    "educational_value",  # educational_value
    "story_quality",  # storytelling_quality
    "factual_density",  # factual_density
]

# 5軸スコアのフィールド名（統合版）
# Phase 3: 7軸から5軸への構造改革
FIVE_AXIS_FIELDS = [
    "総合品質",  # overall_quality: 記憶性 + 生成品質
    "感情インパクト",  # emotional_impact: 共感性 + 意外性
    "educational_value",  # educational_value (維持)
    "story_quality",  # storytelling_quality (維持)
    "factual_density",  # factual_density (維持)
]

# 5軸の計算定義
FIVE_AXIS_COMPOSITION = {
    "総合品質": {
        "sources": ["memorability_score", "generation_quality_score"],
        "weights": [0.5, 0.5],
        "description": "記憶に残る品質の高いエピソード",
    },
    "感情インパクト": {
        "sources": ["empathy_score", "surprise_score"],
        "weights": [0.5, 0.5],
        "description": "共感と驚きによる感情的響き",
    },
    "educational_value": {
        "sources": ["educational_value"],
        "weights": [1.0],
        "description": "学びと教訓の価値",
    },
    "story_quality": {
        "sources": ["story_quality"],
        "weights": [1.0],
        "description": "物語としての構成力",
    },
    "factual_density": {
        "sources": ["factual_density"],
        "weights": [1.0],
        "description": "具体的事実の密度",
    },
}

# 英語→日本語のマッピング
FIELD_MAPPING = {
    "memorability_score": "memorability_score",
    "empathy_score": "empathy_score",
    "surprise_score": "surprise_score",
    "generation_quality_score": "generation_quality_score",
    "educational_value": "educational_value",
    "storytelling_quality": "story_quality",
    "factual_density": "factual_density",
}


def calculate_composite_score(episode_data: Dict, min_axes_required: int = 1) -> Optional[float]:
    """
    7軸スコアの平均からcomposite_scoreを算出

    Args:
        episode_data: エピソードデータ（Dict）
        min_axes_required: 計算に必要な最低軸数（デフォルト: 1）

    Returns:
        composite_score（0-10スケール）、計算不可の場合はNone

    Note:
        - 有効なスコア（0-10の範囲）のみを使用
        - 空文字、None、範囲外の値は除外
        - 必要最低軸数に満たない場合はNoneを返す
    """
    scores = []

    for field in SEVEN_AXIS_FIELDS:
        value = episode_data.get(field)

        # 値の取得と検証
        if value is None or value == "":
            continue

        try:
            score = float(value)
            # 範囲チェック（0-10）
            if 0 <= score <= 10:
                scores.append(score)
        except (ValueError, TypeError):
            continue

    # 最低軸数チェック
    if len(scores) < min_axes_required:
        return None

    # 平均値を計算
    if scores:
        return round(sum(scores) / len(scores), 2)

    return None


def calculate_composite_score_from_english_fields(episode_data: Dict, min_axes_required: int = 1) -> Optional[float]:
    """
    英語フィールド名からcomposite_scoreを算出

    Args:
        episode_data: エピソードデータ（英語フィールド名を含むDict）
        min_axes_required: 計算に必要な最低軸数

    Returns:
        composite_score（0-10スケール）
    """
    # 日本語フィールド名に変換
    converted = {}
    for eng_name, jp_name in FIELD_MAPPING.items():
        if eng_name in episode_data:
            converted[jp_name] = episode_data[eng_name]

    # 日本語フィールドも含める
    for jp_name in SEVEN_AXIS_FIELDS:
        if jp_name in episode_data and jp_name not in converted:
            converted[jp_name] = episode_data[jp_name]

    return calculate_composite_score(converted, min_axes_required)


def get_score_breakdown(episode_data: Dict) -> Dict[str, Optional[float]]:
    """
    7軸スコアの内訳を取得

    Args:
        episode_data: エピソードデータ

    Returns:
        各軸のスコア（Noneまたは数値）
    """
    breakdown = {}

    for field in SEVEN_AXIS_FIELDS:
        value = episode_data.get(field)

        if value is None or value == "":
            breakdown[field] = None
            continue

        try:
            score = float(value)
            breakdown[field] = score if 0 <= score <= 10 else None
        except (ValueError, TypeError):
            breakdown[field] = None

    return breakdown


def count_valid_axes(episode_data: Dict) -> int:
    """
    有効な軸数をカウント

    Args:
        episode_data: エピソードデータ

    Returns:
        有効なスコアを持つ軸の数（0-7）
    """
    breakdown = get_score_breakdown(episode_data)
    return sum(1 for v in breakdown.values() if v is not None)


def normalize_person_name(name: str) -> str:
    """
    人物名を正規化（重複検出用）

    Args:
        name: 元の人物名

    Returns:
        正規化された人物名

    処理内容:
        - 前後の空白除去
        - 全角/半角スペースの除去
        - Unicode正規化（NFKC）
        - 括弧内の情報除去（オプション）
    """
    if not name:
        return ""

    # Unicode正規化（全角→半角など）
    normalized = unicodedata.normalize("NFKC", name)

    # 空白除去（全角・半角）
    normalized = normalized.replace(" ", "").replace("　", "")

    # 前後の空白除去
    normalized = normalized.strip()

    return normalized


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    2つのテキストの類似度を計算

    Args:
        text1: テキスト1
        text2: テキスト2

    Returns:
        類似度（0.0-1.0）
    """
    from difflib import SequenceMatcher

    if not text1 or not text2:
        return 0.0

    # 前後の空白除去
    text1 = text1.strip()
    text2 = text2.strip()

    # 空の場合
    if not text1 or not text2:
        return 0.0

    return SequenceMatcher(None, text1, text2).ratio()


def is_similar_episode(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """
    2つのエピソードテキストが類似しているか判定

    Args:
        text1: エピソードテキスト1
        text2: エピソードテキスト2
        threshold: 類似度閾値（デフォルト: 0.8）

    Returns:
        類似している場合True
    """
    return calculate_text_similarity(text1, text2) > threshold


def calculate_episode_quality_indicators(episode_data: Dict) -> Dict:
    """
    エピソードの品質指標を計算

    Args:
        episode_data: エピソードデータ

    Returns:
        品質指標の辞書
    """
    episode_text = str(episode_data.get("episode_text", ""))

    # テキスト長
    char_count = len(episode_text)

    # 数値データの存在
    numbers = re.findall(r"\d+", episode_text)
    number_count = len(numbers)

    # 引用（「」）の存在
    has_quotes = "「" in episode_text and "」" in episode_text

    # 固有名詞（カタカナ3文字以上）
    katakana_pattern = r"[ァ-ヴー]{3,}"
    katakana_words = re.findall(katakana_pattern, episode_text)
    katakana_count = len(katakana_words)

    # composite_score
    composite = calculate_composite_score(episode_data)

    # 有効軸数
    valid_axes = count_valid_axes(episode_data)

    return {
        "char_count": char_count,
        "number_count": number_count,
        "has_quotes": has_quotes,
        "katakana_count": katakana_count,
        "composite_score": composite,
        "valid_axes_count": valid_axes,
        "is_complete": valid_axes == 7,
    }


def format_composite_score(score: Optional[float]) -> str:
    """
    composite_scoreをCSV保存用に文字列化

    Args:
        score: スコア値（Noneまたは数値）

    Returns:
        文字列（空文字または小数点以下2桁）
    """
    if score is None:
        return ""
    return f"{score:.2f}"


# ============================================================
# 5軸の改善されたルールベース計算関数
# ============================================================

# 記憶性に関連するキーワード
MEMORABILITY_KEYWORDS = {
    "ultra_high": ["世界初", "史上初", "ギネス", "国民的", "社会現象", "歴史的", "革命", "金字塔"],
    "high": ["記録", "受賞", "優勝", "達成", "発明", "発見", "創設", "開発", "成功"],
    "medium": ["挑戦", "転機", "決断", "出会い", "経験"],
}

# 共感性に関連するキーワード
EMPATHY_KEYWORDS = {
    "emotion": ["涙", "感動", "喜び", "悲しみ", "苦悩", "葛藤", "不安", "希望", "絶望", "勇気"],
    "struggle": ["克服", "乗り越え", "挫折", "失敗", "困難", "逆境", "苦労", "努力"],
    "relation": ["家族", "母", "父", "子供", "友人", "恩師", "仲間", "愛"],
}

# 意外性に関連するキーワード（拡張版）
SURPRISE_KEYWORDS = {
    "twist": [
        "実は",
        "意外にも",
        "驚くべきことに",
        "誰も知らない",
        "秘密",
        "真実",
        "知られざる",
        "隠された",
        "裏側",
        "本当は",
        "実際には",
        "明かされた",
    ],
    "contrast": [
        "一方で",
        "しかし",
        "逆に",
        "反面",
        "裏では",
        "ところが",
        "にもかかわらず",
        "それでも",
        "皮肉にも",
        "対照的に",
        "反して",
        "違って",
    ],
    "unexpected": [
        "偶然",
        "予想外",
        "思いがけず",
        "突然",
        "奇跡的",
        "異例",
        "破天荒",
        "型破り",
        "常識を覆す",
        "前例のない",
        "画期的",
        "革新的",
        "異色",
        "独自",
        "ユニーク",
        "唯一",
        "珍しい",
        "稀有",
        "特異",
    ],
    "achievement_twist": [
        "最年少",
        "最年長",
        "史上初",
        "女性初",
        "日本人初",
        "世界初",
        "前人未到",
        "不可能を可能に",
        "常識を破る",
        "逆転",
        "大逆転",
        "番狂わせ",
        "下剋上",
        "奇跡の",
        "ドラマチック",
    ],
    "origin_twist": [
        "元々",
        "当初",
        "最初は",
        "かつては",
        "以前は",
        "本来",
        "全く違う",
        "想像もしなかった",
        "夢にも思わなかった",
        "偶然の発見",
    ],
}

# educational_valueに関連するキーワード
EDUCATIONAL_KEYWORDS = {
    "lesson": ["教訓", "学び", "示唆", "重要", "原則", "哲学", "信念", "思想"],
    "insight": ["発見", "気づき", "理解", "認識", "視点", "考え方"],
    "universal": ["普遍的", "本質", "真理", "原理", "法則"],
}


# ============================================================
# 改善版キーワードカウント関数 v3
# - 否定形パターン除外
# - テキスト長正規化
# - 重複キーワード制限
# ============================================================

# 否定形パターン（キーワードの直後に来ると否定とみなす）
NEGATION_PATTERNS = [
    r"しな[いかけくっ]",  # しない、しなかった
    r"でき[なず]",  # できない、できず
    r"な[いかけくっ]",  # ない、なかった
    r"ず$",  # せず
    r"ずに",  # せずに
    r"なかっ",  # なかった
    r"ません",  # しません
]

# 結合した否定パターン
NEGATION_REGEX = re.compile(r"(" + "|".join(NEGATION_PATTERNS) + r")")


def count_keywords_v3(
    text: str,
    keywords: List[str],
    normalize_by_length: bool = True,
    base_length: int = 307,
    exclude_negation: bool = True,
) -> float:
    """改善版キーワードカウント関数

    Args:
        text: 検索対象テキスト
        keywords: キーワードリスト
        normalize_by_length: テキスト長で正規化するか
        base_length: 正規化の基準長（デフォルト307文字、実データ中央値）
        exclude_negation: 否定形を除外するか

    Returns:
        キーワードカウント（正規化後の浮動小数点数）

    改善点:
        1. 重複キーワードは1回のみカウント（set使用）
        2. 否定形パターンの除外（「成功しなかった」→カウントしない）
        3. テキスト長による正規化（長いテキストへのバイアス軽減）
    """
    if not text or not keywords:
        return 0.0

    # 重複を除いてマッチしたキーワードを収集
    matched_keywords = set()

    for kw in keywords:
        if kw in text:
            if exclude_negation:
                # キーワードの後の文字列を検査
                idx = text.find(kw)
                while idx != -1:
                    # キーワードの直後10文字を取得
                    after_kw = text[idx + len(kw) : idx + len(kw) + 10]
                    # 否定パターンで始まっていなければ有効
                    if not NEGATION_REGEX.match(after_kw):
                        matched_keywords.add(kw)
                        break
                    # 次のマッチを探す
                    idx = text.find(kw, idx + 1)
            else:
                matched_keywords.add(kw)

    count = len(matched_keywords)

    # テキスト長による正規化
    if normalize_by_length and len(text) > 0:
        normalization_factor = len(text) / base_length
        # 正規化係数が極端に小さい/大きい場合を制限
        normalization_factor = max(0.5, min(2.0, normalization_factor))
        count = count / normalization_factor

    return count


def count_keywords_simple(text: str, keywords: List[str]) -> int:
    """シンプルなキーワードカウント（重複制限のみ）

    後方互換性のため、正規化なし・否定形考慮なしのバージョン
    """
    if not text or not keywords:
        return 0
    return len(set(kw for kw in keywords if kw in text))


def calculate_memorability_score(episode_data: Dict) -> float:
    """
    memorability_scoreを計算（改善版v3）

    評価基準:
    - 歴史的重要度（キーワード検出）
    - 人物の知名度（fame_score）
    - エピソードタイプの記憶に残りやすさ
    - 具体的数値・年号の存在
    - ペナルティ要素追加

    改善点（v3）:
    - 否定形パターン除外
    - テキスト長正規化
    - 重複キーワード制限

    Args:
        episode_data: エピソードデータ

    Returns:
        memorability_score（1.0-10.0）
    """
    score = 3.5  # ベーススコア（下方修正）
    episode_text = str(episode_data.get("episode_text", ""))

    # 1. 超高インパクトキーワード (+3.0) - 改善版v3使用
    ultra_high_count = count_keywords_v3(episode_text, MEMORABILITY_KEYWORDS["ultra_high"], normalize_by_length=True)
    score += min(ultra_high_count * 1.5, 3.0)

    # 2. 高インパクトキーワード (+2.0) - 改善版v3使用
    high_count = count_keywords_v3(episode_text, MEMORABILITY_KEYWORDS["high"], normalize_by_length=True)
    score += min(high_count * 0.6, 2.0)

    # 3. 中インパクトキーワード (+1.0) - 改善版v3使用
    medium_count = count_keywords_v3(episode_text, MEMORABILITY_KEYWORDS["medium"], normalize_by_length=True)
    score += min(medium_count * 0.3, 1.0)

    # 4. fame_scoreからの補正 (+1.5)
    fame_score = episode_data.get("fame_score")
    if fame_score:
        try:
            fame = float(fame_score)
            if fame >= 80:
                score += 1.5
            elif fame >= 60:
                score += 1.0
            elif fame >= 40:
                score += 0.5
        except (ValueError, TypeError):
            pass

    # 5. エピソードタイプ補正 (+1.2)
    episode_type = episode_data.get("episode_type", "")
    memorable_types = ["ACHIEVEMENT", "INNOVATION", "TURNING_POINT", "FOUNDING"]
    if episode_type in memorable_types:
        score += 1.2

    # 6. 年号の存在 (+0.5)
    if re.search(r"(19|20)\d{2}年", episode_text):
        score += 0.5

    # 7. 具体的な数値データ (+0.5)
    numbers = re.findall(r"\d+", episode_text)
    if len(numbers) >= 3:
        score += 0.5

    # ペナルティ要素
    # 8. テキストが短すぎる (-1.0)
    if len(episode_text) < 100:
        score -= 1.0
    elif len(episode_text) < 150:
        score -= 0.5

    # 9. 曖昧な表現が多い (-0.5)
    vague_patterns = ["など", "ような", "といった", "かもしれない"]
    vague_count = sum(episode_text.count(p) for p in vague_patterns)
    if vague_count >= 3:
        score -= 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_empathy_score(episode_data: Dict) -> float:
    """
    empathy_scoreを計算（改善版v3）

    評価基準:
    - 感情表現の豊かさ
    - 人間的な葛藤・成長の描写
    - 関係性（家族、仲間）への言及
    - 普遍的な体験への関連
    - ペナルティ要素追加

    改善点（v3）:
    - 否定形パターン除外
    - テキスト長正規化
    - 重複キーワード制限

    Args:
        episode_data: エピソードデータ

    Returns:
        empathy_score（1.0-10.0）
    """
    score = 3.0  # ベーススコア（下方修正）
    episode_text = str(episode_data.get("episode_text", ""))

    # 1. 感情キーワード (+2.5) - 改善版v3使用
    emotion_count = count_keywords_v3(episode_text, EMPATHY_KEYWORDS["emotion"], normalize_by_length=True)
    score += min(emotion_count * 0.7, 2.5)

    # 2. 葛藤・克服キーワード (+2.0) - 改善版v3使用
    struggle_count = count_keywords_v3(episode_text, EMPATHY_KEYWORDS["struggle"], normalize_by_length=True)
    score += min(struggle_count * 0.6, 2.0)

    # 3. 関係性キーワード (+2.0) - 改善版v3使用
    relation_count = count_keywords_v3(episode_text, EMPATHY_KEYWORDS["relation"], normalize_by_length=True)
    score += min(relation_count * 0.6, 2.0)

    # 4. 引用（会話）の存在 (+1.0)
    quote_count = episode_text.count("「")
    if quote_count >= 2:
        score += 1.0
    elif quote_count >= 1:
        score += 0.5

    # 5. エピソードタイプ補正 (+1.5)
    episode_type = episode_data.get("episode_type", "")
    empathetic_types = ["FAMILY", "GROWTH", "FAILURE", "COMEBACK"]
    if episode_type in empathetic_types:
        score += 1.5
    elif episode_type in ["CHALLENGE", "TURNING_POINT"]:
        score += 0.8

    # 6. 一人称・二人称の使用 (+0.5)
    personal_pronouns = ["私", "僕", "俺", "自分", "あなた"]
    if any(p in episode_text for p in personal_pronouns):
        score += 0.5

    # ペナルティ要素
    # 7. 感情表現がない (-1.0)
    if emotion_count == 0 and struggle_count == 0:
        score -= 1.0

    # 8. 事実の羅列のみ (-0.5)
    fact_only_patterns = ["記録", "達成", "受賞", "獲得"]
    fact_count = sum(1 for p in fact_only_patterns if p in episode_text)
    if fact_count >= 3 and emotion_count == 0:
        score -= 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_surprise_score(episode_data: Dict) -> float:
    """
    surprise_scoreを計算（改善版v3）

    評価基準:
    - 意外な展開を示すキーワード
    - 対比・コントラストの存在
    - 予想外の要素
    - 達成・起源に関するツイスト
    - 年齢とエピソードタイプの組み合わせ
    - カテゴリの意外性
    - ペナルティ要素追加

    改善点（v3）:
    - 否定形パターン除外
    - テキスト長正規化
    - 重複キーワード制限

    Args:
        episode_data: エピソードデータ

    Returns:
        surprise_score（1.0-10.0）
    """
    score = 3.0  # ベーススコア（下方修正）
    episode_text = str(episode_data.get("episode_text", ""))
    episode_type = episode_data.get("episode_type", "")
    category = episode_data.get("category", "")

    # 1. ツイストキーワード (+2.5) - 改善版v3使用
    twist_count = count_keywords_v3(episode_text, SURPRISE_KEYWORDS["twist"], normalize_by_length=True)
    score += min(twist_count * 0.8, 2.5)

    # 2. コントラストキーワード (+2.0) - 改善版v3使用
    contrast_count = count_keywords_v3(episode_text, SURPRISE_KEYWORDS["contrast"], normalize_by_length=True)
    score += min(contrast_count * 0.6, 2.0)

    # 3. 予想外キーワード (+2.5) - 改善版v3使用
    unexpected_count = count_keywords_v3(episode_text, SURPRISE_KEYWORDS["unexpected"], normalize_by_length=True)
    score += min(unexpected_count * 0.5, 2.5)

    # 4. 達成ツイストキーワード (+2.0) - 改善版v3使用
    achievement_twist_count = count_keywords_v3(
        episode_text, SURPRISE_KEYWORDS["achievement_twist"], normalize_by_length=True
    )
    score += min(achievement_twist_count * 0.7, 2.0)

    # 5. 起源ツイストキーワード (+1.5) - 改善版v3使用
    origin_twist_count = count_keywords_v3(episode_text, SURPRISE_KEYWORDS["origin_twist"], normalize_by_length=True)
    score += min(origin_twist_count * 0.5, 1.5)

    # 6. 年齢とエピソードタイプの組み合わせ (+1.5)
    try:
        age = float(episode_data.get("age", 0))

        # 若い年齢での大きな達成は意外性が高い
        if age <= 18 and episode_type in ["ACHIEVEMENT", "INNOVATION", "FOUNDING"]:
            score += 1.5
        elif age <= 22 and episode_type in ["ACHIEVEMENT", "INNOVATION", "FOUNDING"]:
            score += 1.0
        elif age <= 25 and episode_type in ["ACHIEVEMENT", "INNOVATION", "FOUNDING"]:
            score += 0.6
        # 高齢での挑戦も意外性が高い
        elif age >= 75 and episode_type in ["CHALLENGE", "GROWTH", "COMEBACK"]:
            score += 1.5
        elif age >= 65 and episode_type in ["CHALLENGE", "GROWTH", "COMEBACK"]:
            score += 1.0
        elif age >= 55 and episode_type in ["CHALLENGE", "GROWTH", "COMEBACK"]:
            score += 0.5
        # 中年での転機
        elif 40 <= age <= 55 and episode_type == "TURNING_POINT":
            score += 0.8
    except (ValueError, TypeError):
        pass

    # 7. エピソードタイプによる補正 (+1.2)
    surprising_types = ["COMEBACK", "FAILURE", "TURNING_POINT"]
    if episode_type in surprising_types:
        score += 1.2

    # 8. カテゴリによる意外性加点 (+0.8)
    surprising_categories = ["探検・冒険", "映画・演劇", "アニメ・漫画・ゲーム", "スポーツ"]
    if category in surprising_categories:
        score += 0.8

    # ペナルティ要素
    # 9. 意外性キーワードが全くない (-1.0)
    total_surprise_keywords = twist_count + contrast_count + unexpected_count
    if total_surprise_keywords == 0:
        score -= 1.0

    # 10. 平凡なエピソードタイプ (-0.5)
    mundane_types = ["DAILY", "ROUTINE"]
    if episode_type in mundane_types:
        score -= 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_generation_quality_score(episode_data: Dict) -> float:
    """
    generation_quality_scoreを計算（改善版v3）

    評価基準:
    - 文章の長さ（適切な長さ）
    - 文法的な完成度（簡易チェック）
    - 読みやすさ（文の長さのバランス）
    - 表現の多様性
    - ペナルティ要素強化

    Args:
        episode_data: エピソードデータ

    Returns:
        generation_quality_score（1.0-10.0）
    """
    score = 3.5  # ベーススコア（さらに下方修正）
    episode_text = str(episode_data.get("episode_text", ""))

    # テキストが空の場合
    if not episode_text.strip():
        return 1.0

    char_count = len(episode_text)

    # 1. 適切な文字数 (+1.5) - 加点を緩やかに
    if 220 <= char_count <= 320:
        score += 1.5
    elif 200 <= char_count <= 350:
        score += 1.0
    elif 180 <= char_count <= 400:
        score += 0.5

    # 2. 文の数と平均長さ (+1.2)
    sentences = re.split(r"[。！？]", episode_text)
    sentences = [s for s in sentences if s.strip()]
    if sentences:
        avg_sentence_length = char_count / len(sentences)
        sentence_count = len(sentences)

        # 適切な文の数（4-6文が理想）
        if 4 <= sentence_count <= 6:
            score += 0.6
        elif 3 <= sentence_count <= 7:
            score += 0.3

        # 適切な平均長さ
        if 35 <= avg_sentence_length <= 45:
            score += 0.6
        elif 30 <= avg_sentence_length <= 50:
            score += 0.3

    # 3. 句読点の適切な使用 (+0.8)
    comma_count = episode_text.count("、")
    period_count = episode_text.count("。")
    # 読点と句点のバランス
    if 5 <= comma_count <= 10 and 3 <= period_count <= 6:
        score += 0.8
    elif comma_count >= 4 and period_count >= 3:
        score += 0.4

    # 4. 完結性（最後が句点で終わる） (+0.3)
    if episode_text.rstrip().endswith("。"):
        score += 0.3

    # 5. フォーマット準拠（「あなたと同じ」で始まる） (+0.8)
    if episode_text.startswith("あなたと同じ"):
        score += 0.8

    # 6. 文章の多様性（異なる文末表現） (+0.8)
    endings = []
    for s in sentences:
        s = s.strip()
        if s:
            # 最後の2-3文字を取得
            ending = s[-3:] if len(s) >= 3 else s
            endings.append(ending)
    unique_endings = len(set(endings))
    if unique_endings >= 4:
        score += 0.8
    elif unique_endings >= 3:
        score += 0.4

    # 7. 具体的な描写（引用、数値） (+0.6)
    quote_count = episode_text.count("「")
    has_numbers = bool(re.search(r"\d+", episode_text))
    if quote_count >= 1 and has_numbers:
        score += 0.6
    elif quote_count >= 1 or has_numbers:
        score += 0.3

    # ペナルティ要素（強化）
    # 8. テキストが短すぎる (-2.5)
    if char_count < 80:
        score -= 2.5
    elif char_count < 120:
        score -= 1.5
    elif char_count < 150:
        score -= 0.8

    # 9. テキストが長すぎる (-1.5)
    if char_count > 500:
        score -= 1.5
    elif char_count > 450:
        score -= 0.8
    elif char_count > 400:
        score -= 0.3

    # 10. 冗長表現のペナルティ (-1.5)
    redundant_patterns = ["ということ", "というものは", "のようなもの", "といえる", "と言える", "であると言える"]
    redundant_count = sum(episode_text.count(p) for p in redundant_patterns)
    if redundant_count >= 3:
        score -= 1.5
    elif redundant_count >= 2:
        score -= 0.8
    elif redundant_count >= 1:
        score -= 0.3

    # 11. 同じ表現の繰り返し (-0.8)
    for pattern in re.findall(r"(.{2,5})\1{2,}", episode_text):
        score -= 0.8
        break

    # 12. メタ的説明のペナルティ (-3.0)
    meta_patterns = ["架空の", "実在しない", "フィクション", "設定上", "想像上"]
    if any(p in episode_text for p in meta_patterns):
        score -= 3.0

    # 13. 文末表現が単調 (-0.5)
    if len(endings) >= 3 and unique_endings <= 2:
        score -= 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_educational_value_score(episode_data: Dict) -> float:
    """
    educational_valueスコアを計算（改善版v3）

    評価基準:
    - 教訓・学びを示すキーワード
    - 具体的な事実の存在
    - カテゴリの教育的重要性
    - 普遍的な洞察の有無
    - ペナルティ要素追加

    改善点（v3）:
    - 否定形パターン除外
    - テキスト長正規化
    - 重複キーワード制限

    Args:
        episode_data: エピソードデータ

    Returns:
        educational_valueスコア（1.0-10.0）
    """
    score = 3.5  # ベーススコア（下方修正）
    episode_text = str(episode_data.get("episode_text", ""))

    # 1. 教訓キーワード (+2.5) - 改善版v3使用
    lesson_count = count_keywords_v3(episode_text, EDUCATIONAL_KEYWORDS["lesson"], normalize_by_length=True)
    score += min(lesson_count * 0.8, 2.5)

    # 2. 洞察キーワード (+2.0) - 改善版v3使用
    insight_count = count_keywords_v3(episode_text, EDUCATIONAL_KEYWORDS["insight"], normalize_by_length=True)
    score += min(insight_count * 0.6, 2.0)

    # 3. 普遍性キーワード (+1.5) - 改善版v3使用
    universal_count = count_keywords_v3(episode_text, EDUCATIONAL_KEYWORDS["universal"], normalize_by_length=True)
    score += min(universal_count * 0.5, 1.5)

    # 4. カテゴリによる補正 (+1.5)
    category = episode_data.get("category", "")
    educational_categories = ["科学・技術", "教育", "医療・福祉", "政治・国際", "思想・哲学"]
    if any(cat in category for cat in educational_categories):
        score += 1.5
    elif category in ["ビジネス・経済", "文学・出版"]:
        score += 0.8

    # 5. 具体的な数値データ (+1.0)
    numbers = re.findall(r"\d+", episode_text)
    if len(numbers) >= 5:
        score += 1.0
    elif len(numbers) >= 3:
        score += 0.5

    # 6. エピソードタイプ補正 (+1.0)
    episode_type = episode_data.get("episode_type", "")
    educational_types = ["ACHIEVEMENT", "INNOVATION", "FAILURE", "GROWTH"]
    if episode_type in educational_types:
        score += 1.0
    elif episode_type in ["CHALLENGE", "TURNING_POINT"]:
        score += 0.5

    # 7. 引用（名言など） (+0.5)
    if "「" in episode_text and "」" in episode_text:
        score += 0.5

    # ペナルティ要素
    # 8. 教訓的要素がない (-1.5)
    total_educational = lesson_count + insight_count + universal_count
    if total_educational == 0:
        score -= 1.5

    # 9. 事実の羅列のみ (-0.5)
    fact_patterns = ["記録", "達成", "受賞", "優勝", "獲得"]
    fact_count = sum(1 for p in fact_patterns if p in episode_text)
    if fact_count >= 3 and total_educational == 0:
        score -= 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_all_five_axes(episode_data: Dict) -> Dict[str, float]:
    """
    5軸スコアを一括計算

    Args:
        episode_data: エピソードデータ

    Returns:
        5軸スコアの辞書
    """
    return {
        "memorability_score": calculate_memorability_score(episode_data),
        "empathy_score": calculate_empathy_score(episode_data),
        "surprise_score": calculate_surprise_score(episode_data),
        "generation_quality_score": calculate_generation_quality_score(episode_data),
        "educational_value": calculate_educational_value_score(episode_data),
    }


# ============================================================
# story_quality・factual_density（統一版）
# ============================================================


def calculate_storytelling_quality(episode_text: str, episode_type: str) -> float:
    """
    story_qualityスコアを算出（統一版・改善版v2）（1-10点）

    評価基準：
    - ストーリーの構成: 起承転結があるか
    - 感情の描写: 感情が伝わるか
    - 臨場感: 場面が想像できるか
    - 引き込む力: 続きが気になるか
    - ペナルティ要素

    Args:
        episode_text: エピソードテキスト
        episode_type: エピソードタイプ（ACHIEVEMENT, TURNING_POINT等）

    Returns:
        story_qualityスコア（1.0-10.0）
    """
    score = 3.0  # ベーススコア（改善版v2）

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
    factual_densityスコアを算出（統一版・改善版v3）（1-10点）

    評価基準：
    - 具体的な数値データ: 年号、数量、記録など（年齢は除外）
    - 固有名詞: 人名、地名、作品名など
    - 検証可能な事実: 記録、受賞、出来事など
    - 情報の密度: 単位文字数あたりの情報量
    - ペナルティ要素

    Args:
        episode_text: エピソードテキスト
        episode_type: エピソードタイプ（ACHIEVEMENT, TURNING_POINT等）

    Returns:
        factual_densityスコア（1.0-10.0）
    """
    score = 3.0  # ベーススコア（改善版v3）

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


def calculate_all_seven_axes(episode_data: Dict) -> Dict[str, float]:
    """
    7軸スコアを一括計算（統一版）

    Args:
        episode_data: エピソードデータ

    Returns:
        7軸スコアの辞書
    """
    episode_text = str(episode_data.get("episode_text", ""))
    episode_type = str(episode_data.get("episode_type", ""))

    # 5軸を計算
    five_axes = calculate_all_five_axes(episode_data)

    # 2軸を追加
    five_axes["story_quality"] = calculate_storytelling_quality(episode_text, episode_type)
    five_axes["factual_density"] = calculate_factual_density(episode_text, episode_type)

    return five_axes


# ============================================================
# 改善版総合スコア（0〜1000スケール）
# ============================================================


def calculate_enhanced_composite_score(
    episode_data: Dict, k: float = 0.85, min_axes_required: int = 1
) -> Optional[float]:
    """
    改善版総合スコア（0〜1000スケール）

    7軸スコアを正規化・非線形変換し、均等重みで平均化。
    旧composite_score（1-10スケール）を置き換える。

    設計:
    - 7軸均等重み
    - 非線形変換 k=0.85（低スコアを上方に伸ばす）
    - スケール: 0〜1000

    変換式:
        1. 正規化: normalized = (score - 1.0) / 9.0  # 1-10 → 0-1
        2. 非線形変換: transformed = normalized ** k
           k < 1.0 により、低〜中スコアの差を拡大
        3. 平均化: avg = mean(transformed_scores)
        4. スケール: final = avg * 1000

    Args:
        episode_data: エピソードデータ（Dict）
        k: 非線形変換の指数（デフォルト: 0.85）
        min_axes_required: 計算に必要な最低軸数（デフォルト: 1）

    Returns:
        enhanced_composite_score（0-1000スケール）、計算不可の場合はNone

    Example:
        7軸平均5.5の場合:
        - 正規化: (5.5-1)/9 = 0.5
        - 変換: 0.5^0.85 = 0.55
        - スコア: 550（中央付近）
    """
    transformed_scores = []

    for field in SEVEN_AXIS_FIELDS:
        raw_score = episode_data.get(field)

        # 値の取得と検証
        if raw_score is None or raw_score == "":
            continue

        try:
            score = float(raw_score)
            # 範囲チェック（1-10）
            if not (1.0 <= score <= 10.0):
                continue

            # Step 1: 正規化 (1-10 → 0-1)
            normalized = (score - 1.0) / 9.0

            # Step 2: 非線形変換（k=0.85）
            # k < 1.0 により、低〜中スコアの差を拡大
            # 例: 0.33 → 0.40, 0.50 → 0.55, 0.78 → 0.82
            transformed = normalized**k

            transformed_scores.append(transformed)
        except (ValueError, TypeError):
            continue

    # 最低軸数チェック
    if len(transformed_scores) < min_axes_required:
        return None

    # Step 3: 均等重み平均 → 0〜1000スケール
    if transformed_scores:
        avg_transformed = sum(transformed_scores) / len(transformed_scores)
        final_score = avg_transformed * 1000
        return round(final_score, 1)

    return None


def convert_old_to_new_score(old_score: float, k: float = 0.85) -> float:
    """
    旧スコア（1-10）を新スコア（0-1000）に変換

    Args:
        old_score: 旧スコア（1-10スケール）
        k: 非線形変換の指数（デフォルト: 0.85）

    Returns:
        新スコア（0-1000スケール）
    """
    if old_score < 1.0:
        return 0.0
    if old_score > 10.0:
        return 1000.0

    normalized = (old_score - 1.0) / 9.0
    transformed = normalized**k
    return round(transformed * 1000, 1)


def get_score_grade(score: float) -> str:
    """
    スコアからグレードを取得

    Args:
        score: 新スコア（0-1000スケール）

    Returns:
        グレード文字列（S/A/B/C/D/E）
    """
    if score >= 800:
        return "S"  # 最高品質（上位5%）
    elif score >= 650:
        return "A"  # 高品質（上位20%）
    elif score >= 500:
        return "B"  # 標準品質（中央）
    elif score >= 350:
        return "C"  # 改善余地あり
    elif score >= 200:
        return "D"  # 要改善
    else:
        return "E"  # 大幅改善必要


# ============================================================
# 統一スケールスコア（全0〜1000）
# ============================================================


def calculate_unified_scores(episode_data: Dict) -> Dict[str, Optional[float]]:
    """
    統一スケールスコアを計算（全0〜1000）

    全ての主要スコアを0-1000スケールに統一し、
    超総合（super_total_score）を加重平均で算出する。

    計算式:
    - fame_score_1000 = fame_score × 10（0-100 → 0-1000）
    - episode_fame_score_1000 = episode_fame_score × 10
    - super_total_score = composite × 0.5 + fame_1000 × 0.25 + ep_fame_1000 × 0.25

    重み設計の根拠:
    - composite_score（7軸総合）: 50% - エピソード品質が最重要
    - fame_score（有名人度）: 25% - 人物の知名度
    - episode_fame_score（エピ有名度）: 25% - エピソード自体の有名度

    Args:
        episode_data: エピソードデータ（Dict）

    Returns:
        統一スコアの辞書:
        {
            'composite_score': 0-1000,
            'fame_score_1000': 0-1000,
            'episode_fame_score_1000': 0-1000,
            'super_total_score': 0-1000,
        }

    Example:
        入力: composite=550, fame=70, ep_fame=84
        変換:
        - fame_1000 = 70 × 10 = 700
        - ep_fame_1000 = 84 × 10 = 840
        - super_total = 550×0.5 + 700×0.25 + 840×0.25
                      = 275 + 175 + 210 = 660
        出力: super_total_score=660
    """
    result = {
        "composite_score": None,
        "fame_score_1000": None,
        "episode_fame_score_1000": None,
        "super_total_score": None,
    }

    # 1. composite_score取得（既に0-1000スケール）
    composite = episode_data.get("composite_score")
    if composite is not None and composite != "":
        try:
            result["composite_score"] = round(float(composite), 1)
        except (ValueError, TypeError):
            pass

    # 2. fame_score変換（0-100 → 0-1000）
    fame = episode_data.get("fame_score")
    if fame is not None and fame != "":
        try:
            fame_val = float(fame)
            # 範囲チェック（0-100）
            if 0 <= fame_val <= 100:
                result["fame_score_1000"] = round(fame_val * 10, 1)
        except (ValueError, TypeError):
            pass

    # 3. episode_fame_score変換（0-100 → 0-1000）
    ep_fame = episode_data.get("episode_fame_score")
    if ep_fame is not None and ep_fame != "":
        try:
            ep_fame_val = float(ep_fame)
            # 範囲チェック（0-100）
            if 0 <= ep_fame_val <= 100:
                result["episode_fame_score_1000"] = round(ep_fame_val * 10, 1)
        except (ValueError, TypeError):
            pass

    # 4. super_total_score計算（加重平均）
    # 重み: composite=0.5, fame=0.25, ep_fame=0.25
    composite_val = result["composite_score"] or 0
    fame_1000 = result["fame_score_1000"] or 0
    ep_fame_1000 = result["episode_fame_score_1000"] or 0

    # 少なくともcomposite_scoreがあれば計算
    if result["composite_score"] is not None:
        super_total = composite_val * 0.5 + fame_1000 * 0.25 + ep_fame_1000 * 0.25
        result["super_total_score"] = round(super_total, 1)

    return result


def get_super_total_grade(score: float) -> str:
    """
    超総合スコアからグレードを取得

    Args:
        score: 超総合スコア（0-1000スケール）

    Returns:
        グレード文字列（S/A/B/C/D/E）
    """
    # composite_scoreと同じ基準を使用
    return get_score_grade(score)


# ============================================================
# ハイブリッド評価システム（ルールベース + LLM最適化重み）
# ============================================================

# 最適化された重み設定（軸間相関低減版 v2）
# Phase 1改善: 共感性と意外性の重み差別化
HYBRID_WEIGHTS = {
    "記憶性": (0.6, 0.4),  # ルール60%, LLM40% (独自要素追加により調整)
    "共感性": (0.2, 0.8),  # ルール20%, LLM80% (感情はLLM向き)
    "意外性": (0.5, 0.5),  # ルール50%, LLM50% (事実確認はルール向き)
    "生成品質": (0.9, 0.1),  # ルール90%, LLM10% (維持)
    "educational_value": (0.4, 0.6),  # ルール40%, LLM60% (維持)
    "story_quality": (0.4, 0.6),  # ルール40%, LLM60% (維持)
    "factual_density": (1.0, 0.0),  # ルールのみ (維持)
}


def calculate_hybrid_rule_scores(episode_data: Dict) -> Dict[str, float]:
    """
    ハイブリッド評価用のルールベーススコアを計算（Phase 1改善版）

    改善点:
    - 共感性キーワード: 感情・人間関係に特化（意外性と重複しない）
    - 意外性キーワード: 展開・事実に特化（共感性と重複しない）
    - 記憶性キーワード: 独自の印象深さ要素を追加

    Args:
        episode_data: エピソードデータ

    Returns:
        各軸のルールベーススコア辞書
    """
    episode_text = str(episode_data.get("episode_text", ""))
    episode_type = str(episode_data.get("episode_type", ""))

    # factual_density用のルールベース計算
    year_count = len(re.findall(r"(19|20)\d{2}年?", episode_text))
    number_count = len(re.findall(r"\d+[歳回位人件万億円ドル%]", episode_text))
    katakana_count = len(re.findall(r"[ァ-ヴー]{3,}", episode_text))

    base_len = max(len(episode_text), 100) / 300
    fact_raw = (year_count * 2 + number_count * 1.5 + katakana_count * 0.5) / base_len
    fact_score = min(10, max(1, 3 + fact_raw * 1.5))

    # ===== Phase 2改善: ベーススコア調整（スケール補正） =====
    # 目標: 平均7-8点、軸間独立性を維持

    # 記憶性キーワード（独自: 印象深さ・象徴性）- Phase 5: factual_densityから独立
    memorability_kw = [
        "印象的",
        "忘れられない",
        "鮮明",
        "象徴的",
        "転換点",
        "分岐点",
        "決定的",
        "運命",
        "ドラマチック",
        "エポック",
        "画期的",
        "歴史的",
        "記念",
        "記録",
        "金字塔",
        "偉業",
    ]
    memorability_count = sum(1 for kw in memorability_kw if kw in episode_text)

    # Phase 6: 記憶性独自の評価要素（factual_density・story_qualityとの相関を排除）
    # 歴史的重要性マーカー（記憶性専用 - story_qualityと異なる）
    historic_markers = ["歴史を変えた", "時代を画した", "革命的", "画期的", "先駆け", "礎を築いた"]
    historic_count = sum(1 for hm in historic_markers if hm in episode_text)

    # 感情的インパクトマーカー（記憶性専用）
    emotional_impact_markers = ["衝撃", "驚愕", "感銘", "鮮烈", "圧倒", "忘れがたい", "心に刻まれ"]
    emotional_impact_count = sum(1 for em in emotional_impact_markers if em in episode_text)

    # インパクト要素（記憶に残る表現）
    impact_markers = ["初めて", "世界初", "史上初", "唯一", "最高", "最大", "前人未踏", "破った"]
    impact_count = sum(1 for im in impact_markers if im in episode_text)

    # 人物・出来事の固有性マーカー（記憶性専用 - story_qualityと異なる）
    uniqueness_markers = ["類を見ない", "比類なき", "空前の", "唯一無二", "特異な", "異例の", "稀有な"]
    uniqueness_count = sum(1 for um in uniqueness_markers if um in episode_text)

    # 伝説・逸話マーカー（記憶性専用）
    legend_markers = ["伝説", "逸話", "語り継がれ", "名を残し", "後世に"]
    legend_count = sum(1 for lm in legend_markers if lm in episode_text)

    # Phase 6: ベース6.0 + 独自要素（factual_density・story_qualityとの相関を排除）
    memorability_score = min(
        10,
        max(
            1,
            6.0
            + memorability_count * 0.5
            + historic_count * 0.5
            + emotional_impact_count * 0.4
            + impact_count * 0.4
            + uniqueness_count * 0.5
            + legend_count * 0.4,
        ),
    )

    # 共感性キーワード（Phase 4: 識別力強化）
    # 基本感情キーワード
    empathy_kw = [
        "涙",
        "感動",
        "喜び",
        "悲しみ",
        "苦悩",
        "希望",
        "絶望",
        "家族",
        "母",
        "父",
        "子供",
        "友人",
        "恩師",
        "愛",
        "心",
        "思い",
        "気持ち",
        "願い",
        "祈り",
        "支え",
        "絆",
    ]
    empathy_count = sum(1 for kw in empathy_kw if kw in episode_text)

    # 感情強度マーカー（強い感情表現）
    intensity_markers = ["深く", "強く", "激しく", "心から", "胸が", "涙が", "震える", "溢れる"]
    intensity_count = sum(1 for im in intensity_markers if im in episode_text)

    # 人間関係の深さ（具体的な関係性描写）
    relationship_depth = ["支えてくれた", "励まし", "見守", "信じて", "寄り添", "共に歩"]
    rel_count = sum(1 for rd in relationship_depth if rd in episode_text)

    # Phase 4: 多層的な共感性評価
    empathy_score = 5.0  # ベースを下げて変動幅確保
    empathy_score += empathy_count * 0.5  # キーワード
    empathy_score += intensity_count * 0.6  # 強度
    empathy_score += rel_count * 0.5  # 関係性深度
    empathy_score = min(10, max(1, empathy_score))

    # 意外性キーワード（Phase 4: 識別力強化）
    # 基本意外性キーワード
    surprise_kw = [
        "実は",
        "意外にも",
        "驚くべき",
        "予想外",
        "突然",
        "逆転",
        "番狂わせ",
        "史上初",
        "世界初",
        "前例のない",
        "秘密",
        "真実",
        "知られざる",
        "皮肉にも",
        "偶然",
    ]
    surprise_count = sum(1 for kw in surprise_kw if kw in episode_text)

    # 物語展開マーカー（転換・対比）
    twist_markers = ["ところが", "だが", "しかし", "一方で", "対照的に", "逆に", "むしろ"]
    twist_count = sum(1 for tm in twist_markers if tm in episode_text)

    # 発見・啓示パターン
    revelation_patterns = ["気づ", "悟", "発見", "明らか", "判明", "分かっ", "知っ"]
    rev_count = sum(1 for rp in revelation_patterns if rp in episode_text)

    # Phase 4: 多層的な意外性評価
    surprise_score = 5.0  # ベースを下げて変動幅確保
    surprise_score += surprise_count * 0.6  # 意外性キーワード
    surprise_score += twist_count * 0.5  # 転換マーカー
    surprise_score += rev_count * 0.4  # 発見パターン
    surprise_score = min(10, max(1, surprise_score))

    # 教訓スコア（Phase 4: 識別力強化）
    # 基本教訓キーワード
    lesson_kw = ["学", "教訓", "大切", "重要", "示", "証明", "物語", "意味", "価値"]
    lesson_count = sum(1 for kw in lesson_kw if kw in episode_text)

    # 洞察・気づきパターン
    insight_patterns = ["ことを教えて", "を学んだ", "を知った", "に気づいた", "を悟った", "を理解した"]
    insight_count = sum(1 for ip in insight_patterns if ip in episode_text)

    # 実践・応用パターン
    practical_patterns = ["活かし", "生かし", "役立て", "応用", "実践", "影響を与え", "変え"]
    practical_count = sum(1 for pp in practical_patterns if pp in episode_text)

    # 普遍性・一般化パターン
    universal_patterns = ["人生", "成功", "努力", "挑戦", "困難", "逆境", "成長", "可能性"]
    universal_count = sum(1 for up in universal_patterns if up in episode_text)

    # Phase 4: 多層的なeducational_value評価
    lesson_score = 5.0  # ベースを下げて変動幅確保
    lesson_score += lesson_count * 0.4  # 基本キーワード
    lesson_score += insight_count * 0.8  # 洞察（重視）
    lesson_score += practical_count * 0.5  # 実践
    lesson_score += universal_count * 0.3  # 普遍性
    lesson_score = min(10, max(1, lesson_score))

    # テキスト品質スコア（既に適切な分布のため維持）
    sentences = len(re.findall(r"[。！？]", episode_text))
    avg_len = len(episode_text) / max(sentences, 1)
    text_quality = 5
    if 40 <= avg_len <= 80:
        text_quality += 2
    elif 30 <= avg_len <= 100:
        text_quality += 1
    if 5 <= sentences <= 10:
        text_quality += 2
    elif 3 <= sentences <= 15:
        text_quality += 1
    text_quality = min(10, max(1, text_quality))

    # 構造スコア（Phase 4: 識別力強化）
    # 基本構造
    structure_score = 5.0  # ベースを下げて変動幅を確保

    # 1. 開始構造ボーナス
    if episode_text.startswith("あなたと同じ"):
        structure_score += 0.8

    # 2. 段落構造
    paragraphs = episode_text.count("\n\n") + 1
    if 2 <= paragraphs <= 4:
        structure_score += 0.5

    # 3. 文の多様性（文長の変動）
    sentences_list = re.split(r"[。！？]", episode_text)
    sentences_list = [s.strip() for s in sentences_list if len(s.strip()) > 5]
    if len(sentences_list) >= 3:
        sent_lengths = [len(s) for s in sentences_list]
        avg_sent_len = sum(sent_lengths) / len(sent_lengths)
        sent_std = (sum((l - avg_sent_len) ** 2 for l in sent_lengths) / len(sent_lengths)) ** 0.5
        # 文長の変動が大きいほどボーナス（多様なリズム）
        if sent_std > 30:
            structure_score += 1.0
        elif sent_std > 20:
            structure_score += 0.6
        elif sent_std > 10:
            structure_score += 0.3

    # 4. 会話・引用の存在（「」の使用）
    dialogue_count = episode_text.count("「")
    if dialogue_count >= 2:
        structure_score += 0.8
    elif dialogue_count == 1:
        structure_score += 0.4

    # 5. 時間的展開（時制マーカー）
    temporal_markers = ["その後", "やがて", "ついに", "最終的に", "結果として", "こうして", "以来", "それから"]
    temporal_count = sum(1 for tm in temporal_markers if tm in episode_text)
    structure_score += min(1.0, temporal_count * 0.4)

    # 6. 対比・展開構造
    contrast_markers = ["しかし", "一方", "ところが", "だが", "それでも", "にもかかわらず"]
    contrast_count = sum(1 for cm in contrast_markers if cm in episode_text)
    structure_score += min(0.8, contrast_count * 0.3)

    # 7. 具体性（固有名詞・数値）
    specificity = year_count + number_count / 2
    if specificity >= 5:
        structure_score += 0.6
    elif specificity >= 3:
        structure_score += 0.3

    structure_score = min(10, max(1, structure_score))

    return {
        "記憶性": memorability_score,  # 独自要素を使用
        "共感性": empathy_score,  # 差別化されたキーワード
        "意外性": surprise_score,  # 差別化されたキーワード
        "生成品質": text_quality,
        "educational_value": lesson_score,
        "story_quality": structure_score,
        "factual_density": fact_score,
    }


def calculate_hybrid_scores(episode_data: Dict, llm_scores: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    ハイブリッド評価スコアを計算

    ルールベーススコアとLLMスコアを最適化された重みで統合。
    LLMスコアがない場合はルールベースのみを使用。

    Args:
        episode_data: エピソードデータ
        llm_scores: LLM評価スコア（オプション）
            期待形式: {"empathy": 7, "surprise": 6, "story_quality": 8}

    Returns:
        7軸のハイブリッドスコア辞書
    """
    # ルールベーススコア計算
    rule_scores = calculate_hybrid_rule_scores(episode_data)

    # Phase 5: LLMスコアがない場合はルールベースのみで計算（分散維持）
    if llm_scores is None:
        # LLMなし時はルールベース100%を使用して分散を維持
        hybrid_scores = {}
        for axis in HYBRID_WEIGHTS.keys():
            hybrid_scores[axis] = round(rule_scores.get(axis, 5), 1)
        return hybrid_scores

    # LLMスコアのマッピング
    llm_mapped = {
        "記憶性": (llm_scores.get("empathy", 7.5) + llm_scores.get("surprise", 7.5)) / 2,
        "共感性": llm_scores.get("empathy", 7.5),
        "意外性": llm_scores.get("surprise", 7.5),
        "生成品質": llm_scores.get("story_quality", 7.5),
        "educational_value": llm_scores.get("empathy", 7.5),
        "story_quality": llm_scores.get("story_quality", 7.5),
        "factual_density": 7.5,  # 使用しない（重み0）
    }

    # 重み付き統合（LLMスコアあり時のみ）
    hybrid_scores = {}
    for axis, (rule_w, llm_w) in HYBRID_WEIGHTS.items():
        rule_val = rule_scores.get(axis, 5)
        llm_val = llm_mapped.get(axis, 7.5)
        hybrid_scores[axis] = round(rule_val * rule_w + llm_val * llm_w, 1)

    return hybrid_scores


def calculate_hybrid_seven_axes(episode_data: Dict) -> Dict[str, float]:
    """
    ハイブリッド方式で7軸スコアを計算（LLMなし版）

    LLM APIを呼び出さず、ルールベースのみで計算。
    本番環境でAPI呼び出しを避けたい場合に使用。

    Args:
        episode_data: エピソードデータ

    Returns:
        7軸スコアの辞書（日本語フィールド名）
    """
    hybrid = calculate_hybrid_scores(episode_data, llm_scores=None)

    return {
        "memorability_score": hybrid["記憶性"],
        "empathy_score": hybrid["共感性"],
        "surprise_score": hybrid["意外性"],
        "generation_quality_score": hybrid["生成品質"],
        "educational_value": hybrid["educational_value"],
        "story_quality": hybrid["story_quality"],
        "factual_density": hybrid["factual_density"],
    }


# ============================================================
# Phase 3: 5軸統合スコア計算
# ============================================================


def calculate_five_axis_scores(seven_axis_data: Dict) -> Dict[str, float]:
    """
    7軸スコアから5軸統合スコアを計算

    統合ルール:
    - 総合品質 = (memorability_score + generation_quality_score) / 2
    - 感情インパクト = (empathy_score + surprise_score) / 2
    - educational_value, story_quality, factual_density = そのまま維持

    Args:
        seven_axis_data: 7軸スコアを含むデータ辞書

    Returns:
        5軸スコアの辞書
    """
    five_axis = {}

    for axis, config in FIVE_AXIS_COMPOSITION.items():
        sources = config["sources"]
        weights = config["weights"]

        # ソーススコアを取得
        values = []
        for source in sources:
            val = seven_axis_data.get(source)
            if val is not None and val != "":
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass

        # 加重平均を計算
        if values and len(values) == len(weights):
            weighted_sum = sum(v * w for v, w in zip(values, weights))
            five_axis[axis] = round(weighted_sum, 2)
        elif values:
            # 一部の値のみ利用可能な場合は単純平均
            five_axis[axis] = round(sum(values) / len(values), 2)
        else:
            five_axis[axis] = None

    return five_axis


def calculate_five_axis_composite(five_axis_data: Dict, min_axes: int = 3) -> Optional[float]:
    """
    5軸スコアからcomposite_scoreを計算

    Args:
        five_axis_data: 5軸スコアを含むデータ辞書
        min_axes: 計算に必要な最低軸数

    Returns:
        composite_score（0-10スケール）、計算不可の場合はNone
    """
    scores = []

    for field in FIVE_AXIS_FIELDS:
        value = five_axis_data.get(field)
        if value is not None:
            try:
                score = float(value)
                if 0 <= score <= 10:
                    scores.append(score)
            except (ValueError, TypeError):
                pass

    if len(scores) >= min_axes:
        return round(sum(scores) / len(scores), 2)

    return None


def convert_seven_to_five_axes(episode_data: Dict) -> Dict:
    """
    エピソードデータを7軸から5軸形式に変換

    元の7軸スコアを保持しつつ、5軸スコアを追加。

    Args:
        episode_data: 7軸スコアを含むエピソードデータ

    Returns:
        5軸スコアが追加されたエピソードデータ
    """
    result = dict(episode_data)

    # 5軸スコアを計算
    five_axis = calculate_five_axis_scores(episode_data)

    # 5軸スコアを追加
    for axis, score in five_axis.items():
        result[axis] = score

    # 5軸ベースのcomposite_scoreを計算
    five_composite = calculate_five_axis_composite(five_axis)
    if five_composite is not None:
        result["composite_score_5axis"] = five_composite

    return result


def calculate_hybrid_five_axes(episode_data: Dict) -> Dict[str, float]:
    """
    エピソードデータから5軸スコアを直接計算

    内部で7軸計算を行い、5軸に統合して返す。

    Args:
        episode_data: エピソードデータ（episode_text等を含む）

    Returns:
        5軸スコアの辞書
    """
    # 7軸スコアを計算
    seven_axis = calculate_hybrid_seven_axes(episode_data)

    # 5軸に変換
    return calculate_five_axis_scores(seven_axis)


# ============================================================
# Phase 7: LLM連携評価システム（分散向上版）
# ============================================================

# LLM評価プロンプト（7軸独立評価用）
LLM_EVALUATION_PROMPT = """
以下のエピソードを7つの軸で評価してください。
各軸は1-10点で、できるだけ差をつけて評価してください。

【評価軸と基準】

1. 記憶性 (1-10): 読者の記憶に残るか
   - 10: 一生忘れない衝撃的な内容
   - 7: 印象に残る
   - 4: 普通
   - 1: 忘れやすい

2. 共感性 (1-10): 感情移入できるか
   - 10: 涙が出るほど共感
   - 7: 気持ちがわかる
   - 4: 普通
   - 1: 共感できない

3. 意外性 (1-10): 予想外の展開があるか
   - 10: 完全に予想を裏切る
   - 7: 少し意外
   - 4: 普通
   - 1: 予想通り

4. 生成品質 (1-10): 文章の品質
   - 10: プロの文章
   - 7: 読みやすい
   - 4: 普通
   - 1: 読みにくい

5. educational_value (1-10): 学びがあるか
   - 10: 人生を変える学び
   - 7: 参考になる
   - 4: 普通
   - 1: 学びなし

6. story_quality (1-10): 物語としての完成度
   - 10: 映画化できるレベル
   - 7: 引き込まれる
   - 4: 普通
   - 1: 面白くない

7. factual_density (1-10): 具体的な事実の豊富さ
   - 10: 年号・数値・固有名詞が豊富
   - 7: 具体的
   - 4: 普通
   - 1: 抽象的

【重要】
- 7点をデフォルトにしないでください
- 各軸で異なる点数をつけてください
- 極端な点数（1-3, 9-10）も積極的に使用してください

【エピソード】
{episode_text}

【出力形式】
必ず以下のJSON形式のみで出力してください（説明不要）:
{{"記憶性": X, "共感性": X, "意外性": X, "生成品質": X, "educational_value": X, "story_quality": X, "factual_density": X}}
"""

# Phase 7B: ターゲット統計（ルールベース実績）
LLM_TARGET_STATS = {
    "記憶性": {"mean": 6.24, "std": 0.35},
    "共感性": {"mean": 5.52, "std": 0.61},
    "意外性": {"mean": 5.45, "std": 0.52},
    "生成品質": {"mean": 8.46, "std": 0.56},
    "educational_value": {"mean": 5.55, "std": 0.52},
    "story_quality": {"mean": 6.70, "std": 0.45},
    "factual_density": {"mean": 9.57, "std": 1.05},
}

# LLMの想定分布（観測値ベース）
LLM_OBSERVED_STATS = {
    "mean": 7.0,
    "std": 1.0,  # 改善プロンプトで分散拡大を期待
}


# Phase 7C: エピソード特性検出用キーワード
EMOTION_KEYWORDS = ["涙", "感動", "喜び", "悲しみ", "怒り", "恐怖", "驚き", "愛", "憎しみ", "希望", "絶望"]
EDUCATIONAL_KEYWORDS_EXTENDED = ["学んだ", "教訓", "気づき", "発見", "理解", "知識", "経験から", "成長"]
STORY_KEYWORDS = ["物語", "ドラマ", "展開", "クライマックス", "転機", "運命"]


def detect_episode_characteristics(episode_text: str) -> Dict[str, bool]:
    """
    Phase 7C: エピソードの特性を検出

    エピソードテキストを分析し、各特性の有無を判定。
    この結果に基づいて動的に重みを調整する。

    Args:
        episode_text: エピソードテキスト

    Returns:
        特性フラグの辞書
    """
    characteristics = {
        "has_numbers": False,  # 数値・年号が多い
        "has_emotions": False,  # 感情表現が多い
        "has_dialogue": False,  # 対話・引用がある
        "has_educational": False,  # 教育的内容が含まれる
        "has_story_elements": False,  # 物語的要素がある
        "is_short": False,  # 短いエピソード
        "is_long": False,  # 長いエピソード
    }

    # 数値・年号の検出
    year_count = len(re.findall(r"(19|20)\d{2}年?", episode_text))
    number_count = len(re.findall(r"\d+[歳回位人件万億円ドル%]", episode_text))
    characteristics["has_numbers"] = (year_count + number_count) >= 3

    # 感情表現の検出
    emotion_count = sum(1 for kw in EMOTION_KEYWORDS if kw in episode_text)
    characteristics["has_emotions"] = emotion_count >= 2

    # 対話・引用の検出
    dialogue_count = episode_text.count("「") + episode_text.count("『")
    characteristics["has_dialogue"] = dialogue_count >= 2

    # 教育的内容の検出
    edu_count = sum(1 for kw in EDUCATIONAL_KEYWORDS_EXTENDED if kw in episode_text)
    characteristics["has_educational"] = edu_count >= 2

    # 物語的要素の検出
    story_count = sum(1 for kw in STORY_KEYWORDS if kw in episode_text)
    characteristics["has_story_elements"] = story_count >= 1

    # テキスト長
    text_len = len(episode_text)
    characteristics["is_short"] = text_len < 200
    characteristics["is_long"] = text_len > 500

    return characteristics


def get_dynamic_weights(episode_data: Dict) -> Dict[str, tuple]:
    """
    Phase 7C: エピソード特性に応じた動的重み決定

    エピソードの内容を分析し、各軸の評価にルールベースとLLMの
    どちらを重視すべきかを動的に決定する。

    Args:
        episode_data: エピソードデータ（episode_textを含む）

    Returns:
        各軸の重み辞書 {軸名: (ルール重み, LLM重み)}
    """
    episode_text = str(episode_data.get("episode_text", ""))

    # 特性検出
    chars = detect_episode_characteristics(episode_text)

    # ベース重み（HYBRID_WEIGHTSのコピー）
    weights = {
        "記憶性": (0.6, 0.4),
        "共感性": (0.2, 0.8),
        "意外性": (0.5, 0.5),
        "生成品質": (0.9, 0.1),
        "educational_value": (0.4, 0.6),
        "story_quality": (0.4, 0.6),
        "factual_density": (1.0, 0.0),
    }

    # 特性に応じて重みを調整

    # 数値・年号が多い → factual_density・記憶性はルール重視
    if chars["has_numbers"]:
        weights["factual_density"] = (1.0, 0.0)  # ルール100%
        weights["記憶性"] = (0.7, 0.3)  # ルール重視強化

    # 感情表現が多い → 共感性・記憶性はLLM重視
    if chars["has_emotions"]:
        weights["共感性"] = (0.1, 0.9)  # LLM90%
        weights["記憶性"] = (0.4, 0.6)  # LLM重視

    # 対話・引用がある → story_qualityはLLM重視
    if chars["has_dialogue"]:
        weights["story_quality"] = (0.3, 0.7)  # LLM70%

    # 教育的内容が含まれる → educational_valueはLLM重視
    if chars["has_educational"]:
        weights["educational_value"] = (0.3, 0.7)  # LLM70%

    # 物語的要素がある → story_quality・意外性はLLM重視
    if chars["has_story_elements"]:
        weights["story_quality"] = (0.2, 0.8)  # LLM80%
        weights["意外性"] = (0.4, 0.6)  # LLM60%

    # 短いエピソード → ルール重視（LLMの判断材料が少ない）
    if chars["is_short"]:
        for axis in weights:
            rule_w, llm_w = weights[axis]
            # ルール重みを20%増加
            new_rule_w = min(1.0, rule_w + 0.2)
            new_llm_w = 1.0 - new_rule_w
            weights[axis] = (new_rule_w, new_llm_w)

    return weights


def calculate_hybrid_scores_dynamic(
    episode_data: Dict,
    llm_scores: Optional[Dict[str, float]] = None,
    use_dynamic_weights: bool = True,
) -> Dict[str, float]:
    """
    Phase 7C: 動的重み付きハイブリッドスコア計算

    エピソード特性に応じて重みを動的調整し、
    ルールベースとLLMスコアを統合。

    Args:
        episode_data: エピソードデータ
        llm_scores: LLM評価スコア（オプション）
        use_dynamic_weights: 動的重み調整を使用するか

    Returns:
        7軸のハイブリッドスコア辞書
    """
    # ルールベーススコア計算
    rule_scores = calculate_hybrid_rule_scores(episode_data)

    # 重み決定
    if use_dynamic_weights:
        weights = get_dynamic_weights(episode_data)
    else:
        weights = HYBRID_WEIGHTS

    # LLMスコアがない場合はルールベースのみ
    if llm_scores is None:
        return {axis: round(rule_scores.get(axis, 5), 1) for axis in weights.keys()}

    # 重み付き統合
    hybrid_scores = {}
    for axis, (rule_w, llm_w) in weights.items():
        rule_val = rule_scores.get(axis, 5)
        llm_val = llm_scores.get(axis, 7.0)
        hybrid_scores[axis] = round(rule_val * rule_w + llm_val * llm_w, 1)

    return hybrid_scores


def calibrate_llm_score(llm_score: float, axis: str) -> float:
    """
    Phase 7B: LLMスコアをルールベース分布に合わせてキャリブレーション

    LLMは7.0付近に集中する傾向があるため、
    Z-score正規化でターゲット分布に変換して識別力を維持。

    Args:
        llm_score: LLMが出力した生のスコア（1-10）
        axis: 評価軸名

    Returns:
        キャリブレーション済みスコア（1-10）
    """
    target = LLM_TARGET_STATS.get(axis, {"mean": 7.0, "std": 0.5})
    llm_stats = LLM_OBSERVED_STATS

    # Z-score正規化 → ターゲット分布に変換
    z_score = (llm_score - llm_stats["mean"]) / max(llm_stats["std"], 0.1)
    calibrated = target["mean"] + z_score * target["std"]

    return max(1.0, min(10.0, round(calibrated, 1)))


def parse_llm_response(response_text: str) -> Optional[Dict[str, float]]:
    """
    LLMレスポンスからJSONスコアを抽出

    Args:
        response_text: LLMの出力テキスト

    Returns:
        7軸スコアの辞書、パース失敗時はNone
    """
    import json

    # JSON部分を抽出（前後の説明文を除去）
    text = response_text.strip()

    # JSONブロックを探す
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1

    if start_idx == -1 or end_idx == 0:
        return None

    json_str = text[start_idx:end_idx]

    try:
        scores = json.loads(json_str)

        # 必須キーの検証
        required_keys = [
            "記憶性",
            "共感性",
            "意外性",
            "生成品質",
            "educational_value",
            "story_quality",
            "factual_density",
        ]
        for key in required_keys:
            if key not in scores:
                return None
            # 数値範囲の検証
            val = float(scores[key])
            if val < 1 or val > 10:
                scores[key] = max(1, min(10, val))
            else:
                scores[key] = val

        return scores

    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def evaluate_with_llm(
    episode_text: str,
    client=None,
    model: str = "claude-sonnet-4-20250514",
    calibrate: bool = True,
) -> Optional[Dict[str, float]]:
    """
    Phase 7A: LLMを使用してエピソードを7軸評価

    Args:
        episode_text: 評価対象のエピソードテキスト
        client: Anthropic APIクライアント（Noneの場合は新規作成）
        model: 使用するモデル名
        calibrate: スケール補正を適用するか

    Returns:
        7軸スコアの辞書、評価失敗時はNone
    """
    try:
        import anthropic
    except ImportError:
        print("Warning: anthropic package not installed")
        return None

    # クライアント作成
    if client is None:
        try:
            client = anthropic.Anthropic()
        except Exception as e:
            print(f"Warning: Failed to create Anthropic client: {e}")
            return None

    # プロンプト生成
    prompt = LLM_EVALUATION_PROMPT.format(episode_text=episode_text[:2000])  # 最大2000文字

    try:
        response = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        scores = parse_llm_response(response_text)

        if scores is None:
            return None

        # Phase 7B: スケール補正
        if calibrate:
            calibrated_scores = {}
            for axis, score in scores.items():
                calibrated_scores[axis] = calibrate_llm_score(score, axis)
            return calibrated_scores

        return scores

    except Exception as e:
        print(f"Warning: LLM evaluation failed: {e}")
        return None


def calculate_hybrid_scores_with_llm(
    episode_data: Dict,
    llm_client=None,
    use_llm: bool = True,
    calibrate: bool = True,
) -> Dict[str, float]:
    """
    Phase 7: LLM連携ハイブリッド評価

    LLM評価とルールベース評価を最適化された重みで統合。
    LLM評価が失敗した場合はルールベースにフォールバック。

    Args:
        episode_data: エピソードデータ
        llm_client: Anthropic APIクライアント
        use_llm: LLM評価を使用するか
        calibrate: LLMスコアのキャリブレーションを適用するか

    Returns:
        7軸のハイブリッドスコア辞書
    """
    # ルールベーススコア計算（常に実行）
    rule_scores = calculate_hybrid_rule_scores(episode_data)

    # LLM評価
    llm_scores = None
    if use_llm:
        episode_text = str(episode_data.get("episode_text", ""))
        if episode_text:
            llm_scores = evaluate_with_llm(
                episode_text,
                client=llm_client,
                calibrate=calibrate,
            )

    # LLMスコアがない場合はルールベースのみ
    if llm_scores is None:
        return {axis: round(rule_scores.get(axis, 5), 1) for axis in HYBRID_WEIGHTS.keys()}

    # 重み付き統合
    hybrid_scores = {}
    for axis, (rule_w, llm_w) in HYBRID_WEIGHTS.items():
        rule_val = rule_scores.get(axis, 5)
        llm_val = llm_scores.get(axis, 7.0)
        hybrid_scores[axis] = round(rule_val * rule_w + llm_val * llm_w, 1)

    return hybrid_scores


def batch_evaluate_with_llm(
    episodes: list,
    llm_client=None,
    calibrate: bool = True,
    progress_callback=None,
) -> list:
    """
    Phase 7: 複数エピソードのバッチLLM評価

    Args:
        episodes: エピソードデータのリスト
        llm_client: Anthropic APIクライアント
        calibrate: スケール補正を適用するか
        progress_callback: 進捗コールバック関数（index, total）

    Returns:
        7軸スコア辞書のリスト（評価失敗時はNone）
    """
    results = []

    for i, episode in enumerate(episodes):
        episode_text = str(episode.get("episode_text", ""))

        if episode_text:
            scores = evaluate_with_llm(
                episode_text,
                client=llm_client,
                calibrate=calibrate,
            )
        else:
            scores = None

        results.append(scores)

        if progress_callback:
            progress_callback(i + 1, len(episodes))

    return results
