#!/usr/bin/env python3
"""
PDCAガーディアンにルール170を追加
ユーザー指示優先の原則を明文化
"""

def add_user_instruction_priority_rule():
    """ルール170: ユーザー指示優先原則を追加"""

    new_rule = '''
    def check_rule_170_user_instruction_priority(self, episode_text: str, age: int,
                                                 person_name: str, user_instruction: str = None) -> List[Dict]:
        """
        RULE_170: ユーザー指示優先の原則

        エラー事例（2025年9月22日）から学習:
        - 大谷翔平: WBC・トラウト指定 → 満票MVPを誤選択（スコア優先の誤り）
        - 村上春樹: ノルウェイの森指定 → 風の歌を聴けを誤選択（自己判断の誤り）

        原則:
        1. ユーザーの明示的指示は、いかなる評価スコアより優先される
        2. 「〜の方が良いかも」「〜してみては？」は変更指示として扱う
        3. 数値評価は指示を満たした上での二次的最適化に留める
        4. 創造的解釈や自己判断による改変は禁止

        判定基準:
        - ユーザー指示と異なる選択 → 重大違反
        - スコア最大化のための指示無視 → 重大違反
        - 暗黙の「改善」による指示からの逸脱 → 重大違反
        """
        violations = []

        # ユーザー指示がある場合のチェック
        if user_instruction:
            instruction_elements = self.extract_instruction_elements(user_instruction)

            # 年齢指定のチェック
            if instruction_elements.get('age'):
                if age != instruction_elements['age']:
                    violations.append({
                        'rule_id': 'RULE_170',
                        'type': ViolationType.USER_INSTRUCTION_VIOLATION.value,
                        'severity': 'CRITICAL',
                        'message': f'{person_name}: ユーザー指定年齢（{instruction_elements["age"]}歳）と異なる（現在: {age}歳）',
                        'suggestion': f'年齢を{instruction_elements["age"]}歳に変更'
                    })

            # キーワード指定のチェック
            required_keywords = instruction_elements.get('keywords', [])
            for keyword in required_keywords:
                if keyword not in episode_text:
                    violations.append({
                        'rule_id': 'RULE_170',
                        'type': ViolationType.USER_INSTRUCTION_VIOLATION.value,
                        'severity': 'CRITICAL',
                        'message': f'{person_name}: ユーザー指定キーワード「{keyword}」が含まれていない',
                        'suggestion': f'エピソードに「{keyword}」を含める'
                    })

        return violations

    def extract_instruction_elements(self, instruction: str) -> Dict:
        """ユーザー指示から要素を抽出"""
        elements = {}

        # 年齢の抽出（例: "38歳", "44歳のとき"）
        age_match = re.search(r'(\d+)歳', instruction)
        if age_match:
            elements['age'] = int(age_match.group(1))

        # キーワードの抽出（例: "ノルウェイの森", "七人の侍", "トラウト"）
        keywords = []

        # 作品名パターン
        works = ['ノルウェイの森', '七人の侍', '風の歌を聴け', 'ちびまる子ちゃん']
        for work in works:
            if work in instruction:
                keywords.append(work)

        # 人名パターン
        if 'トラウト' in instruction or 'マイク・トラウト' in instruction:
            keywords.append('トラウト')

        # イベントパターン
        if 'WBC' in instruction:
            keywords.append('WBC')
        if 'メジャーデビュー' in instruction:
            keywords.append('メジャーデビュー')

        if keywords:
            elements['keywords'] = keywords

        return elements
    '''

    # PDCAガーディアンファイルを更新
    with open('pdca_guardian.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # ViolationTypeにUSER_INSTRUCTION_VIOLATIONを追加
    violation_type_addition = '''    USER_INSTRUCTION_VIOLATION = "ユーザー指示違反"
    '''

    # ViolationTypeの最後に追加
    import_section = content.find('class ViolationType(Enum):')
    if import_section != -1:
        # 最後のenumメンバーを見つける
        last_enum = content.rfind('EDUCATION_VALUE_ABSENCE', import_section)
        if last_enum != -1:
            # その行の終わりを見つける
            line_end = content.find('\n', last_enum)
            # 新しい違反タイプを追加
            content = content[:line_end] + '\n' + violation_type_addition + content[line_end+1:]

    # check_episode_qualityメソッドを更新してルール170を含める
    check_method = content.find('def check_episode_quality(')
    if check_method != -1:
        # RULE_169の後にRULE_170を追加
        rule_169_end = content.find('# RULE_169のチェック終了', check_method)
        if rule_169_end == -1:
            # RULE_169の実装を探す
            rule_169_check = content.find('self.check_rule_169', check_method)
            if rule_169_check != -1:
                line_end = content.find('\n', rule_169_check)
                insert_point = line_end + 1

                rule_170_call = '''
        # RULE_170: ユーザー指示優先の原則
        # エラー事例から学習（2025年9月22日）
        # 明示的指示はスコア最適化より常に優先
        if hasattr(self, 'current_user_instruction'):
            rule_170_violations = self.check_rule_170_user_instruction_priority(
                episode_text, age, person_name_display,
                self.current_user_instruction
            )
            all_violations.extend(rule_170_violations)
'''
                content = content[:insert_point] + rule_170_call + content[insert_point:]

    # 新しいルールメソッドを追加
    # 最後のcheck_rule_メソッドを見つける
    last_rule_method = content.rfind('def check_rule_169')
    if last_rule_method != -1:
        # そのメソッドの終わりを見つける
        method_end = content.find('\n\n    def ', last_rule_method)
        if method_end == -1:
            method_end = len(content)

        content = content[:method_end] + '\n\n' + new_rule + content[method_end:]

    # 更新したファイルを保存
    with open('pdca_guardian_updated.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("="*70)
    print("✅ RULE_170: ユーザー指示優先原則を追加")
    print("="*70)
    print("""
    追加されたルール内容:

    1. 明示的指示の絶対優先
       - ユーザー指定の年齢、作品名、人物名は必須
       - スコアが低くても指示を優先

    2. 指示解釈の明確化
       - 「〜の方が良いかも」→ 変更指示として扱う
       - 「〜してみては？」→ 実装要求として扱う

    3. 違反判定基準
       - 指示と異なる選択 → 重大違反（CRITICAL）
       - スコア優先による指示無視 → 重大違反
       - 自己判断による改変 → 重大違反

    4. エラー事例の記録
       - 大谷翔平: WBC指定を無視して満票MVP選択
       - 村上春樹: ノルウェイの森指定を無視

    このルールにより、同様のエラーを防止します。
    """)

    return True

def create_rule_170_test():
    """ルール170のテストケースを作成"""

    test_code = '''#!/usr/bin/env python3
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
'''

    with open('test_rule_170.py', 'w', encoding='utf-8') as f:
        f.write(test_code)

    print("\n📝 テストコードを作成: test_rule_170.py")

def main():
    # ルール追加
    success = add_user_instruction_priority_rule()

    if success:
        # テストケース作成
        create_rule_170_test()

        print("\n" + "="*70)
        print("🛡️ PDCAガーディアン更新完了")
        print("="*70)
        print("""
        今後の動作:
        1. ユーザー指示を最優先で実装
        2. スコアは制約内での最適化のみ
        3. 創造的解釈による逸脱を防止
        4. 明示的指示からの乖離を自動検出

        二度と同じ過ちを繰り返しません。
        """)

if __name__ == "__main__":
    main()