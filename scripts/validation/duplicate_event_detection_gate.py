#!/usr/bin/env python3
"""
同一出来事の複数年齢出現検出ゲート

同一人物で同一出来事（作品名/受賞名/マイルストーン）が複数の年齢エピソードに
出現する品質問題を検出し、閾値を超える場合にCRITICAL/WARNINGを返す。

Usage:
    python scripts/validation/duplicate_event_detection_gate.py [--threshold N]

Exit codes:
    0: OK
    1: CRITICAL（閾値超過）
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/duplicate_event_gate_result.json"

# デフォルト閾値（Phase 46: 同一EP内重複カウント修正後）
DEFAULT_THRESHOLDS = {
    "critical_max": 110,  # CRITICAL(10歳以上の差) - 現状107件
    "high_max": 35,  # HIGH(5-9歳の差) - 現状29件
    "total_max": 185,  # 合計 - 現状178件
}

# 記念年パターン（これらは重複カウントから除外）
ANNIVERSARY_PATTERNS = [
    r"(\d+)周年(?:記念|企画|祝|イベント|を迎え)",
    r"デビュー(\d+)周年",
    r"創業(\d+)周年",
    r"設立(\d+)周年",
    r"結成(\d+)周年",
    r"(\d+)年(?:目|周年)を(?:迎|記念)",
]

# 死亡・訃報パターン（これらは重複カウントから除外）
# 死亡エピソードは生涯の業績を要約するため、イベント重複は許容
OBITUARY_PATTERNS = [
    r"亡くなりました",
    r"(?:永眠|逝去|他界|死去)(?:しました|された)",
    r"(?:この世を|人生を)去りました",
    r"息を引き取りました",
    r"生涯を閉じました",
    r"最期を迎えました",
    r"訃報",
]

# 回顧・総括パターン（これらは重複カウントから除外）
# 晩年エピソードが過去の業績を振り返るのは自然なため許容
RETROSPECTIVE_PATTERNS = [
    r"振り返(?:り|って|る)",
    r"回顧(?:して|する|した)",
    r"(?:半生|人生|生涯)を(?:振り返|語|綴)",
    r"(?:歩み|足跡|軌跡)を(?:振り返|語|辿)",
    r"これまでの(?:歩み|人生|キャリア|活動)",
    r"長年の(?:功績|活動|貢献|経験)",
    r"(?:\d+|何十|数十)年間(?:の|を)",
]

# 許容される重複パターン（背景言及として許容）
ALLOWED_DUPLICATE_PATTERNS = {
    # (person_id, event_type): reason
    ("P2595B54", "nobel"),  # ヘミングウェイ: ノーベル賞背景言及
}

# イベント抽出パターン
EVENT_PATTERNS = [
    # 作品関連
    (r"[「『]([^」』]+)[」』](?:を|が)(?:完成|発表|出版|リリース|公開)", "work_release"),
    (r"[「『]([^」』]+)[」』](?:を|が)?(?:書き上げ|執筆|書い)", "work_creation"),
    (r"代表作[「『]([^」』]+)[」』]", "masterpiece"),
    # 受賞関連
    (r"(ノーベル[^\s、。]+賞)(?:を|に)?(?:受賞|獲得)", "nobel"),
    (r"(ピューリッツァー賞|オスカー|エミー賞|トニー賞)(?:を|に)?(?:受賞|獲得)?", "major_award"),
    (r"(アカデミー賞|グラミー賞|芥川賞|直木賞)(?:を|に)?(?:受賞|獲得)", "award"),
    # キャリア関連
    (r"(?:プロ|芸能界|音楽界)?(?:デビュー)", "debut"),
    (r"(?:引退|現役引退)", "retirement"),
    (r"(?:創業|設立|創設)", "founding"),
    # 記録関連
    (r"(?:世界記録|日本記録|新記録)", "record"),
    (r"(?:金メダル|銀メダル|銅メダル)(?:を)?(?:獲得)", "medal"),
]


@dataclass
class DuplicateEvent:
    """重複イベント"""

    person_id: str
    person_name: str
    event_type: str
    event_detail: str
    age_spread: float
    severity: str
    episodes: list


def has_anniversary_context(text: str) -> bool:
    """記念年の文脈かどうかを判定"""
    for pattern in ANNIVERSARY_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def has_obituary_context(text: str) -> bool:
    """死亡・訃報の文脈かどうかを判定"""
    for pattern in OBITUARY_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def has_retrospective_context(text: str) -> bool:
    """回顧・総括の文脈かどうかを判定"""
    for pattern in RETROSPECTIVE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def extract_events(
    text: str,
    skip_anniversary: bool = True,
    skip_obituary: bool = True,
    skip_retrospective: bool = True,
) -> list[tuple[str, str]]:
    """テキストからイベントを抽出

    Args:
        text: エピソードテキスト
        skip_anniversary: True の場合、記念年文脈のイベントをスキップ
        skip_obituary: True の場合、死亡・訃報文脈のイベントをスキップ
        skip_retrospective: True の場合、回顧・総括文脈のイベントをスキップ

    Returns:
        (event_type, event_detail) のリスト
    """
    # 記念年文脈の場合は空リストを返す（重複カウントから除外）
    if skip_anniversary and has_anniversary_context(text):
        return []

    # 死亡・訃報文脈の場合は空リストを返す（生涯要約のため重複許容）
    if skip_obituary and has_obituary_context(text):
        return []

    # 回顧・総括文脈の場合は空リストを返す（晩年の振り返りのため重複許容）
    if skip_retrospective and has_retrospective_context(text):
        return []

    events = []
    for pattern, event_type in EVENT_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            detail = match if isinstance(match, str) else match
            events.append((event_type, detail))
    return events


def scan_duplicate_events() -> dict:
    """重複イベントをスキャン"""
    # 人物・イベントごとにグループ化
    person_events = defaultdict(lambda: defaultdict(list))

    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")
            age_str = row.get("age", "")
            text = row.get("episode_text", "")

            if not (person_id and text and age_str):
                continue

            try:
                age = float(age_str)
            except (ValueError, TypeError):
                continue

            events = extract_events(text)
            # 同一エピソード内の重複イベントタイプを除外（1EP1イベントタイプ）
            seen_event_types = set()
            for event_type, event_detail in events:
                # イベントタイプごとに1回だけカウント
                if event_type in seen_event_types:
                    continue
                seen_event_types.add(event_type)

                key = f"{event_type}:{event_detail[:30]}"
                person_events[(person_id, person_name)][key].append(
                    {
                        "episode_id": episode_id,
                        "age": age,
                        "text_snippet": text[:150],
                    }
                )

    # 重複検出
    duplicates = []
    for (person_id, person_name), events in person_events.items():
        for event_key, occurrences in events.items():
            if len(occurrences) < 2:
                continue

            ages = [o["age"] for o in occurrences]
            age_spread = max(ages) - min(ages)

            if age_spread < 2:  # 2歳未満の差は許容
                continue

            event_type, event_detail = event_key.split(":", 1)

            # 許容パターンチェック
            if (person_id, event_type) in ALLOWED_DUPLICATE_PATTERNS:
                continue

            # 重大度判定
            if age_spread >= 10:
                severity = "critical"
            elif age_spread >= 5:
                severity = "high"
            elif age_spread >= 3:
                severity = "medium"
            else:
                severity = "low"

            duplicates.append(
                DuplicateEvent(
                    person_id=person_id,
                    person_name=person_name,
                    event_type=event_type,
                    event_detail=event_detail,
                    age_spread=age_spread,
                    severity=severity,
                    episodes=occurrences,
                )
            )

    # 重大度順にソート
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    duplicates.sort(key=lambda x: (severity_order[x.severity], -x.age_spread))

    # 統計
    severity_counts = {
        "critical": sum(1 for d in duplicates if d.severity == "critical"),
        "high": sum(1 for d in duplicates if d.severity == "high"),
        "medium": sum(1 for d in duplicates if d.severity == "medium"),
        "low": sum(1 for d in duplicates if d.severity == "low"),
    }

    return {
        "scan_date": datetime.now().isoformat(),
        "total_duplicates": len(duplicates),
        "severity_counts": severity_counts,
        "duplicates": [asdict(d) for d in duplicates],
    }


def evaluate_thresholds(result: dict, thresholds: dict) -> list:
    """閾値判定"""
    violations = []
    severity = result["severity_counts"]

    if severity["critical"] > thresholds["critical_max"]:
        violations.append(
            {
                "type": "critical",
                "severity": "CRITICAL",
                "value": severity["critical"],
                "threshold": thresholds["critical_max"],
                "message": f"CRITICAL重複: {severity['critical']}件 > 閾値{thresholds['critical_max']}",
            }
        )

    if severity["high"] > thresholds["high_max"]:
        violations.append(
            {
                "type": "high",
                "severity": "WARNING",
                "value": severity["high"],
                "threshold": thresholds["high_max"],
                "message": f"HIGH重複: {severity['high']}件 > 閾値{thresholds['high_max']}",
            }
        )

    if result["total_duplicates"] > thresholds["total_max"]:
        violations.append(
            {
                "type": "total",
                "severity": "WARNING",
                "value": result["total_duplicates"],
                "threshold": thresholds["total_max"],
                "message": f"合計重複: {result['total_duplicates']}件 > 閾値{thresholds['total_max']}",
            }
        )

    return violations


def main():
    parser = argparse.ArgumentParser(description="同一出来事の複数年齢出現検出ゲート")
    parser.add_argument(
        "--critical-max", type=int, default=DEFAULT_THRESHOLDS["critical_max"], help="CRITICAL最大許容件数"
    )
    parser.add_argument("--high-max", type=int, default=DEFAULT_THRESHOLDS["high_max"], help="HIGH最大許容件数")
    parser.add_argument("--total-max", type=int, default=DEFAULT_THRESHOLDS["total_max"], help="合計最大許容件数")
    parser.add_argument("--info-only", action="store_true", help="ゲートを落とさず情報のみ表示")
    args = parser.parse_args()

    thresholds = {
        "critical_max": args.critical_max,
        "high_max": args.high_max,
        "total_max": args.total_max,
    }

    print("=" * 60)
    print("同一出来事の複数年齢出現検出ゲート")
    print("=" * 60)

    result = scan_duplicate_events()
    violations = evaluate_thresholds(result, thresholds)

    # レポート出力
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        **result,
        "thresholds": thresholds,
        "violations": violations,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 結果表示
    print(f"\n総重複数: {result['total_duplicates']}")
    print(f"  CRITICAL (10歳以上): {result['severity_counts']['critical']}")
    print(f"  HIGH (5-9歳): {result['severity_counts']['high']}")
    print(f"  MEDIUM (3-4歳): {result['severity_counts']['medium']}")
    print(f"  LOW (2歳): {result['severity_counts']['low']}")

    if result["duplicates"]:
        print("\n--- CRITICAL/HIGH (上位5件) ---")
        for d in result["duplicates"][:5]:
            if d["severity"] not in ["critical", "high"]:
                continue
            ages = [e["age"] for e in d["episodes"]]
            print(f"  [{d['severity'].upper()}] {d['person_name']}: {d['event_type']}:{d['event_detail']}")
            print(f"    年齢: {ages} (差: {d['age_spread']}歳)")

    print(f"\n✅ レポート: {REPORT_PATH}")

    # 閾値判定
    if violations:
        critical_count = sum(1 for v in violations if v["severity"] == "CRITICAL")
        warning_count = sum(1 for v in violations if v["severity"] == "WARNING")

        print(f"\n⚠️ 違反: CRITICAL={critical_count}, WARNING={warning_count}")
        for v in violations:
            icon = "❌" if v["severity"] == "CRITICAL" else "⚠️"
            print(f"  {icon} {v['message']}")

        if critical_count > 0 and not args.info_only:
            return 1

    print("\n✅ OK: ゲート通過" if not violations else "\n⚠️ INFO: 警告あり（ゲート通過）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
