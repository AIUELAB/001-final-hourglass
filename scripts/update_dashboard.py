#!/usr/bin/env python3
"""
ダッシュボード更新スクリプト
最新CSVデータでepisode_database_dashboard_v2.htmlを更新
"""

import json
import re
from pathlib import Path

import pandas as pd


def load_latest_csv() -> pd.DataFrame:
    """最新のMASTER CSVを読み込み"""
    csv_files = list(Path(".").glob("MASTER_EPISODES*.csv"))
    if not csv_files:
        raise FileNotFoundError("MASTER_EPISODES*.csv が見つかりません")

    latest = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"📂 読み込み: {latest.name}")

    df = pd.read_csv(latest, encoding="utf-8-sig")
    print(f"📊 エピソード数: {len(df)}")
    return df


def convert_to_dashboard_format(df: pd.DataFrame) -> list:
    """DataFrameをダッシュボード用JSON形式に変換"""
    episodes = []

    for _, row in df.iterrows():
        episode = {
            "person_name": str(row.get("person_name", row.get("person_name_display", ""))),
            "age": int(row.get("age", 0)) if pd.notna(row.get("age")) else 0,
            "slot": int(row.get("slot", 0)) if pd.notna(row.get("slot")) else 0,
            "category": str(row.get("category", "")),
            "episode_text": str(row.get("episode_text", ""))[:500],
            "entity_type": str(row.get("person_type", row.get("entity_type", "real"))).lower(),
            "work_title": str(row.get("work_title", "")) if pd.notna(row.get("work_title")) else "",
            "episode_count": int(row.get("episode_count", 1)) if pd.notna(row.get("episode_count")) else 1,
        }
        episodes.append(episode)

    return episodes


def update_html(episodes: list, df: pd.DataFrame, html_path: str = "episode_database_dashboard_v2.html"):
    """HTMLファイルのEMBEDDED_EPISODE_DATAとheatmapDataを更新"""
    html_file = Path(html_path)

    if not html_file.exists():
        raise FileNotFoundError(f"{html_path} が見つかりません")

    content = html_file.read_text(encoding="utf-8")

    # JSON文字列を生成
    json_data = json.dumps(episodes, ensure_ascii=False, separators=(",", ":"))

    # EMBEDDED_EPISODE_DATAを置換
    pattern = r"const EMBEDDED_EPISODE_DATA = \[.*?\];"
    replacement = f"const EMBEDDED_EPISODE_DATA = {json_data};"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        raise ValueError("EMBEDDED_EPISODE_DATA が見つかりません")

    # coverage_statsを更新
    target = 22630
    total = len(episodes)
    real_count = sum(1 for e in episodes if e["entity_type"] == "real")
    fictional_count = total - real_count
    coverage_percent = round((total / target) * 100, 2)
    gap = target - total

    # overall_coverage_percentを更新
    new_content = re.sub(
        r'"overall_coverage_percent":[0-9.]+', f'"overall_coverage_percent":{coverage_percent}', new_content
    )

    # total_episodesを更新
    new_content = re.sub(r'"total_episodes":[0-9]+', f'"total_episodes":{total}', new_content)

    # gapを更新
    new_content = re.sub(r'"gap":[0-9]+', f'"gap":{gap}', new_content)

    print(f"📊 coverage_stats更新: {coverage_percent}%")

    # バックアップ作成
    backup_path = html_file.with_suffix(".html.bak")
    html_file.rename(backup_path)
    print(f"💾 バックアップ: {backup_path}")

    # 新しいHTMLを保存
    html_file.write_text(new_content, encoding="utf-8")
    print(f"✅ 更新完了: {html_path}")

    return len(episodes)


def main():
    print("=" * 50)
    print("🔄 ダッシュボード更新スクリプト")
    print("=" * 50)

    # 最新CSV読み込み
    df = load_latest_csv()

    # 変換
    episodes = convert_to_dashboard_format(df)

    # 統計表示
    real_count = sum(1 for e in episodes if e["entity_type"] == "real")
    fictional_count = len(episodes) - real_count
    target = 22630
    coverage = (len(episodes) / target) * 100

    print("\n📈 統計:")
    print(f"  総エピソード: {len(episodes):,}")
    print(f"  実在人物: {real_count:,}")
    print(f"  架空キャラ: {fictional_count:,}")
    print(f"  目標: {target:,}")
    print(f"  達成率: {coverage:.2f}%")

    # HTML更新
    update_html(episodes, df)

    print("\n🎉 ダッシュボード更新完了!")
    print("   open episode_database_dashboard_v2.html")


if __name__ == "__main__":
    main()
