#!/usr/bin/env python3
"""
RULE_177: 抽象表現自動検出（Abstract Expression Detection）

あいまいな表現を検出し、具体性を向上させる
- 「多くの」「さまざまな」などの抽象表現検出
- 具体性スコアの計算
- 修正提案の自動生成

評価基準:
✅ 具体的: 数値、固有名詞、具体的な事実が含まれる
❌ 抽象的: あいまいな表現、主観的な形容詞が多い

例:
- ❌ 「多くの賞を受賞」→ ✅ 「ノーベル賞を含む3つの賞を受賞」
- ❌ 「大きな影響を与えた」→ ✅ 「100万人の観客を動員」
- ❌ 「さまざまな分野で活躍」→ ✅ 「映画、音楽、執筆活動で活躍」
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class AbstractExpression:
    """抽象表現"""
    expression: str  # 検出された表現
    position: int  # テキスト内の位置
    category: str  # カテゴリ（量、程度、範囲等）
    suggestion: str  # 具体化の提案


class AbstractExpressionDetector:
    """
    抽象表現検出エンジン

    あいまいな表現を自動検出し、具体化を提案
    """

    # 量に関する抽象表現
    QUANTITY_EXPRESSIONS = [
        "多くの", "たくさんの", "多数の", "複数の", "いくつかの",
        "数多くの", "大量の", "少なくない", "相当数の"
    ]

    # 程度に関する抽象表現
    DEGREE_EXPRESSIONS = [
        "大きな", "小さな", "高い", "低い", "強い", "弱い",
        "深い", "浅い", "広い", "狭い", "長い", "短い",
        "大幅な", "わずかな", "著しい", "顕著な"
    ]

    # 範囲に関する抽象表現
    SCOPE_EXPRESSIONS = [
        "さまざまな", "多様な", "幅広い", "広範囲の", "多岐にわたる",
        "あらゆる", "すべての", "全般的な", "総合的な"
    ]

    # 評価に関する抽象表現
    EVALUATION_EXPRESSIONS = [
        "素晴らしい", "素晴らしく", "優れた", "卓越した", "傑出した",
        "画期的な", "革新的な", "斬新な", "独創的な",
        "重要な", "大切な", "貴重な", "価値ある"
    ]

    # 時間に関する抽象表現
    TIME_EXPRESSIONS = [
        "長年", "長い間", "しばらく", "最近", "近年",
        "当時", "その後", "やがて", "いつか"
    ]

    # 具体性を示すパターン（これらがあれば加点）
    CONCRETE_PATTERNS = {
        r'\d+年': 10,  # 年
        r'\d+月': 10,  # 月
        r'\d+日': 10,  # 日
        r'\d+人': 15,  # 人数
        r'\d+個': 15,  # 個数
        r'\d+回': 15,  # 回数
        r'\d+億': 20,  # 大きな数値（億）
        r'\d+万': 15,  # 数値（万）
        r'\d+歳': 10,  # 年齢
        r'\d+%': 15,   # パーセンテージ
    }

    def __init__(self):
        """初期化"""
        pass

    def detect_abstract_expressions(self, text: str) -> List[AbstractExpression]:
        """
        抽象表現を検出

        Args:
            text: 検査対象テキスト

        Returns:
            検出された抽象表現のリスト
        """
        abstracts = []

        # 量表現の検出
        for expr in self.QUANTITY_EXPRESSIONS:
            pos = text.find(expr)
            if pos != -1:
                abstracts.append(AbstractExpression(
                    expression=expr,
                    position=pos,
                    category="量",
                    suggestion="具体的な数値に置き換え（例: 3つの、10人の）"
                ))

        # 程度表現の検出
        for expr in self.DEGREE_EXPRESSIONS:
            pos = text.find(expr)
            if pos != -1:
                abstracts.append(AbstractExpression(
                    expression=expr,
                    position=pos,
                    category="程度",
                    suggestion="具体的な数値や比較対象を追加（例: 100万人の、前年比2倍の）"
                ))

        # 範囲表現の検出
        for expr in self.SCOPE_EXPRESSIONS:
            pos = text.find(expr)
            if pos != -1:
                abstracts.append(AbstractExpression(
                    expression=expr,
                    position=pos,
                    category="範囲",
                    suggestion="具体的な項目を列挙（例: 映画、音楽、執筆の3分野で）"
                ))

        # 評価表現の検出
        for expr in self.EVALUATION_EXPRESSIONS:
            pos = text.find(expr)
            if pos != -1:
                abstracts.append(AbstractExpression(
                    expression=expr,
                    position=pos,
                    category="評価",
                    suggestion="客観的事実に置き換え（例: ノーベル賞受賞、売上1位）"
                ))

        # 時間表現の検出
        for expr in self.TIME_EXPRESSIONS:
            pos = text.find(expr)
            if pos != -1:
                abstracts.append(AbstractExpression(
                    expression=expr,
                    position=pos,
                    category="時間",
                    suggestion="具体的な年月日を記載（例: 2021年、3年間）"
                ))

        return abstracts

    def calculate_concreteness_score(self, text: str) -> int:
        """
        具体性スコアを計算

        Args:
            text: 評価対象テキスト

        Returns:
            具体性スコア（0-100）
        """
        score = 50  # ベーススコア

        # 具体的なパターンのカウント
        concrete_count = 0
        for pattern, points in self.CONCRETE_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                score += len(matches) * points
                concrete_count += len(matches)

        # 抽象表現のペナルティ
        abstract_expressions = self.detect_abstract_expressions(text)
        abstract_count = len(abstract_expressions)
        score -= abstract_count * 10

        # 固有名詞の存在（大文字始まり、カタカナ等）
        proper_nouns = re.findall(r'[A-Z][a-z]+|[ァ-ヴー]+', text)
        score += min(len(proper_nouns) * 5, 20)

        score = max(0, min(score, 100))

        logger.info(f"📊 具体性スコア: {score}点 (具体的パターン: {concrete_count}個, 抽象表現: {abstract_count}個)")
        return score

    def evaluate(self, text: str, threshold: int = 60) -> Dict:
        """
        テキストの具体性を評価

        Args:
            text: 評価対象テキスト
            threshold: 合格基準スコア（デフォルト60点）

        Returns:
            評価結果
        """
        # 抽象表現を検出
        abstract_expressions = self.detect_abstract_expressions(text)

        # 具体性スコアを計算
        concreteness_score = self.calculate_concreteness_score(text)

        # 判定
        passed = concreteness_score >= threshold and len(abstract_expressions) <= 3

        # カテゴリ別集計
        category_count = {}
        for expr in abstract_expressions:
            category = expr.category
            if category not in category_count:
                category_count[category] = 0
            category_count[category] += 1

        return {
            "passed": passed,
            "concreteness_score": concreteness_score,
            "abstract_count": len(abstract_expressions),
            "abstract_expressions": [
                {
                    "expression": expr.expression,
                    "category": expr.category,
                    "suggestion": expr.suggestion
                }
                for expr in abstract_expressions
            ],
            "category_summary": category_count,
            "rule_id": "RULE_177",
            "rule_name": "抽象表現自動検出"
        }


# グローバル検出エンジン
abstract_detector = AbstractExpressionDetector()


def detect_abstract_expressions(text: str, threshold: int = 60) -> Dict:
    """
    抽象表現を検出（外部インターフェース）

    Args:
        text: 評価対象テキスト
        threshold: 合格基準スコア

    Returns:
        評価結果
    """
    return abstract_detector.evaluate(text, threshold)


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # テストケース
    test_cases = [
        {
            "name": "具体的な例（良い）",
            "text": "あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞した。2021年シーズン、投手として9勝、156奪三振、打者として46本塁打、100打点を記録。ベーブ・ルース以来100年ぶりの快挙として世界中のメディアが報じた。"
        },
        {
            "name": "抽象的な例（悪い）",
            "text": "あなたと同じ年齢のとき、素晴らしい活躍をした。多くの賞を受賞し、さまざまな分野で大きな影響を与えた。長年にわたる努力が実を結び、高い評価を得た。"
        },
        {
            "name": "中間的な例",
            "text": "あなたと同じ35歳のとき、重要な発見をした。この研究は多くの科学者に影響を与え、いくつかの賞を受賞した。"
        }
    ]

    print("=" * 80)
    print("RULE_177: 抽象表現自動検出 - テスト実行")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['name']}")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = detect_abstract_expressions(test["text"])

        status = "✅ 具体的" if result["passed"] else "❌ 抽象的"
        print(f"  {status}")
        print(f"  📊 具体性スコア: {result['concreteness_score']}点")
        print(f"  📝 抽象表現数: {result['abstract_count']}個")

        if result["abstract_expressions"]:
            print(f"  🔍 検出された抽象表現:")
            for expr in result["abstract_expressions"]:
                print(f"     - 「{expr['expression']}」[{expr['category']}]")
                print(f"       提案: {expr['suggestion']}")

        if result["category_summary"]:
            print(f"  📋 カテゴリ別集計: {result['category_summary']}")

        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
