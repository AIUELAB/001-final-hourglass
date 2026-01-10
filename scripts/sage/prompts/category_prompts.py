"""
Category Prompt Manager - Phase 7D

カテゴリ別プロンプトテンプレート管理。
各カテゴリの特性に応じた生成プロンプトを提供。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ==============================================================================
# システムプロンプト（全生成に共通）
# ==============================================================================

# H4最適化: Prompt Caching用にシステムプロンプトを分割
# - SYSTEM_PROMPT_STATIC: 固定部分（キャッシュ対象）
# - SYSTEM_PROMPT_DYNAMIC: 人物名のみ（同一人物で共有）

SYSTEM_PROMPT_STATIC = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール】
1. すべての文を丁寧語（です・ます調）で終えてください
   - 正: 「〜しました。」「〜でした。」「〜です。」「〜ます。」
   - 誤: 「〜した。」「〜だった。」「〜だ。」「〜である。」
2. 主語は人物名または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じX歳のとき、[人物名]は」形式で開始してください
   ※年齢と人物名はユーザープロンプトで指定されます

【禁止事項】
- 常体（だ・である調）での文末
- 一人称（私、俺、僕）
- メタ的表現（「〜と言われています」「〜かもしれません」）
- 経歴や業績の単なる羅列
- 抽象的な表現（「成功を収めた」「活躍した」のみ）

【品質基準】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 300〜400文字で完結"""

# 後方互換性のためのテンプレート（非キャッシュモード用）
SYSTEM_PROMPT_TEMPLATE = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール】
1. すべての文を丁寧語（です・ます調）で終えてください
   - 正: 「〜しました。」「〜でした。」「〜です。」「〜ます。」
   - 誤: 「〜した。」「〜だった。」「〜だ。」「〜である。」
2. 主語は人物名（{person_name}）または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}は」で開始してください

【禁止事項】
- 常体（だ・である調）での文末
- 一人称（私、俺、僕）
- メタ的表現（「〜と言われています」「〜かもしれません」）
- 経歴や業績の単なる羅列
- 抽象的な表現（「成功を収めた」「活躍した」のみ）

【品質基準】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 300〜400文字で完結"""


def get_system_prompt(person_name: str, age: int) -> str:
    """
    システムプロンプトを取得

    Args:
        person_name: 人物名
        age: 年齢

    Returns:
        str: フォーマット済みシステムプロンプト
    """
    return SYSTEM_PROMPT_TEMPLATE.format(person_name=person_name, age=age)


def get_static_system_prompt() -> str:
    """
    H4最適化: キャッシュ用の固定システムプロンプトを取得

    Prompt Caching有効時に使用。人物名・年齢は含まれないため、
    同一人物の複数年齢生成でキャッシュが効く。

    Returns:
        str: 固定システムプロンプト
    """
    return SYSTEM_PROMPT_STATIC


@dataclass
class PromptTemplate:
    """プロンプトテンプレート"""

    category: str
    focus_points: list[str] = field(default_factory=list)  # 重点ポイント
    avoid_points: list[str] = field(default_factory=list)  # 避けるべき表現
    style: str = "客観的"  # 文体
    tone: str = "neutral"  # トーン
    example_themes: list[str] = field(default_factory=list)  # テーマ例
    quality_emphasis: dict[str, float] = field(default_factory=dict)  # 重視スコア軸
    iconic_guidance: str = ""  # 象徴的瞬間のガイダンス（Phase追加）

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "category": self.category,
            "focus_points": self.focus_points,
            "avoid_points": self.avoid_points,
            "style": self.style,
            "tone": self.tone,
            "example_themes": self.example_themes,
            "quality_emphasis": self.quality_emphasis,
            "iconic_guidance": self.iconic_guidance,
        }


# ==============================================================================
# カテゴリ別プロンプト定義
# ==============================================================================

CATEGORY_PROMPTS: dict[str, PromptTemplate] = {
    "科学・技術": PromptTemplate(
        category="科学・技術",
        focus_points=[
            "【最重要】世紀の大発見・大発明の誕生の瞬間",
            "発見・発明の具体的瞬間と研究者の感動",
            "実験や研究の詳細なプロセス",
            "理論構築の論理的道筋",
            "科学的手法とその背景",
            "他の研究者との協力・競争",
        ],
        avoid_points=[
            "過度に感情的な表現",
            "抽象的・曖昧な記述",
            "専門用語の説明なしでの使用",
            "結果だけの記述（プロセス省略）",
            "経歴や業績の単なる羅列",
        ],
        style="客観的・論理的",
        tone="academic",
        example_themes=[
            "アインシュタインが相対性理論を完成させた瞬間",
            "ワトソンとクリックがDNA二重螺旋を発見した日",
            "キュリー夫人がラジウムを発見した夜",
            "ニュートンが万有引力を着想した瞬間",
        ],
        quality_emphasis={
            "factual_density": 1.5,
            "educational_value": 1.4,
            "生成品質": 1.0,
            "象徴性": 1.5,
        },
        iconic_guidance="【世紀の大発見強化】ノーベル賞受賞に至る発見の瞬間、「ユリイカ！」と叫んだ瞬間、人類の歴史を変えた発明の完成、実験室で世界初の成果を確認した瞬間など、科学史に刻まれる象徴的な場面を臨場感を持って描写してください。発見年、研究機関、共同研究者を必ず含めてください。",
    ),
    "スポーツ": PromptTemplate(
        category="スポーツ",
        focus_points=[
            "試合・競技の具体的展開",
            "身体的・精神的挑戦",
            "ライバルとの関係性",
            "トレーニングの工夫と努力",
            "チームダイナミクス",
            "金メダル獲得、世界記録更新など象徴的な瞬間",
        ],
        avoid_points=[
            "過度な感動表現（涙、感動等の多用）",
            "結果のみの記述",
            "抽象的な精神論",
            "経歴や成績の単なる羅列",
        ],
        style="躍動感・臨場感",
        tone="dynamic",
        example_themes=[
            "逆転劇の瞬間",
            "怪我からの復帰",
            "ライバルとの名勝負",
            "記録更新の舞台裏",
        ],
        quality_emphasis={
            "story_quality": 1.3,
            "共感性": 1.2,
            "factual_density": 1.2,
            "象徴性": 1.5,
        },
        iconic_guidance="オリンピック金メダル獲得の瞬間、史上初の記録達成、伝説的な名勝負など、スポーツ史に刻まれる象徴的な場面を具体的に描写してください。",
    ),
    "芸術・文化": PromptTemplate(
        category="芸術・文化",
        focus_points=[
            "【最重要】世紀の傑作誕生の具体的瞬間",
            "作品完成までの創作プロセスと苦悩",
            "インスピレーションの源泉と着想の瞬間",
            "作品が社会・美術史に与えた革命的影響",
            "芸術的葛藤と技法的ブレイクスルー",
            "同時代の芸術家との交流・対立・影響関係",
        ],
        avoid_points=[
            "技術的すぎる専門記述",
            "作品の単なる説明や解説",
            "評論家的な批評",
            "作品一覧や受賞歴の羅列",
        ],
        style="情緒的・描写的",
        tone="artistic",
        example_themes=[
            "モナ・リザ完成の瞬間",
            "ゴッホが星月夜を描いた夜",
            "ピカソがキュビスムを創造した転機",
            "葛飾北斎が富嶽三十六景を構想した瞬間",
        ],
        quality_emphasis={
            "story_quality": 1.5,
            "記憶性": 1.4,
            "意外性": 1.3,
            "象徴性": 1.5,
            "factual_density": 1.2,
        },
        iconic_guidance="【芸術作品誕生エピソード強化】傑作が完成した具体的な瞬間、筆を置いた時の感動、初めて世に出た時の反響など、美術史に刻まれる象徴的場面を臨場感を持って描写してください。作品名、完成年、制作場所を必ず含めてください。",
    ),
    # RCA-20260110: 不足カテゴリ追加
    "文学": PromptTemplate(
        category="文学",
        focus_points=[
            "【最重要】名作誕生の創作過程と完成の瞬間",
            "執筆時の作家の精神状態と環境",
            "作品のインスピレーション源と着想",
            "文学界・社会への影響と受容",
            "出版までの苦労と編集者との関係",
            "読者からの反響と作品の評価",
        ],
        avoid_points=[
            "あらすじの羅列",
            "作品リストの列挙",
            "過度な文学批評",
        ],
        style="文学的・叙情的",
        tone="literary",
        example_themes=[
            "源氏物語執筆の舞台裏",
            "夏目漱石が『坊っちゃん』を書き上げた夜",
            "村上春樹のデビュー作誕生秘話",
        ],
        quality_emphasis={
            "story_quality": 1.5,
            "記憶性": 1.4,
            "factual_density": 1.3,
            "象徴性": 1.4,
        },
        iconic_guidance="名作が生まれた瞬間、最後の一文を書き終えた時の感動、出版後の反響など、文学史に残る象徴的場面を描写してください。",
    ),
    "音楽": PromptTemplate(
        category="音楽",
        focus_points=[
            "【最重要】世紀の名曲誕生の創作過程と完成の瞬間",
            "楽曲のインスピレーションと着想の瞬間",
            "初演・発表時の観客と批評家の反響",
            "音楽的革新と新しいスタイルの確立",
            "他のアーティストとの協力・影響関係",
            "レコーディング現場での決定的瞬間",
        ],
        avoid_points=[
            "楽曲リストの羅列",
            "技術的すぎる音楽理論",
            "売上・チャート順位の羅列",
        ],
        style="リズミカル・情熱的",
        tone="dynamic",
        example_themes=[
            "モーツァルトが『魔笛』を完成させた夜",
            "ビートルズが『Yesterday』を録音した日",
            "クイーンが『ボヘミアン・ラプソディ』を世に出した瞬間",
            "マイケル・ジャクソンが『スリラー』を発表した日",
        ],
        quality_emphasis={
            "story_quality": 1.5,
            "共感性": 1.3,
            "記憶性": 1.4,
            "象徴性": 1.5,
        },
        iconic_guidance="【世紀の名曲誕生強化】名曲が生まれた瞬間、最初のデモ録音、初演の感動、音楽史を変えたパフォーマンスなど、音楽史に刻まれる象徴的場面を臨場感を持って描写してください。曲名、発表年、レコードレーベルを必ず含めてください。",
    ),
    "歴史": PromptTemplate(
        category="歴史",
        focus_points=[
            "歴史の転換点となった具体的出来事",
            "人物の決断とその背景",
            "時代背景と社会状況",
            "後世への影響と歴史的意義",
        ],
        avoid_points=[
            "年表的な羅列",
            "現代視点からの安易な批判",
            "過度な美化",
        ],
        style="客観的・物語的",
        tone="historical",
        example_themes=[
            "本能寺の変の真相",
            "坂本龍馬が薩長同盟を仲介した夜",
            "明治維新の決定的瞬間",
        ],
        quality_emphasis={
            "factual_density": 1.5,
            "educational_value": 1.4,
            "記憶性": 1.3,
            "象徴性": 1.4,
        },
        iconic_guidance="歴史を動かした決定的瞬間、時代の転換点となった出来事を臨場感を持って描写してください。",
    ),
    "医学・健康": PromptTemplate(
        category="医学・健康",
        focus_points=[
            "画期的な医学的発見の瞬間",
            "治療法開発の過程と苦労",
            "患者を救った具体的エピソード",
            "医学界への貢献と影響",
        ],
        avoid_points=[
            "過度に専門的な医学用語",
            "功績リストの羅列",
            "過度に感傷的な表現",
        ],
        style="温かみのある・専門的",
        tone="compassionate",
        example_themes=[
            "北里柴三郎がペスト菌を発見した瞬間",
            "山中伸弥がiPS細胞を作製した日",
            "野口英世の黄熱病研究",
        ],
        quality_emphasis={
            "factual_density": 1.4,
            "educational_value": 1.4,
            "共感性": 1.3,
            "象徴性": 1.3,
        },
        iconic_guidance="人類の健康に貢献した画期的発見、多くの命を救った治療法の誕生など、医学史に残る象徴的場面を描写してください。",
    ),
    "哲学者": PromptTemplate(
        category="哲学者",
        focus_points=[
            "思想形成の背景と転機",
            "著作執筆の過程と完成",
            "思想が社会に与えた影響",
            "他の思想家との対話・論争",
        ],
        avoid_points=[
            "難解な哲学用語の羅列",
            "著作リストの列挙",
            "過度に抽象的な記述",
        ],
        style="思慮深い・知的",
        tone="philosophical",
        example_themes=[
            "デカルトが「我思う、ゆえに我あり」に至った瞬間",
            "カントが純粋理性批判を完成させた夜",
            "西田幾多郎が無の哲学を構築した過程",
        ],
        quality_emphasis={
            "educational_value": 1.5,
            "factual_density": 1.3,
            "記憶性": 1.3,
            "象徴性": 1.4,
        },
        iconic_guidance="思想の転機、著作完成の瞬間、世界観を変えた洞察など、哲学史に残る象徴的場面を描写してください。",
    ),
    "探検・冒険": PromptTemplate(
        category="探検・冒険",
        focus_points=[
            "未踏の地への到達の瞬間",
            "困難と危険の克服",
            "発見の歴史的意義",
            "探検の準備と計画",
        ],
        avoid_points=[
            "行程の単なる羅列",
            "過度に危険を強調",
            "結果だけの記述",
        ],
        style="躍動感・臨場感",
        tone="adventurous",
        example_themes=[
            "コロンブスがアメリカ大陸を発見した瞬間",
            "植村直己が北極点に到達した日",
            "伊能忠敬が日本地図完成に至る旅",
        ],
        quality_emphasis={
            "story_quality": 1.4,
            "記憶性": 1.4,
            "factual_density": 1.3,
            "象徴性": 1.5,
        },
        iconic_guidance="新大陸発見、極地到達、未踏の山頂に立った瞬間など、探検史に刻まれる象徴的場面を臨場感を持って描写してください。",
    ),
    # RCA-20260110: 世紀の名映画・名動画エピソード強化
    "映画・演劇": PromptTemplate(
        category="映画・演劇",
        focus_points=[
            "【最重要】世紀の名作映画誕生の撮影秘話",
            "監督のビジョンと実現過程",
            "俳優たちの演技と撮影現場のエピソード",
            "初公開時の観客・批評家の反応",
            "映画史・演劇史への影響",
            "アカデミー賞・カンヌなど受賞の瞬間",
        ],
        avoid_points=[
            "あらすじの説明",
            "出演作リストの羅列",
            "興行収入の羅列",
            "ゴシップ的内容",
        ],
        style="ドラマチック・臨場感",
        tone="cinematic",
        example_themes=[
            "黒澤明が『七人の侍』を完成させた瞬間",
            "スピルバーグが『E.T.』の最終カットを決めた夜",
            "宮崎駿が『千と千尋の神隠し』でアカデミー賞を受賞した瞬間",
            "チャップリンが『モダン・タイムス』を世に送り出した日",
        ],
        quality_emphasis={
            "story_quality": 1.5,
            "記憶性": 1.4,
            "意外性": 1.3,
            "象徴性": 1.5,
        },
        iconic_guidance="【世紀の名映画誕生強化】名作が完成した瞬間、初公開のプレミア上映、観客のスタンディングオベーション、アカデミー賞のトロフィーを手にした瞬間など、映画史に刻まれる象徴的場面を臨場感を持って描写してください。作品名、公開年、監督名を必ず含めてください。",
    ),
    "動画・デジタルコンテンツ": PromptTemplate(
        category="動画・デジタルコンテンツ",
        focus_points=[
            "【最重要】バイラル動画・名作コンテンツ誕生の瞬間",
            "クリエイターの着想とアイデアの源泉",
            "制作過程と技術的挑戦",
            "視聴者・ユーザーの反響と社会現象",
            "プラットフォーム・業界への影響",
        ],
        avoid_points=[
            "再生回数のみの記述",
            "技術仕様の羅列",
            "プライベートの詳細",
        ],
        style="カジュアル・躍動感",
        tone="engaging",
        example_themes=[
            "YouTubeで1億再生を達成した動画の制作秘話",
            "TikTokで世界的トレンドを生んだ瞬間",
            "ゲーム実況で新ジャンルを開拓した配信者の転機",
            "VTuberブームを生んだ先駆者の挑戦",
        ],
        quality_emphasis={
            "story_quality": 1.4,
            "意外性": 1.4,
            "共感性": 1.3,
            "象徴性": 1.4,
        },
        iconic_guidance="【デジタルコンテンツ誕生強化】バイラルヒットが生まれた瞬間、世界的トレンドを生んだ投稿、新しいメディア表現を確立した転機など、デジタル時代を象徴する出来事を描写してください。プラットフォーム名、投稿日、反響の規模を含めてください。",
    ),
    "政治・経済": PromptTemplate(
        category="政治・経済",
        focus_points=[
            "意思決定の背景と過程",
            "関係者間の交渉・駆け引き",
            "政策・決定の具体的影響",
            "時代背景との関連",
            "リーダーシップの発揮場面",
            "歴史を動かした決断の具体的瞬間",
        ],
        avoid_points=[
            "政治的偏向",
            "現代の価値観での過度な批判",
            "陰謀論的な記述",
            "政策や功績の単なる羅列",
        ],
        style="客観的・分析的",
        tone="analytical",
        example_themes=[
            "歴史的決断の瞬間",
            "危機管理の実際",
            "改革の推進と抵抗",
            "国際関係の転機",
        ],
        quality_emphasis={
            "factual_density": 1.4,
            "educational_value": 1.3,
            "生成品質": 1.2,
            "象徴性": 1.3,
        },
        iconic_guidance="歴史的な条約締結、革命的な政策発表、国家の転機となった演説など、後世に語り継がれる象徴的な場面を描写してください。",
    ),
    "歴史・軍事": PromptTemplate(
        category="歴史・軍事",
        focus_points=[
            "具体的な出来事の詳細",
            "人物の動機と判断",
            "時代背景と社会状況",
            "歴史的転機のメカニズム",
            "後世への影響",
            "歴史の分岐点となった決定的瞬間",
        ],
        avoid_points=[
            "現代視点からの安易な批判",
            "戦争美化",
            "残虐表現の過度な詳細",
            "年表的な出来事の羅列",
        ],
        style="客観的・歴史的",
        tone="historical",
        example_themes=[
            "戦略的判断の分岐点",
            "危機的状況での決断",
            "歴史を変えた瞬間",
            "敗北から学んだ教訓",
        ],
        quality_emphasis={
            "factual_density": 1.5,
            "educational_value": 1.4,
            "記憶性": 1.2,
            "象徴性": 1.4,
        },
        iconic_guidance="新大陸発見、歴史的な戦いの勝利、革命の瞬間など、歴史の流れを変えた象徴的な出来事を臨場感を持って描写してください。",
    ),
    "エンターテインメント": PromptTemplate(
        category="エンターテインメント",
        focus_points=[
            "ブレイクスルーの瞬間",
            "ファンとの関係性",
            "業界での挑戦と革新",
            "キャリアの転機",
            "作品制作の裏話",
            "スターダムへの象徴的な瞬間",
        ],
        avoid_points=[
            "ゴシップ的内容",
            "プライベートの過度な詳細",
            "スキャンダル中心の記述",
            "出演作や活動の単なる羅列",
        ],
        style="親しみやすい・エネルギッシュ",
        tone="engaging",
        example_themes=[
            "デビューの苦労話",
            "大ヒット作の誕生秘話",
            "ジャンルを超えた挑戦",
            "復活劇",
        ],
        quality_emphasis={
            "story_quality": 1.3,
            "共感性": 1.3,
            "意外性": 1.2,
            "象徴性": 1.3,
        },
        iconic_guidance="スターの座を掴んだ瞬間、伝説的なパフォーマンス、業界を変えた革新など、エンターテインメント史に残る象徴的な場面を描写してください。",
    ),
    "ビジネス・起業": PromptTemplate(
        category="ビジネス・起業",
        focus_points=[
            "ビジネスアイデアの着想",
            "困難の克服過程",
            "経営判断の背景",
            "イノベーションの実現方法",
            "チームビルディング",
            "業界を変えた革新的製品・サービスの誕生",
        ],
        avoid_points=[
            "成功礼賛のみ",
            "金銭的成功の過度な強調",
            "失敗の軽視",
            "会社概要や沿革の羅列",
        ],
        style="実践的・インスピレーショナル",
        tone="inspirational",
        example_themes=[
            "ピボットの決断",
            "資金難の乗り越え方",
            "市場創造の瞬間",
            "失敗から学んだビジネス哲学",
        ],
        quality_emphasis={
            "educational_value": 1.3,
            "story_quality": 1.2,
            "factual_density": 1.2,
            "象徴性": 1.4,
        },
        iconic_guidance="ガレージでの創業、革命的製品の発表、IPOの瞬間など、ビジネス界の伝説となった象徴的な場面を描写してください。",
    ),
    "医療・福祉": PromptTemplate(
        category="医療・福祉",
        focus_points=[
            "医学的発見・治療法開発の過程",
            "患者との関わり",
            "倫理的ジレンマへの対応",
            "社会貢献の具体的成果",
            "困難な状況での判断",
            "多くの命を救った画期的な発見・治療",
        ],
        avoid_points=[
            "医学的詳細の過度な専門性",
            "患者プライバシーへの配慮不足",
            "過度に感傷的な表現",
            "功績や受賞歴の羅列",
        ],
        style="温かみのある・専門的",
        tone="compassionate",
        example_themes=[
            "治療法開発のブレイクスルー",
            "難病との闘い",
            "医療制度改革への貢献",
            "緊急事態での対応",
        ],
        quality_emphasis={
            "factual_density": 1.3,
            "共感性": 1.3,
            "educational_value": 1.2,
            "象徴性": 1.3,
        },
        iconic_guidance="ワクチン開発成功、難病克服の瞬間、医学史を変えた発見など、人類の健康に貢献した象徴的な場面を描写してください。",
    ),
    "宗教・思想": PromptTemplate(
        category="宗教・思想",
        focus_points=[
            "思想形成の背景",
            "教えの具体的内容と実践",
            "弟子・信者との関係",
            "社会への影響",
            "思想的転機",
            "悟りや覚醒の象徴的な瞬間",
        ],
        avoid_points=[
            "特定宗教への偏向",
            "現代価値観での安易な批判",
            "神秘主義的な誇張",
            "教義や活動の単なる説明",
        ],
        style="思慮深い・哲学的",
        tone="philosophical",
        example_themes=[
            "悟り・覚醒の瞬間",
            "迫害と信念の貫徹",
            "思想の伝播と発展",
            "宗教間対話の試み",
        ],
        quality_emphasis={
            "educational_value": 1.4,
            "story_quality": 1.2,
            "記憶性": 1.2,
            "象徴性": 1.4,
        },
        iconic_guidance="悟りを開いた瞬間、信仰を貫いた試練、思想が世界に広まった転機など、精神史に残る象徴的な場面を描写してください。",
    ),
    "架空キャラクター": PromptTemplate(
        category="架空キャラクター",
        focus_points=[
            "物語内での具体的行動・決断",
            "キャラクターの成長・変化",
            "他キャラクターとの関係性",
            "物語のテーマとの関連",
            "読者・視聴者への影響",
            "キャラクターを象徴する名場面",
        ],
        avoid_points=[
            "メタ的表現（作者への言及等）",
            "現実との混同",
            "物語外の設定説明",
            "設定や能力の単なる説明",
        ],
        style="物語的・没入感重視",
        tone="narrative",
        example_themes=[
            "決定的な選択の瞬間",
            "仲間との絆",
            "敵との対決",
            "自己発見・成長",
        ],
        quality_emphasis={
            "story_quality": 1.5,
            "記憶性": 1.3,
            "共感性": 1.2,
            "象徴性": 1.3,
        },
        iconic_guidance="そのキャラクターを象徴する名台詞、決定的な決断、感動的なシーンなど、ファンの心に残る象徴的な場面を描写してください。",
    ),
}

# デフォルトテンプレート
DEFAULT_PROMPT_TEMPLATE = PromptTemplate(
    category="一般",
    focus_points=[
        "具体的なエピソード",
        "人物の動機と行動",
        "結果と影響",
        "その人物を象徴する転機や出来事",
    ],
    avoid_points=[
        "抽象的な記述",
        "事実と異なる内容",
        "経歴や業績の単なる羅列",
    ],
    style="バランスの取れた",
    tone="neutral",
    example_themes=["人生の転機", "挑戦と克服", "学びの瞬間"],
    quality_emphasis={
        "factual_density": 1.0,
        "story_quality": 1.0,
        "生成品質": 1.0,
        "象徴性": 1.2,
    },
    iconic_guidance="その人物を象徴する決定的な瞬間、人生を変えた転機、後世に語り継がれる出来事を具体的に描写してください。",
)


# ==============================================================================
# CategoryPromptManager
# ==============================================================================


class CategoryPromptManager:
    """
    カテゴリ別プロンプト管理クラス

    各カテゴリの特性に応じた生成プロンプトを提供。
    """

    def __init__(self, templates: Optional[dict[str, PromptTemplate]] = None):
        self.templates = templates or CATEGORY_PROMPTS

    def get_template(self, category: str) -> PromptTemplate:
        """
        カテゴリのテンプレートを取得

        Args:
            category: カテゴリ名

        Returns:
            PromptTemplate: プロンプトテンプレート
        """
        # 完全一致
        if category in self.templates:
            return self.templates[category]

        # 部分一致
        for key, template in self.templates.items():
            if key in category or category in key:
                return template

        # デフォルト
        return DEFAULT_PROMPT_TEMPLATE

    def build_prompt_instruction(
        self,
        category: str,
        person_name: str,
        age: int,
        additional_context: Optional[str] = None,
    ) -> str:
        """
        プロンプト指示文を構築

        Args:
            category: カテゴリ名
            person_name: 人物名
            age: 年齢
            additional_context: 追加コンテキスト

        Returns:
            str: プロンプト指示文
        """
        template = self.get_template(category)

        # 重点ポイント
        focus_text = "\n".join([f"- {p}" for p in template.focus_points])

        # 避けるポイント
        avoid_text = "\n".join([f"- {p}" for p in template.avoid_points])

        # テーマ例
        themes_text = "、".join(template.example_themes)

        instruction = f"""【カテゴリ特化ガイダンス: {template.category}】

■ 文体・トーン
{template.style}な表現で、{template.tone}なトーンを心がけてください。

■ 重点ポイント（必ず含める）
{focus_text}

■ 避けるべき表現
{avoid_text}

■ 参考テーマ例
{themes_text}

■ 品質重視軸
"""

        for axis, weight in template.quality_emphasis.items():
            if weight > 1.0:
                instruction += f"- {axis}: 特に重視（係数 {weight}）\n"

        # 象徴的瞬間のガイダンスを追加
        if template.iconic_guidance:
            instruction += f"\n■ 象徴的瞬間の描写（重要）\n{template.iconic_guidance}\n"

        if additional_context:
            instruction += f"\n■ 追加情報\n{additional_context}\n"

        return instruction

    def get_quality_weights(self, category: str) -> dict[str, float]:
        """
        カテゴリの品質重み係数を取得

        Args:
            category: カテゴリ名

        Returns:
            dict[str, float]: 品質軸ごとの重み
        """
        template = self.get_template(category)
        # デフォルト重み
        weights = {
            "memorability_score": 1.0,
            "empathy_score": 1.0,
            "surprise_score": 1.0,
            "generation_quality_score": 1.0,
            "educational_value": 1.0,
            "story_quality": 1.0,
            "factual_density": 1.0,
            "iconic_score": 1.0,
        }

        # テンプレートの重みを適用
        for axis, weight in template.quality_emphasis.items():
            if axis in weights:
                weights[axis] = weight
            # 日本語軸名の変換
            axis_map = {
                "factual_density": "factual_density",
                "story_quality": "story_quality",
                "educational_value": "educational_value",
                "記憶性": "memorability_score",
                "共感性": "empathy_score",
                "意外性": "surprise_score",
                "生成品質": "generation_quality_score",
                "象徴性": "iconic_score",
            }
            if axis in axis_map and axis_map[axis] in weights:
                weights[axis_map[axis]] = weight

        return weights

    def list_categories(self) -> list[str]:
        """登録カテゴリ一覧を取得"""
        return list(self.templates.keys())

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得"""
        return {
            "total_categories": len(self.templates),
            "categories": self.list_categories(),
            "average_focus_points": sum(len(t.focus_points) for t in self.templates.values()) / len(self.templates),
            "average_avoid_points": sum(len(t.avoid_points) for t in self.templates.values()) / len(self.templates),
        }


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    print("=== CategoryPromptManager Test ===")

    manager = CategoryPromptManager()

    # カテゴリ一覧
    print(f"\n登録カテゴリ: {len(manager.list_categories())}")
    for cat in manager.list_categories():
        print(f"  - {cat}")

    # 科学・技術テンプレート
    print("\n--- 科学・技術 テンプレート ---")
    template = manager.get_template("科学・技術")
    print(f"文体: {template.style}")
    print(f"トーン: {template.tone}")
    print(f"重点ポイント: {len(template.focus_points)}件")
    print(f"品質重視: {template.quality_emphasis}")

    # プロンプト指示文構築
    print("\n--- プロンプト指示文 ---")
    instruction = manager.build_prompt_instruction(
        category="科学・技術",
        person_name="アインシュタイン",
        age=26,
        additional_context="1905年、特殊相対性理論発表の年",
    )
    print(instruction[:500] + "...")

    # 品質重み
    print("\n--- 品質重み ---")
    weights = manager.get_quality_weights("スポーツ")
    for axis, weight in weights.items():
        if weight != 1.0:
            print(f"  {axis}: {weight}")

    # 統計
    print("\n--- 統計 ---")
    stats = manager.get_stats()
    print(f"総カテゴリ数: {stats['total_categories']}")
    print(f"平均重点ポイント数: {stats['average_focus_points']:.1f}")

    print("\n=== Test Complete ===")
