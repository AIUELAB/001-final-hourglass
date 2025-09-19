#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""緩和モードのテストスクリプト"""

import os
import sys
import json

# .envファイルから環境変数を読み込み
from dotenv import load_dotenv
load_dotenv()

# PDCAガーディアンのテスト
from pdca_guardian import PDCAGuardian

print("="*60)
print("🧪 PDCAガーディアン緩和モードテスト")
print("="*60)

# 通常モード
normal_guardian = PDCAGuardian(relaxed_mode=False)
print(f"通常モード基準値:")
print(f"  品質閾値: {normal_guardian.QUALITY_THRESHOLD}")
print(f"  インパクト閾値: {normal_guardian.IMPACT_THRESHOLD}")
print(f"  感動要素閾値: {normal_guardian.EMOTIONAL_THRESHOLD}")
print(f"  歴史的重要性閾値: {normal_guardian.HISTORICAL_THRESHOLD}")

print("\n" + "-"*60)

# 緩和モード
relaxed_guardian = PDCAGuardian(relaxed_mode=True)
print(f"緩和モード基準値:")
print(f"  品質閾値: {relaxed_guardian.QUALITY_THRESHOLD}")
print(f"  インパクト閾値: {relaxed_guardian.IMPACT_THRESHOLD}")
print(f"  感動要素閾値: {relaxed_guardian.EMOTIONAL_THRESHOLD}")
print(f"  歴史的重要性閾値: {relaxed_guardian.HISTORICAL_THRESHOLD}")

# テストエピソード
test_episode = """あなたと同じ25歳のとき、大谷翔平は2019年にメジャーリーグで日本人選手として史上初となる新人王を獲得。打者として打率.286、22本塁打、61打点を記録し、投手として4勝2敗、防御率3.31の二刀流での活躍が評価された。前年の怪我から復活し、野球界の常識を覆す偉業を達成した瞬間だった。"""

person_data = {
    'person_name_ja': '大谷翔平',
    'birth_year': 1994,
    'category': 'スポーツ',
    'recognition_score': 9.5
}

print("\n" + "="*60)
print("📝 テストエピソード評価")
print("="*60)
print(f"エピソード: {test_episode[:50]}...")

# 通常モードでのチェック
print("\n通常モード評価:")
normal_violations = normal_guardian.check_episode_quality(test_episode, 25, '大谷翔平')  # age=25
if normal_violations:
    print(f"  ❌ 違反: {len(normal_violations)}件")
    for v in normal_violations[:3]:  # 最初の3件のみ表示
        print(f"    - {v['type']}: {v['message'][:50]}...")
else:
    print("  ✅ 違反なし")

# 緩和モードでのチェック
print("\n緩和モード評価:")
relaxed_violations = relaxed_guardian.check_episode_quality(test_episode, 25, '大谷翔平')  # age=25
if relaxed_violations:
    print(f"  ⚠️ 違反: {len(relaxed_violations)}件")
    for v in relaxed_violations[:3]:
        print(f"    - {v['type']}: {v['message'][:50]}...")
else:
    print("  ✅ 違反なし")

print("\n" + "="*60)
print("✅ テスト完了")
print("="*60)