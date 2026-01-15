#!/usr/bin/env python3
from __future__ import annotations

"""
EPUP: 架空キャラクターエピソード ルールベース品質検証スクリプト

11,691件のFICTIONALエピソードから、ルールベースで検出可能な違反を高速に検出する。

## 検出ルール
1. 年号違反検出 - 歴史設定作品に現代年号
2. 現実人物検出 - 作者、声優、実在有名人への言及
3. 現実企業・組織検出 - ルーカスフィルム、集英社等
4. 現実地名検出 - 架空世界作品での実在地名使用
5. メタ的表現検出 - 「この作品では」「原作では」等

## 使用方法
    python scripts/validation/fictional_episode_rule_check.py
    python scripts/validation/fictional_episode_rule_check.py --rule year
    python scripts/validation/fictional_episode_rule_check.py --work-title "鬼滅の刃"
    python scripts/validation/fictional_episode_rule_check.py --limit 100

Author: EPUP Validation Team
Date: 2026-01-15
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# パス定義
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
WORK_SETTINGS_JSON = PROJECT_ROOT / "preserved/data/fictional_work_settings_master.json"
REPORT_DIR = PROJECT_ROOT / "src/reports"


# =============================================================================
# 違反タイプ定義
# =============================================================================


class ViolationType(Enum):
    """違反タイプ"""

    YEAR = "year"  # 年号違反
    REAL_PERSON = "real_person"  # 現実人物検出
    REAL_COMPANY = "real_company"  # 現実企業・組織検出
    REAL_LOCATION = "real_location"  # 現実地名検出
    META = "meta"  # メタ的表現検出


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
    "タツキ",
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
    "星野桂",
    "矢吹健太朗",
    "椎名高志",
    "青山剛昌",
    "秋本治",
    "こち亀作者",
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

# 現実人物言及パターン
REAL_PERSON_PATTERNS = [
    r"(.+?)(?:と共に|との|の協力|から(?:評価|指導|助言)|に(?:師事|弟子入り)|と(?:対談|共演|コラボ))",
    r"(.+?)(?:先生|監督|氏|さん)(?:が|は|の|に|と|を)",
    r"(?:作者|原作者|監督|声優|俳優)の(.+?)(?:が|は|の|に|と|を)",
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
    "東映",
    # ゲーム会社
    "任天堂",
    "バンダイナムコ",
    "バンナム",
    "スクウェア・エニックス",
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

# 現実企業言及パターン
REAL_COMPANY_PATTERNS = [
    r"(.+?)(?:で(?:働く|勤務|入社|就職)|に(?:入社|就職|所属)|と(?:契約|提携|コラボ))",
    r"(.+?)(?:の(?:社員|スタッフ|メンバー|一員))",
    r"(?:出版社|制作会社|スタジオ|映画会社)の(.+?)(?:が|は|の|に|と|を)",
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
    # 作品言及（明確なメタ参照のみ）
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
]


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class Violation:
    """違反情報"""

    episode_id: str
    person_name: str
    work_title: str
    violation_type: ViolationType
    violation_detail: str
    episode_text_snippet: str


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


# =============================================================================
# ルールチェッカークラス
# =============================================================================


class FictionalEpisodeRuleChecker:
    """
    架空キャラクターエピソード ルールベースチェッカー

    高速なルールベース検出で、11,000件以上のエピソードを効率的に検証する。
    """

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        work_settings_json: Path = WORK_SETTINGS_JSON,
    ):
        self.master_csv = master_csv
        self.work_settings_json = work_settings_json

        self._master_df: Optional[pd.DataFrame] = None
        self._work_settings: dict[str, WorkSetting] = {}

        # 統計情報
        self.stats: dict[str, int | dict[str, int]] = {
            "total_checked": 0,
            "violations_by_type": {v.value: 0 for v in ViolationType},
            "violations_by_work": {},
        }

        # 作品設定のロード
        self._load_work_settings()

        # 正規表現のコンパイル
        self._compile_patterns()

    def _load_work_settings(self) -> None:
        """作品設定JSONをロード"""
        if not self.work_settings_json.exists():
            print(f"Warning: Work settings not found: {self.work_settings_json}")
            return

        with open(self.work_settings_json, encoding="utf-8") as f:
            data = json.load(f)

        works = data.get("works", {})
        for title, settings in works.items():
            self._work_settings[title] = WorkSetting(
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
            )

            # バリアントも登録
            for variant in settings.get("work_title_variants", []):
                self._work_settings[variant] = self._work_settings[title]

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

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

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

    def check_year_violation(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[tuple[str, str]]:
        """年号違反をチェック"""
        violations: list[tuple[str, str]] = []

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
                if "-" in pattern:
                    # 範囲パターン: "1900-2026"
                    start, end = pattern.split("-")
                    if int(start) <= year <= int(end):
                        snippet = self._get_snippet(episode_text, f"{year}年")
                        violations.append((f"{year}年（禁止範囲: {pattern}）", snippet))
                        break
                elif pattern.isdigit():
                    # 単一年パターン
                    if year == int(pattern):
                        snippet = self._get_snippet(episode_text, f"{year}年")
                        violations.append((f"{year}年", snippet))
                        break

        return violations

    def check_real_person(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[tuple[str, str]]:
        """現実人物をチェック"""
        violations: list[tuple[str, str]] = []

        # 現実人物が許可されている作品はスキップ
        if work_setting and work_setting.allow_real_people:
            return violations

        matches = self.real_person_re.findall(episode_text)
        for match in matches:
            snippet = self._get_snippet(episode_text, match)
            violations.append((f"現実人物: {match}", snippet))

        return violations

    def check_real_company(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[tuple[str, str]]:
        """現実企業・組織をチェック"""
        violations: list[tuple[str, str]] = []

        matches = self.real_company_re.findall(episode_text)
        for match in matches:
            snippet = self._get_snippet(episode_text, match)
            violations.append((f"現実企業: {match}", snippet))

        return violations

    def check_real_location(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[tuple[str, str]]:
        """現実地名をチェック（架空世界作品のみ）"""
        violations: list[tuple[str, str]] = []

        # 現実地名が許可されている作品はスキップ
        if work_setting and work_setting.allow_real_locations:
            return violations

        # 架空世界作品のみチェック
        if work_setting and work_setting.world_type not in ["fictional"]:
            return violations

        matches = self.real_location_re.findall(episode_text)
        for match in matches:
            snippet = self._get_snippet(episode_text, match)
            violations.append((f"現実地名: {match}", snippet))

        return violations

    def check_meta_expression(self, episode_text: str, work_setting: Optional[WorkSetting]) -> list[tuple[str, str]]:
        """メタ的表現をチェック"""
        violations: list[tuple[str, str]] = []

        matches = self.meta_re.findall(episode_text)
        for match in matches:
            snippet = self._get_snippet(episode_text, match)
            violations.append((f"メタ表現: {match}", snippet))

        return violations

    def _get_snippet(self, text: str, keyword: str, context_len: int = 40) -> str:
        """キーワード周辺のスニペットを取得"""
        if not keyword or keyword not in text:
            return text[:80] + "..." if len(text) > 80 else text

        idx = text.find(keyword)
        start = max(0, idx - context_len)
        end = min(len(text), idx + len(keyword) + context_len)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def check_episode(self, row: dict, enabled_rules: Optional[list[str]] = None) -> list[Violation]:
        """単一エピソードをチェック"""
        violations: list[Violation] = []

        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()
        episode_text = str(row.get("episode_text", ""))
        work_title = str(row.get("work_title", ""))

        # FICTIONALのみ対象
        if "FICTIONAL" not in person_type:
            return violations

        # 作品設定を取得
        work_setting = self.get_work_setting(work_title)

        # 有効なルール（デフォルトは全て）
        if enabled_rules is None:
            enabled_rules = ["year", "real_person", "real_company", "real_location", "meta"]

        # 1. 年号違反チェック
        if "year" in enabled_rules:
            year_violations = self.check_year_violation(episode_text, work_setting)
            for detail, snippet in year_violations:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        work_title=work_title,
                        violation_type=ViolationType.YEAR,
                        violation_detail=detail,
                        episode_text_snippet=snippet,
                    )
                )

        # 2. 現実人物チェック
        if "real_person" in enabled_rules:
            person_violations = self.check_real_person(episode_text, work_setting)
            for detail, snippet in person_violations:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        work_title=work_title,
                        violation_type=ViolationType.REAL_PERSON,
                        violation_detail=detail,
                        episode_text_snippet=snippet,
                    )
                )

        # 3. 現実企業チェック
        if "real_company" in enabled_rules:
            company_violations = self.check_real_company(episode_text, work_setting)
            for detail, snippet in company_violations:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        work_title=work_title,
                        violation_type=ViolationType.REAL_COMPANY,
                        violation_detail=detail,
                        episode_text_snippet=snippet,
                    )
                )

        # 4. 現実地名チェック
        if "real_location" in enabled_rules:
            location_violations = self.check_real_location(episode_text, work_setting)
            for detail, snippet in location_violations:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        work_title=work_title,
                        violation_type=ViolationType.REAL_LOCATION,
                        violation_detail=detail,
                        episode_text_snippet=snippet,
                    )
                )

        # 5. メタ表現チェック
        if "meta" in enabled_rules:
            meta_violations = self.check_meta_expression(episode_text, work_setting)
            for detail, snippet in meta_violations:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        work_title=work_title,
                        violation_type=ViolationType.META,
                        violation_detail=detail,
                        episode_text_snippet=snippet,
                    )
                )

        return violations

    def scan_all_episodes(
        self,
        enabled_rules: Optional[list[str]] = None,
        work_title_filter: Optional[str] = None,
        limit: int = 0,
    ) -> list[Violation]:
        """全エピソードをスキャン"""
        all_violations: list[Violation] = []

        if self.master_df.empty:
            print(f"Error: Master CSV not found: {self.master_csv}")
            return all_violations

        # FICTIONALのみフィルタ
        df = self.master_df[self.master_df["person_type"].str.upper().str.contains("FICTIONAL", na=False)]

        # 作品タイトルフィルタ
        if work_title_filter:
            df = df[df["work_title"].str.contains(work_title_filter, na=False)]  # type: ignore[union-attr]

        self.stats["total_checked"] = len(df)
        print(f"検証対象: {len(df)}件のFICTIONALエピソード")

        violations_by_type = self.stats["violations_by_type"]
        violations_by_work = self.stats["violations_by_work"]
        if not isinstance(violations_by_type, dict) or not isinstance(violations_by_work, dict):
            raise TypeError("stats structure is invalid")

        for _, row in df.iterrows():  # type: ignore[union-attr]
            violations = self.check_episode(row.to_dict(), enabled_rules)

            for v in violations:
                all_violations.append(v)

                # 統計更新
                violations_by_type[v.violation_type.value] += 1
                work = v.work_title or "不明"
                violations_by_work[work] = violations_by_work.get(work, 0) + 1

            # リミット
            if limit > 0 and len(all_violations) >= limit:
                break

        return all_violations

    def export_csv(self, violations: list[Violation], output_path: Path) -> None:
        """違反リストをCSVにエクスポート"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "episode_id",
                    "person_name",
                    "work_title",
                    "violation_type",
                    "violation_detail",
                    "episode_text_snippet",
                ]
            )

            for v in violations:
                writer.writerow(
                    [
                        v.episode_id,
                        v.person_name,
                        v.work_title,
                        v.violation_type.value,
                        v.violation_detail,
                        v.episode_text_snippet,
                    ]
                )

        print(f"CSVエクスポート完了: {output_path}")


# =============================================================================
# CLI
# =============================================================================


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 架空キャラクターエピソード ルールベース品質検証")
    parser.add_argument(
        "--rule",
        choices=["year", "real_person", "real_company", "real_location", "meta", "all"],
        default="all",
        help="検証するルール（デフォルト: all）",
    )
    parser.add_argument(
        "--work-title",
        type=str,
        help="特定の作品タイトルでフィルタ",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="検出する違反の最大件数（0=無制限）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(REPORT_DIR / "fictional_rule_violations.csv"),
        help="出力CSVファイルパス",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="CSVエクスポートをスキップ",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )

    args = parser.parse_args()

    # ルール設定
    if args.rule == "all":
        enabled_rules = ["year", "real_person", "real_company", "real_location", "meta"]
    else:
        enabled_rules = [args.rule]

    # ヘッダー
    print("=" * 70)
    print("EPUP: 架空キャラクターエピソード ルールベース品質検証")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"検証ルール: {', '.join(enabled_rules)}")
    print("=" * 70)

    # チェッカー初期化
    checker = FictionalEpisodeRuleChecker()

    # スキャン実行
    print("\nスキャン中...")
    violations = checker.scan_all_episodes(
        enabled_rules=enabled_rules,
        work_title_filter=args.work_title,
        limit=args.limit,
    )

    # 結果サマリー
    print("\n" + "=" * 70)
    print("検出結果サマリー")
    print("=" * 70)
    print(f"検証対象: {checker.stats['total_checked']}件")
    print(f"検出違反: {len(violations)}件")

    violations_by_type = checker.stats["violations_by_type"]
    violations_by_work = checker.stats["violations_by_work"]

    print("\n違反タイプ別:")
    if isinstance(violations_by_type, dict):
        for vtype, count in sorted(violations_by_type.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {vtype}: {count}件")

    if isinstance(violations_by_work, dict) and violations_by_work:
        print("\n作品別（上位10件）:")
        sorted_works = sorted(violations_by_work.items(), key=lambda x: -x[1])
        for work, count in sorted_works[:10]:
            print(f"  {work}: {count}件")

    # 詳細表示
    if args.verbose and violations:
        print("\n" + "-" * 70)
        print("違反詳細（上位20件）:")
        print("-" * 70)
        for i, v in enumerate(violations[:20], 1):
            print(f"\n{i}. [{v.violation_type.value}] {v.episode_id}")
            print(f"   人物: {v.person_name}")
            print(f"   作品: {v.work_title}")
            print(f"   詳細: {v.violation_detail}")
            print(f"   スニペット: {v.episode_text_snippet}")

    # CSVエクスポート
    if not args.no_export and violations:
        output_path = Path(args.output)
        checker.export_csv(violations, output_path)

    print("\n[完了]")
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
