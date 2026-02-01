#!/usr/bin/env python3
"""
CanonPromptEnhancer - 原作情報ベースのプロンプト強化システム

エピソード生成時にCanonKBから原作情報を取得し、
LLMへのプロンプトに組み込むことで、canon準拠の生成を促す。

## 使用例
    enhancer = CanonPromptEnhancer()
    enhanced_prompt = enhancer.enhance(
        person_name="竈門炭治郎",
        work_title="鬼滅の刃",
        age=13,
        base_prompt="エピソードを生成してください"
    )

Author: EPUP Validation Team
Date: 2026-01-30
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.utils.canon_kb import CanonKB, Character, KeyScene

logger = logging.getLogger(__name__)


@dataclass
class EnhancedPrompt:
    """強化されたプロンプト"""

    prompt: str  # 完全なプロンプト
    canon_events: list[str]  # 利用可能な原作イベント
    has_canon_data: bool  # CanonKBにデータがあるか
    suggested_source: Optional[str]  # 推奨出典


class CanonPromptEnhancer:
    """プロンプト強化エンジン"""

    # 強化プロンプトテンプレート
    ENHANCED_TEMPLATE = """
【キャラクター】{person_name}
【作品】{work_title}
【年齢】{age}歳

【原作で描かれた重要イベント（この中から選んで書く）】
{canon_events}

【禁止事項】
- 上記以外のシーンの創作
- 現実の年号（1900年〜2026年）の使用
- 現実の人物、企業、イベントの混入
- 販売本数、興行収入等のメタ情報
- 「映画化された」「アニメ化された」等の製作情報

【出力形式】
エピソードの最後に必ず出典を記載してください:
[canon: {suggested_source}]

【重要】
- 原作に該当シーンがない年齢の場合は「該当なし」と返答してください
- 原作出典のあるシーンのみ生成してください

---
{base_prompt}
""".strip()

    # データなし時のプロンプトテンプレート
    NO_DATA_TEMPLATE = """
【キャラクター】{person_name}
【作品】{work_title}
【年齢】{age}歳

【注意】原作情報がデータベースに登録されていません。

【厳格なルール】
- 原作に明確に描写されたシーンのみを記述すること
- 現実の年号（1900年〜2026年）の使用禁止
- 現実の人物、企業、イベントの混入禁止
- 販売本数、興行収入等のメタ情報禁止
- 「映画化された」「アニメ化された」等の製作情報禁止

【原作に該当シーンがない場合】
「該当なし」と返答してください。

---
{base_prompt}
""".strip()

    def __init__(self, canon_kb: Optional[CanonKB] = None):
        """
        初期化

        Args:
            canon_kb: CanonKBインスタンス（指定しない場合は新規作成）
        """
        self._canon_kb = canon_kb or CanonKB()

    def enhance(
        self,
        person_name: str,
        work_title: str,
        age: int,
        base_prompt: str = "",
    ) -> EnhancedPrompt:
        """
        プロンプトを強化

        Args:
            person_name: キャラクター名
            work_title: 作品タイトル
            age: 年齢
            base_prompt: 元のプロンプト

        Returns:
            EnhancedPrompt
        """
        # キャラクター情報を取得
        character = self._canon_kb.get_character(work_title, person_name)

        if not character:
            # CanonKBにデータがない場合
            logger.debug(f"No canon data for {person_name} in {work_title}")
            prompt = self.NO_DATA_TEMPLATE.format(
                person_name=person_name,
                work_title=work_title,
                age=age,
                base_prompt=base_prompt,
            )
            return EnhancedPrompt(
                prompt=prompt,
                canon_events=[],
                has_canon_data=False,
                suggested_source=None,
            )

        # 年齢別イベントを取得
        canon_events = self._get_events_for_age(character, age)
        canon_events_text = self.get_canon_events_text(person_name, work_title, age)
        suggested_source = self.get_suggested_source(person_name, work_title, age)

        # プロンプトを構築
        if canon_events:
            prompt = self.ENHANCED_TEMPLATE.format(
                person_name=person_name,
                work_title=work_title,
                age=age,
                canon_events=canon_events_text,
                suggested_source=suggested_source or "原作",
                base_prompt=base_prompt,
            )
        else:
            # 年齢に該当するイベントがない場合
            prompt = self.NO_DATA_TEMPLATE.format(
                person_name=person_name,
                work_title=work_title,
                age=age,
                base_prompt=base_prompt,
            )

        return EnhancedPrompt(
            prompt=prompt,
            canon_events=canon_events,
            has_canon_data=bool(canon_events),
            suggested_source=suggested_source,
        )

    def _get_events_for_age(self, character: Character, age: int) -> list[str]:
        """
        キャラクターの年齢に該当するイベントを取得

        Args:
            character: キャラクター情報
            age: 年齢

        Returns:
            list[str]: イベントのリスト
        """
        events: list[str] = []

        # age_milestonesから取得
        for milestone in character.age_milestones:
            if milestone.age == age:
                events.extend(milestone.events)

        # age_at_storyと一致する場合はkey_scenesも追加
        if character.age_at_story == age:
            for scene in character.key_scenes:
                if scene.description not in events:
                    events.append(scene.description)

        return events

    def _get_scenes_for_age(self, character: Character, age: int) -> list[KeyScene]:
        """
        キャラクターの年齢に該当するシーンを取得

        Args:
            character: キャラクター情報
            age: 年齢

        Returns:
            list[KeyScene]: シーンのリスト
        """
        if character.age_at_story == age:
            return character.key_scenes
        return []

    def get_canon_events_text(self, person_name: str, work_title: str, age: int) -> str:
        """
        該当年齢の原作イベントをテキスト形式で取得

        Args:
            person_name: キャラクター名
            work_title: 作品タイトル
            age: 年齢

        Returns:
            str: イベントのテキスト（箇条書き形式）
        """
        character = self._canon_kb.get_character(work_title, person_name)
        if not character:
            return "（データなし）"

        events = self._get_events_for_age(character, age)
        if not events:
            return "（この年齢の原作イベントは登録されていません）"

        # 箇条書き形式で整形
        lines = []
        for i, event in enumerate(events, 1):
            lines.append(f"  {i}. {event}")

        # シーンの出典情報も追加
        scenes = self._get_scenes_for_age(character, age)
        if scenes:
            lines.append("")
            lines.append("【出典詳細】")
            for scene in scenes[:5]:  # 最大5件
                source_info = f"[{scene.source_type}] {scene.source_reference}"
                lines.append(f"  - {scene.story_arc}: {source_info}")

        return "\n".join(lines)

    def get_suggested_source(self, person_name: str, work_title: str, age: int) -> Optional[str]:
        """
        推奨出典を取得

        Args:
            person_name: キャラクター名
            work_title: 作品タイトル
            age: 年齢

        Returns:
            str: 推奨出典（例: "第1話「残酷」"）
        """
        character = self._canon_kb.get_character(work_title, person_name)
        if not character:
            return None

        # age_milestonesのsourceを優先
        for milestone in character.age_milestones:
            if milestone.age == age and milestone.source:
                return milestone.source

        # key_scenesから最初の出典を取得
        scenes = self._get_scenes_for_age(character, age)
        if scenes:
            first_scene = scenes[0]
            return first_scene.source_reference

        return None

    def should_skip_generation(self, person_name: str, work_title: str, age: int) -> bool:
        """
        生成をスキップすべきか判定

        原作に該当年齢のイベントがない場合はTrue

        Args:
            person_name: キャラクター名
            work_title: 作品タイトル
            age: 年齢

        Returns:
            bool: スキップすべき場合True
        """
        character = self._canon_kb.get_character(work_title, person_name)
        if not character:
            # データがない場合はスキップしない（LLMに判断させる）
            return False

        events = self._get_events_for_age(character, age)
        return len(events) == 0

    def get_available_ages(self, person_name: str, work_title: str) -> list[int]:
        """
        原作情報がある年齢の一覧を取得

        Args:
            person_name: キャラクター名
            work_title: 作品タイトル

        Returns:
            list[int]: 原作情報がある年齢のリスト
        """
        character = self._canon_kb.get_character(work_title, person_name)
        if not character:
            return []

        ages = set()

        # age_milestonesから取得
        for milestone in character.age_milestones:
            if milestone.events:
                ages.add(milestone.age)

        # age_at_storyも追加
        if character.age_at_story is not None:
            ages.add(character.age_at_story)

        return sorted(ages)


# =============================================================================
# CLI (テスト用)
# =============================================================================


if __name__ == "__main__":
    enhancer = CanonPromptEnhancer()

    print("=" * 70)
    print("CanonPromptEnhancer - テスト実行")
    print("=" * 70)

    # テスト1: 竈門炭治郎 15歳（原作のストーリー年齢）
    print("\n[テスト1: 竈門炭治郎 15歳]")
    result = enhancer.enhance(
        person_name="竈門炭治郎",
        work_title="鬼滅の刃",
        age=15,
        base_prompt="人生の転機となったエピソードを生成してください",
    )
    print(f"Canon data: {result.has_canon_data}")
    print(f"Events count: {len(result.canon_events)}")
    print(f"Suggested source: {result.suggested_source}")
    print("\n--- プロンプト ---")
    print(result.prompt)

    # テスト2: 竈門炭治郎 13歳（原作に直接描写がない年齢）
    print("\n" + "=" * 70)
    print("[テスト2: 竈門炭治郎 13歳]")
    result2 = enhancer.enhance(
        person_name="竈門炭治郎",
        work_title="鬼滅の刃",
        age=13,
        base_prompt="人生の転機となったエピソードを生成してください",
    )
    print(f"Canon data: {result2.has_canon_data}")
    print(f"Should skip: {enhancer.should_skip_generation('竈門炭治郎', '鬼滅の刃', 13)}")

    # テスト3: 草壁サツキ 12歳
    print("\n" + "=" * 70)
    print("[テスト3: 草壁サツキ 12歳]")
    result3 = enhancer.enhance(
        person_name="草壁サツキ",
        work_title="となりのトトロ",
        age=12,
        base_prompt="人生の転機となったエピソードを生成してください",
    )
    print(f"Canon data: {result3.has_canon_data}")
    print(f"Events: {result3.canon_events}")
    print(f"Suggested source: {result3.suggested_source}")

    # テスト4: 利用可能な年齢一覧
    print("\n" + "=" * 70)
    print("[テスト4: 利用可能な年齢一覧]")
    ages = enhancer.get_available_ages("竈門炭治郎", "鬼滅の刃")
    print(f"竈門炭治郎: {ages}")

    ages2 = enhancer.get_available_ages("草壁サツキ", "となりのトトロ")
    print(f"草壁サツキ: {ages2}")

    ages3 = enhancer.get_available_ages("草壁メイ", "となりのトトロ")
    print(f"草壁メイ: {ages3}")
