#!/usr/bin/env python3
"""
EPUP: Person Type ミスマッチ検出スクリプト

架空キャラクターなのに person_type = "REAL" に誤分類されているエピソードを検出する。

検出ロジック:
1. MASTER_EPISODES_CURRENT.csv を読み込む
2. 架空キャラクターリスト（ドラゴンボール、ポケモン、マリオ等）と照合
3. person_name が架空キャラなのに person_type = "REAL" のエピソードを検出
4. 年号パターン（1900-2026年）を含むエピソードも補助的に検出

使用方法:
    # 全件スキャン
    python scripts/validation/detect_person_type_mismatch.py

    # 詳細出力
    python scripts/validation/detect_person_type_mismatch.py --verbose

    # JSON出力
    python scripts/validation/detect_person_type_mismatch.py --output report.json

    # CI用（違反があればexit 1）
    python scripts/validation/detect_person_type_mismatch.py --strict

Author: EPUP Validation Team
Date: 2026-01-22
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
SETTINGS_MASTER = PROJECT_ROOT / "preserved/data/fictional_work_settings_master.json"
REPORT_DIR = PROJECT_ROOT / "src/reports"


# =============================================================================
# 架空キャラクターデータベース
# =============================================================================

# 作品別架空キャラクターリスト（完全一致用）
# 各作品の主要キャラクターを網羅（フルネーム形式を優先）
FICTIONAL_CHARACTERS: dict[str, list[str]] = {
    "ドラゴンボール": [
        # 主要キャラクター（フルネーム）
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
        "餃子",
        "亀仙人",
        "ブルマ",
        "チチ",
        "ビーデル",
        "人造人間18号",
        "人造人間17号",
        "ブロリー",
        "ビルス",
        "ウイス",
        "ゴクウブラック",
        "ザマス",
    ],
    "ポケモン": [
        # 人間キャラクター
        "サトシ",
        "カスミ",
        "タケシ",
        "ムサシ",
        "コジロウ",
        "ニャース",
        "シゲル",
        "ヒカリ",
        "セレナ",
        # ポケモンは除外（共通名が多い）
        "ピカチュウ",
    ],
    "マリオ": [
        "マリオ",
        "ルイージ",
        "ピーチ姫",
        "クッパ",
        "キノピオ",
        "ヨッシー",
        "ワリオ",
        "ワルイージ",
        "ロゼッタ",
        "デイジー姫",
    ],
    "ONE PIECE": [
        # 麦わらの一味（フルネーム優先）
        "モンキー・D・ルフィ",
        "ロロノア・ゾロ",
        "ウソップ",
        "サンジ",
        "トニートニー・チョッパー",
        "ニコ・ロビン",
        "フランキー",
        "ブルック",
        "ジンベエ",
        # 四皇・海賊（フルネーム優先）
        "シャンクス",
        "エドワード・ニューゲート",
        "カイドウ",
        "シャーロット・リンリン",
        "マーシャル・D・ティーチ",
        # 海軍
        "スモーカー",
        "コビー",
        # その他
        "ポートガス・D・エース",
        "モンキー・D・ドラゴン",
        "トラファルガー・ロー",
    ],
    "NARUTO": [
        # 第七班（フルネーム）
        "うずまきナルト",
        "うちはサスケ",
        "春野サクラ",
        "はたけカカシ",
        # 他の班（フルネーム）
        "日向ヒナタ",
        "奈良シカマル",
        "秋道チョウジ",
        "山中いの",
        "犬塚キバ",
        "油女シノ",
        "日向ネジ",
        "ロック・リー",
        "テンテン",
        "我愛羅",
        # 暁（フルネーム優先）
        "うちはイタチ",
        "干柿鬼鮫",
        "デイダラ",
        "サソリ",
        "飛段",
        "角都",
        "うちはオビト",
        "うちはマダラ",
        # 歴代火影
        "千手柱間",
        "千手扉間",
        "猿飛ヒルゼン",
        "波風ミナト",
        "綱手",
        # BORUTO
        "うずまきボルト",
        "うちはサラダ",
    ],
    "鬼滅の刃": [
        # 主要キャラクター（フルネーム）
        "竈門炭治郎",
        "竈門禰豆子",
        "我妻善逸",
        "嘴平伊之助",
        # 柱（フルネーム）
        "冨岡義勇",
        "胡蝶しのぶ",
        "煉獄杏寿郎",
        "宇髄天元",
        "甘露寺蜜璃",
        "時透無一郎",
        "伊黒小芭内",
        "不死川実弥",
        "悲鳴嶼行冥",
        # その他
        "栗花落カナヲ",
        "鬼舞辻無惨",
        "産屋敷耀哉",
    ],
    "進撃の巨人": [
        "エレン・イェーガー",
        "ミカサ・アッカーマン",
        "アルミン・アルレルト",
        "リヴァイ・アッカーマン",
        "エルヴィン・スミス",
        "ハンジ・ゾエ",
        "ジャン・キルシュタイン",
        "コニー・スプリンガー",
        "サシャ・ブラウス",
        "ヒストリア・レイス",
        "ライナー・ブラウン",
        "ベルトルト・フーバー",
        "アニ・レオンハート",
        "ジーク・イェーガー",
    ],
    "呪術廻戦": [
        "虎杖悠仁",
        "伏黒恵",
        "釘崎野薔薇",
        "五条悟",
        "夏油傑",
        "両面宿儺",
        "乙骨憂太",
        "狗巻棘",
        "パンダ",
        "禪院真希",
        "東堂葵",
        "七海建人",
    ],
    "BLEACH": [
        "黒崎一護",
        "朽木ルキア",
        "井上織姫",
        "石田雨竜",
        "茶渡泰虎",
        "朽木白哉",
        "日番谷冬獅郎",
        "更木剣八",
        "涅マユリ",
        "藍染惣右介",
        "市丸ギン",
        "浦原喜助",
        "四楓院夜一",
    ],
    "ハリー・ポッター": [
        "ハリー・ポッター",
        "ロン・ウィーズリー",
        "ハーマイオニー・グレンジャー",
        "アルバス・ダンブルドア",
        "セブルス・スネイプ",
        "ヴォルデモート",
        "トム・リドル",
        "ドラコ・マルフォイ",
        "シリウス・ブラック",
        "リーマス・ルーピン",
        "ネビル・ロングボトム",
        "ルビウス・ハグリッド",
        "ジニー・ウィーズリー",
    ],
    "ジョジョの奇妙な冒険": [
        "ジョナサン・ジョースター",
        "ジョセフ・ジョースター",
        "空条承太郎",
        "東方仗助",
        "ジョルノ・ジョバァーナ",
        "空条徐倫",
        "ディオ・ブランドー",
        "吉良吉影",
        "ブローノ・ブチャラティ",
        "グイード・ミスタ",
    ],
    "名探偵コナン": [
        "江戸川コナン",
        "工藤新一",
        "毛利蘭",
        "毛利小五郎",
        "灰原哀",
        "服部平次",
        "怪盗キッド",
        "黒羽快斗",
        "赤井秀一",
        "沖矢昴",
        "安室透",
        "降谷零",
    ],
    "銀魂": [
        "坂田銀時",
        "志村新八",
        "神楽",
        "高杉晋助",
        "桂小太郎",
        "坂本辰馬",
        "沖田総悟",
        "土方十四郎",
        "近藤勲",
    ],
    "僕のヒーローアカデミア": [
        "緑谷出久",
        "爆豪勝己",
        "麗日お茶子",
        "飯田天哉",
        "轟焦凍",
        "オールマイト",
        "相澤消太",
        "死柄木弔",
        "オールフォーワン",
    ],
    "新世紀エヴァンゲリオン": [
        "碇シンジ",
        "綾波レイ",
        "惣流・アスカ・ラングレー",
        "式波・アスカ・ラングレー",
        "碇ゲンドウ",
        "葛城ミサト",
        "赤木リツコ",
        "渚カヲル",
        "加持リョウジ",
    ],
    "聖闘士星矢": [
        "ペガサス星矢",
        "ドラゴン紫龍",
        "キグナス氷河",
        "アンドロメダ瞬",
        "フェニックス一輝",
        "城戸沙織",
    ],
    "るろうに剣心": [
        "緋村剣心",
        "神谷薫",
        "明神弥彦",
        "相楽左之助",
        "斎藤一",
        "四乃森蒼紫",
        "巻町操",
        "志々雄真実",
    ],
    "ディズニープリンセス": [
        # プリンセス系のみ（共通名を避ける）
        "白雪姫",
        "シンデレラ",
        "オーロラ姫",
        "アリエル",
        "ベル",
        "ポカホンタス",
        "ムーラン",
        "ティアナ",
        "ラプンツェル",
        "メリダ",
        "モアナ",
        "エルサ",
        # ミッキー関連
        "ミッキーマウス",
        "ミニーマウス",
        "ドナルドダック",
        "グーフィー",
        "プルート",
    ],
    "スター・ウォーズ": [
        "ルーク・スカイウォーカー",
        "ダース・ベイダー",
        "アナキン・スカイウォーカー",
        "レイア・オーガナ",
        "ハン・ソロ",
        "チューバッカ",
        "オビ＝ワン・ケノービ",
        "ヨーダ",
        "パルパティーン",
        "ダース・シディアス",
        "カイロ・レン",
        "ベン・ソロ",
    ],
}

# 架空キャラクター名のセット（完全一致用）
ALL_FICTIONAL_CHARACTERS: set[str] = set()
for characters in FICTIONAL_CHARACTERS.values():
    ALL_FICTIONAL_CHARACTERS.update(characters)

# 短すぎる名前や一般的すぎる名前のブラックリスト（誤検出防止）
BLACKLIST_NAMES = {
    # 一般的な名前
    "ナミ",
    "ルフィ",
    "ゾロ",
    "サンジ",  # 愛称は除外
    "サクラ",
    "ヒナタ",
    "ナルト",
    "サスケ",  # 愛称は除外
    "アナ",
    "エルサ",  # 一般名と混同しやすい
    "リヴァイ",
    "エレン",
    "ミカサ",
    "アルミン",
    "ジャン",
    "コニー",
    "サシャ",  # 愛称は除外
    "炭治郎",
    "禰豆子",
    "善逸",
    "伊之助",  # 愛称は除外
    "レイ",
    "シンジ",
    "アスカ",  # 愛称は除外
    "星矢",
    "紫龍",
    "氷河",
    "瞬",
    "一輝",  # 愛称は除外
    "剣心",
    "薫",  # 愛称は除外
    "悠仁",
    "恵",  # 愛称は除外
    "一護",
    "ルキア",  # 愛称は除外
    "ハリー",
    "ロン",  # 一般名と混同しやすい
    "ハグリッド",  # 一般名と混同しやすい
    "デク",  # 愛称は除外
    "マリオ",  # 一般名と混同しやすい
    "ルイージ",  # 一般名と混同しやすい
    "チャド",  # 一般名と混同しやすい
    "ロビン",  # 一般名と混同しやすい
    "ドナルド",  # 一般名と混同しやすい
    "ジャスミン",  # 一般名と混同しやすい
}


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class MismatchRecord:
    """ミスマッチ記録"""

    episode_id: str
    person_id: str
    person_name: str
    current_person_type: str
    expected_person_type: str
    work_title: str
    matched_work: str
    episode_text_snippet: str
    detection_reason: str
    has_modern_year: bool = False
    detected_years: list[int] = field(default_factory=list)


# =============================================================================
# 検出ロジック
# =============================================================================


class PersonTypeMismatchDetector:
    """
    Person Type ミスマッチ検出器

    架空キャラクターなのに REAL に分類されているエピソードを検出する。
    """

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None

        # 年号検出パターン（1900-2026年）
        self.year_pattern = re.compile(r"(19\d{2}|20[0-2]\d)年")

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def detect_fictional_character(self, person_name: str) -> tuple[bool, str]:
        """
        人物名が架空キャラクターかどうかを判定（完全一致のみ）

        Args:
            person_name: 人物名

        Returns:
            (is_fictional, matched_work): 架空キャラクターか、マッチした作品名
        """
        # ブラックリストチェック（一般名との混同防止）
        if person_name in BLACKLIST_NAMES:
            return False, ""

        # 完全一致チェックのみ
        if person_name in ALL_FICTIONAL_CHARACTERS:
            for work, characters in FICTIONAL_CHARACTERS.items():
                if person_name in characters:
                    return True, work

        return False, ""

    def detect_modern_years(self, text: str) -> list[int]:
        """
        テキストから現代年号（1900-2026年）を検出

        Args:
            text: エピソードテキスト

        Returns:
            検出された年号のリスト
        """
        if not isinstance(text, str):
            return []

        matches = self.year_pattern.findall(text)
        return [int(year) for year in matches]

    def scan_episode(self, row: dict) -> Optional[MismatchRecord]:
        """
        単一エピソードをスキャン

        Args:
            row: エピソードデータ

        Returns:
            ミスマッチがあればMismatchRecord、なければNone
        """
        episode_id = str(row.get("episode_id", ""))
        person_id = str(row.get("person_id", ""))
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()
        work_title = str(row.get("work_title", ""))
        episode_text = str(row.get("episode_text", ""))

        # FICTIONALの場合はスキップ（正しい分類）
        if "FICTIONAL" in person_type:
            return None

        # 架空キャラクターかどうかをチェック（完全一致）
        is_fictional, matched_work = self.detect_fictional_character(person_name)

        if not is_fictional:
            return None

        # ミスマッチ検出
        detected_years = self.detect_modern_years(episode_text)
        has_modern_year = len(detected_years) > 0

        # エピソードテキストのスニペット（最初の100文字）
        snippet = episode_text[:100] + "..." if len(episode_text) > 100 else episode_text

        return MismatchRecord(
            episode_id=episode_id,
            person_id=person_id,
            person_name=person_name,
            current_person_type=person_type,
            expected_person_type="FICTIONAL",
            work_title=work_title if work_title and work_title != "nan" else "",
            matched_work=matched_work,
            episode_text_snippet=snippet,
            detection_reason=f"架空キャラクター（{matched_work}）がREALに分類されている",
            has_modern_year=has_modern_year,
            detected_years=detected_years,
        )

    def scan_all(self) -> list[MismatchRecord]:
        """
        全エピソードをスキャン

        Returns:
            ミスマッチレコードのリスト
        """
        if self.master_df.empty:
            return []

        records = []

        for _, row in self.master_df.iterrows():
            record = self.scan_episode(row.to_dict())
            if record:
                records.append(record)

        return records

    def get_summary(self, records: list[MismatchRecord]) -> dict:
        """
        サマリーを生成

        Args:
            records: ミスマッチレコードのリスト

        Returns:
            サマリー辞書
        """
        by_work: dict[str, int] = {}
        by_character: dict[str, int] = {}
        with_modern_year = 0

        for record in records:
            # 作品別
            work = record.matched_work
            by_work[work] = by_work.get(work, 0) + 1

            # キャラクター別
            char = record.person_name
            by_character[char] = by_character.get(char, 0) + 1

            # 現代年号あり
            if record.has_modern_year:
                with_modern_year += 1

        return {
            "total_mismatches": len(records),
            "by_work": dict(sorted(by_work.items(), key=lambda x: -x[1])),
            "by_character": dict(sorted(by_character.items(), key=lambda x: -x[1])),
            "with_modern_year": with_modern_year,
            "unique_characters": len(by_character),
            "unique_works": len(by_work),
        }


# =============================================================================
# CLI
# =============================================================================


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: Person Type ミスマッチ検出")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="JSON出力先",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="ミスマッチがあればexit 1",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="表示する最大件数（デフォルト: 50）",
    )

    args = parser.parse_args()

    # ヘッダー
    print("=" * 70)
    print("EPUP: Person Type ミスマッチ検出")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 検出器初期化
    detector = PersonTypeMismatchDetector()

    if detector.master_df.empty:
        print(f"\nError: Master CSV not found: {detector.master_csv}")
        return 2

    print(f"\nマスターCSV: {detector.master_csv}")
    print(f"総エピソード数: {len(detector.master_df):,}")
    print(f"登録架空キャラクター数: {len(ALL_FICTIONAL_CHARACTERS)}")
    print(f"ブラックリスト（除外名）: {len(BLACKLIST_NAMES)}")

    # スキャン実行
    print("\nスキャン中...")
    records = detector.scan_all()

    # サマリー
    summary = detector.get_summary(records)

    print(f"\n{'=' * 70}")
    print("検出結果サマリー")
    print(f"{'=' * 70}")
    print(f"ミスマッチ総数: {summary['total_mismatches']}件")
    print(f"ユニークキャラクター数: {summary['unique_characters']}人")
    print(f"ユニーク作品数: {summary['unique_works']}作品")
    print(f"現代年号を含むエピソード: {summary['with_modern_year']}件")

    if summary["by_work"]:
        print("\n作品別ミスマッチ数:")
        for work, count in list(summary["by_work"].items())[:10]:
            print(f"  {work}: {count}件")

    if summary["by_character"]:
        print("\nキャラクター別ミスマッチ数（上位10）:")
        for char, count in list(summary["by_character"].items())[:10]:
            print(f"  {char}: {count}件")

    # 詳細出力
    if records:
        limit = args.limit
        print(f"\n{'=' * 70}")
        print(f"詳細（上位{min(limit, len(records))}件）")
        print(f"{'=' * 70}")

        for i, record in enumerate(records[:limit], 1):
            print(f"\n{i}. {record.episode_id}")
            print(f"   人物名: {record.person_name}")
            print(f"   現在の分類: {record.current_person_type}")
            print(f"   期待される分類: {record.expected_person_type}")
            print(f"   マッチした作品: {record.matched_work}")
            print(f"   理由: {record.detection_reason}")

            if args.verbose:
                print(f"   person_id: {record.person_id}")
                print(f"   work_title: {record.work_title}")
                print(f"   テキスト: {record.episode_text_snippet}")

            if record.has_modern_year:
                print(f"   [警告] 現代年号検出: {record.detected_years}")

    # エピソードID一覧
    if records:
        print(f"\n{'=' * 70}")
        print("修正が必要なエピソードID一覧")
        print(f"{'=' * 70}")
        episode_ids = [r.episode_id for r in records]
        print(f"総数: {len(episode_ids)}件")
        print("\nエピソードID:")
        for eid in episode_ids[:100]:  # 最大100件
            print(f"  {eid}")
        if len(episode_ids) > 100:
            print(f"  ... 他 {len(episode_ids) - 100}件")

    # JSON出力
    if args.output:
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "records": [
                {
                    "episode_id": r.episode_id,
                    "person_id": r.person_id,
                    "person_name": r.person_name,
                    "current_person_type": r.current_person_type,
                    "expected_person_type": r.expected_person_type,
                    "work_title": r.work_title,
                    "matched_work": r.matched_work,
                    "detection_reason": r.detection_reason,
                    "has_modern_year": r.has_modern_year,
                    "detected_years": r.detected_years,
                }
                for r in records
            ],
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nJSONレポート保存: {output_path}")

    # 終了コード
    if args.strict and summary["total_mismatches"] > 0:
        print(f"\n[FAILED] {summary['total_mismatches']}件のミスマッチがあります")
        return 1

    if summary["total_mismatches"] == 0:
        print("\n[OK] ミスマッチは検出されませんでした")
    else:
        print(f"\n[WARNING] {summary['total_mismatches']}件のミスマッチを検出しました")

    return 0


if __name__ == "__main__":
    sys.exit(main())
