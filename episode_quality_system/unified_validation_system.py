#!/usr/bin/env python3
"""
統合バリデーションシステム
すべてのエピソード生成が必ず通過する統一バリデーション機構

このシステムを通らない限り、エピソードは作成できない
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import sys

# 既存のバリデータをインポート
sys.path.append(str(Path(__file__).parent))
from template_blocker import TemplateBlocker, ViolationType
from realtime_validator import RealTimeValidator, ValidationStatus
from proper_noun_validation_system import ProperNounValidationSystem
from enhanced_proper_noun_validation import EnhancedProperNounValidation


class ValidationLevel(Enum):
    """バリデーションレベル"""
    CRITICAL = "CRITICAL"  # 即座に拒否
    ERROR = "ERROR"        # 修正必須
    WARNING = "WARNING"    # 修正推奨
    INFO = "INFO"          # 情報提供
    PASS = "PASS"          # 合格


@dataclass
class ValidationIssue:
    """バリデーション問題"""
    validator_name: str
    level: ValidationLevel
    message: str
    position: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """バリデーション結果"""
    is_valid: bool
    overall_level: ValidationLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue):
        """問題を追加"""
        self.issues.append(issue)
        # 最も深刻なレベルに更新
        if issue.level == ValidationLevel.CRITICAL:
            self.overall_level = ValidationLevel.CRITICAL
            self.is_valid = False
        elif issue.level == ValidationLevel.ERROR and self.overall_level != ValidationLevel.CRITICAL:
            self.overall_level = ValidationLevel.ERROR
            self.is_valid = False


class BaseValidator:
    """バリデータの基底クラス"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        """バリデーション実行（サブクラスで実装）"""
        raise NotImplementedError


class TemplateValidator(BaseValidator):
    """テンプレート文章検証"""

    def __init__(self):
        super().__init__("TemplateValidator")
        self.blocker = TemplateBlocker()

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        issues = []
        should_block, violations = self.blocker.check_episode(episode)

        if should_block:
            for violation in violations:
                level = ValidationLevel.CRITICAL if violation.type == ViolationType.TEMPLATE else ValidationLevel.ERROR
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=level,
                    message=f"テンプレート検出: {violation.pattern if hasattr(violation, 'pattern') else 'テンプレート文章'}",
                    position=violation.position if hasattr(violation, 'position') else None,
                    suggestion=violation.suggestion if hasattr(violation, 'suggestion') else None
                ))

        return issues


class ProperNounValidator(BaseValidator):
    """固有名詞検証"""

    def __init__(self):
        super().__init__("ProperNounValidator")
        self.enhanced_validator = EnhancedProperNounValidation()

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        issues = []
        validation = self.enhanced_validator.validate_episode(person_name, episode)

        if not validation['is_valid']:
            # 作品名の欠如は最も深刻
            if not validation['has_work_title'] and validation['category'] in ['entertainment', 'literature']:
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=ValidationLevel.CRITICAL,
                    message="作品名（「」付き）が必須です",
                    suggestion="具体的な作品名を「」で囲んで追加してください"
                ))

            # その他の欠落要素
            for missing in validation.get('missing_elements', []):
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=ValidationLevel.ERROR,
                    message=missing,
                    suggestion="具体的な固有名詞を追加してください"
                ))

        return issues


class CharacterCountValidator(BaseValidator):
    """文字数検証"""

    def __init__(self):
        super().__init__("CharacterCountValidator")
        self.min_chars = 132
        self.max_chars = 250

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        issues = []
        char_count = len(episode)

        if char_count < self.min_chars:
            issues.append(ValidationIssue(
                validator_name=self.name,
                level=ValidationLevel.ERROR,
                message=f"文字数不足: {char_count}文字（最小{self.min_chars}文字）",
                suggestion=f"あと{self.min_chars - char_count}文字追加してください"
            ))
        elif char_count > self.max_chars:
            issues.append(ValidationIssue(
                validator_name=self.name,
                level=ValidationLevel.ERROR,
                message=f"文字数超過: {char_count}文字（最大{self.max_chars}文字）",
                suggestion=f"{char_count - self.max_chars}文字削減してください"
            ))

        return issues


class ObjectivityValidator(BaseValidator):
    """客観性検証"""

    def __init__(self):
        super().__init__("ObjectivityValidator")
        self.subjective_terms = [
            '素晴らしい', '凄い', '驚くべき', '感動的', '衝撃的',
            '圧倒的', '革命的', '画期的', '歴史的偉業', '驚異的',
            '奇跡的', '伝説的', '劇的', '前人未到', '空前絶後'
        ]
        self.vague_terms = [
            '多くの', '様々な', '数々の', 'たくさんの', '無数の',
            '重要な成果', '大きな影響', '多大な貢献', '素晴らしい業績'
        ]

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        issues = []

        # 主観的表現のチェック
        for term in self.subjective_terms:
            if term in episode:
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=ValidationLevel.ERROR,
                    message=f"主観的表現: '{term}'",
                    suggestion="具体的な事実や数値に置き換えてください"
                ))

        # 曖昧表現のチェック
        for term in self.vague_terms:
            if term in episode:
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=ValidationLevel.WARNING,
                    message=f"曖昧表現: '{term}'",
                    suggestion="具体的な数値や事例を使用してください"
                ))

        return issues


class NounEndingValidator(BaseValidator):
    """名詞終了検証"""

    def __init__(self):
        super().__init__("NounEndingValidator")
        self.noun_endings = ['革命児', '先駆者', '巨人', '天才', 'レジェンド', 'パイオニア', '第一人者']

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        issues = []

        for noun in self.noun_endings:
            if episode.endswith(f'{noun}。'):
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=ValidationLevel.ERROR,
                    message=f"名詞で終了: '{noun}。'",
                    suggestion=f"'{noun}となった。'や'{noun}として知られる。'に変更してください"
                ))

        return issues


class DateNoiseValidator(BaseValidator):
    """日付ノイズ検証"""

    def __init__(self):
        super().__init__("DateNoiseValidator")
        self.date_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日午[前後]\d+時',
            r'午[前後]\d+時\d+分',
            r'\d+時\d+分\d+秒'
        ]

    def validate(self, episode: str, person_name: str, age: int, **kwargs) -> List[ValidationIssue]:
        issues = []

        for pattern in self.date_patterns:
            if re.search(pattern, episode):
                issues.append(ValidationIssue(
                    validator_name=self.name,
                    level=ValidationLevel.WARNING,
                    message="詳細すぎる日時指定",
                    suggestion="年月程度に簡略化してください"
                ))
                break

        return issues


class UnifiedValidationSystem:
    """統合バリデーションシステム"""

    def __init__(self):
        """初期化"""
        # すべてのバリデータを登録（順序重要）
        self.validators = [
            CharacterCountValidator(),    # まず文字数
            TemplateValidator(),          # テンプレート排除
            ProperNounValidator(),        # 固有名詞必須
            ObjectivityValidator(),       # 客観性確保
            NounEndingValidator(),        # 名詞終了修正
            DateNoiseValidator()          # 日付ノイズ除去
        ]

        # リアルタイムバリデータ（別扱い）
        self.realtime_validator = RealTimeValidator()

        # 統計情報
        self.stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'critical_failures': 0
        }

    def validate(self, episode: str, person_name: str, age: int = 30,
                 strict_mode: bool = True) -> ValidationResult:
        """
        エピソードを完全検証

        Args:
            episode: エピソード文
            person_name: 人物名
            age: 年齢
            strict_mode: 厳格モード（1つでもERROR以上があれば失敗）

        Returns:
            ValidationResult: 検証結果
        """
        self.stats['total_validations'] += 1

        # 結果オブジェクト初期化
        result = ValidationResult(
            is_valid=True,
            overall_level=ValidationLevel.PASS,
            score=100.0
        )

        # メタデータ設定
        result.metadata = {
            'episode_length': len(episode),
            'person_name': person_name,
            'age': age,
            'validators_run': len(self.validators)
        }

        # 各バリデータを実行
        for validator in self.validators:
            if not validator.enabled:
                continue

            try:
                issues = validator.validate(episode, person_name, age)
                for issue in issues:
                    result.add_issue(issue)

                    # スコア減点
                    if issue.level == ValidationLevel.CRITICAL:
                        result.score -= 30
                    elif issue.level == ValidationLevel.ERROR:
                        result.score -= 15
                    elif issue.level == ValidationLevel.WARNING:
                        result.score -= 5

            except Exception as e:
                # バリデータエラーも記録
                result.add_issue(ValidationIssue(
                    validator_name=validator.name,
                    level=ValidationLevel.ERROR,
                    message=f"バリデータエラー: {str(e)}"
                ))

        # リアルタイムバリデータの実行
        rt_result = self.realtime_validator.validate_full_episode(episode)
        if rt_result['status'] == ValidationStatus.BLOCK:
            result.add_issue(ValidationIssue(
                validator_name="RealTimeValidator",
                level=ValidationLevel.CRITICAL,
                message="リアルタイム検証で致命的問題検出"
            ))

        # スコアの正規化
        result.score = max(0, min(100, result.score))

        # 厳格モードでの判定
        if strict_mode:
            if result.overall_level in [ValidationLevel.CRITICAL, ValidationLevel.ERROR]:
                result.is_valid = False

        # 統計更新
        if result.is_valid:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
            if result.overall_level == ValidationLevel.CRITICAL:
                self.stats['critical_failures'] += 1

        return result

    def validate_batch(self, episodes: List[Dict[str, Any]],
                      strict_mode: bool = True) -> List[ValidationResult]:
        """
        複数エピソードを一括検証

        Args:
            episodes: エピソードのリスト（person_name, age, episode を含む辞書）
            strict_mode: 厳格モード

        Returns:
            検証結果のリスト
        """
        results = []
        for ep_data in episodes:
            result = self.validate(
                episode=ep_data.get('episode', ''),
                person_name=ep_data.get('person_name', ''),
                age=ep_data.get('age', 30),
                strict_mode=strict_mode
            )
            results.append(result)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = self.stats.copy()
        if stats['total_validations'] > 0:
            stats['pass_rate'] = stats['passed'] / stats['total_validations'] * 100
            stats['critical_rate'] = stats['critical_failures'] / stats['total_validations'] * 100
        else:
            stats['pass_rate'] = 0
            stats['critical_rate'] = 0

        return stats

    def reset_stats(self):
        """統計をリセット"""
        self.stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'critical_failures': 0
        }

    def enable_validator(self, validator_name: str):
        """特定のバリデータを有効化"""
        for validator in self.validators:
            if validator.name == validator_name:
                validator.enabled = True
                return True
        return False

    def disable_validator(self, validator_name: str):
        """特定のバリデータを無効化"""
        for validator in self.validators:
            if validator.name == validator_name:
                validator.enabled = False
                return True
        return False

    def get_validator_names(self) -> List[str]:
        """バリデータ名のリストを取得"""
        return [v.name for v in self.validators]


def test_unified_validation():
    """統合バリデーションのテスト"""
    validator = UnifiedValidationSystem()

    # テストケース
    test_episodes = [
        {
            'person_name': '大谷翔平',
            'age': 29,
            'episode': 'あなたと同じ29歳のとき、大谷翔平は素晴らしい活躍をした。',  # テンプレート＋主観的
            'expected': False
        },
        {
            'person_name': '村上春樹',
            'age': 38,
            'episode': 'あなたと同じ38歳のとき、村上春樹は「ノルウェイの森」を発表し上下巻430万部の大ベストセラーとなった。',
            'expected': True
        },
        {
            'person_name': '新海誠',
            'age': 43,
            'episode': 'あなたと同じ43歳のとき、新海誠は歴史的偉業を成し遂げた革命児。',  # 主観的＋名詞終了
            'expected': False
        }
    ]

    print("統合バリデーションシステムテスト")
    print("=" * 60)

    for i, test_case in enumerate(test_episodes, 1):
        print(f"\nテストケース {i}: {test_case['person_name']}")
        print(f"エピソード: {test_case['episode'][:50]}...")

        result = validator.validate(
            episode=test_case['episode'],
            person_name=test_case['person_name'],
            age=test_case['age'],
            strict_mode=True
        )

        print(f"検証結果: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
        print(f"スコア: {result.score:.1f}/100")
        print(f"レベル: {result.overall_level.value}")

        if result.issues:
            print("検出された問題:")
            for issue in result.issues[:3]:  # 最初の3つだけ表示
                print(f"  - [{issue.level.value}] {issue.message}")

        # 期待結果との比較
        if result.is_valid == test_case['expected']:
            print(f"✅ テスト成功（期待通り）")
        else:
            print(f"❌ テスト失敗（期待と異なる結果）")

    # 統計表示
    print(f"\n{'=' * 60}")
    print("統計情報:")
    stats = validator.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_unified_validation()
