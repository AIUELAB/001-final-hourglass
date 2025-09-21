#!/usr/bin/env python3
"""
PDCAガーディアンに名詞終了禁止ルールを追加
RULE_165: エピソードの動詞・形容詞終了の徹底
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# RULE_165: 名詞終了禁止ルール
rule_165 = {
    "rule_id": "RULE_165",
    "name": "エピソードの動詞・形容詞終了の徹底",
    "description": "エピソードは必ず動詞または形容詞で終わらせる（名詞終了禁止）",
    "category": "文法基準",
    "priority": "CRITICAL",
    "check_function": "check_sentence_ending",
    "violation_type": "NOUN_ENDING_VIOLATION",
    "validation": "エピソードが動詞・形容詞で終わることを確認",
    "error_message": "エピソードが名詞で終わっています",
    "implementation_rules": [
        "すべてのエピソードは動詞・形容詞で終了する",
        "名詞で終わる場合は「〜した」「〜である」を追加",
        "体言止めの禁止",
        "インパクトのある動詞・形容詞を選択",
        "読後感を高める文末表現"
    ],
    "good_endings": [
        "〜を達成した",
        "〜となった",
        "〜を成し遂げた",
        "〜に成功した",
        "〜を示した",
        "〜を実現した",
        "〜を記録した",
        "〜を獲得した"
    ],
    "bad_endings": [
        "〜の完成",
        "〜の記録",
        "〜の達成",
        "〜の成功",
        "〜の功績",
        "〜の存在",
        "〜の結果"
    ],
    "examples": {
        "wrong": "メジャーリーグ開幕戦後に現役引退",
        "correct": "メジャーリーグ開幕戦後に現役引退を発表した",
        "wrong2": "ノーベル医学生理学賞の受賞",
        "correct2": "ノーベル医学生理学賞を受賞した"
    },
    "rationale": "動詞・形容詞で終わることで読み手への印象が強くなり、完結感が生まれる",
    "historical_context": "2025年9月21日: エピソードの名詞終了を禁止し、動詞・形容詞終了を義務化",
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.8"
}

# ルール追加
pdca_rules['rules'].append(rule_165)

# メタデータ更新
pdca_rules['metadata']['sentence_ending_control'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.8",
    "description": "エピソードの動詞・形容詞終了を義務化",
    "trigger": "名詞で終わるエピソードは印象が弱い問題"
}

# バージョン更新
pdca_rules['version'] = "5.8"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.8",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_165: エピソードの動詞・形容詞終了ルール追加",
        "名詞終了の禁止",
        "インパクトのある文末表現の義務化"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_165: エピソードの動詞・形容詞終了の徹底")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_type = """
    # RULE_165: 名詞終了違反 (v5.8)
    NOUN_ENDING_VIOLATION = "名詞終了違反"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_type)

# チェックメソッド
check_method = '''
def check_sentence_ending(self, episode_text: str) -> List[Dict]:
    """
    文末の動詞・形容詞チェック（RULE_165）

    Args:
        episode_text: エピソードテキスト

    Returns:
        違反リスト
    """
    violations = []

    # 文末の品詞を判定
    text = episode_text.rstrip('。')

    # 名詞で終わる典型的パターン
    noun_endings = [
        '完成', '記録', '達成', '成功', '功績',
        '存在', '結果', '引退', '受賞', '獲得',
        '優勝', '開催', '設立', '発表', '開発',
        '誕生', '完了', '終了', '開始', '実現'
    ]

    # 動詞・形容詞で終わる良いパターン
    verb_adj_endings = [
        'した', 'った', 'いた', 'れた', 'せた',
        'ある', 'いる', 'なる', 'った', 'った'
    ]

    # 文末が名詞で終わっているか確認
    for noun in noun_endings:
        if text.endswith(noun):
            violations.append({
                'rule_id': 'RULE_165',
                'type': ViolationType.NOUN_ENDING_VIOLATION.value,
                'message': f'名詞「{noun}」で終了しています',
                'severity': 'critical',
                'suggestion': f'{text}を達成した'
            })
            break

    # 動詞・形容詞で終わっていない場合の追加チェック
    has_verb_ending = any(text.endswith(ending) for ending in verb_adj_endings)
    if not has_verb_ending and not violations:
        # より詳細な解析が必要な場合はここに実装
        pass

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

print("\n🎯 実装ガイドライン:")
print("1. すべてのエピソードを動詞・形容詞で終了")
print("2. 名詞終了を検出して自動修正")
print("3. 「〜した」「〜となった」等を追加")
print("4. インパクトのある動詞を選択")
print("5. 読後感を高める文末表現を重視")