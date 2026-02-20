#!/usr/bin/env python3
"""
品質回帰チェック - CI/CD統合用

丁寧語・「私は」パターンの品質劣化を自動検出。
GitHub ActionsおよびPre-commitフックから呼び出し可能。

Usage:
    python scripts/validation/quality_regression_check.py
    python scripts/validation/quality_regression_check.py --check polite
    python scripts/validation/quality_regression_check.py --check watashi
    python scripts/validation/quality_regression_check.py --threshold 5.0
"""

import argparse
import json
import re
import sys
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# マスターCSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 閾値設定
DEFAULT_PLAIN_THRESHOLD = 3.0  # 常体混入率 ≤3%
DEFAULT_WATASHI_THRESHOLD = 50  # 「私は」パターン（回帰検出用）
# Note: Phase 1で定型冒頭違反12件修正済み
# Note: Phase 2で文中の「私は/私の/私が」394件修正済み → 現在0件


class QualityRegressionChecker:
    """品質回帰チェッカー"""

    # 常体パターン（違反対象）
    # エピソードは丁寧語で書くべき。常体が残っていたら違反。
    PLAIN_FORM_PATTERNS = [
        (r"(?<!し)(?<!でし)(?<!ま)た[。、]", "常体「た」"),
        (r"(?<!し)だ[。、]", "常体「だ」"),
        (r"である[。、]", "常体「である」"),
        (r"だった[。、]", "常体「だった」"),
        (r"ない[。、]", "常体「ない」"),
        (r"なかった[。、]", "常体「なかった」"),
    ]

    # 「私は」パターン
    WATASHI_PATTERNS = [
        (r"私は[^」』）\n]*[。！？]", "「私は」"),
        (r"私の[^」』）\n]*[。！？]", "「私の」"),
        (r"私が[^」』）\n]*[。！？]", "「私が」"),
    ]

    # 除外パターン（引用・台詞内は許容）
    QUOTE_PATTERNS = [
        r"「[^」]*」",
        r"『[^』]*』",
        r"（[^）]*）",
    ]

    def __init__(
        self,
        csv_path: Path = MASTER_CSV,
        plain_threshold: float = DEFAULT_PLAIN_THRESHOLD,
        watashi_threshold: int = DEFAULT_WATASHI_THRESHOLD,
    ):
        self.csv_path = csv_path
        self.plain_threshold = plain_threshold
        self.watashi_threshold = watashi_threshold
        self.episodes = []

    def load_episodes(self) -> int:
        """エピソードをロード"""
        import pandas as pd

        if not self.csv_path.exists():
            raise FileNotFoundError(f"マスターCSVが見つかりません: {self.csv_path}")

        df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
        self.episodes = df.to_dict("records")
        return len(self.episodes)

    def _remove_quotes(self, text: str) -> str:
        """引用・台詞を除去"""
        for pattern in self.QUOTE_PATTERNS:
            text = re.sub(pattern, "", text)
        return text

    def check_plain_form(self) -> dict:
        """常体混入チェック"""
        violations = []
        total_episodes = len(self.episodes)

        for ep in self.episodes:
            ep_id = ep.get("episode_id", "UNKNOWN")
            text = str(ep.get("episode_text", ""))

            # 引用を除去してチェック
            clean_text = self._remove_quotes(text)

            for pattern, name in self.PLAIN_FORM_PATTERNS:
                matches = re.findall(pattern, clean_text)
                if matches:
                    violations.append(
                        {
                            "episode_id": ep_id,
                            "pattern": name,
                            "matches": matches[:3],  # 最大3件
                        }
                    )
                    break  # 1エピソードにつき1件カウント

        violation_count = len(violations)
        violation_rate = (violation_count / total_episodes * 100) if total_episodes > 0 else 0

        return {
            "check": "plain_form",
            "total_episodes": total_episodes,
            "violation_count": violation_count,
            "violation_rate": round(violation_rate, 2),
            "threshold": self.plain_threshold,
            "passed": violation_rate <= self.plain_threshold,
            "samples": violations[:10],  # サンプル10件
        }

    def check_watashi_pattern(self) -> dict:
        """「私は」パターンチェック"""
        violations = []

        for ep in self.episodes:
            ep_id = ep.get("episode_id", "UNKNOWN")
            text = str(ep.get("episode_text", ""))

            # 引用を除去してチェック
            clean_text = self._remove_quotes(text)

            for pattern, name in self.WATASHI_PATTERNS:
                matches = re.findall(pattern, clean_text)
                if matches:
                    violations.append(
                        {
                            "episode_id": ep_id,
                            "pattern": name,
                            "matches": matches[:3],
                        }
                    )
                    break

        return {
            "check": "watashi_pattern",
            "total_episodes": len(self.episodes),
            "violation_count": len(violations),
            "threshold": self.watashi_threshold,
            "passed": len(violations) <= self.watashi_threshold,
            "samples": violations[:10],
        }

    def check_opening_format(self) -> dict:
        """冒頭フォーマットチェック（情報的・非ブロッキング）"""
        violations = []
        expected_pattern = r"^あなたと同じ\d+歳のとき、.+は"

        for ep in self.episodes:
            ep_id = ep.get("episode_id", "UNKNOWN")
            text = str(ep.get("episode_text", ""))

            if not re.match(expected_pattern, text):
                # 冒頭50文字をサンプルとして取得
                violations.append(
                    {
                        "episode_id": ep_id,
                        "opening": text[:50] + "..." if len(text) > 50 else text,
                    }
                )

        # 冒頭フォーマットは歴史的経緯で違反が多いため、5%以下なら許容
        total = len(self.episodes)
        violation_rate = (len(violations) / total * 100) if total > 0 else 0
        threshold_pct = 5.0  # 5%以下

        return {
            "check": "opening_format",
            "total_episodes": total,
            "violation_count": len(violations),
            "violation_rate": round(violation_rate, 2),
            "threshold": threshold_pct,
            "passed": violation_rate <= threshold_pct,  # 5%以下ならパス
            "samples": violations[:10],
        }

    def run_all_checks(self) -> dict:
        """全チェックを実行"""
        self.load_episodes()

        results = {
            "plain_form": self.check_plain_form(),
            "watashi_pattern": self.check_watashi_pattern(),
            "opening_format": self.check_opening_format(),
        }

        # 全体判定
        all_passed = all(r["passed"] for r in results.values())

        return {
            "all_passed": all_passed,
            "results": results,
            "summary": {
                "total_episodes": len(self.episodes),
                "plain_rate": results["plain_form"]["violation_rate"],
                "watashi_count": results["watashi_pattern"]["violation_count"],
                "opening_violations": results["opening_format"]["violation_count"],
            },
        }


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(description="品質回帰チェック")
    parser.add_argument(
        "--check",
        choices=["all", "plain", "watashi", "opening"],
        default="all",
        help="チェック種別（デフォルト: all）",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_PLAIN_THRESHOLD,
        help=f"常体混入率閾値（デフォルト: {DEFAULT_PLAIN_THRESHOLD}%%）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で出力",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help="マスターCSVパス",
    )

    args = parser.parse_args()

    checker = QualityRegressionChecker(
        csv_path=Path(args.csv),
        plain_threshold=args.threshold,
    )

    try:
        checker.load_episodes()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    # チェック実行
    if args.check == "all":
        results = checker.run_all_checks()
    elif args.check == "plain":
        results = {"plain_form": checker.check_plain_form()}
        results["all_passed"] = results["plain_form"]["passed"]
    elif args.check == "watashi":
        results = {"watashi_pattern": checker.check_watashi_pattern()}
        results["all_passed"] = results["watashi_pattern"]["passed"]
    elif args.check == "opening":
        results = {"opening_format": checker.check_opening_format()}
        results["all_passed"] = results["opening_format"]["passed"]

    # 出力
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("品質回帰チェック結果")
        print("=" * 60)

        if "results" in results:
            for name, data in results["results"].items():
                status = "✅ PASS" if data["passed"] else "❌ FAIL"
                print(f"\n[{name}] {status}")
                print(f"  違反数: {data['violation_count']}")
                if "violation_rate" in data:
                    print(f"  違反率: {data['violation_rate']}% (閾値: {data['threshold']}%)")
                else:
                    print(f"  閾値: {data['threshold']}件")

                if data["samples"]:
                    print("  サンプル:")
                    for s in data["samples"][:3]:
                        print(f"    - {s['episode_id']}: {s.get('pattern', s.get('opening', ''))[:40]}")
        else:
            for name, data in results.items():
                if name == "all_passed":
                    continue
                status = "✅ PASS" if data["passed"] else "❌ FAIL"
                print(f"\n[{name}] {status}")
                print(f"  違反数: {data['violation_count']}")

        print("\n" + "=" * 60)
        overall = "✅ ALL CHECKS PASSED" if results["all_passed"] else "❌ SOME CHECKS FAILED"
        print(f"総合結果: {overall}")
        print("=" * 60)

    # 終了コード
    sys.exit(0 if results["all_passed"] else 1)


if __name__ == "__main__":
    main()
