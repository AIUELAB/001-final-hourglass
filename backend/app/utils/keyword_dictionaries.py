"""カテゴリ別キーワード辞書

エピソード有名度スコアリング用のキーワード辞書
各カテゴリに適したキーワードを定義
"""

from typing import Dict, List, Set

# カテゴリ別の超有名キーワード（+18点）
ULTRA_FAMOUS_KEYWORDS: Dict[str, List[str]] = {
    "default": [
        "ギネス",
        "guinness",
        "guinness world records",
        "世界記録",
        "world record",
        "国民的",
        "national",
        "社会現象",
        "social phenomenon",
        "歴史的",
    ],
    "エンターテインメント": [
        "ギネス",
        "世界記録",
        "国民的",
        "社会現象",
        "視聴率",
        "紅白",
        "レコード大賞",
        "グラミー賞",
        "アカデミー賞",
        "エミー賞",
        "興行収入",
        "歴代1位",
    ],
    "漫画・アニメ": [
        "ギネス",
        "世界記録",
        "国民的",
        "仮面ライダー",
        "ウルトラマン",
        "ドラえもん",
        "ドラゴンボール",
        "ワンピース",
        "鬼滅の刃",
        "手塚治虫",
        "宮崎駿",
        "社会現象",
        "累計発行部数",
        "1億部",
    ],
    "科学・技術": [
        "ノーベル賞",
        "nobel prize",
        "フィールズ賞",
        "世界初",
        "world first",
        "人類初",
        "特許",
        "発明",
        "革命的発見",
        "ブレークスルー",
        "画期的",
    ],
    "スポーツ": [
        "オリンピック",
        "olympic",
        "金メダル",
        "gold medal",
        "ワールドカップ",
        "world cup",
        "MVP",
        "世界記録",
        "world record",
        "殿堂入り",
        "歴代最高",
        "通算記録",
    ],
    "音楽": [
        "グラミー賞",
        "grammy",
        "レコード大賞",
        "紅白",
        "ミリオンセラー",
        "歴代1位",
        "国民的",
        "社会現象",
        "ロック殿堂",
    ],
    "文学": [
        "ノーベル文学賞",
        "芥川賞",
        "直木賞",
        "ピューリッツァー賞",
        "ブッカー賞",
        "国民的作家",
        "ベストセラー",
        "累計発行部数",
    ],
    "美術・芸術": [
        "国宝",
        "National Treasure",
        "重要文化財",
        "人間国宝",
        "文化勲章",
        "巨匠",
        "革新的",
        "印象派",
        "モダンアート",
    ],
    "ビジネス・経営": [
        "世界一",
        "時価総額",
        "創業者",
        "フォーブス",
        "forbes",
        "億万長者",
        "革新的",
        "イノベーター",
        "ユニコーン",
    ],
    "政治・歴史": ["歴史的", "革命", "独立", "改革", "憲法", "条約", "戦争終結", "平和賞", "ノーベル平和賞"],
    "医学・医療": ["ノーベル生理学・医学賞", "世界初", "画期的治療", "新薬", "ワクチン", "人類初", "医学革命"],
}

# カテゴリ別の有名キーワード（+12点）
FAMOUS_KEYWORDS: Dict[str, List[str]] = {
    "default": [
        "世界初",
        "world first",
        "世界で初めて",
        "日本初",
        "japan first",
        "代表作",
        "masterpiece",
        "金字塔",
        "milestone",
        "伝説",
        "legend",
    ],
    "エンターテインメント": [
        "代表作",
        "最高傑作",
        "デビュー",
        "復活",
        "カムバック",
        "引退",
        "全国ツアー",
        "武道館",
        "ドーム",
    ],
    "漫画・アニメ": [
        "代表作",
        "連載開始",
        "連載終了",
        "アニメ化",
        "映画化",
        "実写化",
        "トキワ荘",
        "週刊少年ジャンプ",
        "週刊少年マガジン",
        "週刊少年サンデー",
        "累計",
        "発行部数",
    ],
    "科学・技術": ["発見", "発明", "開発", "論文", "特許取得", "実用化", "産業革命", "技術革新", "新技術"],
    "スポーツ": ["優勝", "準優勝", "記録更新", "代表", "選出", "プロデビュー", "引退", "監督就任", "殿堂"],
    "音楽": ["デビュー", "メジャーデビュー", "アルバム", "シングル", "ヒット", "武道館", "ドームツアー", "引退"],
    "文学": ["処女作", "デビュー作", "代表作", "受賞", "候補", "ベストセラー", "翻訳", "映画化"],
    "美術・芸術": ["個展", "回顧展", "代表作", "受賞", "入選", "美術館", "収蔵", "コレクション"],
    "ビジネス・経営": ["創業", "設立", "上場", "買収", "合併", "IPO", "黒字転換", "V字回復"],
    "政治・歴史": ["就任", "選挙", "当選", "政策", "改革", "演説", "条約", "協定"],
    "医学・医療": ["開発", "承認", "臨床試験", "治療法", "手術", "移植", "発見", "解明"],
}

# カテゴリ別の影響力キーワード（+3点/個、最大+10点）
IMPACT_KEYWORDS: Dict[str, List[str]] = {
    "default": [
        "影響",
        "influence",
        "impact",
        "文化",
        "culture",
        "革命",
        "revolution",
        "先駆者",
        "pioneer",
        "創造",
        "creation",
        "半世紀",
        "50年",
    ],
    "エンターテインメント": ["影響", "文化", "先駆者", "革新", "新境地", "進化", "時代", "世代", "ファン"],
    "漫画・アニメ": ["影響", "革新", "先駆者", "開拓", "新ジャンル", "表現", "キャラクター", "ストーリー", "作風"],
    "科学・技術": ["影響", "革命", "進歩", "発展", "貢献", "応用", "実用", "普及", "標準"],
    "スポーツ": ["影響", "記録", "歴史", "伝説", "レジェンド", "功績", "貢献", "指導", "育成"],
    "音楽": ["影響", "革新", "ジャンル", "サウンド", "スタイル", "時代", "世代", "シーン", "ムーブメント"],
    "文学": ["影響", "文学", "作風", "スタイル", "表現", "言葉", "読者", "評価", "批評"],
    "美術・芸術": ["影響", "革新", "様式", "表現", "技法", "芸術", "美学", "創造", "インスピレーション"],
    "ビジネス・経営": ["影響", "革新", "市場", "業界", "ビジネスモデル", "経営", "戦略", "成長", "拡大"],
    "政治・歴史": ["影響", "歴史", "変革", "改革", "政治", "社会", "国民", "国家", "世界"],
    "医学・医療": ["影響", "医学", "医療", "治療", "患者", "健康", "生命", "研究", "進歩"],
}

# 個人的キーワード（ペナルティ用）
PERSONAL_KEYWORDS: List[str] = [
    "姉",
    "兄",
    "弟",
    "妹",
    "家族",
    "個人的",
    "personal",
    "病",
    "入院",
    "療養",
    "私生活",
    "プライベート",
]


def get_category_keywords(category: str, keyword_type: str = "ultra_famous") -> List[str]:
    """
    カテゴリに応じたキーワードリストを取得

    Args:
        category: カテゴリ名
        keyword_type: キーワードタイプ
            - 'ultra_famous': 超有名キーワード
            - 'famous': 有名キーワード
            - 'impact': 影響力キーワード

    Returns:
        キーワードリスト
    """
    keyword_dict = {"ultra_famous": ULTRA_FAMOUS_KEYWORDS, "famous": FAMOUS_KEYWORDS, "impact": IMPACT_KEYWORDS}

    selected_dict = keyword_dict.get(keyword_type, ULTRA_FAMOUS_KEYWORDS)

    # カテゴリが存在する場合はそのキーワード、なければデフォルト
    if category in selected_dict:
        return selected_dict[category]
    return selected_dict.get("default", [])


def get_all_keywords_for_category(category: str) -> Dict[str, List[str]]:
    """
    カテゴリの全キーワードタイプを取得

    Args:
        category: カテゴリ名

    Returns:
        キーワードタイプをキーとした辞書
    """
    return {
        "ultra_famous": get_category_keywords(category, "ultra_famous"),
        "famous": get_category_keywords(category, "famous"),
        "impact": get_category_keywords(category, "impact"),
        "personal": PERSONAL_KEYWORDS,
    }


def normalize_category(category: str) -> str:
    """
    カテゴリ名を正規化（キーワード辞書のキーに合わせる）

    Args:
        category: 元のカテゴリ名

    Returns:
        正規化されたカテゴリ名
    """
    # カテゴリのマッピング
    category_mapping = {
        # エンターテインメント系
        "芸能": "エンターテインメント",
        "タレント": "エンターテインメント",
        "俳優": "エンターテインメント",
        "女優": "エンターテインメント",
        "映画": "エンターテインメント",
        "テレビ": "エンターテインメント",
        "お笑い": "エンターテインメント",
        "コメディ": "エンターテインメント",
        # 漫画・アニメ系
        "漫画": "漫画・アニメ",
        "アニメ": "漫画・アニメ",
        "マンガ": "漫画・アニメ",
        "コミック": "漫画・アニメ",
        "ゲーム": "漫画・アニメ",
        # 科学・技術系
        "科学": "科学・技術",
        "技術": "科学・技術",
        "工学": "科学・技術",
        "IT": "科学・技術",
        "情報": "科学・技術",
        "数学": "科学・技術",
        "物理": "科学・技術",
        "化学": "科学・技術",
        "生物": "科学・技術",
        # スポーツ系
        "野球": "スポーツ",
        "サッカー": "スポーツ",
        "テニス": "スポーツ",
        "ゴルフ": "スポーツ",
        "陸上": "スポーツ",
        "水泳": "スポーツ",
        "格闘技": "スポーツ",
        "相撲": "スポーツ",
        "プロレス": "スポーツ",
        # 音楽系
        "歌手": "音楽",
        "ミュージシャン": "音楽",
        "アーティスト": "音楽",
        "バンド": "音楽",
        "作曲": "音楽",
        "クラシック": "音楽",
        "ジャズ": "音楽",
        "ロック": "音楽",
        "ポップス": "音楽",
        # 文学系
        "作家": "文学",
        "小説": "文学",
        "詩": "文学",
        "エッセイ": "文学",
        "評論": "文学",
        # 美術・芸術系
        "美術": "美術・芸術",
        "芸術": "美術・芸術",
        "絵画": "美術・芸術",
        "彫刻": "美術・芸術",
        "デザイン": "美術・芸術",
        "建築": "美術・芸術",
        "写真": "美術・芸術",
        # ビジネス・経営系
        "ビジネス": "ビジネス・経営",
        "経営": "ビジネス・経営",
        "起業": "ビジネス・経営",
        "経済": "ビジネス・経営",
        "実業家": "ビジネス・経営",
        # 政治・歴史系
        "政治": "政治・歴史",
        "歴史": "政治・歴史",
        "政治家": "政治・歴史",
        "軍事": "政治・歴史",
        # 医学・医療系
        "医学": "医学・医療",
        "医療": "医学・医療",
        "医師": "医学・医療",
        "看護": "医学・医療",
        "薬学": "医学・医療",
    }

    # マッピングがあればそれを返す
    if category in category_mapping:
        return category_mapping[category]

    # マッピングがなければそのまま返す（辞書にキーがあればそれを使用）
    if category in ULTRA_FAMOUS_KEYWORDS:
        return category

    # どちらにもなければデフォルト
    return "default"


def calculate_keyword_score(text: str, category: str) -> Dict[str, float]:
    """
    テキストからキーワードスコアを計算

    Args:
        text: エピソードテキスト
        category: カテゴリ

    Returns:
        各種スコアの辞書
    """
    text_lower = text.lower()
    normalized_category = normalize_category(category)

    keywords = get_all_keywords_for_category(normalized_category)

    # 超有名キーワード（+18点、1つでも該当すれば）
    ultra_famous_score = 0
    for kw in keywords["ultra_famous"]:
        if kw.lower() in text_lower:
            ultra_famous_score = 18
            break

    # 有名キーワード（+12点、1つでも該当すれば）
    famous_score = 0
    for kw in keywords["famous"]:
        if kw.lower() in text_lower:
            famous_score = 12
            break

    # 影響力キーワード（+3点/個、最大+10点）
    impact_count = sum(1 for kw in keywords["impact"] if kw.lower() in text_lower)
    impact_score = min(impact_count * 3, 10)

    # 個人的キーワード（ペナルティ）
    personal_count = sum(1 for kw in keywords["personal"] if kw.lower() in text_lower)
    personal_penalty = -15 if personal_count >= 2 else 0

    return {
        "ultra_famous_score": ultra_famous_score,
        "famous_score": famous_score,
        "impact_score": impact_score,
        "personal_penalty": personal_penalty,
        "total": ultra_famous_score + famous_score + impact_score + personal_penalty,
        "matched_ultra_famous": [kw for kw in keywords["ultra_famous"] if kw.lower() in text_lower],
        "matched_famous": [kw for kw in keywords["famous"] if kw.lower() in text_lower],
        "impact_count": impact_count,
        "personal_count": personal_count,
    }
