#!/usr/bin/env python3
"""
包括的ファクトチェッカー

同一人物・同一イベントの矛盾検出と事実確認を行う
"""

import csv
import re
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/fact_check_report.json"

# 史実データベース（主要な人物のイベント年齢）
KNOWN_FACTS = {
    "葛飾北斎": {
        "birth_year": 1760,
        "death_year": 1849,
        "events": {
            "富嶽三十六景完成": {"age_range": (71, 73), "year_range": (1831, 1833)},
        },
    },
    "朝永振一郎": {
        "birth_year": 1906,
        "death_year": 1979,
        "events": {
            "ノーベル物理学賞受賞": {"age": 59, "year": 1965},
        },
    },
    "南部陽一郎": {
        "birth_year": 1921,
        "death_year": 2015,
        "events": {
            "ノーベル物理学賞受賞": {"age": 87, "year": 2008},
        },
    },
    "尾崎豊": {
        "birth_year": 1965,
        "death_year": 1992,
        "events": {
            "デビュー": {"age": 18, "year": 1983},
        },
    },
    "宇多田ヒカル": {
        "birth_year": 1983,
        "events": {
            "デビュー": {"age": 15, "year": 1998},
        },
    },
    "手塚治虫": {
        "birth_year": 1928,
        "death_year": 1989,
        "events": {
            "鉄腕アトム連載開始": {"age": 23, "year": 1951},
        },
    },
    "黒澤明": {
        "birth_year": 1910,
        "death_year": 1998,
        "events": {
            "七人の侍公開": {"age": 44, "year": 1954},
            "羅生門公開": {"age": 40, "year": 1950},
        },
    },
    "村上春樹": {
        "birth_year": 1949,
        "events": {
            "ノルウェイの森出版": {"age": 38, "year": 1987},
            "風の歌を聴け受賞": {"age": 30, "year": 1979},
        },
    },
}


@dataclass
class Contradiction:
    """矛盾情報"""

    person_name: str
    person_id: str
    event_type: str
    event_detail: str
    episodes: list = field(default_factory=list)
    age_spread: float = 0.0  # 年齢の最大差
    severity: str = "low"  # low, medium, high, critical
    known_fact: Optional[dict] = None
    recommendation: str = ""


def load_episodes() -> list[dict]:
    """エピソードを読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def extract_events(text: str) -> list[tuple[str, str]]:
    """テキストからイベントを抽出"""
    events = []

    patterns = [
        # 作品関連
        (r"[「『]([^」』]+)[」』](?:を|が)(?:完成|発表|出版|リリース|公開)", "work_release"),
        (r"代表作[「『]([^」』]+)[」』]", "masterpiece"),
        # 受賞関連
        (r"(ノーベル[^\s、。]+賞)(?:を|に)?(?:受賞|獲得)", "nobel"),
        (r"(アカデミー賞|グラミー賞|芥川賞|直木賞)(?:を|に)?(?:受賞|獲得)", "award"),
        # キャリア関連
        (r"(?:プロ|芸能界|音楽界)?(?:デビュー)", "debut"),
        (r"(?:引退|現役引退)", "retirement"),
        (r"(?:創業|設立|創設)", "founding"),
        # 記録関連
        (r"(?:世界記録|日本記録|新記録)", "record"),
        (r"(?:金メダル|銀メダル|銅メダル)(?:を)?(?:獲得)", "medal"),
    ]

    for pattern, event_type in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            detail = match if isinstance(match, str) else match
            events.append((event_type, detail))

    return events


def detect_contradictions(episodes: list[dict]) -> list[Contradiction]:
    """矛盾を検出"""
    # 人物・イベントごとにグループ化
    person_events = defaultdict(lambda: defaultdict(list))

    for ep in episodes:
        person_id = ep.get("person_id", "")
        person_name = ep.get("person_name", "")
        episode_id = ep.get("episode_id", "")
        age_str = ep.get("age", "")
        text = ep.get("episode_text", "")

        if not (person_id and text and age_str):
            continue

        try:
            age = float(age_str)
        except (ValueError, TypeError):
            continue

        events = extract_events(text)
        for event_type, event_detail in events:
            key = f"{event_type}:{event_detail[:30]}"
            person_events[(person_id, person_name)][key].append(
                {
                    "episode_id": episode_id,
                    "age": age,
                    "text_snippet": text[:200],
                }
            )

    contradictions = []

    for (person_id, person_name), events in person_events.items():
        for event_key, occurrences in events.items():
            if len(occurrences) < 2:
                continue

            ages = [o["age"] for o in occurrences]
            age_spread = max(ages) - min(ages)

            if age_spread < 2:  # 2歳未満の差は許容
                continue

            event_type, event_detail = event_key.split(":", 1)

            # 重大度判定
            if age_spread >= 10:
                severity = "critical"
            elif age_spread >= 5:
                severity = "high"
            elif age_spread >= 3:
                severity = "medium"
            else:
                severity = "low"

            # 史実との照合
            known_fact = None
            recommendation = ""
            if person_name in KNOWN_FACTS:
                person_facts = KNOWN_FACTS[person_name]
                for fact_name, fact_data in person_facts.get("events", {}).items():
                    if event_detail in fact_name or fact_name in event_detail:
                        known_fact = {"event": fact_name, **fact_data}
                        # 正しい年齢を特定
                        correct_age = fact_data.get("age") or fact_data.get("age_range", [None])[0]
                        if correct_age:
                            wrong_eps = [o for o in occurrences if abs(o["age"] - correct_age) > 2]
                            if wrong_eps:
                                recommendation = (
                                    f"史実: {correct_age}歳。誤りエピソード: {[e['episode_id'] for e in wrong_eps]}"
                                )
                        break

            contradictions.append(
                Contradiction(
                    person_name=person_name,
                    person_id=person_id,
                    event_type=event_type,
                    event_detail=event_detail,
                    episodes=occurrences,
                    age_spread=age_spread,
                    severity=severity,
                    known_fact=known_fact,
                    recommendation=recommendation,
                )
            )

    # 重大度順にソート
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    contradictions.sort(key=lambda x: (severity_order[x.severity], -x.age_spread))

    return contradictions


def generate_report(contradictions: list[Contradiction]) -> dict:
    """レポートを生成"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_contradictions": len(contradictions),
            "critical": sum(1 for c in contradictions if c.severity == "critical"),
            "high": sum(1 for c in contradictions if c.severity == "high"),
            "medium": sum(1 for c in contradictions if c.severity == "medium"),
            "low": sum(1 for c in contradictions if c.severity == "low"),
        },
        "contradictions": [],
    }

    for c in contradictions:
        report["contradictions"].append(
            {
                "person_name": c.person_name,
                "person_id": c.person_id,
                "event_type": c.event_type,
                "event_detail": c.event_detail,
                "age_spread": c.age_spread,
                "severity": c.severity,
                "episodes": c.episodes,
                "known_fact": c.known_fact,
                "recommendation": c.recommendation,
            }
        )

    return report


def main():
    print("=" * 60)
    print("包括的ファクトチェッカー")
    print("=" * 60)

    print("\nエピソード読み込み中...")
    episodes = load_episodes()
    print(f"総エピソード数: {len(episodes)}")

    print("\n矛盾検出中...")
    contradictions = detect_contradictions(episodes)

    print("\n=== 検出結果 ===")
    print(f"総矛盾数: {len(contradictions)}")
    print(f"  Critical (10歳以上の差): {sum(1 for c in contradictions if c.severity == 'critical')}")
    print(f"  High (5-9歳の差): {sum(1 for c in contradictions if c.severity == 'high')}")
    print(f"  Medium (3-4歳の差): {sum(1 for c in contradictions if c.severity == 'medium')}")
    print(f"  Low (2歳の差): {sum(1 for c in contradictions if c.severity == 'low')}")

    print("\n=== Critical/High の矛盾（上位20件） ===")
    critical_high = [c for c in contradictions if c.severity in ("critical", "high")]
    for i, c in enumerate(critical_high[:20], 1):
        ages = sorted(set(e["age"] for e in c.episodes))
        print(f"\n{i}. [{c.severity.upper()}] {c.person_name}")
        print(f"   イベント: {c.event_type} - {c.event_detail[:40]}")
        print(f"   年齢: {ages} (差: {c.age_spread}歳)")
        if c.known_fact:
            print(f"   史実: {c.known_fact}")
        if c.recommendation:
            print(f"   推奨: {c.recommendation}")
        for ep in c.episodes[:3]:
            print(f"   - {ep['episode_id']} (age={ep['age']})")

    # レポート保存
    report = generate_report(contradictions)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート保存: {REPORT_PATH}")

    # 削除推奨エピソードをリストアップ
    episodes_to_review = set()
    for c in critical_high:
        for ep in c.episodes:
            episodes_to_review.add(ep["episode_id"])

    print("\n=== 要確認エピソード ===")
    print(f"Critical/High矛盾に関連: {len(episodes_to_review)}件")

    return contradictions


if __name__ == "__main__":
    main()
