#!/usr/bin/env python3
"""
PDCAガーディアンにセンセーショナル価値チェックメソッドを追加
"""

import sys

# PDCAガーディアンファイルの読み込み
with open('pdca_guardian.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# check_sensational_valueメソッドの定義
new_method = '''
    def check_sensational_value(self, episode_data: Dict, all_facts: List[Dict] = None) -> List[Dict]:
        """
        センセーショナル価値のチェック（RULE_144-150）

        Args:
            episode_data: エピソードデータ
            all_facts: その人物の全事実データ

        Returns:
            違反リスト
        """
        violations = []
        person_name = episode_data.get('person_name', '不明')
        episode_text = episode_data.get('episode_text', '')
        age = episode_data.get('age', 0)

        # RULE_144: ストーリー性の確保
        story_keywords = ['転換', '初めて', 'きっかけ', '瞬間', '困難', '挫折',
                         '克服', '復活', '奇跡', '挑戦']
        if not any(k in episode_text for k in story_keywords):
            violations.append({
                'rule_id': 'RULE_144',
                'type': ViolationType.LACK_OF_STORY.value,
                'message': f'{person_name}: ストーリー性不足 - 転換点や困難克服の要素なし',
                'severity': 'medium'
            })

        # RULE_145: コンテキストの豊富化
        if len(episode_text) < 100:
            violations.append({
                'rule_id': 'RULE_145',
                'type': ViolationType.POOR_CONTEXT.value,
                'message': f'{person_name}: コンテキスト不足 - 背景説明が少ない',
                'severity': 'medium'
            })

        # RULE_146: 共感性の最大化
        empathy_keywords = ['同じ', '誰もが', '勇気', '希望', '夢', '憧れ']
        if not any(k in episode_text for k in empathy_keywords):
            violations.append({
                'rule_id': 'RULE_146',
                'type': ViolationType.LOW_EMPATHY.value,
                'message': f'{person_name}: 共感性不足 - ユーザーとの接点が弱い',
                'severity': 'medium'
            })

        # RULE_147: 意味付けの明確化
        significance_keywords = ['重要', '意味', '歴史', '画期的', '世界を変えた']
        if not any(k in episode_text for k in significance_keywords):
            if not ('これは' in episode_text or 'この' in episode_text):
                violations.append({
                    'rule_id': 'RULE_147',
                    'type': ViolationType.UNCLEAR_SIGNIFICANCE.value,
                    'message': f'{person_name}: 意味付け不明確 - なぜ重要かの説明なし',
                    'severity': 'low'
                })

        # RULE_148: 最も重要な瞬間を優先
        # 年齢が極端に高い場合の警告
        if age > 60:
            if all_facts and any(f.get('age', 0) < 30 for f in all_facts):
                violations.append({
                    'rule_id': 'RULE_148',
                    'type': ViolationType.AGE_OVER_VALUE.value,
                    'message': f'{person_name}: より若い年齢に重要な出来事がある可能性',
                    'severity': 'low'
                })

        # RULE_149: 年齢制約より価値を重視
        # ヘレン・ケラーのような特別なケース
        if person_name == "ヘレン・ケラー" and age != 7:
            if all_facts and any(f.get('age') == 7 for f in all_facts):
                violations.append({
                    'rule_id': 'RULE_149',
                    'type': ViolationType.RIGID_AGE_SELECTION.value,
                    'message': f'{person_name}: 7歳のWater!エピソードがより価値が高い',
                    'severity': 'high'
                })

        # RULE_150: 複数年齢候補の比較評価
        if all_facts and len(all_facts) > 1:
            # 選択された事実が本当に最適かチェック
            selected_score = episode_data.get('algorithm_score', 0)
            if selected_score == 0:
                violations.append({
                    'rule_id': 'RULE_150',
                    'type': ViolationType.NO_COMPARISON_EVALUATION.value,
                    'message': f'{person_name}: 複数候補の比較評価が不十分',
                    'severity': 'low'
                })

        return violations
'''

# _calculate_grade の前に挿入する位置を探す
insert_index = -1
for i, line in enumerate(lines):
    if 'def _calculate_grade' in line:
        insert_index = i
        break

if insert_index > 0:
    # メソッドを挿入
    lines.insert(insert_index, new_method + '\n')

    # ファイルに書き戻す
    with open('pdca_guardian.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("✅ PDCAガーディアンにcheck_sensational_valueメソッドを追加しました")
else:
    print("❌ 挿入位置が見つかりませんでした")