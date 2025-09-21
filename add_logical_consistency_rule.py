#!/usr/bin/env python3
"""
PDCAガーディアンに論理的整合性ルールを追加
RULE_155: 内容と文脈の論理的整合性
RULE_156: フレーズ重複の防止
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# 新ルール追加
new_rules = [
    {
        "rule_id": "RULE_155",
        "name": "内容と文脈の論理的整合性",
        "description": "エピソードの内容と追加される文脈が論理的に整合していることを確認",
        "category": "論理的整合性",
        "priority": "CRITICAL",
        "check_function": "check_logical_consistency",
        "violation_type": "LOGICAL_INCONSISTENCY",
        "validation": "政治的決定に『挑戦の素晴らしさ』など、内容と不適合な文脈を使用していないか",
        "error_message": "エピソードの内容と文脈が論理的に不整合です",
        "prevention_measures": [
            "内容をカテゴライズして適切な文脈を選択",
            "政治→政治的リーダーシップ、芸術→芸術的価値など",
            "『挑戦』は真に挑戦的な内容（スポーツ、研究等）にのみ使用",
            "文字数調整のための無意味な文章追加を禁止"
        ],
        "historical_context": "2025年9月21日: 郵政民営化に『挑戦の素晴らしさ』という不適切な文脈",
        "examples": {
            "wrong": "郵政民営化を実現。この瞬間は、私たちに挑戦することの素晴らしさを教えてくれます。",
            "correct": "郵政民営化を実現。この決断は日本の歴史に大きな転換点をもたらしました。"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.3"
    },
    {
        "rule_id": "RULE_156",
        "name": "フレーズ重複の防止",
        "description": "同一フレーズの重複使用を防止し、多様な表現を確保",
        "category": "文章品質",
        "priority": "HIGH",
        "check_function": "check_phrase_duplication",
        "violation_type": "PHRASE_DUPLICATION",
        "validation": "同じフレーズが2回以上使用されていないか",
        "error_message": "同一フレーズが重複しています",
        "prevention_measures": [
            "使用済みフレーズを追跡（Set型で管理）",
            "カテゴリ別に複数の代替フレーズを用意",
            "重複検出時は別カテゴリから選択",
            "最低3種類以上の異なるフレーズを準備"
        ],
        "historical_context": "2025年9月21日: 『この瞬間は...』が同一エピソード内で2回重複",
        "examples": {
            "wrong": "この瞬間は...。この瞬間は...。（同じフレーズが2回）",
            "correct": "この決断は...。政治的リーダーシップが...。（異なる表現）"
        },
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "version": "v5.3"
    }
]

# ルール追加
pdca_rules['rules'].extend(new_rules)

# メタデータ更新
pdca_rules['metadata']['logical_consistency'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.3",
    "description": "論理的整合性と重複防止ルールを追加"
}

# バージョン更新
pdca_rules['version'] = "5.3"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.3",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_155: 内容と文脈の論理的整合性ルール追加",
        "RULE_156: フレーズ重複の防止ルール追加"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_155: 内容と文脈の論理的整合性")
print(f"   - RULE_156: フレーズ重複の防止")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_types = """
    # RULE_155-156: 論理的整合性ルール (v5.3)
    LOGICAL_INCONSISTENCY = "論理的不整合"
    PHRASE_DUPLICATION = "フレーズ重複"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_types)

# チェックメソッド
check_method = '''
def check_logical_consistency(self, episode_data: Dict) -> List[Dict]:
    """
    論理的整合性のチェック（RULE_155-156）

    Args:
        episode_data: エピソードデータ

    Returns:
        違反リスト
    """
    violations = []
    person_name = episode_data.get('person_name', '不明')
    episode_text = episode_data.get('episode_text', '')

    # 事実テキストを抽出（「、」の後から「。」まで）
    try:
        fact_part = episode_text.split('、')[1].split('。')[0]
    except:
        fact_part = episode_text

    # RULE_155: 論理的整合性
    inappropriate_matches = [
        (['選挙', '民営化', '政策', '解散'], '挑戦することの素晴らしさ'),
        (['発表', '映画', '作品', '小説'], '挑戦することの素晴らしさ'),
    ]

    for keywords, inappropriate_phrase in inappropriate_matches:
        if any(k in fact_part for k in keywords):
            if inappropriate_phrase in episode_text:
                violations.append({
                    'rule_id': 'RULE_155',
                    'type': ViolationType.LOGICAL_INCONSISTENCY.value,
                    'message': f'{person_name}: {keywords[0]}関連に「{inappropriate_phrase}」は不適切',
                    'severity': 'critical'
                })

    # RULE_156: フレーズ重複
    common_phrases = [
        'この瞬間は、私たちに挑戦することの素晴らしさを教えてくれます。',
        'この出来事は、私たちの心に深く刻まれています。',
        'その功績は今も多くの人々に勇気と希望を与え続けています。'
    ]

    for phrase in common_phrases:
        count = episode_text.count(phrase)
        if count >= 2:
            violations.append({
                'rule_id': 'RULE_156',
                'type': ViolationType.PHRASE_DUPLICATION.value,
                'message': f'{person_name}: 「{phrase[:20]}...」が{count}回重複',
                'severity': 'high'
            })

    return violations
'''

print("\n📝 チェックメソッドを追加:")
print(check_method)

# 提案：外部AIによる検証
print("\n🤖 提案: 外部AI検証システム")
print("""
def validate_with_external_ai(episode_text: str) -> Dict:
    '''
    ChatGPT等の外部AIでエピソードの自然性を検証

    検証項目:
    1. 日本語として自然か
    2. 論理的に整合しているか
    3. 感動的で読みやすいか
    '''

    prompt = f'''
    以下の文章を評価してください：
    「{episode_text}」

    評価基準：
    - 日本語の自然性（1-10点）
    - 論理的整合性（1-10点）
    - 感動度（1-10点）
    - 問題点の指摘
    '''

    # OpenAI API呼び出し（実装例）
    # response = openai.ChatCompletion.create(...)

    return {
        'naturalness': 8,
        'consistency': 9,
        'emotional': 7,
        'issues': []
    }
""")