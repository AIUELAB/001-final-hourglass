#!/usr/bin/env python3
"""
PDCAガーディアンに事実優先原則ルールを追加
RULE_166: 偉業優先・センセーショナル要素は味付け程度
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# RULE_166: 事実優先原則
rule_166 = {
    "rule_id": "RULE_166",
    "name": "事実優先原則（センセーショナル要素は味付け程度）",
    "description": "偉業や歴史的事実を最優先し、感動的要素は事実の範囲内での味付けに留める",
    "category": "コンテンツ品質",
    "priority": "CRITICAL",
    "check_function": "check_fact_first_principle",
    "violation_type": "FACT_DISTORTION_VIOLATION",
    "validation": "すべての記述が検証可能な事実に基づいていることを確認",
    "error_message": "事実の歪曲または未確認情報が検出されました",
    "implementation_rules": [
        "検証可能な事実を最優先する",
        "誇張や脚色は一切禁止",
        "感動的要素は事実の解釈や背景説明に限定",
        "すべての数値は公式記録に基づく",
        "推測や憶測を事実のように記述しない",
        "偉業 > 背景 > 感動要素の優先順位を守る"
    ],
    "prohibited_patterns": [
        "～と言われている（未確認情報）",
        "おそらく～だった（推測）",
        "～に違いない（断定的推測）",
        "実は～（確認できない内部情報）",
        "～という噂がある",
        "～らしい",
        "～のようだ（推測）"
    ],
    "allowed_patterns": [
        "公式記録によると～",
        "～を達成した",
        "～という結果を残した",
        "当時の報道では～",
        "統計データでは～",
        "～を記録した",
        "～に成功した"
    ],
    "priority_structure": {
        "1_highest": "偉業・記録・達成の事実",
        "2_medium": "背景・過程の事実",
        "3_lowest": "観客反応・社会的影響（事実のみ）"
    },
    "examples": {
        "wrong": "イチローは42歳まで控え選手として屈辱の日々を過ごしていた",
        "correct": "イチローは44歳で会長付特別補佐となり、2019年開幕戦で現役復帰した",
        "wrong2": "おそらく相当な苦労があったに違いない",
        "correct2": "7年間で首位打者3回を獲得した"
    },
    "rationale": "読者に感動を与えることは重要だが、事実を歪曲しては信頼を失う。偉業そのものが最も感動的である",
    "historical_context": "2025年9月21日: センセーショナルな脚色により事実を歪曲した反省から追加",
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.9"
}

# ルール追加
pdca_rules['rules'].append(rule_166)

# メタデータ更新
pdca_rules['metadata']['fact_first_principle'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.9",
    "description": "事実優先原則を確立し、センセーショナル要素を適切に制限",
    "trigger": "事実を歪曲したセンセーショナルな記述の防止"
}

# バージョン更新
pdca_rules['version'] = "5.9"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.9",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_166: 事実優先原則の追加",
        "偉業を最優先とする構成",
        "センセーショナル要素の適切な制限",
        "検証可能な事実のみを記述"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_166: 事実優先原則")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_type = """
    # RULE_166: 事実歪曲違反 (v5.9)
    FACT_DISTORTION_VIOLATION = "事実歪曲違反"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_type)

# チェックメソッド
check_method = '''
def check_fact_first_principle(self, episode_text: str) -> List[Dict]:
    """
    事実優先原則チェック（RULE_166）

    Args:
        episode_text: エピソードテキスト

    Returns:
        違反リスト
    """
    violations = []

    # 禁止パターンのチェック
    prohibited_phrases = [
        'と言われている',
        'おそらく',
        'に違いない',
        '実は',
        'という噂',
        'らしい',
        'のようだ'
    ]

    for phrase in prohibited_phrases:
        if phrase in episode_text:
            violations.append({
                'rule_id': 'RULE_166',
                'type': ViolationType.FACT_DISTORTION_VIOLATION.value,
                'message': f'未確認情報または推測「{phrase}」が検出',
                'severity': 'critical'
            })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

print("\n🎯 実装ガイドライン:")
print("1. 偉業・記録を最優先で記述")
print("2. すべての数値は公式記録から引用")
print("3. 背景情報は事実のみ")
print("4. 感動要素は観客数や反応など検証可能な事実に限定")
print("5. 推測や憶測は完全排除")