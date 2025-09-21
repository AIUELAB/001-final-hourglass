#!/usr/bin/env python3
"""
PDCAガーディアンに文字数制限ルールを追加
RULE_160: エピソード文字数150-250文字制限
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# 新ルール追加
new_rule = {
    "rule_id": "RULE_160",
    "name": "エピソード文字数150-250文字制限",
    "description": "エピソードの文字数を150文字以上250文字以下に厳格に制限",
    "category": "文字数制限",
    "priority": "CRITICAL",
    "check_function": "check_character_count_strict",
    "violation_type": "CHARACTER_COUNT_VIOLATION_STRICT",
    "validation": "全エピソードが150-250文字の範囲内であることを確認",
    "error_message": "エピソード文字数が150-250文字の範囲外です",
    "prevention_measures": [
        "最小150文字、最大250文字を厳守",
        "300文字制限から250文字制限への変更",
        "過度な修飾語や冗長な表現の削除",
        "必要最小限の文脈フレーズのみ使用",
        "時代背景フレーズの簡潔化"
    ],
    "historical_context": "2025年9月21日: 300文字制限から250文字制限へ変更要請",
    "examples": {
        "wrong": "280文字のエピソード（範囲外）",
        "correct": "200文字のエピソード（範囲内）"
    },
    "character_limits": {
        "min": 150,
        "max": 250,
        "previous_max": 300,
        "optimal_range": [180, 220]
    },
    "implementation_notes": [
        "self.MIN_LENGTH = 150",
        "self.MAX_LENGTH = 250",
        "文脈フレーズは最大2つまで",
        "時代背景フレーズは短縮版を使用"
    ],
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.5"
}

# ルール追加
pdca_rules['rules'].append(new_rule)

# メタデータ更新
pdca_rules['metadata']['character_count_strict'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.5",
    "description": "文字数制限を150-250文字に厳格化",
    "previous_limits": {
        "min": 150,
        "max": 300
    },
    "current_limits": {
        "min": 150,
        "max": 250
    }
}

# バージョン更新
pdca_rules['version'] = "5.5"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.5",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_160: エピソード文字数150-250文字制限ルール追加",
        "最大文字数を300文字から250文字に変更"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_160: エピソード文字数150-250文字制限")
print(f"   バージョン: {pdca_rules['version']}")
print(f"\n📏 文字数制限変更:")
print(f"   変更前: 150-300文字")
print(f"   変更後: 150-250文字")

# ViolationType列挙型追加用
violation_type = """
    # RULE_160: 文字数制限厳格化 (v5.5)
    CHARACTER_COUNT_VIOLATION_STRICT = "文字数制限違反（150-250）"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_type)

# チェックメソッド
check_method = '''
def check_character_count_strict(self, episode_data: Dict) -> List[Dict]:
    """
    文字数制限の厳格チェック（RULE_160）

    Args:
        episode_data: エピソードデータ

    Returns:
        違反リスト
    """
    violations = []
    person_name = episode_data.get('person_name', '不明')
    episode_text = episode_data.get('episode_text', '')
    text_length = len(episode_text)

    MIN_LENGTH = 150
    MAX_LENGTH = 250  # 300から250に変更

    if text_length < MIN_LENGTH:
        violations.append({
            'rule_id': 'RULE_160',
            'type': ViolationType.CHARACTER_COUNT_VIOLATION_STRICT.value,
            'message': f'{person_name}: {text_length}文字（最小150文字未満）',
            'severity': 'critical'
        })
    elif text_length > MAX_LENGTH:
        violations.append({
            'rule_id': 'RULE_160',
            'type': ViolationType.CHARACTER_COUNT_VIOLATION_STRICT.value,
            'message': f'{person_name}: {text_length}文字（最大250文字超過）',
            'severity': 'critical'
        })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

print("\n🎯 実装ガイドライン:")
print("1. self.MAX_LENGTH = 250 に変更")
print("2. 文脈フレーズを最大2つまでに制限")
print("3. 時代背景フレーズを短縮版に変更")
print("4. 冗長な表現を削除")
print("5. 必要最小限の情報に絞る")