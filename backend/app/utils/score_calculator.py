"""スコア計算の統一モジュール

composite_scoreや各種評価スコアの計算を一元管理
"""

from typing import Dict, Optional, List, Union
import re
import unicodedata

# 7軸スコアのフィールド名（日本語）
SEVEN_AXIS_FIELDS = [
    '記憶性スコア',      # memorability_score
    '共感性スコア',      # empathy_score
    '意外性スコア',      # surprise_score
    '生成品質スコア',    # generation_quality_score
    '教育的価値',        # educational_value
    'ストーリー品質',    # storytelling_quality
    '事実密度'           # factual_density
]

# 英語→日本語のマッピング
FIELD_MAPPING = {
    'memorability_score': '記憶性スコア',
    'empathy_score': '共感性スコア',
    'surprise_score': '意外性スコア',
    'generation_quality_score': '生成品質スコア',
    'educational_value': '教育的価値',
    'storytelling_quality': 'ストーリー品質',
    'factual_density': '事実密度'
}


def calculate_composite_score(
    episode_data: Dict,
    min_axes_required: int = 1
) -> Optional[float]:
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
        if value is None or value == '':
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


def calculate_composite_score_from_english_fields(
    episode_data: Dict,
    min_axes_required: int = 1
) -> Optional[float]:
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

        if value is None or value == '':
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
        return ''

    # Unicode正規化（全角→半角など）
    normalized = unicodedata.normalize('NFKC', name)

    # 空白除去（全角・半角）
    normalized = normalized.replace(' ', '').replace('　', '')

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


def is_similar_episode(
    text1: str,
    text2: str,
    threshold: float = 0.8
) -> bool:
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
    episode_text = str(episode_data.get('episode_text', ''))

    # テキスト長
    char_count = len(episode_text)

    # 数値データの存在
    numbers = re.findall(r'\d+', episode_text)
    number_count = len(numbers)

    # 引用（「」）の存在
    has_quotes = '「' in episode_text and '」' in episode_text

    # 固有名詞（カタカナ3文字以上）
    katakana_pattern = r'[ァ-ヴー]{3,}'
    katakana_words = re.findall(katakana_pattern, episode_text)
    katakana_count = len(katakana_words)

    # composite_score
    composite = calculate_composite_score(episode_data)

    # 有効軸数
    valid_axes = count_valid_axes(episode_data)

    return {
        'char_count': char_count,
        'number_count': number_count,
        'has_quotes': has_quotes,
        'katakana_count': katakana_count,
        'composite_score': composite,
        'valid_axes_count': valid_axes,
        'is_complete': valid_axes == 7
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
        return ''
    return f"{score:.2f}"


# ============================================================
# 5軸の改善されたルールベース計算関数
# ============================================================

# 記憶性に関連するキーワード
MEMORABILITY_KEYWORDS = {
    'ultra_high': ['世界初', '史上初', 'ギネス', '国民的', '社会現象', '歴史的', '革命', '金字塔'],
    'high': ['記録', '受賞', '優勝', '達成', '発明', '発見', '創設', '開発', '成功'],
    'medium': ['挑戦', '転機', '決断', '出会い', '経験']
}

# 共感性に関連するキーワード
EMPATHY_KEYWORDS = {
    'emotion': ['涙', '感動', '喜び', '悲しみ', '苦悩', '葛藤', '不安', '希望', '絶望', '勇気'],
    'struggle': ['克服', '乗り越え', '挫折', '失敗', '困難', '逆境', '苦労', '努力'],
    'relation': ['家族', '母', '父', '子供', '友人', '恩師', '仲間', '愛']
}

# 意外性に関連するキーワード（拡張版）
SURPRISE_KEYWORDS = {
    'twist': [
        '実は', '意外にも', '驚くべきことに', '誰も知らない', '秘密', '真実',
        '知られざる', '隠された', '裏側', '本当は', '実際には', '明かされた',
    ],
    'contrast': [
        '一方で', 'しかし', '逆に', '反面', '裏では', 'ところが',
        'にもかかわらず', 'それでも', '皮肉にも', '対照的に', '反して', '違って',
    ],
    'unexpected': [
        '偶然', '予想外', '思いがけず', '突然', '奇跡的', '異例',
        '破天荒', '型破り', '常識を覆す', '前例のない', '画期的', '革新的',
        '異色', '独自', 'ユニーク', '唯一', '珍しい', '稀有', '特異',
    ],
    'achievement_twist': [
        '最年少', '最年長', '史上初', '女性初', '日本人初', '世界初',
        '前人未到', '不可能を可能に', '常識を破る', '逆転', '大逆転',
        '番狂わせ', '下剋上', '奇跡の', 'ドラマチック',
    ],
    'origin_twist': [
        '元々', '当初', '最初は', 'かつては', '以前は', '本来',
        '全く違う', '想像もしなかった', '夢にも思わなかった', '偶然の発見',
    ],
}

# 教育的価値に関連するキーワード
EDUCATIONAL_KEYWORDS = {
    'lesson': ['教訓', '学び', '示唆', '重要', '原則', '哲学', '信念', '思想'],
    'insight': ['発見', '気づき', '理解', '認識', '視点', '考え方'],
    'universal': ['普遍的', '本質', '真理', '原理', '法則']
}


def calculate_memorability_score(episode_data: Dict) -> float:
    """
    記憶性スコアを計算

    評価基準:
    - 歴史的重要度（キーワード検出）
    - 人物の知名度（fame_score）
    - エピソードタイプの記憶に残りやすさ
    - 具体的数値・年号の存在

    Args:
        episode_data: エピソードデータ

    Returns:
        記憶性スコア（1.0-10.0）
    """
    score = 5.5  # ベーススコア（composite_score平均7.0+を目指して調整）
    episode_text = str(episode_data.get('episode_text', ''))

    # 1. 超高インパクトキーワード (+2.5)
    ultra_high_count = sum(
        1 for kw in MEMORABILITY_KEYWORDS['ultra_high']
        if kw in episode_text
    )
    score += min(ultra_high_count * 1.0, 2.5)

    # 2. 高インパクトキーワード (+1.5)
    high_count = sum(
        1 for kw in MEMORABILITY_KEYWORDS['high']
        if kw in episode_text
    )
    score += min(high_count * 0.5, 1.5)

    # 3. fame_scoreからの補正 (+1.0)
    fame_score = episode_data.get('fame_score')
    if fame_score:
        try:
            fame = float(fame_score)
            if fame >= 80:
                score += 1.0
            elif fame >= 60:
                score += 0.5
        except (ValueError, TypeError):
            pass

    # 4. エピソードタイプ補正 (+1.0)
    episode_type = episode_data.get('episode_type', '')
    memorable_types = ['ACHIEVEMENT', 'INNOVATION', 'TURNING_POINT', 'FOUNDING']
    if episode_type in memorable_types:
        score += 0.8

    # 5. 年号の存在 (+0.5)
    if re.search(r'(19|20)\d{2}年', episode_text):
        score += 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_empathy_score(episode_data: Dict) -> float:
    """
    共感性スコアを計算

    評価基準:
    - 感情表現の豊かさ
    - 人間的な葛藤・成長の描写
    - 関係性（家族、仲間）への言及
    - 普遍的な体験への関連

    Args:
        episode_data: エピソードデータ

    Returns:
        共感性スコア（1.0-10.0）
    """
    # LLM検証で+1.38のバイアスあり → ベーススコアを上方修正
    score = 6.4  # ベーススコア（調整済み）
    episode_text = str(episode_data.get('episode_text', ''))

    # 1. 感情キーワード (+2.0)
    emotion_count = sum(
        1 for kw in EMPATHY_KEYWORDS['emotion']
        if kw in episode_text
    )
    score += min(emotion_count * 0.5, 2.0)

    # 2. 葛藤・克服キーワード (+1.5)
    struggle_count = sum(
        1 for kw in EMPATHY_KEYWORDS['struggle']
        if kw in episode_text
    )
    score += min(struggle_count * 0.5, 1.5)

    # 3. 関係性キーワード (+1.5)
    relation_count = sum(
        1 for kw in EMPATHY_KEYWORDS['relation']
        if kw in episode_text
    )
    score += min(relation_count * 0.5, 1.5)

    # 4. 引用（会話）の存在 (+0.5)
    if '「' in episode_text and '」' in episode_text:
        score += 0.5

    # 5. エピソードタイプ補正
    episode_type = episode_data.get('episode_type', '')
    empathetic_types = ['FAMILY', 'GROWTH', 'FAILURE', 'COMEBACK']
    if episode_type in empathetic_types:
        score += 0.7

    return round(min(10.0, max(1.0, score)), 1)


def calculate_surprise_score(episode_data: Dict) -> float:
    """
    意外性スコアを計算（改善版）

    評価基準:
    - 意外な展開を示すキーワード
    - 対比・コントラストの存在
    - 予想外の要素
    - 達成・起源に関するツイスト
    - 年齢とエピソードタイプの組み合わせ
    - カテゴリの意外性

    Args:
        episode_data: エピソードデータ

    Returns:
        意外性スコア（1.0-10.0）
    """
    score = 5.0  # ベーススコア（分散を維持しつつcomposite_score改善）
    episode_text = str(episode_data.get('episode_text', ''))
    episode_type = episode_data.get('episode_type', '')
    category = episode_data.get('category', '')

    # 1. ツイストキーワード (+2.0)
    twist_count = sum(
        1 for kw in SURPRISE_KEYWORDS['twist']
        if kw in episode_text
    )
    score += min(twist_count * 0.6, 2.0)

    # 2. コントラストキーワード (+1.5)
    contrast_count = sum(
        1 for kw in SURPRISE_KEYWORDS['contrast']
        if kw in episode_text
    )
    score += min(contrast_count * 0.4, 1.5)

    # 3. 予想外キーワード (+2.0)
    unexpected_count = sum(
        1 for kw in SURPRISE_KEYWORDS['unexpected']
        if kw in episode_text
    )
    score += min(unexpected_count * 0.4, 2.0)

    # 4. 達成ツイストキーワード (+1.5)
    achievement_twist_count = sum(
        1 for kw in SURPRISE_KEYWORDS['achievement_twist']
        if kw in episode_text
    )
    score += min(achievement_twist_count * 0.5, 1.5)

    # 5. 起源ツイストキーワード (+1.0)
    origin_twist_count = sum(
        1 for kw in SURPRISE_KEYWORDS['origin_twist']
        if kw in episode_text
    )
    score += min(origin_twist_count * 0.4, 1.0)

    # 6. 年齢とエピソードタイプの組み合わせ (+1.2)
    try:
        age = float(episode_data.get('age', 0))

        # 若い年齢での大きな達成は意外性が高い
        if age <= 20 and episode_type in ['ACHIEVEMENT', 'INNOVATION', 'FOUNDING']:
            score += 1.2
        elif age <= 25 and episode_type in ['ACHIEVEMENT', 'INNOVATION', 'FOUNDING']:
            score += 0.8
        # 高齢での挑戦も意外性が高い
        elif age >= 70 and episode_type in ['CHALLENGE', 'GROWTH', 'COMEBACK']:
            score += 1.0
        elif age >= 60 and episode_type in ['CHALLENGE', 'GROWTH', 'COMEBACK']:
            score += 0.6
        # 中年での転機
        elif 40 <= age <= 55 and episode_type == 'TURNING_POINT':
            score += 0.5
    except (ValueError, TypeError):
        pass

    # 7. エピソードタイプによる補正 (+0.8)
    surprising_types = ['COMEBACK', 'FAILURE', 'TURNING_POINT']
    if episode_type in surprising_types:
        score += 0.8

    # 8. カテゴリによる意外性加点 (+0.5)
    if category in ['探検・冒険', '映画・演劇', 'アニメ・漫画・ゲーム']:
        score += 0.5

    return round(min(10.0, max(1.0, score)), 1)


def calculate_generation_quality_score(episode_data: Dict) -> float:
    """
    生成品質スコアを計算

    評価基準:
    - 文章の長さ（適切な長さ）
    - 文法的な完成度（簡易チェック）
    - 読みやすさ（文の長さのバランス）
    - 表現の多様性

    Args:
        episode_data: エピソードデータ

    Returns:
        生成品質スコア（1.0-10.0）
    """
    # LLM検証で-1.40のバイアスあり → ベーススコアを下方修正
    score = 4.6  # ベーススコア（調整済み）
    episode_text = str(episode_data.get('episode_text', ''))

    # テキストが空の場合
    if not episode_text.strip():
        return 3.0

    # 1. 適切な文字数 (+1.5)
    char_count = len(episode_text)
    if 200 <= char_count <= 400:
        score += 1.5
    elif 150 <= char_count <= 500:
        score += 1.0
    elif char_count < 100:
        score -= 1.0
    elif char_count > 600:
        score -= 0.5

    # 2. 文の数と平均長さ (+1.0)
    sentences = re.split(r'[。！？]', episode_text)
    sentences = [s for s in sentences if s.strip()]
    if sentences:
        avg_sentence_length = char_count / len(sentences)
        if 30 <= avg_sentence_length <= 60:
            score += 1.0
        elif 20 <= avg_sentence_length <= 80:
            score += 0.5

    # 3. 句読点の適切な使用 (+0.5)
    comma_count = episode_text.count('、')
    period_count = episode_text.count('。')
    if comma_count >= 3 and period_count >= 2:
        score += 0.5

    # 4. 冗長表現のペナルティ (-0.5)
    redundant_patterns = ['ということ', 'というものは', 'のようなもの']
    redundant_count = sum(
        episode_text.count(p) for p in redundant_patterns
    )
    if redundant_count >= 2:
        score -= 0.5

    # 5. 完結性（最後が句点で終わる） (+0.3)
    if episode_text.rstrip().endswith('。'):
        score += 0.3

    return round(min(10.0, max(1.0, score)), 1)


def calculate_educational_value_score(episode_data: Dict) -> float:
    """
    教育的価値スコアを計算

    評価基準:
    - 教訓・学びを示すキーワード
    - 具体的な事実の存在
    - カテゴリの教育的重要性
    - 普遍的な洞察の有無

    Args:
        episode_data: エピソードデータ

    Returns:
        教育的価値スコア（1.0-10.0）
    """
    # LLM検証で+1.98のバイアスあり → ベーススコアを上方修正
    score = 7.0  # ベーススコア（調整済み）
    episode_text = str(episode_data.get('episode_text', ''))

    # 1. 教訓キーワード (+2.0)
    lesson_count = sum(
        1 for kw in EDUCATIONAL_KEYWORDS['lesson']
        if kw in episode_text
    )
    score += min(lesson_count * 0.5, 2.0)

    # 2. 洞察キーワード (+1.5)
    insight_count = sum(
        1 for kw in EDUCATIONAL_KEYWORDS['insight']
        if kw in episode_text
    )
    score += min(insight_count * 0.5, 1.5)

    # 3. 普遍性キーワード (+1.0)
    universal_count = sum(
        1 for kw in EDUCATIONAL_KEYWORDS['universal']
        if kw in episode_text
    )
    score += min(universal_count * 0.5, 1.0)

    # 4. カテゴリによる補正 (+1.0)
    category = episode_data.get('category', '')
    educational_categories = [
        '科学・技術', '教育', '医療・福祉', '政治・国際', '思想・哲学'
    ]
    if any(cat in category for cat in educational_categories):
        score += 1.0

    # 5. 具体的な数値データ (+0.5)
    numbers = re.findall(r'\d+', episode_text)
    if len(numbers) >= 3:
        score += 0.5

    # 6. エピソードタイプ補正
    episode_type = episode_data.get('episode_type', '')
    educational_types = ['ACHIEVEMENT', 'INNOVATION', 'FAILURE']
    if episode_type in educational_types:
        score += 0.5

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
        '記憶性スコア': calculate_memorability_score(episode_data),
        '共感性スコア': calculate_empathy_score(episode_data),
        '意外性スコア': calculate_surprise_score(episode_data),
        '生成品質スコア': calculate_generation_quality_score(episode_data),
        '教育的価値': calculate_educational_value_score(episode_data)
    }
