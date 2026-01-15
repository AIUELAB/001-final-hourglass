#!/usr/bin/env python3
"""
Narrative Inconsistency Scanner for Fictional Character Episodes

Scans all fictional character episodes for narrative inconsistencies:
1. Type 1 - Real-world institutions in fictional narratives (ERROR)
2. Type 2 - Modern years in fantasy/historical works (ERROR)
3. Type 3 - Cross-franchise character mixing (WARNING)
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# Paths
BASE_DIR = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass")
MASTER_CSV = BASE_DIR / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = BASE_DIR / "src/reports/narrative_inconsistency_scan.json"


# === Type 1: Real-world Institutions ===
JAPANESE_UNIVERSITIES = [
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
    "神戸大学",
    "広島大学",
    "千葉大学",
    "横浜国立大学",
    "金沢大学",
    "岡山大学",
    "新潟大学",
    "熊本大学",
]

FOREIGN_UNIVERSITIES = [
    "ハーバード大学",
    "MIT",
    "マサチューセッツ工科大学",
    "オックスフォード大学",
    "ケンブリッジ大学",
    "スタンフォード大学",
    "イェール大学",
    "プリンストン大学",
    "コロンビア大学",
    "カリフォルニア大学",
    "シカゴ大学",
    "デューク大学",
    "ペンシルベニア大学",
]

RESEARCH_ORGANIZATIONS = [
    "日本学術振興会",
    "科学技術振興機構",
    "理化学研究所",
    "産業技術総合研究所",
    "NASA",
    "CERN",
    "WHO",
    "国連",
    "UNESCO",
    "ユネスコ",
    "世界保健機関",
    "国際連合",
    "JAXA",
    "宇宙航空研究開発機構",
    "国立科学財団",
    "欧州宇宙機関",
    "ESA",
]

MODERN_EVENTS = [
    "オリンピック",
    "ワールドカップ",
    "甲子園",
    "箱根駅伝",
    "紅白歌合戦",
    "芥川賞",
    "直木賞",
    "アカデミー賞",
    "グラミー賞",
    "ノーベル賞",  # Note: May be appropriate for some fictional works
]

ALL_INSTITUTIONS = JAPANESE_UNIVERSITIES + FOREIGN_UNIVERSITIES + RESEARCH_ORGANIZATIONS + MODERN_EVENTS

# Works where certain real institutions are canonically appropriate
INSTITUTION_EXCEPTIONS: dict[str, list[str]] = {
    "新世紀エヴァンゲリオン": ["京都大学", "国連"],  # Canon: Gendo studied at Kyoto U, NERV is UN-affiliated
    "エヴァンゲリオン": ["京都大学", "国連"],
    "攻殻機動隊": ["国連", "WHO"],  # Near-future setting with real organizations
    "PSYCHO-PASS": ["国連"],  # Dystopian future Japan
    "デスノート": ["東京大学", "警視庁"],  # Modern Japan setting
    "名探偵コナン": ALL_INSTITUTIONS,  # Modern Japan crime drama
    "金田一少年の事件簿": ALL_INSTITUTIONS,  # Modern Japan mystery
    "シュタインズ・ゲート": ["東京大学", "CERN"],  # Time travel involving CERN
    "Steins;Gate": ["東京大学", "CERN"],
    "ペルソナ": ALL_INSTITUTIONS,  # Modern Japan setting
    "Persona": ALL_INSTITUTIONS,
}


# === Type 2: Works that should NOT have modern years ===
FANTASY_HISTORICAL_WORKS = [
    # Fantasy/Shounen
    "鬼滅の刃",
    "ドラゴンボール",
    "ONE PIECE",
    "ワンピース",
    "NARUTO",
    "ナルト",
    "ポケットモンスター",
    "ポケモン",
    "進撃の巨人",
    "聖闘士星矢",
    "呪術廻戦",
    "HUNTER×HUNTER",
    "ハンターハンター",
    "BLEACH",
    "ブリーチ",
    "銀魂",  # Note: Actually has modern elements, but in fictional Edo period
    "るろうに剣心",
    "範馬刃牙",
    "グラップラー刃牙",
    "刃牙",
    "ジョジョの奇妙な冒険",
    "ジョジョ",
    # Western Fantasy
    "ハリー・ポッター",
    "Harry Potter",
    "指輪物語",
    "ロード・オブ・ザ・リング",
    "ナルニア国物語",
    # Historical
    "三国志",
    "水滸伝",
    "西遊記",
    # Other Fantasy
    "ファイナルファンタジー",
    "FF",
    "ゼルダの伝説",
    "ゼルダ",
    "ダークソウル",
    "エルデンリング",
    # Classic Fantasy Manga
    "北斗の拳",
    "幽遊白書",
    "犬夜叉",
    "うしおととら",
    "ベルセルク",
    "クレイモア",
    "魔法陣グルグル",
    # Modern Shounen/Seinen with fantasy settings
    "鋼の錬金術師",
    "ハガレン",
    "FAIRY TAIL",
    "フェアリーテイル",
    "BLACK CLOVER",
    "ブラッククローバー",
    "マギ",
    "七つの大罪",
    "転生したらスライムだった件",
    "転スラ",
    "Re:ゼロ",
    "リゼロ",
    "このすば",
    "この素晴らしい世界に祝福を",
    "オーバーロード",
    "盾の勇者の成り上がり",
]

# Modern year pattern: 1950-2039
MODERN_YEAR_PATTERN = re.compile(r"(19[5-9]\d|20[0-3]\d)年")


# === Type 3: Cross-franchise Characters ===
# Major franchise-specific characters (using unique/longer names to avoid false positives)
FRANCHISE_CHARACTERS: dict[str, list[str]] = {
    "ドラゴンボール": [
        "孫悟空",
        "ベジータ",
        "フリーザ",
        "ピッコロ大魔王",
        "孫悟飯",
        "トランクス",
        "ブルマ",
        "クリリン",
        "亀仙人",
    ],
    "ONE PIECE": [
        "モンキー・D・ルフィ",
        "ロロノア・ゾロ",
        "サンジ",
        "ナミ",
        "ウソップ",
        "トニートニー・チョッパー",
        "ニコ・ロビン",
        "フランキー",
        "ブルック",
    ],
    "NARUTO": ["うずまきナルト", "うちはサスケ", "春野サクラ", "はたけカカシ", "自来也", "大蛇丸", "暁のメンバー"],
    "鬼滅の刃": ["竈門炭治郎", "竈門禰豆子", "我妻善逸", "嘴平伊之助", "煉獄杏寿郎", "鬼舞辻無惨"],
    "進撃の巨人": [
        "エレン・イェーガー",
        "ミカサ・アッカーマン",
        "アルミン・アルレルト",
        "リヴァイ兵長",
        "ハンジ・ゾエ",
        "エルヴィン団長",
    ],
    "呪術廻戦": ["虎杖悠仁", "伏黒恵", "釘崎野薔薇", "五条悟", "両面宿儺"],
    "HUNTER×HUNTER": ["ゴン＝フリークス", "キルア＝ゾルディック", "クラピカ", "レオリオ", "ヒソカ＝モロウ", "幻影旅団"],
    "ハリー・ポッター": [
        "ハリー・ポッター",
        "ロン・ウィーズリー",
        "ハーマイオニー・グレンジャー",
        "アルバス・ダンブルドア",
        "ヴォルデモート卿",
        "セブルス・スネイプ",
    ],
    "ポケットモンスター": ["サトシ", "ピカチュウ", "ロケット団", "ムサシとコジロウ"],
    "北斗の拳": ["ケンシロウ", "ラオウ", "トキ", "ジャギ", "ユリア"],
    "聖闘士星矢": [
        "ペガサス星矢",
        "ドラゴン紫龍",
        "キグナス氷河",
        "アンドロメダ瞬",
        "フェニックス一輝",
        "アテナ城戸沙織",
    ],
    "BLEACH": ["黒崎一護", "朽木ルキア", "井上織姫", "茶渡泰虎", "浦原喜助", "藍染惣右介"],
    "ジョジョの奇妙な冒険": ["ジョナサン・ジョースター", "ディオ・ブランドー", "空条承太郎", "ジョルノ・ジョバァーナ"],
    "銀魂": ["坂田銀時", "志村新八", "神楽", "近藤勲", "土方十四郎", "沖田総悟"],
}


def load_fictional_episodes() -> list[dict[str, Any]]:
    """Load all fictional character episodes from master CSV."""
    episodes = []

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_type = row.get("person_type", "")
            if "FICTIONAL" in person_type.upper():
                episodes.append(row)

    return episodes


def check_type1_institutions(episode_text: str, work_title: str) -> list[dict[str, str]]:
    """Check for real-world institutions in episode text."""
    violations = []

    # Check for work-specific exceptions
    exceptions: list[str] = []
    for work, excepted_institutions in INSTITUTION_EXCEPTIONS.items():
        if work_title and work.lower() in work_title.lower():
            exceptions = excepted_institutions
            break

    for institution in ALL_INSTITUTIONS:
        if institution in episode_text:
            # Skip if this institution is excepted for this work
            if institution in exceptions:
                continue

            violations.append(
                {"violation_type": "TYPE_1_REAL_INSTITUTION", "detected_pattern": institution, "severity": "ERROR"}
            )

    return violations


def check_type2_modern_years(episode_text: str, work_title: str) -> list[dict[str, str]]:
    """Check for modern years in fantasy/historical works."""
    violations = []

    # Check if work_title matches any fantasy/historical work
    is_fantasy_work = False
    matched_work = None

    for work in FANTASY_HISTORICAL_WORKS:
        if work and work_title and work.lower() in work_title.lower():
            is_fantasy_work = True
            matched_work = work
            break

    if is_fantasy_work:
        matches = MODERN_YEAR_PATTERN.findall(episode_text)
        for year in matches:
            violations.append(
                {
                    "violation_type": "TYPE_2_MODERN_YEAR_IN_FANTASY",
                    "detected_pattern": f"{year}年 (in {matched_work})",
                    "severity": "ERROR",
                }
            )

    return violations


def check_type3_cross_franchise(episode_text: str, work_title: str) -> list[dict[str, str]]:
    """Check for cross-franchise character mixing."""
    violations = []

    # Determine which franchise this episode belongs to
    current_franchise = None
    for franchise, _ in FRANCHISE_CHARACTERS.items():
        if work_title and franchise.lower() in work_title.lower():
            current_franchise = franchise
            break

    if not current_franchise:
        return violations

    # Check for characters from OTHER franchises
    for franchise, characters in FRANCHISE_CHARACTERS.items():
        if franchise == current_franchise:
            continue

        for character in characters:
            # Use word boundary check for short names to avoid false positives
            # For names 3 chars or less, require exact match with context
            if len(character) <= 3:
                # Skip very short names that could be part of other words
                continue

            if character in episode_text:
                violations.append(
                    {
                        "violation_type": "TYPE_3_CROSS_FRANCHISE",
                        "detected_pattern": f"{character} (from {franchise}) in {current_franchise}",
                        "severity": "WARNING",
                    }
                )

    return violations


def extract_text_snippet(text: str, pattern: str, context_chars: int = 50) -> str:
    """Extract a text snippet around the detected pattern."""
    idx = text.find(pattern.split(" (")[0])  # Handle patterns like "2020年 (in 鬼滅の刃)"
    if idx == -1:
        return text[:100] + "..." if len(text) > 100 else text

    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(pattern.split(" (")[0]) + context_chars)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def run_scan() -> dict[str, Any]:
    """Run the full narrative inconsistency scan."""
    print("Loading fictional character episodes...")
    episodes = load_fictional_episodes()
    print(f"Found {len(episodes)} fictional character episodes")

    all_violations: list[dict[str, Any]] = []
    type1_count = 0
    type2_count = 0
    type3_count = 0

    for i, episode in enumerate(episodes):
        if (i + 1) % 1000 == 0:
            print(f"Processing episode {i + 1}/{len(episodes)}...")

        episode_id = episode.get("episode_id", "")
        person_name = episode.get("person_name", "")
        work_title = episode.get("work_title", "")
        episode_text = episode.get("episode_text", "")

        if not episode_text:
            continue

        # Check all violation types
        violations = []
        violations.extend(check_type1_institutions(episode_text, work_title))
        violations.extend(check_type2_modern_years(episode_text, work_title))
        violations.extend(check_type3_cross_franchise(episode_text, work_title))

        for v in violations:
            if v["violation_type"].startswith("TYPE_1"):
                type1_count += 1
            elif v["violation_type"].startswith("TYPE_2"):
                type2_count += 1
            elif v["violation_type"].startswith("TYPE_3"):
                type3_count += 1

            all_violations.append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "work_title": work_title,
                    "violation_type": v["violation_type"],
                    "detected_pattern": v["detected_pattern"],
                    "severity": v["severity"],
                    "text_snippet": extract_text_snippet(episode_text, v["detected_pattern"]),
                }
            )

    # Build report
    report = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_fictional_episodes_scanned": len(episodes),
        "summary": {
            "total_violations": len(all_violations),
            "by_type": {
                "TYPE_1_REAL_INSTITUTION": type1_count,
                "TYPE_2_MODERN_YEAR_IN_FANTASY": type2_count,
                "TYPE_3_CROSS_FRANCHISE": type3_count,
            },
            "by_severity": {"ERROR": type1_count + type2_count, "WARNING": type3_count},
        },
        "violations": all_violations,
    }

    return report


def main():
    """Main entry point."""
    print("=" * 60)
    print("Narrative Inconsistency Scanner for Fictional Characters")
    print("=" * 60)

    report = run_scan()

    # Ensure output directory exists
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"\nTotal fictional episodes scanned: {report['total_fictional_episodes_scanned']}")
    print(f"\nViolations found: {report['summary']['total_violations']}")
    print(f"  - Type 1 (Real institutions): {report['summary']['by_type']['TYPE_1_REAL_INSTITUTION']}")
    print(f"  - Type 2 (Modern years in fantasy): {report['summary']['by_type']['TYPE_2_MODERN_YEAR_IN_FANTASY']}")
    print(f"  - Type 3 (Cross-franchise): {report['summary']['by_type']['TYPE_3_CROSS_FRANCHISE']}")
    print(f"\nReport saved to: {REPORT_PATH}")

    # Print sample violations if any
    if report["violations"]:
        print("\n" + "-" * 60)
        print("Sample violations (first 10):")
        print("-" * 60)
        for v in report["violations"][:10]:
            print(f"\n[{v['severity']}] {v['violation_type']}")
            print(f"  Episode: {v['episode_id']}")
            print(f"  Person: {v['person_name']} ({v['work_title']})")
            print(f"  Pattern: {v['detected_pattern']}")
            print(f"  Snippet: {v['text_snippet'][:100]}...")


if __name__ == "__main__":
    main()
