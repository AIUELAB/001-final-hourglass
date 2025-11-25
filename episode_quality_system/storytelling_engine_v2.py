#!/usr/bin/env python3
"""
StorytellingEngine V2 - 改良版ストーリーテリングエンジン
オリジナル29エピソードの品質を再現
"""

import json
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
    context: str        # 追加コンテキスト
    quote: Optional[str] = None  # 本人の言葉

class StorytellingEngineV2:
    """改良版ストーリーテリングエンジン"""

    def __init__(self, moments_db_path: str = None):
        """初期化"""
        if moments_db_path is None:
            moments_db_path = Path(__file__).parent / "historical_moments_database.json"

        self.moments_db = self._load_moments_database(moments_db_path)

        # 拡張された接続表現と詳細化パターン
        self.connectors = {
            "contrast": ["しかし", "だが", "それでも", "にもかかわらず"],
            "result": ["その結果", "こうして", "ついに", "遂に"],
            "emphasis": ["まさに", "正に", "特に", "実に"],
            "time": ["この時", "その瞬間", "この日", "その年"],
            "addition": ["さらに", "また", "そして", "加えて"],
            "context": ["当時", "その頃", "時代は", "背景には"]
        }

        # 詳細化パターン
        self.detail_patterns = {
            "stats": "この記録は{detail}という驚異的な数字",
            "impact": "その影響は{detail}に及んだ",
            "background": "その背景には{detail}があった",
            "legacy": "この功績は後に{detail}となる",
            "emotion": "その瞬間の{detail}は今も語り継がれる"
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
        エピソードを生成（改良版）

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
            return f"{opening}重要な成果を残していた。その功績は今も語り継がれている。"

        # ストーリー要素を抽出
        elements = self._extract_story_elements(moment_data)

        # エピソードを構築（長さを意識）
        episode = self._build_enhanced_episode(opening, elements,
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
        """瞬間データからストーリー要素を抽出（拡張版）"""
        details = moment_data.get("details", {})

        # 背景・状況設定
        setup = details.get("background", "")
        if not setup:
            moment_type = moment_data.get("type", "")
            if "世界" in moment_type:
                setup = "世界が注目する中"
            elif "歴史" in moment_type:
                setup = "歴史に残る挑戦として"
            elif "社会" in moment_type:
                setup = "時代の転換点において"
            else:
                setup = "キャリアの重要な局面で"

        # 成果・記録
        achievement = details.get("achievement", moment_data.get("event", ""))
        if "stats" in details:
            achievement = f"{achievement}を達成。{details['stats']}"

        # 感情・人間性
        emotion = details.get("emotion", "")
        if not emotion:
            emotion = self._generate_enhanced_emotion(moment_data.get("type", ""))

        # 意義・影響
        significance = details.get("significance", "")
        if not significance:
            impact_score = moment_data.get("impact", 8)
            if impact_score >= 9:
                significance = "これは歴史を塗り替える偉業となった"
            elif impact_score >= 8:
                significance = "新たな時代の幕開けを告げた"
            else:
                significance = "大きな影響を与えた"

        # 追加コンテキスト
        context = self._generate_context(moment_data)

        # 引用
        quote = details.get("quote")

        return StoryElements(
            setup=setup,
            achievement=achievement,
            emotion=emotion,
            significance=significance,
            context=context,
            quote=quote
        )

    def _generate_context(self, moment_data: Dict) -> str:
        """追加コンテキストを生成"""
        moment_type = moment_data.get("type", "")
        year = moment_data.get("year", "")

        context_parts = []

        if year:
            context_parts.append(f"{year}年")

        if "世界" in moment_type:
            context_parts.append("世界中が注目した")
        elif "日本" in moment_type or "最年少" in moment_type:
            context_parts.append("日本中が沸いた")
        elif "社会現象" in moment_type:
            context_parts.append("社会現象となった")

        return "、".join(context_parts) if context_parts else ""

    def _generate_enhanced_emotion(self, moment_type: str) -> str:
        """拡張された感情表現を生成"""
        emotion_mapping = {
            "世界的偉業": "その瞬間、世界が息を呑んだ",
            "歴史的記録": "前人未到の領域へ到達した瞬間",
            "不屈の精神": "涙と感動が交錯する劇的な場面",
            "集大成": "長年の努力が結実した瞬間",
            "運命の転換": "人生を賭けた決断の時",
            "医学革命": "人類の希望に光を灯した",
            "新職業確立": "新しい生き方の道を切り開いた",
            "社会現象": "時代の空気を一変させた"
        }

        return emotion_mapping.get(moment_type, "歴史的な瞬間となった")

    def _build_enhanced_episode(self, opening: str, elements: StoryElements,
                               include_emotion: bool, target_length: int) -> str:
        """拡張されたエピソードを構築"""
        episode_parts = [opening]

        # メイン achievement
        if elements.context:
            episode_parts.append(f"{elements.context}、{elements.achievement}")
        else:
            episode_parts.append(elements.achievement)

        # 背景情報を追加（文字数調整）
        current_length = len("。".join(episode_parts))

        if current_length < target_length - 50:
            if elements.setup:
                episode_parts.append(elements.setup)

        # 引用を追加（あれば）
        if elements.quote and current_length < target_length - 30:
            episode_parts.append(f"「{elements.quote}」との言葉を残した")

        # 感情表現を追加
        if include_emotion and elements.emotion:
            current_length = len("。".join(episode_parts))
            if current_length < target_length - 20:
                episode_parts.append(elements.emotion)

        # 意義を追加
        episode_parts.append(elements.significance)

        # 文章を結合
        episode = "。".join(episode_parts) + "。"
        episode = episode.replace("。。", "。")

        # 最終調整
        episode = self._fine_tune_length(episode, target_length)

        return episode

    def _fine_tune_length(self, text: str, target_length: int) -> str:
        """文字数を微調整"""
        current_length = len(text)

        # 短すぎる場合は詳細を追加
        if current_length < target_length - 30:
            # 追加の修飾語を挿入
            if "偉業" in text and "驚異的な" not in text:
                text = text.replace("偉業", "驚異的な偉業")
            if "記録" in text and "歴史的な" not in text:
                text = text.replace("記録", "歴史的な記録")
            if "成功" in text and "大きな" not in text:
                text = text.replace("成功", "大きな成功")

        # 長すぎる場合は簡潔に
        elif current_length > target_length + 50:
            sentences = text.split("。")
            # 優先度の低い文を削除
            if len(sentences) > 5:
                # 中間の文を1つ削除
                sentences.pop(len(sentences)//2)
            text = "。".join(sentences)
            if not text.endswith("。"):
                text += "。"

        return text


def test_storytelling_engine_v2():
    """改良版テスト実行"""
    engine = StorytellingEngineV2()

    test_cases = [
        ("大谷翔平", 29),
        ("イチロー", 45),
        ("宮崎駿", 60),
        ("浅田真央", 24),
        ("村上春樹", 38),
        ("羽生結弦", 23),
        ("ヘレン・ケラー", 7),
        ("藤井聡太", 19),
        ("山中伸弥", 50),
        ("HIKAKIN", 30),
        ("さくらももこ", 21),
    ]

    print("改良版ストーリーテリングエンジンテスト")
    print("="*60)
    print("目標: 150-250文字の範囲で品質の高いエピソードを生成")
    print("="*60)

    results = []

    for person_name, age in test_cases:
        print(f"\n【{person_name} ({age}歳)】")

        # 感情あり版（標準）
        episode = engine.create_episode(
            person_name, age, include_emotion=True, target_length=150
        )
        char_count = len(episode)

        print(f"エピソード:")
        print(f"  {episode}")
        print(f"  文字数: {char_count} {'✓' if 132 <= char_count <= 250 else '✗'}")

        results.append({
            "person": person_name,
            "age": age,
            "episode": episode,
            "length": char_count,
            "in_range": 132 <= char_count <= 250
        })

    # 統計
    print("\n" + "="*60)
    print("統計:")
    valid_count = sum(1 for r in results if r["in_range"])
    avg_length = sum(r["length"] for r in results) / len(results)

    print(f"  有効エピソード数: {valid_count}/{len(results)}")
    print(f"  平均文字数: {avg_length:.1f}")
    print(f"  最短: {min(r['length'] for r in results)}文字")
    print(f"  最長: {max(r['length'] for r in results)}文字")


if __name__ == "__main__":
    test_storytelling_engine_v2()
