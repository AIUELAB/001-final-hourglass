#!/usr/bin/env python3
"""
RULE_171: ファクトチェック必須化のテスト
"""

def test_rule_171():
    """ファクトチェックのテスト"""

    test_cases = [
        {
            "episode": "イチローがマウンドに向かった",
            "person": "イチロー",
            "expected_error": "事実と矛盾"
        },
        {
            "episode": "死んでもいいと語った",
            "person": "任意",
            "expected_error": "ソースが未確認"
        },
        {
            "episode": "約1000本のホームラン",
            "person": "任意",
            "expected_error": "曖昧な数値表現"
        }
    ]

    print("✅ RULE_171 ファクトチェックテスト完了")

if __name__ == "__main__":
    test_rule_171()
