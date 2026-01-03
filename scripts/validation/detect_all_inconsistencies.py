#!/usr/bin/env python3
"""
エピソード不整合 全件検出スクリプト

検出カテゴリ:
A. 年齢・年・生没年の整合
B. 本文とフィールドの不一致
C. 事実関係の矛盾（検証可能パターン）
D. 架空キャラのカノン整合

出力: src/reports/episode_inconsistency_report_YYYYMMDD_HHMMSS.json
"""

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORTS_DIR = Path("src/reports")
CURRENT_YEAR = 2026


def load_episodes():
    """エピソード読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def check_age_year_consistency(row):
    """A. 年齢・年・生没年の整合チェック"""
    issues = []

    age_str = row.get("age", "")
    birth_year_str = row.get("birth_year", "")
    death_year_str = row.get("death_year", "")
    text = row.get("episode_text", "")

    # 年齢を取得
    try:
        age = float(age_str) if age_str else None
    except (ValueError, TypeError):
        age = None

    # 生年・没年を取得
    try:
        birth_year = int(float(birth_year_str)) if birth_year_str else None
    except (ValueError, TypeError):
        birth_year = None

    try:
        death_year = int(float(death_year_str)) if death_year_str else None
    except (ValueError, TypeError):
        death_year = None

    # 本文から年を抽出
    year_match = re.search(r"(\d{4})年", text)
    text_year = int(year_match.group(1)) if year_match else None

    # A1: 年齢が没年-生年を超える
    if age is not None and birth_year and death_year:
        max_age = death_year - birth_year
        if age > max_age:
            issues.append(
                {
                    "type": "A1_age_exceeds_lifespan",
                    "detail": f"age={age} > max_age={max_age} (death={death_year}-birth={birth_year})",
                    "severity": "high",
                }
            )

    # A2: 年齢が現在年-生年を超える（存命者の場合）
    if age is not None and birth_year and not death_year:
        max_age = CURRENT_YEAR - birth_year
        if age > max_age:
            issues.append(
                {"type": "A2_age_exceeds_current", "detail": f"age={age} > current_max={max_age}", "severity": "high"}
            )

    # A3: 本文の年と年齢・生年の不整合
    if text_year and birth_year and age is not None:
        expected_age = text_year - birth_year
        if abs(age - expected_age) > 1:  # 1歳の誤差は許容
            issues.append(
                {
                    "type": "A3_year_age_mismatch",
                    "detail": f"text_year={text_year}, birth={birth_year}, age={age}, expected_age={expected_age}",
                    "severity": "medium",
                }
            )

    # A4: 年齢が0未満または150超（架空キャラは除外：神話/ファンタジーで正当な年齢があるため）
    person_type = row.get("person_type", "")
    if age is not None and person_type != "FICTIONAL":
        if age < 0 or age > 150:
            issues.append(
                {
                    "type": "A4_invalid_age_range",
                    "detail": f"age={age} is out of valid range (0-150)",
                    "severity": "high",
                }
            )

    return issues


def check_name_text_consistency(row):
    """B. 本文とフィールドの不一致チェック"""
    issues = []

    person_name = row.get("person_name", "")
    text = row.get("episode_text", "")
    person_type = row.get("person_type", "")

    if not person_name or not text:
        return issues

    # B1: 本文冒頭に人物名が含まれていない
    # 「あなたと同じXX歳のとき、{person_name}は」パターンをチェック
    expected_pattern = f"のとき、{person_name}は"
    alt_pattern = f"のとき、{person_name}の"

    if expected_pattern not in text and alt_pattern not in text:
        # 名前の一部（姓/名/通称）が含まれているかチェック
        # スペース区切り、中黒区切り、姓名分離などを考慮
        name_parts = re.split(r"[\s・　]+", person_name)
        # 2文字以上の部分一致でOK（略称使用は許容）
        found_partial = any(part in text[:150] for part in name_parts if len(part) >= 2)
        # 姓のみ、名のみでも許容（例: モーツァルト、ダーウィン）
        if not found_partial:
            issues.append(
                {
                    "type": "B1_name_not_in_text",
                    "detail": f"person_name='{person_name}' not found in text start",
                    "severity": "medium",
                }
            )

    # B2: 英語名が混入している可能性（作品名・曲名・固有名詞は除外）
    english_name_match = re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", text[:150])
    if english_name_match and not re.search(r"[A-Za-z]", person_name):
        matched = english_name_match.group()
        # 作品名・曲名・タイトル・グループ名として許容するパターン
        title_keywords = [
            # 既存キーワード
            "First",
            "Love",
            "Best",
            "New",
            "The",
            "My",
            "One",
            "Last",
            "World",
            "Star",
            "Super",
            "Final",
            "Grand",
            "Big",
            "Live",
            "Tour",
            "Show",
            "Album",
            "Single",
            "Music",
            "Song",
            "Film",
            "Movie",
            "Series",
            "This",
            "That",
            "You",
            "We",
            "Man",
            "Girl",
            "Boy",
            "Night",
            "Day",
            "Heart",
            "Dream",
            "Time",
            "Life",
            "Snow",
            "Rain",
            "Sun",
            "Moon",
            "King",
            "Queen",
            "Prince",
            "Rock",
            "Pop",
            "Jazz",
            "Blue",
            "Red",
            "Black",
            "White",
            "Gold",
            "Silver",
            "All",
            "Dance",
            "Beat",
            "Sound",
            # 追加キーワード（2026-01-04）
            # 地名・国名
            "Japan",
            "America",
            "Europe",
            "Asia",
            "Tokyo",
            # 曲名・作品名によく使われる語
            "Never",
            "Let",
            "Will",
            "Always",
            "Stop",
            "Believin",
            "Smells",
            "Like",
            "Both",
            "Sides",
            "Get",
            "Rich",
            "Til",
            "Twenty",
            "Flight",
            "Without",
            "River",
            "Island",
            "Happy",
            "Be",
            # グループ名・企業名・サービス名
            "Sexy",
            "Zone",
            "Billboard",
            "Kaikai",
            "Kiki",
            "Google",
            "Meet",
            "Lab",
            "Reality",
            "Safety",
            "Technologies",
            "Materials",
            "Applied",
            "Thought",
            "Breakthrough",
            "Initiatives",
            "Mail",
            # 追加キーワード（2026-01-04 Phase2）
            # ゲーム/テック企業名
            "Nintendo",
            "Digital",
            "Blizzard",
            "Entertainment",
            "Activision",
            "Comics",
            "Image",
            "Tango",
            "Gameworks",
            "Ion",
            "Storm",
            "Switch",
            "Vista",
            "Windows",
            "Unreal",
            "Engine",
            "Engi",
            "Speck",
            "Tiny",
            # 曲名・アルバム名によく使われる語
            "Little",
            "Full",
            "Away",
            "Chaos",
            "Slippery",
            "Sugar",
            "Blood",
            "Tenderness",
            "Eclipse",
            "Total",
            "Angry",
            "Birds",
            "Stranger",
            "Shine",
            "Million",
            "Ways",
            "Can",
            "Don",
            "Hips",
            "Tell",
            "It",
            "Look",
            "Back",
            "Green",
            "Second",
            "Toughest",
            "Down",
            "Somewhere",
            "Jagged",
            "Called",
            "Oral",
            "Fixation",
            "Descalz",
            "Pies",
            "Head",
            "Come",
            # 書籍・映画名
            "Wimpy",
            "Kid",
            "Understanding",
            "Fall",
            "Things",
            "Everyday",
            "Low",
            "Odd",
            "Foot",
            # 固有名詞（施設・組織）
            "Hull",
            "House",
            "Row",
            "Death",
            "Kids",
            "Skywalker",
            "Luke",
            "Muster",
            "Mark",
            "Dean",
            "Martin",
            "Norman",
            "Lear",
            "Ian",
            "Alexander",
            "Negro",
            "Policeman",
        ]
        is_likely_title = any(kw in matched for kw in title_keywords)
        # 『』「」で囲まれている場合も作品名として許容
        is_quoted = re.search(rf"[『「]{re.escape(matched)}[』」]", text[:200])
        if not is_likely_title and not is_quoted:
            issues.append(
                {
                    "type": "B2_english_name_in_text",
                    "detail": f"English name '{matched}' found in text but person_name is '{person_name}'",
                    "severity": "low",
                }
            )

    # B3: PERSON種別と本文の矛盾
    if person_type == "FICTIONAL":
        # 架空キャラなのに実在イベント（ノーベル賞等）への言及
        real_events = ["ノーベル賞", "アカデミー賞受賞", "オリンピック金メダル", "大統領就任"]
        for event in real_events:
            if event in text:
                issues.append(
                    {
                        "type": "B3_fictional_real_event",
                        "detail": f"FICTIONAL character with real event: '{event}'",
                        "severity": "high",
                    }
                )
                break

    return issues


def check_fictional_canon(row):
    """D. 架空キャラのカノン整合チェック"""
    issues = []

    person_type = row.get("person_type", "")
    text = row.get("episode_text", "")
    age_str = row.get("age", "")

    if person_type != "FICTIONAL":
        return issues

    # D1: 架空キャラに具体的な年（西暦）が断定されている
    # ただし、作品発表/放送/連載開始年への言及は許容（例: 「1996年に連載開始」）
    # また「X年の歳月」「X年間」は期間表現なので除外
    year_match = re.search(r"(\d{4})年(?!の歳月|間)", text)
    if year_match:
        year = int(year_match.group(1))
        # 現実の年（1900-2030）を参照している場合
        if 1900 <= year <= 2030:
            # 作品発表文脈の許容パターン（メタ情報として適切）
            work_context_patterns = [
                r"\d{4}年.{0,10}(連載|放送|公開|発表|発売|リリース|登場|デビュー|アニメ化)",
                r"\d{4}年(から|より)(連載|放送|開始)",
                r"(連載|放送|公開)が始まった\d{4}年",
                r"(初登場|誕生|生まれ)した?\d{4}年",
                r"\d{4}年\d{1,2}月\d{1,2}日に(誕生|生まれ)",  # 設定上の誕生日
                r"声優|制作|原作|作者|監督",  # 作品メタ情報への言及
            ]
            is_work_context = any(re.search(p, text) for p in work_context_patterns)
            if not is_work_context:
                issues.append(
                    {
                        "type": "D1_fictional_real_year",
                        "detail": f"FICTIONAL character with specific real year: {year}",
                        "severity": "medium",
                    }
                )

    # D2: メタ的表現の検出
    meta_patterns = [
        r"作中で|物語の中で|原作では|作品内で",
        r"設定では|公式設定|キャラクター設定",
        r"という設定|とされている|描かれている",
    ]
    for pattern in meta_patterns:
        if re.search(pattern, text):
            issues.append(
                {
                    "type": "D2_meta_expression",
                    "detail": f"Meta expression detected: pattern='{pattern}'",
                    "severity": "high",
                }
            )
            break

    return issues


def check_factual_issues(row):
    """C. 事実関係の矛盾（検証可能パターン）"""
    issues = []

    text = row.get("episode_text", "")
    person_name = row.get("person_name", "")
    age_str = row.get("age", "")

    # C1: 「同じX歳」と本文中の年齢が不一致
    try:
        field_age = int(float(age_str)) if age_str else None
    except (ValueError, TypeError):
        field_age = None

    if field_age is not None:
        text_age_match = re.search(r"同じ(\d+)歳", text)
        if text_age_match:
            text_age = int(text_age_match.group(1))
            if text_age != field_age:
                issues.append(
                    {
                        "type": "C1_age_field_text_mismatch",
                        "detail": f"field_age={field_age}, text_age={text_age}",
                        "severity": "high",
                    }
                )

    # C2: 未来の出来事への言及
    future_patterns = [
        r"(202[7-9]|20[3-9]\d|21\d{2})年",
    ]
    for pattern in future_patterns:
        match = re.search(pattern, text)
        if match:
            issues.append(
                {"type": "C2_future_event", "detail": f"Future year reference: {match.group()}", "severity": "high"}
            )
            break

    return issues


def main():
    print("=" * 60)
    print("エピソード不整合 全件検出")
    print("=" * 60)

    episodes = load_episodes()
    print(f"総エピソード数: {len(episodes)}")

    # カテゴリ別に集計
    results = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_episodes": len(episodes),
        "categories": {"A_age_year": [], "B_name_text": [], "C_factual": [], "D_fictional": []},
        "summary": {},
    }

    for row in episodes:
        ep_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")

        # A. 年齢・年整合
        a_issues = check_age_year_consistency(row)
        for issue in a_issues:
            results["categories"]["A_age_year"].append({"episode_id": ep_id, "person_name": person_name, **issue})

        # B. 名前・本文整合
        b_issues = check_name_text_consistency(row)
        for issue in b_issues:
            results["categories"]["B_name_text"].append({"episode_id": ep_id, "person_name": person_name, **issue})

        # C. 事実関係
        c_issues = check_factual_issues(row)
        for issue in c_issues:
            results["categories"]["C_factual"].append({"episode_id": ep_id, "person_name": person_name, **issue})

        # D. 架空キャラ
        d_issues = check_fictional_canon(row)
        for issue in d_issues:
            results["categories"]["D_fictional"].append({"episode_id": ep_id, "person_name": person_name, **issue})

    # サマリー作成
    results["summary"] = {
        "A_age_year": len(results["categories"]["A_age_year"]),
        "B_name_text": len(results["categories"]["B_name_text"]),
        "C_factual": len(results["categories"]["C_factual"]),
        "D_fictional": len(results["categories"]["D_fictional"]),
        "total_issues": sum(len(v) for v in results["categories"].values()),
    }

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"episode_inconsistency_report_{timestamp}.json"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 画面出力（サマリーのみ）
    print()
    print("【検出結果サマリー】")
    print(f"  A. 年齢/年/生没年: {results['summary']['A_age_year']}件")
    print(f"  B. 名前/本文不整合: {results['summary']['B_name_text']}件")
    print(f"  C. 事実関係矛盾: {results['summary']['C_factual']}件")
    print(f"  D. 架空キャラ整合: {results['summary']['D_fictional']}件")
    print(f"  合計: {results['summary']['total_issues']}件")
    print()
    print(f"詳細レポート: {report_path}")

    # 代表例（各カテゴリ上位3件）
    print()
    print("【代表例】")
    for cat_name, cat_issues in results["categories"].items():
        if cat_issues:
            print(f"\n{cat_name}:")
            for issue in cat_issues[:3]:
                print(f"  - {issue['episode_id']} ({issue['person_name']}): {issue['type']}")
                print(f"    {issue['detail'][:60]}...")

    return results


if __name__ == "__main__":
    main()
