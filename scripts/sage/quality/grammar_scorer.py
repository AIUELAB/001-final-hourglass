"""
Grammar Quality Scorer

ルールベースの文法品質スコアラー（LLM非依存）。
文の完結性、形式一貫性、文構造をチェックしてスコアを算出。
"""

import re


# 常体の文末パターン（違反対象）
PLAIN_ENDINGS = [
    "た",
    "だ",
    "である",
    "ある",
    "いた",
    "った",
    "のだ",
]

# 述語として有効な文末パターン（丁寧語）
VALID_ENDINGS = [
    "ました",
    "でした",
    "です",
    "ます",
    "ません",
    "ございます",
    "ございました",
    "でしょう",
    "ましょう",
    "ください",
    "いたします",
    "おります",
    "なります",
    "ています",
    "ていました",
    "ておりました",
    "てまいりました",
    "を果たしました",
    "を遂げました",
    "を成し遂げました",
    "を残しました",
]

# 体言止めで頻出する名詞（taigendome.pyと共通だが、ここではスコア計算用に使う）
NOUN_ENDINGS = [
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
    "誕生",
    "復活",
    "飛躍",
    "成長",
    "進化",
    "変革",
    "革新",
]


def _extract_sentences(text: str) -> list[str]:
    """テキストを文に分割（「」内の。は無視）"""
    sentences = []
    current = []
    in_quote = False

    for char in text:
        if char == "「":
            in_quote = True
            current.append(char)
        elif char == "」":
            in_quote = False
            current.append(char)
        elif char == "。" and not in_quote:
            current.append(char)
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []
        else:
            current.append(char)

    remaining = "".join(current).strip()
    if remaining:
        sentences.append(remaining)

    return sentences


def _is_noun_ending(sentence: str) -> bool:
    """文が名詞で終わっているかチェック"""
    clean = sentence.rstrip("。").strip()
    if not clean:
        return False
    for noun in NOUN_ENDINGS:
        if clean.endswith(noun):
            return True
    return False


def _is_plain_ending(sentence: str) -> bool:
    """文が常体で終わっているかチェック（違反検出用）"""
    clean = sentence.rstrip("。").strip()
    if not clean:
        return False
    # 丁寧語を先に除外（「しました」等は常体判定しない）
    for ending in VALID_ENDINGS:
        if clean.endswith(ending):
            return False
    for ending in PLAIN_ENDINGS:
        if clean.endswith(ending):
            return True
    return False


class GrammarQualityScorer:
    """
    文法品質スコアラー

    ルールベースでエピソードテキストの文法品質を評価。
    - 文の完結性チェック（40%）
    - 形式一貫性チェック（30%）
    - 文構造チェック（30%）

    出力範囲: 1.0-10.0
    """

    def calculate(self, text: str) -> float:
        """
        文法品質スコアを計算

        Args:
            text: エピソードテキスト

        Returns:
            float: スコア（1.0-10.0）
        """
        if not text:
            return 5.0

        sentences = _extract_sentences(text)
        if not sentences:
            return 5.0

        # 1. 文の完結性チェック（40%）- 10点満点
        completeness_score = self._check_completeness(sentences)

        # 2. 形式一貫性チェック（30%）- 10点満点
        consistency_score = self._check_consistency(sentences)

        # 3. 文構造チェック（30%）- 10点満点
        structure_score = self._check_structure(sentences, text)

        # 加重平均
        total = completeness_score * 0.4 + consistency_score * 0.3 + structure_score * 0.3

        return max(1.0, min(10.0, total))

    def _check_completeness(self, sentences: list[str]) -> float:
        """
        文の完結性チェック
        全文が述語（動詞/形容詞/助動詞）で終わっているか。
        体言止め1件あたり-1.5点。
        """
        score = 10.0
        noun_ending_count = 0

        for sentence in sentences:
            if _is_noun_ending(sentence):
                noun_ending_count += 1

        # 体言止め1件あたり-1.5点
        score -= noun_ending_count * 1.5

        return max(1.0, score)

    def _check_consistency(self, sentences: list[str]) -> float:
        """
        形式一貫性チェック
        常体混入率。常体1文あたり-1.0点。
        """
        score = 10.0
        plain_count = 0

        for sentence in sentences:
            if _is_plain_ending(sentence):
                plain_count += 1

        # 常体1文あたり-1.0点
        score -= plain_count * 1.0

        return max(1.0, score)

    def _check_structure(self, sentences: list[str], text: str) -> float:
        """
        文構造チェック
        最低文長、文断片の検出。
        """
        score = 10.0

        # 極端に短い文（10文字未満）の検出
        short_count = sum(1 for s in sentences if len(s.rstrip("。")) < 10)
        score -= short_count * 0.5

        # 全体の文字数が少なすぎる場合
        if len(text) < 100:
            score -= 2.0

        # 文の数が少なすぎる場合（2文以下）
        if len(sentences) <= 2:
            score -= 1.0

        return max(1.0, score)
