#!/usr/bin/env python3
"""フォーマットチェックのデバッグ"""

from pdca_guardian import PDCAGuardian

guardian = PDCAGuardian()

# テストケース
age = 23
person_name_display = "大谷翔平"
episode_text = "あなたと同じ23歳のとき、大谷翔平は2018年4月1日、エンゼルス対アスレチックス戦で、メジャーリーグ移籍後初本塁打を放つ。"

# 標準フォーマット
standard_prefix = f"あなたと同じ{age}歳のとき、{person_name_display}は"

print(f"期待される開始: '{standard_prefix}'")
print(f"実際の開始: '{episode_text[:len(standard_prefix)]}'")
print(f"完全一致: {episode_text.startswith(standard_prefix)}")

# 文字コード確認
print(f"\n期待される文字コード: {[ord(c) for c in standard_prefix[:10]]}")
print(f"実際の文字コード: {[ord(c) for c in episode_text[:10]]}")

# PDCAガーディアンでチェック
violations = guardian.check_episode_quality(episode_text, age, person_name_display)
print(f"\n違反数: {len(violations)}")
if violations:
    print("違反内容:")
    for v in violations[:3]:
        print(f"  - {v.get('message', '')}")