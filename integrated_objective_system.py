#!/usr/bin/env python3
"""
統合型客観的感動抽出システム
演出ではなく事実から感動を汲み取る完全版
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from objective_emotion_extraction_system import ObjectiveEmotionExtractor, FactChecker
from public_resonance_analyzer import PublicResonanceAnalyzer

@dataclass
class ObjectiveEpisode:
    """客観的エピソード"""
    person_name: str
    age: int
    facts: List[str]           # 検証済み事実リスト
    primary_achievement: str    # 主要な達成
    supporting_data: Dict       # 補足データ
    emotion_score: float        # 感動スコア（事実ベース）
    public_resonance: float     # 大衆共感度
    verification_sources: List[str]  # 検証ソース

class IntegratedObjectiveSystem:
    """統合型の客観的評価システム"""

    def __init__(self):
        self.emotion_extractor = ObjectiveEmotionExtractor()
        self.fact_checker = FactChecker()
        self.resonance_analyzer = PublicResonanceAnalyzer()

        # 分野判定キーワード
        self.field_keywords = {
            "スポーツ": ["野球", "サッカー", "テニス", "オリンピック", "メダル", "記録", "打", "投"],
            "文化": ["小説", "映画", "音楽", "アニメ", "漫画", "作品", "出版", "放送"],
            "ビジネス": ["企業", "会社", "経営", "億円", "投資", "事業", "創業"],
            "学術": ["研究", "発見", "論文", "ノーベル", "博士", "大学"],
            "芸能": ["歌", "俳優", "タレント", "舞台", "ドラマ", "コンサート"]
        }

    def create_objective_episode(self, person_name: str, age: int,
                                raw_facts: List[str]) -> ObjectiveEpisode:
        """客観的エピソードを作成"""

        # 1. 事実の検証
        verified_facts = self._verify_facts(raw_facts, person_name)

        if not verified_facts:
            raise ValueError(f"{person_name}の検証可能な事実が見つかりません")

        # 2. 分野の判定
        field = self._determine_field(verified_facts)

        # 3. 主要達成の特定
        primary_achievement = self._identify_primary_achievement(verified_facts)

        # 4. 感動要素の抽出（演出なし）
        emotion_data = self._extract_pure_emotion(verified_facts, age, field)

        # 5. 大衆共感度の測定
        resonance_data = self._measure_public_resonance(
            verified_facts, person_name, primary_achievement
        )

        # 6. 検証ソースの収集
        sources = self._collect_verification_sources(person_name, primary_achievement)

        # 7. エピソード文の構築（事実のみ）
        episode_text = self._build_factual_episode(
            person_name, age, verified_facts, primary_achievement
        )

        return ObjectiveEpisode(
            person_name=person_name,
            age=age,
            facts=verified_facts,
            primary_achievement=primary_achievement,
            supporting_data={
                "field": field,
                "episode_text": episode_text,
                "character_count": len(episode_text)
            },
            emotion_score=emotion_data["score"],
            public_resonance=resonance_data["score"],
            verification_sources=sources
        )

    def _verify_facts(self, raw_facts: List[str], person_name: str) -> List[str]:
        """事実を検証して返す"""
        verified = []

        for fact in raw_facts:
            # 演出的表現を先に除去
            clean_fact = self._remove_dramatic_expressions(fact)
            if clean_fact:
                is_valid, message = self.fact_checker.verify_fact(clean_fact, person_name)
                if is_valid:
                    verified.append(clean_fact)

        return verified

    def _remove_dramatic_expressions(self, fact: str) -> str:
        """演出的表現を除去"""
        # 禁止表現のパターン
        dramatic_patterns = [
            r'涙を?流し(て|ながら)?',
            r'震え(る|て|ながら)?',
            r'死んでも?いい',
            r'運命の?',
            r'奇跡の?',
            r'伝説の?',
            r'感動の?',
            r'衝撃の?'
        ]

        clean_fact = fact
        for pattern in dramatic_patterns:
            clean_fact = re.sub(pattern, '', clean_fact)

        # 余分な空白を削除
        clean_fact = re.sub(r'\s+', ' ', clean_fact).strip()

        return clean_fact if len(clean_fact) > 10 else None

    def _determine_field(self, facts: List[str]) -> str:
        """事実から分野を判定"""
        field_scores = {}

        for field, keywords in self.field_keywords.items():
            score = sum(1 for fact in facts
                       for keyword in keywords
                       if keyword in fact)
            field_scores[field] = score

        if field_scores:
            return max(field_scores, key=field_scores.get)
        return "その他"

    def _identify_primary_achievement(self, facts: List[str]) -> str:
        """主要な達成を特定"""
        # 数値を含む事実を優先
        numeric_facts = [f for f in facts if re.search(r'\d+', f)]

        if numeric_facts:
            # 最も大きな数値を含む事実
            max_fact = max(numeric_facts,
                          key=lambda x: max([int(n) for n in re.findall(r'\d+', x)],
                                          default=0))
            return max_fact

        # 記録・達成系のキーワードを含む事実
        achievement_keywords = ["初", "最", "記録", "達成", "獲得", "受賞", "優勝"]
        for fact in facts:
            if any(kw in fact for kw in achievement_keywords):
                return fact

        return facts[0] if facts else ""

    def _extract_pure_emotion(self, facts: List[str], age: int, field: str) -> Dict:
        """純粋な感動要素を抽出（演出なし）"""
        emotion_scores = []

        for fact in facts:
            try:
                result = self.emotion_extractor.extract_emotion(
                    fact, age, "test", field
                )
                emotion_scores.append(result.public_resonance)
            except ValueError:
                continue

        avg_score = sum(emotion_scores) / len(emotion_scores) if emotion_scores else 0

        return {
            "score": avg_score,
            "fact_count": len(facts),
            "verified_count": len(emotion_scores)
        }

    def _measure_public_resonance(self, facts: List[str], person_name: str,
                                 achievement: str) -> Dict:
        """大衆共感度を測定"""
        combined_fact = " ".join(facts)
        resonance = self.resonance_analyzer.analyze_resonance(
            combined_fact, person_name, achievement
        )

        return {
            "score": resonance["final_score"],
            "numeric_impact": resonance.get("numeric_impact", 0),
            "benchmark": resonance.get("benchmark_comparison", 0)
        }

    def _collect_verification_sources(self, person_name: str,
                                     achievement: str) -> List[str]:
        """検証ソースを収集"""
        return self.resonance_analyzer.suggest_verification_sources(
            person_name, achievement
        )

    def _build_factual_episode(self, person_name: str, age: int,
                              facts: List[str], primary: str) -> str:
        """事実のみでエピソードを構築"""
        # テンプレート
        episode = f"あなたと同じ{age}歳のとき、{person_name}は"

        # 主要事実
        if primary:
            episode += primary

        # 補足事実（文字数制限内で）
        remaining_space = 250 - len(episode) - 1  # 終止符分
        for fact in facts:
            if fact != primary and len(fact) < remaining_space:
                episode += f"。{fact}"
                remaining_space -= len(fact) + 1

        # 文字数調整
        if len(episode) > 250:
            episode = episode[:247] + "。"
        elif len(episode) < 132:
            # 最低文字数に満たない場合は詳細を追加
            pass

        return episode + "。" if not episode.endswith("。") else episode

def test_integrated_system():
    """統合システムのテスト"""

    system = IntegratedObjectiveSystem()

    test_cases = [
        {
            "person": "大谷翔平",
            "age": 29,
            "facts": [
                "WBC決勝で最後の打者マイク・トラウトから三振を奪った",
                "日本の14年ぶりの世界一に貢献した",
                "二刀流として投打で活躍した",
                "涙を流しながら喜んだ"  # これは除去される
            ]
        },
        {
            "person": "村上春樹",
            "age": 38,
            "facts": [
                "ノルウェイの森を発表した",
                "上下巻合計で430万部を売り上げた",
                "100パーセントの恋愛小説というジャンルを確立した",
                "40か国以上で翻訳された"
            ]
        }
    ]

    print("="*70)
    print("統合型客観的感動抽出システムのテスト")
    print("="*70)

    for case in test_cases:
        print(f"\n【{case['person']}（{case['age']}歳）】")

        try:
            episode = system.create_objective_episode(
                case["person"], case["age"], case["facts"]
            )

            print(f"\n生成されたエピソード:")
            print(episode.supporting_data["episode_text"])

            print(f"\n評価結果:")
            print(f"  感動スコア: {episode.emotion_score:.1f}/10")
            print(f"  大衆共感度: {episode.public_resonance:.1f}/10")
            print(f"  分野: {episode.supporting_data['field']}")
            print(f"  文字数: {episode.supporting_data['character_count']}文字")

            print(f"\n検証済み事実:")
            for i, fact in enumerate(episode.facts, 1):
                print(f"  {i}. {fact}")

            print(f"\n検証ソース:")
            for source in episode.verification_sources[:3]:
                print(f"  - {source}")

        except Exception as e:
            print(f"エラー: {e}")

if __name__ == "__main__":
    test_integrated_system()
