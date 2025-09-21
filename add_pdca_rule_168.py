#!/usr/bin/env python3
"""
PDCAガーディアンにエピソード品質保証ルールを追加
RULE_168: 量より質の優先原則
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# RULE_168: エピソード品質優先ルール
rule_168 = {
    "rule_id": "RULE_168",
    "name": "エピソード品質優先原則",
    "description": "量産よりも品質を絶対優先。曖昧・間接的・主観的エピソードは即却下",
    "category": "品質保証",
    "priority": "CRITICAL",
    "check_function": "check_episode_quality_priority",
    "violation_type": "QUALITY_PRIORITY_VIOLATION",
    "validation": "具体的な年齢時の直接的な偉業・出来事のみ許可",
    "error_message": "品質基準を満たさないエピソードが検出されました",
    "implementation_rules": [
        "「○○から××年後」などの間接的時期表現は禁止",
        "「語り継がれた」「評価された」など受動的表現は禁止",
        "その年齢時の直接的な行動・達成のみを記述",
        "「美しさ」「カリスマ」など検証不可能な主観表現は禁止",
        "必ず具体的な数値・記録・作品名を含める",
        "大量生成時も1件ずつ品質チェックを実施",
        "カバー率より品質を優先する"
    ],
    "prohibited_patterns": [
        "○○から××年後",
        "××年経っても",
        "語り継がれた",
        "評価された",
        "認められた",
        "美しさ",
        "カリスマ",
        "憧れの存在",
        "象徴となった",
        "君臨し続けた"
    ],
    "required_elements": [
        "その年齢時の具体的行動",
        "検証可能な数値・記録",
        "作品名・賞名・会社名など固有名詞",
        "能動的な達成動詞",
        "直接的な因果関係"
    ],
    "quality_checklist": {
        "step1": "年齢と出来事の時期が完全一致するか",
        "step2": "受動態ではなく能動態で書かれているか",
        "step3": "具体的数値・記録が含まれているか",
        "step4": "主観的表現が排除されているか",
        "step5": "Wikipedia等で検証可能か"
    },
    "examples": {
        "wrong": "43歳のとき、ロングバケーションから10年経っても語り継がれた",
        "correct": "32歳のとき、ロングバケーションで最高視聴率36.7%を記録した",
        "wrong2": "美しさで憧れの存在となった",
        "correct2": "主演作が年間視聴率1位を獲得した"
    },
    "rationale": "曖昧で検証困難なエピソードは読者の信頼を失う。品質なき量産は無価値",
    "historical_context": "2025年9月21日: 山口智子エピソードの品質問題から追加",
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.11"
}

# RULE_169: バッチ生成時の個別検証ルール
rule_169 = {
    "rule_id": "RULE_169",
    "name": "バッチ生成個別検証必須",
    "description": "大量生成時も1件ずつ個別にファクトチェックと品質検証を実施",
    "category": "プロセス管理",
    "priority": "CRITICAL",
    "check_function": "check_batch_individual_verification",
    "violation_type": "BATCH_VERIFICATION_VIOLATION",
    "validation": "全エピソードに個別検証ログが存在すること",
    "error_message": "バッチ生成での検証省略が検出されました",
    "implementation_rules": [
        "10件以上のバッチ生成でも個別検証必須",
        "各エピソードに検証タイムスタンプを付与",
        "検証ソースURLを記録",
        "形式的な「verified」付与は禁止",
        "検証できないエピソードは即削除",
        "量産プレッシャーでの品質妥協を禁止"
    ],
    "verification_requirements": {
        "per_episode": {
            "fact_check_source": "必須（Wikipedia/公式サイトURL）",
            "verification_timestamp": "必須（実際の検証時刻）",
            "checker_notes": "推奨（検証時の注意点）",
            "confidence_score": "必須（0.0-1.0）"
        }
    },
    "batch_limits": {
        "max_per_batch": 10,
        "min_interval_seconds": 60,
        "quality_threshold": 0.95
    },
    "rationale": "大量生成は品質劣化の温床。個別検証なき量産は禁止",
    "historical_context": "2025年9月21日: 99件バッチ生成での品質問題から追加",
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.11"
}

# ルール追加
pdca_rules['rules'].append(rule_168)
pdca_rules['rules'].append(rule_169)

# メタデータ更新
pdca_rules['metadata']['quality_priority_system'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.11",
    "description": "品質優先原則とバッチ検証システムの確立",
    "trigger": "山口智子エピソードの品質問題"
}

# バージョン更新
pdca_rules['version'] = "5.11"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.11",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_168: エピソード品質優先原則の追加",
        "RULE_169: バッチ生成個別検証ルールの追加",
        "間接的表現・主観的表現の禁止",
        "量より質の絶対優先"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_168: エピソード品質優先原則")
print(f"   - RULE_169: バッチ生成個別検証必須")
print(f"   バージョン: {pdca_rules['version']}")

# 問題エピソードの修正例
print("\n📝 山口智子エピソードの修正案:")
print("【誤】43歳: ロングバケーションから10年経っても語り継がれた")
print("【正】32歳: ロングバケーションで最高視聴率36.7%、社会現象を起こした")

# チェックメソッド
check_method = '''
def check_episode_quality_priority(self, episode_text: str) -> List[Dict]:
    """
    エピソード品質優先チェック（RULE_168）
    """
    violations = []

    # 禁止パターンチェック
    prohibited = [
        "から.*年", "経っても", "語り継が", "評価され",
        "美しさ", "カリスマ", "憧れ", "象徴", "君臨"
    ]

    for pattern in prohibited:
        if pattern in episode_text:
            violations.append({
                'rule_id': 'RULE_168',
                'type': ViolationType.QUALITY_PRIORITY_VIOLATION.value,
                'message': f'禁止表現を検出: {pattern}',
                'severity': 'critical'
            })

    # 必須要素チェック
    import re
    has_number = bool(re.search(r'\d+[万億千百十]?[人円枚本%]', episode_text))
    has_active_verb = any(v in episode_text for v in
                         ['達成した', '記録した', '獲得した', '創業した'])

    if not has_number:
        violations.append({
            'rule_id': 'RULE_168',
            'type': ViolationType.QUALITY_PRIORITY_VIOLATION.value,
            'message': '具体的数値が不在',
            'severity': 'critical'
        })

    if not has_active_verb:
        violations.append({
            'rule_id': 'RULE_168',
            'type': ViolationType.QUALITY_PRIORITY_VIOLATION.value,
            'message': '能動的達成動詞が不在',
            'severity': 'critical'
        })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)