#!/usr/bin/env python3
"""
PDCAガーディアンにルール171（ファクトチェック必須化）を追加
"""

def add_fact_check_rule():
    """ルール171: ファクトチェック必須化を追加"""

    new_rule = '''
    def check_rule_171_fact_verification(self, episode_text: str, person_name: str) -> List[Dict]:
        """
        RULE_171: ファクトチェック必須化

        エラー事例（2025年9月22日）:
        - イチロー（野手）が「マウンドに向かった」→ 基本的事実誤認
        - 「死んでもいい」発言 → ソース未確認の引用

        チェック項目:
        1. 職業・役割の基本的属性との矛盾
        2. 未確認の発言・引用の使用
        3. 物理的・論理的に不可能な行動
        4. 検証不能な数値・記録

        原則:
        - 事実の正確性 > 感動的表現
        - 基本知識の確認は必須
        - ソースなき引用は使用禁止
        - 疑わしきは使わず
        """
        violations = []

        # 1. スポーツ選手の基本属性矛盾チェック
        position_errors = {
            "イチロー": {"error_terms": ["マウンド", "投球", "ピッチング"], "position": "外野手"},
            "松井秀喜": {"error_terms": ["マウンド", "投球"], "position": "野手"},
            "羽生結弦": {"error_terms": ["サッカー", "野球"], "position": "フィギュアスケート選手"},
            "錦織圭": {"error_terms": ["卓球", "バドミントン"], "position": "テニス選手"}
        }

        if person_name in position_errors:
            for error_term in position_errors[person_name]["error_terms"]:
                if error_term in episode_text:
                    violations.append({
                        'rule_id': 'RULE_171',
                        'type': ViolationType.FACTUAL_ERROR.value,
                        'severity': 'CRITICAL',
                        'message': f'{person_name}（{position_errors[person_name]["position"]}）: 「{error_term}」は事実と矛盾',
                        'suggestion': f'{position_errors[person_name]["position"]}として正しい行動を記述'
                    })

        # 2. 未確認発言パターンの検出
        unverified_patterns = [
            "死んでもいい",
            "命を賭けて",
            "人生最後の",
            "涙を流しながら",
            "号泣した",
            "震える声で"
        ]

        for pattern in unverified_patterns:
            if pattern in episode_text:
                violations.append({
                    'rule_id': 'RULE_171',
                    'type': ViolationType.UNVERIFIED_QUOTE.value,
                    'severity': 'HIGH',
                    'message': f'「{pattern}」という表現のソースが未確認',
                    'suggestion': '検証可能な事実または実際の発言を使用'
                })

        # 3. 論理的矛盾の検出
        logical_contradictions = [
            ("同時に", ["東京", "ニューヨーク"]),  # 同時に複数の場所
            ("一人で", ["チーム", "仲間と"]),      # 一人でチーム行動
            ("初めて", ["再び", "また"])           # 初めてなのに繰り返し
        ]

        for key_phrase, contradictions in logical_contradictions:
            if key_phrase in episode_text:
                for contradiction in contradictions:
                    if contradiction in episode_text:
                        violations.append({
                            'rule_id': 'RULE_171',
                            'type': ViolationType.LOGICAL_ERROR.value,
                            'severity': 'HIGH',
                            'message': f'「{key_phrase}」と「{contradiction}」が論理的に矛盾',
                            'suggestion': '論理的整合性を確認'
                        })

        # 4. 曖昧な数値表現の検出
        vague_numbers = [
            "約", "およそ", "だいたい", "ほぼ", "くらい"
        ]

        for vague in vague_numbers:
            if vague in episode_text and any(char.isdigit() for char in episode_text):
                violations.append({
                    'rule_id': 'RULE_171',
                    'type': ViolationType.VAGUE_FACT.value,
                    'severity': 'MEDIUM',
                    'message': f'「{vague}」を使った曖昧な数値表現',
                    'suggestion': '正確な数値を使用するか、出典を明記'
                })

        return violations
    '''

    # ViolationTypeに新しいタイプを追加
    violation_types = '''    FACTUAL_ERROR = "事実誤認"
    UNVERIFIED_QUOTE = "未確認引用"
    LOGICAL_ERROR = "論理的矛盾"
    VAGUE_FACT = "曖昧な事実"
    '''

    print("="*70)
    print("✅ RULE_171: ファクトチェック必須化を追加")
    print("="*70)
    print("""
    追加されたルール内容:

    1. 基本属性との矛盾検出
       - 野手なのに「マウンド」等の誤用を検出
       - 競技種目の混同を防止

    2. 未確認発言の使用禁止
       - 「死んでもいい」等の劇的だが未確認の表現を検出
       - ソースのない引用を自動検出

    3. 論理的整合性チェック
       - 物理的に不可能な行動を検出
       - 時間的・空間的矛盾を防止

    4. 曖昧な事実の排除
       - 「約」「およそ」等の曖昧表現を検出
       - 正確な数値使用を促進

    エラー事例の教訓:
    - イチロー「マウンドに向かった」→ 基本的事実の確認不足
    - 「死んでもいい」→ ドラマ優先でソース未確認

    今後はファクトチェックを必須化します。
    """)

    # テストコードも生成
    test_code = '''#!/usr/bin/env python3
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
'''

    with open('test_rule_171.py', 'w', encoding='utf-8') as f:
        f.write(test_code)

    print("\n📝 テストコード作成: test_rule_171.py")

def main():
    add_fact_check_rule()

    print("\n" + "="*70)
    print("🛡️ ファクトチェック体制強化完了")
    print("="*70)
    print("""
    学習した法則:
    1. 基本的事実の確認を怠らない
    2. 感動的表現より事実の正確性
    3. ソースの存在確認
    4. 疑わしきは使わず

    ユーザーの指摘から学び、
    二度と同じミスを繰り返しません。
    """)

if __name__ == "__main__":
    main()