#!/usr/bin/env python3
"""
RealTimeValidator - リアルタイムバリデーションシステム
エピソード生成中に即座に品質をチェックし、問題を検出
"""

import re
import time
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ValidationStatus(Enum):
    """検証ステータス"""
    PASS = "pass"          # 合格
    WARNING = "warning"    # 警告
    ERROR = "error"        # エラー
    BLOCK = "block"        # ブロック（生成停止）


@dataclass
class ValidationResult:
    """検証結果"""
    status: ValidationStatus
    message: str
    timestamp: datetime
    char_position: Optional[int] = None
    suggestion: Optional[str] = None


class RealTimeValidator:
    """リアルタイムバリデータ"""

    def __init__(self):
        """初期化"""
        # 文字数制限
        self.MIN_LENGTH = 132
        self.MAX_LENGTH = 250

        # リアルタイムチェック用のパターン
        self.realtime_patterns = {
            # 即座にブロックすべきパターン
            "block": [
                (r'その後も', "定型文「その後も」を検出"),
                (r'多くの.*影響', "定型文「多くの～影響」を検出"),
                (r'永遠に.*残', "定型文「永遠に～残」を検出"),
                (r'伝説となった', "定型文「伝説となった」を検出"),
                (r'歴史に名を刻', "定型文「歴史に名を刻」を検出"),
                (r'\d{4}年\d{1,2}月\d{1,2}日', "RULE_164違反：具体的日付は禁止"),
                (r'午[前後]\d+時', "RULE_164違反：時刻表記は禁止")
            ],
            # エラーレベル（修正必須）
            "error": [
                (r'素晴らしい|凄い|驚くべき|感動的', "主観的表現は禁止"),
                (r'(革命児|先駆者|巨人|天才|レジェンド|カリスマ)。$', "名詞終了は禁止"),
                (r'^.{0,50}$', "文章が短すぎます（50文字未満）")
            ],
            # 警告レベル（修正推奨）
            "warning": [
                (r'多くの|たくさんの|様々な|いくつもの', "曖昧な表現を避けてください"),
                (r'約|およそ|ほぼ|だいたい', "正確な数値を使用してください"),
                (r'最も|最高の|最強の|最大の', "最上級表現は事実確認が必要")
            ]
        }

        # 検証履歴
        self.validation_history = []

        # コールバック関数（問題検出時に呼ばれる）
        self.callbacks = {
            ValidationStatus.BLOCK: [],
            ValidationStatus.ERROR: [],
            ValidationStatus.WARNING: [],
            ValidationStatus.PASS: []
        }

    def validate_character(self, text: str, position: int) -> Optional[ValidationResult]:
        """
        1文字入力されるたびに検証

        Args:
            text: 現在のテキスト
            position: 現在の文字位置

        Returns:
            検証結果（問題なければNone）
        """
        # 最新の部分を取得（直近20文字）
        start = max(0, position - 20)
        recent_text = text[start:position]

        # ブロックパターンチェック
        for pattern, message in self.realtime_patterns["block"]:
            if re.search(pattern, recent_text):
                return ValidationResult(
                    status=ValidationStatus.BLOCK,
                    message=message,
                    timestamp=datetime.now(),
                    char_position=position,
                    suggestion="即座に修正が必要です"
                )

        return None

    def validate_sentence(self, sentence: str) -> List[ValidationResult]:
        """
        文単位で検証

        Args:
            sentence: 検証する文

        Returns:
            検証結果のリスト
        """
        results = []

        # 各レベルのパターンをチェック
        for level, patterns in self.realtime_patterns.items():
            for pattern, message in patterns:
                matches = re.finditer(pattern, sentence)
                for match in matches:
                    status = {
                        "block": ValidationStatus.BLOCK,
                        "error": ValidationStatus.ERROR,
                        "warning": ValidationStatus.WARNING
                    }.get(level, ValidationStatus.WARNING)

                    result = ValidationResult(
                        status=status,
                        message=message,
                        timestamp=datetime.now(),
                        char_position=match.start(),
                        suggestion=self._get_suggestion(level, pattern)
                    )
                    results.append(result)

        return results

    def validate_full_episode(self, episode: str) -> Dict[str, any]:
        """
        完全なエピソードを検証

        Args:
            episode: エピソード全文

        Returns:
            検証結果の辞書
        """
        validation = {
            "is_valid": True,
            "status": ValidationStatus.PASS,
            "violations": [],
            "statistics": {
                "length": len(episode),
                "block_count": 0,
                "error_count": 0,
                "warning_count": 0
            },
            "suggestions": []
        }

        # 文字数チェック
        if len(episode) < self.MIN_LENGTH:
            validation["violations"].append({
                "type": "length",
                "status": ValidationStatus.ERROR,
                "message": f"文字数不足: {len(episode)}文字（最低{self.MIN_LENGTH}文字必要）"
            })
            validation["statistics"]["error_count"] += 1
            validation["is_valid"] = False

        elif len(episode) > self.MAX_LENGTH:
            validation["violations"].append({
                "type": "length",
                "status": ValidationStatus.ERROR,
                "message": f"文字数超過: {len(episode)}文字（最大{self.MAX_LENGTH}文字）"
            })
            validation["statistics"]["error_count"] += 1
            validation["is_valid"] = False

        # パターンチェック
        for level, patterns in self.realtime_patterns.items():
            for pattern, message in patterns:
                matches = re.finditer(pattern, episode)
                for match in matches:
                    status = {
                        "block": ValidationStatus.BLOCK,
                        "error": ValidationStatus.ERROR,
                        "warning": ValidationStatus.WARNING
                    }.get(level)

                    validation["violations"].append({
                        "type": "pattern",
                        "status": status,
                        "message": message,
                        "position": match.start(),
                        "matched_text": match.group()[:30]
                    })

                    # 統計更新
                    if status == ValidationStatus.BLOCK:
                        validation["statistics"]["block_count"] += 1
                        validation["is_valid"] = False
                        validation["status"] = ValidationStatus.BLOCK
                    elif status == ValidationStatus.ERROR:
                        validation["statistics"]["error_count"] += 1
                        validation["is_valid"] = False
                        if validation["status"] != ValidationStatus.BLOCK:
                            validation["status"] = ValidationStatus.ERROR
                    elif status == ValidationStatus.WARNING:
                        validation["statistics"]["warning_count"] += 1
                        if validation["status"] == ValidationStatus.PASS:
                            validation["status"] = ValidationStatus.WARNING

        # 事実の存在チェック
        fact_patterns = [r'\d+', r'「[^」]+」', r'優勝|受賞|達成|記録']
        has_facts = any(re.search(p, episode) for p in fact_patterns)

        if not has_facts:
            validation["violations"].append({
                "type": "content",
                "status": ValidationStatus.ERROR,
                "message": "具体的な事実・数値が含まれていません"
            })
            validation["statistics"]["error_count"] += 1
            validation["is_valid"] = False

        # 提案生成
        validation["suggestions"] = self._generate_suggestions(validation["violations"])

        # 履歴に追加
        self._add_to_history(episode, validation)

        return validation

    def _get_suggestion(self, level: str, pattern: str) -> str:
        """
        パターンに応じた提案を取得

        Args:
            level: 違反レベル
            pattern: 正規表現パターン

        Returns:
            提案文
        """
        suggestions = {
            "block": {
                r'その後も': "「その後も」を削除し、具体的な成果を記述",
                r'多くの.*影響': "「多くの～影響」を具体的な影響例に変更",
                r'\d{4}年\d{1,2}月\d{1,2}日': "具体的日付を削除（年齢対比に集中）"
            },
            "error": {
                r'素晴らしい|凄い': "主観的表現を客観的事実に変更",
                r'(革命児|先駆者)。$': "名詞終了を「～となった」等の動詞で終わらせる"
            },
            "warning": {
                r'多くの|たくさんの': "具体的な数を記述",
                r'約|およそ': "正確な数値を使用"
            }
        }

        level_suggestions = suggestions.get(level, {})
        for pattern_key, suggestion in level_suggestions.items():
            if pattern_key in pattern:
                return suggestion

        return "修正が必要です"

    def _generate_suggestions(self, violations: List[Dict]) -> List[str]:
        """
        違反から提案を生成

        Args:
            violations: 違反リスト

        Returns:
            提案リスト
        """
        suggestions = []
        seen = set()

        # 重要度順に提案
        for v in sorted(violations, key=lambda x:
                       0 if x["status"] == ValidationStatus.BLOCK else
                       1 if x["status"] == ValidationStatus.ERROR else 2):

            suggestion = f"{v['message']}を修正"
            if suggestion not in seen:
                suggestions.append(suggestion)
                seen.add(suggestion)

            if len(suggestions) >= 5:  # 最大5件
                break

        return suggestions

    def _add_to_history(self, episode: str, validation: Dict):
        """
        検証履歴に追加

        Args:
            episode: エピソード
            validation: 検証結果
        """
        self.validation_history.append({
            "timestamp": datetime.now(),
            "episode_preview": episode[:50] + "..." if len(episode) > 50 else episode,
            "is_valid": validation["is_valid"],
            "status": validation["status"],
            "violation_count": len(validation["violations"])
        })

        # 履歴は最新100件まで保持
        if len(self.validation_history) > 100:
            self.validation_history = self.validation_history[-100:]

    def register_callback(self, status: ValidationStatus, callback: Callable):
        """
        コールバック関数を登録

        Args:
            status: トリガーとなるステータス
            callback: 呼び出す関数
        """
        if status in self.callbacks:
            self.callbacks[status].append(callback)

    def trigger_callbacks(self, status: ValidationStatus, data: Dict):
        """
        コールバックをトリガー

        Args:
            status: ステータス
            data: コールバックに渡すデータ
        """
        for callback in self.callbacks.get(status, []):
            try:
                callback(data)
            except Exception as e:
                print(f"コールバックエラー: {e}")

    def get_statistics(self) -> Dict:
        """
        統計情報を取得

        Returns:
            統計情報
        """
        if not self.validation_history:
            return {}

        total = len(self.validation_history)
        valid_count = sum(1 for h in self.validation_history if h["is_valid"])

        status_counts = {}
        for h in self.validation_history:
            status = h["status"].value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_validations": total,
            "valid_rate": (valid_count / total * 100) if total > 0 else 0,
            "status_distribution": status_counts,
            "recent_validations": self.validation_history[-10:]
        }


def test_realtime_validator():
    """テスト実行"""
    validator = RealTimeValidator()

    # コールバック関数の例
    def on_block(data):
        print(f"  ⛔ ブロック検出: {data['message']}")

    def on_error(data):
        print(f"  ❌ エラー検出: {data['message']}")

    # コールバック登録
    validator.register_callback(ValidationStatus.BLOCK, on_block)
    validator.register_callback(ValidationStatus.ERROR, on_error)

    # テストケース
    test_cases = [
        {
            "text": "あなたと同じ25歳のとき、大谷翔平は素晴らしい活躍をした。その後も活躍を続け、2024年3月15日に優勝した。",
            "description": "複数の違反を含む"
        },
        {
            "text": "あなたと同じ30歳のとき、松井秀喜は31本塁打を記録し革命児。",
            "description": "名詞終了"
        },
        {
            "text": "あなたと同じ27歳のとき、イチローはMLBで242安打を記録し、84年ぶりにシーズン最多安打記録を更新した。",
            "description": "良質なエピソード"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"テストケース {i}: {test_case['description']}")
        print(f"テキスト: {test_case['text']}")
        print("")

        # リアルタイム検証（文字入力シミュレーション）
        print("リアルタイム検証:")
        text = test_case["text"]
        for pos in range(10, len(text), 10):  # 10文字ごとにチェック
            result = validator.validate_character(text, pos)
            if result:
                validator.trigger_callbacks(result.status, {
                    "message": result.message,
                    "position": pos
                })

        # 文単位の検証
        print("\n文単位の検証:")
        results = validator.validate_sentence(text)
        for result in results[:3]:  # 上位3件
            print(f"  [{result.status.value}] {result.message}")

        # 全体検証
        print("\n全体検証:")
        validation = validator.validate_full_episode(text)
        print(f"  有効: {'✅' if validation['is_valid'] else '❌'}")
        print(f"  ステータス: {validation['status'].value}")
        print(f"  違反数: {len(validation['violations'])}")
        print(f"  統計: Block={validation['statistics']['block_count']}, "
              f"Error={validation['statistics']['error_count']}, "
              f"Warning={validation['statistics']['warning_count']}")

        if validation["suggestions"]:
            print(f"\n  提案:")
            for suggestion in validation["suggestions"][:3]:
                print(f"    • {suggestion}")

    # 統計表示
    print(f"\n{'='*60}")
    print("検証統計:")
    stats = validator.get_statistics()
    print(f"  総検証数: {stats.get('total_validations', 0)}")
    print(f"  有効率: {stats.get('valid_rate', 0):.1f}%")
    if stats.get('status_distribution'):
        print(f"  ステータス分布:")
        for status, count in stats['status_distribution'].items():
            print(f"    {status}: {count}")


if __name__ == "__main__":
    test_realtime_validator()
