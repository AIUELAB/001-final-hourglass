#!/usr/bin/env python3
"""
RULE_170: ユーザー指示優先原則のテスト
"""

from pdca_guardian import PDCAGuardian

def test_rule_170():
    """ユーザー指示優先のテスト"""

    guardian = PDCAGuardian()

    # テストケース1: 年齢指定違反
    guardian.current_user_instruction = "38歳のノルウェイの森で"

    # 間違った実装（30歳、風の歌を聴け）
    wrong_episode = "30歳のとき、風の歌を聴けで受賞"
    violations = guardian.check_episode_quality(
        wrong_episode, 30, "村上春樹（30歳）"
    )

    user_violations = [v for v in violations if v['rule_id'] == 'RULE_170']
    assert len(user_violations) > 0, "年齢指定違反が検出されるべき"

    # テストケース2: キーワード欠落
    guardian.current_user_instruction = "WBCでトラウトと対決"

    # トラウトが含まれない
    wrong_episode = "29歳のとき、WBCで優勝した"
    violations = guardian.check_episode_quality(
        wrong_episode, 29, "大谷翔平（29歳）"
    )

    keyword_violations = [v for v in violations
                         if v['rule_id'] == 'RULE_170'
                         and 'トラウト' in v['message']]
    assert len(keyword_violations) > 0, "キーワード欠落が検出されるべき"

    print("✅ RULE_170 テスト成功")

if __name__ == "__main__":
    test_rule_170()
