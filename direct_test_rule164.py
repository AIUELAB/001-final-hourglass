#!/usr/bin/env python3
"""
RULE_164の直接テスト
"""

import sys
import importlib

# モジュールを強制的に再読み込み
if 'pdca_guardian' in sys.modules:
    importlib.reload(sys.modules['pdca_guardian'])

from pdca_guardian import PDCAGuardian

# テスト用エピソード
test_episode = "あなたと同じ23歳のとき、大谷翔平は2018年4月1日、エンゼルス対アスレチックス戦で、メジャーリーグ移籍後初本塁打を放つ。"

# PDCAガーディアンで検証
guardian = PDCAGuardian()
violations = guardian.check_episode_quality(
    episode_text=test_episode,
    age=23,
    person_name_display="大谷翔平"
)

print("RULE_164 動作確認")
print("=" * 60)
print(f"テストエピソード: {test_episode[:50]}...")
print()
print("検出された違反:")
for v in violations:
    if 'rule_id' in v and v['rule_id'] == 'RULE_164':
        print(f"✅ RULE_164検出: {v['message']}")
        break
else:
    # デバッグ: ソースコードを確認
    import inspect
    source = inspect.getsource(guardian.check_episode_quality)
    if 'RULE_164' in source:
        print("❌ RULE_164はソースに存在するが、検出されず")
        print("\n全違反内容:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("❌ RULE_164がメソッドに実装されていません")
