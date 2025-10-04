#!/usr/bin/env python3
"""
Episode Quality System V3 - 統合エピソード品質システム
歴史的瞬間を中心とした高品質エピソード生成
"""

import json
import csv
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

# 既存コンポーネントのインポート
from quality_guardian_v2 import QualityGuardianV2
from template_blocker import TemplateBlocker
from auto_fact_injector import AutoFactInjector
from realtime_validator import RealTimeValidator
from storytelling_engine_v2 import StorytellingEngineV2
from optimal_age_algorithm import OptimalAgeSelector

@dataclass
class EpisodeData:
    """エピソードデータクラス"""
    person_name: str
    age: int
    episode: str
    character_count: int
    quality_score: float
    factual_accuracy: float
    memorability: float
    emotional_resonance: float
    template_free: bool
    historical_moment: str
    created_at: str

class EpisodeQualitySystemV3:
    """統合エピソード品質システムV3"""

    def __init__(self):
        """初期化"""
        print("Episode Quality System V3 初期化中...")

        # コンポーネントの初期化
        self.quality_guardian = QualityGuardianV2()
        self.template_blocker = TemplateBlocker()
        self.fact_injector = AutoFactInjector()
        self.validator = RealTimeValidator()
        self.storytelling_engine = StorytellingEngineV2()
        self.age_selector = OptimalAgeSelector()

        # 人物データベースの読み込み
        self.persons_db = self._load_persons_database()

        # 統計情報
        self.stats = {
            "total_generated": 0,
            "passed_validation": 0,
            "failed_validation": 0,
            "average_score": 0.0,
            "average_length": 0.0
        }

    def _load_persons_database(self) -> Dict:
        """人物データベースを読み込み"""
        fact_db_path = Path(__file__).parent / "data" / "person_facts.json"
        try:
            with open(fact_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                persons = data.get("persons", {})
                print(f"人物データベース読み込み完了: {len(persons)}人")
                return persons
        except FileNotFoundError:
            print("警告: person_facts.jsonが見つかりません")
            return {}

    def generate_episode(self, person_name: str,
                        use_optimal_age: bool = True) -> Optional[EpisodeData]:
        """
        単一エピソードを生成

        Args:
            person_name: 人物名
            use_optimal_age: 最適年齢を自動選択するか

        Returns:
            生成されたエピソードデータ
        """
        try:
            # 年齢の決定
            if use_optimal_age:
                age, moment_description = self.age_selector.select_optimal_age(person_name)
            else:
                # デフォルト年齢を使用
                age = 30
                moment_description = "標準的な成功年齢"

            print(f"  生成中: {person_name} ({age}歳) - {moment_description}")

            # エピソード生成（ストーリーテリングエンジン使用）
            raw_episode = self.storytelling_engine.create_episode(
                person_name=person_name,
                age=age,
                include_emotion=True,
                target_length=150
            )

            # テンプレートチェック
            has_template, violations = self.template_blocker.check_episode(raw_episode)
            if has_template:
                print(f"    警告: テンプレート検出 - 再生成")
                # ファクトインジェクターで修正
                raw_episode = self.fact_injector.inject_facts(
                    raw_episode, person_name
                )

            # 品質評価
            quality_result = self.quality_guardian.evaluate(raw_episode)

            # リアルタイム検証
            validation = self.validator.validate(raw_episode, person_name, age)

            # 文字数チェック
            char_count = len(raw_episode)
            if not (132 <= char_count <= 250):
                print(f"    警告: 文字数範囲外 ({char_count}文字)")

            # エピソードデータ作成
            episode_data = EpisodeData(
                person_name=person_name,
                age=age,
                episode=raw_episode,
                character_count=char_count,
                quality_score=quality_result['total_score'],
                factual_accuracy=quality_result['scores']['factual_accuracy'],
                memorability=quality_result['scores']['memorability'],
                emotional_resonance=quality_result['scores']['emotional_resonance'],
                template_free=not has_template,
                historical_moment=moment_description,
                created_at=datetime.now().isoformat()
            )

            # 統計更新
            self.stats["total_generated"] += 1
            if validation['is_valid']:
                self.stats["passed_validation"] += 1
                print(f"    ✓ 生成成功 (スコア: {quality_result['total_score']:.1f})")
            else:
                self.stats["failed_validation"] += 1
                print(f"    ✗ 検証失敗: {validation['errors']}")

            return episode_data

        except Exception as e:
            print(f"    エラー: {person_name}のエピソード生成失敗 - {str(e)}")
            return None

    def generate_all_episodes(self) -> List[EpisodeData]:
        """
        全人物のエピソードを生成

        Returns:
            生成されたエピソードリスト
        """
        print("\n全エピソード生成開始")
        print("="*60)

        episodes = []

        for person_name in self.persons_db:
            episode_data = self.generate_episode(person_name)
            if episode_data:
                episodes.append(episode_data)

        # 統計計算
        if episodes:
            self.stats["average_score"] = sum(e.quality_score for e in episodes) / len(episodes)
            self.stats["average_length"] = sum(e.character_count for e in episodes) / len(episodes)

        print("\n生成完了統計:")
        print(f"  総生成数: {self.stats['total_generated']}")
        print(f"  検証合格: {self.stats['passed_validation']}")
        print(f"  検証失敗: {self.stats['failed_validation']}")
        print(f"  平均スコア: {self.stats['average_score']:.1f}")
        print(f"  平均文字数: {self.stats['average_length']:.1f}")

        return episodes

    def save_to_csv(self, episodes: List[EpisodeData], filename: str = None) -> str:
        """
        エピソードをCSVファイルに保存

        Args:
            episodes: エピソードリスト
            filename: ファイル名（省略時は自動生成）

        Returns:
            保存したファイルパス
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"episodes_v3_quality_{timestamp}.csv"

        filepath = Path(__file__).parent / filename

        # UTF-8 BOM付きで保存（Excel対応）
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'person_name', 'age', 'episode', 'character_count',
                'quality_score', 'factual_accuracy', 'memorability',
                'emotional_resonance', 'template_free', 'historical_moment',
                'created_at'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for episode in episodes:
                writer.writerow(asdict(episode))

        print(f"\nCSV保存完了: {filepath}")
        return str(filepath)

    def generate_sample_episodes(self, count: int = 10) -> List[EpisodeData]:
        """
        サンプルエピソードを生成（テスト用）

        Args:
            count: 生成数

        Returns:
            生成されたエピソードリスト
        """
        print(f"\nサンプル{count}件生成開始")
        print("="*60)

        # 重要人物を優先的に選択
        priority_persons = [
            "大谷翔平", "イチロー", "宮崎駿", "村上春樹", "浅田真央",
            "羽生結弦", "藤井聡太", "山中伸弥", "HIKAKIN", "さくらももこ",
            "ヘレン・ケラー", "羽生善治", "北野武", "黒澤明", "坂本龍一"
        ]

        episodes = []
        for person_name in priority_persons[:count]:
            if person_name in self.persons_db:
                episode_data = self.generate_episode(person_name)
                if episode_data:
                    episodes.append(episode_data)

        return episodes


def main():
    """メイン実行"""
    print("Episode Quality System V3 - 統合システムテスト")
    print("="*60)

    # システム初期化
    system = EpisodeQualitySystemV3()

    # サンプル生成
    print("\n1. サンプルエピソード生成（15件）")
    sample_episodes = system.generate_sample_episodes(15)

    # 品質レポート
    print("\n2. 品質レポート")
    print("-"*40)

    high_quality = [e for e in sample_episodes if e.quality_score >= 8.0]
    valid_length = [e for e in sample_episodes if 132 <= e.character_count <= 250]
    template_free = [e for e in sample_episodes if e.template_free]

    print(f"高品質エピソード（8.0以上）: {len(high_quality)}/{len(sample_episodes)}")
    print(f"適正文字数（132-250）: {len(valid_length)}/{len(sample_episodes)}")
    print(f"テンプレートフリー: {len(template_free)}/{len(sample_episodes)}")

    # ベストエピソードを表示
    if sample_episodes:
        print("\n3. ベストエピソード（スコア上位3件）")
        print("-"*40)

        sorted_episodes = sorted(sample_episodes, key=lambda e: e.quality_score, reverse=True)
        for i, episode in enumerate(sorted_episodes[:3], 1):
            print(f"\n#{i} {episode.person_name}（{episode.age}歳）")
            print(f"   スコア: {episode.quality_score:.1f}")
            print(f"   瞬間: {episode.historical_moment}")
            print(f"   エピソード: {episode.episode}")
            print(f"   文字数: {episode.character_count}")

    # CSV保存
    if sample_episodes:
        csv_path = system.save_to_csv(sample_episodes)
        print(f"\n4. CSV出力完了: {csv_path}")

    print("\n" + "="*60)
    print("テスト完了")


if __name__ == "__main__":
    main()