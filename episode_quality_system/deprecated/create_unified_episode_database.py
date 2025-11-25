#!/usr/bin/env python3
"""
統合エピソードデータベース作成
全てのエピソードを単一のマスターデータベースに統合
"""

import csv
import json
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import pandas as pd

from storytelling_engine_v2 import StorytellingEngineV2
from optimal_age_algorithm import OptimalAgeSelector

@dataclass
class UnifiedEpisode:
    """統合エピソードデータ"""
    person_name: str
    age: int
    episode: str
    character_count: int
    quality_score: float
    source: str  # データソース（original/generated/enhanced）
    historical_moment: str
    created_at: str
    status: str  # final/draft/review

class UnifiedEpisodeDatabase:
    """統合エピソードデータベース"""

    def __init__(self):
        """初期化"""
        self.storytelling_engine = StorytellingEngineV2()
        self.age_selector = OptimalAgeSelector()
        self.episodes = {}  # person_name -> UnifiedEpisode
        self.statistics = {
            "total": 0,
            "from_original": 0,
            "newly_generated": 0,
            "enhanced": 0,
            "valid_length": 0
        }

    def load_original_29_episodes(self, filepath: str = None):
        """オリジナル29エピソードを読み込み"""
        if not filepath:
            filepath = "../episodes_29_corrected_20250922_210220.csv"

        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            loaded = 0

            for _, row in df.iterrows():
                person_name = row['person_name']

                # 年齢抽出（エピソード文から）
                episode_text = row.get('episode_text', row.get('episode', ''))
                age = row.get('episode_age', self._extract_age_from_episode(episode_text))

                episode = UnifiedEpisode(
                    person_name=person_name,
                    age=age,
                    episode=episode_text,
                    character_count=len(episode_text),
                    quality_score=row.get('weighted_score', row.get('score', 9.0)),
                    source='original',
                    historical_moment=row.get('category', 'オリジナルデータ'),
                    created_at=row.get('created_date', row.get('created_at', '2025-09-22')),
                    status='final'
                )

                self.episodes[person_name] = episode
                loaded += 1

            self.statistics["from_original"] = loaded
            print(f"オリジナル29エピソード読み込み完了: {loaded}件")
            return loaded

        except Exception as e:
            print(f"オリジナルエピソード読み込みエラー: {e}")
            return 0

    def _extract_age_from_episode(self, episode: str) -> int:
        """エピソードテキストから年齢を抽出"""
        import re
        match = re.search(r'(\d+)歳', episode)
        if match:
            return int(match.group(1))
        return 30  # デフォルト

    def load_generated_episodes(self, filepath: str = None):
        """生成済みエピソードを読み込み"""
        if not filepath:
            filepath = "episodes_final_102_20250923_174922.csv"

        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            loaded = 0
            enhanced = 0

            for _, row in df.iterrows():
                person_name = row['person_name']

                # 既存エピソードがある場合はスキップまたは品質比較
                if person_name in self.episodes:
                    # より長いエピソードを採用
                    if row['character_count'] > self.episodes[person_name].character_count:
                        self.episodes[person_name] = UnifiedEpisode(
                            person_name=person_name,
                            age=row['age'],
                            episode=row['episode'],
                            character_count=row['character_count'],
                            quality_score=8.0,
                            source='enhanced',
                            historical_moment=row.get('historical_moment', ''),
                            created_at=row.get('created_at', datetime.now().isoformat()),
                            status='final'
                        )
                        enhanced += 1
                else:
                    # 新規エピソード
                    self.episodes[person_name] = UnifiedEpisode(
                        person_name=person_name,
                        age=row['age'],
                        episode=row['episode'],
                        character_count=row['character_count'],
                        quality_score=7.5,
                        source='generated',
                        historical_moment=row.get('historical_moment', ''),
                        created_at=row.get('created_at', datetime.now().isoformat()),
                        status='final' if row['character_count'] >= 132 else 'review'
                    )
                    loaded += 1

            self.statistics["newly_generated"] = loaded
            self.statistics["enhanced"] = enhanced
            print(f"生成エピソード処理完了: 新規{loaded}件、更新{enhanced}件")
            return loaded + enhanced

        except Exception as e:
            print(f"生成エピソード読み込みエラー: {e}")
            return 0

    def generate_missing_episodes(self):
        """不足エピソードを生成"""
        # 全人物リスト（102人）
        all_persons = self._get_all_persons_list()
        missing = []

        for person_name in all_persons:
            if person_name not in self.episodes:
                missing.append(person_name)

        print(f"\n不足エピソード生成: {len(missing)}人分")

        for i, person_name in enumerate(missing, 1):
            print(f"  [{i}/{len(missing)}] {person_name}生成中...")

            # 最適年齢選択
            age, moment = self.age_selector.select_optimal_age(person_name)

            # エピソード生成
            episode_text = self.storytelling_engine.create_episode(
                person_name=person_name,
                age=age,
                include_emotion=True,
                target_length=150
            )

            # 保存
            self.episodes[person_name] = UnifiedEpisode(
                person_name=person_name,
                age=age,
                episode=episode_text,
                character_count=len(episode_text),
                quality_score=7.0,
                source='generated',
                historical_moment=moment,
                created_at=datetime.now().isoformat(),
                status='draft'
            )

            if i % 10 == 0:
                print(f"    進捗: {i}/{len(missing)}")

        self.statistics["newly_generated"] += len(missing)
        return len(missing)

    def _get_all_persons_list(self) -> List[str]:
        """完全な人物リストを取得"""
        # person_facts.jsonから読み込み
        try:
            with open("data/person_facts.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                return list(data.get("persons", {}).keys())
        except:
            # フォールバック
            return [
                "大谷翔平", "イチロー", "宮崎駿", "村上春樹", "浅田真央",
                "羽生結弦", "藤井聡太", "山中伸弥", "HIKAKIN", "さくらももこ",
                # ... 残り92人
            ]

    def optimize_episodes(self):
        """エピソードを最適化（文字数調整）"""
        optimized = 0

        for person_name, episode in self.episodes.items():
            # 短すぎるエピソードを再生成
            if episode.character_count < 132 and episode.source != 'original':
                print(f"  最適化: {person_name} ({episode.character_count}文字 → 再生成)")

                # 再生成
                new_episode_text = self.storytelling_engine.create_episode(
                    person_name=person_name,
                    age=episode.age,
                    include_emotion=True,
                    target_length=150
                )

                # 更新
                episode.episode = new_episode_text
                episode.character_count = len(new_episode_text)
                episode.source = 'enhanced'
                episode.status = 'final' if len(new_episode_text) >= 132 else 'review'

                optimized += 1

        print(f"最適化完了: {optimized}件")
        return optimized

    def calculate_statistics(self):
        """統計を計算"""
        self.statistics["total"] = len(self.episodes)

        valid_count = 0
        total_chars = 0

        for episode in self.episodes.values():
            if 132 <= episode.character_count <= 250:
                valid_count += 1
            total_chars += episode.character_count

        self.statistics["valid_length"] = valid_count
        self.statistics["avg_length"] = total_chars / len(self.episodes) if self.episodes else 0

        # ソース別集計
        source_counts = {'original': 0, 'generated': 0, 'enhanced': 0}
        for episode in self.episodes.values():
            source_counts[episode.source] = source_counts.get(episode.source, 0) + 1

        self.statistics.update(source_counts)

    def save_unified_database(self, filename: str = None) -> str:
        """統合データベースを保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"unified_episode_database_{timestamp}.csv"

        filepath = Path(__file__).parent / filename

        # UTF-8 BOM付きで保存（Excel対応）
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'person_name', 'age', 'episode', 'character_count',
                'quality_score', 'source', 'historical_moment',
                'created_at', 'status'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # 人物名でソート
            for person_name in sorted(self.episodes.keys()):
                writer.writerow(asdict(self.episodes[person_name]))

        print(f"\n統合データベース保存完了: {filepath}")
        return str(filepath)

    def print_report(self):
        """レポート表示"""
        self.calculate_statistics()

        print("\n" + "="*60)
        print("統合エピソードデータベース レポート")
        print("="*60)
        print(f"総エピソード数: {self.statistics['total']}")
        print(f"  - オリジナル: {self.statistics.get('original', 0)}")
        print(f"  - 新規生成: {self.statistics.get('generated', 0)}")
        print(f"  - 強化版: {self.statistics.get('enhanced', 0)}")
        print(f"\n適正文字数(132-250): {self.statistics['valid_length']} ({self.statistics['valid_length']/self.statistics['total']*100:.1f}%)")
        print(f"平均文字数: {self.statistics['avg_length']:.1f}")

        # 品質別
        final_count = sum(1 for e in self.episodes.values() if e.status == 'final')
        review_count = sum(1 for e in self.episodes.values() if e.status == 'review')
        draft_count = sum(1 for e in self.episodes.values() if e.status == 'draft')

        print(f"\nステータス別:")
        print(f"  - Final: {final_count}")
        print(f"  - Review必要: {review_count}")
        print(f"  - Draft: {draft_count}")

        # トップ5表示
        print("\n高品質エピソード例（上位5件）:")
        sorted_episodes = sorted(self.episodes.values(),
                                key=lambda e: (e.quality_score, e.character_count),
                                reverse=True)

        for i, episode in enumerate(sorted_episodes[:5], 1):
            print(f"\n{i}. {episode.person_name}（{episode.age}歳）")
            print(f"   スコア: {episode.quality_score} | 文字数: {episode.character_count} | ソース: {episode.source}")
            print(f"   {episode.episode[:80]}...")


def main():
    """メイン実行"""
    print("統合エピソードデータベース作成")
    print("="*60)

    database = UnifiedEpisodeDatabase()

    # 1. オリジナル29エピソードを読み込み
    print("\n1. オリジナルエピソード読み込み")
    database.load_original_29_episodes()

    # 2. 生成済みエピソードを読み込み
    print("\n2. 生成済みエピソード読み込み")
    database.load_generated_episodes()

    # 3. 不足分を生成
    print("\n3. 不足エピソード生成")
    database.generate_missing_episodes()

    # 4. 最適化
    print("\n4. エピソード最適化")
    database.optimize_episodes()

    # 5. レポート表示
    database.print_report()

    # 6. 統合データベース保存
    csv_path = database.save_unified_database()

    print("\n" + "="*60)
    print("統合完了！")
    print(f"最終データベース: {csv_path}")


if __name__ == "__main__":
    main()
