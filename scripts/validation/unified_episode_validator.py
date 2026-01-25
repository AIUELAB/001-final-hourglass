#!/usr/bin/env python3
"""
EPUP: 統合エピソード検証スクリプト

MASTER_EPISODES_CURRENT.csvの全件を検証し、person_type（REAL/FICTIONAL）で
検証ルールを分岐させる。

## 機能
1. FICTIONAL向け検証
   - メタ情報混入検出（「架空の」「実在しない」「設定上」「原作では」「声優」「キャスト」「演じ」）
   - LLM創作（カノン逸脱）検出
     - 実在機関言及（NHK, 東京大学, NASA等）
     - 現代年号（1900-2026年）を架空世界作品で使用
   - 年齢境界（作中設定）チェック

2. REAL向け検証
   - 生年/没年×年齢整合チェック
     - age > (death_year - birth_year) 違反
     - age > (current_year - birth_year) 違反
     - birth_year > death_year 違反
   - 断定口調の根拠不明主張検出

## 使用方法
    python scripts/validation/unified_episode_validator.py --dry-run
    python scripts/validation/unified_episode_validator.py --fix
    python scripts/validation/unified_episode_validator.py --verify
    python scripts/validation/unified_episode_validator.py --report

Author: EPUP Validation Team
Date: 2026-01-17
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import logging
import pandas as pd

# ロガー設定
logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"


# =============================================================================
# 検証設定（フラグ）
# =============================================================================

# UNVERIFIED_CLAIM検出: False = 無効（適切なヘッジ表現は許容）
# 「〜とされる」「〜と言われている」「諸説あり」等のヘッジ表現は、
# 主観的評価や歴史的推計の適切な表現であり、
# 削除すると根拠なき断定になるため、デフォルトで無効化
# 対象パターン詳細: UNVERIFIED_CLAIM_PATTERNS を参照
ENABLE_UNVERIFIED_CLAIM_CHECK = False


# =============================================================================
# 違反タイプ定義（unified_gate.pyから共通インポート）
# =============================================================================

# ViolationTypeはunified_gate.pyで統一定義
# 名前衝突を防ぎ、csv_writer.pyとの整合性を確保
from scripts.sage.persistence.unified_gate import ViolationType


class Severity(Enum):
    """重大度"""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# =============================================================================
# 検出パターン定義
# =============================================================================


# FICTIONAL向け: メタ情報混入パターン
META_INFO_PATTERNS = [
    (r"架空の", "「架空の」表現"),
    (r"実在しない", "「実在しない」表現"),
    (r"設定上", "「設定上」表現"),
    (r"原作では", "「原作では」表現"),
    (r"声優", "声優への言及"),
    (r"キャスト", "キャストへの言及"),
    (r"演じ(?:る|た|ている)", "演じる表現"),
    (r"作者", "作者への言及"),
    (r"連載", "連載への言及"),
    (r"アニメ化", "アニメ化への言及"),
    (r"映画化", "映画化への言及"),
    (r"(?:単行本|コミックス)", "出版形態への言及"),
]

# FICTIONAL向け: 実在機関パターン
REAL_INSTITUTIONS = [
    # 日本の大学
    "東京大学",
    "京都大学",
    "大阪大学",
    "名古屋大学",
    "北海道大学",
    "九州大学",
    "早稲田大学",
    "慶應義塾大学",
    "筑波大学",
    "東北大学",
    "一橋大学",
    "東京工業大学",
    # 海外大学
    "ハーバード大学",
    "MIT",
    "マサチューセッツ工科大学",
    "オックスフォード大学",
    "ケンブリッジ大学",
    "スタンフォード大学",
    # 研究機関
    "NASA",
    "JAXA",
    "CERN",
    "理化学研究所",
    "WHO",
    "UNESCO",
    "国連",
    # 放送・メディア
    "NHK",
    "TBS",
    "フジテレビ",
    "日本テレビ",
    "テレビ朝日",
    "テレビ東京",
    # 企業
    "トヨタ",
    "ソニー",
    "任天堂",
    "Google",
    "Apple",
    "Microsoft",
    "Amazon",
]

# FICTIONAL向け: 現代設定の作品（年号使用OK）
MODERN_SETTING_WORKS = [
    "名探偵コナン",
    "金田一少年の事件簿",
    "デスノート",
    "DEATH NOTE",
    "シュタインズ・ゲート",
    "Steins;Gate",
    "攻殻機動隊",
    "PSYCHO-PASS",
    "サイコパス",
    "ペルソナ",
    "Persona",
    "ドラえもん",
    "クレヨンしんちゃん",
    "サザエさん",
    "ちびまる子ちゃん",
    "こち亀",
    "こちら葛飾区亀有公園前派出所",
]

# FICTIONAL向け: 架空世界作品（現代年号禁止）
FICTIONAL_WORLD_WORKS = [
    "鬼滅の刃",
    "ONE PIECE",
    "ワンピース",
    "NARUTO",
    "ナルト",
    "ドラゴンボール",
    "進撃の巨人",
    "呪術廻戦",
    "HUNTER×HUNTER",
    "ハンターハンター",
    "BLEACH",
    "ブリーチ",
    "聖闘士星矢",
    "北斗の拳",
    "幽遊白書",
    "るろうに剣心",
    "銀魂",
    "鋼の錬金術師",
    "ハガレン",
    "ジョジョの奇妙な冒険",
    "範馬刃牙",
    "グラップラー刃牙",
    "刃牙",
    "ポケットモンスター",
    "ポケモン",
    "ハリー・ポッター",
    "Harry Potter",
    "ベルセルク",
    "犬夜叉",
    "転生したらスライムだった件",
    "転スラ",
    "Re:ゼロ",
    "リゼロ",
    "このすば",
    "この素晴らしい世界に祝福を",
    "オーバーロード",
]

# 現代年号パターン（1900-2026年）
MODERN_YEAR_PATTERN = re.compile(r"(19\d{2}|20[0-2]\d)年")

# REAL向け: 曖昧表現パターン（警告レベル）
UNVERIFIED_CLAIM_PATTERNS = [
    (r"と言われている", "「〜と言われている」"),
    (r"とされる", "「〜とされる」"),
    (r"とも言われ", "「〜とも言われ」"),
    (r"という説(?:も|が)ある", "「〜という説がある」"),
    (r"(?:諸説|異説)(?:あり|ある)", "諸説あり表現"),
    (r"定かではない", "「定かではない」"),
    (r"真偽は不明", "「真偽は不明」"),
]


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class Violation:
    """違反情報"""

    episode_id: str
    person_name: str
    person_type: str
    violation_type: ViolationType
    severity: Severity
    message: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "episode_id": self.episode_id,
            "person_name": self.person_name,
            "person_type": self.person_type,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ValidationResult:
    """検証結果"""

    total_episodes: int
    real_episodes: int
    fictional_episodes: int
    violations: list[Violation] = field(default_factory=list)

    def get_summary(self) -> dict:
        """サマリー生成"""
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        by_person_type: dict[str, int] = {"REAL": 0, "FICTIONAL": 0}

        for v in self.violations:
            vtype = v.violation_type.value
            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_severity[v.severity.value] += 1
            by_person_type[v.person_type] = by_person_type.get(v.person_type, 0) + 1

        return {
            "total_episodes": self.total_episodes,
            "real_episodes": self.real_episodes,
            "fictional_episodes": self.fictional_episodes,
            "total_violations": len(self.violations),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_person_type": by_person_type,
        }


# =============================================================================
# バリデーションロジック
# =============================================================================


class UnifiedEpisodeValidator:
    """統合エピソードバリデーター"""

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None
        self.current_year = datetime.now().year

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if not self.master_csv.exists():
                raise FileNotFoundError(f"Master CSV not found: {self.master_csv}. Please verify the path is correct.")
            self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            logger.info(f"Loaded {len(self._master_df)} episodes from {self.master_csv}")
        return self._master_df

    def validate_all(self) -> ValidationResult:
        """全件検証"""
        if self.master_df.empty:
            return ValidationResult(total_episodes=0, real_episodes=0, fictional_episodes=0)

        # UNVERIFIED_CLAIM検出の無効化をログ
        if not ENABLE_UNVERIFIED_CLAIM_CHECK:
            logger.info("UNVERIFIED_CLAIM check is disabled (適切なヘッジ表現は許容)")

        violations: list[Violation] = []
        real_count = 0
        fictional_count = 0

        for _, row in self.master_df.iterrows():
            row_dict = row.to_dict()
            person_type = str(row_dict.get("person_type", "")).upper()

            if "FICTIONAL" in person_type:
                fictional_count += 1
                violations.extend(self._validate_fictional(row_dict))
            else:
                real_count += 1
                violations.extend(self._validate_real(row_dict))

        return ValidationResult(
            total_episodes=len(self.master_df),
            real_episodes=real_count,
            fictional_episodes=fictional_count,
            violations=violations,
        )

    def _validate_fictional(self, row: dict) -> list[Violation]:
        """FICTIONAL向け検証"""
        violations: list[Violation] = []
        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        episode_text = str(row.get("episode_text", ""))
        work_title = str(row.get("work_title", ""))

        # 1. メタ情報混入検出
        for pattern, label in META_INFO_PATTERNS:
            if re.search(pattern, episode_text):
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        person_type="FICTIONAL",
                        violation_type=ViolationType.META_INFO_CONTAMINATION,
                        severity=Severity.ERROR,
                        message=f"メタ情報混入: {label}",
                        details={
                            "pattern": label,
                            "snippet": self._get_snippet(episode_text, pattern),
                        },
                    )
                )
                break  # 1つ検出で十分

        # 2. 実在機関言及検出（架空世界作品のみ）
        if self._is_fictional_world_work(work_title):
            for institution in REAL_INSTITUTIONS:
                if institution in episode_text:
                    violations.append(
                        Violation(
                            episode_id=episode_id,
                            person_name=person_name,
                            person_type="FICTIONAL",
                            violation_type=ViolationType.REAL_INSTITUTION_IN_FICTIONAL,
                            severity=Severity.ERROR,
                            message=f"架空世界作品に実在機関: {institution}",
                            details={
                                "institution": institution,
                                "work_title": work_title,
                                "snippet": self._get_snippet(episode_text, institution),
                            },
                        )
                    )
                    break  # 1つ検出で十分

        # 3. 現代年号検出（架空世界作品のみ）
        if self._is_fictional_world_work(work_title):
            matches = MODERN_YEAR_PATTERN.findall(episode_text)
            if matches:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        person_type="FICTIONAL",
                        violation_type=ViolationType.MODERN_YEAR_IN_FICTIONAL,
                        severity=Severity.ERROR,
                        message=f"架空世界作品に現代年号: {matches[0]}年",
                        details={
                            "detected_years": matches[:3],
                            "work_title": work_title,
                            "snippet": self._get_snippet(episode_text, f"{matches[0]}年"),
                        },
                    )
                )

        return violations

    def _validate_real(self, row: dict) -> list[Violation]:
        """REAL向け検証"""
        violations: list[Violation] = []
        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        episode_text = str(row.get("episode_text", ""))

        # 数値フィールドの安全な取得
        age = self._safe_int(row.get("age"), "age")
        birth_year = self._safe_int(row.get("birth_year"), "birth_year")
        death_year = self._safe_int(row.get("death_year"), "death_year")

        # 1. birth_year > death_year チェック
        if birth_year and death_year and birth_year > death_year:
            violations.append(
                Violation(
                    episode_id=episode_id,
                    person_name=person_name,
                    person_type="REAL",
                    violation_type=ViolationType.BIRTH_AFTER_DEATH,
                    severity=Severity.ERROR,
                    message=f"時系列矛盾: 生年({birth_year}) > 没年({death_year})",
                    details={
                        "birth_year": birth_year,
                        "death_year": death_year,
                    },
                )
            )

        # 2. age > (death_year - birth_year) チェック
        if age and birth_year and death_year:
            max_age = death_year - birth_year
            if age > max_age:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        person_type="REAL",
                        violation_type=ViolationType.AGE_EXCEEDS_LIFESPAN,
                        severity=Severity.ERROR,
                        message=f"享年超過: age({age}) > 最大年齢({max_age})",
                        details={
                            "age": age,
                            "max_age": max_age,
                            "birth_year": birth_year,
                            "death_year": death_year,
                        },
                    )
                )

        # 3. age > (current_year - birth_year) チェック（存命人物のみ）
        if age and birth_year and not death_year:
            current_age = self.current_year - birth_year
            if age > current_age:
                violations.append(
                    Violation(
                        episode_id=episode_id,
                        person_name=person_name,
                        person_type="REAL",
                        violation_type=ViolationType.AGE_EXCEEDS_CURRENT,
                        severity=Severity.ERROR,
                        message=f"未来年齢: age({age}) > 現在年齢({current_age})",
                        details={
                            "age": age,
                            "current_age": current_age,
                            "birth_year": birth_year,
                            "current_year": self.current_year,
                        },
                    )
                )

        # 4. 曖昧表現検出（設定フラグで制御）
        if ENABLE_UNVERIFIED_CLAIM_CHECK:
            for pattern, label in UNVERIFIED_CLAIM_PATTERNS:
                if re.search(pattern, episode_text):
                    violations.append(
                        Violation(
                            episode_id=episode_id,
                            person_name=person_name,
                            person_type="REAL",
                            violation_type=ViolationType.UNVERIFIED_CLAIM,
                            severity=Severity.WARNING,
                            message=f"曖昧表現: {label}",
                            details={
                                "pattern": label,
                                "snippet": self._get_snippet(episode_text, pattern),
                            },
                        )
                    )
                    break  # 1つ検出で十分

        return violations

    def _is_fictional_world_work(self, work_title: str) -> bool:
        """架空世界作品かどうか判定"""
        if not work_title or work_title == "nan":
            return False

        # 現代設定作品は除外
        for modern_work in MODERN_SETTING_WORKS:
            if modern_work.lower() in work_title.lower():
                return False

        # 架空世界作品リストに含まれるか
        for fictional_work in FICTIONAL_WORLD_WORKS:
            if fictional_work.lower() in work_title.lower():
                return True

        return False

    def _get_snippet(self, text: str, keyword: str, context_len: int = 50) -> str:
        """キーワード周辺のスニペット取得"""
        # 正規表現パターンの場合はマッチを探す
        match = re.search(keyword, text)
        if match:
            idx = match.start()
            keyword_text = match.group()
        elif keyword in text:
            idx = text.find(keyword)
            keyword_text = keyword
        else:
            return text[:100] + "..." if len(text) > 100 else text

        start = max(0, idx - context_len)
        end = min(len(text), idx + len(keyword_text) + context_len)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    @staticmethod
    def _safe_int(value: Any, field_name: str = "") -> Optional[int]:
        """安全にintに変換（変換失敗時はログを残す）"""
        if value is None or pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError) as e:
            if value and str(value).strip():  # 空でない値の場合のみ警告
                logger.warning(f"Failed to convert '{value}' to int for field '{field_name}': {e}")
            return None


# =============================================================================
# レポート生成
# =============================================================================


def generate_report(result: ValidationResult, output_path: Path) -> None:
    """JSONレポート生成"""
    summary = result.get_summary()

    # 代表例を抽出（各カテゴリ最大5件）
    examples_by_type: dict[str, list[dict]] = {}
    for v in result.violations:
        vtype = v.violation_type.value
        if vtype not in examples_by_type:
            examples_by_type[vtype] = []
        if len(examples_by_type[vtype]) < 5:
            examples_by_type[vtype].append(v.to_dict())

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "examples_by_type": examples_by_type,
        "all_violations": [v.to_dict() for v in result.violations],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def print_summary(result: ValidationResult) -> None:
    """サマリー表示"""
    summary = result.get_summary()

    print("=" * 70)
    print("EPUP: 統合エピソード検証結果")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print(f"\n総エピソード数: {summary['total_episodes']:,}件")
    print(f"  REAL: {summary['real_episodes']:,}件")
    print(f"  FICTIONAL: {summary['fictional_episodes']:,}件")

    print(f"\n違反件数: {summary['total_violations']}件")

    if summary["by_person_type"]:
        print("\n【人物タイプ別】")
        for ptype, count in summary["by_person_type"].items():
            if count > 0:
                print(f"  {ptype}: {count}件")

    if summary["by_severity"]:
        print("\n【重大度別】")
        for severity, count in summary["by_severity"].items():
            if count > 0:
                print(f"  {severity}: {count}件")

    if summary["by_type"]:
        print("\n【違反タイプ別】")
        for vtype, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
            print(f"  {vtype}: {count}件")


def print_examples(result: ValidationResult, limit: int = 5) -> None:
    """代表例表示"""
    # タイプ別にグループ化
    by_type: dict[str, list[Violation]] = {}
    for v in result.violations:
        vtype = v.violation_type.value
        if vtype not in by_type:
            by_type[vtype] = []
        by_type[vtype].append(v)

    print("\n" + "=" * 70)
    print("代表例（各カテゴリ最大5件）")
    print("=" * 70)

    for vtype, violations in sorted(by_type.items()):
        print(f"\n【{vtype}】({len(violations)}件)")
        for i, v in enumerate(violations[:limit], 1):
            print(f"  {i}. {v.episode_id} | {v.person_name}")
            print(f"     [{v.severity.value}] {v.message}")
            if v.details.get("snippet"):
                snippet = v.details["snippet"][:80]
                print(f"     スニペット: {snippet}...")


# =============================================================================
# CLI
# =============================================================================


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 統合エピソード検証スクリプト")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="検証のみ実行（修正なし）",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="検出した問題を自動修正（将来実装予定）",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="詳細レポートをJSONで出力",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="違反があればexit 1",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(REPORT_DIR / "unified_validation_report.json"),
        help="レポート出力先パス",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="代表例の表示件数（デフォルト: 5）",
    )
    parser.add_argument(
        "--person-type",
        type=str,
        choices=["REAL", "FICTIONAL", "ALL"],
        default="ALL",
        help="検証対象の人物タイプ",
    )

    args = parser.parse_args()

    # バリデーター初期化
    validator = UnifiedEpisodeValidator()

    if not validator.master_csv.exists():
        print(f"エラー: マスターCSVが見つかりません: {validator.master_csv}")
        return 2

    print("検証実行中...")
    result = validator.validate_all()

    # 人物タイプでフィルタリング
    if args.person_type != "ALL":
        result.violations = [v for v in result.violations if v.person_type == args.person_type]

    # サマリー表示
    print_summary(result)

    # 代表例表示
    if result.violations:
        print_examples(result, limit=args.limit)

    # レポート出力
    if args.report:
        output_path = Path(args.output)
        generate_report(result, output_path)
        print(f"\nレポート保存: {output_path}")

    # --fix モード（将来実装）
    if args.fix:
        print("\n注意: --fix モードは将来実装予定です。")
        print("現在は検出のみ実行されます。")

    # 終了コード
    summary = result.get_summary()
    error_count = summary["by_severity"].get("ERROR", 0)

    if args.verify and error_count > 0:
        print(f"\n[FAILED] {error_count}件のERROR違反があります")
        return 1

    print("\n[OK] 検証完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
