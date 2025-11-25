#!/usr/bin/env python3
"""
最終エピソードデータベース生成
歴史的瞬間アプローチで102人分の高品質エピソードを生成
"""

import json
import csv
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

from storytelling_engine_v2 import StorytellingEngineV2
from optimal_age_algorithm import OptimalAgeSelector

@dataclass
class Episode:
    """エピソードデータ"""
    person_name: str
    age: int
    episode: str
    character_count: int
    historical_moment: str
    created_at: str

class FinalEpisodeGenerator:
    """最終エピソードジェネレーター"""

    def __init__(self):
        """初期化"""
        self.storytelling_engine = StorytellingEngineV2()
        self.age_selector = OptimalAgeSelector()

        # 人物データベース読み込み
        self.persons_db = self._load_persons_database()

        # 統計
        self.stats = {
            "total": 0,
            "valid_length": 0,
            "avg_length": 0.0,
            "min_length": 999,
            "max_length": 0
        }

    def _load_persons_database(self) -> List[str]:
        """人物リストを読み込み"""
        fact_db_path = Path(__file__).parent / "data" / "person_facts.json"

        try:
            with open(fact_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                persons = list(data.get("persons", {}).keys())
                print(f"人物データベース読み込み完了: {len(persons)}人")
                return persons
        except FileNotFoundError:
            # フォールバック: 最低限の重要人物リスト
            print("person_facts.json未検出 - デフォルトリスト使用")
            return [
                "大谷翔平", "イチロー", "宮崎駿", "村上春樹", "浅田真央",
                "羽生結弦", "藤井聡太", "山中伸弥", "HIKAKIN", "さくらももこ",
                "ヘレン・ケラー", "羽生善治", "北野武", "黒澤明", "坂本龍一",
                "松田聖子", "錦織圭", "吉田沙保里", "孫正義", "本庶佑",
                "三木谷浩史", "柳井正", "櫻井翔", "YOSHIKI", "あいみょん",
                "小泉純一郎", "安倍晋三", "スティーブ・ジョブズ", "Ado",
                "田中将大", "内村航平", "北島康介", "高橋尚子", "野村萬斎",
                "久石譲", "新海誠", "是枝裕和", "細田守", "庵野秀明",
                "押井守", "富野由悠季", "手塚治虫", "藤子・F・不二雄", "鳥山明",
                "尾田栄一郎", "諫山創", "吾峠呼世晴", "岸本斉史", "空知英秋",
                "秋元康", "つんく♂", "小室哲哉", "中田ヤスタカ", "米津玄師"
            ]

    def generate_episode(self, person_name: str) -> Episode:
        """単一エピソードを生成"""
        try:
            # 最適年齢を選択
            age, moment = self.age_selector.select_optimal_age(person_name)

            # エピソード生成
            episode_text = self.storytelling_engine.create_episode(
                person_name=person_name,
                age=age,
                include_emotion=True,
                target_length=150
            )

            # 文字数
            char_count = len(episode_text)

            # 統計更新
            self.stats["total"] += 1
            if 132 <= char_count <= 250:
                self.stats["valid_length"] += 1
            if char_count < self.stats["min_length"]:
                self.stats["min_length"] = char_count
            if char_count > self.stats["max_length"]:
                self.stats["max_length"] = char_count

            # エピソード作成
            episode = Episode(
                person_name=person_name,
                age=age,
                episode=episode_text,
                character_count=char_count,
                historical_moment=moment,
                created_at=datetime.now().isoformat()
            )

            # 進捗表示
            valid_mark = "✓" if 132 <= char_count <= 250 else "✗"
            print(f"  {valid_mark} {person_name}({age}歳): {char_count}文字 - {moment}")

            return episode

        except Exception as e:
            print(f"  ✗ {person_name}: エラー - {str(e)}")
            # エラー時はデフォルトエピソード
            return Episode(
                person_name=person_name,
                age=30,
                episode=f"あなたと同じ30歳のとき、{person_name}は重要な成果を残していた。",
                character_count=30,
                historical_moment="データなし",
                created_at=datetime.now().isoformat()
            )

    def generate_all(self) -> List[Episode]:
        """全エピソード生成"""
        print("\n全エピソード生成開始")
        print("="*60)

        episodes = []

        for i, person_name in enumerate(self.persons_db, 1):
            print(f"\n[{i}/{len(self.persons_db)}] 生成中...")
            episode = self.generate_episode(person_name)
            episodes.append(episode)

            # 10人ごとに進捗表示
            if i % 10 == 0:
                valid_rate = self.stats["valid_length"] / self.stats["total"] * 100
                print(f"\n--- 進捗: {i}/{len(self.persons_db)} ({valid_rate:.1f}%が適正文字数) ---")

        # 統計計算
        if episodes:
            total_chars = sum(e.character_count for e in episodes)
            self.stats["avg_length"] = total_chars / len(episodes)

        return episodes

    def save_to_csv(self, episodes: List[Episode], filename: str = None) -> str:
        """CSVに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"episodes_final_{len(episodes)}_{timestamp}.csv"

        filepath = Path(__file__).parent / filename

        # UTF-8 BOM付きで保存（Excel対応）
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_name', 'age', 'episode', 'character_count',
                         'historical_moment', 'created_at']

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for episode in episodes:
                writer.writerow(asdict(episode))

        return str(filepath)

    def print_statistics(self):
        """統計情報を表示"""
        print("\n" + "="*60)
        print("生成統計:")
        print(f"  総生成数: {self.stats['total']}")
        print(f"  適正文字数(132-250): {self.stats['valid_length']} ({self.stats['valid_length']/self.stats['total']*100:.1f}%)")
        print(f"  平均文字数: {self.stats['avg_length']:.1f}")
        print(f"  最短: {self.stats['min_length']}文字")
        print(f"  最長: {self.stats['max_length']}文字")


def main():
    """メイン実行"""
    print("最終エピソードデータベース生成システム")
    print("="*60)
    print("歴史的瞬間アプローチによる高品質エピソード生成")
    print("="*60)

    generator = FinalEpisodeGenerator()

    # 全エピソード生成
    episodes = generator.generate_all()

    # 統計表示
    generator.print_statistics()

    # CSV保存
    csv_path = generator.save_to_csv(episodes)
    print(f"\nCSV保存完了: {csv_path}")

    # ベスト5を表示
    print("\n" + "="*60)
    print("適正文字数エピソード例（最初の5件）:")

    valid_episodes = [e for e in episodes if 132 <= e.character_count <= 250]
    for i, episode in enumerate(valid_episodes[:5], 1):
        print(f"\n{i}. {episode.person_name}（{episode.age}歳）- {episode.character_count}文字")
        print(f"   {episode.episode}")

    print("\n" + "="*60)
    print("完了！")


if __name__ == "__main__":
    main()
