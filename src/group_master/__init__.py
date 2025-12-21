#!/usr/bin/env python3
"""
グループ所属判定モジュール

人物名からグループ所属を判定し、group_name と is_group_member を返す。

フォーマット仕様:
- 所属: is_group_member=True, group_name=グループ名
- 無所属: is_group_member=False, group_name=None
- 未判定: is_group_member=None, group_name=None

使用例:
    >>> from src.group_master import get_group_info, is_group_entity
    >>> group_name, is_member = get_group_info("桜井和寿", "REAL")
    >>> print(f"{group_name=}, {is_member=}")
    group_name='Mr.Children', is_member=True
"""

# エンティティ定義
from .entities import (
    GROUP_DETAILS,
    GROUP_ENTITIES,
    SOLO_ARTISTS,
    GroupCategory,
    GroupInfo,
)

# メンバーマップ・関数
from .members import (
    GROUP_MEMBER_MAP,
    get_group_info,
    get_group_members,
    get_statistics,
    is_group_entity,
    is_solo_artist,
)

# 分散ルール
from .dispersion import (
    DISPERSION_RULES,
    DispersionRule,
    DispersionStrategy,
    get_dispersion_rule,
    get_group_details,
)

__all__ = [
    # Classes
    "GroupCategory",
    "GroupInfo",
    "DispersionStrategy",
    "DispersionRule",
    # Constants
    "GROUP_MEMBER_MAP",
    "GROUP_ENTITIES",
    "SOLO_ARTISTS",
    "GROUP_DETAILS",
    "DISPERSION_RULES",
    # Functions
    "get_group_info",
    "get_group_details",
    "get_group_members",
    "is_solo_artist",
    "is_group_entity",
    "get_statistics",
    "get_dispersion_rule",
]


if __name__ == "__main__":
    # テスト
    print("=" * 60)
    print("グループマスタ統計")
    print("=" * 60)

    stats = get_statistics()
    print(f"登録メンバー数: {stats['total_members']}")
    print(f"ユニークグループ数: {stats['unique_groups']}")
    print(f"グループエンティティ数: {stats['group_entities']}")
    print(f"ソロアーティスト数: {stats['solo_artists']}")

    print("\n" + "=" * 60)
    print("グループ判定テスト")
    print("=" * 60)

    test_cases = [
        ("桜井和寿", "REAL"),
        ("松本人志", "REAL"),
        ("大野智", "REAL"),
        ("宇多田ヒカル", "REAL"),
        ("毛利蘭", "FICTIONAL"),
        ("嵐", "REAL"),  # グループ本体
        ("田中太郎", "REAL"),  # 未登録
    ]

    for name, ptype in test_cases:
        group_name, is_member = get_group_info(name, ptype)
        if is_member is True:
            status = f"所属 → {group_name}"
        elif is_member is False:
            status = "無所属"
        else:
            status = "未判定"
        print(f"  {name} ({ptype}): {status}")
