#!/usr/bin/env python3
"""
客観的事実から感動要素を汲み取るシステム
文章の演出ではなく、事実そのものが持つ価値を評価
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class EmotionSource(Enum):
    """感動の源泉"""
    RARITY = "希少性"
    DIFFICULTY = "困難度"
    CONTINUITY = "継続性"
    IMPACT = "影響力"
    AGE_RELATION = "年齢関係"
    SYNERGY = "相乗効果"

@dataclass
class FactualEmotion:
    """事実から抽出された感動要素"""
    fact: str                          # 客観的事実
    emotion_sources: List[EmotionSource]  # 感動の源泉
    public_resonance: float            # 大衆の共感度（0-10）
    evidence: List[str]                # 根拠となるデータ
    field_bonus: float                 # 分野別補正

class ObjectiveEmotionExtractor:
    """客観的事実から感動要素を抽出するシステム"""

    def __init__(self):
        # 禁止ワード（安っぽい演出表現）
        self.forbidden_words = [
            "涙", "震え", "覚悟", "運命", "奇跡", "伝説",
            "号泣", "感動", "衝撃", "驚愕", "歓喜", "悲願",
            "死んでも", "命を賭け", "魂", "宿命"
        ]

        # 分野別評価基準
        self.field_criteria = {
            "スポーツ": {"primary": "記録・数値", "weight": 1.2},
            "文化": {"primary": "影響力・普及度", "weight": 1.1},
            "ビジネス": {"primary": "規模・革新性", "weight": 1.15},
            "学術": {"primary": "貢献度・引用数", "weight": 1.0},
            "芸能": {"primary": "認知度・作品数", "weight": 1.1}
        }

        # 検証可能な感動パターン（事実ベース）
        self.emotion_patterns = {
            "世界初": {"source": EmotionSource.RARITY, "base_score": 9},
            "日本初": {"source": EmotionSource.RARITY, "base_score": 8},
            "史上最": {"source": EmotionSource.RARITY, "base_score": 9},
            "唯一": {"source": EmotionSource.RARITY, "base_score": 9},
            "年連続": {"source": EmotionSource.CONTINUITY, "base_score": 7},
            "年間": {"source": EmotionSource.CONTINUITY, "base_score": 6},
            "万人": {"source": EmotionSource.IMPACT, "base_score": 7},
            "億円": {"source": EmotionSource.IMPACT, "base_score": 8},
            "最年少": {"source": EmotionSource.AGE_RELATION, "base_score": 8},
            "歳で": {"source": EmotionSource.AGE_RELATION, "base_score": 6}
        }

    def extract_emotion(self, fact_text: str, age: int,
                        person_name: str, field: str) -> FactualEmotion:
        """事実から感動要素を抽出"""

        # 1. 禁止ワードチェック
        if self._contains_forbidden_words(fact_text):
            raise ValueError(f"演出的表現が含まれています: {fact_text}")

        # 2. 事実要素の抽出
        facts = self._extract_facts(fact_text)

        # 3. 感動源泉の特定
        emotion_sources = self._identify_emotion_sources(facts, age)

        # 4. 大衆共感度の推定（本来はWebサーチで取得）
        public_resonance = self._estimate_public_resonance(facts, person_name)

        # 5. 分野別補正
        field_bonus = self.field_criteria.get(field, {}).get("weight", 1.0)

        # 6. エビデンスの収集
        evidence = self._collect_evidence(facts)

        return FactualEmotion(
            fact=fact_text,
            emotion_sources=emotion_sources,
            public_resonance=public_resonance,
            evidence=evidence,
            field_bonus=field_bonus
        )

    def _contains_forbidden_words(self, text: str) -> bool:
        """禁止ワードが含まれているか確認"""
        return any(word in text for word in self.forbidden_words)

    def _extract_facts(self, text: str) -> Dict[str, any]:
        """事実要素を抽出"""
        facts = {
            "numbers": re.findall(r'\d+[万億千]?\d*', text),
            "records": [],
            "achievements": [],
            "durations": []
        }

        # 記録系の抽出
        if "初" in text or "最" in text or "唯一" in text:
            facts["records"].append(text)

        # 期間系の抽出
        duration_match = re.findall(r'(\d+)年', text)
        if duration_match:
            facts["durations"] = [int(d) for d in duration_match]

        # 達成系の抽出
        if any(word in text for word in ["達成", "獲得", "受賞", "記録"]):
            facts["achievements"].append(text)

        return facts

    def _identify_emotion_sources(self, facts: Dict, age: int) -> List[EmotionSource]:
        """感動の源泉を特定"""
        sources = []

        # 希少性
        if facts["records"]:
            sources.append(EmotionSource.RARITY)

        # 継続性
        if facts["durations"] and any(d >= 10 for d in facts["durations"]):
            sources.append(EmotionSource.CONTINUITY)

        # 影響力
        if any("万" in num or "億" in num for num in facts["numbers"]):
            sources.append(EmotionSource.IMPACT)

        # 年齢関係
        if age < 25 or age > 60:
            sources.append(EmotionSource.AGE_RELATION)

        # 相乗効果（複数要素の組み合わせ）
        if len(sources) >= 3:
            sources.append(EmotionSource.SYNERGY)

        return sources

    def _estimate_public_resonance(self, facts: Dict, person_name: str) -> float:
        """大衆共感度を推定（本来はWebサーチを使用）"""
        # 簡易実装：事実の要素数と規模から推定
        score = 5.0

        # 大きな数値は共感を呼ぶ
        for num in facts["numbers"]:
            if "億" in num:
                score += 2
            elif "万" in num:
                score += 1

        # 記録は共感を呼ぶ
        score += len(facts["records"]) * 1.5

        # 長期継続は共感を呼ぶ
        if facts["durations"]:
            max_duration = max(facts["durations"])
            if max_duration >= 20:
                score += 2
            elif max_duration >= 10:
                score += 1

        return min(10.0, score)

    def _collect_evidence(self, facts: Dict) -> List[str]:
        """エビデンスを収集"""
        evidence = []

        if facts["numbers"]:
            evidence.append(f"数値的事実: {', '.join(facts['numbers'])}")

        if facts["durations"]:
            evidence.append(f"継続期間: {max(facts['durations'])}年")

        if facts["records"]:
            evidence.append(f"記録: {len(facts['records'])}件")

        return evidence

class FactChecker:
    """ファクトチェック機能"""

    def __init__(self):
        self.required_sources = ["Wikipedia", "公式記録", "複数の証言"]

    def verify_fact(self, fact: str, person_name: str) -> Tuple[bool, str]:
        """事実を検証"""
        # 簡易実装
        checks = {
            "has_specific_number": bool(re.findall(r'\d+', fact)),
            "has_verifiable_event": any(word in fact for word in
                                       ["受賞", "発表", "記録", "達成", "設立", "奪った", "貢献", "活躍",
                                        "売り上げ", "翻訳", "確立", "優勝", "三振"]),
            "no_speculation": not any(word in fact for word in
                                     ["らしい", "ようだ", "かもしれない", "推測"])
        }

        # 少なくとも2つの条件を満たせば合格
        passed_count = sum(1 for v in checks.values() if v)
        if passed_count >= 2:
            return True, "検証可能な事実"
        else:
            failed = [k for k, v in checks.items() if not v]
            return False, f"検証不可: {', '.join(failed)}"

def evaluate_episode_objectively(episode_text: str, age: int,
                                person_name: str, field: str = "その他") -> Dict:
    """エピソードを客観的に評価"""

    extractor = ObjectiveEmotionExtractor()
    checker = FactChecker()

    # 1. ファクトチェック
    is_valid, check_message = checker.verify_fact(episode_text, person_name)

    if not is_valid:
        return {
            "valid": False,
            "message": check_message,
            "score": 0
        }

    try:
        # 2. 感動要素の抽出
        emotion = extractor.extract_emotion(episode_text, age, person_name, field)

        # 3. 総合スコアの計算
        base_score = emotion.public_resonance
        source_bonus = len(emotion.emotion_sources) * 0.5
        field_multiplier = emotion.field_bonus

        total_score = (base_score + source_bonus) * field_multiplier

        return {
            "valid": True,
            "score": min(10.0, total_score),
            "emotion_sources": [s.value for s in emotion.emotion_sources],
            "evidence": emotion.evidence,
            "public_resonance": emotion.public_resonance,
            "message": "客観的事実に基づく感動要素を抽出"
        }

    except ValueError as e:
        return {
            "valid": False,
            "message": str(e),
            "score": 0
        }

def main():
    """テスト実行"""

    test_cases = [
        {
            "text": "あなたと同じ38歳のとき、村上春樹は「ノルウェイの森」を発表し、上下巻で430万部を売り上げた",
            "age": 38,
            "person": "村上春樹",
            "field": "文化"
        },
        {
            "text": "あなたと同じ45歳のとき、イチローは涙を流しながらマウンドに向かった",  # 禁止ワード含む
            "age": 45,
            "person": "イチロー",
            "field": "スポーツ"
        },
        {
            "text": "あなたと同じ29歳のとき、大谷翔平は日米通算で10年連続200本安打を記録した",
            "age": 29,
            "person": "大谷翔平",
            "field": "スポーツ"
        }
    ]

    print("="*70)
    print("客観的感動要素抽出システムのテスト")
    print("="*70)

    for i, case in enumerate(test_cases, 1):
        print(f"\n【テストケース{i}】")
        print(f"人物: {case['person']}（{case['age']}歳）")
        print(f"分野: {case['field']}")
        print(f"事実: {case['text'][:50]}...")

        result = evaluate_episode_objectively(
            case['text'], case['age'], case['person'], case['field']
        )

        print(f"\n結果:")
        print(f"  有効性: {'✅' if result['valid'] else '❌'}")
        print(f"  スコア: {result.get('score', 0):.1f}/10")

        if result['valid'] and 'emotion_sources' in result:
            print(f"  感動源: {', '.join(result['emotion_sources'])}")
            print(f"  根拠: {', '.join(result['evidence'])}")
        else:
            print(f"  理由: {result['message']}")

if __name__ == "__main__":
    main()