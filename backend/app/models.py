"""データモデル定義"""

from typing import Literal, Optional

from pydantic import BaseModel


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
    # Phase 1: 3軸評価カラム
    milestone_tags: Optional[str] = None
    memorability_score: Optional[float] = None
    empathy_score: Optional[float] = None
    surprise_score: Optional[float] = None
    # Phase 2: 4軸評価カラム
    generation_quality_score: Optional[float] = None
    educational_value: Optional[float] = None
    storytelling_quality: Optional[float] = None
    factual_density: Optional[float] = None


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


# ========================================
# Phase 3: 分析モデル
# ========================================


class AxisStatistics(BaseModel):
    """軸統計モデル"""

    name: str
    count: int
    mean: float
    median: float
    stdev: float
    min: float
    max: float


class DistributionBin(BaseModel):
    """分布ビンモデル"""

    range: str
    bin_start: float
    bin_end: float
    count: int
    percentage: float


class CorrelationRow(BaseModel):
    """相関行モデル"""

    axis: str
    記憶性スコア: float
    共感性スコア: float
    意外性スコア: float
    生成品質スコア: float
    教育的価値: float
    ストーリー品質: float
    事実密度: float


class TopPerformer(BaseModel):
    """トップパフォーマーモデル"""

    person_name: str
    age: str
    episode: str
    composite_score: float
    memorability_score: float
    empathy_score: float
    surprise_score: float
    generation_quality_score: float
    educational_value: float
    storytelling_quality: float
    factual_density: float


class ScoreSummary(BaseModel):
    """スコアサマリーモデル"""

    total_episodes: int
    axes: list[AxisStatistics]


# ========================================
# Phase 4: 高度な検索モデル
# ========================================


class EpisodeSearchResult(BaseModel):
    """エピソード検索結果"""

    person_name: str
    age: str
    episode: str
    composite_score: float
    memorability_score: float = 0.0
    empathy_score: float = 0.0
    surprise_score: float = 0.0
    generation_quality_score: float = 0.0
    educational_value: float = 0.0
    storytelling_quality: float = 0.0
    factual_density: float = 0.0


class EpisodeSearchResponse(BaseModel):
    """エピソード検索レスポンス"""

    total: int
    page: int
    page_size: int
    results: list[EpisodeSearchResult]


class SearchStatsResponse(BaseModel):
    """検索統計レスポンス"""

    total_episodes: int
    score_ranges: dict
    age_range: dict


# ========================================
# Phase 4: データ品質管理モデル
# ========================================


class DuplicateInfo(BaseModel):
    """重複情報"""

    person_name: str
    age: str
    count: int
    row_numbers: list[int]


class OutlierInfo(BaseModel):
    """外れ値情報"""

    person_name: str
    age: str
    row_number: int
    axis: str
    score: float
    mean: float
    stdev: float
    z_score: float


class CompletenessIssue(BaseModel):
    """完全性問題"""

    type: str
    field: Optional[str] = None
    axis: Optional[str] = None
    count: int
    percentage: Optional[float] = None
    examples: Optional[list] = None


class QualitySummary(BaseModel):
    """品質サマリー"""

    quality_score: float
    total_episodes: int
    duplicate_count: int
    duplicate_rate: float
    outlier_count: int
    outlier_rate: float
    completeness_issues: int
    grade: str


class QualityReport(BaseModel):
    """品質レポート"""

    summary: QualitySummary
    duplicates: dict
    outliers: dict
    completeness: dict


# ========================================
# Phase 5: エピソード管理（CRUD）モデル
# ========================================


class EpisodeBase(BaseModel):
    """エピソード基本モデル"""

    person_name: str
    age: str
    episode_text: str
    category: Optional[str] = None
    episode_type: Optional[str] = None
    person_type: Optional[str] = "REAL"
    work_title: Optional[str] = None
    group_name: Optional[str] = None
    is_group_member: Optional[bool] = False


class EpisodeCreate(EpisodeBase):
    """エピソード作成モデル"""

    # 7軸スコアは作成時にオプション（後で評価可能）
    memorability_score: Optional[float] = None
    empathy_score: Optional[float] = None
    surprise_score: Optional[float] = None
    generation_quality_score: Optional[float] = None
    educational_value: Optional[float] = None
    storytelling_quality: Optional[float] = None
    factual_density: Optional[float] = None

    # 人生の節目タグ
    milestone_tags: Optional[str] = None


class EpisodeUpdate(BaseModel):
    """エピソード更新モデル（すべてOptional）"""

    person_name: Optional[str] = None
    age: Optional[str] = None
    episode_text: Optional[str] = None
    category: Optional[str] = None
    episode_type: Optional[str] = None
    person_type: Optional[str] = None
    work_title: Optional[str] = None
    group_name: Optional[str] = None
    is_group_member: Optional[bool] = None

    # 7軸スコア
    memorability_score: Optional[float] = None
    empathy_score: Optional[float] = None
    surprise_score: Optional[float] = None
    generation_quality_score: Optional[float] = None
    educational_value: Optional[float] = None
    storytelling_quality: Optional[float] = None
    factual_density: Optional[float] = None

    # 人生の節目タグ
    milestone_tags: Optional[str] = None

    # ファクトチェック結果
    fact_check_result: Optional[str] = None


class Episode(BaseModel):
    """エピソード完全モデル（読み取り用）

    CSVデータをそのまま読み込むため、すべてのフィールドをOptionalかstrで定義
    """

    person_id: str
    person_name: str
    age: str
    episode_text: str = ""

    # 基本フィールド
    category: Optional[str] = None
    episode_type: Optional[str] = None
    person_type: Optional[str] = None
    work_title: Optional[str] = None
    group_name: Optional[str] = None
    is_group_member: Optional[str] = None  # CSVでは文字列（"True"/"False"/""）

    # メタデータ
    episode_count: Optional[str] = None
    char_count: Optional[str] = None
    fact_check_result: Optional[str] = None
    quality_score: Optional[str] = None
    slot: Optional[str] = None
    source: Optional[str] = None  # "V7_JSON"などの文字列
    tier: Optional[str] = None
    week: Optional[str] = None
    generation_timestamp: Optional[str] = None

    # 有名度関連
    fame_tier: Optional[str] = None
    wikipedia_ja: Optional[str] = None  # CSVでは文字列
    textbook: Optional[str] = None  # CSVでは文字列
    award_level: Optional[str] = None
    notoriety: Optional[str] = None  # CSVでは文字列
    fame_score: Optional[str] = None
    composite_score: Optional[str] = None
    fame_score_updated_at: Optional[str] = None
    episode_fame_score: Optional[str] = None  # エピソード有名度スコア
    episode_importance_score: Optional[str] = None  # エピソード重要度スコア

    # 7軸スコア（日本語カラム名）
    milestone_tags: Optional[str] = None
    人生の節目タグ: Optional[str] = None
    記憶性スコア: Optional[str] = None
    共感性スコア: Optional[str] = None
    意外性スコア: Optional[str] = None
    生成品質スコア: Optional[str] = None
    教育的価値: Optional[str] = None
    ストーリー品質: Optional[str] = None
    事実密度: Optional[str] = None
    age_numeric: Optional[str] = None


class EpisodeList(BaseModel):
    """エピソードリスト"""

    total: int
    page: int
    page_size: int
    episodes: list[Episode]


class EpisodeDeleteResponse(BaseModel):
    """エピソード削除レスポンス"""

    success: bool
    message: str
    deleted_person_id: str


# ========================================
# Phase 5: 認証関連モデル
# ========================================


class Token(BaseModel):
    """認証トークン"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """トークンデータ"""

    username: Optional[str] = None


class User(BaseModel):
    """ユーザーモデル"""

    username: str
    email: str
    full_name: str
    role: Literal["admin", "editor", "viewer"]
    disabled: bool = False


class UserInDB(User):
    """DBに保存されるユーザーモデル"""

    hashed_password: str
