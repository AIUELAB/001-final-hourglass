"""
Instant Quality Gate System
============================

生成直後の即時検証システム
LLM評価前に高速でチェックし、明らかな失敗を検出

Phase 1: Foundation - Instant Quality Gate
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class QualityGateResult:
    """品質ゲート検証結果"""
    passed: bool
    total_score: float
    checks: Dict[str, bool]
    failures: List[str]
    suggestions: List[str]
    details: Dict[str, any]


class InstantQualityGate:
    """
    即時品質ゲート

    生成されたエピソードを高速検証：
    1. キーワード存在チェック
    2. 数値カウント
    3. 文字数確認
    4. 年齢一致検証
    """

    # 必須キーワード
    ANXIETY_KEYWORDS = [
        '本当に', '不安', '懸念', '心配', '葛藤', '?', 'だろうか',
        'できるのか', '疑問', '批判', '反対', '無理', '懐疑',
        '「', '」'  # 引用符の存在
    ]

    RISK_KEYWORDS = [
        '初めて', '前例なく', '無名', '断行', '挑戦', '賭け', '決断',
        '覚悟', '逆境', '挫折', '乗り越え', 'ハンデ', '若さ',
        '困難', '障害'
    ]

    TURNING_POINT_KEYWORDS = [
        '転機', '決断', 'もたらした', '切り開いた', '押し上げた',
        '確立した', '達成した', '成し遂げた', '築いた', '実現した',
        '駆け上がった', '刻んだ'
    ]

    # 強い動詞
    STRONG_VERBS = [
        '駆け上がった', '切り開いた', 'もたらした', '押し上げた',
        '確立した', '達成した', '成し遂げた', '築いた', '実現した',
        '刻んだ', '変えた', '示した'
    ]

    def __init__(
        self,
        min_chars: int = 180,
        max_chars: int = 250,
        min_numbers: int = 2,  # 2個以上（3個推奨だが2個でも許容）
        min_anxiety_keywords: int = 1,
        min_risk_keywords: int = 1,
        min_turning_point_keywords: int = 1,
        strict_mode: bool = False  # 厳格モード（3個必須）
    ):
        """初期化"""
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.min_numbers = 3 if strict_mode else min_numbers  # 厳格モードでは3個必須
        self.min_anxiety_keywords = min_anxiety_keywords
        self.min_risk_keywords = min_risk_keywords
        self.min_turning_point_keywords = min_turning_point_keywords
        self.strict_mode = strict_mode

    def validate(
        self,
        episode_text: str,
        target_age: int,
        person_name: Optional[str] = None
    ) -> QualityGateResult:
        """
        エピソードを即時検証

        Args:
            episode_text: エピソードテキスト
            target_age: 対象年齢
            person_name: 人物名（オプション）

        Returns:
            QualityGateResult
        """
        checks = {}
        failures = []
        suggestions = []
        details = {}

        # 1. 文字数チェック
        char_count = len(episode_text)
        chars_ok = self.min_chars <= char_count <= self.max_chars
        checks['character_count'] = chars_ok
        details['character_count'] = char_count

        if not chars_ok:
            if char_count < self.min_chars:
                failures.append(f"文字数不足: {char_count}文字（最低{self.min_chars}文字必要）")
                suggestions.append(f"あと{self.min_chars - char_count}文字追加してください")
            else:
                failures.append(f"文字数超過: {char_count}文字（最大{self.max_chars}文字）")
                suggestions.append(f"{char_count - self.max_chars}文字削減してください")

        # 2. 年齢一致チェック
        age_match = self._check_age_match(episode_text, target_age)
        checks['age_match'] = age_match
        details['target_age'] = target_age

        if not age_match:
            failures.append(f"{target_age}歳時点のエピソードではありません")
            suggestions.append(f"「{target_age}歳のとき」を明示してください")

        # 注: 対象年齢の数値は除外（冒頭の「XX歳のとき」）
        age_pattern_to_exclude = f'{target_age}歳'

        # 3. キーワードチェック
        anxiety_found, anxiety_list = self._find_keywords(episode_text, self.ANXIETY_KEYWORDS)
        anxiety_ok = len(anxiety_list) >= self.min_anxiety_keywords
        checks['anxiety_keywords'] = anxiety_ok
        details['anxiety_keywords'] = anxiety_list

        if not anxiety_ok:
            failures.append(f"不安・葛藤キーワード不足: {len(anxiety_list)}個（最低{self.min_anxiety_keywords}個必要）")
            suggestions.append("「本当に〜？」「〜だろうか」等の不安表現を追加")

        risk_found, risk_list = self._find_keywords(episode_text, self.RISK_KEYWORDS)
        risk_ok = len(risk_list) >= self.min_risk_keywords
        checks['risk_keywords'] = risk_ok
        details['risk_keywords'] = risk_list

        if not risk_ok:
            failures.append(f"リスクキーワード不足: {len(risk_list)}個（最低{self.min_risk_keywords}個必要）")
            suggestions.append("「初めて」「無名」「挑戦」等のリスク表現を追加")

        turning_found, turning_list = self._find_keywords(episode_text, self.TURNING_POINT_KEYWORDS)
        turning_ok = len(turning_list) >= self.min_turning_point_keywords
        checks['turning_point_keywords'] = turning_ok
        details['turning_point_keywords'] = turning_list

        if not turning_ok:
            failures.append(f"転機キーワード不足: {len(turning_list)}個（最低{self.min_turning_point_keywords}個必要）")
            suggestions.append("「もたらした」「切り開いた」等の強い表現を追加")

        # 4. 数値チェック
        numbers = self._extract_numbers(episode_text)
        numbers_ok = len(numbers) >= self.min_numbers
        checks['numerical_data'] = numbers_ok
        details['numbers'] = numbers
        details['number_count'] = len(numbers)

        if not numbers_ok:
            failures.append(f"数値不足: {len(numbers)}個（最低{self.min_numbers}個必要）")
            suggestions.append(f"あと{self.min_numbers - len(numbers)}個の具体的数値を追加（金額、人数、期間等）")

        # 5. 引用符チェック
        has_quotes = '「' in episode_text and '」' in episode_text
        checks['has_quotes'] = has_quotes
        details['has_quotes'] = has_quotes

        if not has_quotes:
            failures.append("引用符「」がありません")
            suggestions.append("不安・懸念を「本当に〜？」のように引用符で明示")

        # 6. 強い動詞チェック
        strong_verbs_found, verb_list = self._find_keywords(episode_text, self.STRONG_VERBS)
        has_strong_verb = len(verb_list) > 0
        checks['strong_verbs'] = has_strong_verb
        details['strong_verbs'] = verb_list

        if not has_strong_verb:
            failures.append("強い動詞がありません")
            suggestions.append("「駆け上がった」「切り開いた」等の印象的な動詞を使用")

        # 7. 人物名チェック（オプション）
        if person_name:
            has_person_name = person_name in episode_text
            checks['person_name'] = has_person_name
            details['person_name'] = person_name

            if not has_person_name:
                failures.append(f"人物名「{person_name}」が含まれていません")
                suggestions.append(f"冒頭に「{person_name}は〜」を追加")

        # 総合判定（重要項目のみ必須）
        # 必須項目: 文字数、年齢一致、人物名
        critical_checks = ['character_count', 'age_match']
        if person_name:
            critical_checks.append('person_name')

        # 重要項目がすべてパスしていればOK
        passed = all(checks.get(key, True) for key in critical_checks)

        # スコア計算（各項目を10点満点で評価）
        scores = []

        # 文字数スコア（180-250の範囲内なら10点、外れるほど減点）
        if chars_ok:
            scores.append(10.0)
        else:
            deviation = min(abs(char_count - self.min_chars), abs(char_count - self.max_chars))
            scores.append(max(0, 10 - deviation / 10))

        # 年齢一致スコア
        scores.append(10.0 if age_match else 0.0)

        # キーワードスコア（各カテゴリ）
        scores.append(min(10.0, len(anxiety_list) * 5))
        scores.append(min(10.0, len(risk_list) * 5))
        scores.append(min(10.0, len(turning_list) * 3))

        # 数値スコア
        scores.append(min(10.0, len(numbers) * 3))

        # 引用符スコア
        scores.append(10.0 if has_quotes else 0.0)

        # 強い動詞スコア
        scores.append(min(10.0, len(verb_list) * 5))

        total_score = sum(scores) / len(scores)

        return QualityGateResult(
            passed=passed,
            total_score=total_score,
            checks=checks,
            failures=failures,
            suggestions=suggestions,
            details=details
        )

    def _check_age_match(self, text: str, target_age: int) -> bool:
        """年齢一致チェック"""
        # 「XX歳のとき」「XX歳時点」等のパターンを探す
        patterns = [
            rf'{target_age}歳のとき',
            rf'{target_age}歳時点',
            rf'同じ{target_age}歳',
        ]

        for pattern in patterns:
            if re.search(pattern, text):
                return True

        return False

    def _find_keywords(self, text: str, keywords: List[str]) -> Tuple[bool, List[str]]:
        """キーワード検索"""
        found = []
        for keyword in keywords:
            if keyword in text:
                found.append(keyword)

        return len(found) > 0, found

    def _extract_numbers(self, text: str) -> List[str]:
        """数値を抽出"""
        # 数値パターン: 1234, 1,234, 1.234, 100万, 10億, 10% 等
        patterns = [
            r'\d+億円?',
            r'\d+兆円?',
            r'\d+万円?',
            r'\d+千円?',
            r'\d+[,，]\d+',  # カンマ区切り
            r'\d+%',
            r'\d+歳(?!のとき|時点)',  # 年齢（「〜歳のとき」「〜歳時点」以外）
            r'\d+年(?!間)',  # 年（「〜年間」以外）
            r'\d+年間',
            r'\d+ヶ?月',
            r'\d+日',
            r'\d+時間',
            r'\d+回',
            r'\d+本',
            r'\d+人',
            r'\d+社',
            r'\d+作品?',
            r'\d+位',
            r'\d+勝',
            r'\d+敗',
            r'\d+\.?\d+点',
            r'\d+\.?\d+秒',
        ]

        numbers = []
        seen = set()  # 重複チェック用

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 数値部分を抽出して重複判定
                num_part = re.search(r'\d+', match).group()
                # 同じ数値でも単位が違えば別としてカウント
                if match not in seen:
                    numbers.append(match)
                    seen.add(match)

        return numbers

    def generate_improvement_prompt(self, result: QualityGateResult, original_text: str) -> str:
        """
        改善プロンプトを生成

        Args:
            result: 検証結果
            original_text: 元のエピソード

        Returns:
            改善指示プロンプト
        """
        if result.passed:
            return ""

        prompt = f"""# エピソード改善指示

以下のエピソードは品質基準を満たしていません。具体的に修正してください。

## 元のエピソード
{original_text}

## 問題点
"""
        for i, failure in enumerate(result.failures, 1):
            prompt += f"{i}. {failure}\n"

        prompt += "\n## 改善方法\n"
        for i, suggestion in enumerate(result.suggestions, 1):
            prompt += f"{i}. {suggestion}\n"

        prompt += f"\n## 詳細情報\n"
        prompt += f"- 文字数: {result.details.get('character_count', 0)}文字\n"
        prompt += f"- 数値: {result.details.get('number_count', 0)}個\n"
        prompt += f"- 不安キーワード: {len(result.details.get('anxiety_keywords', []))}個\n"
        prompt += f"- リスクキーワード: {len(result.details.get('risk_keywords', []))}個\n"
        prompt += f"- 転機キーワード: {len(result.details.get('turning_point_keywords', []))}個\n"

        prompt += "\n改善したエピソードを出力してください（説明不要）。"

        return prompt


def main():
    """メイン処理 - デモンストレーション"""
    print("=" * 60)
    print("🚦 Instant Quality Gate Demo")
    print("=" * 60)

    gate = InstantQualityGate()

    # テストケース
    test_cases = [
        {
            "name": "良いエピソード例（新垣結衣）",
            "text": """あなたと同じ18歳のとき、新垣結衣は主演映画『恋空』が興行収入39億円の大ヒットを記録した。しかし「演技経験が少ない新人に大作主演は無理」という映画業界の強い反対があった。オーディションで何度も落選し、沖縄出身というハンデを乗り越えて勝ち取った役だった。撮影中も「なぜこの子が主演？」という批判の声が絶えなかったが、透明感のある演技で日本アカデミー賞新人俳優賞を受賞。この年CM出演社数は10社を超え、「ガッキー」の愛称で国民的女優への階段を駆け上がった。""",
            "age": 18
        },
        {
            "name": "悪いエピソード例（キーワード不足）",
            "text": """あなたと同じ30歳のとき、田中太郎は大きな成功を収めた。素晴らしい実績を残し、多くの人から評価された。""",
            "age": 30
        },
        {
            "name": "文字数不足の例",
            "text": """あなたと同じ25歳のとき、山田花子はビジネスで成功した。売上100億円。""",
            "age": 25
        }
    ]

    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"📝 {case['name']}")
        print(f"{'='*60}\n")

        result = gate.validate(
            episode_text=case['text'],
            target_age=case['age']
        )

        print(f"✅ 合否: {'PASS ✅' if result.passed else 'FAIL ❌'}")
        print(f"📊 スコア: {result.total_score:.1f}/10.0")
        print(f"\n🔍 詳細チェック:")
        for check_name, passed in result.checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")

        if not result.passed:
            print(f"\n❌ 問題点:")
            for i, failure in enumerate(result.failures, 1):
                print(f"  {i}. {failure}")

            print(f"\n💡 改善提案:")
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"  {i}. {suggestion}")

            print(f"\n📋 詳細情報:")
            print(f"  - 文字数: {result.details['character_count']}")
            print(f"  - 数値: {result.details['number_count']}個")
            print(f"  - 不安キーワード: {result.details.get('anxiety_keywords', [])}")
            print(f"  - リスクキーワード: {result.details.get('risk_keywords', [])}")

    print(f"\n{'='*60}")
    print("✅ Demo Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
