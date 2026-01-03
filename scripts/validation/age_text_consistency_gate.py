#!/usr/bin/env python3
"""
年齢-本文整合性ゲート

エピソード保存前に、ageフィールドと本文中の「X歳」が一致することを検証する。
不一致の場合はエラーを返し、保存をブロックする。

使用方法:
    from scripts.validation.age_text_consistency_gate import validate_age_text_consistency

    result = validate_age_text_consistency(episode_dict)
    if not result["valid"]:
        raise ValueError(result["error"])
"""

import re
from typing import Dict, Any


def validate_age_text_consistency(episode: Dict[str, Any]) -> Dict[str, Any]:
    """
    年齢フィールドと本文の年齢が一致するか検証

    Args:
        episode: エピソードデータ（age, episode_text を含む）

    Returns:
        {"valid": bool, "error": str or None}
    """
    age_str = str(episode.get("age", ""))
    text = episode.get("episode_text", "")

    if not age_str or not text:
        return {"valid": True, "error": None}

    # ageフィールドの値を取得
    try:
        field_age = int(float(age_str))
    except (ValueError, TypeError):
        return {"valid": True, "error": None}  # 年齢が数値でない場合はスキップ

    # 本文から「同じX歳」パターンを抽出
    text_age_match = re.search(r"同じ(\d+)歳", text)
    if not text_age_match:
        return {"valid": True, "error": None}  # パターンがない場合はスキップ

    text_age = int(text_age_match.group(1))

    # 比較
    if field_age != text_age:
        return {"valid": False, "error": f"年齢不一致: field_age={field_age}, text_age={text_age}"}

    return {"valid": True, "error": None}


def check_all_episodes(csv_path: str) -> list:
    """全エピソードをチェックし、不整合リストを返す"""
    import csv
    from pathlib import Path

    issues = []
    with open(Path(csv_path), "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = validate_age_text_consistency(row)
            if not result["valid"]:
                issues.append(
                    {
                        "episode_id": row.get("episode_id", ""),
                        "person_name": row.get("person_name", ""),
                        "error": result["error"],
                    }
                )
    return issues


if __name__ == "__main__":
    import sys

    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    issues = check_all_episodes(csv_path)

    print("=" * 60)
    print("年齢-本文整合性チェック")
    print("=" * 60)

    if not issues:
        print("✅ 不整合なし")
        sys.exit(0)
    else:
        print(f"❌ 不整合: {len(issues)}件")
        for issue in issues[:10]:
            print(f"  - {issue['episode_id']} ({issue['person_name']}): {issue['error']}")
        sys.exit(1)
