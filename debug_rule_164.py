#!/usr/bin/env python3
"""
RULE_164のデバッグテスト
"""

import re

# テストエピソード
test_episode = "あなたと同じ23歳のとき、大谷翔平は2018年4月1日、エンゼルス対アスレチックス戦で、メジャーリーグ移籍後初本塁打を放つ。"

# RULE_164のパターン
date_patterns = [
    (r'\d{4}年\d{1,2}月\d{1,2}日', '年月日'),
    (r'\d{1,2}月\d{1,2}日', '月日'),
    (r'\d{4}年\d{1,2}月(?!\d)', '年月'),
    (r'午前\d+時', '時刻'),
    (r'午後\d+時', '時刻'),
    (r'\d+時\d+分', '時分')
]

print("RULE_164 パターンマッチテスト")
print("=" * 60)
print(f"テストエピソード: {test_episode}")
print()

for pattern, pattern_type in date_patterns:
    matches = re.findall(pattern, test_episode)
    if matches:
        print(f"✅ パターン「{pattern_type}」にマッチ: {matches}")
    else:
        print(f"❌ パターン「{pattern_type}」にマッチせず")

# PDCAガーディアンをインポートして確認
print("\n" + "=" * 60)
print("PDCAガーディアン内でのRULE_164実装確認:")

from pdca_guardian import PDCAGuardian

guardian = PDCAGuardian()

# PDCAガーディアンのメソッド内容を確認
import inspect
source = inspect.getsource(guardian.check_episode_quality)

# RULE_164が含まれているか確認
if "RULE_164" in source:
    print("✅ RULE_164がcheck_episode_qualityメソッドに実装されています")
    # 該当部分を表示
    lines = source.split('\n')
    rule_164_start = None
    for i, line in enumerate(lines):
        if 'RULE_164' in line:
            rule_164_start = i
            break

    if rule_164_start:
        print("\n実装部分:")
        for i in range(max(0, rule_164_start - 2), min(len(lines), rule_164_start + 15)):
            print(f"  {lines[i]}")
else:
    print("❌ RULE_164がcheck_episode_qualityメソッドに実装されていません")