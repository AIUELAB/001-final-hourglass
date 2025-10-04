#!/usr/bin/env python3
"""
StorytellingEngine - ストーリーテリングエンジン
事実と感情を融合させ、記憶に残るエピソードを生成
"""

import json
import random
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

@dataclass
class StoryElements:
    """ストーリー要素"""
    setup: str           # 背景・状況設定
    achievement: str     # 成果・記録
    emotion: str        # 感情・人間性
    significance: str   # 意義・影響
    quote: Optional[str] = None  # 本人の言葉

class StorytellingEngine:
    """ストーリーテリングエンジン"""

    def __init__(self, moments_db_path: str = None):
        """初期化"""
        if moments_db_path is None:
            moments_db_path = Path(__file__).parent / "historical_moments_database.json"

        self.moments_db = self._load_moments_database(moments_db_path)

        # ストーリーテンプレート（パターン）
        self.story_patterns = {
            "challenge_overcome": {
                "structure": "{setup}。{achievement}。{emotion}。{significance}。",
                "example": "挑戦→達成→感情→意義"
            },
            "historic_moment": {
                "structure": "{achievement}。{setup}。{significance}。{emotion}。",
                "example": "記録→背景→意義→感動"
            },
            "turning_point": {
                "structure": "{setup}。{achievement}。「{quote}」。{significance}。",
                "example": "状況→決断→言葉→影響"
            },
            "culmination": {
                "structure": "{achievement}。{quote}。{emotion}。{significance}。",
                "example": "集大成→哲学→感慨→遺産"
            },
            "breakthrough": {
                "structure": "{setup}。{achievement}。{emotion}。{significance}。",
                "example": "困難→突破→喜び→革新"
            }
        }

        # 感情表現の語彙
        self.emotion_vocabulary = {
            "achievement": ["喜び", "達成感", "充実感", "誇り"],
            "struggle": ["苦悩", "葛藤", "試練", "挑戦"],
            "breakthrough": ["突破", "開眼", "覚醒", "飛躍"],
            "legacy": ["遺産", "継承", "影響", "足跡"],
            "inspiration": ["感動", "共感", "勇気", "希望"]
        }

        # 接続表現
        self.connectors = {
            "contrast": ["しかし", "だが", "それでも", "にもかかわらず"],
            "result": ["その結果", "こうして", "ついに", "遂に"],
            "emphasis": ["まさに", "正に", "まさしく", "確かに"],
            "time": ["この時", "その瞬間", "この日", "その年"]
        }

    def _load_moments_database(self, path: str) -> Dict:
        """歴史的瞬間データベースを読み込み"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: {path} が見つかりません")
            return {"persons": {}}

    def create_episode(self, person_name: str, age: int,
                      include_emotion: bool = True,
                      target_length: int = 150) -> str:
        """
        エピソードを生成

        Args:
            person_name: 人物名
            age: 年齢
            include_emotion: 感情表現を含むか
            target_length: 目標文字数

        Returns:
            エピソード文字列
        """
        # 基本フレーズ
        opening = f"あなたと同じ{age}歳のとき、{person_name}は"

        # 歴史的瞬間データを取得
        moment_data = self._get_moment_data(person_name, age)

        if not moment_data:
            # データがない場合は基本的なエピソード
            return f"{opening}重要な成果を残した。"

        # ストーリー要素を抽出
        elements = self._extract_story_elements(moment_data)

        # ストーリーパターンを選択
        pattern = self._select_pattern(moment_data.get("type", ""))

        # エピソードを構築
        episode = self._build_episode(opening, elements, pattern,
                                     include_emotion, target_length)

        return episode

    def _get_moment_data(self, person_name: str, age: int) -> Optional[Dict]:
        """指定された人物・年齢の瞬間データを取得"""
        persons_data = self.moments_db.get("persons", {})

        if person_name not in persons_data:
            return None

        person_moments = persons_data[person_name].get("moments", [])

        # 指定年齢に最も近い瞬間を探す
        closest_moment = None
        min_diff = float('inf')

        for moment in person_moments:
            age_diff = abs(moment.get("age", 0) - age)
            if age_diff < min_diff:
                min_diff = age_diff
                closest_moment = moment

        # 年齢差が5歳以内なら採用
        if closest_moment and min_diff <= 5:
            return closest_moment

        # それ以外は最も重要な瞬間を返す
        if person_moments:
            return max(person_moments, key=lambda m: m.get("impact", 0))

        return None

    def _extract_story_elements(self, moment_data: Dict) -> StoryElements:
        """瞬間データからストーリー要素を抽出"""
        details = moment_data.get("details", {})

        # 背景・状況設定
        setup = details.get("background", "")
        if not setup and "stats" in details:
            setup = f"それまでの記録を塗り替える挑戦"

        # 成果・記録
        achievement = details.get("achievement", moment_data.get("event", ""))
        if "stats" in details:
            achievement += f"（{details['stats']}）"

        # 感情・人間性
        emotion = details.get("emotion", "")
        if not emotion:
            emotion = self._generate_emotion(moment_data.get("type", ""))

        # 意義・影響
        significance = details.get("significance", "")
        if not significance:
            significance = "歴史に新たな1ページを刻んだ"

        # 引用
        quote = details.get("quote")

        return StoryElements(
            setup=setup,
            achievement=achievement,
            emotion=emotion,
            significance=significance,
            quote=quote
        )

    def _select_pattern(self, moment_type: str) -> str:
        """瞬間タイプに基づいてストーリーパターンを選択"""
        pattern_mapping = {
            "世界的偉業": "historic_moment",
            "歴史的記録": "historic_moment",
            "不屈の精神": "challenge_overcome",
            "集大成": "culmination",
            "運命の転換": "turning_point",
            "医学革命": "breakthrough",
            "新職業確立": "breakthrough",
            "社会現象": "historic_moment"
        }

        return pattern_mapping.get(moment_type, "challenge_overcome")

    def _generate_emotion(self, moment_type: str) -> str:
        """瞬間タイプに基づいて感情表現を生成"""
        emotion_mapping = {
            "世界的偉業": "この瞬間、新たな歴史が始まった",
            "歴史的記録": "誰も成し遂げられなかった偉業を達成",
            "不屈の精神": "涙は努力が報われた証だった",
            "集大成": "積み重ねた日々が結実した",
            "運命の転換": "人生を賭けた決断だった",
            "医学革命": "人類の希望を切り開いた",
            "社会現象": "時代の空気を変えた"
        }

        return emotion_mapping.get(moment_type, "歴史的な瞬間だった")

    def _build_episode(self, opening: str, elements: StoryElements,
                      pattern: str, include_emotion: bool,
                      target_length: int) -> str:
        """エピソードを構築"""
        # 基本構成を作成
        episode_parts = [opening]

        # パターンに基づいて構成
        if pattern == "historic_moment":
            episode_parts.append(elements.achievement)
            if elements.setup:
                episode_parts.append(elements.setup)
            episode_parts.append(elements.significance)
            if include_emotion and elements.emotion:
                episode_parts.append(elements.emotion)

        elif pattern == "challenge_overcome":
            if elements.setup:
                episode_parts.append(elements.setup)
            episode_parts.append(elements.achievement)
            if include_emotion and elements.emotion:
                episode_parts.append(elements.emotion)
            episode_parts.append(elements.significance)

        elif pattern == "turning_point":
            if elements.setup:
                episode_parts.append(elements.setup)
            episode_parts.append(elements.achievement)
            if elements.quote:
                episode_parts.append(f"「{elements.quote}」")
            episode_parts.append(elements.significance)

        elif pattern == "culmination":
            episode_parts.append(elements.achievement)
            if elements.quote:
                episode_parts.append(f"「{elements.quote}」と語った")
            if include_emotion and elements.emotion:
                episode_parts.append(elements.emotion)
            episode_parts.append(elements.significance)

        else:  # breakthrough
            if elements.setup:
                episode_parts.append(elements.setup)
            episode_parts.append(elements.achievement)
            if include_emotion and elements.emotion:
                episode_parts.append(elements.emotion)
            episode_parts.append(elements.significance)

        # 文章を結合
        episode = "。".join(episode_parts) + "。"
        episode = episode.replace("。。", "。")

        # 文字数調整
        episode = self._adjust_length(episode, target_length)

        return episode

    def _adjust_length(self, text: str, target_length: int) -> str:
        """文字数を調整"""
        current_length = len(text)

        # 短すぎる場合は詳細を追加
        if current_length < target_length - 20:
            # ここで追加の詳細や背景情報を加える
            pass

        # 長すぎる場合は簡潔に
        elif current_length > target_length + 20:
            sentences = text.split("。")
            # 重要度の低い文を削除
            if len(sentences) > 4:
                sentences = sentences[:4]
            text = "。".join(sentences) + "。"

        return text


def test_storytelling_engine():
    """テスト実行"""
    engine = StorytellingEngine()

    test_cases = [
        ("大谷翔平", 29),
        ("イチロー", 45),
        ("宮崎駿", 60),
        ("浅田真央", 24),
        ("村上春樹", 38),
        ("羽生結弦", 23),
        ("ヘレン・ケラー", 7),
        ("藤井聡太", 19)
    ]

    print("ストーリーテリングエンジンテスト")
    print("="*60)

    for person_name, age in test_cases:
        print(f"\n【{person_name} ({age}歳)】")

        # 感情あり版
        episode_with_emotion = engine.create_episode(
            person_name, age, include_emotion=True, target_length=150
        )
        print("感情あり:")
        print(f"  {episode_with_emotion}")
        print(f"  文字数: {len(episode_with_emotion)}")

        # 感情なし版
        episode_without_emotion = engine.create_episode(
            person_name, age, include_emotion=False, target_length=150
        )
        print("感情なし:")
        print(f"  {episode_without_emotion}")
        print(f"  文字数: {len(episode_without_emotion)}")


if __name__ == "__main__":
    test_storytelling_engine()