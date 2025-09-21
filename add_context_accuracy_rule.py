#!/usr/bin/env python3
"""
PDCAガーディアンにコンテキスト正確性ルールを追加
RULE_153: 賞の国内外区別の正確性
RULE_154: テンプレート文章の文脈適合性
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# 新ルール追加
new_rules = [
    {
        "rule_id": "RULE_153",
        "name": "賞の国内外区別の正確性",
        "description": "国内賞と国際賞を正確に区別し、適切な文脈を付与する",
        "category": "コンテキスト正確性",
        "priority": "HIGH",
        "check_function": "check_award_context_accuracy",
        "violation_type": "AWARD_CONTEXT_MISMATCH",
        "validation": "国内賞に『世界が認めた』等の不適切な表現を使用していないか",
        "error_message": "賞の性質（国内/国際）と文脈が不一致です",
        "prevention_measures": [
            "『日本アカデミー賞』と『アカデミー賞（Oscar）』を明確に区別",
            "国内賞には国内向けの表現を使用",
            "国際賞にのみ『世界』『国際的』の表現を使用",
            "部分文字列マッチングではなく完全な賞名で判定"
        ],
        "historical_context": "2025年9月21日: 櫻井翔の日本アカデミー賞に『世界が認めた』と誤った文脈を付与",
        "examples": {
            "wrong": "日本アカデミー賞...世界が認めたその才能は",
            "correct": "日本アカデミー賞...日本映画界最高峰の賞での評価は"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.2"
    },
    {
        "rule_id": "RULE_154",
        "name": "テンプレート文章の文脈適合性",
        "description": "機械的なテンプレート適用を避け、文脈に応じた適切な表現を使用",
        "category": "文章品質",
        "priority": "HIGH",
        "check_function": "check_template_context_fit",
        "violation_type": "TEMPLATE_MISAPPLICATION",
        "validation": "テンプレート文章が実際の内容と矛盾していないか",
        "error_message": "テンプレート文章が文脈に適合していません",
        "prevention_measures": [
            "キーワードの部分一致ではなく、完全な文脈を理解",
            "カテゴリ分類を詳細化（国内賞/国際賞/地方賞等）",
            "文章追加前に論理的整合性をチェック",
            "固定テンプレートではなく動的な文章生成"
        ],
        "historical_context": "2025年9月21日: 機械的なパターンマッチングによる不自然な文章生成",
        "examples": {
            "wrong": "文字数を埋めるための機械的な文章追加",
            "correct": "内容に即した自然な文脈の追加"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.2"
    }
]

# ルール追加
pdca_rules['rules'].extend(new_rules)

# メタデータ更新
pdca_rules['metadata']['context_accuracy'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.2",
    "description": "コンテキスト正確性ルールを追加"
}

# バージョン更新
pdca_rules['version'] = "5.2"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.2",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_153: 賞の国内外区別の正確性ルール追加",
        "RULE_154: テンプレート文章の文脈適合性ルール追加"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_153: 賞の国内外区別の正確性")
print(f"   - RULE_154: テンプレート文章の文脈適合性")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_types = """
    # RULE_153-154: コンテキスト正確性ルール (v5.2)
    AWARD_CONTEXT_MISMATCH = "賞の文脈不一致"
    TEMPLATE_MISAPPLICATION = "テンプレート誤適用"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_types)

# チェックメソッド
check_method = '''
def check_context_accuracy(self, episode_data: Dict) -> List[Dict]:
    """
    コンテキスト正確性のチェック（RULE_153-154）

    Args:
        episode_data: エピソードデータ

    Returns:
        違反リスト
    """
    violations = []
    person_name = episode_data.get('person_name', '不明')
    episode_text = episode_data.get('episode_text', '')

    # RULE_153: 賞の国内外区別
    domestic_awards = ['日本アカデミー賞', '日本レコード大賞', '芥川賞', '直木賞']
    international_phrases = ['世界が認めた', '世界に示した', '国際的な評価']

    for award in domestic_awards:
        if award in episode_text:
            for phrase in international_phrases:
                if phrase in episode_text:
                    violations.append({
                        'rule_id': 'RULE_153',
                        'type': ViolationType.AWARD_CONTEXT_MISMATCH.value,
                        'message': f'{person_name}: {award}に「{phrase}」は不適切',
                        'severity': 'high'
                    })

    # RULE_154: テンプレート重複チェック
    template_phrases = [
        'この瞬間は、私たちに挑戦することの素晴らしさを教えてくれます。',
        'この出来事は、私たちの心に深く刻まれています。'
    ]

    # 同じフレーズが2回以上出現
    for phrase in template_phrases:
        count = episode_text.count(phrase)
        if count >= 2:
            violations.append({
                'rule_id': 'RULE_154',
                'type': ViolationType.TEMPLATE_MISAPPLICATION.value,
                'message': f'{person_name}: テンプレート文「{phrase[:20]}...」が{count}回重複',
                'severity': 'medium'
            })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)