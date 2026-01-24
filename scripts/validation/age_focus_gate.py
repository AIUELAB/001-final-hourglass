#!/usr/bin/env python3
"""
年齢集中度ゲート

エピソード保存前に、本文がフィールド年齢の出来事に集中しているか検証する。
他年齢への言及が多すぎる場合はブロック/警告する。

使用方法:
    from scripts.validation.age_focus_gate import validate_age_focus

    result = validate_age_focus(episode_dict)
    if not result["valid"]:
        print(f"警告: {result['warning']}")
"""

import re
from typing import Any


def validate_age_focus(episode: dict[str, Any]) -> dict[str, Any]:
    """
    年齢集中度を検証

    Args:
        episode: エピソードデータ（age, episode_text を含む）

    Returns:
        {
            "valid": bool,
            "warning": str or None,
            "other_ages": list[int],
            "deviation": int (最大年齢差)
        }
    """
    age_str = str(episode.get("age", ""))
    text = episode.get("episode_text", "")

    if not age_str or not text:
        return {"valid": True, "warning": None, "other_ages": [], "deviation": 0}

    # フィールド年齢を取得
    try:
        field_age = int(float(age_str))
    except (ValueError, TypeError):
        return {"valid": True, "warning": None, "other_ages": [], "deviation": 0}

    # 本文中の年齢言及を抽出
    ages_in_text = re.findall(r"(\d+)歳", text)
    ages_int = [int(a) for a in ages_in_text]

    # フィールド年齢から大きく離れた年齢を検出（5歳以上の差）
    other_ages = [a for a in ages_int if abs(a - field_age) > 5]

    if not other_ages:
        return {"valid": True, "warning": None, "other_ages": [], "deviation": 0}

    # 最大偏差を計算
    max_deviation = max(abs(a - field_age) for a in other_ages)

    # 文を分割して他年齢言及の割合を計算
    sentences = re.split(r"[。！？]", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    other_age_sentence_count = 0
    for sentence in sentences:
        ages_in_sentence = [int(a) for a in re.findall(r"(\d+)歳", sentence)]
        if any(abs(a - field_age) > 5 for a in ages_in_sentence):
            other_age_sentence_count += 1

    other_age_ratio = other_age_sentence_count / len(sentences) if sentences else 0

    # 判定
    # Critical: 年齢差20歳以上 かつ 他年齢言及30%以上 → ブロック
    # Warning: 年齢差10歳以上 かつ 他年齢言及20%以上 → 警告
    if max_deviation >= 20 and other_age_ratio >= 0.3:
        return {
            "valid": False,
            "warning": f"年齢集中度不足: field_age={field_age}, other_ages={sorted(set(other_ages))}, ratio={other_age_ratio:.1%}",
            "other_ages": sorted(set(other_ages)),
            "deviation": max_deviation,
        }
    elif max_deviation >= 10 and other_age_ratio >= 0.2:
        return {
            "valid": True,  # 警告だがブロックしない
            "warning": f"他年齢言及多め: field_age={field_age}, other_ages={sorted(set(other_ages))}, ratio={other_age_ratio:.1%}",
            "other_ages": sorted(set(other_ages)),
            "deviation": max_deviation,
        }

    return {"valid": True, "warning": None, "other_ages": sorted(set(other_ages)), "deviation": max_deviation}


def check_all_episodes(csv_path: str) -> list:
    """全エピソードをチェックし、問題リストを返す"""
    import csv
    from pathlib import Path

    issues = []
    with open(Path(csv_path), "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = validate_age_focus(row)
            if result["warning"]:
                issues.append(
                    {
                        "episode_id": row.get("episode_id", ""),
                        "person_name": row.get("person_name", ""),
                        "field_age": row.get("age", ""),
                        "valid": result["valid"],
                        "warning": result["warning"],
                        "other_ages": result["other_ages"],
                        "deviation": result["deviation"],
                    }
                )
    return issues


if __name__ == "__main__":
    import sys

    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    issues = check_all_episodes(csv_path)

    blocked = [i for i in issues if not i["valid"]]
    warned = [i for i in issues if i["valid"] and i["warning"]]

    print("=" * 60)
    print("年齢集中度チェック")
    print("=" * 60)
    print(f"ブロック対象: {len(blocked)}件")
    print(f"警告対象: {len(warned)}件")

    if blocked:
        print("\n【ブロック対象】")
        for i in blocked[:10]:
            print(f"  {i['episode_id']} ({i['person_name']}, {i['field_age']}歳)")
            print(f"    {i['warning']}")

    if warned:
        print("\n【警告対象（上位10件）】")
        for i in sorted(warned, key=lambda x: -x["deviation"])[:10]:
            print(f"  {i['episode_id']} ({i['person_name']}, {i['field_age']}歳)")
            print(f"    {i['warning']}")

    sys.exit(1 if blocked else 0)
