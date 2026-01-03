#!/usr/bin/env python3
"""
最重要転機（Tier1イベント）欠落検出スクリプト

目的:
- 有名人度上位N人について、最重要転機がエピソードに含まれているかを点検
- 欠落候補を検出し、追加計画を立案

使用方法:
    python scripts/validation/detect_turning_point_gaps.py --top 100 --dry-run
    python scripts/validation/detect_turning_point_gaps.py --top 50 --report
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"

# カテゴリ別期待転機キーワード
EXPECTED_TURNING_POINTS = {
    "政治・社会": [
        "大統領就任",
        "大統領初当選",
        "首相就任",
        "首相に就任",
        "国家主席",
        "王位継承",
        "皇位継承",
        "即位",
        "政権樹立",
        "革命",
        "クーデター",
        "独立宣言",
    ],
    "スポーツ": [
        "オリンピック金メダル",
        "金メダル獲得",
        "世界記録",
        "史上初",
        "世界選手権優勝",
        "ワールドカップ優勝",
        "グランドスラム",
        "MVP",
        "最優秀選手",
        "殿堂入り",
    ],
    "学術・研究": [
        "ノーベル賞",
        "ノーベル物理学賞",
        "ノーベル化学賞",
        "ノーベル医学賞",
        "ノーベル経済学賞",
        "フィールズ賞",
        "発見",
        "発明",
    ],
    "芸術・文化": [
        "ノーベル文学賞",
        "アカデミー賞",
        "カンヌ",
        "ベネチア",
        "芥川賞",
        "直木賞",
        "代表作",
        "デビュー",
    ],
    "音楽": [
        "グラミー賞",
        "レコード大賞",
        "デビュー",
        "初アルバム",
        "ビルボード1位",
        "オリコン1位",
    ],
    "ビジネス・経済": [
        "創業",
        "設立",
        "上場",
        "CEO就任",
        "買収",
        "世界一",
        "フォーブス",
    ],
}

# Tier1キーワード（最重要）
TIER1_KEYWORDS = [
    "ノーベル賞",
    "ノーベル平和賞",
    "ノーベル物理学賞",
    "ノーベル化学賞",
    "ノーベル文学賞",
    "ノーベル医学賞",
    "ノーベル経済学賞",
    "世界初",
    "史上初",
    "オリンピック金メダル",
    "大統領就任",
    "大統領初当選",
    "首相就任",
    "アカデミー賞",
    "グラミー賞",
]


@dataclass
class PersonTurningPointStatus:
    """人物の転機カバレッジ状態"""

    person_id: str
    person_name: str
    category: str
    celebrity_score: float
    episode_count: int
    tier1_found: list = field(default_factory=list)
    expected_found: list = field(default_factory=list)
    missing_candidates: list = field(default_factory=list)
    episodes: list = field(default_factory=list)


def load_master_csv() -> list[dict]:
    """マスターCSV読み込み"""
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def check_turning_points(episodes: list[dict], category: str) -> tuple[list, list]:
    """エピソードに含まれる転機キーワードを検出"""
    tier1_found = []
    expected_found = []

    for ep in episodes:
        text = ep.get("episode_text", "")

        # Tier1キーワード検出
        for kw in TIER1_KEYWORDS:
            if kw in text and kw not in tier1_found:
                tier1_found.append(kw)

        # カテゴリ別期待転機検出
        cat_keywords = EXPECTED_TURNING_POINTS.get(category, [])
        for kw in cat_keywords:
            if kw in text and kw not in expected_found:
                expected_found.append(kw)

    return tier1_found, expected_found


def detect_gaps(top_n: int = 100) -> list[PersonTurningPointStatus]:
    """有名人度上位N人の転機欠落を検出"""
    rows = load_master_csv()

    # 人物ごとにグループ化
    person_map = {}
    for row in rows:
        pid = row["person_id"]
        if pid not in person_map:
            person_map[pid] = {
                "person_id": pid,
                "person_name": row["person_name"],
                "category": row.get("category", ""),
                "celebrity_score": float(row.get("celebrity_score_v2", 0) or 0),
                "episode_count": int(float(row.get("episode_count", 0) or 0)),
                "episodes": [],
            }
        person_map[pid]["episodes"].append(row)

    # 有名人度でソート
    persons = sorted(person_map.values(), key=lambda x: x["celebrity_score"], reverse=True)

    results = []
    for p in persons[:top_n]:
        tier1_found, expected_found = check_turning_points(p["episodes"], p["category"])

        # 欠落候補の検出
        missing = []

        # 政治家なのにTier1政治キーワードがない
        if p["category"] == "政治・社会" and not any(
            k in tier1_found for k in ["大統領就任", "大統領初当選", "首相就任"]
        ):
            missing.append("最高職就任（大統領/首相）")

        # 科学者なのにノーベル賞系がない（ノーベル賞受賞者の場合）
        if (
            p["category"] == "学術・研究"
            and p["celebrity_score"] > 700
            and not any("ノーベル" in k for k in tier1_found)
        ):
            missing.append("ノーベル賞（該当する場合）")

        # アスリートなのにオリンピック金メダルがない
        if p["category"] == "スポーツ" and not any(
            "オリンピック" in k or "金メダル" in k for k in tier1_found + expected_found
        ):
            missing.append("オリンピック金メダル/主要タイトル")

        status = PersonTurningPointStatus(
            person_id=p["person_id"],
            person_name=p["person_name"],
            category=p["category"],
            celebrity_score=p["celebrity_score"],
            episode_count=p["episode_count"],
            tier1_found=tier1_found,
            expected_found=expected_found,
            missing_candidates=missing,
            episodes=[ep.get("episode_text", "")[:50] + "..." for ep in p["episodes"]],
        )
        results.append(status)

    return results


def generate_report(results: list[PersonTurningPointStatus], output_path: Path):
    """レポート生成"""
    # 欠落候補がある人物を抽出
    gaps = [r for r in results if r.missing_candidates]
    no_tier1 = [r for r in results if not r.tier1_found]

    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_checked": len(results),
            "with_tier1": len([r for r in results if r.tier1_found]),
            "without_tier1": len(no_tier1),
            "with_missing_candidates": len(gaps),
        },
        "missing_candidates": [
            {
                "person_id": r.person_id,
                "person_name": r.person_name,
                "category": r.category,
                "celebrity_score": r.celebrity_score,
                "missing": r.missing_candidates,
                "tier1_found": r.tier1_found,
            }
            for r in gaps
        ],
        "no_tier1_keywords": [
            {
                "person_id": r.person_id,
                "person_name": r.person_name,
                "category": r.category,
                "celebrity_score": r.celebrity_score,
                "expected_found": r.expected_found,
            }
            for r in no_tier1[:20]  # 上位20件のみ
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(description="最重要転機欠落検出")
    parser.add_argument("--top", type=int, default=100, help="点検対象の上位N人")
    parser.add_argument("--report", action="store_true", help="レポートファイルを生成")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（結果表示のみ）")
    args = parser.parse_args()

    print(f"=== 最重要転機欠落検出 (Top {args.top}) ===\n")

    results = detect_gaps(args.top)

    # サマリー
    with_tier1 = [r for r in results if r.tier1_found]
    without_tier1 = [r for r in results if not r.tier1_found]
    with_gaps = [r for r in results if r.missing_candidates]

    print(f"点検人物数: {len(results)}")
    print(f"Tier1キーワード含有: {len(with_tier1)}人")
    print(f"Tier1キーワードなし: {len(without_tier1)}人")
    print(f"欠落候補あり: {len(with_gaps)}人\n")

    # 欠落候補を表示
    if with_gaps:
        print("=== 欠落候補一覧 ===")
        for r in with_gaps[:10]:
            print(f"{r.person_name} ({r.category}): {r.missing_candidates}")

    # Tier1なしを表示
    if without_tier1:
        print("\n=== Tier1キーワードなし（上位10件） ===")
        for r in without_tier1[:10]:
            found = r.expected_found[:3] if r.expected_found else ["なし"]
            print(f"{r.person_name}: 検出キーワード={found}")

    # レポート生成
    if args.report:
        report_path = REPORT_DIR / f"turning_point_gaps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report = generate_report(results, report_path)
        print(f"\nレポート保存: {report_path}")

    return results


if __name__ == "__main__":
    main()
