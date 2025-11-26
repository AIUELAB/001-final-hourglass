#!/usr/bin/env python3
"""
グループ所属判定モジュール

人物名からグループ所属を判定し、group_name と is_group_member を返す。

フォーマット仕様:
- 所属: is_group_member=True, group_name=グループ名
- 無所属: is_group_member=False, group_name=None
- 未判定: is_group_member=None, group_name=None
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class GroupCategory(Enum):
    """グループカテゴリ"""

    MUSIC_BAND = "音楽バンド"
    MUSIC_UNIT = "音楽ユニット"
    IDOL_GROUP = "アイドルグループ"
    COMEDY_DUO = "お笑いコンビ"
    COMEDY_TRIO = "お笑いトリオ"
    YOUTUBE_GROUP = "YouTubeグループ"
    SPORTS_TEAM = "スポーツチーム"
    COMPANY = "企業"
    OTHER = "その他"


@dataclass
class GroupInfo:
    """グループ情報"""

    group_name: str
    category: GroupCategory
    is_active: bool = True  # 活動中かどうか
    disbanded_year: Optional[int] = None  # 解散年


# ========================================
# グループメンバーマスタ
# ========================================

GROUP_MEMBER_MAP: Dict[str, str] = {
    # ===== 音楽グループ =====
    # Mr.Children
    "桜井和寿": "Mr.Children",
    "田原健一": "Mr.Children",
    "中川敬輔": "Mr.Children",
    "鈴木英哉": "Mr.Children",
    # B'z
    "稲葉浩志": "B'z",
    "松本孝弘": "B'z",
    # サザンオールスターズ
    "桑田佳祐": "サザンオールスターズ",
    "原由子": "サザンオールスターズ",
    "関口和之": "サザンオールスターズ",
    "松田弘": "サザンオールスターズ",
    "野沢秀行": "サザンオールスターズ",
    # L'Arc~en~Ciel
    "hyde": "L'Arc~en~Ciel",
    "ken": "L'Arc~en~Ciel",
    "tetsuya": "L'Arc~en~Ciel",
    "yukihiro": "L'Arc~en~Ciel",
    # スピッツ
    "草野マサムネ": "スピッツ",
    "三輪テツヤ": "スピッツ",
    "田村明浩": "スピッツ",
    "﨑山龍男": "スピッツ",
    # DREAMS COME TRUE
    "吉田美和": "DREAMS COME TRUE",
    "中村正人": "DREAMS COME TRUE",
    # LUNA SEA
    "河村隆一": "LUNA SEA",
    "SUGIZO": "LUNA SEA",
    "INORAN": "LUNA SEA",
    "J": "LUNA SEA",
    "真矢": "LUNA SEA",
    # 黒夢
    "清春": "黒夢",
    "人時": "黒夢",
    # X JAPAN
    "YOSHIKI": "X JAPAN",
    "TOSHI": "X JAPAN",
    "PATA": "X JAPAN",
    "HEATH": "X JAPAN",
    # GLAY
    "TERU": "GLAY",
    "TAKURO": "GLAY",
    "HISASHI": "GLAY",
    "JIRO": "GLAY",
    # ゆず
    "北川悠仁": "ゆず",
    "岩沢厚治": "ゆず",
    # コブクロ
    "小渕健太郎": "コブクロ",
    "黒田俊介": "コブクロ",
    # EXILE
    "ATSUSHI": "EXILE",
    "TAKAHIRO": "EXILE",
    "AKIRA": "EXILE",
    "HIRO": "EXILE",
    # 三代目 J SOUL BROTHERS
    "登坂広臣": "三代目 J SOUL BROTHERS",
    "今市隆二": "三代目 J SOUL BROTHERS",
    # ===== お笑いグループ =====
    # ダウンタウン
    "松本人志": "ダウンタウン",
    "浜田雅功": "ダウンタウン",
    # ナインティナイン
    "岡村隆史": "ナインティナイン",
    "矢部浩之": "ナインティナイン",
    # キングコング
    "西野亮廣": "キングコング",
    "梶原雄太": "キングコング",
    # ピース
    "又吉直樹": "ピース",
    "綾部祐二": "ピース",
    # オードリー
    "若林正恭": "オードリー",
    "春日俊彰": "オードリー",
    # サンドウィッチマン
    "伊達みきお": "サンドウィッチマン",
    "富澤たけし": "サンドウィッチマン",
    # 千鳥
    "大悟": "千鳥",
    "ノブ": "千鳥",
    # かまいたち
    "山内健司": "かまいたち",
    "濱家隆一": "かまいたち",
    # 霜降り明星
    "粗品": "霜降り明星",
    "せいや": "霜降り明星",
    # ===== アイドルグループ =====
    # 嵐
    "大野智": "嵐",
    "櫻井翔": "嵐",
    "相葉雅紀": "嵐",
    "二宮和也": "嵐",
    "松本潤": "嵐",
    # SMAP（解散）
    "中居正広": "SMAP",
    "木村拓哉": "SMAP",
    "稲垣吾郎": "SMAP",
    "草彅剛": "SMAP",
    "香取慎吾": "SMAP",
    # V6（解散）
    "坂本昌行": "V6",
    "長野博": "V6",
    "井ノ原快彦": "V6",
    "森田剛": "V6",
    "三宅健": "V6",
    "岡田准一": "V6",
    # TOKIO
    "城島茂": "TOKIO",
    "国分太一": "TOKIO",
    "松岡昌宏": "TOKIO",
    # KinKi Kids
    "堂本光一": "KinKi Kids",
    "堂本剛": "KinKi Kids",
    # King & Prince
    "平野紫耀": "King & Prince",
    "永瀬廉": "King & Prince",
    "高橋海人": "King & Prince",
    # SKE48
    "松井珠理奈": "SKE48",
    "松井玲奈": "SKE48",
    "高柳明音": "SKE48",
    # 乃木坂46
    "白石麻衣": "乃木坂46",
    "西野七瀬": "乃木坂46",
    "生田絵梨花": "乃木坂46",
    "齋藤飛鳥": "乃木坂46",
    # 欅坂46/櫻坂46
    "平手友梨奈": "欅坂46",
    # モーニング娘。
    "安倍なつみ": "モーニング娘。",
    "後藤真希": "モーニング娘。",
    # AKB48
    "前田敦子": "AKB48",
    "大島優子": "AKB48",
    "篠田麻里子": "AKB48",
    "板野友美": "AKB48",
    "指原莉乃": "AKB48",
    # ===== YouTubeグループ =====
    # Fischer's
    "シルクロード": "Fischer's",
    # 東海オンエア
    "てつや": "東海オンエア",
    # ===== 企業・スポーツチーム =====
    # （既存データから）
    "前田晃伸": "みずほフィナンシャルグループ",
    "藤沢武夫": "本田技研工業",
    "森稔": "森ビル",
    "堤義明": "西武グループ",
    "川上哲治": "読売ジャイアンツ",
    "落合博満": "ロッテオリオンズ",
}

# ========================================
# グループ本体（person_name がグループ名そのもの）
# ========================================

GROUP_ENTITIES: Set[str] = {
    "嵐",
    "SMAP",
    "V6",
    "TOKIO",
    "ダウンタウン",
    "ナインティナイン",
    "ウッチャンナンチャン",
    "とんねるず",
    "爆笑問題",
    "ドリカム",
    "B'z",
    "Mr.Children",
    "サザンオールスターズ",
    "モーニング娘。",
    "AKB48",
    "乃木坂46",
    "EXILE",
}

# ========================================
# ソロアーティスト（明示的に無所属）
# ========================================

SOLO_ARTISTS: Set[str] = {
    # シンガーソングライター
    "宇多田ヒカル",
    "松任谷由実",
    "山下達郎",
    "長渕剛",
    "槇原敬之",
    "大黒摩季",
    "福山雅治",
    "桑田佳祐",  # ソロ活動時
    "浜崎あゆみ",
    "倖田來未",
    "MISIA",
    "aiko",
    "椎名林檎",
    "Superfly",
    "あいみょん",
    "米津玄師",
    "星野源",
    "back number",
    "YOASOBI",
    "Ado",
    # 演歌・歌謡
    "美空ひばり",
    "北島三郎",
    "五木ひろし",
    "石川さゆり",
    "坂本冬美",
    # ピン芸人
    "明石家さんま",
    "タモリ",
    "ビートたけし",
    "志村けん",
    "所ジョージ",
    "有吉弘行",
    "マツコ・デラックス",
    "渡辺直美",
}

# ========================================
# グループ詳細情報
# ========================================

GROUP_DETAILS: Dict[str, GroupInfo] = {
    "Mr.Children": GroupInfo("Mr.Children", GroupCategory.MUSIC_BAND),
    "B'z": GroupInfo("B'z", GroupCategory.MUSIC_UNIT),
    "サザンオールスターズ": GroupInfo("サザンオールスターズ", GroupCategory.MUSIC_BAND),
    "L'Arc~en~Ciel": GroupInfo("L'Arc~en~Ciel", GroupCategory.MUSIC_BAND),
    "スピッツ": GroupInfo("スピッツ", GroupCategory.MUSIC_BAND),
    "DREAMS COME TRUE": GroupInfo("DREAMS COME TRUE", GroupCategory.MUSIC_UNIT),
    "LUNA SEA": GroupInfo("LUNA SEA", GroupCategory.MUSIC_BAND),
    "黒夢": GroupInfo("黒夢", GroupCategory.MUSIC_BAND, is_active=False),
    "X JAPAN": GroupInfo("X JAPAN", GroupCategory.MUSIC_BAND),
    "GLAY": GroupInfo("GLAY", GroupCategory.MUSIC_BAND),
    "ダウンタウン": GroupInfo("ダウンタウン", GroupCategory.COMEDY_DUO),
    "ナインティナイン": GroupInfo("ナインティナイン", GroupCategory.COMEDY_DUO),
    "キングコング": GroupInfo("キングコング", GroupCategory.COMEDY_DUO),
    "ピース": GroupInfo("ピース", GroupCategory.COMEDY_DUO),
    "オードリー": GroupInfo("オードリー", GroupCategory.COMEDY_DUO),
    "サンドウィッチマン": GroupInfo("サンドウィッチマン", GroupCategory.COMEDY_DUO),
    "嵐": GroupInfo("嵐", GroupCategory.IDOL_GROUP, is_active=False, disbanded_year=2020),
    "SMAP": GroupInfo("SMAP", GroupCategory.IDOL_GROUP, is_active=False, disbanded_year=2016),
    "V6": GroupInfo("V6", GroupCategory.IDOL_GROUP, is_active=False, disbanded_year=2021),
    "TOKIO": GroupInfo("TOKIO", GroupCategory.IDOL_GROUP),
    "KinKi Kids": GroupInfo("KinKi Kids", GroupCategory.IDOL_GROUP),
    "SKE48": GroupInfo("SKE48", GroupCategory.IDOL_GROUP),
    "乃木坂46": GroupInfo("乃木坂46", GroupCategory.IDOL_GROUP),
    "AKB48": GroupInfo("AKB48", GroupCategory.IDOL_GROUP),
    "モーニング娘。": GroupInfo("モーニング娘。", GroupCategory.IDOL_GROUP),
}


def get_group_info(person_name: str, person_type: Optional[str] = None) -> Tuple[Optional[str], Optional[bool]]:
    """
    人物名からグループ情報を取得

    Args:
        person_name: 人物名
        person_type: 人物タイプ（REAL/FICTIONAL）

    Returns:
        (group_name, is_group_member)
        - 所属: (グループ名, True)
        - 無所属: (None, False)
        - 未判定: (None, None)
    """
    # 架空キャラクターは対象外
    if person_type and person_type.upper() == "FICTIONAL":
        return None, False

    # グループ本体
    if person_name in GROUP_ENTITIES:
        return None, None  # GROUP扱い（特殊ケース）

    # ソロアーティスト
    if person_name in SOLO_ARTISTS:
        return None, False

    # マスタから検索
    if person_name in GROUP_MEMBER_MAP:
        return GROUP_MEMBER_MAP[person_name], True

    # 未判定
    return None, None


def get_group_details(group_name: str) -> Optional[GroupInfo]:
    """
    グループ名から詳細情報を取得

    Args:
        group_name: グループ名

    Returns:
        GroupInfo または None
    """
    return GROUP_DETAILS.get(group_name)


def get_group_members(group_name: str) -> List[str]:
    """
    グループ名からメンバー一覧を取得

    Args:
        group_name: グループ名

    Returns:
        メンバー名のリスト
    """
    return [name for name, group in GROUP_MEMBER_MAP.items() if group == group_name]


def is_solo_artist(person_name: str) -> bool:
    """
    ソロアーティストかどうか判定

    Args:
        person_name: 人物名

    Returns:
        ソロアーティストならTrue
    """
    return person_name in SOLO_ARTISTS


def is_group_entity(person_name: str) -> bool:
    """
    グループ本体（person_name=グループ名）かどうか判定

    Args:
        person_name: 人物名

    Returns:
        グループ本体ならTrue
    """
    return person_name in GROUP_ENTITIES


# ========================================
# 統計情報
# ========================================


def get_statistics() -> Dict[str, int]:
    """
    マスタの統計情報を取得

    Returns:
        統計情報の辞書
    """
    unique_groups = set(GROUP_MEMBER_MAP.values())
    return {
        "total_members": len(GROUP_MEMBER_MAP),
        "unique_groups": len(unique_groups),
        "group_entities": len(GROUP_ENTITIES),
        "solo_artists": len(SOLO_ARTISTS),
    }


if __name__ == "__main__":
    # テスト
    print("=" * 60)
    print("グループマスタ統計")
    print("=" * 60)

    stats = get_statistics()
    print(f"登録メンバー数: {stats['total_members']}")
    print(f"ユニークグループ数: {stats['unique_groups']}")
    print(f"グループエンティティ数: {stats['group_entities']}")
    print(f"ソロアーティスト数: {stats['solo_artists']}")

    print("\n" + "=" * 60)
    print("グループ判定テスト")
    print("=" * 60)

    test_cases = [
        ("桜井和寿", "REAL"),
        ("松本人志", "REAL"),
        ("大野智", "REAL"),
        ("宇多田ヒカル", "REAL"),
        ("毛利蘭", "FICTIONAL"),
        ("嵐", "REAL"),  # グループ本体
        ("田中太郎", "REAL"),  # 未登録
    ]

    for name, ptype in test_cases:
        group_name, is_member = get_group_info(name, ptype)
        if is_member is True:
            status = f"所属 → {group_name}"
        elif is_member is False:
            status = "無所属"
        else:
            status = "未判定"
        print(f"  {name} ({ptype}): {status}")
