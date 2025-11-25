#!/usr/bin/env python3
"""
OptimalAgeSelector - 人物の最も重要な瞬間の年齢を選択するアルゴリズム
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class MomentType(Enum):
    """重要な瞬間のタイプ"""
    BREAKTHROUGH = "突破口"          # 初めての大成功
    PEAK_ACHIEVEMENT = "頂点達成"    # キャリアの頂点
    WORLD_CHANGE = "世界的影響"      # 世界を変えた瞬間
    LIFE_TURNING = "人生転換"        # 運命の分岐点
    HISTORIC_RECORD = "歴史的記録"   # 前人未到の記録
    SOCIAL_PHENOMENON = "社会現象"   # 時代を代表
    CULMINATION = "集大成"          # キャリアの総括
    NEW_PARADIGM = "新領域開拓"     # 新分野の確立
    COMEBACK = "復活・克服"         # 挫折からの復活
    CONTRIBUTION = "社会貢献"       # 人類・社会への貢献

@dataclass
class KeyMoment:
    """重要な瞬間の定義"""
    age: int
    year: Optional[int]
    event: str
    moment_type: MomentType
    impact_score: float  # 1.0-10.0
    description: str

class OptimalAgeSelector:
    """最適年齢選択システム"""

    def __init__(self):
        """初期化"""
        # 人物ごとの重要な瞬間データベース
        self.key_moments_db = self._initialize_moments_database()

        # 瞬間タイプの重要度重み
        self.moment_weights = {
            MomentType.WORLD_CHANGE: 10.0,
            MomentType.HISTORIC_RECORD: 9.5,
            MomentType.BREAKTHROUGH: 9.0,
            MomentType.PEAK_ACHIEVEMENT: 8.5,
            MomentType.SOCIAL_PHENOMENON: 8.5,
            MomentType.NEW_PARADIGM: 8.0,
            MomentType.CONTRIBUTION: 8.0,
            MomentType.COMEBACK: 7.5,
            MomentType.LIFE_TURNING: 7.5,
            MomentType.CULMINATION: 7.0,
        }

    def _initialize_moments_database(self) -> Dict[str, List[KeyMoment]]:
        """重要瞬間データベースの初期化"""
        return {
            "大谷翔平": [
                KeyMoment(23, 2018, "MLB新人王", MomentType.BREAKTHROUGH, 8.0, "二刀流でMLBデビュー"),
                KeyMoment(26, 2021, "MVP満票受賞", MomentType.PEAK_ACHIEVEMENT, 9.0, "46本塁打で歴史的シーズン"),
                KeyMoment(29, 2023, "WBC制覇", MomentType.HISTORIC_RECORD, 10.0, "トラウト対決で世界一"),
            ],
            "イチロー": [
                KeyMoment(27, 2001, "MLB新人王・MVP同時受賞", MomentType.BREAKTHROUGH, 9.0, "日本人野手の道を開く"),
                KeyMoment(30, 2004, "年間262安打", MomentType.HISTORIC_RECORD, 10.0, "84年ぶりの記録更新"),
                KeyMoment(45, 2019, "引退", MomentType.CULMINATION, 8.0, "4367安打の集大成"),
            ],
            "藤井聡太": [
                KeyMoment(14, 2016, "プロデビュー29連勝", MomentType.BREAKTHROUGH, 9.0, "最年少プロ入り"),
                KeyMoment(17, 2020, "最年少タイトル", MomentType.HISTORIC_RECORD, 9.5, "棋聖獲得"),
                KeyMoment(19, 2021, "最年少五冠", MomentType.PEAK_ACHIEVEMENT, 10.0, "将棋界新時代"),
            ],
            "宮崎駿": [
                KeyMoment(47, 1988, "となりのトトロ", MomentType.BREAKTHROUGH, 8.5, "ジブリブランド確立"),
                KeyMoment(56, 1997, "もののけ姫", MomentType.SOCIAL_PHENOMENON, 9.0, "興行新記録"),
                KeyMoment(60, 2001, "千と千尋の神隠し", MomentType.WORLD_CHANGE, 10.0, "アカデミー賞受賞"),
            ],
            "村上春樹": [
                KeyMoment(30, 1979, "風の歌を聴け", MomentType.LIFE_TURNING, 7.0, "作家デビュー"),
                KeyMoment(38, 1987, "ノルウェイの森", MomentType.SOCIAL_PHENOMENON, 10.0, "430万部の社会現象"),
                KeyMoment(50, 1999, "海外での評価確立", MomentType.WORLD_CHANGE, 8.5, "世界的作家へ"),
            ],
            "羽生結弦": [
                KeyMoment(19, 2014, "ソチ五輪金メダル", MomentType.BREAKTHROUGH, 9.0, "日本男子初の金"),
                KeyMoment(23, 2018, "平昌五輪連覇", MomentType.HISTORIC_RECORD, 10.0, "66年ぶりの連覇"),
                KeyMoment(27, 2022, "北京五輪4回転アクセル", MomentType.PEAK_ACHIEVEMENT, 8.5, "挑戦の極致"),
            ],
            "山中伸弥": [
                KeyMoment(44, 2006, "iPS細胞作製成功", MomentType.BREAKTHROUGH, 9.5, "再生医療の扉"),
                KeyMoment(50, 2012, "ノーベル賞受賞", MomentType.WORLD_CHANGE, 10.0, "医学革命の承認"),
            ],
            "HIKAKIN": [
                KeyMoment(22, 2011, "YouTube本格開始", MomentType.LIFE_TURNING, 7.0, "会社員から転身"),
                KeyMoment(28, 2017, "登録者500万人", MomentType.BREAKTHROUGH, 8.5, "日本トップYouTuber"),
                KeyMoment(30, 2019, "登録者800万人", MomentType.NEW_PARADIGM, 9.0, "YouTuber職業確立"),
            ],
        }

    def select_optimal_age(self, person_name: str,
                          available_facts: Dict = None) -> Tuple[int, str]:
        """
        最適な年齢を選択

        Args:
            person_name: 人物名
            available_facts: 利用可能な事実データ

        Returns:
            (年齢, 選択理由)
        """
        # データベースに登録済みの人物
        if person_name in self.key_moments_db:
            moments = self.key_moments_db[person_name]

            # スコア計算（影響度 × タイプ重み）
            best_moment = None
            best_score = 0

            for moment in moments:
                score = moment.impact_score * self.moment_weights[moment.moment_type]
                if score > best_score:
                    best_score = score
                    best_moment = moment

            if best_moment:
                return best_moment.age, f"{best_moment.event}（{best_moment.moment_type.value}）"

        # データベースにない場合は、事実から推測
        if available_facts:
            return self._infer_from_facts(person_name, available_facts)

        # デフォルト
        return 30, "標準的な成功年齢"

    def _infer_from_facts(self, person_name: str, facts: Dict) -> Tuple[int, str]:
        """
        事実データから最適年齢を推測

        Args:
            person_name: 人物名
            facts: 事実データ

        Returns:
            (年齢, 選択理由)
        """
        # キーワードベースの推測ロジック
        age_hints = []

        # 全事実をスキャン
        for category, fact_list in facts.items():
            for fact in fact_list:
                # 特定のパターンを探す
                if "最年少" in fact:
                    # 最年少記録は若い年齢
                    import re
                    age_match = re.search(r'(\d+)歳', fact)
                    if age_match:
                        age_hints.append((int(age_match.group(1)), "最年少記録"))

                elif "引退" in fact:
                    # 引退は晩年
                    age_hints.append((45, "引退・集大成"))

                elif "デビュー" in fact or "初" in fact:
                    # デビューは早い時期
                    age_hints.append((25, "デビュー・突破口"))

                elif "優勝" in fact or "金メダル" in fact:
                    # 優勝は全盛期
                    age_hints.append((28, "優勝・頂点"))

                elif "ノーベル" in fact:
                    # ノーベル賞は研究の集大成
                    age_hints.append((50, "ノーベル賞・世界的評価"))

        # 最も適切な年齢を選択
        if age_hints:
            # 最も具体的な理由を持つ年齢を選択
            return age_hints[0]

        # カテゴリーベースのデフォルト
        category_defaults = {
            "sports": (28, "アスリートの全盛期"),
            "entertainment": (30, "エンタメ界での確立"),
            "business": (40, "ビジネス成功期"),
            "politics": (50, "政治的影響力"),
            "science": (45, "研究成果の結実"),
            "music": (27, "音楽的成熟"),
            "art": (35, "芸術的円熟"),
        }

        # カテゴリから推定
        person_category = facts.get("category", "").lower()
        for cat, (age, reason) in category_defaults.items():
            if cat in person_category:
                return age, reason

        return 30, "一般的な成功年齢"

    def get_moment_timeline(self, person_name: str) -> List[str]:
        """
        人物の重要瞬間タイムラインを取得

        Args:
            person_name: 人物名

        Returns:
            タイムライン文字列のリスト
        """
        if person_name not in self.key_moments_db:
            return []

        moments = sorted(self.key_moments_db[person_name], key=lambda m: m.age)
        timeline = []

        for moment in moments:
            year_str = f"({moment.year}年)" if moment.year else ""
            timeline.append(
                f"{moment.age}歳{year_str}: {moment.event} - {moment.description}"
            )

        return timeline


def test_optimal_age_selector():
    """テスト実行"""
    selector = OptimalAgeSelector()

    # テスト対象
    test_persons = [
        "大谷翔平",
        "イチロー",
        "藤井聡太",
        "宮崎駿",
        "村上春樹",
        "羽生結弦",
        "山中伸弥",
        "HIKAKIN",
    ]

    print("最適年齢選択テスト")
    print("="*60)

    for person in test_persons:
        age, reason = selector.select_optimal_age(person)
        print(f"\n{person}:")
        print(f"  最適年齢: {age}歳")
        print(f"  選択理由: {reason}")

        # タイムライン表示
        timeline = selector.get_moment_timeline(person)
        if timeline:
            print(f"  タイムライン:")
            for event in timeline:
                print(f"    - {event}")


if __name__ == "__main__":
    test_optimal_age_selector()
