#!/usr/bin/env python3
"""
グループエンティティ定義モジュール

グループカテゴリ、グループ情報、グループエンティティ、ソロアーティストを定義。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Set


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
# グループ本体（person_name がグループ名そのもの）
# ========================================

GROUP_ENTITIES: Set[str] = {
    # ===== 日本のアイドルグループ =====
    "嵐",
    "SMAP",
    "V6",
    "TOKIO",
    "KinKi Kids",
    "AKB48",
    "SKE48",
    "NMB48",
    "HKT48",
    "乃木坂46",
    "欅坂46",
    "櫻坂46",
    "日向坂46",
    "モーニング娘。",
    "King & Prince",
    "SixTONES",
    "Snow Man",
    "Hey! Say! JUMP",
    "NEWS",
    "関ジャニ∞",
    "Kis-My-Ft2",
    "ももいろクローバーZ",
    "でんぱ組.inc",
    # ===== 日本の音楽グループ =====
    "B'z",
    "Mr.Children",
    "サザンオールスターズ",
    "DREAMS COME TRUE",
    "ドリカム",
    "EXILE",
    "DA PUMP",
    "三代目 J SOUL BROTHERS",
    "三代目J Soul Brothers",  # 表記ゆれ対応
    "L'Arc~en~Ciel",
    "ラルクアンシエル",
    "X JAPAN",
    "GLAY",
    "LUNA SEA",
    "スピッツ",
    "ゆず",
    "コブクロ",
    "Official髭男dism",
    "Perfume",
    "SEKAI NO OWARI",
    "King Gnu",
    "ONE OK ROCK",
    "RADWIMPS",
    "YOASOBI",
    "back number",
    # ===== 海外ロック/ポップバンド =====
    "Radiohead",
    "Nirvana",
    "Alice in Chains",
    "Soundgarden",
    "Metallica",
    # ===== お笑いグループ =====
    "ダウンタウン",
    "ナインティナイン",
    "NON STYLE",
    "ウッチャンナンチャン",
    "とんねるず",
    "爆笑問題",
    "サンドウィッチマン",
    "オードリー",
    "千鳥",
    "かまいたち",
    "霜降り明星",
    "ミルクボーイ",
    "バナナマン",
    "おぎやはぎ",
    "ザ・ドリフターズ",
    "笑点メンバー",
    "EXIT",
    "おかずクラブ",
    "ぺこぱ",
    "南海キャンディーズ",
    "くりぃむしちゅー",
    # ===== 日本のバンド（追加） =====
    "ゴールデンボンバー",
    "ORANGE RANGE",
    "SADS",
    "Superfly",
    "THE BLUE HEARTS",
    # ===== スポーツチーム =====
    "清水エスパルス",
    "湘南ベルマーレ",
    # ===== 学校チーム =====
    "星稜高校",
    "東海大学相模",
    # ===== 研究・開発チーム =====
    "青色LED開発チーム",
    "ASIMO開発チーム",
    # ===== 海外バンド =====
    "ビートルズ",
    "The Beatles",
    "Beatles",
    "ローリング・ストーンズ",
    "The Rolling Stones",
    "クイーン",
    "Queen",
    "レッド・ツェッペリン",
    "Led Zeppelin",
    "ピンク・フロイド",
    "Pink Floyd",
    "U2",
    "コールドプレイ",
    "Coldplay",
    "マルーン5",
    "Maroon 5",
    "ワン・ダイレクション",
    "One Direction",
    # ===== K-POP =====
    "BTS",
    "防弾少年団",
    "BLACKPINK",
    "ブラックピンク",
    "TWICE",
    "トゥワイス",
    "EXO",
    "NCT",
    "SEVENTEEN",
    "Stray Kids",
    "aespa",
    "IVE",
    "NewJeans",
    "LE SSERAFIM",
    # ===== VTuberグループ =====
    "ホロライブ",
    "hololive",
    "にじさんじ",
    "NIJISANJI",
    "VShojo",
    # ===== YouTubeグループ =====
    "東海オンエア",
    "Fischer's",
    "フィッシャーズ",  # Fischer'sの日本語表記
    "コムドット",
    "QuizKnock",
    "水溜りボンド",
    "兄者弟者",
    # ===== その他団体 =====
    "宝塚歌劇団",
    "劇団四季",
    # ===== Phase 5追加: 学校チーム =====
    "智弁和歌山",
    "流経大柏高校",
    "駒大苫小牧",
    "早稲田実業",
    # ===== Phase 5追加: 家族グループ =====
    "阿部兄妹",
    # ===== Phase 5追加: 兄弟パターン =====
    "ライト兄弟",
    "コーエン兄弟",
    # ===== Phase 5追加: 創業者チーム =====
    "富士フイルム創業者",
    "島津製作所創業者",
    # ===== Phase 5追加: 音楽グループ（Web検索で確認） =====
    "竹内電気",  # ポップバンド
    "真心ブラザーズ",  # 音楽ユニット
    # ===== Phase 6追加: 音楽バンド =====
    "野猿",  # とんねるずプロデュースの音楽グループ
    "デレク・アンド・ザ・ドミノス",  # エリック・クラプトンのバンド
    "カーペンターズ",  # 兄妹音楽デュオ
    "イーグルス",  # アメリカンロックバンド
    "フリートウッド・マック",  # イギリス系ロックバンド
    "ケミカル・ブラザーズ",  # イギリスのエレクトロニックデュオ
    "バンク・バンド",  # 桜井和寿のプロジェクトバンド
    # ===== Phase 6追加: 夫妻グループ =====
    "キュリー夫妻",  # 科学者夫妻
    # ===== Phase 7追加: v5グループ =====
    # お笑いコンビ
    "浅草キッド",  # お笑いコンビ
    # 漫画家コンビ
    "藤子不二雄",  # 漫画家コンビ
    # 音楽グループ
    "サイモン&ガーファンクル",  # フォークロックデュオ
    "ゴスペラーズ",  # アカペラグループ
    "ガンズ・アンド・ローゼズ",  # ハードロックバンド
    "オレンジレンジ",  # 沖縄ロックバンド
    "サッズ",  # ロックバンド（SADS）
    "ザ・キュアー",  # イギリスロックバンド
    "ニルヴァーナ",  # グランジバンド
    "パール・ジャム",  # グランジバンド
    "アリス・イン・チェインズ",  # グランジバンド
    "サウンドガーデン",  # グランジバンド
    "フー・ファイターズ",  # ロックバンド
    "グリーン・デイ",  # パンクバンド
    "メタリカ",  # メタルバンド
    "AC/DC",  # ハードロックバンド
    "ブルーハーツ",  # パンクバンド
    "かりゆし58",  # 沖縄ロックバンド
}

# ========================================
# ソロアーティスト（明示的に無所属）
# ========================================

SOLO_ARTISTS: Set[str] = {
    # 漫画家・アニメ監督
    "石ノ森章太郎",
    "赤塚不二夫",
    "ちばてつや",
    "山田玲司",
    "庵野秀明",
    # 一般・その他（LLM補完で確認済みソロ）
    "西村嘉央",
    "福井谷祐子",
    "田中信行",
    "山田恵子",
    "小川桂子",
    "北野日奈子",  # 注: 同名の乃木坂46メンバーとは別人（学術分野）
    # シンガーソングライター
    "宇多田ヒカル",
    # 松任谷由実: ソロ活動が主だがユーミンとしてカテゴリ外
    # 山下達郎: グループ「シュガー・ベイブ」出身だがソロが主
    "長渕剛",
    # 槇原敬之: ソロアーティスト
    # 大黒摩季: ソロアーティスト
    "福山雅治",
    # 桑田佳祐: サザンオールスターズのメンバーとしてGROUP_MEMBER_MAPに登録
    "浜崎あゆみ",
    "倖田來未",
    "MISIA",
    "aiko",
    "椎名林檎",
    "Superfly",
    "あいみょん",
    "米津玄師",
    "星野源",
    # back number, YOASOBI: グループとしてGROUP_ENTITIESに移動
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
    # 志村けん: ザ・ドリフターズメンバーのためGROUP_MEMBER_MAPに移動
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
