#!/usr/bin/env python3
"""
EPUP: メタ要素違反検出スクリプト

既存エピソードからメタ要素違反を検出する。
架空キャラクターのエピソードで、作品メタ情報（販売本数、製作プロセス等）が
混入しているケースを特定する。

## 検出対象
1. 販売・興行成績 - 「980万本を売上」「興行収入100億円」
2. 製作プロセス - 「開発期間5年」「映画化が決定」
3. ゲーム的ステータス - 「魔力500ポイント」
4. 現実イベント - 「東京ゲームショウ」「E3」「アカデミー賞」
5. 作品言及表現 - 「この作品では」「原作では」

## 使用方法
    # ドライラン（検出のみ）
    python scripts/validation/detect_meta_element_violations.py --dry-run

    # レポート出力
    python scripts/validation/detect_meta_element_violations.py --output report.txt

    # 処理件数上限
    python scripts/validation/detect_meta_element_violations.py --limit 100

    # 違反エピソードをLLMで再生成して修正
    python scripts/validation/detect_meta_element_violations.py --fix

    # 違反エピソードを削除（再生成なし）
    python scripts/validation/detect_meta_element_violations.py --delete-only

    # バッチサイズ指定（デフォルト10件ずつ）
    python scripts/validation/detect_meta_element_violations.py --fix --batch-size 20

Author: EPUP Validation Team
Date: 2026-01-23
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

# RCA-20260130: 共通モジュールから架空キャラクターリストをインポート
# 独自定義のセットを削除し、単一ソースを使用
from src.utils.fictional_characters import ALL_FICTIONAL_CHARACTERS

# =============================================================================
# パス設定
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"

# =============================================================================
# ロギング設定
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# メタ要素パターン定義
# =============================================================================

# カテゴリ別メタ要素パターン
META_PATTERNS: dict[str, list[str]] = {
    # 販売・興行成績
    "販売本数": [
        r"(?:\d+万?本|累計\d+部)(?:を|が)(?:突破|達成|記録|売上)",
        r"(?:販売|売上)[が高]?(?:\d+|記録)",
        r"(?:売れ行き|販売実績|売上高)",
        r"(?:\d+(?:万|億)?部)(?:以上)?(?:を|が)?(?:突破|達成|記録|売上|販売)",
    ],
    "興行成績": [
        r"(?:興行収入|興行成績|観客動員)(?:が)?(?:\d+|〜|が|は)",
        r"(?:動員数|観客数)(?:\d+万人|が)",
        r"(?:歴代|過去)(?:\d+位|最高)",
        r"(?:大ヒット|メガヒット)(?:を記録|作品)",
    ],
    # 製作プロセス
    "開発・製作": [
        r"(?:\d+年間?の)?(?:開発|製作|撮影)(?:期間|準備|開始|が始)",
        r"(?:映画化|アニメ化|実写化|ドラマ化|ゲーム化)(?:され|が決定|の発表|が発表)",
        r"(?:スタッフ|キャスト|声優)(?:が発表|が決定|陣)",
        r"(?:制作|製作)(?:委員会|チーム|スタッフ)",
        r"(?:原作|脚本|監督)(?:を担当|が)",
    ],
    # ゲーム的ステータス（架空世界内ならOKだが、メタ視点は問題）
    "ゲーム的表現": [
        r"(?:魔力|攻撃力|防御力|判断力|耐久力|HP|MP|レベル)(?:\d+%?|\d+ポイント|が\d+)",
        r"(?:ステータス|パラメータ|能力値)(?:が|は|の)",
        r"(?:スキル|アビリティ)(?:を習得|がレベル|ポイント)",
    ],
    # 現実イベント
    "現実イベント": [
        r"(?:東京ゲームショウ|E3|コミケ|コミックマーケット|映画祭)",
        r"(?:アカデミー賞|グラミー賞|エミー賞|カンヌ|ベネチア)",
        r"(?:ジャンプフェスタ|アニメジャパン|AnimeJapan)",
        r"(?:ワンダーフェスティバル|ワンフェス)",
    ],
    # 作品言及（メタ参照）
    "作品メタ言及": [
        r"この(?:作品|アニメ|漫画|マンガ|ゲーム)(?:では|において|の中で|は)",
        r"(?:原作|漫画版|アニメ版|映画版|実写版|ゲーム版)(?:では|において|の中で|と(?:は|の)違い)",
        r"(?:連載|放送|配信)(?:当時|開始時|終了時|中)",
        r"(?:作者|原作者|監督)(?:が描いた|の意図|によると|が)",
        r"(?:ストーリー|展開)(?:上の都合|として設定)",
        r"(?:設定|世界観)(?:上は|として|では)",
        r"(?:読者|視聴者|ファン|プレイヤー)(?:に向けて|から見ると|の間で話題|人気)",
    ],
    # 第四の壁を破る表現
    "第四の壁": [
        r"(?:伏線|フラグ)(?:が回収|を張|の回収)",
        r"(?:ネタバレ|ネタばれ)(?:注意|になる)",
        r"(?:作品内|物語内|劇中)(?:では|で)",
    ],
    # 受賞・評価
    "受賞・評価": [
        r"(?:ベストセラー|大ヒット作|名作)(?:として|になった|に選ばれ)",
        r"(?:アワード|漫画賞|アニメ賞|ゲーム賞)(?:を受賞|にノミネート|で受賞)",
        r"(?:ランキング|人気投票)(?:\d+位|で|に)",
        r"(?:評価|レビュー|批評)(?:が高い|を受け)",
    ],
    # メディア展開
    "メディア展開": [
        r"(?:グッズ|フィギュア|プラモデル)(?:が発売|化|展開)",
        r"(?:コラボ|タイアップ)(?:が決定|商品|キャンペーン)",
        r"(?:舞台化|ミュージカル化|2\.5次元)",
    ],
    # 架空性言及
    "架空性言及": [
        r"架空の(?:キャラクター|人物|存在)",
        r"フィクション(?:の|である|として)",
        r"実在(?:しない|の人物ではない)",
        r"(?:物語|創作)(?:上の|の中の)",
    ],
    # ================================================
    # RCA-20260128: 年号+作品名・シリーズ言及パターン追加
    # ================================================
    "年号+作品名": [
        r"(?:19[0-9]{2}|20[0-2][0-9])年の[『「].+?[』」]",
        r"[『「].+?[』」](?:が|は|を)?(?:19[0-9]{2}|20[0-2][0-9])年",
    ],
    "シリーズ・続編言及": [
        r"[『「].+?[』」]シリーズ",
        r"(?:シリーズ|続編|前作|次回作|劇場版|OVA|OAD)(?:で|において|の|が|は|を通じて)",
    ],
    "制作年言及": [
        r"(?:制作|公開|放送|発売|配信|上映)(?:さ?れ|が|は|から).*?(?:19[0-9]{2}|20[0-2][0-9])年",
    ],
    "作品評価メタ": [
        r"[『「].+?[』」](?:で|は)(?:不朽|伝説|金字塔|名作|代表作)",
    ],
    # ================================================
    # RCA-20260128: 広範メタ要素パターン追加
    # ================================================
    "現実企業名": [
        r"任天堂|スクウェア・エニックス|バンダイナムコ|カプコン|コナミ|セガ",
        r"集英社|講談社|小学館|角川|KADOKAWA",
        r"週刊少年ジャンプ|少年マガジン|少年サンデー|Vジャンプ",
        r"ソニー・ピクチャーズ|ワーナー・ブラザース|ユニバーサル",
        r"NHK|Netflix|Amazon\s*Prime|Disney\+",
    ],
    "現実人物名_作者": [
        r"鳥山明|尾田栄一郎|岸本斉史|荒川弘|手塚治虫|藤子不二雄|藤子・F・不二雄",
        r"宮崎駿|庵野秀明|新海誠|高橋留美子|冨樫義博|久保帯人|諫山創",
        r"堀越耕平|芥見下々|吾峠呼世晴|藤本タツキ|空知英秋",
        r"テリー・プラチェット|J\.?K\.?\s*ローリング|トールキン",
    ],
    "現実商業施設_イベント": [
        r"ブロードウェイ|ハリウッド|Broadway|Hollywood",
        r"ウォルト・ディズニー(?:・カンパニー)?|Walt\s*Disney",
        r"秋葉原|渋谷109|原宿|六本木ヒルズ",
        r"レコード大賞|紅白歌合戦|オリコン",
    ],
    "ファン_動員メタ": [
        r"\d+万人(?:以上)?の(?:ファン|観客|動員|視聴者|読者)",
        r"(?:ファン|観客|動員数|来場者)(?:が|を)?\d+(?:万|億)?人",
        r"全世界(?:で|の)?\d+(?:万|億)(?:人|部|本)",
        r"オーディション(?:合格率|通過率)\d+",
    ],
    "販売実績_拡張": [
        r"\d+(?:万|億)?(?:本|部|枚|巻)(?:を|が)?(?:突破|達成|売上|販売|出荷|発行)",
        r"(?:累計|総|全世界)\d+(?:万|億)?(?:部|本|枚|巻)",
        r"(?:ベストセラー|ロングセラー|ミリオンセラー|ダブルミリオン)",
    ],
}

# コンパイル済みパターン（キャッシュ用）
_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = {}


def get_compiled_patterns() -> dict[str, list[re.Pattern[str]]]:
    """コンパイル済みパターンを取得（遅延初期化）"""
    global _COMPILED_PATTERNS
    if not _COMPILED_PATTERNS:
        for category, patterns in META_PATTERNS.items():
            _COMPILED_PATTERNS[category] = [re.compile(p) for p in patterns]
    return _COMPILED_PATTERNS


# =============================================================================
# 架空キャラクター検出用データ
# =============================================================================

# RCA-20260130: 独自のセット定義を削除し、共通モジュールを使用
# src/utils/fictional_characters.py の ALL_FICTIONAL_CHARACTERS をインポート済み
# これにより、キャラクターリストの単一ソース化を実現


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class MetaViolation:
    """メタ要素違反情報"""

    episode_id: str
    person_name: str
    age: int
    category: str  # 違反カテゴリ
    pattern_name: str  # 違反パターン名
    matched_text: str  # マッチした箇所
    field: str  # 検出フィールド（episode_content or title_jp）
    context: str  # 前後のコンテキスト


@dataclass
class DetectionResult:
    """検出結果"""

    total_checked: int = 0
    violations: list[MetaViolation] = field(default_factory=list)
    by_category: dict[str, int] = field(default_factory=dict)
    by_person: dict[str, int] = field(default_factory=dict)


# =============================================================================
# 検出クラス
# =============================================================================


class MetaElementViolationDetector:
    """
    メタ要素違反検出器

    FICTIONALエピソードからメタ的表現を検出する。
    """

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None
        self.patterns = get_compiled_patterns()
        # 作品時代設定マスター読み込み
        self.work_settings = self._load_work_settings()

    def _load_work_settings(self) -> dict[str, dict]:
        """作品時代設定マスターを読み込む"""
        settings_path = PROJECT_ROOT / "preserved/data/fictional_work_settings_master.json"
        if not settings_path.exists():
            logger.warning(f"作品設定マスターが見つかりません: {settings_path}")
            return {}
        import json

        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        # work_title と variants の両方からルックアップできるようにする
        lookup: dict[str, dict] = {}
        for work_name, settings in data.get("works", {}).items():
            lookup[work_name] = settings
            for variant in settings.get("work_title_variants", []):
                lookup[variant] = settings
        return lookup

    def _check_year_violation(
        self,
        text: str,
        episode_id: str,
        person_name: str,
        age: int,
        work_title: str,
    ) -> list[MetaViolation]:
        """作品時代設定に基づく年号違反チェック"""
        violations: list[MetaViolation] = []

        # work_titleから作品設定を取得
        settings = self.work_settings.get(work_title)
        if not settings:
            # work_titleで見つからない場合、部分一致を試みる
            for key, val in self.work_settings.items():
                if key in work_title or work_title in key:
                    settings = val
                    break

        if not settings:
            # 設定が見つからない場合はスキップ（他のパターンマッチに委ねる）
            return violations
        else:
            forbidden_patterns = settings.get("forbidden_year_patterns", [])
            if not forbidden_patterns:
                # 年号制限なし（ハリポタ、ジョジョ等の西暦世界）
                return violations
            forbidden_ranges = []
            for pat in forbidden_patterns:
                if "-" in pat and pat[0].isdigit():
                    parts = pat.split("-")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        forbidden_ranges.append((int(parts[0]), int(parts[1])))
                # 文字列パターン（「西暦」「大正」等）は別途チェック

        # 西暦年号の検出
        year_pattern = re.compile(r"((?:19|20)\d{2})年")
        for match in year_pattern.finditer(text):
            year = int(match.group(1))
            for start, end in forbidden_ranges:
                if start <= year <= end:
                    violations.append(
                        MetaViolation(
                            episode_id=episode_id,
                            person_name=person_name,
                            age=age,
                            category="年号違反",
                            pattern_name=f"forbidden_year:{start}-{end}",
                            matched_text=match.group(),
                            field="episode_text",
                            context=self.get_context(text, match),
                        )
                    )
                    break  # 一つのmatchに対して一度だけ違反報告

        # 文字列パターンチェック（「西暦」「大正」等）
        if settings:
            for pat in settings.get("forbidden_year_patterns", []):
                if not pat[0].isdigit():
                    # 文字列パターン
                    str_match = re.search(pat, text)
                    if str_match:
                        violations.append(
                            MetaViolation(
                                episode_id=episode_id,
                                person_name=person_name,
                                age=age,
                                category="年号違反",
                                pattern_name=f"forbidden_keyword:{pat}",
                                matched_text=str_match.group(),
                                field="episode_text",
                                context=self.get_context(text, str_match),
                            )
                        )

        return violations

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                logger.info(f"マスターCSV読み込み: {self.master_csv}")
                # RCA-20260123: CSV読み込みエラーハンドリング追加
                try:
                    self._master_df = pd.read_csv(
                        self.master_csv,
                        encoding="utf-8-sig",
                        low_memory=False,
                    )
                except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
                    logger.error(f"CSV解析エラー: {e}")
                    self._master_df = pd.DataFrame()
                # RCA-20260123 Phase7: 予期しないエラーは上位へ伝播（MemoryError, UnicodeDecodeError等を握りつぶさない）
            else:
                logger.error(f"マスターCSVが見つかりません: {self.master_csv}")
                self._master_df = pd.DataFrame()
        return self._master_df

    def is_fictional_character(self, person_name: str) -> bool:
        """
        人物名が架空キャラクターかどうかを判定

        Args:
            person_name: 人物名

        Returns:
            架空キャラクターならTrue
        """
        return person_name in ALL_FICTIONAL_CHARACTERS

    def get_context(self, text: str, match: re.Match, context_len: int = 30) -> str:
        """
        マッチ箇所の前後コンテキストを取得

        Args:
            text: 全文
            match: マッチオブジェクト
            context_len: 前後の文字数

        Returns:
            コンテキスト付きテキスト
        """
        start = max(0, match.start() - context_len)
        end = min(len(text), match.end() + context_len)

        context = text[start:end]
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        return context

    def check_text(
        self,
        text: str,
        episode_id: str,
        person_name: str,
        age: int,
        field_name: str,
    ) -> list[MetaViolation]:
        """
        テキストをチェックしてメタ要素違反を検出

        Args:
            text: チェック対象テキスト
            episode_id: エピソードID
            person_name: 人物名
            age: 年齢
            field_name: フィールド名

        Returns:
            検出された違反のリスト
        """
        violations: list[MetaViolation] = []

        if not text:
            return violations

        for category, compiled_patterns in self.patterns.items():
            for i, pattern in enumerate(compiled_patterns):
                matches = list(pattern.finditer(text))
                for match in matches:
                    violations.append(
                        MetaViolation(
                            episode_id=episode_id,
                            person_name=person_name,
                            age=age,
                            category=category,
                            pattern_name=META_PATTERNS[category][i],
                            matched_text=match.group(),
                            field=field_name,
                            context=self.get_context(text, match),
                        )
                    )

        return violations

    def check_episode(self, row: dict) -> list[MetaViolation]:
        """
        単一エピソードをチェック

        Args:
            row: エピソードデータ

        Returns:
            検出された違反のリスト
        """
        violations: list[MetaViolation] = []

        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()
        # age が "ageless" などの非数値の場合は0として扱う
        raw_age = row.get("age", 0)
        try:
            age = int(raw_age) if raw_age and str(raw_age).isdigit() else 0
        except (ValueError, TypeError):
            age = 0

        # FICTIONALまたは架空キャラ名の場合のみ対象
        is_fictional = "FICTIONAL" in person_type or self.is_fictional_character(person_name)
        if not is_fictional:
            return violations

        # episode_text をチェック（メインのエピソード内容）
        episode_text = str(row.get("episode_text", ""))
        if episode_text and episode_text != "nan":
            violations.extend(self.check_text(episode_text, episode_id, person_name, age, "episode_text"))

        # work_title をチェック（作品タイトル - 通常は問題ないが念のため）
        # ※ 通常はスキップ。必要に応じてコメントアウトを解除
        # work_title = str(row.get("work_title", ""))
        # if work_title and work_title != "nan":
        #     violations.extend(
        #         self.check_text(work_title, episode_id, person_name, age, "work_title")
        #     )

        # 年号違反チェック（作品時代設定に基づく）
        work_title = str(row.get("work_title", ""))
        if episode_text and episode_text != "nan" and work_title and work_title != "nan":
            violations.extend(self._check_year_violation(episode_text, episode_id, person_name, age, work_title))

        return violations

    def scan_all(self, limit: int = 0) -> DetectionResult:
        """
        全エピソードをスキャン

        Args:
            limit: 処理件数上限（0=無制限）

        Returns:
            検出結果
        """
        result = DetectionResult()

        if self.master_df.empty:
            logger.error("マスターデータが空です")
            return result

        # FICTIONALまたは架空キャラ名のエピソードをフィルタ
        df = self.master_df.copy()

        # person_typeがFICTIONALのものを抽出
        fictional_mask = df["person_type"].str.upper().str.contains("FICTIONAL", na=False)

        # 架空キャラ名のものも追加（person_type誤分類対応）
        char_mask = df["person_name"].isin(list(ALL_FICTIONAL_CHARACTERS))

        df = df[fictional_mask | char_mask]
        result.total_checked = len(df)

        logger.info(f"検証対象: {result.total_checked}件のエピソード")

        processed = 0
        for _, row in df.iterrows():
            violations = self.check_episode(row.to_dict())

            for v in violations:
                result.violations.append(v)

                # カテゴリ別集計
                result.by_category[v.category] = result.by_category.get(v.category, 0) + 1

                # 人物別集計
                result.by_person[v.person_name] = result.by_person.get(v.person_name, 0) + 1

            processed += 1
            if limit > 0 and processed >= limit:
                logger.info(f"処理件数上限 {limit} に達しました")
                break

            # 進捗表示
            if processed % 1000 == 0:
                logger.info(f"処理中: {processed}/{result.total_checked}")

        return result


# =============================================================================
# 修正クラス
# =============================================================================


class MetaViolationFixer:
    """
    メタ要素違反エピソードの修正器

    LLMを使用してメタ要素を含むエピソードを再生成する。
    """

    # 架空キャラクター用再生成プロンプト
    REGENERATE_PROMPT = """あなたは{work_title}の世界観を深く理解するストーリーテラーです。

{person_name}（{work_title}のキャラクター）が{age}歳の時点での作品内エピソードを生成してください。

【絶対遵守ルール】
1. すべての文を丁寧語（です・ます調）で終えてください
2. 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}は」で開始してください
3. 物語の「中」で起きた出来事のみを書く（作品内の冒険、戦い、成長等）

【禁止（メタ要素）】
- 現実の年号＋作品タイトル（例: 「1979年の『機動戦士ガンダム』」）
- シリーズ・続編・劇場版への言及
- アニメ化、放送開始、興行収入、視聴率、連載開始、原作、声優
- 「読者」「視聴者」「ファン」「社会現象」など作品外の視点
- 販売本数、興行成績、受賞歴、ランキング
- 「不朽の」「伝説の」「金字塔」など現実世界での評価表現
- ディズニーランド、テーマパーク、グッズ、DVD売上
- 「架空のキャラクター」「実在しない」「設定上は」

【品質基準】
- 固有名詞を5つ以上含める
- 300〜400文字で完結
- 作品世界内の視点で臨場感を持って描写

【現在の問題テキスト（参考）】
以下のテキストにメタ要素「{violation_summary}」が含まれていました。
同じキャラクター・年齢で、メタ要素を一切含まない新しいエピソードを生成してください。
"""

    # 作品名マッピング（フォールバック用）
    WORK_TITLE_MAP: dict[str, str] = {
        "孫悟空": "ドラゴンボール",
        "孫悟飯": "ドラゴンボール",
        "ベジータ": "ドラゴンボール",
        "フリーザ": "ドラゴンボール",
        "クリリン": "ドラゴンボール",
        "モンキー・D・ルフィ": "ONE PIECE",
        "ロロノア・ゾロ": "ONE PIECE",
        "うずまきナルト": "NARUTO",
        "うちはサスケ": "NARUTO",
        "竈門炭治郎": "鬼滅の刃",
        "竈門禰豆子": "鬼滅の刃",
        "エレン・イェーガー": "進撃の巨人",
        "江戸川コナン": "名探偵コナン",
        "空条承太郎": "ジョジョの奇妙な冒険",
        "緑谷出久": "僕のヒーローアカデミア",
        "碇シンジ": "新世紀エヴァンゲリオン",
        "坂田銀時": "銀魂",
        "虎杖悠仁": "呪術廻戦",
        "マリオ": "スーパーマリオ",
        "ピカチュウ": "ポケットモンスター",
        "セフィロス": "ファイナルファンタジーVII",
        "クラウド・ストライフ": "ファイナルファンタジーVII",
        "ミッキーマウス": "ディズニー",
        "ルーク・スカイウォーカー": "スター・ウォーズ",
        "ダース・ベイダー": "スター・ウォーズ",
        "ハリー・ポッター": "ハリー・ポッター",
        "シャア・アズナブル": "機動戦士ガンダム",
        "アムロ・レイ": "機動戦士ガンダム",
    }

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Anthropic クライアントの遅延初期化"""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic()
            except ImportError:
                logger.error("anthropicライブラリがインストールされていません: pip install anthropic")
                raise
        return self._client

    def get_work_title(self, person_name: str, work_title: str) -> str:
        """作品名を取得（空の場合はマッピングから）"""
        if work_title and str(work_title) != "nan":
            return str(work_title)
        return self.WORK_TITLE_MAP.get(person_name, "作品")

    def regenerate_episode(
        self,
        person_name: str,
        age: int,
        work_title: str,
        violation_summary: str,
        max_retries: int = 3,
    ) -> tuple[Optional[str], bool]:
        """
        メタ要素フリーのエピソードをLLMで再生成

        Args:
            person_name: キャラクター名
            age: 年齢
            work_title: 作品名
            violation_summary: 違反内容の要約
            max_retries: リトライ回数

        Returns:
            (新エピソード, 成功フラグ)
        """
        work = self.get_work_title(person_name, work_title)
        prompt = self.REGENERATE_PROMPT.format(
            person_name=person_name,
            age=int(age),
            work_title=work,
            violation_summary=violation_summary,
        )

        detector = MetaElementViolationDetector.__new__(MetaElementViolationDetector)
        detector.patterns = get_compiled_patterns()

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                block = response.content[0]
                episode_text = block.text.strip() if hasattr(block, "text") else str(block)

                # 再生成テキストのメタ要素チェック
                violations = detector.check_text(episode_text, "REGEN", person_name, int(age), "episode_text")
                if not violations:
                    return episode_text, True

                logger.warning(
                    f"  リトライ {attempt + 1}/{max_retries}: " f"再生成テキストにもメタ要素あり ({len(violations)}件)"
                )
            except Exception as e:
                logger.error(f"  LLMエラー (attempt {attempt + 1}): {e}")
                return None, False

        return None, False

    def fix_violations(
        self,
        result: DetectionResult,
        dry_run: bool = True,
        delete_only: bool = False,
        batch_size: int = 10,
    ) -> dict:
        """
        検出された違反エピソードを修正

        Args:
            result: 検出結果
            dry_run: ドライラン
            delete_only: 削除のみ（再生成なし）
            batch_size: バッチサイズ

        Returns:
            修正結果
        """
        if not result.violations:
            logger.info("修正対象の違反はありません")
            return {"regenerated": 0, "deleted": 0, "failed": 0, "skipped": 0}

        # episode_id単位で違反をグループ化
        violations_by_episode: dict[str, list[MetaViolation]] = {}
        for v in result.violations:
            if v.episode_id not in violations_by_episode:
                violations_by_episode[v.episode_id] = []
            violations_by_episode[v.episode_id].append(v)

        total_episodes = len(violations_by_episode)
        logger.info(f"修正対象: {total_episodes}件のエピソード（違反合計: {len(result.violations)}件）")

        if dry_run:
            logger.info("ドライラン: 実際の修正は行いません")
            logger.info("")
            for ep_id, violations in list(violations_by_episode.items())[:20]:
                v0 = violations[0]
                categories = set(v.category for v in violations)
                logger.info(
                    f"  [{ep_id}] {v0.person_name} ({v0.age}歳) - " f"違反{len(violations)}件: {', '.join(categories)}"
                )
            if total_episodes > 20:
                logger.info(f"  ... 他 {total_episodes - 20}件")
            return {
                "regenerated": 0,
                "deleted": 0,
                "failed": 0,
                "skipped": 0,
                "total_target": total_episodes,
            }

        # マスターCSV読み込み
        df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)

        # バックアップ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.master_csv.parent / f"MASTER_EPISODES_BACKUP_meta_fix_{timestamp}.csv"
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ作成: {backup_path}")

        stats = {"regenerated": 0, "deleted": 0, "failed": 0, "skipped": 0}
        processed = 0

        for ep_id, violations in violations_by_episode.items():
            if processed >= batch_size:
                logger.info(f"バッチサイズ上限 ({batch_size}) に到達。残りは次回実行で処理")
                stats["skipped"] = total_episodes - processed
                break

            v0 = violations[0]
            categories = [v.category for v in violations]
            violation_summary = ", ".join(set(categories))

            logger.info(
                f"[{processed + 1}/{min(batch_size, total_episodes)}] "
                f"{v0.person_name} ({v0.age}歳) - {violation_summary}"
            )

            mask = df["episode_id"].astype(str) == str(ep_id)
            if not mask.any():
                logger.warning(f"  episode_id={ep_id} がCSVに見つかりません")
                stats["failed"] += 1
                processed += 1
                continue

            row = df.loc[mask].iloc[0]

            if delete_only:
                df = df[~mask]
                logger.info("  削除しました")
                stats["deleted"] += 1
            else:
                work_title = str(row.get("work_title", ""))
                new_text, success = self.regenerate_episode(
                    person_name=v0.person_name,
                    age=v0.age,
                    work_title=work_title,
                    violation_summary=violation_summary,
                )

                if success:
                    df.loc[mask, "episode_text"] = new_text
                    df.loc[mask, "fact_check_result"] = "EPUP_META_FIX_REGENERATED"
                    logger.info(f"  再生成成功: {new_text[:80]}...")
                    stats["regenerated"] += 1
                else:
                    # 再生成失敗時は削除
                    df = df[~mask]
                    logger.warning("  再生成失敗 → 削除しました")
                    stats["deleted"] += 1

            processed += 1

        # CSV保存
        df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")
        logger.info(f"CSV保存完了: {self.master_csv}")

        # 結果サマリー
        logger.info("")
        logger.info("=" * 50)
        logger.info("修正結果サマリー")
        logger.info("=" * 50)
        logger.info(f"  再生成成功: {stats['regenerated']}件")
        logger.info(f"  削除: {stats['deleted']}件")
        logger.info(f"  失敗: {stats['failed']}件")
        logger.info(f"  スキップ（次回）: {stats['skipped']}件")
        logger.info(f"  バックアップ: {backup_path}")

        return stats


# =============================================================================
# レポート生成
# =============================================================================


def generate_report(result: DetectionResult) -> str:
    """
    検出レポートを生成

    Args:
        result: 検出結果

    Returns:
        レポート文字列
    """
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("=== メタ要素違反検出レポート ===")
    lines.append("=" * 70)
    lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"対象エピソード数: {result.total_checked}件")
    lines.append(f"違反検出数: {len(result.violations)}件")
    lines.append("")

    # カテゴリ別サマリー
    if result.by_category:
        lines.append("-" * 70)
        lines.append("カテゴリ別違反数:")
        lines.append("-" * 70)
        for category, count in sorted(result.by_category.items(), key=lambda x: -x[1]):
            lines.append(f"  {category}: {count}件")
        lines.append("")

    # 人物別サマリー（上位10件）
    if result.by_person:
        lines.append("-" * 70)
        lines.append("人物別違反数（上位10件）:")
        lines.append("-" * 70)
        sorted_persons = sorted(result.by_person.items(), key=lambda x: -x[1])
        for person, count in sorted_persons[:10]:
            lines.append(f"  {person}: {count}件")
        lines.append("")

    # 違反詳細
    if result.violations:
        lines.append("=" * 70)
        lines.append("違反詳細:")
        lines.append("=" * 70)

        for i, v in enumerate(result.violations, 1):
            lines.append("")
            lines.append(f"[違反{i}]")
            lines.append(f"episode_id: {v.episode_id}")
            lines.append(f"person_name: {v.person_name}")
            lines.append(f"age: {v.age}")
            lines.append(f"違反カテゴリ: {v.category}")
            lines.append(f"違反パターン: {v.pattern_name}")
            lines.append(f"検出フィールド: {v.field}")
            lines.append(f'該当箇所: "{v.matched_text}"')
            lines.append(f"コンテキスト: {v.context}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("[完了]")

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="EPUP: メタ要素違反検出スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（検出のみ）
  python scripts/validation/detect_meta_element_violations.py --dry-run

  # レポート出力
  python scripts/validation/detect_meta_element_violations.py --output report.txt

  # 処理件数上限
  python scripts/validation/detect_meta_element_violations.py --limit 100

  # 違反エピソードをLLMで再生成して修正
  python scripts/validation/detect_meta_element_violations.py --fix

  # 違反エピソードを削除（再生成なし）
  python scripts/validation/detect_meta_element_violations.py --delete-only

  # バッチサイズ指定（デフォルト10件ずつ）
  python scripts/validation/detect_meta_element_violations.py --fix --batch-size 20
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="検出のみ（修正しない）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="レポート出力先（デフォルト: stdout）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="処理件数上限（0=無制限）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログ出力",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="違反エピソードをLLMで再生成して修正（デフォルト: ドライラン）",
    )
    parser.add_argument(
        "--delete-only",
        action="store_true",
        help="再生成せず違反エピソードを削除する",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="一度に修正するエピソード数（デフォルト: 10）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="違反があればexit(1)で終了（CI/pre-commit用）",
    )

    args = parser.parse_args()

    # ログレベル設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ヘッダー表示
    logger.info("=" * 70)
    logger.info("EPUP: メタ要素違反検出スクリプト")
    logger.info(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # 検出器初期化
    detector = MetaElementViolationDetector()

    if detector.master_df.empty:
        logger.error(f"マスターCSVが見つかりません: {detector.master_csv}")
        return 2

    logger.info(f"マスターCSV: {detector.master_csv}")
    logger.info(f"総エピソード数: {len(detector.master_df):,}")

    # スキャン実行
    logger.info("")
    logger.info("スキャン開始...")
    result = detector.scan_all(limit=args.limit)

    # レポート生成
    report = generate_report(result)

    # 出力
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"レポート保存: {output_path}")
    else:
        print(report)

    # 結果サマリー
    logger.info("")
    logger.info(f"検証完了: {result.total_checked}件チェック, {len(result.violations)}件違反検出")

    # --fix または --delete-only の場合は修正実行
    if (args.fix or args.delete_only) and result.violations:
        logger.info("")
        logger.info("=" * 70)
        logger.info("メタ要素違反 修正処理")
        logger.info("=" * 70)

        fixer = MetaViolationFixer()
        fix_result = fixer.fix_violations(
            result=result,
            dry_run=False,
            delete_only=args.delete_only,
            batch_size=args.batch_size,
        )
        return 0 if fix_result.get("failed", 0) == 0 else 1

    # 終了コード（違反があれば1）
    if args.strict and args.dry_run and len(result.violations) > 0:
        logger.error(f"STRICT MODE: 違反 {len(result.violations)} 件検出 - exit(1)")
    return 0 if len(result.violations) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
