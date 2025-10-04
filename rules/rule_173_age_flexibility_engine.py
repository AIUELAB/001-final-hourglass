#!/usr/bin/env python3
"""
RULE_173: 年齢柔軟性エンジン（Age Flexibility Engine）

人物の人生における複数の象徴的瞬間から、最も適切な年齢を自動選択
- データベース登録年齢が必ずしも最も象徴的とは限らない
- エピソードテキストから年齢候補を抽出
- 各候補年齢のシンボリズムスコアを計算
- 最高スコアの年齢を選択

例:
- イチロー: 51歳（引退）vs 27歳（MLB MVP）→ 27歳がより象徴的
- 大谷翔平: 30歳（現在）vs 28歳（MVP受賞）→ 28歳がより象徴的
"""

from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgeCandidate:
    """年齢候補"""
    age: int
    context: str  # 年齢が言及された文脈
    symbolism_score: float  # 象徴性スコア
    source: str  # データソース（database/episode/automatic）


class AgeFlexibilityEngine:
    """
    年齢柔軟性エンジン

    エピソードテキストから最も象徴的な年齢を自動選択
    """

    # 象徴性の高いキーワード（年齢選択の判断材料）
    HIGH_SYMBOLISM_KEYWORDS = [
        "ノーベル賞", "金メダル", "オリンピック", "MVP", "優勝", "世界記録",
        "受賞", "初", "史上", "記録", "達成", "創業", "デビュー"
    ]

    MEDIUM_SYMBOLISM_KEYWORDS = [
        "逮捕", "辞任", "引退", "転身", "決断", "挑戦", "成功",
        "社会現象", "ベストセラー", "話題"
    ]

    def __init__(self):
        """初期化"""
        pass

    def extract_age_from_text(self, episode_text: str) -> List[Tuple[int, str]]:
        """
        エピソードテキストから年齢を抽出

        Args:
            episode_text: エピソード本文

        Returns:
            [(年齢, 文脈), ...]
        """
        ages = []

        # パターン1: "あなたと同じN歳のとき"
        pattern1 = r'あなたと同じ(\d+)歳のとき'
        matches1 = re.finditer(pattern1, episode_text)
        for match in matches1:
            age = int(match.group(1))
            # 前後50文字を文脈として抽出
            start = max(0, match.start() - 20)
            end = min(len(episode_text), match.end() + 30)
            context = episode_text[start:end]
            ages.append((age, context))

        # パターン2: "N歳で〜した"
        pattern2 = r'(\d+)歳で'
        matches2 = re.finditer(pattern2, episode_text)
        for match in matches2:
            age = int(match.group(1))
            start = max(0, match.start() - 10)
            end = min(len(episode_text), match.end() + 40)
            context = episode_text[start:end]
            ages.append((age, context))

        # パターン3: "N歳のとき"
        pattern3 = r'(\d+)歳のとき'
        matches3 = re.finditer(pattern3, episode_text)
        for match in matches3:
            age = int(match.group(1))
            start = max(0, match.start() - 10)
            end = min(len(episode_text), match.end() + 40)
            context = episode_text[start:end]
            ages.append((age, context))

        return ages

    def calculate_context_symbolism(self, context: str) -> float:
        """
        文脈の象徴性スコアを計算

        Args:
            context: 文脈テキスト

        Returns:
            象徴性スコア（0-100）
        """
        score = 50  # ベーススコア

        # 高象徴性キーワード
        for keyword in self.HIGH_SYMBOLISM_KEYWORDS:
            if keyword in context:
                score += 20

        # 中象徴性キーワード
        for keyword in self.MEDIUM_SYMBOLISM_KEYWORDS:
            if keyword in context:
                score += 10

        return min(score, 100)

    def select_optimal_age(
        self,
        database_age: int,
        episode_text: str,
        person_name: str = ""
    ) -> AgeCandidate:
        """
        最適な年齢を選択

        Args:
            database_age: データベース登録年齢
            episode_text: エピソード本文
            person_name: 人物名（ログ用）

        Returns:
            選択された年齢候補
        """
        candidates = []

        # データベース年齢を候補に追加
        # Note: データベース年齢は保守的なスコア（50点）
        # エピソードで明示的に言及されている年齢を優先
        db_candidate = AgeCandidate(
            age=database_age,
            context="データベース登録値",
            symbolism_score=50,  # 保守的スコア（エピソード年齢を優先）
            source="database"
        )
        candidates.append(db_candidate)

        # エピソードから年齢抽出
        extracted_ages = self.extract_age_from_text(episode_text)

        if person_name:
            logger.info(f"🔍 {person_name} 抽出された年齢: {len(extracted_ages)}件")

        # 重複削除（同じ年齢が複数回出現する場合）
        age_contexts = {}
        for age, context in extracted_ages:
            if age not in age_contexts:
                age_contexts[age] = []
            age_contexts[age].append(context)
            if person_name:
                logger.info(f"   - {age}歳: {context[:40]}...")

        # 各年齢の象徴性スコアを計算
        for age, contexts in age_contexts.items():
            # 複数の文脈がある場合は最高スコアを採用
            max_score = 0
            best_context = contexts[0]

            for context in contexts:
                score = self.calculate_context_symbolism(context)
                if person_name:
                    logger.info(f"   → {age}歳のスコア: {score:.1f}点")
                if score > max_score:
                    max_score = score
                    best_context = context

            # エピソードで明示的に言及されている年齢には優先ボーナス+5点
            # これにより、同点の場合はエピソード年齢が優先される
            final_score = max_score + 5

            candidate = AgeCandidate(
                age=age,
                context=best_context,
                symbolism_score=final_score,
                source="episode"
            )
            candidates.append(candidate)
            if person_name:
                logger.info(f"   ✅ 候補追加: {age}歳 (最終スコア: {final_score:.1f}点、ボーナス+5点適用)")

        # 最高スコアの年齢を選択
        optimal = max(candidates, key=lambda x: x.symbolism_score)

        # ログ出力
        if person_name:
            logger.info(f"📊 {person_name} 年齢選択:")
            logger.info(f"   データベース年齢: {database_age}歳")
            logger.info(f"   選択された年齢: {optimal.age}歳 (スコア: {optimal.symbolism_score:.1f})")
            if optimal.source == "episode":
                logger.info(f"   理由: エピソード内の象徴的文脈に基づく選択")

        return optimal

    def evaluate(
        self,
        database_age: int,
        episode_text: str,
        person_name: str = ""
    ) -> Dict:
        """
        年齢柔軟性評価（外部インターフェース）

        Args:
            database_age: データベース登録年齢
            episode_text: エピソード本文
            person_name: 人物名

        Returns:
            評価結果
        """
        optimal = self.select_optimal_age(database_age, episode_text, person_name)

        age_changed = optimal.age != database_age

        return {
            "selected_age": optimal.age,
            "database_age": database_age,
            "age_changed": age_changed,
            "symbolism_score": optimal.symbolism_score,
            "context": optimal.context,
            "source": optimal.source,
            "rule_id": "RULE_173",
            "rule_name": "年齢柔軟性エンジン"
        }


# グローバルエンジン
age_engine = AgeFlexibilityEngine()


def select_optimal_age(
    database_age: int,
    episode_text: str,
    person_name: str = ""
) -> Dict:
    """
    最適な年齢を選択（外部インターフェース）

    Args:
        database_age: データベース登録年齢
        episode_text: エピソード本文
        person_name: 人物名

    Returns:
        評価結果
    """
    return age_engine.evaluate(database_age, episode_text, person_name)


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # テストケース
    test_cases = [
        {
            "person": "大谷翔平",
            "database_age": 30,
            "text": "あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞し、投手と打者の二刀流で歴史を変えた。2021年シーズン、投球では9勝、156奪三振、打撃では46本塁打、100打点を記録。ベーブ・ルース以来100年ぶりの快挙として世界中のメディアが報じ、野球の常識を覆した。"
        },
        {
            "person": "イチロー",
            "database_age": 51,
            "text": "あなたと同じ27歳のとき、イチローはメジャーリーグでア・リーグMVPと首位打者を同時受賞し、日本人野手初の快挙を達成した。2001年シーズン、打率.350、242安打で新人王も獲得。28年間のプロ野球人生で培った技術が、メジャーの頂点で開花した。"
        },
        {
            "person": "HIKAKIN",
            "database_age": 35,
            "text": "あなたと同じ23歳のとき、HIKAKINはYouTube登録者数100万人を突破し、日本のYouTuber文化の礎を築いた。2012年、ボイスパーカッションの動画が海外で1000万再生を記録し一夜にして有名に。その後、子供向けコンテンツで健全なYouTubeエンターテイメントを確立した。"
        }
    ]

    print("=" * 80)
    print("RULE_173: 年齢柔軟性エンジン - テスト実行")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']}")
        print(f"  データベース年齢: {test['database_age']}歳")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = select_optimal_age(
            test["database_age"],
            test["text"],
            test["person"]
        )

        status = "✅ 変更" if result["age_changed"] else "➡️ 維持"
        print(f"  {status}")
        print(f"  📊 選択された年齢: {result['selected_age']}歳")
        print(f"  📈 象徴性スコア: {result['symbolism_score']:.1f}点")
        print(f"  📝 ソース: {result['source']}")
        print(f"  💡 文脈: {result['context'][:40]}...")
        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
