#!/usr/bin/env python3
"""
RULE_201: 代表作必須ルール

石ノ森章太郎事例から導出された品質ゲート
- 人物ごとに「代表作リスト」をマスターデータとして保持
- エピソード生成時、代表作が1つ以上含まれることを必須化
- 代表作が含まれない場合、品質ゲートでブロック

Phase: 品質ゲート強化（RULE_200-206）
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MasterworkInfo:
    """代表作情報"""
    person_name: str
    category: str
    masterworks: List[str]  # 代表作リスト
    keywords: List[str]  # 検出用キーワード


# 代表作マスターデータ（サンプル - 拡張可能）
MASTERWORK_DATABASE: List[MasterworkInfo] = [
    # === 漫画家 ===
    MasterworkInfo(
        "石ノ森章太郎",
        "漫画家",
        ["仮面ライダー", "サイボーグ009", "人造人間キカイダー", "秘密戦隊ゴレンジャー"],
        ["仮面ライダー", "サイボーグ", "キカイダー", "ゴレンジャー", "ギネス", "萬画"]
    ),
    MasterworkInfo(
        "手塚治虫",
        "漫画家",
        ["鉄腕アトム", "ブラック・ジャック", "火の鳥", "ジャングル大帝", "リボンの騎士"],
        ["アトム", "ブラック・ジャック", "火の鳥", "ジャングル大帝", "リボンの騎士"]
    ),
    MasterworkInfo(
        "宮崎駿",
        "アニメーション監督",
        ["風の谷のナウシカ", "天空の城ラピュタ", "となりのトトロ", "もののけ姫", "千と千尋の神隠し"],
        ["ナウシカ", "ラピュタ", "トトロ", "もののけ姫", "千と千尋", "ジブリ"]
    ),
    MasterworkInfo(
        "鳥山明",
        "漫画家",
        ["ドラゴンボール", "Dr.スランプ"],
        ["ドラゴンボール", "Dr.スランプ", "アラレちゃん", "悟空", "鳥山"]
    ),
    MasterworkInfo(
        "尾田栄一郎",
        "漫画家",
        ["ONE PIECE"],
        ["ONE PIECE", "ワンピース", "ルフィ"]
    ),

    # === 映画監督 ===
    MasterworkInfo(
        "黒澤明",
        "映画監督",
        ["七人の侍", "羅生門", "生きる", "用心棒", "乱"],
        ["七人の侍", "羅生門", "生きる", "用心棒", "乱"]
    ),
    MasterworkInfo(
        "小津安二郎",
        "映画監督",
        ["東京物語", "晩春", "秋刀魚の味"],
        ["東京物語", "晩春", "秋刀魚の味"]
    ),

    # === 作家 ===
    MasterworkInfo(
        "夏目漱石",
        "作家",
        ["坊っちゃん", "吾輩は猫である", "こころ", "三四郎"],
        ["坊っちゃん", "吾輩は猫である", "こころ", "三四郎"]
    ),
    MasterworkInfo(
        "村上春樹",
        "作家",
        ["ノルウェイの森", "1Q84", "海辺のカフカ", "ねじまき鳥クロニクル"],
        ["ノルウェイの森", "1Q84", "海辺のカフカ", "ねじまき鳥"]
    ),

    # === 音楽家 ===
    MasterworkInfo(
        "坂本龍一",
        "音楽家",
        ["戦場のメリークリスマス", "ラストエンペラー", "YMO"],
        ["戦メリ", "ラストエンペラー", "YMO", "Yellow Magic Orchestra"]
    ),

    # === 音楽家（コンクール入賞者） ===
    MasterworkInfo(
        "内田光子",
        "ピアニスト",
        ["シューベルト", "モーツァルト", "ベートーヴェン"],
        ["リーズ国際", "ショパンコンクール", "グラミー賞", "指揮者"]
    ),
    MasterworkInfo(
        "諏訪内晶子",
        "ヴァイオリニスト",
        ["チャイコフスキー", "ストラディヴァリウス"],
        ["チャイコフスキーコンクール", "最年少優勝", "ドルフィン"]
    ),
    MasterworkInfo(
        "反田恭平",
        "ピアニスト",
        ["ショパン", "ラフマニノフ"],
        ["ショパンコンクール", "2位入賞", "Japan National Orchestra"]
    ),
    MasterworkInfo(
        "中村紘子",
        "ピアニスト",
        ["ショパン", "チャイコフスキー"],
        ["ショパンコンクール", "日本人初入賞", "NHK交響楽団"]
    ),

    # === 児童文学作家 ===
    MasterworkInfo(
        "角野栄子",
        "児童文学作家",
        ["魔女の宅急便", "アッチ・コッチ・ソッチ"],
        ["魔女の宅急便", "アンデルセン賞", "国際アンデルセン"]
    ),
    MasterworkInfo(
        "上橋菜穂子",
        "児童文学作家",
        ["精霊の守り人", "獣の奏者", "鹿の王"],
        ["守り人シリーズ", "アンデルセン賞", "国際アンデルセン", "本屋大賞"]
    ),
    MasterworkInfo(
        "安野光雅",
        "絵本作家",
        ["ふしぎなえ", "旅の絵本", "ABCの本"],
        ["アンデルセン賞", "国際アンデルセン", "ケイト・グリーナウェイ賞"]
    ),
    MasterworkInfo(
        "まど・みちお",
        "詩人",
        ["ぞうさん", "やぎさんゆうびん", "ふしぎなポケット"],
        ["アンデルセン賞", "国際アンデルセン", "童謡"]
    ),
]


class MasterworkChecker:
    """代表作チェッカー"""

    def __init__(self):
        self.database = MASTERWORK_DATABASE
        self._build_person_index()

    def _build_person_index(self):
        """人物名インデックスを構築"""
        self.person_to_masterwork: Dict[str, MasterworkInfo] = {}
        for info in self.database:
            self.person_to_masterwork[info.person_name] = info

    def get_masterworks(self, person_name: str) -> Optional[MasterworkInfo]:
        """人物の代表作情報を取得"""
        return self.person_to_masterwork.get(person_name)

    def check_masterwork_coverage(
        self,
        person_name: str,
        episodes: List[str]
    ) -> Dict:
        """
        代表作の網羅性をチェック

        Args:
            person_name: 人物名
            episodes: エピソードテキストのリスト

        Returns:
            チェック結果
        """
        masterwork_info = self.get_masterworks(person_name)

        # データベースに登録されていない人物は警告のみ
        if not masterwork_info:
            return {
                "passed": True,  # 登録なしは通過
                "person_name": person_name,
                "status": "not_in_database",
                "message": "代表作データベースに未登録",
                "rule_id": "RULE_201",
                "rule_name": "代表作必須ルール"
            }

        # エピソードから代表作・キーワードを検出
        all_text = " ".join(episodes)
        covered_masterworks: Set[str] = set()
        covered_keywords: Set[str] = set()

        for masterwork in masterwork_info.masterworks:
            if masterwork in all_text:
                covered_masterworks.add(masterwork)

        for keyword in masterwork_info.keywords:
            if keyword in all_text:
                covered_keywords.add(keyword)

        # 判定: 代表作またはキーワードが1つ以上含まれているか
        has_masterwork = len(covered_masterworks) > 0
        has_keyword = len(covered_keywords) > 0
        passed = has_masterwork or has_keyword

        # 不足している代表作
        missing_masterworks = [
            mw for mw in masterwork_info.masterworks
            if mw not in covered_masterworks
        ]

        return {
            "passed": passed,
            "person_name": person_name,
            "category": masterwork_info.category,
            "covered_masterworks": list(covered_masterworks),
            "covered_keywords": list(covered_keywords),
            "missing_masterworks": missing_masterworks,
            "total_masterworks": len(masterwork_info.masterworks),
            "coverage_rate": len(covered_masterworks) / len(masterwork_info.masterworks) * 100,
            "rule_id": "RULE_201",
            "rule_name": "代表作必須ルール"
        }

    def add_person(self, person_name: str, category: str, masterworks: List[str], keywords: List[str]):
        """
        人物を代表作データベースに追加

        Args:
            person_name: 人物名
            category: カテゴリ
            masterworks: 代表作リスト
            keywords: 検出用キーワード
        """
        info = MasterworkInfo(person_name, category, masterworks, keywords)
        self.database.append(info)
        self.person_to_masterwork[person_name] = info
        logger.info(f"✅ 代表作データベースに追加: {person_name}")


# グローバルインスタンス
masterwork_checker = MasterworkChecker()


def check_masterwork_required(person_name: str, episodes: List[str]) -> Dict:
    """
    代表作必須チェック（外部インターフェース）

    Args:
        person_name: 人物名
        episodes: エピソードテキストのリスト

    Returns:
        チェック結果
    """
    return masterwork_checker.check_masterwork_coverage(person_name, episodes)


if __name__ == "__main__":
    # テスト
    print("=" * 60)
    print("RULE_201: 代表作必須ルール - テスト")
    print("=" * 60)

    # テストケース1: 石ノ森章太郎（代表作なし）
    test1_episodes = [
        "あなたと同じ38歳のとき、石ノ森章太郎は芸術・文化分野において画期的な成果を達成しました。"
    ]
    result1 = check_masterwork_required("石ノ森章太郎", test1_episodes)

    print(f"\n【テスト1】{result1['person_name']}")
    print(f"判定: {'✅ 合格' if result1['passed'] else '❌ 不合格'}")
    print(f"カバー済み代表作: {result1.get('covered_masterworks', [])}")
    print(f"不足代表作: {result1.get('missing_masterworks', [])}")

    # テストケース2: 石ノ森章太郎（代表作あり）
    test2_episodes = [
        "あなたと同じ33歳のとき、石ノ森章太郎は仮面ライダーの原作を発表し、特撮ヒーローの新時代を切り開いた。"
    ]
    result2 = check_masterwork_required("石ノ森章太郎", test2_episodes)

    print(f"\n【テスト2】{result2['person_name']}")
    print(f"判定: {'✅ 合格' if result2['passed'] else '❌ 不合格'}")
    print(f"カバー済み代表作: {result2.get('covered_masterworks', [])}")
    print(f"カバー率: {result2.get('coverage_rate', 0):.1f}%")

    # テストケース3: 未登録人物
    test3_episodes = ["テストエピソード"]
    result3 = check_masterwork_required("未登録の人物", test3_episodes)

    print(f"\n【テスト3】{result3['person_name']}")
    print(f"判定: {result3.get('status', '')} - {result3.get('message', '')}")
