#!/usr/bin/env python3
"""
PDCAガーディアンにファクトチェック必須化ルールを追加
RULE_167: エピソード生成前の事実検証必須化
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# RULE_167: ファクトチェック必須化
rule_167 = {
    "rule_id": "RULE_167",
    "name": "エピソードファクトチェック必須化",
    "description": "すべての数値・記録・年代は生成前に必ず外部ソースで検証",
    "category": "データ品質",
    "priority": "CRITICAL",
    "check_function": "check_fact_verification",
    "violation_type": "FACT_CHECK_VIOLATION",
    "validation": "全数値・記録が信頼できるソースで確認済みであること",
    "error_message": "未検証の事実または誤った情報が検出されました",
    "implementation_rules": [
        "エピソード生成前に必ずWebSearch/Wikipediaでファクトチェックを実施",
        "年齢と年代の整合性を必ず確認（生年月日から計算）",
        "「初」「最高」「世界記録」等の最上級表現は必ず公式記録で確認",
        "数値データ（登録者数、売上、視聴率等）は必ず公式発表を確認",
        "達成時期（○歳の時）と実際の年代が一致することを確認",
        "複数ソースで情報が異なる場合は最も信頼できるソースを採用",
        "検証結果をvalidation_logに記録"
    ],
    "fact_check_required": [
        "日本人初、世界初などの「初」記録",
        "最高、最多、最年少などの「最」記録",
        "○○万人、○○億円などの具体的数値",
        "○歳の時という年齢と出来事の対応",
        "受賞歴、達成記録の正確な名称と時期",
        "統計データ、ランキング情報"
    ],
    "verification_sources": [
        "公式ウェブサイト",
        "Wikipedia（複数言語版で確認）",
        "信頼できるニュースサイト",
        "政府・公的機関の発表",
        "学術論文・研究データ",
        "業界団体の公式記録"
    ],
    "examples": {
        "wrong": "HIKAKINは30歳で登録者1000万人を日本人初で達成（未検証）",
        "correct": "HIKAKINは30歳で登録者800万人、32歳で1000万人達成（検証済み）",
        "wrong2": "イチローは42歳まで控え選手だった（事実誤認）",
        "correct2": "イチローは44歳まで現役、45歳で引退（検証済み）"
    },
    "verification_process": {
        "step1": "エピソード内の全数値・記録を抽出",
        "step2": "各項目についてWebSearchまたはWikipediaで確認",
        "step3": "年齢と年代の整合性を生年月日から計算して確認",
        "step4": "複数ソースで情報を照合",
        "step5": "検証結果をログに記録",
        "step6": "検証済みマークを付与"
    },
    "rationale": "誤った情報は読者の信頼を失い、エピソードの価値を損なう。すべての事実は検証可能でなければならない",
    "historical_context": "2025年9月21日: HIKAKINの1000万人達成時期の誤記から追加",
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.10"
}

# ルール追加
pdca_rules['rules'].append(rule_167)

# メタデータ更新
pdca_rules['metadata']['fact_check_system'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.10",
    "description": "エピソードファクトチェックシステムの確立",
    "trigger": "HIKAKINの登録者数達成時期の事実誤認防止"
}

# バージョン更新
pdca_rules['version'] = "5.10"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.10",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_167: ファクトチェック必須化ルールの追加",
        "エピソード生成前の事実検証プロセス確立",
        "年齢と年代の整合性確認必須化",
        "検証ソースの優先順位明確化"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_167: ファクトチェック必須化")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_type = """
    # RULE_167: ファクトチェック違反 (v5.10)
    FACT_CHECK_VIOLATION = "ファクトチェック違反"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_type)

# チェックメソッド
check_method = '''
def check_fact_verification(self, episode_data: Dict) -> List[Dict]:
    """
    ファクトチェック実施確認（RULE_167）

    Args:
        episode_data: エピソードデータ（テキスト、検証ログ含む）

    Returns:
        違反リスト
    """
    violations = []

    # 検証ログの確認
    if 'validation_log' not in episode_data:
        violations.append({
            'rule_id': 'RULE_167',
            'type': ViolationType.FACT_CHECK_VIOLATION.value,
            'message': 'ファクトチェック未実施',
            'severity': 'critical'
        })
        return violations

    # 必須検証項目のチェック
    text = episode_data.get('episode_text', '')
    validation_log = episode_data.get('validation_log', {})

    # 数値の検証
    import re
    numbers = re.findall(r'\d+[万億千百十]?[人円回歳年]', text)
    for num in numbers:
        if num not in validation_log.get('verified_numbers', []):
            violations.append({
                'rule_id': 'RULE_167',
                'type': ViolationType.FACT_CHECK_VIOLATION.value,
                'message': f'未検証の数値: {num}',
                'severity': 'critical'
            })

    # 最上級表現の検証
    superlatives = ['初', '最高', '最多', '最年少', '世界記録']
    for word in superlatives:
        if word in text and word not in validation_log.get('verified_records', []):
            violations.append({
                'rule_id': 'RULE_167',
                'type': ViolationType.FACT_CHECK_VIOLATION.value,
                'message': f'未検証の記録: {word}',
                'severity': 'critical'
            })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

print("\n🎯 実装ガイドライン:")
print("1. エピソード生成前に必ずWebSearchまたはWikipediaで事実確認")
print("2. 年齢と達成年の整合性を生年月日から計算")
print("3. 「初」「最」などの最上級表現は公式記録で確認")
print("4. 数値データは必ず一次ソースで検証")
print("5. 検証結果をvalidation_logに記録")
print("6. 複数ソースで矛盾がある場合は最も信頼できるソースを採用")

print("\n⚠️ HIKAKINの例:")
print("誤: 30歳で1000万人突破（2019年）")
print("正: 30歳で800万人突破（2019年）、32歳で1000万人突破（2021年）")