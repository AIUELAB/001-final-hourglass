#!/usr/bin/env python3
"""
グループ分散ルールモジュール

グループ→メンバー変換時の戦略を定義。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from .entities import GROUP_DETAILS, GroupInfo


class DispersionStrategy(Enum):
    """分散戦略"""

    ALL = "all"  # 全メンバーに分散
    REPRESENTATIVE = "representative"  # 代表メンバーのみ
    DELETE = "delete"  # 削除（エピソード不要）


@dataclass
class DispersionRule:
    """分散ルール定義"""

    strategy: DispersionStrategy
    members: List[str]  # 分散先メンバー（空リストの場合は自動取得）
    max_members: int = 5  # 最大分散メンバー数


DISPERSION_RULES: Dict[str, DispersionRule] = {
    # ===== 海外バンド（小規模→全員分散） =====
    "ビートルズ": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["ジョン・レノン", "ポール・マッカートニー", "ジョージ・ハリスン", "リンゴ・スター"],
        max_members=4,
    ),
    "The Beatles": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["John Lennon", "Paul McCartney", "George Harrison", "Ringo Starr"],
        max_members=4,
    ),
    "クイーン": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["フレディ・マーキュリー", "ブライアン・メイ", "ロジャー・テイラー", "ジョン・ディーコン"],
        max_members=4,
    ),
    "ローリング・ストーンズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["ミック・ジャガー", "キース・リチャーズ"], max_members=2
    ),
    "U2": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["ボノ", "ジ・エッジ"], max_members=2),
    # ===== K-POP（大規模→代表のみ） =====
    "BTS": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["RM", "SUGA", "Jimin"], max_members=3),
    "BLACKPINK": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["Jisoo", "Jennie", "Rosé", "Lisa"], max_members=4
    ),
    "TWICE": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["ナヨン", "サナ", "ツウィ"], max_members=3
    ),
    # ===== 日本のアイドルグループ =====
    "嵐": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["大野智", "櫻井翔", "相葉雅紀", "二宮和也", "松本潤"], max_members=5
    ),
    "SMAP": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["木村拓哉", "中居正広", "香取慎吾"], max_members=3
    ),
    "AKB48": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["前田敦子", "大島優子", "指原莉乃"], max_members=3
    ),
    "乃木坂46": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["白石麻衣", "西野七瀬", "齋藤飛鳥"], max_members=3
    ),
    # ===== VTuberグループ（代表に分散） =====
    "ホロライブ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["星街すいせい", "兎田ぺこら", "湊あくあ"], max_members=3
    ),
    "hololive": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["星街すいせい", "兎田ぺこら", "湊あくあ"], max_members=3
    ),
    "にじさんじ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["葛葉", "叶", "月ノ美兎"], max_members=3
    ),
    # ===== お笑いコンビ（全員分散） =====
    "ダウンタウン": DispersionRule(strategy=DispersionStrategy.ALL, members=["松本人志", "浜田雅功"], max_members=2),
    "サンドウィッチマン": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["伊達みきお", "富澤たけし"], max_members=2
    ),
    "霜降り明星": DispersionRule(strategy=DispersionStrategy.ALL, members=["粗品", "せいや"], max_members=2),
    # ===== 音楽グループ =====
    "B'z": DispersionRule(strategy=DispersionStrategy.ALL, members=["稲葉浩志", "松本孝弘"], max_members=2),
    "Mr.Children": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["桜井和寿"], max_members=1),
    "サザンオールスターズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["桑田佳祐", "原由子"], max_members=2
    ),
    # ===== YouTubeグループ =====
    "東海オンエア": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["てつや", "しばゆー"], max_members=2
    ),
    "コムドット": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["やまと"], max_members=1),
    "QuizKnock": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["伊沢拓司"], max_members=1),
    "Fischer's": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["シルクロード", "ンダホ"], max_members=2
    ),
    "フィッシャーズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["シルクロード", "ンダホ"], max_members=2
    ),
    # ===== 追加アイドル・音楽グループ =====
    "櫻坂46": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["菅井友香", "小林由依"], max_members=2
    ),
    "NMB48": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["山本彩", "渡辺美優紀"], max_members=2
    ),
    "KinKi Kids": DispersionRule(strategy=DispersionStrategy.ALL, members=["堂本光一", "堂本剛"], max_members=2),
    "DREAMS COME TRUE": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["吉田美和", "中村正人"], max_members=2
    ),
    "Perfume": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["あ〜ちゃん", "かしゆか", "のっち"], max_members=3
    ),
    "Official髭男dism": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["藤原聡"], max_members=1),
    "スピッツ": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["草野マサムネ"], max_members=1),
    "コブクロ": DispersionRule(strategy=DispersionStrategy.ALL, members=["小渕健太郎", "黒田俊介"], max_members=2),
    # ===== 追加お笑いコンビ =====
    "ミルクボーイ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["駒場孝", "内海崇"], max_members=2
    ),
    "かまいたち": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["山内健司", "濱家隆一"], max_members=2
    ),
    "千鳥": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["大悟", "ノブ"], max_members=2),
    "南海キャンディーズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["山里亮太", "山崎静代"], max_members=2
    ),
    # ===== 海外バンド（追加） =====
    "マルーン5": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["アダム・レヴィーン"], max_members=1
    ),
    "Maroon 5": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["Adam Levine"], max_members=1),
    "コールドプレイ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["クリス・マーティン"], max_members=1
    ),
    "Coldplay": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["Chris Martin"], max_members=1),
    # ===== Phase 2追加: 日本アイドル =====
    "King & Prince": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["平野紫耀", "永瀬廉", "高橋海人"], max_members=3
    ),
    "SixTONES": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["ジェシー", "京本大我", "松村北斗"], max_members=3
    ),
    "Snow Man": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["岩本照", "目黒蓮", "ラウール"], max_members=3
    ),
    "Hey! Say! JUMP": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["山田涼介", "中島裕翔", "知念侑李"], max_members=3
    ),
    "TOKIO": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["城島茂", "国分太一", "松岡昌宏"], max_members=3
    ),
    "V6": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["岡田准一", "井ノ原快彦", "坂本昌行"], max_members=3
    ),
    "SKE48": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["松井珠理奈", "松井玲奈"], max_members=2
    ),
    "HKT48": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["指原莉乃", "宮脇咲良"], max_members=2
    ),
    "日向坂46": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["佐々木久美", "加藤史帆"], max_members=2
    ),
    "欅坂46": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["平手友梨奈"], max_members=1),
    "モーニング娘。": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["安倍なつみ", "後藤真希"], max_members=2
    ),
    # ===== Phase 2追加: 日本ロック =====
    "X JAPAN": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["YOSHIKI", "TOSHI", "hide"], max_members=3
    ),
    "GLAY": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["TERU", "TAKURO"], max_members=2),
    "LUNA SEA": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["河村隆一", "SUGIZO"], max_members=2
    ),
    "L'Arc~en~Ciel": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["hyde", "ken"], max_members=2),
    "ラルクアンシエル": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["hyde", "ken"], max_members=2
    ),
    "SEKAI NO OWARI": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["Fukase", "Saori"], max_members=2
    ),
    "ゆず": DispersionRule(strategy=DispersionStrategy.ALL, members=["北川悠仁", "岩沢厚治"], max_members=2),
    "RADWIMPS": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["野田洋次郎"], max_members=1),
    "back number": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["清水依与吏"], max_members=1),
    "King Gnu": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["常田大希", "井口理"], max_members=2
    ),
    "ONE OK ROCK": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["Taka"], max_members=1),
    "YOASOBI": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["幾田りら", "Ayase"], max_members=2),
    # ===== Phase 2追加: お笑い =====
    "ナインティナイン": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["岡村隆史", "矢部浩之"], max_members=2
    ),
    "オードリー": DispersionRule(strategy=DispersionStrategy.ALL, members=["若林正恭", "春日俊彰"], max_members=2),
    "とんねるず": DispersionRule(strategy=DispersionStrategy.ALL, members=["石橋貴明", "木梨憲武"], max_members=2),
    "爆笑問題": DispersionRule(strategy=DispersionStrategy.ALL, members=["太田光", "田中裕二"], max_members=2),
    "バナナマン": DispersionRule(strategy=DispersionStrategy.ALL, members=["設楽統", "日村勇紀"], max_members=2),
    "おぎやはぎ": DispersionRule(strategy=DispersionStrategy.ALL, members=["小木博明", "矢作兼"], max_members=2),
    "ザ・ドリフターズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["志村けん", "加藤茶", "いかりや長介"], max_members=3
    ),
    "ウッチャンナンチャン": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["内村光良", "南原清隆"], max_members=2
    ),
    "EXIT": DispersionRule(strategy=DispersionStrategy.ALL, members=["兼近大樹", "りんたろー。"], max_members=2),
    "ぺこぱ": DispersionRule(strategy=DispersionStrategy.ALL, members=["シュウペイ", "松陰寺太勇"], max_members=2),
    # ===== Phase 2追加: K-POP（日本語表記） =====
    "防弾少年団": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["RM", "SUGA", "Jimin"], max_members=3
    ),
    "ブラックピンク": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["Jisoo", "Jennie", "Rosé", "Lisa"], max_members=4
    ),
    "トゥワイス": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["ナヨン", "サナ", "ツウィ"], max_members=3
    ),
    "EXO": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["ベッキョン", "カイ"], max_members=2),
    "NCT": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["テヨン", "マーク"], max_members=2),
    "SEVENTEEN": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["エスクプス", "ジョンハン"], max_members=2
    ),
    "Stray Kids": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["バンチャン", "ヒョンジン"], max_members=2
    ),
    "aespa": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["カリナ", "ウィンター"], max_members=2
    ),
    "IVE": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["ウォニョン", "レイ"], max_members=2),
    "NewJeans": DispersionRule(strategy=DispersionStrategy.REPRESENTATIVE, members=["ミンジ", "へイン"], max_members=2),
    "LE SSERAFIM": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["サクラ", "カズハ"], max_members=2
    ),
    # ===== Phase 2追加: 海外バンド =====
    "Beatles": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["John Lennon", "Paul McCartney", "George Harrison", "Ringo Starr"],
        max_members=4,
    ),
    "Queen": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["Freddie Mercury", "Brian May", "Roger Taylor", "John Deacon"],
        max_members=4,
    ),
    "The Rolling Stones": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["Mick Jagger", "Keith Richards"], max_members=2
    ),
    "Led Zeppelin": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["Jimmy Page", "Robert Plant"], max_members=2
    ),
    "レッド・ツェッペリン": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["ジミー・ペイジ", "ロバート・プラント"], max_members=2
    ),
    "Pink Floyd": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["Roger Waters", "David Gilmour"], max_members=2
    ),
    "ピンク・フロイド": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["ロジャー・ウォーターズ", "デヴィッド・ギルモア"],
        max_members=2,
    ),
    "One Direction": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["Harry Styles", "Zayn Malik"], max_members=2
    ),
    "ワン・ダイレクション": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["ハリー・スタイルズ", "ゼイン・マリク"], max_members=2
    ),
    # ===== Phase 2追加: VTuber =====
    "NIJISANJI": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["葛葉", "叶", "月ノ美兎"], max_members=3
    ),
    "VShojo": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["Ironmouse", "Nyanners"], max_members=2
    ),
    # ===== Phase 2追加: 流動的グループ（REPRESENTATIVE変換） =====
    "劇団四季": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["市村正親", "浅利慶太"], max_members=2
    ),
    "宝塚歌劇団": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["天海祐希", "真矢ミキ"], max_members=2
    ),
    "笑点メンバー": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["桂歌丸", "林家木久扇"], max_members=2
    ),
    # ===== Phase 3追加: アイドルグループ =====
    "ももいろクローバーZ": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["百田夏菜子", "玉井詩織", "佐々木彩夏", "高城れに"],
        max_members=4,
    ),
    "でんぱ組.inc": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["古川未鈴", "相沢梨紗"], max_members=2
    ),
    # ===== Phase 3追加: YouTubeグループ =====
    "兄者弟者": DispersionRule(strategy=DispersionStrategy.ALL, members=["兄者", "弟者"], max_members=2),
    # ===== Phase 4追加: お笑いコンビ =====
    "くりぃむしちゅー": DispersionRule(
        strategy=DispersionStrategy.ALL, members=["上田晋也", "有田哲平"], max_members=2
    ),
    # ===== Phase 4追加: バンド =====
    "ゴールデンボンバー": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE, members=["鬼龍院翔"], max_members=1
    ),
    # ===== Phase 4追加: スポーツ・学校・研究チーム（DELETE戦略） =====
    # これらは組織であり、エピソード内の個人に紐付けるか削除する
    "清水エスパルス": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "湘南ベルマーレ": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "星稜高校": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "東海大学相模": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "青色LED開発チーム": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "ASIMO開発チーム": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    # ===== Phase 5追加: 学校チーム（DELETE戦略） =====
    "智弁和歌山": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "流経大柏高校": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "駒大苫小牧": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "早稲田実業": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    # ===== Phase 5追加: 家族グループ（ALL戦略） =====
    "阿部兄妹": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["阿部一二三", "阿部詩"],
        max_members=2,
    ),
    # ===== Phase 5追加: 兄弟パターン（ALL戦略） =====
    "ライト兄弟": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["ウィルバー・ライト", "オーヴィル・ライト"],
        max_members=2,
    ),
    "コーエン兄弟": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["ジョエル・コーエン", "イーサン・コーエン"],
        max_members=2,
    ),
    # ===== Phase 5追加: 創業者チーム（DELETE戦略） =====
    "富士フイルム創業者": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    "島津製作所創業者": DispersionRule(strategy=DispersionStrategy.DELETE, members=[], max_members=0),
    # ===== Phase 5追加: 音楽グループ =====
    "竹内電気": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["竹内サティフォ"],  # 代表メンバーのみ（他メンバーの知名度低）
        max_members=1,
    ),
    "真心ブラザーズ": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["YO-KING", "桜井秀俊"],  # 倉持陽一の芸名がYO-KING
        max_members=2,
    ),
    # ===== Phase 6追加: 音楽バンド =====
    "野猿": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["石橋貴明"],  # とんねるずプロデュース
        max_members=1,
    ),
    "デレク・アンド・ザ・ドミノス": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["エリック・クラプトン"],  # バンドリーダー
        max_members=1,
    ),
    "カーペンターズ": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["カレン・カーペンター", "リチャード・カーペンター"],  # 兄妹デュオ
        max_members=2,
    ),
    "イーグルス": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["ドン・ヘンリー"],  # 代表メンバー
        max_members=1,
    ),
    "フリートウッド・マック": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["スティーヴィー・ニックス"],  # 代表メンバー
        max_members=1,
    ),
    "ケミカル・ブラザーズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["トム・ローランズ"],  # エド・シモンズとのデュオ
        max_members=1,
    ),
    "バンク・バンド": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["桜井和寿"],  # Mr.Children桜井のプロジェクト
        max_members=1,
    ),
    # ===== Phase 6追加: 夫妻グループ =====
    "キュリー夫妻": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["マリ・キュリー", "ピエール・キュリー"],  # 科学者夫妻
        max_members=2,
    ),
    # ===== Phase 7追加: v5グループ =====
    # お笑いコンビ
    "浅草キッド": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["水道橋博士", "ビートたけし"],
        max_members=2,
    ),
    # 漫画家コンビ
    "藤子不二雄": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["藤子・F・不二雄", "藤子不二雄A"],
        max_members=2,
    ),
    # 音楽デュオ（ALL戦略）
    "サイモン&ガーファンクル": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["ポール・サイモン", "アート・ガーファンクル"],
        max_members=2,
    ),
    "ブルーハーツ": DispersionRule(
        strategy=DispersionStrategy.ALL,
        members=["甲本ヒロト", "真島昌利"],
        max_members=2,
    ),
    # 音楽グループ（REPRESENTATIVE戦略）
    "ゴスペラーズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["村上てつや"],
        max_members=1,
    ),
    "ガンズ・アンド・ローゼズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["アクセル・ローズ"],
        max_members=1,
    ),
    "オレンジレンジ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["NAOTO"],
        max_members=1,
    ),
    "サッズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["清春"],
        max_members=1,
    ),
    "ザ・キュアー": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["ロバート・スミス"],
        max_members=1,
    ),
    "ニルヴァーナ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["カート・コバーン"],
        max_members=1,
    ),
    "パール・ジャム": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["エディ・ヴェダー"],
        max_members=1,
    ),
    "アリス・イン・チェインズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["レイン・ステイリー"],
        max_members=1,
    ),
    "サウンドガーデン": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["クリス・コーネル"],
        max_members=1,
    ),
    "フー・ファイターズ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["デイヴ・グロール"],
        max_members=1,
    ),
    "グリーン・デイ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["ビリー・ジョー・アームストロング"],
        max_members=1,
    ),
    "メタリカ": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["ジェイムズ・ヘットフィールド"],
        max_members=1,
    ),
    "AC/DC": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["アンガス・ヤング"],
        max_members=1,
    ),
    "かりゆし58": DispersionRule(
        strategy=DispersionStrategy.REPRESENTATIVE,
        members=["前川真悟"],
        max_members=1,
    ),
}


def get_dispersion_rule(group_name: str) -> Optional[DispersionRule]:
    """
    グループ名から分散ルールを取得

    Args:
        group_name: グループ名

    Returns:
        DispersionRule または None（未定義の場合）
    """
    return DISPERSION_RULES.get(group_name)


def get_group_details(group_name: str) -> Optional[GroupInfo]:
    """
    グループ名から詳細情報を取得

    Args:
        group_name: グループ名

    Returns:
        GroupInfo または None
    """
    return GROUP_DETAILS.get(group_name)
