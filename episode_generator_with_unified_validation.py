#!/usr/bin/env python3
"""
統合検証システム対応エピソード生成器
Episode Generator with Unified Validation System

既存のエピソード生成パイプラインに統合検証システムを組み込む
"""

import json
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

# 統合検証システムのインポート
from unified_validation_system_with_persistence import create_validator

# 既存のエピソード生成システム（例）
# from weekly_episode_generator import WeeklyEpisodeGenerator


class ValidatedEpisodeGenerator:
    """
    統合検証システムを組み込んだエピソード生成器

    既存のエピソード生成ロジックに品質検証を追加
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初期化

        Args:
            config_path: 統合検証システムの設定ファイルパス
        """
        self.validator = create_validator(config_path)
        self.config = self.validator.config
        self.validation_enabled = self.config.get("integration", {}).get(
            "episode_generator", {}
        ).get("enabled", True)
        self.auto_correct = self.config.get("integration", {}).get(
            "episode_generator", {}
        ).get("auto_correct_violations", True)
        self.reject_on_failure = self.config.get("integration", {}).get(
            "episode_generator", {}
        ).get("reject_on_failure", True)

    def generate_episode(self, person_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        エピソードを生成し、検証を実行

        Args:
            person_data: 人物データ

        Returns:
            検証済みエピソード、または検証失敗時はNone
        """
        # エピソード生成（既存ロジックをここに実装）
        episode = self._generate_episode_internal(person_data)

        if not self.validation_enabled:
            return episode

        # 統合検証システムで検証
        validation_result = self.validator.validate_episode(episode)

        # 検証結果をエピソードに追加
        episode['validation_result'] = {
            'is_valid': validation_result.is_valid,
            'emotional_score': validation_result.emotional_impact_score,
            'specificity_score': validation_result.specificity_score,
            'violations': len(validation_result.violations),
            'critical_violations': len(validation_result.get_critical_violations())
        }

        # 検証失敗時の処理
        if not validation_result.is_valid:
            print(f"⚠️ エピソード検証失敗: {person_data.get('person_name', 'Unknown')}")

            for violation in validation_result.violations:
                print(f"  - [{violation.severity.value}] {violation.message}")
                if violation.suggestion:
                    print(f"    提案: {violation.suggestion}")

            # 自動修正を試行
            if self.auto_correct:
                corrected_episode = self._attempt_auto_correction(
                    episode, validation_result
                )
                if corrected_episode:
                    # 再検証
                    revalidation = self.validator.validate_episode(corrected_episode)
                    if revalidation.is_valid:
                        print(f"✅ 自動修正成功")
                        return corrected_episode

            # 修正失敗、かつreject_on_failureが有効な場合はNoneを返す
            if self.reject_on_failure:
                print(f"❌ エピソード生成を中止")
                return None

        return episode

    def _generate_episode_internal(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        内部エピソード生成ロジック（プレースホルダ）

        実際のエピソード生成ロジックをここに実装
        """
        # この部分は既存のエピソード生成システムのロジックを統合
        # 例: LLMを使った生成、テンプレートベース生成など

        return {
            "person_id": person_data.get("person_id", "P000000"),
            "person_name": person_data.get("person_name", "Unknown"),
            "episode_text": person_data.get("episode_text", ""),
            "user_age": person_data.get("user_age", 30),
            "episode_age": person_data.get("episode_age", 30),
            "category": person_data.get("category", "その他")
        }

    def _attempt_auto_correction(
        self,
        episode: Dict[str, Any],
        validation_result
    ) -> Optional[Dict[str, Any]]:
        """
        自動修正を試行

        Args:
            episode: 元のエピソード
            validation_result: 検証結果

        Returns:
            修正後のエピソード、または修正不可能な場合はNone
        """
        corrected_text = episode['episode_text']

        # 各違反に対する自動修正を試行
        for violation in validation_result.violations:
            if violation.rule_name == "specificity":
                # 年号・日付の削除
                import re
                for pattern in [r'\d{4}年', r'令和\d+年', r'平成\d+年', r'\d+月\d+日']:
                    corrected_text = re.sub(pattern, '', corrected_text)

            elif violation.rule_name == "objective_emotional":
                # 主観表現の削除
                subjective_words = [
                    "素晴らしい", "すごい", "驚異的", "圧倒的",
                    "感動的", "劇的", "衝撃的", "奇跡的",
                    "伝説的", "壮大な"
                ]
                for word in subjective_words:
                    corrected_text = corrected_text.replace(word, '')

            # その他の自動修正可能なルールに対する処理...

        # 修正後のテキストが元と同じ場合は修正不可
        if corrected_text == episode['episode_text']:
            return None

        # 修正版エピソードを作成
        corrected_episode = episode.copy()
        corrected_episode['episode_text'] = corrected_text
        corrected_episode['corrections_applied'] = ['auto_correction']

        return corrected_episode

    def batch_generate_episodes(
        self,
        person_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        バッチでエピソードを生成

        Args:
            person_list: 人物データのリスト

        Returns:
            検証済みエピソードのリスト
        """
        validated_episodes = []
        failed_count = 0

        for person_data in person_list:
            episode = self.generate_episode(person_data)
            if episode:
                validated_episodes.append(episode)
            else:
                failed_count += 1

        # 統計情報
        stats = self.validator.get_statistics()
        print(f"\n=== バッチ生成結果 ===")
        print(f"処理件数: {len(person_list)}")
        print(f"成功: {len(validated_episodes)}")
        print(f"失敗: {failed_count}")
        print(f"準拠率: {stats['compliance_rate']:.1f}%")
        print(f"平均感銘スコア: {stats['avg_emotional_score']:.2f}")
        print(f"平均具体性スコア: {stats['avg_specificity_score']:.2f}")

        # 検証履歴を保存
        self.validator.save_validation_history()

        return validated_episodes


def integrate_with_existing_generator():
    """
    既存のエピソード生成システムとの統合例

    この関数は既存の weekly_episode_generator.py などと統合する際の
    インテグレーションポイントとして機能する
    """
    # 統合検証システム対応ジェネレータを作成
    generator = ValidatedEpisodeGenerator("unified_validation_config.json")

    # 既存のエピソード生成パイプラインに組み込む
    # 例:
    # original_generator = WeeklyEpisodeGenerator()
    # generator.generate_episode = original_generator.generate_episode

    return generator


if __name__ == "__main__":
    # テスト実行
    generator = ValidatedEpisodeGenerator()

    test_person = {
        "person_id": "P999999",
        "person_name": "山田太郎",
        "episode_text": "30歳でノーベル物理学賞を受賞。素粒子理論の研究で史上最年少記録を達成し、世界中の研究者に影響を与えた。京都大学での15年にわたる基礎研究の成果が実を結び、量子力学の新理論を確立した。",
        "user_age": 30,
        "episode_age": 30,
        "category": "科学"
    }

    episode = generator.generate_episode(test_person)

    if episode:
        print("\n✅ エピソード生成成功")
        print(f"人名: {episode['person_name']}")
        print(f"検証状態: {episode['validation_result']}")
    else:
        print("\n❌ エピソード生成失敗")
