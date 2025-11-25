#!/usr/bin/env python3
"""
内在的価値評価システム
表面的なキーワードではなく、事実の本質的な価値を評価する
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class IntrinsicValue:
    """内在的価値の評価結果"""
    memorability: float  # 記憶性 (0-10)
    empathy: float      # 共感性 (0-10)
    surprise: float     # 意外性 (0-10)
    education: float    # 教育的価値 (0-10)
    reasons: Dict[str, List[str]]  # 評価理由

class IntrinsicValueEvaluator:
    """事実の内在的価値を評価するシステム"""

    def __init__(self):
        # 事実パターンとその内在的価値
        self.fact_patterns = {
            "転機・決断": {
                "patterns": ["退職", "転身", "決断", "選んだ", "捨てて", "離れ"],
                "values": {"empathy": 8, "education": 8, "surprise": 6}
            },
            "若年での達成": {
                "patterns": ["歳で", "若さで", "最年少", "歳にして"],
                "values": {"surprise": 9, "memorability": 8, "education": 7}
            },
            "困難の克服": {
                "patterns": ["克服", "乗り越え", "闘病", "怪我を抱え", "逆境"],
                "values": {"empathy": 9, "education": 9, "surprise": 7}
            },
            "社会的影響": {
                "patterns": ["確立", "革命", "定着", "生み出した", "切り開いた"],
                "values": {"education": 9, "memorability": 8}
            },
            "努力の過程": {
                "patterns": ["年間", "毎日", "続けた", "積み重ね", "継続"],
                "values": {"empathy": 8, "education": 9}
            },
            "対比・逆転": {
                "patterns": ["にもかかわらず", "一方で", "逆に", "むしろ"],
                "values": {"surprise": 9, "memorability": 7}
            }
        }

        # 文脈による価値修正
        self.context_modifiers = {
            "年齢_若い": {"age_under": 25, "bonus": {"surprise": 2, "memorability": 1}},
            "年齢_高齢": {"age_over": 60, "bonus": {"surprise": 2, "education": 1}},
            "規模_大": {"numbers": [1000000, "億", "万人"], "bonus": {"memorability": 2}},
            "期間_長": {"patterns": ["年間", "年続", "生涯"], "bonus": {"education": 2}}
        }

    def evaluate(self, episode_text: str, age: int, person_name: str) -> IntrinsicValue:
        """エピソードの内在的価値を評価"""

        # 初期値
        scores = {
            "memorability": 5.0,
            "empathy": 5.0,
            "surprise": 5.0,
            "education": 5.0
        }
        reasons = {
            "memorability": [],
            "empathy": [],
            "surprise": [],
            "education": []
        }

        # 1. 事実パターンによる評価
        for category, config in self.fact_patterns.items():
            if self._contains_pattern(episode_text, config["patterns"]):
                for value_type, score in config["values"].items():
                    scores[value_type] = max(scores[value_type], score)
                    reasons[value_type].append(f"{category}の要素を含む")

        # 2. 文脈による修正
        self._apply_context_modifiers(episode_text, age, scores, reasons)

        # 3. 暗黙的価値の認識
        self._recognize_implicit_values(episode_text, scores, reasons)

        # 4. 相対的評価
        self._apply_relative_evaluation(episode_text, age, scores, reasons)

        # スコアを0-10の範囲に正規化
        for key in scores:
            scores[key] = min(10.0, max(0.0, scores[key]))

        return IntrinsicValue(
            memorability=scores["memorability"],
            empathy=scores["empathy"],
            surprise=scores["surprise"],
            education=scores["education"],
            reasons=reasons
        )

    def _contains_pattern(self, text: str, patterns: List[str]) -> bool:
        """テキストがパターンのいずれかを含むか確認"""
        return any(pattern in text for pattern in patterns)

    def _apply_context_modifiers(self, text: str, age: int, scores: Dict, reasons: Dict):
        """文脈による価値修正を適用"""

        # 年齢による修正
        if age < 25:
            scores["surprise"] += 2
            scores["memorability"] += 1
            reasons["surprise"].append(f"{age}歳という若さ")
            reasons["memorability"].append("若年での達成")
        elif age > 60:
            scores["surprise"] += 1
            scores["education"] += 1
            reasons["surprise"].append(f"{age}歳での活躍")
            reasons["education"].append("生涯現役の姿勢")

        # 数値の大きさによる修正
        large_numbers = re.findall(r'\d{4,}|\d+億|\d+万', text)
        if large_numbers:
            scores["memorability"] += 1
            reasons["memorability"].append(f"印象的な数値: {', '.join(large_numbers[:3])}")

    def _recognize_implicit_values(self, text: str, scores: Dict, reasons: Dict):
        """明示されていない暗黙的価値を認識"""

        # 選択と犠牲
        if "退職" in text and ("選んだ" in text or "道" in text):
            scores["empathy"] += 1
            scores["education"] += 1
            reasons["empathy"].append("人生の選択への共感")
            reasons["education"].append("夢を追う勇気の教訓")

        # 継続の価値
        if re.search(r'\d+年', text) and ("続" in text or "連続" in text):
            scores["education"] += 1
            reasons["education"].append("継続の重要性を示す")

        # パイオニア精神
        if "初" in text or "初めて" in text or "第一" in text:
            scores["surprise"] += 1
            scores["education"] += 1
            reasons["surprise"].append("前例のない挑戦")
            reasons["education"].append("開拓者としての価値")

    def _apply_relative_evaluation(self, text: str, age: int, scores: Dict, reasons: Dict):
        """相対的な評価を適用"""

        # 同世代との比較
        if "平均" in text or "一般" in text or "通常" in text:
            scores["surprise"] += 1
            reasons["surprise"].append("一般的な期待を超える")

        # 時代背景の考慮
        if "当時" in text or "その時代" in text:
            scores["education"] += 1
            reasons["education"].append("時代背景を考慮した価値")

def compare_evaluations(episode_text: str, age: int, person_name: str):
    """新旧の評価システムを比較"""

    evaluator = IntrinsicValueEvaluator()
    result = evaluator.evaluate(episode_text, age, person_name)

    # 旧システムのシミュレーション（キーワードベース）
    old_scores = {
        "memorability": 8 if re.search(r'\d{4,}', episode_text) else 3,
        "empathy": 8 if any(word in episode_text for word in ['涙', '感動', '喜び']) else 0,
        "surprise": 8 if any(word in episode_text for word in ['しかし', '実は', '意外']) else 0,
        "education": 8 if any(word in episode_text for word in ['証明', '教えてくれる', '大切さ']) else 3
    }

    print(f"\n【{person_name}（{age}歳）】の評価比較")
    print("\n◆ 旧システム（キーワードベース）:")
    print(f"  記憶性: {old_scores['memorability']}/10")
    print(f"  共感性: {old_scores['empathy']}/10 {'❌' if old_scores['empathy'] < 3 else '✅'}")
    print(f"  意外性: {old_scores['surprise']}/10 {'❌' if old_scores['surprise'] < 3 else '✅'}")
    print(f"  教育的価値: {old_scores['education']}/10")

    print("\n◆ 新システム（内在的価値評価）:")
    print(f"  記憶性: {result.memorability}/10")
    for reason in result.reasons['memorability']:
        print(f"    - {reason}")

    print(f"  共感性: {result.empathy}/10 {'✅' if result.empathy >= 5 else '⚠️'}")
    for reason in result.reasons['empathy']:
        print(f"    - {reason}")

    print(f"  意外性: {result.surprise}/10 {'✅' if result.surprise >= 5 else '⚠️'}")
    for reason in result.reasons['surprise']:
        print(f"    - {reason}")

    print(f"  教育的価値: {result.education}/10")
    for reason in result.reasons['education']:
        print(f"    - {reason}")

    # 総合評価
    old_total = sum(old_scores.values()) / 4
    new_total = (result.memorability + result.empathy + result.surprise + result.education) / 4

    print(f"\n総合評価:")
    print(f"  旧システム: {old_total:.1f}/10 {'❌ 不合格' if old_total < 6 else '✅ 合格'}")
    print(f"  新システム: {new_total:.1f}/10 {'✅ 合格' if new_total >= 6 else '⚠️ 要改善'}")

    return result

def main():
    """テスト実行"""

    # さくらももこのエピソードでテスト
    test_episode = "あなたと同じ21歳のとき、さくらももこは「りぼん」8月号で「ちびまる子ちゃん」の連載を開始した。会社を2か月で退職し漫画家の道を選んだ決断が、後に視聴率39.9％の国民的アニメを生んだ。静岡の小学生時代を描いた作品は、3世代が共感できる普遍的な家族像を創り出し、日本の文化的財産となった。"

    print("="*70)
    print("内在的価値評価システムのテスト")
    print("="*70)

    compare_evaluations(test_episode, 21, "さくらももこ")

if __name__ == "__main__":
    main()
