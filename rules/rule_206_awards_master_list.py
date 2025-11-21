#!/usr/bin/env python3
"""
RULE_206: 賞・認定マスターリスト

石ノ森章太郎事例から導出された品質ゲート
- 主要な賞・認定を受けた人物は、必ずその受賞エピソードを含める
- 受賞者リストとエピソード照合を行い、漏れを検出

Phase: 品質ゲート強化（RULE_200-206）
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AwardInfo:
    """賞・認定情報"""
    award_name: str
    category: str  # international, national, industry
    importance: str  # critical, high, medium
    keywords: List[str]  # 検出用キーワード


# 賞・認定マスターリスト
AWARDS_MASTER_LIST: List[AwardInfo] = [
    # === 国際的な賞（Critical） ===
    AwardInfo("ノーベル賞", "international", "critical",
              ["ノーベル", "Nobel", "ノーベル賞"]),
    AwardInfo("アカデミー賞", "international", "critical",
              ["アカデミー賞", "オスカー", "Academy Award", "Oscar"]),
    AwardInfo("グラミー賞", "international", "critical",
              ["グラミー賞", "Grammy"]),
    AwardInfo("ピューリッツァー賞", "international", "critical",
              ["ピューリッツァー", "Pulitzer"]),
    AwardInfo("ギネス世界記録", "international", "critical",
              ["ギネス", "ギネス世界記録", "ギネスブック", "Guinness"]),
    AwardInfo("オリンピック金メダル", "international", "critical",
              ["オリンピック", "金メダル", "五輪"]),
    AwardInfo("ワールドカップ優勝", "international", "critical",
              ["ワールドカップ", "W杯", "World Cup"]),
    AwardInfo("カンヌ映画祭", "international", "high",
              ["カンヌ", "パルムドール", "Cannes"]),
    AwardInfo("ベルリン映画祭", "international", "high",
              ["ベルリン", "金熊賞", "Berlin"]),
    AwardInfo("ヴェネツィア映画祭", "international", "high",
              ["ヴェネツィア", "金獅子賞", "Venice"]),

    # === 日本国内の賞（Critical/High） ===
    AwardInfo("文化勲章", "national", "critical",
              ["文化勲章"]),
    AwardInfo("国民栄誉賞", "national", "critical",
              ["国民栄誉賞"]),
    AwardInfo("紫綬褒章", "national", "high",
              ["紫綬褒章", "褒章"]),
    AwardInfo("人間国宝", "national", "critical",
              ["人間国宝", "重要無形文化財保持者"]),
    AwardInfo("芥川賞", "national", "critical",
              ["芥川賞", "芥川龍之介賞"]),
    AwardInfo("直木賞", "national", "critical",
              ["直木賞", "直木三十五賞"]),
    AwardInfo("本屋大賞", "national", "high",
              ["本屋大賞"]),
    AwardInfo("日本レコード大賞", "national", "high",
              ["レコード大賞", "日本レコード大賞"]),

    # === 漫画・アニメ業界（High） ===
    AwardInfo("手塚治虫文化賞", "industry", "high",
              ["手塚治虫文化賞", "手塚賞"]),
    AwardInfo("星雲賞", "industry", "high",
              ["星雲賞"]),
    AwardInfo("日本漫画家協会賞", "industry", "high",
              ["日本漫画家協会賞", "漫画家協会賞"]),
    AwardInfo("講談社漫画賞", "industry", "medium",
              ["講談社漫画賞"]),
    AwardInfo("小学館漫画賞", "industry", "medium",
              ["小学館漫画賞"]),
    AwardInfo("日本アカデミー賞", "national", "high",
              ["日本アカデミー賞"]),

    # === ビジネス・産業（High） ===
    AwardInfo("経団連会長", "industry", "high",
              ["経団連会長", "日本経済団体連合会"]),
    AwardInfo("Forbes選出", "international", "medium",
              ["Forbes", "フォーブス", "世界長者番付"]),

    # === スポーツ（High） ===
    AwardInfo("殿堂入り", "industry", "high",
              ["殿堂入り", "Hall of Fame"]),
    AwardInfo("MVP", "industry", "high",
              ["MVP", "最優秀選手"]),
    AwardInfo("世界記録", "international", "critical",
              ["世界記録", "世界新記録", "World Record"]),

    # === 音楽コンクール（Critical/High）- RULE_207追加 ===
    AwardInfo("ショパン国際ピアノコンクール", "international", "critical",
              ["ショパンコンクール", "ショパン国際", "Chopin Competition"]),
    AwardInfo("チャイコフスキー国際コンクール", "international", "critical",
              ["チャイコフスキーコンクール", "チャイコフスキー国際", "Tchaikovsky"]),
    AwardInfo("エリザベート王妃国際音楽コンクール", "international", "high",
              ["エリザベート王妃", "Queen Elisabeth"]),
    AwardInfo("ヴァン・クライバーン国際ピアノコンクール", "international", "high",
              ["ヴァン・クライバーン", "Van Cliburn"]),
    AwardInfo("リーズ国際ピアノコンクール", "international", "high",
              ["リーズ国際", "Leeds"]),

    # === 児童文学（Critical）- RULE_207追加 ===
    AwardInfo("国際アンデルセン賞", "international", "critical",
              ["アンデルセン賞", "国際アンデルセン", "Hans Christian Andersen Award"]),

    # === 科学・学術（Critical/High）- RULE_207追加 ===
    AwardInfo("フィールズ賞", "international", "critical",
              ["フィールズ賞", "Fields Medal"]),
    AwardInfo("ラスカー賞", "international", "critical",
              ["ラスカー賞", "Lasker Award"]),
    AwardInfo("京都賞", "international", "high",
              ["京都賞", "Kyoto Prize"]),
    AwardInfo("ウルフ賞", "international", "high",
              ["ウルフ賞", "Wolf Prize"]),
    AwardInfo("日本学士院賞", "national", "high",
              ["日本学士院賞", "学士院賞"]),

    # === 建築（Critical） ===
    AwardInfo("プリツカー賞", "international", "critical",
              ["プリツカー賞", "Pritzker", "建築のノーベル賞"]),

    # === 演劇・ミュージカル ===
    AwardInfo("トニー賞", "international", "high",
              ["トニー賞", "Tony Award"]),
    AwardInfo("エミー賞", "international", "high",
              ["エミー賞", "Emmy Award"]),

    # === 日本の文学賞（追加） ===
    AwardInfo("吉川英治文学賞", "national", "high",
              ["吉川英治文学賞", "吉川英治賞"]),
    AwardInfo("谷崎潤一郎賞", "national", "high",
              ["谷崎潤一郎賞", "谷崎賞"]),
    AwardInfo("読売文学賞", "national", "high",
              ["読売文学賞"]),

    # === 日本の芸術賞 ===
    AwardInfo("芸術選奨文部科学大臣賞", "national", "high",
              ["芸術選奨", "文部科学大臣賞"]),
    AwardInfo("毎日芸術賞", "national", "high",
              ["毎日芸術賞"]),
    AwardInfo("朝日賞", "national", "high",
              ["朝日賞"]),
]


class AwardChecker:
    """賞・認定チェッカー"""

    def __init__(self):
        self.awards = AWARDS_MASTER_LIST
        self._build_keyword_index()

    def _build_keyword_index(self):
        """キーワードインデックスを構築"""
        self.keyword_to_award: Dict[str, AwardInfo] = {}
        for award in self.awards:
            for keyword in award.keywords:
                self.keyword_to_award[keyword.lower()] = award

    def detect_awards_in_text(self, text: str) -> List[AwardInfo]:
        """
        テキストから賞・認定を検出

        Args:
            text: チェック対象テキスト

        Returns:
            検出された賞のリスト
        """
        detected = []
        text_lower = text.lower()

        for award in self.awards:
            for keyword in award.keywords:
                if keyword.lower() in text_lower:
                    if award not in detected:
                        detected.append(award)
                    break

        return detected

    def check_person_awards(
        self,
        person_name: str,
        episodes: List[str],
        known_awards: Optional[List[str]] = None
    ) -> Dict:
        """
        人物の賞・認定エピソード網羅性をチェック

        Args:
            person_name: 人物名
            episodes: エピソードテキストのリスト
            known_awards: 既知の受賞歴（外部データ）

        Returns:
            チェック結果
        """
        # エピソードから賞を検出
        covered_awards: Set[str] = set()
        for episode in episodes:
            detected = self.detect_awards_in_text(episode)
            for award in detected:
                covered_awards.add(award.award_name)

        # 既知の受賞歴との照合
        missing_awards = []
        if known_awards:
            for award_name in known_awards:
                if award_name not in covered_awards:
                    # マスターリストで重要度を確認
                    award_info = self._find_award_by_name(award_name)
                    if award_info and award_info.importance in ["critical", "high"]:
                        missing_awards.append({
                            "award": award_name,
                            "importance": award_info.importance,
                            "category": award_info.category
                        })

        passed = len(missing_awards) == 0

        return {
            "passed": passed,
            "person_name": person_name,
            "covered_awards": list(covered_awards),
            "missing_awards": missing_awards,
            "total_episodes": len(episodes),
            "rule_id": "RULE_206",
            "rule_name": "賞・認定必須エピソード"
        }

    def _find_award_by_name(self, award_name: str) -> Optional[AwardInfo]:
        """賞名からAwardInfoを検索"""
        for award in self.awards:
            if award.award_name == award_name:
                return award
            for keyword in award.keywords:
                if keyword in award_name:
                    return award
        return None

    def get_critical_awards(self) -> List[str]:
        """Critical重要度の賞リストを取得"""
        return [a.award_name for a in self.awards if a.importance == "critical"]

    def get_all_keywords(self) -> List[str]:
        """全キーワードリストを取得"""
        keywords = []
        for award in self.awards:
            keywords.extend(award.keywords)
        return keywords


# グローバルインスタンス
award_checker = AwardChecker()


def check_award_coverage(person_name: str, episodes: List[str], known_awards: Optional[List[str]] = None) -> Dict:
    """
    賞・認定エピソードの網羅性をチェック（外部インターフェース）

    Args:
        person_name: 人物名
        episodes: エピソードテキストのリスト
        known_awards: 既知の受賞歴

    Returns:
        チェック結果
    """
    return award_checker.check_person_awards(person_name, episodes, known_awards)


if __name__ == "__main__":
    # テスト
    print("=" * 60)
    print("RULE_206: 賞・認定マスターリスト - テスト")
    print("=" * 60)

    # 石ノ森章太郎のテストケース
    test_person = "石ノ森章太郎"
    test_episodes = [
        "あなたと同じ38歳のとき、石ノ森章太郎は芸術・文化分野において画期的な成果を達成しました。"
    ]
    known_awards = ["ギネス世界記録", "紫綬褒章"]

    result = check_award_coverage(test_person, test_episodes, known_awards)

    print(f"\n人物: {result['person_name']}")
    print(f"判定: {'✅ 合格' if result['passed'] else '❌ 不合格'}")
    print(f"カバー済み賞: {result['covered_awards']}")
    print(f"不足している賞: {result['missing_awards']}")

    # Critical賞リスト表示
    print(f"\n📋 Critical重要度の賞:")
    for award in award_checker.get_critical_awards():
        print(f"  - {award}")
