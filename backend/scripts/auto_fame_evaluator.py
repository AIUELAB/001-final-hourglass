#!/usr/bin/env python3
"""
有名度自動評価スクリプト

Wikipedia APIを使用して人物の有名度を自動評価します。
- Wikipedia日本語版ページの有無
- ページビュー数による fame_tier の推定
- fame_score の自動計算
"""

import csv
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


def check_wikipedia_ja(person_name):
    """
    Wikipedia日本語版でページを検索

    Returns:
        dict: {
            'exists': bool,
            'page_title': str,
            'page_views': int,
            'fame_tier_estimate': int
        }
    """
    try:
        # User-Agentヘッダー（Wikipedia APIは必須）
        headers = {"User-Agent": "FinalHourglassBot/1.0 (https://github.com/example; example@example.com)"}

        # Wikipedia検索API
        search_url = "https://ja.wikipedia.org/w/api.php"
        search_params = {"action": "query", "list": "search", "srsearch": person_name, "format": "json", "utf8": 1}

        response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("query", {}).get("search"):
            return {"exists": False, "page_title": "", "page_views": 0, "fame_tier_estimate": 0}

        # 最初の検索結果を使用
        page_title = data["query"]["search"][0]["title"]

        # ページビュー数取得（過去30日間）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        pageviews_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ja.wikipedia/all-access/all-agents/{}/daily/{}/{}".format(
            page_title.replace(" ", "_"), start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
        )

        pv_response = requests.get(pageviews_url, headers=headers, timeout=10)

        if pv_response.status_code == 200:
            pv_data = pv_response.json()
            total_views = sum(item["views"] for item in pv_data.get("items", []))

            # ページビュー数から fame_tier を推定
            # 月間10,000ビュー以上 → Tier 5（世界的）
            # 月間5,000-9,999 → Tier 4（全国的）
            # 月間1,000-4,999 → Tier 3（地域的）
            # 月間100-999 → Tier 2（専門的）
            # 月間100未満 → Tier 1（限定的）

            if total_views >= 10000:
                fame_tier = 5
            elif total_views >= 5000:
                fame_tier = 4
            elif total_views >= 1000:
                fame_tier = 3
            elif total_views >= 100:
                fame_tier = 2
            else:
                fame_tier = 1
        else:
            total_views = 0
            fame_tier = 1  # ページは存在するがビュー数不明

        return {"exists": True, "page_title": page_title, "page_views": total_views, "fame_tier_estimate": fame_tier}

    except Exception as e:
        print(f"⚠️  Wikipedia検索エラー [{person_name}]: {e}", file=sys.stderr)
        return {"exists": False, "page_title": "", "page_views": 0, "fame_tier_estimate": 0}


def calculate_fame_score(row):
    """
    有名度スコア計算

    Args:
        row: CSVレコード（辞書）

    Returns:
        int: 有名度スコア（0-100）
    """
    score = 0

    # fame_tier（基礎点）: 0-50点
    fame_tier = int(row.get("fame_tier", 0))
    score += fame_tier * 10

    # Wikipedia日本語版（+20点）
    if row.get("wikipedia_ja", "").upper() == "TRUE":
        score += 20

    # 教科書掲載（+15点）
    if row.get("textbook", "").upper() == "TRUE":
        score += 15

    # 受賞レベル（+0〜15点）
    award_level = int(row.get("award_level", 0))
    score += award_level * 5

    # 悪名度（-5点）
    if row.get("notoriety", "").upper() == "TRUE":
        score -= 5

    return min(max(score, 0), 100)


def auto_evaluate_fame(csv_path, output_path=None, limit=None, start_index=0):
    """
    CSVファイルの有名度を自動評価

    Args:
        csv_path: 入力CSVパス
        output_path: 出力CSVパス（Noneの場合は上書き）
        limit: 処理件数制限（テスト用）
        start_index: 開始インデックス（バッチ処理用）
    """
    if output_path is None:
        output_path = csv_path

    # CSVを読み込み
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    total = len(rows)
    print(f"📋 総レコード数: {total}件")

    if limit:
        end_index = min(start_index + limit, total)
        print(f"📊 処理範囲: {start_index+1}件目 〜 {end_index}件目")
    else:
        end_index = total
        print("📊 全件処理")

    evaluated_count = 0
    updated_count = 0

    for i in range(start_index, end_index):
        row = rows[i]
        person_name = row.get("person_name", "")

        if not person_name:
            continue

        # 既に評価済み（fame_tier > 0）の場合はスキップ
        current_fame_tier = int(row.get("fame_tier", 0))
        if current_fame_tier > 0:
            print(f"⏭️  [{i+1}/{total}] {person_name}: 既に評価済み (Tier {current_fame_tier})")
            continue

        print(f"🔍 [{i+1}/{total}] {person_name} を評価中...", end="", flush=True)

        # Wikipedia検索
        wiki_info = check_wikipedia_ja(person_name)

        if wiki_info["exists"]:
            row["wikipedia_ja"] = "TRUE"
            row["fame_tier"] = str(wiki_info["fame_tier_estimate"])

            print(f" ✅ Wikipedia発見！ Tier {wiki_info['fame_tier_estimate']} (月間{wiki_info['page_views']:,}ビュー)")
            updated_count += 1
        else:
            # Wikipediaページがない場合、デフォルト値
            row["wikipedia_ja"] = "FALSE"
            # fame_tierは0のまま（または最低限のTier 1）
            # row['fame_tier'] = '1'

            print(" ⚪ Wikipediaなし")

        # fame_scoreを再計算
        row["fame_score"] = str(calculate_fame_score(row))
        row["fame_score_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        evaluated_count += 1

        # API制限対策（1秒あたり1リクエスト）
        time.sleep(1)

    # CSV書き出し
    print(f"\n💾 {output_path} に保存中...")

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("✅ 評価完了！")
    print(f"   - 評価件数: {evaluated_count}件")
    print(f"   - 更新件数: {updated_count}件（Wikipediaページ発見）")
    print(f"   - 保存先: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="有名度自動評価スクリプト")
    parser.add_argument("--input", default="MASTER_EPISODES_CURRENT.csv", help="入力CSVファイル")
    parser.add_argument("--output", help="出力CSVファイル（省略時は入力ファイルを上書き）")
    parser.add_argument("--limit", type=int, help="処理件数制限（テスト用）")
    parser.add_argument("--start", type=int, default=0, help="開始インデックス（バッチ処理用）")

    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    auto_evaluate_fame(csv_path=csv_path, output_path=args.output, limit=args.limit, start_index=args.start)
