#!/usr/bin/env python3
"""
RULE_176: 架空キャラクター統合（Fictional Character Integration）

フィクション作品の文化的影響度を評価し、適切に扱う
- 文化的影響力のスコアリング
- 実在人物との明確な区別
- キャラクターの象徴性評価
- 知名度に基づく保護判定

評価基準:
✅ 保護対象: 国民的・世界的に有名な作品のキャラクター
❌ 削除候補: 認知度が低いマイナー作品のキャラクター

例:
- ✅ ドラえもん（国民的キャラクター）
- ✅ ピカチュウ（世界的認知度）
- ✅ 竈門炭治郎（社会現象作品）
- ❌ マイナー作品のキャラクター（認知度<30）
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class CharacterEvaluation:
    """架空キャラクター評価結果"""
    character_name: str
    cultural_impact_score: float  # 文化的影響度（0-100）
    category: str  # 国民的、世界的、社会現象、有名、マイナー
    should_keep: bool  # 保護対象かどうか
    reason: str  # 判定理由


class FictionalCharacterEvaluator:
    """
    架空キャラクター評価エンジン

    フィクション作品のキャラクターの文化的影響度を評価
    """

    # 国民的キャラクター（絶対保存）
    NATIONAL_CHARACTERS = [
        "ドラえもん", "サザエさん", "アンパンマン", "ちびまる子ちゃん",
        "ポケモン", "ピカチュウ", "マリオ", "ルイージ",
        "鉄腕アトム", "仮面ライダー", "ウルトラマン", "ガンダム"
    ]

    # 世界的有名作品（絶対保存）
    WORLD_FAMOUS_WORKS = [
        "ドラゴンボール", "ナルト", "ONE PIECE", "ポケモン",
        "進撃の巨人", "鬼滅の刃", "スーパーマリオ", "ゼルダの伝説",
        "ファイナルファンタジー", "スタジオジブリ"
    ]

    # 社会現象作品（保存）
    SOCIAL_PHENOMENON_WORKS = [
        "呪術廻戦", "東京リベンジャーズ", "チェンソーマン",
        "SPY×FAMILY", "推しの子", "エヴァンゲリオン",
        "美少女戦士セーラームーン", "プリキュア"
    ]

    # 文化的影響度を示すキーワード
    CULTURAL_IMPACT_KEYWORDS = {
        "社会現象": 30,
        "国民的": 30,
        "世界的": 25,
        "大ヒット": 20,
        "歴代": 20,
        "記録的": 15,
        "累計": 10,
        "億": 10,
        "万部": 5,
        "映画化": 5,
        "アニメ化": 5,
    }

    def __init__(self):
        """初期化"""
        pass

    def is_national_character(self, character_name: str) -> bool:
        """
        国民的キャラクターかどうか判定

        Args:
            character_name: キャラクター名

        Returns:
            国民的キャラクターならTrue
        """
        return any(nc in character_name for nc in self.NATIONAL_CHARACTERS)

    def is_world_famous_work(self, work_title: str) -> bool:
        """
        世界的有名作品かどうか判定

        Args:
            work_title: 作品タイトル

        Returns:
            世界的有名作品ならTrue
        """
        return any(wf in work_title for wf in self.WORLD_FAMOUS_WORKS)

    def is_social_phenomenon_work(self, work_title: str) -> bool:
        """
        社会現象作品かどうか判定

        Args:
            work_title: 作品タイトル

        Returns:
            社会現象作品ならTrue
        """
        return any(sp in work_title for sp in self.SOCIAL_PHENOMENON_WORKS)

    def calculate_cultural_impact(
        self,
        character_name: str,
        work_title: str,
        description: str = ""
    ) -> float:
        """
        文化的影響度スコアを計算

        Args:
            character_name: キャラクター名
            work_title: 作品タイトル
            description: 作品・キャラクター説明文

        Returns:
            文化的影響度スコア（0-100）
        """
        score = 0

        # 国民的キャラクター判定
        if self.is_national_character(character_name):
            score = 95
            logger.info(f"📺 {character_name}: 国民的キャラクター → {score}点")
            return score

        # 世界的有名作品判定
        if self.is_world_famous_work(work_title):
            score = 85
            logger.info(f"🌍 {work_title}: 世界的有名作品 → {score}点")
            return score

        # 社会現象作品判定
        if self.is_social_phenomenon_work(work_title):
            score = 75
            logger.info(f"🔥 {work_title}: 社会現象作品 → {score}点")
            return score

        # 説明文からキーワード抽出でスコアリング
        combined_text = f"{work_title} {description}"
        for keyword, points in self.CULTURAL_IMPACT_KEYWORDS.items():
            if keyword in combined_text:
                score += points

        score = min(score, 100)
        logger.info(f"📊 {character_name} ({work_title}): 影響度スコア → {score}点")
        return score

    def categorize_character(self, impact_score: float) -> str:
        """
        スコアに基づいてカテゴリ分類

        Args:
            impact_score: 文化的影響度スコア

        Returns:
            カテゴリ名
        """
        if impact_score >= 90:
            return "国民的"
        elif impact_score >= 80:
            return "世界的"
        elif impact_score >= 70:
            return "社会現象"
        elif impact_score >= 50:
            return "有名"
        else:
            return "マイナー"

    def should_keep_character(self, impact_score: float) -> bool:
        """
        キャラクターを保護すべきか判定

        Args:
            impact_score: 文化的影響度スコア

        Returns:
            保護対象ならTrue
        """
        # スコア60点以上は保護
        return impact_score >= 60

    def evaluate(
        self,
        character_name: str,
        work_title: str,
        description: str = ""
    ) -> CharacterEvaluation:
        """
        架空キャラクターを評価

        Args:
            character_name: キャラクター名
            work_title: 作品タイトル
            description: 作品・キャラクター説明文

        Returns:
            評価結果
        """
        # 文化的影響度を計算
        impact_score = self.calculate_cultural_impact(
            character_name, work_title, description
        )

        # カテゴリ分類
        category = self.categorize_character(impact_score)

        # 保護判定
        should_keep = self.should_keep_character(impact_score)

        # 判定理由
        if should_keep:
            reason = f"{category}キャラクター（影響度{impact_score:.0f}点） - 保護対象"
        else:
            reason = f"{category}作品（影響度{impact_score:.0f}点） - 要レビュー"

        logger.info(f"🎭 {character_name}: {reason}")

        return CharacterEvaluation(
            character_name=character_name,
            cultural_impact_score=impact_score,
            category=category,
            should_keep=should_keep,
            reason=reason
        )


# グローバル評価エンジン
fictional_evaluator = FictionalCharacterEvaluator()


def evaluate_fictional_character(
    character_name: str,
    work_title: str,
    description: str = ""
) -> Dict:
    """
    架空キャラクターを評価（外部インターフェース）

    Args:
        character_name: キャラクター名
        work_title: 作品タイトル
        description: 作品・キャラクター説明文

    Returns:
        評価結果
    """
    evaluation = fictional_evaluator.evaluate(
        character_name, work_title, description
    )

    return {
        "character_name": evaluation.character_name,
        "cultural_impact_score": evaluation.cultural_impact_score,
        "category": evaluation.category,
        "should_keep": evaluation.should_keep,
        "reason": evaluation.reason,
        "rule_id": "RULE_176",
        "rule_name": "架空キャラクター統合"
    }


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # テストケース
    test_cases = [
        {
            "character": "ドラえもん",
            "work": "ドラえもん",
            "description": "国民的アニメキャラクター、50年以上の歴史"
        },
        {
            "character": "竈門炭治郎",
            "work": "鬼滅の刃",
            "description": "社会現象となった作品の主人公、興行収入歴代1位"
        },
        {
            "character": "ピカチュウ",
            "work": "ポケモン",
            "description": "世界的に有名なキャラクター、ゲーム累計4億本"
        },
        {
            "character": "孫悟空",
            "work": "ドラゴンボール",
            "description": "世界80カ国で放送、累計2億6000万部"
        },
        {
            "character": "架空のキャラA",
            "work": "マイナー作品X",
            "description": "地方限定の小規模作品"
        }
    ]

    print("=" * 80)
    print("RULE_176: 架空キャラクター統合 - テスト実行")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['character']} ({test['work']})")
        print(f"  説明: {test['description'][:50]}...")
        print()

        result = evaluate_fictional_character(
            test["character"],
            test["work"],
            test["description"]
        )

        status = "✅ 保護対象" if result["should_keep"] else "⚠️ 要レビュー"
        print(f"  {status}")
        print(f"  📊 文化的影響度: {result['cultural_impact_score']:.0f}点")
        print(f"  🏷️ カテゴリ: {result['category']}")
        print(f"  💡 理由: {result['reason']}")
        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
