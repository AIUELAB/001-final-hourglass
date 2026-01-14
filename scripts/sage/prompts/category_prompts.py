"""Category Prompt Manager - Phase 7D (Compressed)"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ==============================================================================
# 共通定義
# ==============================================================================

COMMON_AVOID_POINTS = ["経歴や業績の単なる羅列", "抽象的・曖昧な記述"]

# H4最適化: Prompt Caching用にシステムプロンプトを分割
SYSTEM_PROMPT_STATIC = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール】
1. すべての文を丁寧語（です・ます調）で終えてください
   - 正: 「〜しました。」「〜でした。」「〜です。」「〜ます。」
   - 誤: 「〜した。」「〜だった。」「〜だ。」「〜である。」
2. 主語は人物名または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じX歳のとき、[人物名]は」形式で開始してください

【禁止事項】
- 常体（だ・である調）での文末
- 一人称（私、俺、僕）
- メタ的表現（「〜と言われています」「〜かもしれません」）
- 経歴や業績の単なる羅列
- 抽象的な表現（「成功を収めた」「活躍した」のみ）

【架空キャラクター専用ルール】
架空キャラクターの場合、以下を絶対に守ってください：
- 物語の「中」で起きた出来事のみを書く（作品内の冒険、戦い、成長等）
- 禁止：アニメ化、放送開始、興行収入、視聴率、連載開始、原作、声優
- 禁止：「読者」「視聴者」「ファン」「社会現象」など作品外の視点
- 禁止：ディズニーランド、テーマパーク、アトラクション、グッズ、DVD売上
- 禁止：「人気を受けて」「興行成績」「観客動員」「オリコン」
- 例: 悟空なら「フリーザと戦った」はOK、「アニメが放送開始した」はNG

【品質基準】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 300〜400文字で完結"""

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

【架空キャラクター専用ルール】
架空キャラクターの場合、以下を絶対に守ってください：
- 物語の「中」で起きた出来事のみを書く（作品内の冒険、戦い、成長等）
- 禁止：アニメ化、放送開始、興行収入、視聴率、連載開始、原作、声優
- 禁止：「読者」「視聴者」「ファン」「社会現象」など作品外の視点
- 禁止：ディズニーランド、テーマパーク、アトラクション、グッズ、DVD売上
- 禁止：「人気を受けて」「興行成績」「観客動員」「オリコン」
- 例: 悟空なら「フリーザと戦った」はOK、「アニメが放送開始した」はNG

【品質基準】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 300〜400文字で完結"""


def get_system_prompt(person_name: str, age: int) -> str:
    """システムプロンプトを取得"""
    return SYSTEM_PROMPT_TEMPLATE.format(person_name=person_name, age=age)


def get_static_system_prompt() -> str:
    """H4最適化: キャッシュ用の固定システムプロンプトを取得"""
    return SYSTEM_PROMPT_STATIC


@dataclass
class PromptTemplate:
    """プロンプトテンプレート"""

    category: str
    focus_points: list[str] = field(default_factory=list)
    avoid_points: list[str] = field(default_factory=list)
    style: str = "客観的"
    tone: str = "neutral"
    example_themes: list[str] = field(default_factory=list)
    quality_emphasis: dict[str, float] = field(default_factory=dict)
    iconic_guidance: str = ""

    def to_dict(self) -> dict[str, Any]:
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
        avoid_points=COMMON_AVOID_POINTS + ["過度に感情的な表現", "専門用語の説明なしでの使用", "結果だけの記述"],
        style="客観的・論理的",
        tone="academic",
        example_themes=["アインシュタインが相対性理論を完成させた瞬間", "ワトソンとクリックがDNA二重螺旋を発見した日"],
        quality_emphasis={"factual_density": 1.5, "educational_value": 1.4, "生成品質": 1.0, "象徴性": 1.5},
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
        avoid_points=COMMON_AVOID_POINTS + ["過度な感動表現", "結果のみの記述", "抽象的な精神論"],
        style="躍動感・臨場感",
        tone="dynamic",
        example_themes=["逆転劇の瞬間", "怪我からの復帰"],
        quality_emphasis={"story_quality": 1.3, "共感性": 1.2, "factual_density": 1.2, "象徴性": 1.5},
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
        avoid_points=["技術的すぎる専門記述", "作品の単なる説明や解説", "評論家的な批評", "作品一覧や受賞歴の羅列"],
        style="情緒的・描写的",
        tone="artistic",
        example_themes=["モナ・リザ完成の瞬間", "ゴッホが星月夜を描いた夜"],
        quality_emphasis={"story_quality": 1.5, "記憶性": 1.4, "意外性": 1.3, "象徴性": 1.5, "factual_density": 1.2},
        iconic_guidance="【芸術作品誕生エピソード強化】傑作が完成した具体的な瞬間、筆を置いた時の感動、初めて世に出た時の反響など、美術史に刻まれる象徴的場面を臨場感を持って描写してください。作品名、完成年、制作場所を必ず含めてください。",
    ),
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
        avoid_points=["あらすじの羅列", "作品リストの列挙", "過度な文学批評"],
        style="文学的・叙情的",
        tone="literary",
        example_themes=["源氏物語執筆の舞台裏", "夏目漱石が『坊っちゃん』を書き上げた夜"],
        quality_emphasis={"story_quality": 1.5, "記憶性": 1.4, "factual_density": 1.3, "象徴性": 1.4},
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
        avoid_points=["楽曲リストの羅列", "技術的すぎる音楽理論", "売上・チャート順位の羅列"],
        style="リズミカル・情熱的",
        tone="dynamic",
        example_themes=["モーツァルトが『魔笛』を完成させた夜", "ビートルズが『Yesterday』を録音した日"],
        quality_emphasis={"story_quality": 1.5, "共感性": 1.3, "記憶性": 1.4, "象徴性": 1.5},
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
        avoid_points=["年表的な羅列", "現代視点からの安易な批判", "過度な美化"],
        style="客観的・物語的",
        tone="historical",
        example_themes=["本能寺の変の真相", "坂本龍馬が薩長同盟を仲介した夜"],
        quality_emphasis={"factual_density": 1.5, "educational_value": 1.4, "記憶性": 1.3, "象徴性": 1.4},
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
        avoid_points=["過度に専門的な医学用語", "功績リストの羅列", "過度に感傷的な表現"],
        style="温かみのある・専門的",
        tone="compassionate",
        example_themes=["北里柴三郎がペスト菌を発見した瞬間", "山中伸弥がiPS細胞を作製した日"],
        quality_emphasis={"factual_density": 1.4, "educational_value": 1.4, "共感性": 1.3, "象徴性": 1.3},
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
        avoid_points=["難解な哲学用語の羅列", "著作リストの列挙", "過度に抽象的な記述"],
        style="思慮深い・知的",
        tone="philosophical",
        example_themes=["デカルトが「我思う、ゆえに我あり」に至った瞬間", "カントが純粋理性批判を完成させた夜"],
        quality_emphasis={"educational_value": 1.5, "factual_density": 1.3, "記憶性": 1.3, "象徴性": 1.4},
        iconic_guidance="思想の転機、著作完成の瞬間、世界観を変えた洞察など、哲学史に残る象徴的場面を描写してください。",
    ),
    "探検・冒険": PromptTemplate(
        category="探検・冒険",
        focus_points=["未踏の地への到達の瞬間", "困難と危険の克服", "発見の歴史的意義", "探検の準備と計画"],
        avoid_points=["行程の単なる羅列", "過度に危険を強調", "結果だけの記述"],
        style="躍動感・臨場感",
        tone="adventurous",
        example_themes=["コロンブスがアメリカ大陸を発見した瞬間", "植村直己が北極点に到達した日"],
        quality_emphasis={"story_quality": 1.4, "記憶性": 1.4, "factual_density": 1.3, "象徴性": 1.5},
        iconic_guidance="新大陸発見、極地到達、未踏の山頂に立った瞬間など、探検史に刻まれる象徴的場面を臨場感を持って描写してください。",
    ),
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
        avoid_points=["あらすじの説明", "出演作リストの羅列", "興行収入の羅列", "ゴシップ的内容"],
        style="ドラマチック・臨場感",
        tone="cinematic",
        example_themes=[
            "黒澤明が『七人の侍』を完成させた瞬間",
            "宮崎駿が『千と千尋の神隠し』でアカデミー賞を受賞した瞬間",
        ],
        quality_emphasis={"story_quality": 1.5, "記憶性": 1.4, "意外性": 1.3, "象徴性": 1.5},
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
        avoid_points=["再生回数のみの記述", "技術仕様の羅列", "プライベートの詳細"],
        style="カジュアル・躍動感",
        tone="engaging",
        example_themes=["YouTubeで1億再生を達成した動画の制作秘話", "TikTokで世界的トレンドを生んだ瞬間"],
        quality_emphasis={"story_quality": 1.4, "意外性": 1.4, "共感性": 1.3, "象徴性": 1.4},
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
        avoid_points=COMMON_AVOID_POINTS + ["政治的偏向", "現代の価値観での過度な批判", "陰謀論的な記述"],
        style="客観的・分析的",
        tone="analytical",
        example_themes=["歴史的決断の瞬間", "危機管理の実際"],
        quality_emphasis={"factual_density": 1.4, "educational_value": 1.3, "生成品質": 1.2, "象徴性": 1.3},
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
        avoid_points=["現代視点からの安易な批判", "戦争美化", "残虐表現の過度な詳細", "年表的な出来事の羅列"],
        style="客観的・歴史的",
        tone="historical",
        example_themes=["戦略的判断の分岐点", "危機的状況での決断"],
        quality_emphasis={"factual_density": 1.5, "educational_value": 1.4, "記憶性": 1.2, "象徴性": 1.4},
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
        avoid_points=COMMON_AVOID_POINTS + ["ゴシップ的内容", "プライベートの過度な詳細", "スキャンダル中心の記述"],
        style="親しみやすい・エネルギッシュ",
        tone="engaging",
        example_themes=["デビューの苦労話", "大ヒット作の誕生秘話"],
        quality_emphasis={"story_quality": 1.3, "共感性": 1.3, "意外性": 1.2, "象徴性": 1.3},
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
        avoid_points=["成功礼賛のみ", "金銭的成功の過度な強調", "失敗の軽視", "会社概要や沿革の羅列"],
        style="実践的・インスピレーショナル",
        tone="inspirational",
        example_themes=["ピボットの決断", "資金難の乗り越え方"],
        quality_emphasis={"educational_value": 1.3, "story_quality": 1.2, "factual_density": 1.2, "象徴性": 1.4},
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
        avoid_points=COMMON_AVOID_POINTS
        + ["医学的詳細の過度な専門性", "患者プライバシーへの配慮不足", "過度に感傷的な表現"],
        style="温かみのある・専門的",
        tone="compassionate",
        example_themes=["治療法開発のブレイクスルー", "難病との闘い"],
        quality_emphasis={"factual_density": 1.3, "共感性": 1.3, "educational_value": 1.2, "象徴性": 1.3},
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
        avoid_points=COMMON_AVOID_POINTS + ["特定宗教への偏向", "現代価値観での安易な批判", "神秘主義的な誇張"],
        style="思慮深い・哲学的",
        tone="philosophical",
        example_themes=["悟り・覚醒の瞬間", "迫害と信念の貫徹"],
        quality_emphasis={"educational_value": 1.4, "story_quality": 1.2, "記憶性": 1.2, "象徴性": 1.4},
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
        avoid_points=["メタ的表現（作者への言及等）", "現実との混同", "物語外の設定説明", "設定や能力の単なる説明"],
        style="物語的・没入感重視",
        tone="narrative",
        example_themes=["決定的な選択の瞬間", "仲間との絆"],
        quality_emphasis={"story_quality": 1.5, "記憶性": 1.3, "共感性": 1.2, "象徴性": 1.3},
        iconic_guidance="そのキャラクターを象徴する名台詞、決定的な決断、感動的なシーンなど、ファンの心に残る象徴的な場面を描写してください。",
    ),
    # Phase 27: 架空キャラ・動物拡張カテゴリ
    "神話・伝説": PromptTemplate(
        category="神話・伝説",
        focus_points=[
            "神話・伝説内での具体的な偉業・冒険",
            "神々や英雄との関係性・対決",
            "試練を乗り越えた象徴的な瞬間",
            "人間界への影響と教訓",
            "神話的な力の発現・覚醒",
            "運命との対峙・宿命の達成",
        ],
        avoid_points=[
            "現代的な解釈の押し付け",
            "学術的な神話学の説明",
            "複数の神話バージョンの混同",
            "能力や設定の単なる説明",
        ],
        style="壮大・叙事詩的",
        tone="epic",
        example_themes=["ヘラクレスが12の功業を達成した瞬間", "孫悟空（西遊記）が天界で暴れた日"],
        quality_emphasis={"story_quality": 1.5, "記憶性": 1.4, "意外性": 1.2, "象徴性": 1.5},
        iconic_guidance="神話・伝説の中で語り継がれる象徴的な場面を、臨場感を持って描写してください。神々の力、英雄の勇気、運命との対峙など、時代を超えて人々の心に刻まれる瞬間を描いてください。",
    ),
    "アニメ・漫画": PromptTemplate(
        category="アニメ・漫画",
        focus_points=[
            "作品内での象徴的な名シーン・名場面",
            "キャラクターの成長・覚醒の瞬間",
            "仲間との絆・友情の描写",
            "強敵との決戦・死闘",
            "夢や目標に向かう決意の瞬間",
            "名台詞・名シーンの文脈と意味",
        ],
        avoid_points=[
            "メタ的表現（作者、読者への言及）",
            "作品外の設定・裏話",
            "アニメと漫画のバージョン違いの混同",
            "戦闘力や能力値の羅列",
        ],
        style="熱血・感動的",
        tone="passionate",
        example_themes=["孫悟空（DB）が初めてスーパーサイヤ人に覚醒した瞬間", "ルフィが仲間を守るために立ち上がった時"],
        quality_emphasis={"story_quality": 1.5, "共感性": 1.4, "記憶性": 1.4, "象徴性": 1.5},
        iconic_guidance="アニメ・漫画ファンの心に刻まれた名シーンを、作品内の視点で臨場感を持って描写してください。覚醒、決戦、別れ、再会など、ファンが涙した瞬間を再現してください。",
    ),
    "ゲーム": PromptTemplate(
        category="ゲーム",
        focus_points=[
            "ゲーム内での象徴的な冒険・達成",
            "主人公としての決断・選択の瞬間",
            "強敵・ラスボスとの決戦",
            "仲間との出会いと別れ",
            "世界を救う・平和をもたらす瞬間",
            "プレイヤーの心に残る名シーン",
        ],
        avoid_points=[
            "ゲームシステムやプレイ方法の説明",
            "現実世界のゲーム開発・発売情報",
            "プレイヤーキャラクターとしての言及",
            "ステータスや能力値の説明",
        ],
        style="冒険的・ヒロイック",
        tone="adventurous",
        example_themes=["マリオがピーチ姫を救出した瞬間", "リンクがガノンドロフを倒した決戦"],
        quality_emphasis={"story_quality": 1.4, "意外性": 1.3, "記憶性": 1.4, "象徴性": 1.4},
        iconic_guidance="ゲームの世界観の中で、キャラクターとして体験した象徴的な冒険を描写してください。ボス戦、エンディング、仲間との絆など、ゲーマーの心に残る瞬間を描いてください。",
    ),
    "競走馬": PromptTemplate(
        category="競走馬",
        focus_points=[
            "レースでの激闘・激走の瞬間",
            "ゴール前の逆転劇・接戦",
            "三冠達成・歴史的記録の瞬間",
            "騎手との絆・信頼関係",
            "ライバル馬との名勝負",
            "引退レース・最後の走り",
        ],
        avoid_points=["血統や配合の詳細説明", "オッズや配当金の話", "調教師・馬主の経営話", "獣医学的な説明"],
        style="躍動感・ドラマチック",
        tone="dramatic",
        example_themes=["ディープインパクトが三冠を達成した瞬間", "オグリキャップのラストラン"],
        quality_emphasis={"story_quality": 1.4, "記憶性": 1.4, "共感性": 1.3, "象徴性": 1.5},
        iconic_guidance="競馬ファンの心に刻まれた名レース、名シーンを臨場感を持って描写してください。ゴール前の激闘、奇跡の逆転、感動の引退レースなど、競馬史に残る瞬間を描いてください。レース名、年、着順を含めてください。",
    ),
    "歴史的動物": PromptTemplate(
        category="歴史的動物",
        focus_points=[
            "人々の心を動かした具体的エピソード",
            "飼い主・人間との絆",
            "社会に与えた影響",
            "動物としての本能と愛情",
            "最期の時・別れの瞬間",
            "後世に語り継がれる理由",
        ],
        avoid_points=["擬人化しすぎた表現", "生物学的な説明", "動物の気持ちの過度な推測", "感傷的すぎる表現"],
        style="温かみ・感動的",
        tone="heartwarming",
        example_themes=["ハチ公が渋谷駅で主人を待ち続けた日々", "タマ駅長が和歌山電鉄を救った物語"],
        quality_emphasis={"共感性": 1.5, "story_quality": 1.4, "記憶性": 1.4, "象徴性": 1.4},
        iconic_guidance="動物と人間の絆、動物が社会に与えた影響を、事実に基づいて感動的に描写してください。過度な擬人化は避けつつ、動物の純粋さと人々の愛情を描いてください。",
    ),
}

# ==============================================================================
# 年齢帯別プロンプトガイダンス
# ==============================================================================

AGE_GUIDANCE: dict[str, dict] = {
    "early_childhood": {
        "age_range": (1, 9),
        "focus_points": [
            "家庭環境と両親からの影響",
            "才能の萌芽・最初の兆候",
            "幼少期の印象的な出来事",
            "早熟な才能を示した具体的エピソード",
        ],
        "example_themes": ["3歳でピアノを弾き始めたモーツァルト", "5歳で絵を描き始めたピカソ"],
        "quality_note": "この年齢では具体的な業績より、将来の才能を予感させる印象的な出来事に焦点を当ててください。",
    },
    "youth": {
        "age_range": (10, 14),
        "focus_points": [
            "学校での出来事・恩師との運命的な出会い",
            "才能が開花した具体的瞬間・目覚め",
            "初めての大きな挑戦・デビュー・コンクール",
            "進路を決定づけた転機・決意の瞬間",
            "習い事・スポーツでの初めての成功体験",
            "夢を持つきっかけとなった出来事",
            "少年少女時代の冒険・発見・創造",
            "初めてのファン・観客・支持者との出会い",
        ],
        "example_themes": ["12歳でプロ棋士になった藤井聡太", "14歳でオリンピック出場した体操選手"],
        "quality_note": "思春期・少年少女時代ならではの「初めての経験」「夢への目覚め」「才能の開花」に焦点を当て、将来への伏線となる印象的なエピソードを描写してください。この年齢層は現在極端に不足しているため、積極的に生成してください。",
    },
    "young_adult": {
        "age_range": (15, 29),
        "focus_points": [
            "デビュー・初めての大きな成功",
            "挫折と克服の経験",
            "メンターや仲間との出会い",
            "独自のスタイル確立",
        ],
        "example_themes": ["26歳で相対性理論を発表したアインシュタイン", "20歳でデビューして大ヒットした歌手"],
        "quality_note": "キャリアの出発点や転機となった出来事、若い頃の野心と挑戦を臨場感を持って描写してください。",
    },
    "mature_adult": {
        "age_range": (30, 50),
        "focus_points": [
            "代表的な業績・傑作の完成",
            "社会的影響力の確立",
            "リーダーシップの発揮",
            "人生の転機となる決断",
        ],
        "example_themes": ["35歳で『神曲』を書き始めたダンテ", "40歳で世界記録を更新したアスリート"],
        "quality_note": "最も充実した時期の代表的業績や、人生を象徴する出来事に焦点を当ててください。",
    },
    "senior_adult": {
        "age_range": (51, 69),
        "focus_points": [
            "キャリアの集大成となる業績",
            "後進への指導・影響",
            "新たな挑戦・第二のキャリア",
            "人生経験に基づく洞察",
        ],
        "example_themes": ["60歳で新境地を開いた芸術家", "長年の研究が実を結んだ科学者"],
        "quality_note": "経験と実績に裏打ちされた円熟期の活動、後世への貢献に焦点を当ててください。",
    },
    "elderly": {
        "age_range": (70, 89),
        "focus_points": [
            "晩年も精力的に続けた活動",
            "後世に残したレガシー",
            "人生を振り返る象徴的な場面",
            "年齢を超えた挑戦・功績",
        ],
        "example_themes": ["80歳で新作を発表した黒澤明", "70代で世界一周を達成した冒険家"],
        "quality_note": "年齢を超えた活力、積み重ねた経験からの洞察、後世への影響に焦点を当ててください。",
    },
    "super_elderly": {
        "age_range": (90, 100),
        "focus_points": [
            "【重要】90歳を超えても続いた活動",
            "長寿を支えた秘訣やエピソード",
            "最晩年まで持ち続けた情熱",
            "100年近い人生を象徴する出来事",
        ],
        "example_themes": ["93歳で現役を続けた葛飾北斎", "100歳を超えて創作活動を続けた篠田桃紅"],
        "quality_note": "【超高齢エピソード品質強化】90歳以上の非常に稀少な年齢帯です。長寿の秘訣、最晩年まで続いた情熱、1世紀に渡る人生の重みを感じさせる臨場感のあるエピソードを描写してください。具体的な年号、場所、発言を必ず含めてください。",
    },
}


def get_age_guidance(age: int) -> Optional[dict]:
    """年齢に応じたプロンプトガイダンスを取得"""
    for guidance in AGE_GUIDANCE.values():
        age_min, age_max = guidance["age_range"]
        if age_min <= age <= age_max:
            return guidance
    return None


DEFAULT_PROMPT_TEMPLATE = PromptTemplate(
    category="一般",
    focus_points=["具体的なエピソード", "人物の動機と行動", "結果と影響", "その人物を象徴する転機や出来事"],
    avoid_points=COMMON_AVOID_POINTS + ["事実と異なる内容"],
    style="バランスの取れた",
    tone="neutral",
    example_themes=["人生の転機", "挑戦と克服"],
    quality_emphasis={"factual_density": 1.0, "story_quality": 1.0, "生成品質": 1.0, "象徴性": 1.2},
    iconic_guidance="その人物を象徴する決定的な瞬間、人生を変えた転機、後世に語り継がれる出来事を具体的に描写してください。",
)


# ==============================================================================
# CategoryPromptManager
# ==============================================================================


class CategoryPromptManager:
    """カテゴリ別プロンプト管理クラス"""

    def __init__(self, templates: Optional[dict[str, PromptTemplate]] = None):
        self.templates = templates or CATEGORY_PROMPTS

    def get_template(self, category: str) -> PromptTemplate:
        """カテゴリのテンプレートを取得"""
        if category in self.templates:
            return self.templates[category]
        for key, template in self.templates.items():
            if key in category or category in key:
                return template
        return DEFAULT_PROMPT_TEMPLATE

    def build_prompt_instruction(
        self,
        category: str,
        person_name: str,
        age: int,
        additional_context: Optional[str] = None,
    ) -> str:
        """プロンプト指示文を構築"""
        _ = person_name  # API互換性のため保持（カテゴリガイダンスでは未使用）
        template = self.get_template(category)
        focus_text = "\n".join([f"- {p}" for p in template.focus_points])
        avoid_text = "\n".join([f"- {p}" for p in template.avoid_points])
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

        if template.iconic_guidance:
            instruction += f"\n■ 象徴的瞬間の描写（重要）\n{template.iconic_guidance}\n"

        age_guidance = get_age_guidance(age)
        if age_guidance:
            instruction += f"\n■ 年齢帯別ガイダンス（{age}歳）\n"
            instruction += f"【品質ノート】{age_guidance['quality_note']}\n"
            instruction += "【この年齢帯の重点ポイント】\n"
            for point in age_guidance["focus_points"]:
                instruction += f"- {point}\n"
            instruction += "【参考例】\n"
            for theme in age_guidance["example_themes"][:2]:
                instruction += f"- {theme}\n"

        if additional_context:
            instruction += f"\n■ 追加情報\n{additional_context}\n"

        return instruction

    def get_quality_weights(self, category: str) -> dict[str, float]:
        """カテゴリの品質重み係数を取得"""
        template = self.get_template(category)
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
        for axis, weight in template.quality_emphasis.items():
            if axis in weights:
                weights[axis] = weight
            if axis in axis_map and axis_map[axis] in weights:
                weights[axis_map[axis]] = weight
        return weights

    def list_categories(self) -> list[str]:
        return list(self.templates.keys())

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_categories": len(self.templates),
            "categories": self.list_categories(),
            "average_focus_points": sum(len(t.focus_points) for t in self.templates.values()) / len(self.templates),
            "average_avoid_points": sum(len(t.avoid_points) for t in self.templates.values()) / len(self.templates),
        }


if __name__ == "__main__":
    print("=== CategoryPromptManager Test ===")
    manager = CategoryPromptManager()
    print(f"\n登録カテゴリ: {len(manager.list_categories())}")
    for cat in manager.list_categories():
        print(f"  - {cat}")
    print("\n--- 科学・技術 テンプレート ---")
    template = manager.get_template("科学・技術")
    print(f"文体: {template.style}, トーン: {template.tone}")
    print(f"重点ポイント: {len(template.focus_points)}件, 品質重視: {template.quality_emphasis}")
    print("\n--- プロンプト指示文 ---")
    instruction = manager.build_prompt_instruction(
        "科学・技術", "アインシュタイン", 26, "1905年、特殊相対性理論発表の年"
    )
    print(instruction[:500] + "...")
    print("\n--- 品質重み ---")
    weights = manager.get_quality_weights("スポーツ")
    for axis, weight in weights.items():
        if weight != 1.0:
            print(f"  {axis}: {weight}")
    print("\n--- 統計 ---")
    stats = manager.get_stats()
    print(f"総カテゴリ数: {stats['total_categories']}, 平均重点ポイント数: {stats['average_focus_points']:.1f}")
    print("\n=== Test Complete ===")
