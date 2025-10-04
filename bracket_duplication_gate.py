#!/usr/bin/env python3
"""
Bracket Duplication Quality Gate

括弧内ワード重複チェックゲート
エピソード本文に括弧内ワードが重複している場合は即失格
"""

from dataclasses import dataclass
from typing import Optional
from bracket_display_engine import BracketDisplayEngine


@dataclass
class BracketDuplicationGateResult:
    """括弧重複ゲート結果"""
    passed: bool
    score: float  # 1.0 (pass) or 0.0 (fail)
    has_duplication: bool
    duplications: list
    reason: str


class BracketDuplicationGate:
    """
    括弧内ワード重複チェックゲート

    重複検出時は即失格（score = 0.0）
    """

    def __init__(self):
        """初期化"""
        self.bracket_engine = BracketDisplayEngine()
        self.gate_name = "bracket_duplication_check"
        self.min_score = 1.0  # 重複なし = 1.0, 重複あり = 0.0

    def evaluate(
        self,
        episode_text: str,
        bracket_word: Optional[str],
        person_name: str,
        show_bracket: bool = True
    ) -> BracketDuplicationGateResult:
        """
        重複チェック

        Args:
            episode_text: エピソード本文
            bracket_word: 括弧内ワード
            person_name: 人物名
            show_bracket: 括弧表示フラグ

        Returns:
            BracketDuplicationGateResult
        """
        # 括弧表示なしの場合は常に合格
        if not show_bracket or not bracket_word:
            return BracketDuplicationGateResult(
                passed=True,
                score=1.0,
                has_duplication=False,
                duplications=[],
                reason="括弧表示なし（チェック対象外）"
            )

        # 重複検証
        is_valid, duplications = self.bracket_engine.validate_no_word_duplication(
            episode_text=episode_text,
            bracket_word=bracket_word,
            person_name=person_name
        )

        if is_valid:
            return BracketDuplicationGateResult(
                passed=True,
                score=1.0,
                has_duplication=False,
                duplications=[],
                reason="括弧内ワード重複なし"
            )
        else:
            return BracketDuplicationGateResult(
                passed=False,
                score=0.0,
                has_duplication=True,
                duplications=duplications,
                reason=f"括弧内ワード「{bracket_word}」がエピソード本文に重複"
            )

    def get_gate_info(self) -> dict:
        """ゲート情報を取得"""
        return {
            'name': self.gate_name,
            'description': '括弧内ワードの重複チェック',
            'min_score': self.min_score,
            'weight': 1.0,
            'strict': True  # 重複検出時は即失格
        }


def test_bracket_duplication_gate():
    """テスト実行"""
    print("=" * 80)
    print("Bracket Duplication Gate - テスト")
    print("=" * 80)

    gate = BracketDuplicationGate()

    # テストケース
    test_cases = [
        {
            'name': '重複なし（正常）',
            'episode_text': '上田晋也(くりぃむしちゅー)は30歳のときにコンビとして大きな転機を迎えた。',
            'bracket_word': 'くりぃむしちゅー',
            'person_name': '上田晋也',
            'show_bracket': True,
            'expected_pass': True
        },
        {
            'name': '重複あり（失格）',
            'episode_text': '上田晋也(くりぃむしちゅー)は30歳のときにくりぃむしちゅーを結成した。',
            'bracket_word': 'くりぃむしちゅー',
            'person_name': '上田晋也',
            'show_bracket': True,
            'expected_pass': False
        },
        {
            'name': '括弧表示なし（常に合格）',
            'episode_text': 'HIKAKINは30歳のときにYouTuberとして大きな転機を迎えた。',
            'bracket_word': None,
            'person_name': 'HIKAKIN',
            'show_bracket': False,
            'expected_pass': True
        },
        {
            'name': '架空キャラクター - 重複なし',
            'episode_text': 'さくらももこ(ちびまる子ちゃん)は30歳のとき作品の映画化を手掛けた。',
            'bracket_word': 'ちびまる子ちゃん',
            'person_name': 'さくらももこ',
            'show_bracket': True,
            'expected_pass': True
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nテスト {i}: {test_case['name']}")
        print("-" * 60)

        result = gate.evaluate(
            episode_text=test_case['episode_text'],
            bracket_word=test_case['bracket_word'],
            person_name=test_case['person_name'],
            show_bracket=test_case['show_bracket']
        )

        status = "✅ PASS" if result.passed else "❌ FAIL"
        expected_status = "✅" if test_case['expected_pass'] else "❌"

        print(f"結果: {status}")
        print(f"期待値: {expected_status}")
        print(f"スコア: {result.score:.1f}/1.0")
        print(f"重複検出: {result.has_duplication}")
        if result.duplications:
            print(f"重複箇所: {result.duplications}")
        print(f"理由: {result.reason}")

        # 検証
        if result.passed == test_case['expected_pass']:
            print("✅ テスト成功")
        else:
            print("❌ テスト失敗")

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == '__main__':
    test_bracket_duplication_gate()
