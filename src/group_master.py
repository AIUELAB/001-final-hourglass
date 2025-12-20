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
    # NON STYLE
    "井上裕介": "NON STYLE",
    "石田明": "NON STYLE",
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
    # 南海キャンディーズ
    "しずちゃん": "南海キャンディーズ",
    "山崎静代": "南海キャンディーズ",  # 本名
    "山里亮太": "南海キャンディーズ",
    # ザ・ドリフターズ
    "高木ブー": "ザ・ドリフターズ",
    "加藤茶": "ザ・ドリフターズ",
    "仲本工事": "ザ・ドリフターズ",
    "志村けん": "ザ・ドリフターズ",
    "いかりや長介": "ザ・ドリフターズ",
    # ウッチャンナンチャン
    "内村光良": "ウッチャンナンチャン",
    "南原清隆": "ウッチャンナンチャン",
    # とんねるず
    "石橋貴明": "とんねるず",
    "木梨憲武": "とんねるず",
    # 爆笑問題
    "太田光": "爆笑問題",
    "田中裕二": "爆笑問題",
    # バナナマン
    "設楽統": "バナナマン",
    "日村勇紀": "バナナマン",
    # おぎやはぎ
    "小木博明": "おぎやはぎ",
    "矢作兼": "おぎやはぎ",
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
    "岸優太": "King & Prince",
    "神宮寺勇太": "King & Prince",
    # SixTONES
    "ジェシー": "SixTONES",
    "京本大我": "SixTONES",
    "松村北斗": "SixTONES",
    "髙地優吾": "SixTONES",
    "森本慎太郎": "SixTONES",
    "田中樹": "SixTONES",
    # Snow Man
    "岩本照": "Snow Man",
    "深澤辰哉": "Snow Man",
    "ラウール": "Snow Man",
    "渡辺翔太": "Snow Man",
    "向井康二": "Snow Man",
    "阿部亮平": "Snow Man",
    "目黒蓮": "Snow Man",
    "宮舘涼太": "Snow Man",
    "佐久間大介": "Snow Man",
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
    # ===== 音楽ユニット =====
    # YOASOBI
    "Ayase": "YOASOBI",
    "ikura": "YOASOBI",
    "幾田りら": "YOASOBI",  # ikuraの本名
    # ===== YouTubeグループ =====
    # Fischer's / フィッシャーズ
    "シルクロード": "Fischer's",
    "シルク": "フィッシャーズ",  # シルクロードの別名
    # 東海オンエア
    "てつや": "東海オンエア",
    # 水溜りボンド
    "トミー": "水溜りボンド",
    "カンタ": "水溜りボンド",
    # 兄者弟者
    "兄者": "兄者弟者",
    "弟者": "兄者弟者",
    # ===== 企業・スポーツチーム =====
    # （既存データから）
    "前田晃伸": "みずほフィナンシャルグループ",
    "藤沢武夫": "本田技研工業",
    "森稔": "森ビル",
    "堤義明": "西武グループ",
    "川上哲治": "読売ジャイアンツ",
    "落合博満": "ロッテオリオンズ",
    # ===== Phase 31追加 =====
    # 海外音楽
    "ジョン・レノン": "ビートルズ",
    "ポール・マッカートニー": "ビートルズ",
    "ビヨンセ": "デスティニーズ・チャイルド",
    "LISA": "BLACKPINK",
    # X JAPAN追加
    "hide": "X JAPAN",
    # L'Arc~en~Ciel追加（表記ゆれ対応）
    "HYDE": "L'Arc~en~Ciel",
    "hydeラルクアンシエル": "L'Arc~en~Ciel",
    # その他音楽
    "GACKT": "MALICE MIZER",
    "つんく": "シャ乱Q",
    "小田和正": "オフコース",
    "山下達郎": "シュガー・ベイブ",
    "三浦大知": "Folder",
    "Perfume": "Perfume",
    "Official髭男dism": "Official髭男dism",
    # お笑いコンビ追加
    "萩本欽一": "コント55号",
    "千原ジュニア": "千原兄弟",
    "千原せいじ": "千原兄弟",
    "今田耕司": "130R",
    "東野幸治": "130R",
    "上田晋也": "くりぃむしちゅー",
    "有田哲平": "くりぃむしちゅー",
    "宮藤官九郎": "劇団大人計画",
    # Hey! Say! JUMP
    "山田涼介": "Hey! Say! JUMP",
    "中島裕翔": "Hey! Say! JUMP",
    "知念侑李": "Hey! Say! JUMP",
    "有岡大貴": "Hey! Say! JUMP",
    "伊野尾慧": "Hey! Say! JUMP",
    "高木雄也": "Hey! Say! JUMP",
    "八乙女光": "Hey! Say! JUMP",
    "薮宏太": "Hey! Say! JUMP",
    # 文学グループ
    "尾崎紅葉": "硯友社",
    "横光利一": "新感覚派",
    "川端康成": "新感覚派",
    # その他
    "シェイクスピア": "宮内大臣一座",
    # ===== Phase 40追加: 海外バンドメンバー =====
    # ビートルズ（全メンバー）
    "ジョージ・ハリスン": "ビートルズ",
    "リンゴ・スター": "ビートルズ",
    "John Lennon": "The Beatles",
    "Paul McCartney": "The Beatles",
    "George Harrison": "The Beatles",
    "Ringo Starr": "The Beatles",
    # ローリング・ストーンズ
    "ミック・ジャガー": "ローリング・ストーンズ",
    "キース・リチャーズ": "ローリング・ストーンズ",
    "Mick Jagger": "The Rolling Stones",
    "Keith Richards": "The Rolling Stones",
    # クイーン
    "フレディ・マーキュリー": "クイーン",
    "ブライアン・メイ": "クイーン",
    "ロジャー・テイラー": "クイーン",
    "ジョン・ディーコン": "クイーン",
    "Freddie Mercury": "Queen",
    "Brian May": "Queen",
    # レッド・ツェッペリン
    "ジミー・ペイジ": "レッド・ツェッペリン",
    "ロバート・プラント": "レッド・ツェッペリン",
    # U2
    "ボノ": "U2",
    "ジ・エッジ": "U2",
    "Bono": "U2",
    "The Edge": "U2",
    # ===== Phase 40追加: K-POPメンバー =====
    # BTS（全メンバー）
    "RM": "BTS",
    "Jin": "BTS",
    "SUGA": "BTS",
    "j-hope": "BTS",
    "Jimin": "BTS",
    "V": "BTS",
    "Jung Kook": "BTS",
    "ジョングク": "BTS",
    "ジミン": "BTS",
    "テテ": "BTS",
    # BLACKPINK（全メンバー）
    "Jisoo": "BLACKPINK",
    "ジス": "BLACKPINK",
    "Jennie": "BLACKPINK",
    "ジェニー": "BLACKPINK",
    "Rosé": "BLACKPINK",
    "ロゼ": "BLACKPINK",
    "Lisa": "BLACKPINK",
    "リサ": "BLACKPINK",
    # TWICE（代表メンバー）
    "ナヨン": "TWICE",
    "サナ": "TWICE",
    "モモ": "TWICE",
    "ミナ": "TWICE",
    "ツウィ": "TWICE",
    # ===== Phase 40追加: VTuber =====
    # ホロライブ（代表）
    "星街すいせい": "ホロライブ",
    "兎田ぺこら": "ホロライブ",
    "白上フブキ": "ホロライブ",
    "湊あくあ": "ホロライブ",
    "宝鐘マリン": "ホロライブ",
    "さくらみこ": "ホロライブ",
    "大空スバル": "ホロライブ",
    "天音かなた": "ホロライブ",
    "角巻わため": "ホロライブ",
    "獅白ぼたん": "ホロライブ",
    # にじさんじ（代表）
    "葛葉": "にじさんじ",
    "叶": "にじさんじ",
    "月ノ美兎": "にじさんじ",
    "剣持刀也": "にじさんじ",
    "笹木咲": "にじさんじ",
    "椎名唯華": "にじさんじ",
    "本間ひまわり": "にじさんじ",
    "樋口楓": "にじさんじ",
    "リゼ・ヘルエスタ": "にじさんじ",
    "アンジュ・カトリーナ": "にじさんじ",
    # ===== Phase 40追加: YouTubeグループ =====
    # 東海オンエア
    "しばゆー": "東海オンエア",
    "りょう": "東海オンエア",
    "としみつ": "東海オンエア",
    "ゆめまる": "東海オンエア",
    "虫眼鏡": "東海オンエア",
    # コムドット
    "やまと": "コムドット",
    "ひゅうが": "コムドット",
    "ゆうた": "コムドット",
    "あむぎり": "コムドット",
    # Fischer's
    "ンダホ": "Fischer's",
    "ダーマ": "Fischer's",
    # QuizKnock
    "伊沢拓司": "QuizKnock",
    "ふくらP": "QuizKnock",
    "河村拓哉": "QuizKnock",
}

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
    "ぺこぱ",
    "南海キャンディーズ",
    "くりぃむしちゅー",
    # ===== 日本のバンド（追加） =====
    "ゴールデンボンバー",
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


# ========================================
# 分散ルール（グループ→メンバー変換時の戦略）
# ========================================


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
