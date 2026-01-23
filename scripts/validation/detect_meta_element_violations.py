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

import pandas as pd

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

# 主要作品の架空キャラクター名（完全一致用）
FICTIONAL_CHARACTERS: set[str] = {
    # ドラゴンボール
    "孫悟空",
    "孫悟飯",
    "孫悟天",
    "ベジータ",
    "トランクス",
    "フリーザ",
    "セル",
    "魔人ブウ",
    "ピッコロ",
    "クリリン",
    "ヤムチャ",
    "天津飯",
    # ONE PIECE
    "モンキー・D・ルフィ",
    "ロロノア・ゾロ",
    "ウソップ",
    "サンジ",
    "トニートニー・チョッパー",
    "ニコ・ロビン",
    "フランキー",
    "ブルック",
    # NARUTO
    "うずまきナルト",
    "うちはサスケ",
    "春野サクラ",
    "はたけカカシ",
    "日向ヒナタ",
    "奈良シカマル",
    "うちはイタチ",
    "我愛羅",
    # 鬼滅の刃
    "竈門炭治郎",
    "竈門禰豆子",
    "我妻善逸",
    "嘴平伊之助",
    "冨岡義勇",
    "胡蝶しのぶ",
    "煉獄杏寿郎",
    "鬼舞辻無惨",
    # 進撃の巨人
    "エレン・イェーガー",
    "ミカサ・アッカーマン",
    "アルミン・アルレルト",
    "リヴァイ・アッカーマン",
    "エルヴィン・スミス",
    # その他多数...（簡略化）
    "江戸川コナン",
    "工藤新一",
    "毛利蘭",
    "怪盗キッド",
    "黒崎一護",
    "朽木ルキア",
    "藍染惣右介",
    "ハリー・ポッター",
    "ハーマイオニー・グレンジャー",
    "ヴォルデモート",
    "空条承太郎",
    "ディオ・ブランドー",
    "吉良吉影",
    "緑谷出久",
    "爆豪勝己",
    "オールマイト",
    "碇シンジ",
    "綾波レイ",
    "惣流・アスカ・ラングレー",
    "坂田銀時",
    "志村新八",
    "神楽",
    "虎杖悠仁",
    "伏黒恵",
    "五条悟",
    "マリオ",
    "ルイージ",
    "ピーチ姫",
    "クッパ",
    "ピカチュウ",
    "サトシ",
    "セフィロス",
    "クラウド・ストライフ",
    "ミッキーマウス",
    "ドナルドダック",
    "ルーク・スカイウォーカー",
    "ダース・ベイダー",
}


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
                except Exception as e:
                    logger.error(f"予期しないCSV読み込みエラー: {e}")
                    self._master_df = pd.DataFrame()
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
        return person_name in FICTIONAL_CHARACTERS

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
        age = int(row.get("age", 0)) if row.get("age") else 0

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
        char_mask = df["person_name"].isin(list(FICTIONAL_CHARACTERS))

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

    # 終了コード（違反があれば1）
    return 0 if len(result.violations) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
