#!/usr/bin/env python3
"""
PDCAガーディアンに文字数制限と文末改善ルールを追加
RULE_151: 文字数制限（150-300文字）
RULE_152: 名詞終わりの禁止
"""

import json
from datetime import datetime

# PDCAガーディアンのルールファイルを読み込み
try:
    with open('pdca_rules.json', 'r', encoding='utf-8') as f:
        pdca_rules = json.load(f)
except FileNotFoundError:
    pdca_rules = {'rules': [], 'failure_patterns': [], 'success_patterns': []}

# 新ルール追加（リスト形式）
new_rules = [
    {
        "rule_id": "RULE_151",
        "name": "エピソード文字数制限（150-300文字）",
        "description": "エピソードは読者に深い印象を与えるため150-300文字の範囲で記述する",
        "category": "エピソード品質",
        "priority": "HIGH",
        "check_function": "check_character_length",
        "violation_type": "EPISODE_LENGTH_VIOLATION",
        "validation": "len(episode_text) >= 150 and len(episode_text) <= 300",
        "error_message": "エピソードは150-300文字の範囲内で記述する必要があります",
        "prevention_measures": [
            "エピソード生成時に文字数チェックを必須化",
            "不足時は背景情報や文脈を追加",
            "超過時は冗長部分を削除"
        ],
        "historical_context": "2025年9月21日: ユーザーから「150-300文字にします」との指示",
        "examples": {
            "wrong": "45文字の短いエピソード",
            "correct": "ヘレン・ケラーのWater!エピソード（222文字）"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.1"
    },
    {
        "rule_id": "RULE_152",
        "name": "名詞終わりの禁止",
        "description": "エピソードの文末が名詞で終わるのは味気ないため、感動的な表現で締めくくる",
        "category": "エピソード品質",
        "priority": "MEDIUM",
        "check_function": "check_bland_ending",
        "violation_type": "EPISODE_BLAND_ENDING",
        "validation": "not any(text.rstrip('。').endswith(noun) for noun in ['達成', '獲得', '受賞', '優勝', '成功', '発表', '創業', '設立', '記録', '更新', '突破', '登板', '就任', '当選', '完成', '出版'])",
        "error_message": "エピソードの文末が名詞で終わっているため、感動的な文末表現に変更してください",
        "prevention_measures": [
            "名詞終わりを検出したら自動で感動的な表現に変換",
            "「達成」→「という偉業を成し遂げました」",
            "「獲得」→「を手にすることができました」"
        ],
        "historical_context": "2025年9月21日: ユーザーから「達成などの名詞で終わりにすると味気ないのでやめましょう」との指摘",
        "examples": {
            "wrong": "...史上初の50本塁打50盗塁達成",
            "correct": "...史上初の50本塁打50盗塁という偉業を成し遂げました"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.1"
    }
]

# 既存ルールに追加
pdca_rules['rules'].extend(new_rules)

# メタデータ更新
if 'metadata' not in pdca_rules:
    pdca_rules['metadata'] = {}

pdca_rules['metadata']['character_rules'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.1",
    "description": "文字数制限と文末改善ルールを追加"
}

# バージョン更新
pdca_rules['version'] = "5.1"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
if 'update_history' not in pdca_rules:
    pdca_rules['update_history'] = []

pdca_rules['update_history'].append({
    "version": "5.1",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_151: エピソード文字数制限（150-300文字）追加",
        "RULE_152: 名詞終わりの禁止ルール追加"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_151: 文字数制限（150-300文字）")
print(f"   - RULE_152: 名詞終わりの禁止")
print(f"   バージョン: {pdca_rules['version']}")
print(f"   更新日時: {pdca_rules['last_updated']}")

# ViolationType列挙型に追加する内容を生成
violation_types = """
    # RULE_151-152: 文字数・文末ルール (v5.1)
    EPISODE_LENGTH_VIOLATION = "文字数制限違反"
    EPISODE_BLAND_ENDING = "味気ない名詞終わり"
"""

print("\n📝 ViolationType列挙型に以下を追加してください:")
print(violation_types)

# チェックメソッドの雛形を生成
check_method = '''
def check_character_rules(self, episode_data: Dict) -> List[Dict]:
    """
    文字数制限と文末改善のチェック（RULE_151-152）

    Args:
        episode_data: エピソードデータ

    Returns:
        違反リスト
    """
    violations = []
    person_name = episode_data.get('person_name', '不明')
    episode_text = episode_data.get('episode_text', '')

    # RULE_151: 文字数制限（150-300文字）
    text_length = len(episode_text)
    if text_length < 150 or text_length > 300:
        violations.append({
            'rule_id': 'RULE_151',
            'type': ViolationType.EPISODE_LENGTH_VIOLATION.value,
            'message': f'{person_name}: 文字数 {text_length} - 150-300文字の範囲外',
            'severity': 'high'
        })

    # RULE_152: 名詞終わりの禁止
    boring_endings = [
        '達成', '獲得', '受賞', '優勝', '成功', '発表', '創業', '設立',
        '記録', '更新', '突破', '登板', '就任', '当選', '完成', '出版'
    ]

    text_without_period = episode_text.rstrip('。')
    for noun in boring_endings:
        if text_without_period.endswith(noun):
            violations.append({
                'rule_id': 'RULE_152',
                'type': ViolationType.EPISODE_BLAND_ENDING.value,
                'message': f'{person_name}: 文末が「{noun}」で終わっている（味気ない）',
                'severity': 'medium'
            })
            break

    return violations
'''

print("\n📝 PDCAガーディアンに以下のメソッドを追加してください:")
print(check_method)