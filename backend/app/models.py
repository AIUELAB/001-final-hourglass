"""
Pydantic モデル定義

APIのリクエスト/レスポンスモデル
"""

from pydantic import BaseModel, Field
from typing import Optional


class Character(BaseModel):
    """キャラクターモデル"""

    id: int = Field(..., description="キャラクターID")
    character_name: str = Field(..., description="キャラクター名")
    work_title: str = Field(..., description="作品名")
    genre: str = Field(..., description="ジャンル")
    episode_category: str = Field(..., description="エピソードカテゴリ")
    episode_text: str = Field(..., description="エピソード本文")


class CharacterList(BaseModel):
    """キャラクターリストモデル（ページネーション対応）"""

    total: int = Field(..., description="総件数")
    page: int = Field(..., description="現在のページ番号")
    page_size: int = Field(..., description="ページサイズ")
    characters: list[Character] = Field(..., description="キャラクターリスト")


class StatsSummary(BaseModel):
    """統計サマリーモデル"""

    total_characters: int = Field(..., description="総キャラクター数")
    total_genres: int = Field(..., description="総ジャンル数")
    female_count: int = Field(..., description="女性キャラクター数")
    male_count: int = Field(..., description="男性キャラクター数")
    female_ratio: float = Field(..., description="女性比率（%）")
    era_range: Optional[str] = Field(None, description="年代範囲")


class GenreStats(BaseModel):
    """ジャンル統計モデル"""

    genre: str = Field(..., description="ジャンル名")
    count: int = Field(..., description="キャラクター数")
    percentage: float = Field(..., description="割合（%）")


class GenderStats(BaseModel):
    """性別統計モデル"""

    gender: str = Field(..., description="性別")
    count: int = Field(..., description="キャラクター数")
    percentage: float = Field(..., description="割合（%）")
