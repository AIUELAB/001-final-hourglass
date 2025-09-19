#!/usr/bin/env python3
"""
エピソードデータ用の敬称なし短縮名生成
- エピソードデータでは敬称を付けない
- シンプルで読みやすい名前表示
"""

import json
from pathlib import Path
from typing import Any

from japanese_name_shortener import JapaneseNameShortener, PersonInfo


class EpisodeDisplayNameGenerator:
    """エピソードデータ用表示名生成クラス"""

    def __init__(self) -> None:
        self.shortener = JapaneseNameShortener()

    def _process_character_list(self, characters: list[Any]) -> None:
        """
        リスト形式の登場人物データを処理

        Args:
            characters: 登場人物のリスト
        """
        for character in characters:
            if isinstance(character, dict) and 'name' in character:
                person_info = PersonInfo(name=character['name'])
                display_name = self.shortener.generate_short_name_no_honorific(person_info)
                character['display_name_ja'] = display_name

    def _process_character_dict(self, characters: dict[str, Any]) -> None:
        """
        辞書形式の登場人物データを処理

        Args:
            characters: 登場人物の辞書
        """
        for char_data in characters.values():
            if isinstance(char_data, dict) and 'name' in char_data:
                person_info = PersonInfo(name=char_data['name'])
                display_name = self.shortener.generate_short_name_no_honorific(person_info)
                char_data['display_name_ja'] = display_name

    def _process_single_person(self, person_data: dict[str, Any]) -> None:
        """
        単一の人物データを処理

        Args:
            person_data: 人物データの辞書
        """
        if 'name' in person_data:
            person_info = PersonInfo(name=person_data['name'])
            display_name = self.shortener.generate_short_name_no_honorific(person_info)
            person_data['display_name_ja'] = display_name

    def _process_characters_field(self, processed_episode: dict[str, Any]) -> None:
        """
        登場人物フィールドを処理

        Args:
            processed_episode: 処理中のエピソードデータ
        """
        if 'characters' not in processed_episode:
            return

        characters = processed_episode['characters']
        if isinstance(characters, list):
            self._process_character_list(characters)
        elif isinstance(characters, dict):
            self._process_character_dict(characters)

    def _process_person_fields(self, processed_episode: dict[str, Any]) -> None:
        """
        人物関連フィールドを処理

        Args:
            processed_episode: 処理中のエピソードデータ
        """
        person_fields = ['main_character', 'protagonist', 'antagonist', 'supporting_character', 'narrator']

        for field in person_fields:
            if field in processed_episode:
                person_data = processed_episode[field]
                if isinstance(person_data, dict):
                    self._process_single_person(person_data)

    def process_episode_data(self, episode_data: dict[str, Any]) -> dict[str, Any]:
        """
        エピソードデータを処理

        Args:
            episode_data: エピソードデータの辞書

        Returns:
            処理後のエピソードデータ
        """
        processed_episode = episode_data.copy()

        # 登場人物の名前を敬称なしで処理
        self._process_characters_field(processed_episode)

        # その他の人物フィールドを処理
        self._process_person_fields(processed_episode)

        return processed_episode

    def generate_episode_display_names(self, input_file: str, output_file: str) -> None:
        """
        エピソードデータの表示用短縮名を生成

        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス
        """
        print(f"🎬 エピソードデータ用表示名の生成を開始: {input_file}")

        # JSONファイルを読み込み
        input_path = Path(input_file)
        with input_path.open(encoding='utf-8') as f:
            data = json.load(f)

        # データの形式を確認
        processed_data: dict[str, Any] | list[dict[str, Any]]
        if isinstance(data, dict):
            # 単一のエピソードデータの場合
            processed_data = self.process_episode_data(data)
            total_episodes = 1
        elif isinstance(data, list):
            # エピソードのリストの場合
            processed_data = []
            for episode in data:
                processed_episode = self.process_episode_data(episode)
                processed_data.append(processed_episode)
            total_episodes = len(data)
        else:
            print(f"❌ サポートされていないデータ形式: {type(data)}")
            return

        # 処理後のデータを保存
        output_path = Path(output_file)
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ エピソードデータ用表示名の生成完了: {output_file}")
        print("📊 処理結果:")
        print(f"  処理されたエピソード数: {total_episodes}")
        print("🔤 エピソードデータでは敬称なしの名前表示が適用されました")


def main() -> None:
    """メイン処理"""
    generator = EpisodeDisplayNameGenerator()

    # エピソードデータファイルのパス(実際のファイルパスに変更してください)
    input_file = 'episodes_data.json'  # 実際のエピソードデータファイル
    output_file = 'episodes_with_display_names.json'

    try:
        # エピソードデータの表示用短縮名を生成
        generator.generate_episode_display_names(input_file, output_file)

    except FileNotFoundError:
        print(f"⚠️ ファイルが見つかりません: {input_file}")
        print("実際のエピソードデータファイルのパスを指定してください")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
