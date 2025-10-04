"""
Auto Fix Engine
===============

品質ゲートで検出された問題を自動修正する提案エンジン

Phase 2: Auto-fix - Automatic Improvement System
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from instant_quality_gate import QualityGateResult, InstantQualityGate


@dataclass
class FixTemplate:
    """修正テンプレート"""
    problem_type: str
    template: str
    example: str
    priority: int  # 1=高, 2=中, 3=低


class AutoFixEngine:
    """
    自動修正エンジン

    InstantQualityGateの結果から具体的な修正案を生成
    """

    # 不安・葛藤の追加テンプレート
    ANXIETY_TEMPLATES = [
        FixTemplate(
            problem_type="anxiety_missing",
            template='「{doubt_phrase}」という{stakeholder}の懸念',
            example='「本当にこの人で大丈夫か？」という業界の懸念',
            priority=1
        ),
        FixTemplate(
            problem_type="anxiety_missing",
            template='{stakeholder}から「{criticism}」という批判',
            example='制作陣から「経験不足だ」という批判',
            priority=1
        ),
        FixTemplate(
            problem_type="anxiety_missing",
            template='「{worry}」という不安の声',
            example='「失敗するのではないか」という不安の声',
            priority=2
        ),
    ]

    # リスク追加テンプレート
    RISK_TEMPLATES = [
        FixTemplate(
            problem_type="risk_missing",
            template='{industry}で初めて{action}',
            example='業界で初めて週休2日制を導入',
            priority=1
        ),
        FixTemplate(
            problem_type="risk_missing",
            template='{period}の{adjective}{challenge}',
            example='わずか3ヶ月の無謀な挑戦',
            priority=1
        ),
        FixTemplate(
            problem_type="risk_missing",
            template='{handicap}を乗り越えて',
            example='無名の新人というハンデを乗り越えて',
            priority=2
        ),
        FixTemplate(
            problem_type="risk_missing",
            template='{opposition}の中、{action}を断行',
            example='業界の猛反対の中、改革を断行',
            priority=1
        ),
    ]

    # 数値追加テンプレート
    NUMBER_TEMPLATES = [
        FixTemplate(
            problem_type="numbers_missing",
            template='{amount}円の{result}',
            example='39億円の大ヒット',
            priority=1
        ),
        FixTemplate(
            problem_type="numbers_missing",
            template='{count}人を超える{group}',
            example='10万人を超える従業員',
            priority=2
        ),
        FixTemplate(
            problem_type="numbers_missing",
            template='{period}間の{effort}',
            example='28年間の努力',
            priority=2
        ),
        FixTemplate(
            problem_type="numbers_missing",
            template='{metric}%の{improvement}',
            example='20%の生産性向上',
            priority=2
        ),
    ]

    # 強い動詞の置換候補
    STRONG_VERB_REPLACEMENTS = {
        '成功した': '成し遂げた',
        '変化した': '転機をもたらした',
        '達成した': '切り開いた',
        '成長した': '押し上げた',
        '実現した': '実現した',  # そのまま
        '作った': '築いた',
        '変えた': '変えた',  # そのまま
        '示した': '示した',  # そのまま
    }

    def __init__(self):
        """初期化"""
        self.gate = InstantQualityGate()

    def generate_fix_suggestions(
        self,
        episode_text: str,
        gate_result: QualityGateResult,
        target_age: int,
        person_name: Optional[str] = None
    ) -> Dict[str, any]:
        """
        修正提案を生成

        Args:
            episode_text: 元のエピソード
            gate_result: 品質ゲート結果
            target_age: 対象年齢
            person_name: 人物名

        Returns:
            修正提案の辞書
        """
        suggestions = {
            'original_text': episode_text,
            'fixes': [],
            'priority_order': [],
            'estimated_improvement': 0.0
        }

        # 1. 不安・葛藤キーワードの追加
        if not gate_result.checks.get('anxiety_keywords', True):
            anxiety_fixes = self._suggest_anxiety_fixes(episode_text, person_name)
            suggestions['fixes'].extend(anxiety_fixes)

        # 2. リスクキーワードの追加
        if not gate_result.checks.get('risk_keywords', True):
            risk_fixes = self._suggest_risk_fixes(episode_text)
            suggestions['fixes'].extend(risk_fixes)

        # 3. 数値の追加
        if not gate_result.checks.get('numerical_data', True):
            number_fixes = self._suggest_number_fixes(episode_text, gate_result)
            suggestions['fixes'].extend(number_fixes)

        # 4. 強い動詞の置換
        if not gate_result.checks.get('strong_verbs', True):
            verb_fixes = self._suggest_verb_replacements(episode_text)
            suggestions['fixes'].extend(verb_fixes)

        # 5. 引用符の追加
        if not gate_result.checks.get('has_quotes', True):
            quote_fixes = self._suggest_quote_additions(episode_text)
            suggestions['fixes'].extend(quote_fixes)

        # 6. 文字数調整
        if not gate_result.checks.get('character_count', True):
            char_fixes = self._suggest_character_adjustments(
                episode_text,
                gate_result.details.get('character_count', 0)
            )
            suggestions['fixes'].extend(char_fixes)

        # 優先順位でソート
        suggestions['fixes'].sort(key=lambda x: x['priority'])
        suggestions['priority_order'] = [f['type'] for f in suggestions['fixes']]

        # 改善度推定
        suggestions['estimated_improvement'] = len(suggestions['fixes']) * 5.0

        return suggestions

    def _suggest_anxiety_fixes(self, text: str, person_name: Optional[str]) -> List[Dict]:
        """不安・葛藤の追加提案"""
        fixes = []

        # パターン1: 「本当に〜？」形式
        fixes.append({
            'type': 'add_anxiety_quote',
            'priority': 1,
            'description': '不安・葛藤の引用符を追加',
            'suggestion': '「本当にこの人で大丈夫か？」という業界の懸念があった。',
            'insertion_point': 'after_first_sentence',
            'example': '「演技経験が少ない新人に大作主演は無理」という映画業界の強い反対があった。'
        })

        # パターン2: 批判の声
        fixes.append({
            'type': 'add_criticism',
            'priority': 2,
            'description': '批判・疑問の声を追加',
            'suggestion': f'周囲から「{person_name or "この人物"}には無理だ」という批判の声が上がった。',
            'insertion_point': 'middle',
            'example': '撮影中も「なぜこの子が主演？」という批判の声が絶えなかった'
        })

        return fixes

    def _suggest_risk_fixes(self, text: str) -> List[Dict]:
        """リスクテイキングの追加提案"""
        fixes = []

        # パターン1: 「初めて」
        fixes.append({
            'type': 'add_first_time',
            'priority': 1,
            'description': '「初めて」「前例なく」を追加',
            'suggestion': '業界で初めて〜を導入し、',
            'insertion_point': 'before_achievement',
            'example': '日本で初めて週休2日制を導入し、労働改革の先駆者となった。'
        })

        # パターン2: ハンデ・逆境
        fixes.append({
            'type': 'add_handicap',
            'priority': 2,
            'description': 'ハンデや逆境を追加',
            'suggestion': '〜というハンデを乗り越え、',
            'insertion_point': 'middle',
            'example': '沖縄出身というハンデを乗り越えて勝ち取った役だった。'
        })

        # パターン3: 具体的期間
        fixes.append({
            'type': 'add_time_constraint',
            'priority': 1,
            'description': '具体的な期間制約を追加',
            'suggestion': 'わずか〜ヶ月で',
            'insertion_point': 'before_achievement',
            'example': 'わずか3ヶ月で断行した決断'
        })

        return fixes

    def _suggest_number_fixes(self, text: str, gate_result: QualityGateResult) -> List[Dict]:
        """数値の追加提案"""
        fixes = []
        current_count = gate_result.details.get('number_count', 0)
        needed = self.gate.min_numbers - current_count

        # 金額
        if needed > 0:
            fixes.append({
                'type': 'add_money_figure',
                'priority': 1,
                'description': '金額を追加',
                'suggestion': '〜億円の売上/興行収入/契約金',
                'insertion_point': 'achievement_description',
                'example': '興行収入39億円の大ヒットを記録した。'
            })

        # 人数
        if needed > 1:
            fixes.append({
                'type': 'add_people_count',
                'priority': 2,
                'description': '人数・規模を追加',
                'suggestion': '〜万人/〜人/〜社',
                'insertion_point': 'impact_description',
                'example': '従業員10万人を超える巨大企業へ。'
            })

        # 期間
        if needed > 2:
            fixes.append({
                'type': 'add_duration',
                'priority': 2,
                'description': '期間を追加',
                'suggestion': '〜年間/〜ヶ月/〜日間',
                'insertion_point': 'effort_description',
                'example': '28年間のプロ野球人生に幕を下ろした。'
            })

        return fixes

    def _suggest_verb_replacements(self, text: str) -> List[Dict]:
        """強い動詞の置換提案"""
        fixes = []

        for weak, strong in self.STRONG_VERB_REPLACEMENTS.items():
            if weak in text and weak != strong:
                fixes.append({
                    'type': 'replace_verb',
                    'priority': 3,
                    'description': f'「{weak}」→「{strong}」に置換',
                    'suggestion': f'「{weak}」を「{strong}」に変更',
                    'original': weak,
                    'replacement': strong,
                    'example': f'松下電器を売上高1兆円企業に{strong}。'
                })

        return fixes

    def _suggest_quote_additions(self, text: str) -> List[Dict]:
        """引用符の追加提案"""
        fixes = []

        # 否定的な表現を探して引用符で囲む提案
        negative_patterns = [
            (r'(無理|できない|不可能|難しい)', '引用符で強調'),
            (r'(反対|批判|懸念|疑問)', '引用符で囲む'),
        ]

        for pattern, description in negative_patterns:
            matches = re.findall(pattern, text)
            if matches and '「' not in text:
                fixes.append({
                    'type': 'add_quotes',
                    'priority': 1,
                    'description': '不安・懸念を引用符で明示',
                    'suggestion': f'「{matches[0]}」という声',
                    'insertion_point': 'near_conflict',
                    'example': '「演技経験が少ない新人に大作主演は無理」という映画業界の強い反対'
                })
                break

        return fixes

    def _suggest_character_adjustments(self, text: str, current_count: int) -> List[Dict]:
        """文字数調整の提案"""
        fixes = []

        if current_count < self.gate.min_chars:
            shortage = self.gate.min_chars - current_count
            fixes.append({
                'type': 'expand_text',
                'priority': 3,
                'description': f'文字数を{shortage}文字追加',
                'suggestion': '具体的な成果、数値、背景を追加',
                'amount': shortage,
                'example': '具体的な金額、人数、期間、成果物を記述'
            })
        elif current_count > self.gate.max_chars:
            excess = current_count - self.gate.max_chars
            fixes.append({
                'type': 'reduce_text',
                'priority': 3,
                'description': f'文字数を{excess}文字削減',
                'suggestion': '冗長な表現を削除',
                'amount': excess,
                'example': '重複表現や説明的な文を削除'
            })

        return fixes

    def apply_fixes_to_prompt(
        self,
        original_text: str,
        fix_suggestions: Dict,
        max_fixes: int = 3
    ) -> str:
        """
        修正提案をプロンプトに変換

        Args:
            original_text: 元のエピソード
            fix_suggestions: 修正提案
            max_fixes: 適用する修正の最大数

        Returns:
            改善指示プロンプト
        """
        top_fixes = fix_suggestions['fixes'][:max_fixes]

        prompt = f"""# エピソード改善タスク

以下のエピソードを改善してください。

## 元のエピソード
{original_text}

## 必須の改善点（優先順位順）

"""

        for i, fix in enumerate(top_fixes, 1):
            prompt += f"### {i}. {fix['description']}\n"
            prompt += f"**提案**: {fix['suggestion']}\n"
            prompt += f"**例**: {fix['example']}\n\n"

        prompt += """## 出力要件

- 上記の改善点をすべて反映してください
- 文字数: 180-250文字
- 元のエピソードの核心的な事実は変えないでください
- 改善したエピソードのみを出力（説明不要）
"""

        return prompt


def main():
    """メイン処理 - デモンストレーション"""
    print("=" * 60)
    print("🔧 Auto Fix Engine Demo")
    print("=" * 60)

    engine = AutoFixEngine()
    gate = InstantQualityGate()

    # テストケース: 品質不足のエピソード
    test_episode = """あなたと同じ30歳のとき、田中太郎は大きな成功を収めた。事業で素晴らしい実績を残し、多くの人から評価を受けた。"""

    print(f"\n📝 元のエピソード:")
    print(test_episode)
    print(f"\n文字数: {len(test_episode)}文字")

    # 品質ゲート検証
    print(f"\n{'='*60}")
    print("🚦 品質ゲート検証")
    print(f"{'='*60}")

    result = gate.validate(test_episode, 30, "田中太郎")

    print(f"\n合否: {'PASS ✅' if result.passed else 'FAIL ❌'}")
    print(f"スコア: {result.total_score:.1f}/10.0")

    if not result.passed:
        print(f"\n❌ 問題点:")
        for i, failure in enumerate(result.failures, 1):
            print(f"  {i}. {failure}")

    # 自動修正提案
    print(f"\n{'='*60}")
    print("🔧 自動修正提案")
    print(f"{'='*60}")

    suggestions = engine.generate_fix_suggestions(
        episode_text=test_episode,
        gate_result=result,
        target_age=30,
        person_name="田中太郎"
    )

    print(f"\n💡 修正提案 ({len(suggestions['fixes'])}個):")
    for i, fix in enumerate(suggestions['fixes'][:5], 1):  # 上位5個
        print(f"\n{i}. [{fix['type']}] {fix['description']}")
        print(f"   提案: {fix['suggestion']}")
        print(f"   例: {fix['example']}")

    # 改善プロンプト生成
    print(f"\n{'='*60}")
    print("📋 改善プロンプト")
    print(f"{'='*60}\n")

    improvement_prompt = engine.apply_fixes_to_prompt(
        original_text=test_episode,
        fix_suggestions=suggestions,
        max_fixes=3
    )

    print(improvement_prompt)

    print(f"\n{'='*60}")
    print("✅ Demo Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
