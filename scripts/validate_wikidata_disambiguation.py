#!/usr/bin/env python3
"""
Wikidata同名曖昧性検出スクリプト（再発防止用）

短い名前で高いsitelinks_countを持つ人物を検出し、
Wikidataの誤エンティティ取得を防止する。
"""

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 閾値設定
SHORT_NAME_LENGTH = 5  # 短い名前の定義
HIGH_SITELINKS_THRESHOLD = 50  # 疑わしいsitelinks数
VERY_HIGH_SITELINKS_THRESHOLD = 100  # 高リスク

# CSVパス
DEFAULT_CSV = Path(__file__).parent.parent / "preserved/data/MASTER_EPISODES_CURRENT.csv"


@dataclass
class SuspiciousPerson:
    """疑わしい人物"""

    person_id: str
    person_name: str
    sitelinks_count: float
    fame_score_v3: float
    risk_level: str  # "high", "medium", "low"
    reason: str


def is_latin_only(name: str) -> bool:
    """ラテン文字のみかどうか"""
    return bool(re.match(r"^[A-Za-z\s'\-]+$", name))


def detect_suspicious_persons(csv_path: Path = DEFAULT_CSV) -> list[SuspiciousPerson]:
    """
    同名曖昧性リスクのある人物を検出。

    検出ルール:
    1. ラテン文字のみの短い名前 + 高sitelinks → 高リスク
    2. 日本語の短い名前 + 非常に高いsitelinks → 中リスク
    3. sitelinks > 200（言語数の実上限超過）→ 要確認
    """
    suspicious = []
    seen = set()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            pid = row.get("person_id", "")
            if pid in seen:
                continue
            seen.add(pid)

            name = row.get("person_name", "")
            sitelinks_str = row.get("sitelinks_count", "0")
            fame_str = row.get("fame_score_v3", "0")

            if not sitelinks_str:
                continue

            try:
                sitelinks = float(sitelinks_str)
                fame = float(fame_str) if fame_str else 0.0
            except ValueError:
                continue

            name_len = len(name)
            is_latin = is_latin_only(name)

            # ルール1: ラテン文字短名 + 高sitelinks
            if is_latin and name_len <= SHORT_NAME_LENGTH and sitelinks >= HIGH_SITELINKS_THRESHOLD:
                risk = "high" if sitelinks >= VERY_HIGH_SITELINKS_THRESHOLD else "medium"
                suspicious.append(
                    SuspiciousPerson(
                        person_id=pid,
                        person_name=name,
                        sitelinks_count=sitelinks,
                        fame_score_v3=fame,
                        risk_level=risk,
                        reason=f"ラテン文字短名({name_len}文字) + 高sitelinks",
                    )
                )
                continue

            # ルール2: sitelinks > 200（言語版上限超過）
            if sitelinks > 200:
                suspicious.append(
                    SuspiciousPerson(
                        person_id=pid,
                        person_name=name,
                        sitelinks_count=sitelinks,
                        fame_score_v3=fame,
                        risk_level="medium",
                        reason="sitelinks > 200（言語版上限超過）",
                    )
                )

    return suspicious


def main():
    """メインエントリポイント"""
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"📋 Wikidata同名曖昧性チェック: {csv_path}")
    print()

    suspicious = detect_suspicious_persons(csv_path)

    if not suspicious:
        print("✅ 疑わしい人物は検出されませんでした")
        sys.exit(0)

    # リスクレベル別に集計
    high_risk = [s for s in suspicious if s.risk_level == "high"]
    medium_risk = [s for s in suspicious if s.risk_level == "medium"]

    print(f"⚠️ 疑わしい人物: {len(suspicious)}件")
    print(f"  - 高リスク: {len(high_risk)}件")
    print(f"  - 中リスク: {len(medium_risk)}件")
    print()

    # 高リスクを表示
    if high_risk:
        print("=== 高リスク（要確認） ===")
        print(f"{'PID':<12} {'NAME':<8} {'sitelinks':>10} {'score':>10} {'理由'}")
        print("-" * 65)
        for s in sorted(high_risk, key=lambda x: -x.sitelinks_count)[:10]:
            print(
                f"{s.person_id:<12} {s.person_name:<8} {s.sitelinks_count:>10.0f} {s.fame_score_v3:>10.2f} {s.reason}"
            )
        print()

    # 中リスクを表示（上位5件）
    if medium_risk:
        print("=== 中リスク ===")
        for s in sorted(medium_risk, key=lambda x: -x.sitelinks_count)[:5]:
            print(f"  {s.person_id}: {s.person_name} - sitelinks={s.sitelinks_count:.0f}")
        if len(medium_risk) > 5:
            print(f"  ... 他 {len(medium_risk) - 5} 件")
        print()

    # 高リスクがあれば終了コード1
    if high_risk:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
