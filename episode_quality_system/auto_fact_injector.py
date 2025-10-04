#!/usr/bin/env python3
"""
AutoFactInjector - 自動事実注入システム
エピソードが短い場合や定型文を使いそうな場面で、自動的に事実を追加
"""

import json
import random
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class AutoFactInjector:
    """自動事実注入システム"""

    def __init__(self, facts_db_path: str = None):
        """
        初期化

        Args:
            facts_db_path: person_facts.jsonのパス
        """
        if facts_db_path is None:
            facts_db_path = Path(__file__).parent / "data" / "person_facts.json"

        self.facts_db = self._load_facts_database(facts_db_path)

        # 文字数目標
        self.MIN_LENGTH = 132
        self.MAX_LENGTH = 250
        self.TARGET_LENGTH = 180  # 理想的な長さ

        # 事実カテゴリの優先順位
        self.category_priority = [
            "achievements",  # 実績が最優先
            "numbers",      # 具体的数値
            "timeline",     # 時系列情報
            "unique"        # ユニークな特徴
        ]

        # 接続詞パターン（自然な文章のため）
        self.connectors = [
            "さらに",
            "また",
            "その他にも",
            "同時に",
            "加えて"
        ]

    def _load_facts_database(self, path: str) -> Dict:
        """
        事実データベースを読み込み

        Args:
            path: JSONファイルのパス

        Returns:
            事実データベース
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("persons", {})
        except FileNotFoundError:
            print(f"警告: {path} が見つかりません。空のデータベースで初期化します。")
            return {}
        except json.JSONDecodeError as e:
            print(f"エラー: JSONの読み込みに失敗: {e}")
            return {}

    def needs_injection(self, episode_text: str) -> Tuple[bool, int]:
        """
        事実注入が必要かチェック

        Args:
            episode_text: エピソードテキスト

        Returns:
            (注入が必要か, 必要な文字数)
        """
        current_length = len(episode_text)

        # 短すぎる場合
        if current_length < self.MIN_LENGTH:
            needed_chars = self.TARGET_LENGTH - current_length
            return True, needed_chars

        # 定型文っぽい終わり方を検出
        template_endings = [
            r'活躍.*。$',
            r'貢献.*。$',
            r'影響.*。$',
            r'記録.*。$',
            r'成果.*。$'
        ]

        for pattern in template_endings:
            if re.search(pattern, episode_text):
                # 定型文で終わっている場合、事実で置き換え
                needed_chars = 50  # 追加の事実で補強
                return True, needed_chars

        return False, 0

    def select_facts(self, person_name: str, needed_chars: int,
                    exclude_facts: List[str] = None) -> List[str]:
        """
        注入する事実を選択

        Args:
            person_name: 人物名
            needed_chars: 必要な文字数
            exclude_facts: 除外する事実（既に使用済み）

        Returns:
            選択された事実のリスト
        """
        if person_name not in self.facts_db:
            return []

        person_facts = self.facts_db[person_name]["facts"]
        exclude_facts = exclude_facts or []
        selected_facts = []
        current_chars = 0

        # カテゴリ優先順位に従って選択
        for category in self.category_priority:
            if category not in person_facts:
                continue

            available_facts = [
                fact for fact in person_facts[category]
                if fact not in exclude_facts
            ]

            # ランダムにシャッフル（多様性のため）
            random.shuffle(available_facts)

            for fact in available_facts:
                fact_length = len(fact)
                if current_chars + fact_length <= needed_chars + 20:  # 少し余裕を持たせる
                    selected_facts.append(fact)
                    current_chars += fact_length

                if current_chars >= needed_chars:
                    break

            if current_chars >= needed_chars:
                break

        return selected_facts

    def inject_facts(self, episode_text: str, person_name: str,
                     age: int = None) -> Tuple[str, List[str]]:
        """
        エピソードに事実を注入

        Args:
            episode_text: 元のエピソードテキスト
            person_name: 人物名
            age: 年齢（コンテキスト用）

        Returns:
            (改善されたエピソード, 使用した事実リスト)
        """
        needs_injection, needed_chars = self.needs_injection(episode_text)

        if not needs_injection:
            return episode_text, []

        # 既存のエピソードから既に使われている事実を抽出
        used_facts = self._extract_used_facts(episode_text, person_name)

        # 新しい事実を選択
        new_facts = self.select_facts(person_name, needed_chars, used_facts)

        if not new_facts:
            return episode_text, []

        # エピソードを構築
        improved_episode = self._build_improved_episode(
            episode_text, new_facts, person_name, age
        )

        return improved_episode, new_facts

    def _extract_used_facts(self, episode_text: str, person_name: str) -> List[str]:
        """
        既に使用されている事実を抽出

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名

        Returns:
            使用済み事実のリスト
        """
        used_facts = []

        if person_name not in self.facts_db:
            return used_facts

        person_facts = self.facts_db[person_name]["facts"]

        # 全カテゴリの事実をチェック
        for category in person_facts:
            for fact in person_facts[category]:
                # 事実の主要部分がエピソードに含まれているかチェック
                key_parts = self._extract_key_parts(fact)
                if any(part in episode_text for part in key_parts):
                    used_facts.append(fact)

        return used_facts

    def _extract_key_parts(self, fact: str) -> List[str]:
        """
        事実から主要部分を抽出

        Args:
            fact: 事実テキスト

        Returns:
            主要部分のリスト
        """
        # 数値、賞名、記録などを抽出
        key_parts = []

        # 数値パターン
        numbers = re.findall(r'\d+[^\s]*', fact)
        key_parts.extend(numbers)

        # 賞・タイトル（「」内）
        titles = re.findall(r'「([^」]+)」', fact)
        key_parts.extend(titles)

        # 重要キーワード
        keywords = re.findall(r'(優勝|受賞|達成|記録|樹立|獲得)', fact)
        key_parts.extend(keywords)

        return [part for part in key_parts if len(part) > 2]

    def _build_improved_episode(self, original: str, new_facts: List[str],
                               person_name: str, age: int = None) -> str:
        """
        改善されたエピソードを構築

        Args:
            original: 元のエピソード
            new_facts: 追加する事実
            person_name: 人物名
            age: 年齢

        Returns:
            改善されたエピソード
        """
        # 定型文的な終わりを削除
        cleaned_episode = self._remove_template_ending(original)

        # 事実を自然に追加
        if new_facts:
            # 接続詞を選択
            connector = random.choice(self.connectors)

            # 事実を文章化
            fact_sentences = []
            for i, fact in enumerate(new_facts):
                if i == 0:
                    fact_sentences.append(f"{connector}{fact}")
                else:
                    fact_sentences.append(fact)

            # エピソードを結合
            improved = f"{cleaned_episode}{'。' if not cleaned_episode.endswith('。') else ''}"
            improved += "".join(fact_sentences)

            # 文字数チェックと調整
            if len(improved) > self.MAX_LENGTH:
                improved = self._trim_to_length(improved)

            # 最後が句点で終わることを確認
            if not improved.endswith("。"):
                improved += "。"

            return improved

        return original

    def _remove_template_ending(self, text: str) -> str:
        """
        定型文的な終わりを削除

        Args:
            text: テキスト

        Returns:
            クリーンなテキスト
        """
        # 定型文パターンを削除
        template_patterns = [
            r'その後も[^。]*。?$',
            r'現在も[^。]*。?$',
            r'今も[^。]*。?$',
            r'[^。]*影響を与え[^。]*。?$',
            r'[^。]*貢献し[^。]*。?$'
        ]

        for pattern in template_patterns:
            text = re.sub(pattern, '', text)

        return text.rstrip("。").rstrip()

    def _trim_to_length(self, text: str) -> str:
        """
        最大文字数に収まるようトリミング

        Args:
            text: テキスト

        Returns:
            トリミングされたテキスト
        """
        if len(text) <= self.MAX_LENGTH:
            return text

        # 句点で分割
        sentences = text.split("。")
        trimmed = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence) + 1  # 句点分
            if current_length + sentence_length <= self.MAX_LENGTH:
                trimmed.append(sentence)
                current_length += sentence_length
            else:
                break

        return "。".join(trimmed) + "。" if trimmed else text[:self.MAX_LENGTH]

    def validate_injection(self, episode: str) -> Dict[str, any]:
        """
        注入後のエピソードを検証

        Args:
            episode: エピソード

        Returns:
            検証結果
        """
        validation = {
            "valid": True,
            "length": len(episode),
            "length_ok": self.MIN_LENGTH <= len(episode) <= self.MAX_LENGTH,
            "has_facts": False,
            "has_template": False
        }

        # 文字数チェック
        if not validation["length_ok"]:
            validation["valid"] = False

        # 事実の存在チェック（数値や具体的な記録）
        fact_patterns = [
            r'\d+',  # 数値
            r'優勝|受賞|達成|記録',  # 実績
            r'「[^」]+」',  # タイトル
        ]

        for pattern in fact_patterns:
            if re.search(pattern, episode):
                validation["has_facts"] = True
                break

        # 定型文チェック
        template_patterns = [
            r'その後も',
            r'多くの.*影響',
            r'現在も.*続',
            r'永遠に.*残'
        ]

        for pattern in template_patterns:
            if re.search(pattern, episode):
                validation["has_template"] = True
                validation["valid"] = False
                break

        return validation


def test_auto_fact_injector():
    """テスト実行"""
    injector = AutoFactInjector()

    # テストケース
    test_cases = [
        {
            "name": "大谷翔平",
            "age": 30,
            "episode": "あなたと同じ30歳のとき、大谷翔平は二刀流で活躍した。",  # 短すぎる
            "description": "短いエピソード"
        },
        {
            "name": "松井秀喜",
            "age": 31,
            "episode": "あなたと同じ31歳のとき、松井秀喜はヤンキースで31本塁打を記録した。その後も活躍を続けた。",  # 定型文あり
            "description": "定型文を含むエピソード"
        },
        {
            "name": "イチロー",
            "age": 27,
            "episode": "あなたと同じ27歳のとき、イチローはMLBで242安打を記録し、シーズン最多安打記録を84年ぶりに更新した。この年の打率は.372で、首位打者も獲得した。",  # 良い例
            "description": "既に良質なエピソード"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"テストケース {i}: {test_case['description']}")
        print(f"人物: {test_case['name']}")
        print(f"元のエピソード: {test_case['episode']}")
        print(f"文字数: {len(test_case['episode'])}")

        # 事実注入
        improved, used_facts = injector.inject_facts(
            test_case['episode'],
            test_case['name'],
            test_case['age']
        )

        print(f"\n改善後: {improved}")
        print(f"文字数: {len(improved)}")

        if used_facts:
            print(f"\n追加された事実:")
            for fact in used_facts:
                print(f"  • {fact}")

        # 検証
        validation = injector.validate_injection(improved)
        print(f"\n検証結果:")
        print(f"  有効: {'✅' if validation['valid'] else '❌'}")
        print(f"  文字数OK: {'✅' if validation['length_ok'] else '❌'} ({validation['length']}文字)")
        print(f"  事実あり: {'✅' if validation['has_facts'] else '❌'}")
        print(f"  定型文なし: {'✅' if not validation['has_template'] else '❌'}")


if __name__ == "__main__":
    test_auto_fact_injector()