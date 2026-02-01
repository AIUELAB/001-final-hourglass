#!/usr/bin/env python3
"""
Canon Knowledge Base - 原作情報データベースローダー

架空キャラクターエピソードの真正性検証に使用する
原作情報（key_scenes, age_milestones）を管理するクラス。

## 用途
- エピソード生成時の原作シーン検証
- 年齢別マイルストーンの参照
- キャラクターの作品横断検索

## 使用例
    kb = CanonKB()
    scenes = kb.get_character_scenes("竈門炭治郎")
    milestones = kb.get_milestones_for_age("鬼滅の刃", "竈門炭治郎", 15)

Author: EPUP Validation Team
Date: 2026-01-30
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class KeyScene:
    """キャラクターの重要シーン情報"""

    scene_id: str
    description: str
    story_arc: str
    source_type: str  # manga, anime, movie
    source_reference: str  # 第1話, 第23巻 等

    @classmethod
    def from_dict(cls, data: dict) -> "KeyScene":
        """辞書からKeySceneを生成"""
        source = data.get("source", {})
        return cls(
            scene_id=data.get("scene_id", ""),
            description=data.get("description", ""),
            story_arc=data.get("story_arc", ""),
            source_type=source.get("type", "") if isinstance(source, dict) else "",
            source_reference=source.get("reference", "") if isinstance(source, dict) else "",
        )


@dataclass
class AgeMilestone:
    """年齢別の重要イベント情報"""

    age: int
    events: list[str]
    source: str

    @classmethod
    def from_dict(cls, data: dict) -> "AgeMilestone":
        """辞書からAgeMilestoneを生成"""
        return cls(
            age=data.get("age", 0),
            events=data.get("events", []),
            source=data.get("source", ""),
        )


@dataclass
class Character:
    """キャラクター情報"""

    name: str
    character_id: str
    aliases: list[str]
    age_at_story: Optional[int]
    abilities: list[str]
    key_scenes: list[KeyScene]
    age_milestones: list[AgeMilestone]

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Character":
        """辞書からCharacterを生成"""
        key_scenes = [KeyScene.from_dict(s) for s in data.get("key_scenes", [])]
        age_milestones = [AgeMilestone.from_dict(m) for m in data.get("age_milestones", [])]

        return cls(
            name=name,
            character_id=data.get("character_id", ""),
            aliases=data.get("aliases", []),
            age_at_story=data.get("age_at_story"),
            abilities=data.get("abilities", []),
            key_scenes=key_scenes,
            age_milestones=age_milestones,
        )


@dataclass
class StoryArc:
    """物語編情報"""

    arc_name: str
    order: int
    main_characters: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "StoryArc":
        """辞書からStoryArcを生成"""
        return cls(
            arc_name=data.get("arc_name", ""),
            order=data.get("order", 0),
            main_characters=data.get("main_characters", []),
        )


@dataclass
class Work:
    """作品情報"""

    work_id: str
    title: str
    title_variants: list[str]
    source_urls: list[str]
    era_setting: str
    characters: dict[str, Character]
    story_arcs: list[StoryArc]

    @classmethod
    def from_dict(cls, data: dict) -> "Work":
        """辞書からWorkを生成"""
        characters = {}
        for char_name, char_data in data.get("characters", {}).items():
            characters[char_name] = Character.from_dict(char_name, char_data)

        story_arcs = [StoryArc.from_dict(arc) for arc in data.get("story_arcs", [])]

        return cls(
            work_id=data.get("work_id", ""),
            title=data.get("work_title", ""),
            title_variants=data.get("work_title_variants", []),
            source_urls=data.get("source_urls", []),
            era_setting=data.get("era_setting", ""),
            characters=characters,
            story_arcs=story_arcs,
        )


# =============================================================================
# CanonKB クラス
# =============================================================================


class CanonKB:
    """
    Canon Knowledge Base ローダー

    原作情報データベース（canon_knowledge_base.json）を読み込み、
    作品・キャラクター・シーン情報へのアクセスを提供する。
    """

    DEFAULT_PATH = PROJECT_ROOT / "preserved/data/canon_knowledge_base.json"

    def __init__(self, kb_path: Optional[Path] = None):
        """
        初期化時にJSONをロード

        Args:
            kb_path: Knowledge BaseのJSONファイルパス（指定しない場合はデフォルト）
        """
        self._kb_path = kb_path or self.DEFAULT_PATH
        self._works: dict[str, Work] = {}
        self._title_to_work: dict[str, str] = {}  # タイトル変種 -> 正式タイトルのマッピング
        self._loaded = False

        self._load()

    def _load(self) -> None:
        """JSONファイルを読み込み、dataclassに変換"""
        if self._loaded:
            return

        if not self._kb_path.exists():
            logger.warning(f"Canon Knowledge Base not found: {self._kb_path}. Operating with empty KB.")
            self._loaded = True
            return

        try:
            with open(self._kb_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Canon KB JSON: {e}")
            self._loaded = True
            return

        # 作品データをロード
        works_data = data.get("works", {})
        for work_title, work_data in works_data.items():
            work = Work.from_dict(work_data)
            self._works[work_title] = work

            # タイトル変種のマッピングを登録
            self._title_to_work[work_title] = work_title
            for variant in work.title_variants:
                self._title_to_work[variant] = work_title

        self._loaded = True
        logger.info(f"Canon KB loaded: {len(self._works)} works")

    def get_work(self, work_title: str) -> Optional[Work]:
        """
        作品情報を取得

        Args:
            work_title: 作品タイトル（変種も対応）

        Returns:
            Work: 作品情報（見つからない場合はNone）
        """
        if not work_title:
            return None

        # 完全一致
        if work_title in self._works:
            return self._works[work_title]

        # 変種から検索
        if work_title in self._title_to_work:
            canonical_title = self._title_to_work[work_title]
            return self._works.get(canonical_title)

        # 部分一致
        for title, work in self._works.items():
            if title in work_title or work_title in title:
                return work

        return None

    def get_character(self, work_title: str, character_name: str) -> Optional[Character]:
        """
        キャラクター情報を取得（aliases も検索）

        Args:
            work_title: 作品タイトル
            character_name: キャラクター名（aliasesも検索対象）

        Returns:
            Character: キャラクター情報（見つからない場合はNone）
        """
        work = self.get_work(work_title)
        if not work:
            return None

        # 正式名で検索
        if character_name in work.characters:
            return work.characters[character_name]

        # aliases で検索
        for char in work.characters.values():
            if character_name in char.aliases:
                return char

        return None

    def get_character_scenes(self, character_name: str) -> list[KeyScene]:
        """
        全作品からキャラクターのシーンを検索

        Args:
            character_name: キャラクター名（aliasesも検索対象）

        Returns:
            list[KeyScene]: 該当するシーンのリスト
        """
        scenes: list[KeyScene] = []

        for work in self._works.values():
            # 正式名で検索
            if character_name in work.characters:
                scenes.extend(work.characters[character_name].key_scenes)
                continue

            # aliases で検索
            for char in work.characters.values():
                if character_name in char.aliases:
                    scenes.extend(char.key_scenes)
                    break

        return scenes

    def has_scene(self, work_title: str, character: str, scene_ref: str) -> bool:
        """
        指定の出典がKBに存在するか確認

        Args:
            work_title: 作品タイトル
            character: キャラクター名
            scene_ref: 出典参照（例: "第1話", "第23巻"）

        Returns:
            bool: 該当するシーンが存在すればTrue
        """
        char = self.get_character(work_title, character)
        if not char:
            return False

        for scene in char.key_scenes:
            if scene.source_reference == scene_ref:
                return True
            # 部分一致も許可
            if scene_ref in scene.source_reference or scene.source_reference in scene_ref:
                return True

        return False

    def get_milestones_for_age(self, work_title: str, character: str, age: int) -> list[str]:
        """
        指定年齢のマイルストーンイベントを取得

        Args:
            work_title: 作品タイトル
            character: キャラクター名
            age: 年齢

        Returns:
            list[str]: その年齢でのイベントリスト
        """
        char = self.get_character(work_title, character)
        if not char:
            return []

        for milestone in char.age_milestones:
            if milestone.age == age:
                return milestone.events

        return []

    def list_works(self) -> list[str]:
        """
        登録済み作品一覧を取得

        Returns:
            list[str]: 作品タイトルのリスト
        """
        return list(self._works.keys())

    def list_characters(self, work_title: str) -> list[str]:
        """
        作品内のキャラクター一覧を取得

        Args:
            work_title: 作品タイトル

        Returns:
            list[str]: キャラクター名のリスト
        """
        work = self.get_work(work_title)
        if not work:
            return []

        return list(work.characters.keys())

    def find_character_by_alias(self, alias: str) -> list[tuple[str, Character]]:
        """
        エイリアスからキャラクターを検索（全作品対象）

        Args:
            alias: キャラクターのエイリアス

        Returns:
            list[tuple[str, Character]]: (作品タイトル, キャラクター) のリスト
        """
        results: list[tuple[str, Character]] = []

        for work_title, work in self._works.items():
            for char in work.characters.values():
                if alias == char.name or alias in char.aliases:
                    results.append((work_title, char))

        return results

    def get_story_arcs(self, work_title: str) -> list[StoryArc]:
        """
        作品のストーリーアーク一覧を取得

        Args:
            work_title: 作品タイトル

        Returns:
            list[StoryArc]: ストーリーアークのリスト（order順）
        """
        work = self.get_work(work_title)
        if not work:
            return []

        return sorted(work.story_arcs, key=lambda arc: arc.order)


# =============================================================================
# CLI (テスト用)
# =============================================================================


if __name__ == "__main__":
    # テスト実行
    kb = CanonKB()

    print("=" * 60)
    print("Canon Knowledge Base - テスト実行")
    print("=" * 60)

    # 登録済み作品一覧
    print("\n[登録済み作品]")
    works = kb.list_works()
    for work_title in works:
        print(f"  - {work_title}")

    # キャラクター検索テスト
    print("\n[キャラクター検索: 竈門炭治郎]")
    scenes = kb.get_character_scenes("竈門炭治郎")
    if scenes:
        print(f"  シーン数: {len(scenes)}")
        for scene in scenes[:3]:  # 最初の3件
            print(f"    - {scene.scene_id}: {scene.description}")
    else:
        print("  シーンなし（key_scenesが空）")

    # 鬼滅の刃のキャラクター一覧
    print("\n[鬼滅の刃 キャラクター一覧]")
    characters = kb.list_characters("鬼滅の刃")
    for char_name in characters:
        print(f"  - {char_name}")

    # エイリアス検索テスト
    print("\n[エイリアス検索: 炭治郎]")
    results = kb.find_character_by_alias("炭治郎")
    for work_title, char in results:
        print(f"  - {work_title}: {char.name} (aliases: {char.aliases})")

    # ストーリーアーク
    print("\n[鬼滅の刃 ストーリーアーク]")
    arcs = kb.get_story_arcs("鬼滅の刃")
    for arc in arcs[:5]:  # 最初の5件
        print(f"  {arc.order}. {arc.arc_name}")
