#!/usr/bin/env python3
"""
PDCAガーディアンに日付排除・年齢比較フォーカスルールを追加
RULE_164: 年齢比較純粋性の確保
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# RULE_164: 年齢比較純粋性の確保
rule_164 = {
    "rule_id": "RULE_164",
    "name": "年齢比較純粋性の確保",
    "description": "具体的な日付を排除し、年齢比較の本質に集中",
    "category": "品質基準",
    "priority": "CRITICAL",
    "check_function": "check_age_comparison_purity",
    "violation_type": "DATE_NOISE_VIOLATION",
    "validation": "具体的な日付が含まれていないことを確認",
    "error_message": "具体的な日付がノイズとして検出されました",
    "prevention_measures": [
        "年月日の具体的記述を排除",
        "『◯月◯日』形式の削除",
        "西暦年の単独使用禁止",
        "年齢比較の本質への集中",
        "時系列より同年齢での達成内容を重視"
    ],
    "prohibited_patterns": [
        r"\d{4}年\d{1,2}月\d{1,2}日",  # 2021年3月21日
        r"\d{1,2}月\d{1,2}日",          # 3月21日
        r"\d{4}年\d{1,2}月",            # 2021年3月
        r"午前\d+時",                    # 午前9時
        r"午後\d+時",                    # 午後3時
        r"\d+時\d+分"                   # 11時30分
    ],
    "allowed_patterns": [
        "同じ○○歳のとき",
        "○○歳で",
        "○年間",
        "○年ぶり",
        "第○回"
    ],
    "rationale": "ユーザーとの年齢比較が目的であり、具体的な日付は比較の本質を損なうノイズとなる",
    "historical_context": "2025年9月21日: 年齢比較の純粋性確保のため日付排除を決定",
    "examples": {
        "wrong": "1887年4月5日、アラバマ州の自宅で",
        "correct": "アラバマ州の自宅で",
        "wrong2": "2018年2月17日、平昌オリンピックで",
        "correct2": "平昌オリンピックで"
    },
    "implementation_notes": [
        "日付パターンの自動検出と削除",
        "年齢情報の強調",
        "出来事の内容に焦点",
        "時代背景は概略のみ"
    ],
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.7"
}

# ルール追加
pdca_rules['rules'].append(rule_164)

# メタデータ更新
pdca_rules['metadata']['age_comparison_focus'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.7",
    "description": "年齢比較の純粋性を確保するため日付を排除",
    "trigger": "具体的な日付が比較感を損なうノイズとなる問題"
}

# バージョン更新
pdca_rules['version'] = "5.7"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.7",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_164: 年齢比較純粋性の確保ルール追加",
        "具体的な日付の排除",
        "年齢比較の本質への集中"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_164: 年齢比較純粋性の確保")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_type = """
    # RULE_164: 日付ノイズ違反 (v5.7)
    DATE_NOISE_VIOLATION = "具体的日付ノイズ違反"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_type)

# チェックメソッド
check_method = '''
def check_age_comparison_purity(self, episode_text: str) -> List[Dict]:
    """
    年齢比較純粋性チェック（RULE_164）

    Args:
        episode_text: エピソードテキスト

    Returns:
        違反リスト
    """
    import re
    violations = []

    # 禁止パターンのチェック
    prohibited_patterns = [
        (r'\d{4}年\d{1,2}月\d{1,2}日', '年月日'),
        (r'\d{1,2}月\d{1,2}日', '月日'),
        (r'\d{4}年\d{1,2}月', '年月'),
        (r'午前\d+時', '時刻'),
        (r'午後\d+時', '時刻'),
        (r'\d+時\d+分', '時分')
    ]

    for pattern, pattern_type in prohibited_patterns:
        matches = re.findall(pattern, episode_text)
        if matches:
            violations.append({
                'rule_id': 'RULE_164',
                'type': ViolationType.DATE_NOISE_VIOLATION.value,
                'message': f'{pattern_type}形式の日付「{matches[0]}」がノイズとして検出',
                'severity': 'critical'
            })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

print("\n🎯 実装ガイドライン:")
print("1. 全ての具体的日付を削除")
print("2. 『あなたと同じ○○歳のとき』を強調")
print("3. 年齢での達成・出来事に焦点")
print("4. 時系列情報より内容を重視")
print("5. 比較の純粋性を保つ")