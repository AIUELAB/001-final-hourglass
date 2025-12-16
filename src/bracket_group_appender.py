#!/usr/bin/env python3
"""
グループ名括弧追記モジュール

グループ所属人物のエピソードリード文に「（グループ名）」を追記する機能を提供。

Usage:
    from src.bracket_group_appender import should_append_group, append_group_bracket_to_lead

    if should_append_group(person_name, group_name, episode_text, person_type, is_group_member):
        new_text = append_group_bracket_to_lead(episode_text, person_name, group_name)
"""

import re
from typing import Optional, Tuple

from src.group_master import SOLO_ARTISTS


def should_append_group(
    person_name: str,
    group_name: str,
    episode_text: str,
    person_type: str,
    is_group_member: str,
    fame_tier: Optional[str] = None,
    fame_score: Optional[float] = None,
) -> Tuple[bool, str]:
    """
    グループ名を追記すべきか判定

    Args:
        person_name: 人物名
        group_name: グループ名
        episode_text: エピソード本文
        person_type: 人物種別（REAL/FICTIONAL）
        is_group_member: グループ所属フラグ（True/False文字列）
        fame_tier: 知名度ティア（未使用）
        fame_score: 知名度スコア（未使用）

    Returns:
        (追記すべきか, スキップ理由)
        - (True, ""): 追記すべき
        - (False, "skip_reason"): スキップすべき（理由付き）

    判定フロー：
        1. person_type != "REAL" → False, "person_type_not_real"
        2. is_group_member != "True" → False, "not_group_member"
        3. group_name が空/未登録/nan → False, "no_group_name"
        4. person_name が SOLO_ARTISTS に含まれる → False, "solo_artist"
        5. リード文に既に括弧が含まれる → False, "already_has_bracket"
        6. episode_text に group_name が含まれる → False, "group_name_in_text"
        7. デフォルト → True, ""
    """
    # 1. 基本条件チェック
    if person_type != "REAL":
        return False, "person_type_not_real"

    if str(is_group_member) != "True":
        return False, "not_group_member"

    if not group_name or str(group_name).lower() in ("", "nan", "未登録", "none"):
        return False, "no_group_name"

    # 2. 明示的無所属チェック（SOLO_ARTISTS）
    if person_name in SOLO_ARTISTS:
        return False, "solo_artist"

    # 3. 既存括弧チェック（全角・半角両方）
    # リード文形式: あなたと同じ{age}歳のとき、{person_name}は
    lead_pattern = re.compile(r"^あなたと同じ\d+歳のとき、.+?[（(].+?[）)]は")
    if lead_pattern.match(episode_text):
        return False, "already_has_bracket"

    # 4. 本文重複チェック
    if group_name in episode_text:
        return False, "group_name_in_text"

    # 5. デフォルト: 追記する
    return True, ""


def append_group_bracket_to_lead(
    episode_text: str,
    person_name: str,
    group_name: str,
) -> str:
    """
    エピソードリード文にグループ名を括弧で追記

    Args:
        episode_text: エピソード本文
        person_name: 人物名
        group_name: グループ名

    Returns:
        括弧を追記した新しいエピソード本文

    変換例：
        Before: あなたと同じ27歳のとき、桜井和寿は音楽活動を...
        After:  あなたと同じ27歳のとき、桜井和寿（Mr.Children）は音楽活動を...

    Raises:
        ValueError: リード文のパターンが想定外の場合
    """
    # リード文パターン: あなたと同じ{age}歳のとき、{person_name}は
    lead_pattern = re.compile(r"^(あなたと同じ\d+歳のとき、)(.+?)(は.*)$", re.DOTALL)

    match = lead_pattern.match(episode_text)
    if not match:
        raise ValueError(f"リード文のパターンが想定外です: {episode_text[:100]}...")

    prefix = match.group(1)  # あなたと同じ27歳のとき、
    name_part = match.group(2)  # 桜井和寿
    rest = match.group(3)  # は音楽活動を...

    # 人物名が一致するか確認（安全性チェック）
    if person_name not in name_part:
        raise ValueError(f"人物名が一致しません: expected={person_name}, found={name_part}")

    # 全角括弧でグループ名を追記
    new_text = f"{prefix}{name_part}（{group_name}）{rest}"

    return new_text


def validate_appended_text(original: str, appended: str, group_name: str) -> bool:
    """
    追記後のテキストが正しいか検証

    Args:
        original: 元のテキスト
        appended: 追記後のテキスト
        group_name: 追記したグループ名

    Returns:
        検証成功ならTrue
    """
    # 1. グループ名が含まれているか
    if f"（{group_name}）" not in appended:
        return False

    # 2. 元のテキストの内容が保持されているか（括弧部分以外）
    # 簡易チェック: 長さの増加が妥当か
    expected_increase = len(f"（{group_name}）")
    actual_increase = len(appended) - len(original)

    if actual_increase != expected_increase:
        return False

    # 3. リード文パターンが維持されているか
    lead_pattern = re.compile(r"^あなたと同じ\d+歳のとき、.+?（.+?）は")
    if not lead_pattern.match(appended):
        return False

    return True


if __name__ == "__main__":
    # 簡易テスト
    test_cases = [
        {
            "person_name": "桜井和寿",
            "group_name": "Mr.Children",
            "episode_text": "あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。",
            "person_type": "REAL",
            "is_group_member": "True",
            "expected_should": True,
        },
        {
            "person_name": "宇多田ヒカル",
            "group_name": "",
            "episode_text": "あなたと同じ20歳のとき、宇多田ヒカルはアルバムを発表しました。",
            "person_type": "REAL",
            "is_group_member": "False",
            "expected_should": False,
        },
    ]

    print("=== bracket_group_appender.py 簡易テスト ===\n")

    for i, case in enumerate(test_cases, 1):
        person_name = str(case["person_name"])
        group_name = str(case["group_name"])
        episode_text = str(case["episode_text"])
        person_type = str(case["person_type"])
        is_group_member = str(case["is_group_member"])

        print(f"Test {i}: {person_name}")

        should, reason = should_append_group(
            person_name,
            group_name,
            episode_text,
            person_type,
            is_group_member,
        )

        print(f"  判定: {should} (理由: {reason or 'N/A'})")
        print(f"  期待: {case['expected_should']}")

        if should:
            try:
                new_text = append_group_bracket_to_lead(
                    episode_text,
                    person_name,
                    group_name,
                )
                print(f"  変換後: {new_text[:80]}...")

                is_valid = validate_appended_text(
                    episode_text,
                    new_text,
                    group_name,
                )
                print(f"  検証: {'✅ OK' if is_valid else '❌ NG'}")
            except Exception as e:
                print(f"  エラー: {e}")

        print()

    print("✅ 簡易テスト完了")
