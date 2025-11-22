"""データモデル定義"""

from pydantic import BaseModel
from typing import Optional


class Character(BaseModel):
    """キャラクターモデル"""
    id: int
    character_name: str
    work_title: str
    genre: str
    age_in_story: str
    key_episode: str
    detailed_achievements: str
    story_events: str
    growth_narrative: str
    wikipedia_url: str
    validation_status: str
    curator_notes: str


class CharacterList(BaseModel):
    """キャラクターリストモデル"""
    total: int
    page: int
    page_size: int
    characters: list[Character]


class StatsSummary(BaseModel):
    """統計サマリーモデル"""
    total_characters: int
    total_genres: int
    female_count: int
    male_count: int
    female_ratio: float
    era_range: str


class GenreStats(BaseModel):
    """ジャンル統計モデル"""
    genre: str
    count: int
    percentage: float


class GenderStats(BaseModel):
    """性別統計モデル"""
    gender: str
    count: int
    percentage: float


class EpisodeCategoryStats(BaseModel):
    """エピソードカテゴリ統計モデル"""
    category: str
    count: int
    percentage: float


class WorkStats(BaseModel):
    """作品統計モデル"""
    work_title: str
    count: int
    percentage: float
