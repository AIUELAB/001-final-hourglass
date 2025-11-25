#!/usr/bin/env python3
"""
ハイブリッド感情的インパクト評価器（Hybrid Impact Evaluator）
キーワードベース + LLMベースの2段階評価システム

評価フロー:
1. Phase 3A: キーワードベース評価（高速・無料）
2. Phase 3B: LLMベース評価（ボーダーライン時のみ）

コスト最適化:
- キーワードスコア ≥ 30点 → 即合格（LLM不要）
- キーワードスコア < 20点 → 即不合格（LLM不要）
- 20-29点（ボーダーライン）→ LLM評価を実施
"""

import os
from typing import Optional, Dict
from dataclasses import dataclass
import time

from impact_evaluator import ImpactEvaluator, ImpactScore
from llm_impact_evaluator import LLMImpactEvaluator, LLMImpactScore


@dataclass
class HybridImpactScore:
    """ハイブリッド評価スコア"""
    # キーワードベース
    keyword_score: int
    keyword_details: Dict[str, int]

    # LLMベース（実行時のみ）
    llm_score: Optional[int]
    llm_details: Optional[Dict[str, int]]
    llm_reasoning: Optional[str]
    llm_used: bool

    # 総合判定
    total_score: int
    passed: bool
    evaluation_method: str  # "keyword_only" or "hybrid"
    cost_saved: bool  # LLM呼び出しを回避できたか


class HybridImpactEvaluator:
    """
    キーワード + LLM のハイブリッド感情的インパクト評価器

    コスト最適化戦略:
    - 明確な合格（≥30点）: LLM不要
    - 明確な不合格（<20点）: LLM不要
    - ボーダーライン（20-29点）: LLMで最終判定
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        enable_llm: bool = True,
        borderline_min: int = 20,
        borderline_max: int = 29
    ):
        """
        Args:
            llm_provider: LLMプロバイダー ("openai" or "anthropic")
            llm_model: LLMモデル名（Noneの場合はデフォルト）
            enable_llm: LLM評価の有効化（False=キーワードのみ）
            borderline_min: LLM評価を実施する最小スコア
            borderline_max: LLM評価を実施する最大スコア
        """
        self.keyword_evaluator = ImpactEvaluator()
        self.llm_evaluator = None
        self.enable_llm = enable_llm
        self.borderline_min = borderline_min
        self.borderline_max = borderline_max
        self.min_passing_score = 30

        # LLM評価が有効で、APIキーが設定されている場合のみ初期化
        if enable_llm:
            try:
                self.llm_evaluator = LLMImpactEvaluator(
                    provider=llm_provider,
                    model=llm_model
                )
                print(f"✅ LLM評価有効: {llm_provider} / {self.llm_evaluator.model}")
            except ValueError as e:
                print(f"⚠️ LLM評価無効: {e}")
                print("キーワードベースのみで評価します")
                self.enable_llm = False

        # 統計情報
        self.stats = {
            'total_evaluations': 0,
            'llm_calls': 0,
            'cost_saved': 0,
            'keyword_pass': 0,
            'keyword_fail': 0,
            'borderline': 0
        }

    def evaluate(self, episode_text: str, person_name: str, age: int) -> HybridImpactScore:
        """
        ハイブリッド評価を実施

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            HybridImpactScore: ハイブリッド評価結果
        """
        self.stats['total_evaluations'] += 1

        # Phase 3A: キーワードベース評価（必須）
        keyword_result = self.keyword_evaluator.evaluate(episode_text, person_name, age)
        keyword_score = keyword_result.total

        # コスト最適化判定
        if keyword_score >= self.min_passing_score:
            # 明確な合格 → LLM不要
            self.stats['keyword_pass'] += 1
            self.stats['cost_saved'] += 1
            return HybridImpactScore(
                keyword_score=keyword_score,
                keyword_details={
                    'turning_point': keyword_result.turning_point,
                    'surprise': keyword_result.surprise,
                    'risk_taking': keyword_result.risk_taking,
                    'relatability': keyword_result.relatability,
                    'sensational': keyword_result.sensational
                },
                llm_score=None,
                llm_details=None,
                llm_reasoning=None,
                llm_used=False,
                total_score=keyword_score,
                passed=True,
                evaluation_method="keyword_only",
                cost_saved=True
            )

        elif keyword_score < self.borderline_min:
            # 明確な不合格 → LLM不要
            self.stats['keyword_fail'] += 1
            self.stats['cost_saved'] += 1
            return HybridImpactScore(
                keyword_score=keyword_score,
                keyword_details={
                    'turning_point': keyword_result.turning_point,
                    'surprise': keyword_result.surprise,
                    'risk_taking': keyword_result.risk_taking,
                    'relatability': keyword_result.relatability,
                    'sensational': keyword_result.sensational
                },
                llm_score=None,
                llm_details=None,
                llm_reasoning=None,
                llm_used=False,
                total_score=keyword_score,
                passed=False,
                evaluation_method="keyword_only",
                cost_saved=True
            )

        # Phase 3B: LLMベース評価（ボーダーライン時のみ）
        self.stats['borderline'] += 1

        if not self.enable_llm or self.llm_evaluator is None:
            # LLM無効時はキーワードスコアで判定
            return HybridImpactScore(
                keyword_score=keyword_score,
                keyword_details={
                    'turning_point': keyword_result.turning_point,
                    'surprise': keyword_result.surprise,
                    'risk_taking': keyword_result.risk_taking,
                    'relatability': keyword_result.relatability,
                    'sensational': keyword_result.sensational
                },
                llm_score=None,
                llm_details=None,
                llm_reasoning="LLM評価が無効のため実施せず",
                llm_used=False,
                total_score=keyword_score,
                passed=keyword_score >= self.min_passing_score,
                evaluation_method="keyword_only",
                cost_saved=False
            )

        # LLM評価を実施
        self.stats['llm_calls'] += 1
        print(f"🔄 ボーダーライン検出（{keyword_score}点）→ LLM評価実施: {person_name}")

        llm_result = self.llm_evaluator.evaluate(episode_text, person_name, age)
        llm_score = llm_result.total

        # ハイブリッドスコア: LLMスコアを最終判定に使用
        # （キーワードは参考情報として保持）
        total_score = llm_score
        passed = total_score >= self.min_passing_score

        return HybridImpactScore(
            keyword_score=keyword_score,
            keyword_details={
                'turning_point': keyword_result.turning_point,
                'surprise': keyword_result.surprise,
                'risk_taking': keyword_result.risk_taking,
                'relatability': keyword_result.relatability,
                'sensational': keyword_result.sensational
            },
            llm_score=llm_score,
            llm_details={
                'turning_point': llm_result.turning_point,
                'surprise': llm_result.surprise,
                'risk_taking': llm_result.risk_taking,
                'relatability': llm_result.relatability,
                'sensational': llm_result.sensational
            },
            llm_reasoning=llm_result.reasoning,
            llm_used=True,
            total_score=total_score,
            passed=passed,
            evaluation_method="hybrid",
            cost_saved=False
        )

    def get_impact_report(self, score: HybridImpactScore, person_name: str, age: int) -> str:
        """
        ハイブリッド評価レポートを生成

        Args:
            score: ハイブリッドスコア
            person_name: 人物名
            age: 年齢

        Returns:
            str: レポート文字列
        """
        status = "✅ 合格" if score.passed else "❌ 不合格"
        method = "ハイブリッド評価" if score.evaluation_method == "hybrid" else "キーワード評価のみ"

        report = f"""
{'='*80}
感情的インパクト評価: {status}
{'='*80}

人物: {person_name}（{age}歳）
評価方法: {method}

【Phase 3A - キーワードベース評価】
スコア: {score.keyword_score}/50点（{score.keyword_score/50*100:.0f}%）
詳細:
  1. 人生の転換点: {score.keyword_details['turning_point']}/10点 {"★" * score.keyword_details['turning_point']}
  2. 意外性: {score.keyword_details['surprise']}/10点 {"★" * score.keyword_details['surprise']}
  3. リスクテイキング: {score.keyword_details['risk_taking']}/10点 {"★" * score.keyword_details['risk_taking']}
  4. 共感性: {score.keyword_details['relatability']}/10点 {"★" * score.keyword_details['relatability']}
  5. センセーショナル度: {score.keyword_details['sensational']}/10点 {"★" * score.keyword_details['sensational']}
"""

        if score.llm_used:
            report += f"""
【Phase 3B - LLMベース評価】
スコア: {score.llm_score}/50点（{score.llm_score/50*100:.0f}%）
詳細:
  1. 人生の転換点: {score.llm_details['turning_point']}/10点 {"★" * score.llm_details['turning_point']}
  2. 意外性: {score.llm_details['surprise']}/10点 {"★" * score.llm_details['surprise']}
  3. リスクテイキング: {score.llm_details['risk_taking']}/10点 {"★" * score.llm_details['risk_taking']}
  4. 共感性: {score.llm_details['relatability']}/10点 {"★" * score.llm_details['relatability']}
  5. センセーショナル度: {score.llm_details['sensational']}/10点 {"★" * score.llm_details['sensational']}

判定理由:
{score.llm_reasoning}
"""
        else:
            cost_msg = "✅ コスト最適化: LLM呼び出し不要" if score.cost_saved else ""
            report += f"""
【LLM評価】
実施せず（キーワードスコアで判定確定）
{cost_msg}
"""

        report += f"""
{'='*80}
最終判定:
  総合スコア: {score.total_score}/50点（{score.total_score/50*100:.0f}%）
  合格基準: 30点以上（60%）
  結果: {status}
{'='*80}
"""
        return report

    def get_statistics(self) -> str:
        """評価統計情報を取得"""
        llm_usage_rate = (self.stats['llm_calls'] / self.stats['total_evaluations'] * 100) if self.stats['total_evaluations'] > 0 else 0
        cost_savings_rate = (self.stats['cost_saved'] / self.stats['total_evaluations'] * 100) if self.stats['total_evaluations'] > 0 else 0

        return f"""
{'='*80}
ハイブリッド評価統計
{'='*80}

総評価数: {self.stats['total_evaluations']}件

【評価内訳】
  キーワードのみで合格: {self.stats['keyword_pass']}件
  キーワードのみで不合格: {self.stats['keyword_fail']}件
  ボーダーライン（LLM評価）: {self.stats['borderline']}件

【コスト最適化】
  LLM呼び出し回数: {self.stats['llm_calls']}件
  LLM使用率: {llm_usage_rate:.1f}%
  コスト削減率: {cost_savings_rate:.1f}%

{'='*80}
"""


def test_hybrid_impact_evaluator():
    """ハイブリッド評価器のテスト"""

    # 環境変数チェック
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ OPENAI_API_KEYまたはANTHROPIC_API_KEY環境変数が設定されていません")
        print("キーワードベースのみで評価します")

    print("="*80)
    print("ハイブリッド感情的インパクト評価システム")
    print("="*80)

    evaluator = HybridImpactEvaluator(llm_provider="openai")

    # テストケース1: Ado（ボーダーライン - LLM評価実施）
    print("\nテストケース1: Ado - 紅白出場・Billboard1位（21歳）")
    print("期待: キーワード37点 → ボーダーライン → LLM評価実施")
    print("="*80)

    ado_episode = """あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。「うっせぇわ」で顔を公開せずに紅白歌合戦出場とBillboardJapan年間1位を獲得し、匿名アーティストという新しい成功モデルを確立した。YouTubeでの楽曲は若者を中心に広範な支持を集め、新時代の音楽シーンを象徴する存在となった。"""

    score = evaluator.evaluate(ado_episode, "Ado", 21)
    print(evaluator.get_impact_report(score, "Ado", 21))

    # レート制限対策
    if score.llm_used:
        time.sleep(2)

    # テストケース2: スティーブ・ジョブズ（低スコア - LLM評価実施）
    print("\n" + "="*80)
    print("テストケース2: スティーブ・ジョブズ - iPhone発表（52歳）")
    print("期待: キーワード7点 → 不合格判定確定 → LLM不要")
    print("="*80)

    jobs_episode = """あなたと同じ52歳のとき、スティーブ・ジョブズはMacworld2007でiPhoneを発表し、携帯電話を再定義した。タッチスクリーン技術により年間10億台超のスマートフォン市場を創出し、アップルの時価総額を40億ドルから3500億ドルへと875倍に成長させた。"""

    score = evaluator.evaluate(jobs_episode, "スティーブ・ジョブズ", 52)
    print(evaluator.get_impact_report(score, "スティーブ・ジョブズ", 52))

    # テストケース3: マーティン・ルーサー・キング（高スコア - LLM不要）
    print("\n" + "="*80)
    print("テストケース3: MLキング - 公民権運動（34歳）")
    print("期待: キーワード31点 → 合格判定確定 → LLM不要")
    print("="*80)

    mlk_episode = """あなたと同じ34歳のとき、マーティン・ルーサー・キング・ジュニアは、ワシントン大行進で25万人の前で「I have a dream」演説を行い、公民権運動の象徴となった。この歴史的瞬間は、黒人への人種差別撤廃運動の決定的な転換点となり、翌年の公民権法制定の原動力となった。"""

    score = evaluator.evaluate(mlk_episode, "MLキング", 34)
    print(evaluator.get_impact_report(score, "MLキング", 34))

    # 統計情報表示
    print(evaluator.get_statistics())


if __name__ == '__main__':
    test_hybrid_impact_evaluator()
