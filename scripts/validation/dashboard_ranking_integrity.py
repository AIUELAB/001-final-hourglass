#!/usr/bin/env python3
"""
ダッシュボードランキング整合性検証

目的:
    ダッシュボードの人物ランキングがCSVの実データと整合しているかを検証

検証項目:
    1. 新しいスコアフィールドがpersonMap集計に含まれているか
    2. ダッシュボードTop 10がCSV Top 10と一致するか
    3. 有名度の低い人物が上位に来ていないか

使用方法:
    python scripts/validation/dashboard_ranking_integrity.py
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = PROJECT_ROOT / "preserved/episode_database_dashboard_v10.html"
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def extract_dashboard_person_scores(html: str) -> dict:
    """ダッシュボードHTMLから人物ごとの超総合スコアを抽出"""
    pattern = r'"person_name": "([^"]+)".*?"super_total_score": ([0-9.]+)'
    matches = re.findall(pattern, html, re.DOTALL)

    person_max = {}
    for name, score in matches:
        score = float(score)
        if name not in person_max or score > person_max[name]:
            person_max[name] = score
    return person_max


def get_csv_person_max_scores(csv_path: Path) -> dict:
    """CSVから人物ごとの超総合スコア最大値を取得"""
    df = pd.read_csv(csv_path, dtype=str)
    df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")

    person_max = {}
    for _, row in df.iterrows():
        name = row.get("person_name")
        score = row.get("super_total_score")
        if pd.notna(name) and pd.notna(score):
            if name not in person_max or score > person_max[name]:
                person_max[name] = score
    return person_max


def check_personmap_includes_super_total(html: str) -> bool:
    """personMapにsuper_total_scoreが含まれているか"""
    return "super_total_score: ep.super_total_score" in html


def check_max_score_logic(html: str) -> bool:
    """同一人物の最大値採用ロジックが含まれているか"""
    return "existing.super_total_score = ep.super_total_score" in html


def check_ranking_consistency(dashboard_scores: dict, csv_scores: dict, top_n: int = 20) -> list:
    """Top N人物のランキング整合性をチェック"""
    issues = []

    # CSVのTop N
    csv_sorted = sorted(csv_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    csv_top_names = {name for name, _ in csv_sorted}

    # ダッシュボードのTop N
    dash_sorted = sorted(dashboard_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    dash_top_names = {name for name, _ in dash_sorted}

    # 差分チェック
    only_in_csv = csv_top_names - dash_top_names
    only_in_dash = dash_top_names - csv_top_names

    if only_in_csv:
        issues.append(f"CSVにのみTop{top_n}入り: {only_in_csv}")
    if only_in_dash:
        issues.append(f"ダッシュボードにのみTop{top_n}入り: {only_in_dash}")

    return issues


def check_low_celebrity_in_top(dashboard_scores: dict, csv_path: Path, top_n: int = 50) -> list:
    """有名度の低い人物がTop Nに入っていないかチェック"""
    issues = []

    df = pd.read_csv(csv_path, dtype=str)
    df["celebrity_score_v2"] = pd.to_numeric(df["celebrity_score_v2"], errors="coerce")

    # 人物ごとのcelebrity_score_v2を取得
    person_celebrity = {}
    for _, row in df.iterrows():
        name = row.get("person_name")
        celeb = row.get("celebrity_score_v2")
        if pd.notna(name) and pd.notna(celeb):
            person_celebrity[name] = celeb

    # ダッシュボードTop N
    dash_sorted = sorted(dashboard_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # celebrity < 300 の人物がTop Nに入っていたら警告
    for name, score in dash_sorted:
        celeb = person_celebrity.get(name, 0)
        if celeb < 300:
            issues.append(f"低知名度人物がTop{top_n}入り: {name} (celebrity={celeb:.0f}, super_total={score:.0f})")

    return issues


def main():
    print("=" * 60)
    print("ダッシュボードランキング整合性検証")
    print("=" * 60)

    # ファイル読み込み
    html = DASHBOARD_PATH.read_text(encoding="utf-8")

    # 検証1: personMapにsuper_total_scoreが含まれているか
    print("\n1. personMap構造チェック")
    if check_personmap_includes_super_total(html):
        print("   ✅ super_total_scoreが含まれている")
    else:
        print("   ❌ super_total_scoreが含まれていない")
        sys.exit(1)

    # 検証2: 最大値採用ロジック
    print("\n2. 最大値採用ロジックチェック")
    if check_max_score_logic(html):
        print("   ✅ 同一人物の最大値採用ロジックあり")
    else:
        print("   ❌ 最大値採用ロジックなし")
        sys.exit(1)

    # 検証3: ランキング整合性
    print("\n3. ランキング整合性チェック (Top 20)")
    dashboard_scores = extract_dashboard_person_scores(html)
    csv_scores = get_csv_person_max_scores(CSV_PATH)
    issues = check_ranking_consistency(dashboard_scores, csv_scores, top_n=20)
    if issues:
        for issue in issues:
            print(f"   ⚠️ {issue}")
    else:
        print("   ✅ CSVとダッシュボードのTop 20が一致")

    # 検証4: 低知名度人物チェック
    print("\n4. 低知名度人物チェック (Top 50)")
    low_celeb_issues = check_low_celebrity_in_top(dashboard_scores, CSV_PATH, top_n=50)
    if low_celeb_issues:
        for issue in low_celeb_issues:
            print(f"   ⚠️ {issue}")
    else:
        print("   ✅ Top 50に低知名度人物なし")

    # 検証5: Top 10表示
    print("\n5. 超総合スコア Top 10")
    dash_sorted = sorted(dashboard_scores.items(), key=lambda x: x[1], reverse=True)
    for i, (name, score) in enumerate(dash_sorted[:10], 1):
        print(f"   {i:2}. {name}: {score:,.0f}")

    print("\n" + "=" * 60)
    if issues or low_celeb_issues:
        print("⚠️ 一部警告あり - 確認が必要です")
        return 1
    else:
        print("✅ 全検証PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
