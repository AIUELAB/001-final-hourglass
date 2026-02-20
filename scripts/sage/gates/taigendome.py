"""
体言止めゲート - 文末の名詞終了を検出

体言止め（名詞で文が終わる不完全な文）を検出し、品質違反として報告する。
エピソードテキストは常体（だ・である調）で完結する文で構成されるべき。
"""

import re
from dataclasses import dataclass, field


@dataclass
class TaigendomeCheckResult:
    """体言止めチェック結果"""

    passed: bool
    violation_count: int = 0
    warning_count: int = 0
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""


# 体言止めで頻出する名詞（文末にこれが来たら違反）
NOUN_ENDINGS: list[str] = [
    # 抽象的な物語調名詞
    "瞬間",
    "存在",
    "時代",
    "遺産",
    "挑戦",
    "転機",
    "始まり",
    "象徴",
    "頂点",
    "覚悟",
    "軌跡",
    "物語",
    "到達点",
    "出発点",
    "分岐点",
    "出来事",
    "歴史",
    "証",
    "証明",
    "偉業",
    "功績",
    "足跡",
    "結晶",
    "集大成",
    "原点",
    "礎",
    "旅立ち",
    "決意",
    "覚醒",
    # 人物評価系
    "革命児",
    "先駆者",
    "開拓者",
    "巨人",
    "天才",
    "鬼才",
    "パイオニア",
    "レジェンド",
    "マエストロ",
    "カリスマ",
    "第一人者",
    "立役者",
    "功労者",
    "救世主",
    # 感情・状態系
    "感動",
    "衝撃",
    "驚き",
    "喜び",
    "苦悩",
    "葛藤",
    "決断",
    "情熱",
    "執念",
    "信念",
    "意志",
    "誇り",
    # 事象系
    "誕生",
    "復活",
    "飛躍",
    "成長",
    "進化",
    "変革",
    "革新",
    "挫折",
    "苦難",
    "試練",
    "逆境",
]

# 体言止めパターン（正規表現）
NOUN_ENDING_PATTERNS: list[str] = [
    r"という[^。]{1,6}。$",  # 「〜という存在。」
    r"への[^。]{1,8}。$",  # 「〜への挑戦。」
    r"としての[^。]{1,8}。$",  # 「〜としての証。」
    r"を刻んだ[^。]{1,6}。$",  # 「〜を刻んだ瞬間。」
    r"た[^。]{1,4}。$",  # 「〜た瞬間。」（名詞が短い場合）
]


def _is_inside_quote(text: str, pos: int) -> bool:
    """指定位置が「」引用内かどうかを判定"""
    open_count = 0
    for i in range(pos):
        if text[i] == "\u300c":
            open_count += 1
        elif text[i] == "\u300d":
            open_count -= 1
    return open_count > 0


def _extract_sentences(text: str) -> list[str]:
    """テキストを文に分割（「」内の。は無視）"""
    sentences = []
    current = []
    in_quote = False

    for char in text:
        if char == "\u300c":
            in_quote = True
            current.append(char)
        elif char == "\u300d":
            in_quote = False
            current.append(char)
        elif char == "\u3002" and not in_quote:
            current.append(char)
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []
        else:
            current.append(char)

    # 最後の文（。で終わらない場合）
    remaining = "".join(current).strip()
    if remaining:
        sentences.append(remaining)

    return sentences


def _check_noun_ending(sentence: str) -> tuple[bool, str]:
    """
    文が名詞で終わっているかチェック

    Returns:
        (is_noun_ending, matched_noun): 体言止めかどうかと、マッチした名詞
    """
    # 。を除去
    clean = sentence.rstrip("\u3002").strip()

    if not clean:
        return False, ""

    # NOUN_ENDINGS リストでチェック
    for noun in NOUN_ENDINGS:
        if clean.endswith(noun):
            # ただし、直前が助動詞/動詞活用語尾なら除外
            prefix = clean[: -len(noun)]
            if prefix and prefix[-1] in ("\u3060", "\u305f", "\u308b", "\u306e", "\u306a"):
                # 「〜だ存在」「〜た瞬間」 → 体言止め
                # ただし「〜した」「〜なった」は述語で終わっている
                pass
            return True, noun

    # パターンマッチでもチェック
    for pattern in NOUN_ENDING_PATTERNS:
        if re.search(pattern, sentence):
            match = re.search(pattern, sentence)
            if match:
                return True, match.group(0).rstrip("\u3002")

    return False, ""


def check_taigendome(episode_text: str) -> TaigendomeCheckResult:
    """
    エピソードテキストの体言止めをチェック

    - 最終文が名詞で終わっていれば REJECT（ブロッキングゲート）
    - 中間文の体言止めは warning のみ（スコアで減点）
    - 引用「」内は除外

    Args:
        episode_text: チェック対象のテキスト

    Returns:
        TaigendomeCheckResult: チェック結果
    """
    if not episode_text:
        return TaigendomeCheckResult(
            passed=True,
            message="テキストなし",
        )

    sentences = _extract_sentences(episode_text)

    if not sentences:
        return TaigendomeCheckResult(
            passed=True,
            message="文なし",
        )

    violations = []
    warnings = []

    for i, sentence in enumerate(sentences):
        is_last = i == len(sentences) - 1
        is_noun_ending, matched = _check_noun_ending(sentence)

        if is_noun_ending:
            truncated = sentence[:30] + "..." if len(sentence) > 30 else sentence
            if is_last:
                # 最終文の体言止め → REJECT
                violations.append(f"最終文の体言止め: 「{truncated}」(名詞: {matched})")
            else:
                # 中間文の体言止め → warning
                warnings.append(f"中間文の体言止め: 「{truncated}」(名詞: {matched})")

    if violations:
        return TaigendomeCheckResult(
            passed=False,
            violation_count=len(violations),
            warning_count=len(warnings),
            violations=violations,
            warnings=warnings,
            message=f"体言止め違反: {len(violations)}件 (最終文で名詞終了)",
        )

    return TaigendomeCheckResult(
        passed=True,
        violation_count=0,
        warning_count=len(warnings),
        violations=[],
        warnings=warnings,
        message=f"体言止めチェック通過 (警告: {len(warnings)}件)" if warnings else "体言止めチェック通過",
    )


# ゲートインターフェース（他のゲートとの統一）
def gate_check(episode_text: str, **kwargs) -> dict:
    """
    ゲート統一インターフェース
    """
    result = check_taigendome(episode_text)
    return {
        "passed": result.passed,
        "gate_name": "taigendome",
        "message": result.message,
        "details": {
            "violation_count": result.violation_count,
            "warning_count": result.warning_count,
            "violations": result.violations[:5],
            "warnings": result.warnings[:5],
        },
    }
