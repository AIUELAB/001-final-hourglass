#!/usr/bin/env python3
"""
統合検証システム - 永続化対応版 (Unified Validation System with Persistence)
PDCAガーディアンとOptimizedValidationSystemの矛盾を解消した統一品質基準

Author: Claude Code
Date: 2025-10-01
Version: 1.1.0 (永続化対応)
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

# 既存の unified_validation_system.py から全てインポート
from unified_validation_system import (
    UnifiedValidationSystem as BaseUnifiedValidationSystem,
    ValidationResult,
    ValidationRule,
    CharacterCountRule,
    HistoricalMomentRule,
    ObjectiveEmotionalRule,
    AchievementRule,
    DuplicateAgeRule,
    SpecificityRule,
    SeverityLevel
)


class UnifiedValidationSystem(BaseUnifiedValidationSystem):
    """
    統合検証システム - 永続化対応版

    設定ファイルからルールを読み込み、検証履歴を記録する
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス（デフォルト: unified_validation_config.json）
        """
        self.config = self._load_config(config_path)
        self.rules = self._initialize_rules()
        self.validation_history = []
        self.history_path = self.config.get("persistence", {}).get(
            "validation_history_path", "validation_history.json"
        )
        self.load_validation_history()

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """設定ファイルを読み込む"""
        if config_path is None:
            config_path = "unified_validation_config.json"

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定
            return {
                "validation_rules": {
                    "character_count": {"enabled": True, "min_chars": 130, "max_chars": 250},
                    "historical_moment": {"enabled": True},
                    "objective_emotional": {"enabled": True},
                    "achievement": {"enabled": True},
                    "duplicate_age": {"enabled": True},
                    "specificity": {"enabled": True}
                },
                "monitoring": {"log_all_validations": True}
            }

    def _initialize_rules(self):
        """設定に基づいてルールを初期化"""
        rules = []
        rule_config = self.config.get("validation_rules", {})

        # 最高優先度: 年齢重複
        if rule_config.get("duplicate_age", {}).get("enabled", True):
            rules.append(DuplicateAgeRule())

        # 文字数制限
        if rule_config.get("character_count", {}).get("enabled", True):
            char_cfg = rule_config.get("character_count", {})
            rules.append(CharacterCountRule(
                char_cfg.get("min_chars", 130),
                char_cfg.get("max_chars", 250)
            ))

        # 具体性
        if rule_config.get("specificity", {}).get("enabled", True):
            rules.append(SpecificityRule())

        # 歴史的瞬間
        if rule_config.get("historical_moment", {}).get("enabled", True):
            rules.append(HistoricalMomentRule())

        # 客観的感動表現
        if rule_config.get("objective_emotional", {}).get("enabled", True):
            rules.append(ObjectiveEmotionalRule())

        # 実績判定
        if rule_config.get("achievement", {}).get("enabled", True):
            rules.append(AchievementRule())

        return rules

    def save_validation_history(self):
        """検証履歴を保存"""
        try:
            # 最大エントリ数の制限
            max_entries = self.config.get("persistence", {}).get("max_history_entries", 1000)
            if len(self.validation_history) > max_entries:
                self.validation_history = self.validation_history[-max_entries:]

            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(self.validation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 検証履歴の保存に失敗: {e}")

    def load_validation_history(self):
        """検証履歴を読み込む"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    self.validation_history = json.load(f)
            except Exception as e:
                print(f"⚠️ 検証履歴の読み込みに失敗: {e}")
                self.validation_history = []

    def validate_episode(self, episode: Dict[str, Any]) -> ValidationResult:
        """
        エピソードの検証を実行（履歴記録付き）

        Args:
            episode: 検証対象のエピソード

        Returns:
            ValidationResult: 検証結果
        """
        # 基底クラスのメソッドを呼び出して検証実行
        result = super().validate_episode(episode)

        # 検証履歴に追加
        if self.config.get("monitoring", {}).get("log_all_validations", True):
            self.validation_history.append({
                "timestamp": datetime.now().isoformat(),
                "episode_id": episode.get("person_id", "Unknown"),
                "episode_name": episode.get("person_name", "Unknown"),
                "is_valid": result.is_valid,
                "violation_count": len(result.violations),
                "critical_violations": len(result.get_critical_violations()),
                "emotional_score": result.emotional_impact_score,
                "specificity_score": result.specificity_score
            })

            # 定期的に保存
            if len(self.validation_history) % 10 == 0:
                self.save_validation_history()

        return result

    def get_statistics(self) -> Dict:
        """検証統計を取得"""
        if not self.validation_history:
            return {
                "total_validations": 0,
                "valid_episodes": 0,
                "compliance_rate": 0.0
            }

        total = len(self.validation_history)
        valid = sum(1 for h in self.validation_history if h.get("is_valid", False))

        return {
            "total_validations": total,
            "valid_episodes": valid,
            "invalid_episodes": total - valid,
            "compliance_rate": (valid / total * 100) if total > 0 else 0.0,
            "avg_emotional_score": sum(h.get("emotional_score", 0) for h in self.validation_history) / total,
            "avg_specificity_score": sum(h.get("specificity_score", 0) for h in self.validation_history) / total,
            "critical_violations_total": sum(h.get("critical_violations", 0) for h in self.validation_history)
        }


def create_validator(config_path: Optional[str] = None) -> UnifiedValidationSystem:
    """
    検証システムのファクトリ関数

    Args:
        config_path: 設定ファイルのパス

    Returns:
        UnifiedValidationSystem: 初期化済みの検証システム
    """
    return UnifiedValidationSystem(config_path)


if __name__ == "__main__":
    # テスト実行
    validator = create_validator()

    test_episode = {
        "person_id": "P000001",
        "person_name": "テスト太郎",
        "episode_text": "30歳でノーベル物理学賞を受賞。素粒子理論の研究で史上最年少記録を達成し、世界中の研究者に影響を与えた。京都大学での15年にわたる基礎研究の成果が実を結び、量子力学の新理論を確立した。" * 2,
        "user_age": 30,
        "episode_age": 30
    }

    result = validator.validate_episode(test_episode)

    print("\n=== 検証結果 ===")
    print(f"有効: {result.is_valid}")
    print(f"違反数: {len(result.violations)}")
    print(f"感銘スコア: {result.emotional_impact_score:.2f}")
    print(f"具体性スコア: {result.specificity_score:.2f}")

    if result.violations:
        print("\n違反内容:")
        for v in result.violations:
            print(f"  - [{v.severity.value}] {v.message}")

    # 統計情報
    stats = validator.get_statistics()
    print("\n=== 統計情報 ===")
    print(f"総検証数: {stats['total_validations']}")
    print(f"合格率: {stats['compliance_rate']:.1f}%")

    # 履歴保存
    validator.save_validation_history()
    print("\n✅ 検証履歴を保存しました")
