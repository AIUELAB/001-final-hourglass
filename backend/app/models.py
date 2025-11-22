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


class FameScore(BaseModel):
    """有名度スコアモデル"""
    id: int
    person_name: str
    fame_tier: int
    fame_score: int
    composite_score: int
    wikipedia_ja: bool
    textbook: bool
    award_level: int
    notoriety: bool
    last_updated: str


class FameRanking(BaseModel):
    """有名度ランキングモデル"""
    total: int
    rankings: list[FameScore]


class FameDetail(BaseModel):
    """有名度詳細モデル"""
    person_name: str
    fame_tier: int
    fame_score: int
    composite_score: int
    quality_score: float
    wikipedia_ja: bool
    textbook: bool
    award_level: int
    notoriety: bool
    category: str
    person_type: str
    evaluation_breakdown: dict
    last_updated: str
