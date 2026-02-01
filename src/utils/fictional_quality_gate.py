#!/usr/bin/env python3
"""
FictionalQualityGate - 架空キャラクターエピソード品質ゲート

架空キャラクターのエピソード生成時に品質チェックを行い、
違反を検出した場合は修正または再生成を促す。

## 検出ルール
1. 年号違反: 作品設定に基づき禁止年号を検出
2. 現実人物: リストベースで検出
3. 現実企業: リストベースで検出
4. 現実地名: 架空世界作品で検出
5. メタ表現: 「原作では」「この作品では」等
6. キャラクター設定違反: アーク不整合等
7. 世界観設定違反: 技術レベル不整合等

## 統合箇所
1. SAGEオーケストレーター（生成直後）
2. SafeCSVWriter（書き込み直前）

## 使用方法
    gate = FictionalQualityGate()
    result = gate.check(episode)

    if not result.passed:
        if result.fixable:
            episode["episode_text"] = result.auto_fixed_text
        else:
            raise QualityViolationError(result.violations)

Author: EPUP Validation Team
Date: 2026-01-15
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_SETTINGS_PATH = PROJECT_ROOT / "preserved/data/fictional_work_settings_master.json"

# 架空キャラクター判定（RCA-20260123: person_name からの二重チェック用）
from src.utils.fictional_characters import is_fictional_character
from src.utils.authenticity_checker import AuthenticityChecker, AuthenticityStatus


# =============================================================================
# 違反タイプ定義
# =============================================================================


class ViolationType(Enum):
    """違反タイプ"""

    YEAR = "year_violation"  # 年号違反
    YEAR_RANGE = "year_range_violation"  # 許可年号範囲外
    CUSTOM_YEAR = "custom_year_violation"  # 独自年号体系での西暦使用
    TECHNOLOGY = "technology_violation"  # 技術レベル違反
    REAL_PERSON = "real_person"  # 現実人物検出
    REAL_COMPANY = "real_company"  # 現実企業検出
    REAL_LOCATION = "real_location"  # 現実地名検出
    META_EXPRESSION = "meta_expression"  # メタ的表現検出
    CHARACTER_SETTING = "character_setting_violation"  # キャラクター設定違反
    WORLD_SETTING = "world_setting_violation"  # 世界観設定違反
    AUTHENTICITY = "authenticity"  # 真正性違反（canon出典検証失敗）


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class Violation:
    """違反情報"""

    type: ViolationType
    detail: str
    fixable: bool
    suggested_fix: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "detail": self.detail,
            "fixable": self.fixable,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class QualityResult:
    """品質チェック結果"""

    passed: bool
    violations: list[Violation] = field(default_factory=list)
    fixable: bool = False
    auto_fixed_text: Optional[str] = None
    authenticity_status: Optional[AuthenticityStatus] = None
    canon_source: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "fixable": self.fixable,
            "auto_fixed_text": self.auto_fixed_text,
            "authenticity_status": self.authenticity_status.value if self.authenticity_status else None,
            "canon_source": self.canon_source,
        }


class QualityViolationError(Exception):
    """品質違反による例外"""

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        message = "; ".join([f"{v.type.value}: {v.detail}" for v in violations])
        super().__init__(f"Quality violations detected: {message}")


# =============================================================================
# 検出パターン定義
# =============================================================================

# 年号パターン（西暦）
YEAR_PATTERN = re.compile(r"(19[0-9]{2}|20[0-2][0-9])年")

# 現実人物リスト（作者、声優、俳優、実在有名人）
REAL_PERSONS = [
    # 漫画家・作者
    "吾峠呼世晴",
    "尾田栄一郎",
    "岸本斉史",
    "鳥山明",
    "荒木飛呂彦",
    "冨樫義博",
    "井上雄彦",
    "久保帯人",
    "諫山創",
    "堀越耕平",
    "芥見下々",
    "藤本タツキ",
    "和久井健",
    "赤坂アカ",
    "ジョージ・ルーカス",
    "スティーブン・スピルバーグ",
    "J・K・ローリング",
    "宮崎駿",
    "庵野秀明",
    "新海誠",
    "高畑勲",
    "手塚治虫",
    "藤子・F・不二雄",
    "藤子不二雄",
    "赤塚不二夫",
    "永井豪",
    "車田正美",
    "高橋留美子",
    "あだち充",
    "原哲夫",
    "北条司",
    "板垣恵介",
    "森川ジョージ",
    "武論尊",
    "小畑健",
    "大場つぐみ",
    "空知英秋",
    "松井優征",
    "天野明",
    "青山剛昌",
    "秋本治",
    # 声優
    "花江夏樹",
    "鬼頭明里",
    "下野紘",
    "松岡禎丞",
    "日野聡",
    "早見沙織",
    "櫻井孝宏",
    "中村悠一",
    "宮野真守",
    "神谷浩史",
    "小野大輔",
    "杉田智和",
    "子安武人",
    "関智一",
    "緑川光",
    "石田彰",
    "山寺宏一",
    "林原めぐみ",
    "田中真弓",
    "野沢雅子",
    "堀川りょう",
    "古川登志夫",
    "古谷徹",
    "池田秀一",
    "諏訪部順一",
    "津田健次郎",
    "福山潤",
    "鈴村健一",
    "坂本真綾",
    "沢城みゆき",
    "釘宮理恵",
    "水樹奈々",
    "堀江由衣",
    "田村ゆかり",
    "能登麻美子",
    "花澤香菜",
    "戸松遥",
    "豊崎愛生",
    "竹達彩奈",
    "井上麻里奈",
    "佐倉綾音",
    "内田真礼",
    "小倉唯",
    "上坂すみれ",
    "水瀬いのり",
    "雨宮天",
    # 俳優（実写化関連）
    "藤原竜也",
    "小栗旬",
    "山崎賢人",
    "神木隆之介",
    "佐藤健",
    "永野芽郁",
    "浜辺美波",
    "橋本環奈",
    "広瀬すず",
    "広瀬アリス",
    "吉沢亮",
    "菅田将暉",
    "山田裕貴",
    "横浜流星",
    # 有名人・タレント
    "明石家さんま",
    "ビートたけし",
    "タモリ",
    "所ジョージ",
    "松本人志",
    "浜田雅功",
    "有吉弘行",
    "マツコ・デラックス",
]

# 現実企業・組織リスト
REAL_COMPANIES = [
    # 出版社
    "集英社",
    "講談社",
    "小学館",
    "角川",
    "KADOKAWA",
    "秋田書店",
    "白泉社",
    "スクウェア・エニックス",
    "スクエニ",
    # アニメスタジオ
    "ufotable",
    "MAPPA",
    "WIT STUDIO",
    "Production I.G",
    "京都アニメーション",
    "京アニ",
    "サンライズ",
    "ボンズ",
    "マッドハウス",
    "A-1 Pictures",
    "CloverWorks",
    "シャフト",
    "トリガー",
    "TRIGGER",
    "スタジオジブリ",
    "ジブリ",
    "東映アニメーション",
    "東映",
    "ぴえろ",
    "J.C.STAFF",
    # 映画会社・配給
    "ルーカスフィルム",
    "ディズニー",
    "ピクサー",
    "ワーナー・ブラザース",
    "ワーナー",
    "ユニバーサル",
    "20世紀フォックス",
    "東宝",
    "松竹",
    # ゲーム会社
    "任天堂",
    "バンダイナムコ",
    "バンナム",
    "カプコン",
    "セガ",
    "コナミ",
    # テレビ局
    "フジテレビ",
    "日本テレビ",
    "TBS",
    "テレビ朝日",
    "テレビ東京",
    "NHK",
    "WOWOW",
    "Netflix",
    "Amazon Prime",
    "Amazonプライム",
]

# 現実地名リスト（架空世界作品用）
REAL_LOCATIONS = [
    # 日本の都市
    "東京",
    "大阪",
    "京都",
    "名古屋",
    "横浜",
    "神戸",
    "福岡",
    "札幌",
    "仙台",
    "広島",
    "新宿",
    "渋谷",
    "池袋",
    "秋葉原",
    "原宿",
    "六本木",
    "銀座",
    "浅草",
    "上野",
    "品川",
    "北海道",
    "沖縄",
    "九州",
    "四国",
    "関西",
    "関東",
    "東北",
    "中部",
    "中国地方",
    # 世界の都市・国
    "ニューヨーク",
    "ロサンゼルス",
    "ロンドン",
    "パリ",
    "ベルリン",
    "ローマ",
    "北京",
    "上海",
    "香港",
    "ソウル",
    "シンガポール",
    "アメリカ",
    "イギリス",
    "フランス",
    "ドイツ",
    "イタリア",
    "中国",
    "韓国",
    "ロシア",
    "オーストラリア",
    "インド",
    "ブラジル",
    "カナダ",
    "メキシコ",
    # 地理的特徴
    "太平洋",
    "大西洋",
    "インド洋",
    "地中海",
    "日本海",
    "富士山",
    "エベレスト",
    "アマゾン",
    "ナイル",
    "ミシシッピ",
]

# メタ的表現パターン
META_PATTERNS = [
    # 作品言及
    r"この(?:作品|アニメ|漫画|マンガ)(?:では|において|の中で)",
    r"(?:原作|漫画版|アニメ版|映画版|実写版)(?:では|において|の中で|と(?:は|の)違い)",
    r"(?:連載|放送)(?:当時|開始時|終了時)",
    r"(?:作者|原作者)(?:が描いた|の意図|によると)",
    r"(?:ストーリー|展開)(?:上の都合|として設定)",
    r"(?:設定|世界観)(?:上は|として)",
    r"(?:読者|視聴者|ファン)(?:に向けて|から見ると|の間で話題)",
    # 第四の壁を破る表現
    r"(?:伏線|フラグ)(?:が回収|を張)",
    # 作品メタ情報への言及
    r"(?:ベストセラー|大ヒット作)(?:として|になった)",
    r"(?:アワード|漫画賞|アニメ賞)(?:を受賞|にノミネート)",
    # ================================================
    # RCA-20260123: メタ要素検出パターン拡張
    # ================================================
    # 販売・興行成績（キャラクター視点では知り得ない現実世界のメタ情報）
    r"(?:\d+万?本|累計\d+部)(?:を|が)(?:突破|達成|記録|売上)",
    r"(?:興行収入|興行成績|観客動員)(?:\d+|〜)",
    r"(?:セールス|販売実績|売上高)",
    # 製作プロセス（作品外の制作情報）
    r"(?:\d+年間?の)?(?:開発|製作|撮影)(?:期間|準備|開始)",
    r"(?:映画化|アニメ化|実写化|ドラマ化)(?:され|が決定|の発表)",
    # ゲーム的ステータス表示（物語内で不自然な数値表現）
    r"(?:魔力|攻撃力|防御力|判断力|耐久力)(?:\d+%|\d+ポイント)",
    # 現実イベント（架空世界に存在しないイベント）
    r"(?:東京ゲームショウ|E3|コミケ|映画祭|アカデミー賞)",
    # ================================================
    # RCA-20260128: 年号+作品名・シリーズ言及パターン追加
    # ================================================
    # 年号+作品名パターン（「1979年の『機動戦士ガンダム』」等）
    r"(?:19[0-9]{2}|20[0-2][0-9])年の[『「].+?[』」]",
    r"[『「].+?[』」](?:が|は|を)?(?:19[0-9]{2}|20[0-2][0-9])年",
    # シリーズ・続編・劇場版言及
    r"[『「].+?[』」]シリーズ",
    r"(?:シリーズ|続編|前作|次回作|劇場版|OVA|OAD)(?:で|において|の|が|は|を通じて)",
    # 制作・放送・公開年言及
    r"(?:制作|公開|放送|発売|配信|上映)(?:さ?れ|が|は|から).*?(?:19[0-9]{2}|20[0-2][0-9])年",
    # 作品タイトルの直接言及（「不朽の名作」等の評価付き）
    r"[『「].+?[』」](?:で|は)(?:不朽|伝説|金字塔|名作|代表作)",
]

# 独自年号パターン（作品固有の年号表記を検出）
CUSTOM_YEAR_PATTERNS: dict[str, re.Pattern] = {
    "ドラゴンボール": re.compile(r"エイジ\s*\d+"),
    "スター・ウォーズ": re.compile(r"\d+\s*(BBY|ABY)"),
    "ONE PIECE": re.compile(r"海円暦\s*\d+年?"),
    "進撃の巨人": re.compile(r"壁内暦\s*\d+年?"),
    "ロード・オブ・ザ・リング": re.compile(r"第[一二三四]紀\s*\d+年?"),
}

# 技術レベル別禁止キーワード
TECHNOLOGY_LEVEL_FORBIDDEN: dict[str, list[str]] = {
    "pre_modern": [
        "スマートフォン",
        "スマホ",
        "携帯電話",
        "携帯",
        "ケータイ",
        "パソコン",
        "PC",
        "コンピューター",
        "コンピュータ",
        "インターネット",
        "ネット検索",  # 「ネット」単体は除外（「ネットワーク」=人的ネットワークと誤検出）
        "SNS",
        "LINE",
        "Twitter",
        "テレビ",
        "TV",
        "ラジオ",
        "飛行機",
        "自動車",
        "Eメール",  # 「メール」単体は除外（「ベルメール」等の人名と誤検出）
        "電子メール",
        "アプリ",
    ],
}

# 技術レベル検出時の除外パターン（偽陽性防止）
# 禁止キーワードが含まれていても、これらのパターンにマッチする場合は違反としない
TECHNOLOGY_EXCLUSION_PATTERNS: dict[str, list[str]] = {
    "ネット": [
        "ネットワーク",  # 人的ネットワーク/組織ネットワーク
        "バスケットネット",  # スポーツ用品
        "テニスネット",
        "ヘアネット",
        "セーフティネット",  # 比喩的表現
    ],
    "メール": [
        "ベルメール",  # ONE PIECE人物名
        "メールストロム",  # 渦巻き
        "エナメール",
    ],
}


# =============================================================================
# FictionalQualityGate クラス
# =============================================================================


@dataclass
class WorkSetting:
    """作品設定"""

    work_title: str
    work_title_variants: list[str] = field(default_factory=list)
    world_type: str = "fictional"
    era_setting: str = ""
    year_system: str = "none"
    allowed_year_range: str = ""
    forbidden_year_patterns: list[str] = field(default_factory=list)
    allow_real_locations: bool = False
    allow_real_people: bool = False
    technology_level: str = "modern"
    forbidden_keywords: list[str] = field(default_factory=list)
    custom_year_pattern: str = ""  # 独自年号の正規表現パターン


class FictionalQualityGate:
    """
    架空キャラクターエピソードの品質ゲート

    エピソード生成時に品質チェックを行い、違反を検出した場合は
    修正または再生成を促す。
    """

    def __init__(
        self,
        work_settings_path: Optional[Path] = None,
        enable_authenticity_check: bool = True,
    ):
        """
        作品設定マスターを読み込む

        Args:
            work_settings_path: 作品設定JSONファイルのパス
            enable_authenticity_check: 真正性検証を有効化するか（デフォルト: True）
        """
        self.work_settings_path = work_settings_path or DEFAULT_WORK_SETTINGS_PATH
        self._work_settings: dict[str, WorkSetting] = {}
        self._enable_authenticity_check = enable_authenticity_check

        # 正規表現のコンパイル
        self._compile_patterns()

        # 作品設定のロード
        self._load_work_settings()

        # AuthenticityChecker の初期化（canonのみ保存方針）
        self._authenticity_checker: Optional[AuthenticityChecker] = None
        if enable_authenticity_check:
            self._authenticity_checker = AuthenticityChecker()

    def _load_work_settings(self) -> None:
        """作品設定JSONをロード"""
        if not self.work_settings_path.exists():
            # RCA-20260123: サイレント継続ではなくエラーを発生させる
            # 設定ファイル不在で品質ゲートが無効化されることを防ぐ
            raise FileNotFoundError(
                f"Work settings file not found: {self.work_settings_path}. "
                f"FictionalQualityGate cannot function without work settings."
            )

        try:
            with open(self.work_settings_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse work settings JSON: {e}")
            raise ValueError(f"Work settings file is corrupted: {self.work_settings_path}. JSON error: {e}")

        works = data.get("works", {})
        for title, settings in works.items():
            # custom_year_noteからパターンを生成
            custom_year_pattern = ""
            custom_year_note = settings.get("custom_year_note", "")
            if custom_year_note:
                # 「エイジ」「BBY/ABY」「海円暦」等のキーワードを抽出してパターン化
                if "エイジ" in custom_year_note:
                    custom_year_pattern = r"エイジ\s*\d+"
                elif "BBY" in custom_year_note or "ABY" in custom_year_note:
                    custom_year_pattern = r"\d+\s*(BBY|ABY)"
                elif "海円暦" in custom_year_note:
                    custom_year_pattern = r"海円暦\s*\d+年?"
                elif "壁内暦" in custom_year_note:
                    custom_year_pattern = r"壁内暦\s*\d+年?"
                elif "第三紀" in custom_year_note:
                    custom_year_pattern = r"第[一二三四]紀\s*\d+年?"

            work_setting = WorkSetting(
                work_title=settings.get("work_title", title),
                work_title_variants=settings.get("work_title_variants", []),
                world_type=settings.get("world_type", "fictional"),
                era_setting=settings.get("era_setting", ""),
                year_system=settings.get("year_system", "none"),
                allowed_year_range=settings.get("allowed_year_range", ""),
                forbidden_year_patterns=settings.get("forbidden_year_patterns", []),
                allow_real_locations=settings.get("allow_real_locations", False),
                allow_real_people=settings.get("allow_real_people", False),
                technology_level=settings.get("technology_level", "modern"),
                forbidden_keywords=settings.get("forbidden_keywords", []),
                custom_year_pattern=custom_year_pattern,
            )
            self._work_settings[title] = work_setting

            # バリアントも登録
            for variant in settings.get("work_title_variants", []):
                self._work_settings[variant] = work_setting

    def _compile_patterns(self) -> None:
        """正規表現パターンをコンパイル"""
        # 現実人物パターン
        self.real_person_re = re.compile(
            "|".join(re.escape(p) for p in REAL_PERSONS),
            re.IGNORECASE,
        )

        # 現実企業パターン
        self.real_company_re = re.compile(
            "|".join(re.escape(c) for c in REAL_COMPANIES),
            re.IGNORECASE,
        )

        # 現実地名パターン
        self.real_location_re = re.compile(
            "|".join(re.escape(loc) for loc in REAL_LOCATIONS),
        )

        # メタ表現パターン
        self.meta_re = re.compile(
            "|".join(META_PATTERNS),
        )

    def get_work_setting(self, work_title: str) -> Optional[WorkSetting]:
        """作品設定を取得"""
        if not work_title or str(work_title) == "nan":
            return None

        # 完全一致
        if work_title in self._work_settings:
            return self._work_settings[work_title]

        # 部分一致
        for title, setting in self._work_settings.items():
            if title in work_title or work_title in title:
                return setting

        return None

    def check(self, episode: dict) -> QualityResult:
        """
        エピソードの品質チェック

        Args:
            episode: episode_id, person_name, work_title, episode_text, person_type等を含むdict

        Returns:
            QualityResult: 検証結果
        """
        violations: list[Violation] = []

        # 必要なフィールドを取得
        episode_text = str(episode.get("episode_text", ""))
        work_title = str(episode.get("work_title", ""))
        person_type = str(episode.get("person_type", "")).upper()
        person_name = str(episode.get("person_name", ""))

        # RCA-20260123: person_type だけでなく person_name からも架空キャラを判定（二重チェック）
        is_fictional_by_type = "FICTIONAL" in person_type
        is_fictional_by_name = is_fictional_character(person_name)

        # FICTIONALのみ対象（person_type または person_name のいずれかで架空キャラと判定された場合）
        if not is_fictional_by_type and not is_fictional_by_name:
            return QualityResult(passed=True)

        # person_type とperson_name が矛盾する場合は警告
        if is_fictional_by_name and not is_fictional_by_type:
            logger.warning(
                f"FictionalQualityGate: person_type不整合 - {person_name} はFICTIONALであるべき (現在: {person_type})"
            )

        # 作品設定を取得
        work_setting = self.get_work_setting(work_title)

        # 1. 年号違反チェック
        year_violations = self._check_year_violation(episode_text, work_setting)
        violations.extend(year_violations)

        # 2. 現実人物チェック
        person_violations = self._check_real_person(episode_text, work_setting)
        violations.extend(person_violations)

        # 3. 現実企業チェック
        company_violations = self._check_real_company(episode_text)
        violations.extend(company_violations)

        # 4. 現実地名チェック
        location_violations = self._check_real_location(episode_text, work_setting)
        violations.extend(location_violations)

        # 5. メタ表現チェック
        meta_violations = self._check_meta_expression(episode_text)
        violations.extend(meta_violations)

        # 6. 禁止キーワードチェック
        keyword_violations = self._check_forbidden_keywords(episode_text, work_setting)
        violations.extend(keyword_violations)

        # 7. 年号範囲チェック（allowed_year_range）
        year_range_violations = self._check_year_range_violation(episode_text, work_setting)
        violations.extend(year_range_violations)

        # 8. 独自年号体系チェック（custom year_system）
        custom_year_violations = self._check_custom_year_system(episode_text, work_setting)
        violations.extend(custom_year_violations)

        # 9. 技術レベルチェック
        technology_violations = self._check_technology_violation(episode_text, work_setting)
        violations.extend(technology_violations)

        # 10. 真正性検証（AuthenticityChecker による canon 出典チェック）
        authenticity_status: Optional[AuthenticityStatus] = None
        canon_source: Optional[str] = None

        if self._enable_authenticity_check and self._authenticity_checker is not None:
            auth_result = self._authenticity_checker.check(episode)
            authenticity_status = auth_result.status
            canon_source = auth_result.canon_source

            if not auth_result.passed:
                # 真正性違反を追加（fixable=False: 再生成が必要）
                violation_details = ", ".join(auth_result.violations) if auth_result.violations else "canon出典検証失敗"
                violations.append(
                    Violation(
                        type=ViolationType.AUTHENTICITY,
                        detail=f"真正性検証失敗: {violation_details}",
                        fixable=False,  # 再生成が必要
                        suggested_fix=auth_result.suggestion,
                    )
                )

        # 結果を構築
        if not violations:
            return QualityResult(
                passed=True,
                authenticity_status=authenticity_status,
                canon_source=canon_source,
            )

        # 修正可能性を判定
        fixable_violations = [v for v in violations if v.fixable]
        all_fixable = len(fixable_violations) == len(violations)

        # 自動修正を試行
        auto_fixed_text = None
        if all_fixable:
            auto_fixed_text = self.auto_fix(episode, violations)

        return QualityResult(
            passed=False,
            violations=violations,
            fixable=all_fixable,
            auto_fixed_text=auto_fixed_text,
            authenticity_status=authenticity_status,
            canon_source=canon_source,
        )

    def _check_year_violation(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """年号違反をチェック"""
        violations: list[Violation] = []

        if not work_setting:
            return violations

        # forbidden_year_patterns がない場合はスキップ
        if not work_setting.forbidden_year_patterns:
            return violations

        # エピソードテキストから年号を抽出
        found_years = YEAR_PATTERN.findall(episode_text)

        for year_str in found_years:
            year = int(year_str)

            # forbidden_year_patterns をチェック
            for pattern in work_setting.forbidden_year_patterns:
                is_forbidden = False
                if "-" in pattern:
                    # 範囲パターン: "1900-2026"
                    try:
                        start, end = pattern.split("-")
                        if int(start) <= year <= int(end):
                            is_forbidden = True
                    except ValueError as e:
                        # RCA-20260123: 範囲パターン解析例外を警告ログに出力
                        logger.warning(f"Invalid year range pattern '{pattern}': {e}")
                        continue
                elif pattern.isdigit():
                    # 単一年パターン
                    if year == int(pattern):
                        is_forbidden = True

                if is_forbidden:
                    violations.append(
                        Violation(
                            type=ViolationType.YEAR,
                            detail=f"{year}年は{work_setting.era_setting}の{work_setting.work_title}では使用禁止",
                            fixable=True,
                            suggested_fix=f"{year}年 -> ある年",
                        )
                    )
                    break

        return violations

    def _check_real_person(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """現実人物をチェック"""
        violations: list[Violation] = []

        # 現実人物が許可されている作品はスキップ
        if work_setting and work_setting.allow_real_people:
            return violations

        matches = self.real_person_re.findall(episode_text)
        for match in matches:
            violations.append(
                Violation(
                    type=ViolationType.REAL_PERSON,
                    detail=f"現実人物「{match}」への言及",
                    fixable=True,
                    suggested_fix=f"「{match}」を削除",
                )
            )

        return violations

    def _check_real_company(self, episode_text: str) -> list[Violation]:
        """現実企業・組織をチェック"""
        violations: list[Violation] = []

        matches = self.real_company_re.findall(episode_text)
        for match in matches:
            violations.append(
                Violation(
                    type=ViolationType.REAL_COMPANY,
                    detail=f"現実企業「{match}」への言及",
                    fixable=True,
                    suggested_fix=f"「{match}」を削除",
                )
            )

        return violations

    def _check_real_location(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """現実地名をチェック（架空世界作品のみ）"""
        violations: list[Violation] = []

        # 現実地名が許可されている作品はスキップ
        if work_setting and work_setting.allow_real_locations:
            return violations

        # 架空世界作品のみチェック
        if work_setting and work_setting.world_type not in ["fictional"]:
            return violations

        matches = self.real_location_re.findall(episode_text)
        for match in matches:
            violations.append(
                Violation(
                    type=ViolationType.REAL_LOCATION,
                    detail=f"架空世界作品での現実地名「{match}」使用",
                    fixable=False,  # 地名削除は文脈を破壊するため修正不可
                    suggested_fix=None,
                )
            )

        return violations

    def _check_meta_expression(self, episode_text: str) -> list[Violation]:
        """メタ的表現をチェック"""
        violations: list[Violation] = []

        matches = self.meta_re.findall(episode_text)
        for match in matches:
            violations.append(
                Violation(
                    type=ViolationType.META_EXPRESSION,
                    detail=f"メタ表現「{match}」を検出",
                    fixable=False,  # メタ表現の修正は再生成が必要
                    suggested_fix=None,
                )
            )

        return violations

    def _check_forbidden_keywords(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """禁止キーワードをチェック"""
        violations: list[Violation] = []

        if not work_setting or not work_setting.forbidden_keywords:
            return violations

        for keyword in work_setting.forbidden_keywords:
            if keyword in episode_text:
                violations.append(
                    Violation(
                        type=ViolationType.WORLD_SETTING,
                        detail=f"作品設定に反するキーワード「{keyword}」を検出",
                        fixable=False,
                        suggested_fix=None,
                    )
                )

        return violations

    def _parse_allowed_year_range(self, range_str: str) -> tuple[int, int] | None:
        """許可年号範囲をパース（西暦/和暦両対応）

        Examples:
            "1980-2000" → (1980, 2000)
            "大正元年-大正15年（1912-1926）" → (1912, 1926)
            "明治元年-明治45年（1868-1912）" → (1868, 1912)

        Returns:
            (start_year, end_year) or None if parse fails
        """
        if not range_str:
            return None

        # 西暦範囲形式: "1980-2000"
        simple_match = re.match(r"^(\d{4})-(\d{4})$", range_str)
        if simple_match:
            return int(simple_match.group(1)), int(simple_match.group(2))

        # 和暦形式: "大正元年-大正15年（1912-1926）"
        # 括弧内の西暦を抽出
        paren_match = re.search(r"（(\d{4})-(\d{4})）", range_str)
        if paren_match:
            return int(paren_match.group(1)), int(paren_match.group(2))

        return None

    def _check_year_range_violation(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """allowed_year_range外の年号を検出"""
        violations: list[Violation] = []

        if not work_setting or not work_setting.allowed_year_range:
            return violations

        year_range = self._parse_allowed_year_range(work_setting.allowed_year_range)
        if not year_range:
            return violations

        start_year, end_year = year_range

        # 西暦年号の検出
        found_years = YEAR_PATTERN.findall(episode_text)
        for year_str in found_years:
            year = int(year_str)
            if year < start_year or year > end_year:
                violations.append(
                    Violation(
                        type=ViolationType.YEAR_RANGE,
                        detail=f"{year}年は{work_setting.work_title}の許可範囲({start_year}-{end_year})外",
                        fixable=True,
                        suggested_fix=f"{year}年 -> ある年",
                    )
                )

        return violations

    def _check_custom_year_system(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """独自年号体系の作品で西暦使用を検出"""
        violations: list[Violation] = []

        if not work_setting:
            return violations

        # year_system="custom"の作品のみ対象
        if work_setting.year_system != "custom":
            return violations

        # 西暦年号の検出
        found_years = YEAR_PATTERN.findall(episode_text)
        if found_years:
            violations.append(
                Violation(
                    type=ViolationType.CUSTOM_YEAR,
                    detail=f"{work_setting.work_title}では独自年号体系を使用（西暦{found_years[0]}年は禁止）",
                    fixable=True,
                    suggested_fix="西暦を削除、または作品固有の年号表記を使用",
                )
            )

        return violations

    def _check_technology_violation(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[Violation]:
        """技術レベル違反をチェック"""
        violations: list[Violation] = []

        if not work_setting:
            return violations

        tech_level = work_setting.technology_level
        if tech_level not in TECHNOLOGY_LEVEL_FORBIDDEN:
            return violations

        forbidden_words = TECHNOLOGY_LEVEL_FORBIDDEN[tech_level]

        for word in forbidden_words:
            if word in episode_text:
                violations.append(
                    Violation(
                        type=ViolationType.TECHNOLOGY,
                        detail=f"{work_setting.work_title}（{tech_level}）に不適切な技術用語「{word}」",
                        fixable=False,
                        suggested_fix=None,
                    )
                )
                # 最初の1つだけ報告（大量の違反を防ぐ）
                break

        return violations

    def auto_fix(self, episode: dict, violations: list[Violation]) -> Optional[str]:
        """
        修正可能な違反を自動修正

        - 年号削除: 「2019年」→「ある年」
        - 現実企業名削除: 「ディズニー社」→ 削除（前後の文脈を保持）
        - 現実人物名削除: 「荒木飛呂彦と」→ 削除（前後の文脈を保持）

        Args:
            episode: エピソードデータ
            violations: 違反リスト

        Returns:
            修正後のエピソードテキスト（修正不可の場合はNone）
        """
        episode_text = str(episode.get("episode_text", ""))

        # 修正不可の違反があればNoneを返す
        if any(not v.fixable for v in violations):
            return None

        modified_text = episode_text

        for violation in violations:
            if violation.type == ViolationType.YEAR:
                # 年号を「ある年」に置換
                year_match = re.search(r"(19[0-9]{2}|20[0-2][0-9])年", modified_text)
                if year_match:
                    modified_text = modified_text.replace(f"{year_match.group(1)}年", "ある年", 1)

            elif violation.type == ViolationType.YEAR_RANGE:
                # 許可範囲外の年号を「ある年」に置換
                year_match = re.search(r"(19[0-9]{2}|20[0-2][0-9])年", modified_text)
                if year_match:
                    modified_text = modified_text.replace(f"{year_match.group(1)}年", "ある年", 1)

            elif violation.type == ViolationType.CUSTOM_YEAR:
                # 独自年号体系での西暦を「ある年」に置換
                year_match = re.search(r"(19[0-9]{2}|20[0-2][0-9])年", modified_text)
                if year_match:
                    modified_text = modified_text.replace(f"{year_match.group(1)}年", "ある年", 1)

            elif violation.type == ViolationType.REAL_PERSON:
                # 現実人物名を削除（前後の助詞も考慮）
                for person in REAL_PERSONS:
                    # 「{人物名}と」「{人物名}の」「{人物名}が」等のパターンを削除
                    patterns = [
                        rf"{re.escape(person)}(?:と|の|が|は|を|に|で|から|まで)",
                        re.escape(person),
                    ]
                    for pattern in patterns:
                        modified_text = re.sub(pattern, "", modified_text)

            elif violation.type == ViolationType.REAL_COMPANY:
                # 現実企業名を削除（前後の助詞も考慮）
                for company in REAL_COMPANIES:
                    patterns = [
                        rf"{re.escape(company)}(?:社|株式会社)?(?:と|の|が|は|を|に|で|から|まで|への)",
                        re.escape(company),
                    ]
                    for pattern in patterns:
                        modified_text = re.sub(pattern, "", modified_text)

        # 空白の正規化（連続空白を単一空白に）
        modified_text = re.sub(r"\s+", " ", modified_text).strip()

        # 修正があった場合のみ返す
        if modified_text != episode_text:
            return modified_text

        return None


# =============================================================================
# ユーティリティ関数
# =============================================================================


def check_fictional_quality(episode: dict, enable_authenticity_check: bool = True) -> QualityResult:
    """
    架空キャラクターエピソードの品質チェック（シンプルAPI）

    Args:
        episode: エピソードデータ
        enable_authenticity_check: 真正性検証を有効化するか（デフォルト: True）

    Returns:
        QualityResult: 検証結果
    """
    gate = FictionalQualityGate(enable_authenticity_check=enable_authenticity_check)
    return gate.check(episode)


def validate_and_fix_fictional_episode(episode: dict, enable_authenticity_check: bool = True) -> tuple[bool, str]:
    """
    架空キャラクターエピソードの検証と自動修正

    Args:
        episode: エピソードデータ
        enable_authenticity_check: 真正性検証を有効化するか（デフォルト: True）

    Returns:
        (passed, episode_text): 検証結果と（修正後の）エピソードテキスト
    """
    gate = FictionalQualityGate(enable_authenticity_check=enable_authenticity_check)
    result = gate.check(episode)

    if result.passed:
        return True, str(episode.get("episode_text", ""))

    if result.fixable and result.auto_fixed_text:
        return True, result.auto_fixed_text

    return False, str(episode.get("episode_text", ""))


# =============================================================================
# CLI (テスト用)
# =============================================================================


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="FictionalQualityGate - 架空キャラクターエピソード品質ゲート")
    parser.add_argument(
        "--text",
        type=str,
        help="チェックするエピソードテキスト",
    )
    parser.add_argument(
        "--work-title",
        type=str,
        default="鬼滅の刃",
        help="作品タイトル（デフォルト: 鬼滅の刃）",
    )
    parser.add_argument(
        "--person-type",
        type=str,
        default="FICTIONAL",
        help="人物タイプ（デフォルト: FICTIONAL）",
    )

    args = parser.parse_args()

    if args.text:
        episode = {
            "episode_text": args.text,
            "work_title": args.work_title,
            "person_type": args.person_type,
        }
        gate = FictionalQualityGate()
        result = gate.check(episode)

        print("=" * 60)
        print("FictionalQualityGate 検証結果")
        print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print(f"Passed: {result.passed}")
        print(f"Fixable: {result.fixable}")

        if result.violations:
            print(f"\nViolations ({len(result.violations)}件):")
            for i, v in enumerate(result.violations, 1):
                print(f"  {i}. [{v.type.value}] {v.detail}")
                if v.suggested_fix:
                    print(f"     -> Suggested fix: {v.suggested_fix}")

        if result.auto_fixed_text:
            print(f"\nAuto-fixed text:\n{result.auto_fixed_text}")
    else:
        # デモモード
        demo_episodes = [
            {
                "episode_text": "2019年、竈門炭治郎は集英社から出版された漫画の主人公として活躍した。",
                "work_title": "鬼滅の刃",
                "person_type": "FICTIONAL",
            },
            {
                "episode_text": "ある年の春、炭治郎は師匠のもとで修行を積んでいた。",
                "work_title": "鬼滅の刃",
                "person_type": "FICTIONAL",
            },
        ]

        gate = FictionalQualityGate()
        print("=" * 60)
        print("FictionalQualityGate デモ")
        print("=" * 60)

        for i, episode in enumerate(demo_episodes, 1):
            print(f"\n[Episode {i}]")
            print(f"Text: {episode['episode_text'][:50]}...")
            result = gate.check(episode)
            print(f"Passed: {result.passed}")
            if result.violations:
                for v in result.violations:
                    print(f"  - {v.type.value}: {v.detail}")
            if result.auto_fixed_text:
                print(f"Auto-fixed: {result.auto_fixed_text[:50]}...")
