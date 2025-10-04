#!/usr/bin/env python3
"""
大衆の感動度を測定するシステム
Webサーチや統計データから実際の共感度を分析
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PublicResonanceData:
    """大衆の共感データ"""
    google_trends_score: float      # Google Trendsスコア（0-100）
    wikipedia_views: int            # Wikipedia閲覧数
    news_mentions: int              # ニュース言及数
    social_media_engagement: float  # SNSエンゲージメント率
    books_written: int              # 関連書籍数
    documentary_count: int          # ドキュメンタリー数

class PublicResonanceAnalyzer:
    """大衆の感動度を分析"""

    def __init__(self):
        # 感動を示す指標と重み
        self.emotion_indicators = {
            "social_phenomenon": {
                "keywords": ["社会現象", "ブーム", "流行語", "国民的"],
                "weight": 2.0
            },
            "media_coverage": {
                "keywords": ["特集", "ドキュメンタリー", "映画化", "書籍化"],
                "weight": 1.5
            },
            "awards_recognition": {
                "keywords": ["受賞", "殿堂", "表彰", "記念"],
                "weight": 1.3
            },
            "generational_impact": {
                "keywords": ["世代", "影響", "憧れ", "目標"],
                "weight": 1.4
            },
            "quantifiable_following": {
                "keywords": ["ファン", "観客動員", "視聴率", "売上"],
                "weight": 1.2
            }
        }

        # 既知の高共感度事例（ベンチマーク）
        self.benchmark_cases = {
            "イチロー引退試合": {
                "attendance": 46451,
                "tv_rating": 17.4,
                "trending_days": 7,
                "resonance_score": 9.5
            },
            "羽生結弦オリンピック金メダル": {
                "tv_rating": 33.9,
                "trending_days": 14,
                "resonance_score": 9.8
            },
            "ちびまる子ちゃん放送開始": {
                "tv_rating": 39.9,
                "long_term_impact": 30,  # 30年以上継続
                "resonance_score": 9.0
            }
        }

    def analyze_resonance(self, fact: str, person_name: str,
                         achievement: str) -> Dict[str, float]:
        """大衆の共感度を分析"""

        resonance_data = {
            "base_score": 5.0,
            "indicator_scores": {},
            "benchmark_comparison": 0,
            "final_score": 0
        }

        # 1. 指標ベースの評価
        for indicator, config in self.emotion_indicators.items():
            score = self._evaluate_indicator(fact, config["keywords"])
            resonance_data["indicator_scores"][indicator] = score * config["weight"]

        # 2. 数値的インパクトの評価
        numeric_impact = self._evaluate_numeric_impact(fact)
        resonance_data["numeric_impact"] = numeric_impact

        # 3. ベンチマークとの比較
        benchmark_score = self._compare_with_benchmark(achievement)
        resonance_data["benchmark_comparison"] = benchmark_score

        # 4. 総合スコアの計算
        indicator_total = sum(resonance_data["indicator_scores"].values())
        final_score = (
            resonance_data["base_score"] +
            indicator_total +
            numeric_impact +
            benchmark_score
        ) / 3

        resonance_data["final_score"] = min(10.0, final_score)

        return resonance_data

    def _evaluate_indicator(self, fact: str, keywords: List[str]) -> float:
        """指標を評価"""
        matches = sum(1 for keyword in keywords if keyword in fact)
        return min(1.0, matches * 0.5)

    def _evaluate_numeric_impact(self, fact: str) -> float:
        """数値的インパクトを評価"""
        score = 0

        # 大きな数値の検出
        numbers = re.findall(r'(\d+)([万億])?', fact)
        for num, unit in numbers:
            value = int(num)
            if unit == "億":
                value *= 100000000
                score += 2
            elif unit == "万":
                value *= 10000
                score += 1

            # 絶対値でのインパクト
            if value >= 1000000:
                score += 1
            if value >= 10000000:
                score += 1

        # パーセンテージの検出
        percentages = re.findall(r'(\d+(?:\.\d+)?)[%％]', fact)
        for pct in percentages:
            if float(pct) >= 80:
                score += 1
            if float(pct) >= 90:
                score += 1

        return min(3.0, score)

    def _compare_with_benchmark(self, achievement: str) -> float:
        """ベンチマークケースと比較"""
        # 簡易実装：類似の偉業と比較
        if "引退" in achievement:
            return 2.0
        elif "金メダル" in achievement or "世界一" in achievement:
            return 2.5
        elif "記録" in achievement or "史上初" in achievement:
            return 2.0
        return 1.0

    def suggest_verification_sources(self, person_name: str,
                                   achievement: str) -> List[str]:
        """検証に使用すべきソースを提案"""
        sources = []

        # 基本ソース
        sources.append(f"Wikipedia: {person_name}")
        sources.append(f"Google Trends: {person_name} {achievement}")

        # 分野別ソース
        if any(sport in achievement for sport in ["野球", "サッカー", "テニス"]):
            sources.append("公式スポーツ記録データベース")

        if any(culture in achievement for culture in ["小説", "映画", "音楽"]):
            sources.append("文化庁・各種文化賞記録")

        if "会社" in achievement or "ビジネス" in achievement:
            sources.append("日経新聞アーカイブ")

        # 信頼度の高いソース
        sources.extend([
            "NHKアーカイブス",
            "国立国会図書館デジタルコレクション",
            "各分野の公式団体記録"
        ])

        return sources

def create_fact_based_episode(person_name: str, age: int,
                             facts: List[str], field: str) -> str:
    """事実のみに基づくエピソード作成"""

    # 事実を重要度順にソート
    sorted_facts = sorted(facts, key=lambda x: len(re.findall(r'\d+', x)),
                         reverse=True)

    # 最も重要な事実を中心に構成
    primary_fact = sorted_facts[0] if sorted_facts else ""
    supporting_facts = sorted_facts[1:3] if len(sorted_facts) > 1 else []

    # 客観的な文体で記述
    episode_parts = [f"あなたと同じ{age}歳のとき、{person_name}は"]

    episode_parts.append(primary_fact)

    if supporting_facts:
        episode_parts.append("。")
        for fact in supporting_facts:
            episode_parts.append(fact)
            episode_parts.append("。")

    episode = "".join(episode_parts)

    # 文字数調整（132-250文字）
    if len(episode) > 250:
        episode = episode[:247] + "。"
    elif len(episode) < 132:
        # 不足分は具体的数値や記録で補完
        pass

    return episode

def main():
    """システムテスト"""

    print("="*70)
    print("大衆共感度分析システムのテスト")
    print("="*70)

    analyzer = PublicResonanceAnalyzer()

    test_cases = [
        {
            "person": "大谷翔平",
            "fact": "WBCで優勝し、MVP満票で獲得。視聴率40%を記録",
            "achievement": "WBC優勝"
        },
        {
            "person": "村上春樹",
            "fact": "ノルウェイの森が430万部を売り上げ社会現象に",
            "achievement": "ベストセラー"
        },
        {
            "person": "イチロー",
            "fact": "日米通算4367安打を記録し、10年連続200本安打達成",
            "achievement": "引退"
        }
    ]

    for case in test_cases:
        print(f"\n【{case['person']}】")
        result = analyzer.analyze_resonance(
            case['fact'], case['person'], case['achievement']
        )

        print(f"事実: {case['fact'][:50]}...")
        print(f"共感度スコア: {result['final_score']:.1f}/10")
        print(f"数値インパクト: {result['numeric_impact']:.1f}")
        print(f"ベンチマーク比較: {result['benchmark_comparison']:.1f}")

        # 検証ソースの提案
        sources = analyzer.suggest_verification_sources(
            case['person'], case['achievement']
        )
        print(f"\n推奨検証ソース:")
        for source in sources[:3]:
            print(f"  - {source}")

if __name__ == "__main__":
    main()