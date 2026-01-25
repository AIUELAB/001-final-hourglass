#!/usr/bin/env python3
"""
年齢分布チェッカー（品質ゲート）

5歳刻み問題の再発を防止するため、エピソードの年齢分布を検証する。

【検出パターン】
1. 等間隔パターン: 全エピソードが等間隔（例: 20, 25, 30）
2. 5の倍数偏重: 80%以上が5の倍数年齢
3. 機械的パターン: 同一人物のエピソードが不自然に規則的

【使用方法】
    from src.validators.age_distribution_checker import AgeDistributionChecker

    checker = AgeDistributionChecker()

    # 単一エピソード追加時のチェック
    result = checker.check_new_episode(person_id, new_age, existing_ages)
    if result.is_suspicious:
        print(f"警告: {result.message}")

    # 人物全体のチェック
    result = checker.check_person_distribution(person_id, all_ages)
    if result.is_suspicious:
        print(f"警告: {result.message}")

【作成日】2026-01-02
【目的】5歳刻み問題の再発防止
"""

from dataclasses import dataclass
from enum import Enum


class CheckResult(Enum):
    """チェック結果"""

    OK = "OK"
    WARNING = "WARNING"
    BLOCK = "BLOCK"


@dataclass
class AgeCheckResult:
    """年齢分布チェック結果"""

    result: CheckResult
    is_suspicious: bool
    message: str
    details: dict


class AgeDistributionChecker:
    """年齢分布チェッカー"""

    def __init__(
        self,
        five_multiple_threshold: float = 0.8,  # 5の倍数が80%以上で警告
        uniform_interval_threshold: int = 3,  # 3件以上の等間隔で警告
        strict: bool = False,  # True: BLOCK / False: WARNING
    ):
        self.five_multiple_threshold = five_multiple_threshold
        self.uniform_interval_threshold = uniform_interval_threshold
        self.strict = strict

    def check_new_episode(
        self,
        person_id: str,
        new_age: float,
        existing_ages: list[float],
    ) -> AgeCheckResult:
        """
        新規エピソード追加時のチェック

        追加後の年齢分布が疑わしいパターンにならないか検証する。
        """
        all_ages = sorted(existing_ages + [new_age])
        return self._check_distribution(person_id, all_ages, is_new_addition=True)

    def check_person_distribution(
        self,
        person_id: str,
        ages: list[float],
    ) -> AgeCheckResult:
        """人物全体の年齢分布チェック"""
        return self._check_distribution(person_id, sorted(ages), is_new_addition=False)

    def _check_distribution(
        self,
        person_id: str,
        ages: list[float],
        is_new_addition: bool = False,
    ) -> AgeCheckResult:
        """年齢分布の検証"""
        if len(ages) < 2:
            return AgeCheckResult(
                result=CheckResult.OK,
                is_suspicious=False,
                message="エピソード数が少ないためスキップ",
                details={"ages": ages, "count": len(ages)},
            )

        issues = []

        # 1. 5の倍数偏重チェック
        five_multiples = [a for a in ages if int(a) % 5 == 0]
        five_ratio = len(five_multiples) / len(ages)
        if five_ratio >= self.five_multiple_threshold:
            issues.append(f"5の倍数偏重: {len(five_multiples)}/{len(ages)} ({five_ratio:.0%})")

        # 2. 等間隔パターンチェック
        if len(ages) >= self.uniform_interval_threshold:
            int_ages = [int(a) for a in ages]
            if self._is_uniform_interval(int_ages):
                interval = int_ages[1] - int_ages[0]
                issues.append(f"等間隔パターン検出: {interval}歳刻み {int_ages}")

        # 3. 全て5の倍数チェック（最高リスク）
        if len(ages) >= 3 and all(int(a) % 5 == 0 for a in ages):
            issues.append(f"全て5の倍数: {[int(a) for a in ages]}")

        if issues:
            result_type = CheckResult.BLOCK if self.strict else CheckResult.WARNING
            action = "ブロック" if self.strict else "警告"
            context = "追加" if is_new_addition else "既存"

            return AgeCheckResult(
                result=result_type,
                is_suspicious=True,
                message=f"[{action}] {person_id} の{context}エピソード: " + "; ".join(issues),
                details={
                    "ages": ages,
                    "five_ratio": five_ratio,
                    "issues": issues,
                },
            )

        return AgeCheckResult(
            result=CheckResult.OK,
            is_suspicious=False,
            message="OK",
            details={"ages": ages, "five_ratio": five_ratio},
        )

    def _is_uniform_interval(self, ages: list[int]) -> bool:
        """等間隔かどうか判定"""
        if len(ages) < 3:
            return False

        intervals = [ages[i + 1] - ages[i] for i in range(len(ages) - 1)]

        # 全て同じ間隔か
        if len(set(intervals)) == 1:
            return True

        return False

    def scan_database(
        self,
        episodes_by_person: dict[str, list[float]],
    ) -> list[AgeCheckResult]:
        """
        データベース全体をスキャン

        Args:
            episodes_by_person: {person_id: [ages...]}

        Returns:
            疑わしい人物のリスト
        """
        suspicious = []
        for person_id, ages in episodes_by_person.items():
            result = self.check_person_distribution(person_id, ages)
            if result.is_suspicious:
                suspicious.append(result)

        return suspicious


def main():
    """CLI エントリーポイント"""
    import argparse
    import csv
    from collections import defaultdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description="年齢分布チェッカー")
    parser.add_argument(
        "--csv",
        type=str,
        default="preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="CSVファイルパス",
    )
    parser.add_argument("--strict", action="store_true", help="厳格モード")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        return 1

    # CSV読み込み
    episodes_by_person = defaultdict(list)
    person_names = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            age = row.get("age", "")
            name = row.get("person_name", "")
            if pid and age:
                try:
                    episodes_by_person[pid].append(float(age))
                    person_names[pid] = name
                except ValueError:
                    pass

    print("📊 年齢分布チェッカー")
    print(f"   対象: {len(episodes_by_person)}人")
    print()

    checker = AgeDistributionChecker(strict=args.strict)
    suspicious = checker.scan_database(episodes_by_person)

    if suspicious:
        print(f"⚠️ 疑わしいパターン: {len(suspicious)}件")
        print()
        for i, result in enumerate(suspicious[:20], 1):
            pid = result.details.get("ages", ["?"])[0] if result.details else "?"
            # person_idを抽出
            pid_match = result.message.split()[1] if len(result.message.split()) > 1 else "?"
            name = person_names.get(pid_match, "?")
            print(f"{i:3}. {name}: {result.message}")
    else:
        print("✅ 疑わしいパターンは検出されませんでした")

    # 統計
    total_episodes = sum(len(ages) for ages in episodes_by_person.values())
    five_multiple_count = sum(1 for ages in episodes_by_person.values() for a in ages if int(a) % 5 == 0)
    print()
    print("📈 統計")
    print(f"   総エピソード数: {total_episodes}")
    print(f"   5の倍数年齢: {five_multiple_count} ({five_multiple_count / total_episodes:.1%})")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
