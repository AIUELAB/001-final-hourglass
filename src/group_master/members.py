#!/usr/bin/env python3
"""
グループメンバーマスタモジュール

グループメンバーマップと関連関数を定義。
"""

from typing import Dict, List, Optional, Tuple

from .entities import GROUP_ENTITIES, SOLO_ARTISTS

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
