#!/usr/bin/env python3
"""
状態ラベル検出ゲート（State Label Gate）

人物名の先頭に付与された状態ラベル（「ポケモン博士」「赤ちゃん」「老～」など）を
エピソード生成前に検出し、データ品質問題を防止する。

Usage:
    # MASTER_CSVをスキャンして状態ラベル付き人物名を検出
    python scripts/validation/state_label_gate.py --scan

    # テストケースを実行
    python scripts/validation/state_label_gate.py --test

    # 特定の人物名をチェック
    python scripts/validation/state_label_gate.py --check "ポケモン博士オーキド"

Exit codes:
    0: OK（状態ラベルなし）
    1: FAIL（状態ラベル検出）
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/state_label_gate_result.json"


# ============================================================================
# 状態ラベルパターン定義
# ============================================================================

STATE_LABEL_PATTERNS = [
    r"^ポケモン博士",  # ポケモン博士オーキド
    r"^赤ちゃん",  # 赤ちゃんプルート
    r"^金色の",  # 金色のガッシュ
    r"^銀色の",  # 銀色の髪のアギト
    r"^白い",  # 白いファング
    r"^黒い",  # 黒いマント
    r"^老(?!子)",  # 老ハンター（「老子」は哲学者なので除外）
    r"^幼少期の",  # 幼少期のルフィ
    r"^覚醒",  # 覚醒ルフィ
    r"^変身",  # 変身ヒーロー
    r"^進化",  # 進化形態
    r"^真の",  # 真の姿
]

# 除外パターン（これらにマッチする場合は状態ラベルとみなさない）
EXCLUSION_PATTERNS = [
    r"^老子$",  # 哲学者
    r"^老舗",  # 老舗〜（店の名前など）
    r"^老界王神$",  # ドラゴンボールの正式キャラクター名
    r"^老師$",  # 中国の敬称・正式な呼称
    r"^金色夜叉",  # 作品名
    r"^白井",  # 苗字
    r"^白石",  # 苗字
    r"^白川",  # 苗字
    r"^黒田",  # 苗字
    r"^黒澤",  # 苗字
    r"^黒沢",  # 苗字
]


class Severity(Enum):
    """重大度レベル"""

    CRITICAL = "critical"  # エピソード生成を完全にブロックすべき
    HIGH = "high"  # 高い優先度で修正が必要
    MEDIUM = "medium"  # 修正推奨
    LOW = "low"  # 注意喚起のみ


@dataclass
class GateCheckResult:
    """ゲートチェック結果"""

    is_valid: bool
    person_name: str
    work_title: str
    matched_pattern: Optional[str]
    severity: Optional[Severity]
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        result = asdict(self)
        if result["severity"]:
            result["severity"] = result["severity"].value
        return result


@dataclass
class StateLabelViolation:
    """状態ラベル違反レコード"""

    episode_id: str
    person_id: str
    person_name: str
    work_title: str
    matched_pattern: str
    severity: str
    episode_preview: str


# ============================================================================
# コア関数
# ============================================================================


def check_person_name(name: str) -> tuple[bool, str]:
    """
    人物名に状態ラベルが含まれているかチェック

    Args:
        name: チェック対象の人物名

    Returns:
        (is_valid, message) - is_validがTrueなら問題なし
    """
    if not name:
        return True, "空の名前"

    # 除外パターンチェック（これらはOK）
    for exclusion in EXCLUSION_PATTERNS:
        if re.search(exclusion, name):
            return True, f"除外パターンに該当: {exclusion}"

    # 状態ラベルチェック
    for pattern in STATE_LABEL_PATTERNS:
        if re.search(pattern, name):
            return False, f"状態ラベル検出: {pattern}"

    return True, "OK"


def validate_before_generation(person_name: str, work_title: str = "") -> GateCheckResult:
    """
    エピソード生成前の検証（SAGEオーケストレーター統合用）

    Args:
        person_name: 人物名
        work_title: 作品タイトル（オプション）

    Returns:
        GateCheckResult オブジェクト
    """
    if not person_name:
        return GateCheckResult(
            is_valid=True,
            person_name=person_name,
            work_title=work_title,
            matched_pattern=None,
            severity=None,
            message="空の人物名",
        )

    # 除外パターンチェック
    for exclusion in EXCLUSION_PATTERNS:
        if re.search(exclusion, person_name):
            return GateCheckResult(
                is_valid=True,
                person_name=person_name,
                work_title=work_title,
                matched_pattern=None,
                severity=None,
                message=f"除外パターンに該当: {exclusion}",
            )

    # 状態ラベルチェック
    for pattern in STATE_LABEL_PATTERNS:
        if re.search(pattern, person_name):
            # 重大度判定
            if pattern in [r"^ポケモン博士", r"^幼少期の", r"^覚醒", r"^変身", r"^進化"]:
                severity = Severity.CRITICAL
            elif pattern in [r"^赤ちゃん", r"^老(?!子)", r"^真の"]:
                severity = Severity.HIGH
            else:
                severity = Severity.MEDIUM

            # 修正提案の生成
            suggestion = _generate_suggestion(person_name, pattern)

            return GateCheckResult(
                is_valid=False,
                person_name=person_name,
                work_title=work_title,
                matched_pattern=pattern,
                severity=severity,
                message=f"状態ラベル '{pattern}' を検出。人物名には状態を含めないでください。",
                suggestion=suggestion,
            )

    return GateCheckResult(
        is_valid=True,
        person_name=person_name,
        work_title=work_title,
        matched_pattern=None,
        severity=None,
        message="OK",
    )


def _generate_suggestion(name: str, pattern: str) -> Optional[str]:
    """状態ラベル除去の提案を生成"""
    # パターンごとに除去を試みる
    removals = {
        r"^ポケモン博士": "ポケモン博士",
        r"^赤ちゃん": "赤ちゃん",
        r"^金色の": "金色の",
        r"^銀色の": "銀色の",
        r"^白い": "白い",
        r"^黒い": "黒い",
        r"^老(?!子)": "老",
        r"^幼少期の": "幼少期の",
        r"^覚醒": "覚醒",
        r"^変身": "変身",
        r"^進化": "進化",
        r"^真の": "真の",
    }

    prefix = removals.get(pattern, "")
    if prefix and name.startswith(prefix):
        suggested = name[len(prefix) :]
        if suggested:
            return f"'{suggested}' を使用してください"

    return None


# ============================================================================
# スキャン機能
# ============================================================================


def scan_master_csv() -> dict:
    """MASTER_CSVをスキャンして状態ラベル付き人物名を検出"""
    violations = []
    unique_persons = set()
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    if not MASTER_CSV.exists():
        return {
            "error": f"MASTER_CSVが見つかりません: {MASTER_CSV}",
            "total_violations": 0,
            "violations": [],
        }

    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_name = row.get("person_name", "")
            person_id = row.get("person_id", "")
            episode_id = row.get("episode_id", "")
            work_title = row.get("work_title", "")
            episode_text = row.get("episode_text", "")[:100] if row.get("episode_text") else ""

            if not person_name:
                continue

            # 重複チェック（同じ人物名は1回だけカウント）
            if person_name in unique_persons:
                continue

            result = validate_before_generation(person_name, work_title)

            if not result.is_valid:
                unique_persons.add(person_name)
                severity = result.severity.value if result.severity else "medium"
                severity_counts[severity] += 1

                violations.append(
                    StateLabelViolation(
                        episode_id=episode_id,
                        person_id=person_id,
                        person_name=person_name,
                        work_title=work_title,
                        matched_pattern=result.matched_pattern or "",
                        severity=severity,
                        episode_preview=episode_text,
                    )
                )

    # 重大度でソート
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    violations.sort(key=lambda x: severity_order.get(x.severity, 3))

    return {
        "scan_date": datetime.now().isoformat(),
        "master_csv": str(MASTER_CSV),
        "total_violations": len(violations),
        "unique_person_names": len(unique_persons),
        "severity_counts": severity_counts,
        "violations": [asdict(v) for v in violations],
    }


# ============================================================================
# テスト機能
# ============================================================================


def run_tests() -> bool:
    """テストケースを実行"""
    test_cases = [
        # (name, expected_valid, description)
        ("ポケモン博士オーキド", False, "ポケモン博士パターン"),
        ("赤ちゃんプルート", False, "赤ちゃんパターン"),
        ("金色のガッシュ", False, "金色のパターン"),
        ("銀色のアギト", False, "銀色のパターン"),
        ("白い牙", False, "白いパターン"),
        ("黒いマント", False, "黒いパターン"),
        ("老ハンター", False, "老パターン"),
        ("幼少期のルフィ", False, "幼少期のパターン"),
        ("覚醒ルフィ", False, "覚醒パターン"),
        ("変身ヒーロー", False, "変身パターン"),
        ("進化形態", False, "進化パターン"),
        ("真の姿", False, "真のパターン"),
        # 除外パターン（OK）
        ("老子", True, "老子は哲学者（除外）"),
        ("白井健三", True, "白井は苗字（除外）"),
        ("白石麻衣", True, "白石は苗字（除外）"),
        ("黒田官兵衛", True, "黒田は苗字（除外）"),
        ("黒澤明", True, "黒澤は苗字（除外）"),
        # 通常の名前（OK）
        ("織田信長", True, "通常の名前"),
        ("孫悟空", True, "通常の名前"),
        ("ルフィ", True, "通常の名前"),
        ("ピカチュウ", True, "通常の名前"),
        ("オーキド博士", True, "博士が後ろにある"),
    ]

    print("=" * 60)
    print("状態ラベルゲート テスト実行")
    print("=" * 60)

    passed = 0
    failed = 0
    failures = []

    for name, expected_valid, description in test_cases:
        is_valid, message = check_person_name(name)

        if is_valid == expected_valid:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
            failures.append((name, expected_valid, is_valid, message, description))

        print(f"  [{status}] {name:<20} (期待: {'OK' if expected_valid else 'NG'}) - {description}")

    print()
    print("=" * 60)
    print(f"結果: {passed}/{len(test_cases)} 成功")

    if failures:
        print("\n失敗ケース:")
        for name, expected, actual, msg, _desc in failures:
            print(f"  - {name}: 期待={expected}, 実際={actual}, メッセージ={msg}")

    print("=" * 60)

    return failed == 0


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="状態ラベル検出ゲート - 人物名の状態ラベルを検出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
    python scripts/validation/state_label_gate.py --scan
    python scripts/validation/state_label_gate.py --test
    python scripts/validation/state_label_gate.py --check "ポケモン博士オーキド"
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true", help="MASTER_CSVをスキャンして状態ラベル付き人物名を検出")
    group.add_argument("--test", action="store_true", help="テストケースを実行")
    group.add_argument("--check", type=str, metavar="NAME", help="特定の人物名をチェック")

    parser.add_argument("--json", action="store_true", help="結果をJSON形式で出力")
    parser.add_argument("--info-only", action="store_true", help="ゲートを落とさず情報のみ表示")

    args = parser.parse_args()

    # テストモード
    if args.test:
        success = run_tests()
        return 0 if success else 1

    # チェックモード
    if args.check:
        result = validate_before_generation(args.check)

        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print("状態ラベルチェック結果")
            print("=" * 60)
            print(f"  人物名: {result.person_name}")
            print(f"  有効: {'Yes' if result.is_valid else 'No'}")
            print(f"  メッセージ: {result.message}")
            if result.matched_pattern:
                print(f"  マッチしたパターン: {result.matched_pattern}")
            if result.severity:
                print(f"  重大度: {result.severity.value}")
            if result.suggestion:
                print(f"  提案: {result.suggestion}")
            print("=" * 60)

        if not result.is_valid and not args.info_only:
            return 1
        return 0

    # スキャンモード
    if args.scan:
        print("=" * 60)
        print("状態ラベルゲート - MASTER_CSVスキャン")
        print("=" * 60)

        result = scan_master_csv()

        if "error" in result:
            print(f"\n{result['error']}")
            return 1

        # レポート保存
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 結果表示
        print(f"\nスキャン日時: {result['scan_date']}")
        print(f"対象ファイル: {result['master_csv']}")
        print(f"\n総違反数: {result['total_violations']}")
        print(f"ユニーク人物名: {result['unique_person_names']}")
        print("\n重大度別:")
        print(f"  CRITICAL: {result['severity_counts']['critical']}")
        print(f"  HIGH: {result['severity_counts']['high']}")
        print(f"  MEDIUM: {result['severity_counts']['medium']}")
        print(f"  LOW: {result['severity_counts']['low']}")

        if result["violations"]:
            print("\n--- 検出された状態ラベル ---")
            for v in result["violations"][:20]:
                severity_icon = {
                    "critical": "CRITICAL",
                    "high": "HIGH",
                    "medium": "MEDIUM",
                    "low": "LOW",
                }.get(v["severity"], "")
                print(f"\n  [{severity_icon}] {v['person_name']}")
                print(f"    パターン: {v['matched_pattern']}")
                if v["work_title"]:
                    print(f"    作品: {v['work_title']}")
                if v["episode_preview"]:
                    print(f"    プレビュー: {v['episode_preview'][:60]}...")

            if len(result["violations"]) > 20:
                print(f"\n  ... 他 {len(result['violations']) - 20} 件")

        print(f"\nレポート保存: {REPORT_PATH}")

        # ゲート判定
        critical_high = result["severity_counts"]["critical"] + result["severity_counts"]["high"]

        if critical_high > 0:
            print(f"\nCRITICAL/HIGH違反: {critical_high}件検出")
            if not args.info_only:
                return 1

        if result["total_violations"] == 0:
            print("\nOK: 状態ラベル付き人物名なし")
        else:
            print(f"\n警告: {result['total_violations']}件の状態ラベル付き人物名を検出（ゲート通過）")

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
