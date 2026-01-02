#!/usr/bin/env python3
"""
エピソード本文の人物名不整合検出スクリプト

目的: person_name と episode_text 冒頭の人物名の不整合を検出
"""

import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def extract_name_from_text(episode_text: str, person_name: str = "") -> str | None:
    """本文冒頭から人物名を抽出"""
    # 優先: person_nameで始まるパターン
    if person_name:
        # 架空キャラ『作品名』形式
        fictional_pattern = rf"^あなたと同じ[\d.]+歳のとき、{re.escape(person_name)}『.+?』は"
        if re.match(fictional_pattern, episode_text):
            match = re.match(r"^あなたと同じ[\d.]+歳のとき、(.+?)は", episode_text)
            if match:
                return match.group(1)
        # 通常形式
        normal_pattern = rf"^あなたと同じ[\d.]+歳のとき、{re.escape(person_name)}は"
        if re.match(normal_pattern, episode_text):
            return person_name

    # フォールバック: 最初の「は」で区切る（ただし『』内は無視）
    # 架空キャラ形式をまず試す
    fictional_match = re.match(r"^あなたと同じ[\d.]+歳のとき、(.+?『.+?』)は", episode_text)
    if fictional_match:
        return fictional_match.group(1)

    # 通常形式
    pattern = r"^あなたと同じ[\d.]+歳のとき、(.+?)は"
    match = re.match(pattern, episode_text)
    if match:
        return match.group(1)
    return None


def classify_mismatch(person_name: str, text_name: str) -> str:
    """不整合のタイプを分類"""
    # ASCII文字のみ = 英語名
    if text_name.isascii():
        return "英語名混入"

    # 半角英数が含まれる
    if re.search(r"[A-Za-z]", text_name):
        return "英語混在"

    # 括弧表記
    if "(" in text_name or "（" in text_name:
        return "括弧表記"

    # 旧字体チェック（簡易）
    old_chars = "國學會髙濱邊邉齋齊澤澁"
    if any(c in text_name for c in old_chars):
        return "旧字体"

    # かな/カナ違い
    if set(person_name) - set(text_name):
        # ひらがな/カタカナの違いをチェック
        return "表記ゆれ"

    return "その他"


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
    report_dir = Path("src/reports/logs")
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_report_path = report_dir / f"name_mismatch_detail_{timestamp}.csv"

    mismatches = []
    type_counts = defaultdict(int)
    total = 0
    no_pattern = 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")
            episode_text = row.get("episode_text", "")
            name_raw = row.get("name_raw", "")

            text_name = extract_name_from_text(episode_text, person_name)

            if text_name is None:
                no_pattern += 1
                continue

            # 架空キャラ『作品名』形式は正常とみなす
            text_name_clean = re.sub(r"『.+?』$", "", text_name)

            # 不整合チェック
            if text_name_clean != person_name:
                mismatch_type = classify_mismatch(person_name, text_name)
                type_counts[mismatch_type] += 1
                mismatches.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "text_name": text_name,
                        "name_raw": name_raw,
                        "mismatch_type": mismatch_type,
                        "episode_text_head": episode_text[:100] if episode_text else "",
                    }
                )

    # 詳細レポート出力
    with open(detail_report_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["episode_id", "person_name", "text_name", "name_raw", "mismatch_type", "episode_text_head"]
        )
        writer.writeheader()
        writer.writerows(mismatches)

    # サマリー出力
    print("=" * 60)
    print("【ドライラン結果】エピソード本文の人物名不整合検出")
    print("=" * 60)
    print(f"総エピソード数: {total:,}")
    print(f"パターン不一致（抽出不可）: {no_pattern:,}")
    print(f"★ 不整合件数: {len(mismatches):,}")
    print()
    print("【不整合タイプ別内訳】")
    for mtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {mtype}: {count:,}件")
    print()
    print("【代表例（最大10件）】")
    for i, m in enumerate(mismatches[:10]):
        print(f"  {i+1}. {m['episode_id']}")
        print(f"     名前フィールド: {m['person_name']}")
        print(f"     本文冒頭名: {m['text_name']}")
        print(f"     name_raw: {m['name_raw']}")
        print(f"     タイプ: {m['mismatch_type']}")
        print()

    print(f"詳細レポート: {detail_report_path}")

    return len(mismatches)


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
