#!/usr/bin/env python3
"""
UNKNOWN違反の詳細分析
"""

from pdca_guardian import PDCAGuardian
import pandas as pd

# サンプルエピソードで詳細分析
guardian = PDCAGuardian()

# CSVから一つ目のエピソードを取得
df = pd.read_csv('ultra_think_improved_20250922_063204.csv', encoding='utf-8-sig')
row = df.iloc[0]

person_name = row['person_name']
age = row['episode_age']
episode = row.get('episode_improved', row['episode_text'])
person_name_display = f"{person_name}（{age}歳）"

print("分析対象エピソード:")
print(f"人物: {person_name_display}")
print(f"エピソード: {episode[:100]}...")
print("\n" + "="*60)
print("違反詳細:")
print("="*60)

violations = guardian.check_episode_quality(
    episode_text=episode,
    age=age,
    person_name_display=person_name_display
)

for i, v in enumerate(violations, 1):
    print(f"\n違反{i}:")
    print(f"  ルール: {v.get('rule_id', 'UNKNOWN')}")
    print(f"  タイプ: {v.get('type', 'UNKNOWN')}")
    print(f"  メッセージ: {v.get('message', '')[:100]}")

    # UNKNOWNタイプの場合、詳細を調査
    if v.get('type') == 'FORMAT_ERROR' or v.get('rule_id') == 'UNKNOWN':
        print(f"  ⚠️ 要調査: この違反タイプはルールIDが不明です")