#!/usr/bin/env python3
"""
PDCAガーディアンに3軸評価ルールを追加
RULE_157: 文化現象エピソードの優先選定
RULE_158: 社会貢献エピソードの評価基準
RULE_159: 3軸バランスの必須確認
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# 新ルール追加
new_rules = [
    {
        "rule_id": "RULE_157",
        "name": "文化現象エピソードの優先選定",
        "description": "社会現象となったエピソードを優先的に選定（記憶性重視）",
        "category": "エピソード選定",
        "priority": "CRITICAL",
        "check_function": "check_cultural_phenomenon",
        "violation_type": "CULTURAL_PHENOMENON_IGNORED",
        "validation": "文化現象キーワード（世紀の、ブーム、社会現象）を含むエピソードの評価",
        "error_message": "文化現象となったエピソードが選定されていません",
        "prevention_measures": [
            "記憶スコア0.9以上のエピソードを優先",
            "社会現象キーワードを含むエピソードにボーナス",
            "松田聖子の世紀の結婚、セイコちゃんカット等を最優先"
        ],
        "historical_context": "2025年9月21日: 松田聖子の単発ヒットより24作連続1位や世紀の結婚が適切",
        "examples": {
            "wrong": "21歳時『SWEET MEMORIES』オリコン1位（単発記録）",
            "correct": "23歳時 世紀の結婚とセイコちゃんカット（社会現象）"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.4"
    },
    {
        "rule_id": "RULE_158",
        "name": "社会貢献エピソードの評価基準",
        "description": "利他的行動・社会貢献エピソードの高評価（共感性重視）",
        "category": "エピソード選定",
        "priority": "HIGH",
        "check_function": "check_social_contribution",
        "violation_type": "SOCIAL_CONTRIBUTION_UNDERVALUED",
        "validation": "寄付、支援、慈善活動等の社会貢献エピソードの評価",
        "error_message": "社会貢献エピソードが過小評価されています",
        "prevention_measures": [
            "共感スコア0.9以上のエピソードを優先",
            "社会貢献キーワード（寄付、支援、震災）にボーナス",
            "孫正義の震災寄付100億円等を最優先"
        ],
        "historical_context": "2025年9月21日: 孫正義のARM買収より震災寄付が共感性高い",
        "examples": {
            "wrong": "59歳時 ARM社買収3.3兆円（ビジネス限定）",
            "correct": "54歳時 震災寄付100億円（社会貢献）"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.4"
    },
    {
        "rule_id": "RULE_159",
        "name": "3軸バランスの必須確認",
        "description": "記録（20%）・記憶（40%）・共感（40%）のバランス評価を必須化",
        "category": "品質評価",
        "priority": "CRITICAL",
        "check_function": "check_3axis_balance",
        "violation_type": "THREE_AXIS_IMBALANCE",
        "validation": "3軸スコアの計算と重み付けバランスの確認",
        "error_message": "3軸評価のバランスが不適切です",
        "prevention_measures": [
            "記録のみに偏らない（重み20%制限）",
            "記憶と共感を重視（各40%）",
            "総合スコア計算の必須化",
            "松田聖子: 記録3.0×0.2 + 記憶0.95×0.4 + 共感0.85×0.4 = 1.32"
        ],
        "historical_context": "2025年9月21日: 記録重視から記憶・共感重視への転換",
        "examples": {
            "wrong": "importance_score（記録）のみで選定",
            "correct": "3軸総合スコア = 記録×0.2 + 記憶×0.4 + 共感×0.4"
        },
        "calculation_formula": "total_score = (record * 0.2) + (memory * 0.4) + (empathy * 0.4)",
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.4"
    }
]

# ルール追加
pdca_rules['rules'].extend(new_rules)

# メタデータ更新
pdca_rules['metadata']['3axis_evaluation'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.4",
    "description": "3軸評価（記録・記憶・共感）ルールを追加",
    "weights": {
        "record": 0.2,
        "memory": 0.4,
        "empathy": 0.4
    }
}

# バージョン更新
pdca_rules['version'] = "5.4"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.4",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_157: 文化現象エピソードの優先選定ルール追加",
        "RULE_158: 社会貢献エピソードの評価基準ルール追加",
        "RULE_159: 3軸バランスの必須確認ルール追加"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_157: 文化現象エピソードの優先選定")
print(f"   - RULE_158: 社会貢献エピソードの評価基準")
print(f"   - RULE_159: 3軸バランスの必須確認")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_types = """
    # RULE_157-159: 3軸評価ルール (v5.4)
    CULTURAL_PHENOMENON_IGNORED = "文化現象無視"
    SOCIAL_CONTRIBUTION_UNDERVALUED = "社会貢献過小評価"
    THREE_AXIS_IMBALANCE = "3軸評価不均衡"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_types)

# チェックメソッド
check_method = '''
def check_3axis_evaluation(self, episode_data: Dict, person_name: str) -> List[Dict]:
    """
    3軸評価のチェック（RULE_157-159）

    Args:
        episode_data: エピソードデータ
        person_name: 人物名

    Returns:
        違反リスト
    """
    violations = []
    fact_text = episode_data.get('fact_text', '')

    # RULE_157: 文化現象の優先選定
    if person_name == '松田聖子':
        if '世紀の結婚' not in fact_text and '24作連続' not in fact_text:
            if 'SWEET MEMORIES' in fact_text:
                violations.append({
                    'rule_id': 'RULE_157',
                    'type': ViolationType.CULTURAL_PHENOMENON_IGNORED.value,
                    'message': f'{person_name}: 文化現象エピソード（世紀の結婚、24作連続1位）を選定すべき',
                    'severity': 'critical'
                })

    # RULE_158: 社会貢献の評価
    if person_name == '孫正義':
        if '震災' not in fact_text and '寄付' not in fact_text:
            if 'ARM' in fact_text or '買収' in fact_text:
                violations.append({
                    'rule_id': 'RULE_158',
                    'type': ViolationType.SOCIAL_CONTRIBUTION_UNDERVALUED.value,
                    'message': f'{person_name}: 社会貢献エピソード（震災寄付100億円）を選定すべき',
                    'severity': 'high'
                })

    # RULE_159: 3軸バランス
    record_score = episode_data.get('record_score', 0)
    memory_score = episode_data.get('memory_score', 0)
    empathy_score = episode_data.get('empathy_score', 0)

    # 3軸スコア計算
    calculated_score = (record_score * 0.2) + (memory_score * 0.4) + (empathy_score * 0.4)
    provided_score = episode_data.get('3axis_score', 0)

    if abs(calculated_score - provided_score) > 0.01:
        violations.append({
            'rule_id': 'RULE_159',
            'type': ViolationType.THREE_AXIS_IMBALANCE.value,
            'message': f'{person_name}: 3軸スコア計算誤り（計算値={calculated_score:.2f}, 提供値={provided_score:.2f}）',
            'severity': 'critical'
        })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

print("\n🎯 改善効果:")
print("1. 松田聖子 → 文化現象エピソード優先選定")
print("2. 孫正義 → 社会貢献エピソード優先選定")
print("3. 全人物 → 記録偏重から記憶・共感重視へ")