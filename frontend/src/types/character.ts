/**
 * キャラクター型定義
 */

export interface Character {
  id: number;
  character_name: string;
  work_title: string;
  genre: string;
  age_in_story: string;
  key_episode: string;
  detailed_achievements: string;
  story_events: string;
  growth_narrative: string;
  wikipedia_url: string;
  validation_status: string;
  curator_notes: string;
}

export interface CharacterList {
  total: number;
  page: number;
  page_size: number;
  characters: Character[];
}

export interface StatsSummary {
  total_characters: number;
  total_genres: number;
  female_count: number;
  male_count: number;
  female_ratio: number;
  era_range: string;
}

export interface GenreStats {
  genre: string;
  count: number;
  percentage: number;
}

export interface GenderStats {
  gender: string;
  count: number;
  percentage: number;
}

export interface EpisodeCategoryStats {
  category: string;
  count: number;
  percentage: number;
}

export interface WorkStats {
  work_title: string;
  count: number;
  percentage: number;
}

export interface FameScore {
  id: number;
  person_name: string;
  fame_tier: number;
  fame_score: number;
  composite_score: number;
  wikipedia_ja: boolean;
  textbook: boolean;
  award_level: number;
  notoriety: boolean;
  last_updated: string;
  // Phase 1: 3軸評価カラム
  milestone_tags?: string | null;
  memorability_score?: number | null;
  empathy_score?: number | null;
  surprise_score?: number | null;
  // Phase 2: 4軸評価カラム
  generation_quality_score?: number | null;
  educational_value?: number | null;
  storytelling_quality?: number | null;
  factual_density?: number | null;
}

export interface FameRanking {
  total: number;
  rankings: FameScore[];
}

// ========================================
// Phase 3: 分析関連の型定義
// ========================================

/**
 * 軸統計情報
 */
export interface AxisStatistics {
  name: string;
  count: number;
  mean: number;
  median: number;
  stdev: number;
  min: number;
  max: number;
}

/**
 * スコアサマリー
 */
export interface ScoreSummary {
  total_episodes: number;
  axes: AxisStatistics[];
}

/**
 * 分布ビン
 */
export interface DistributionBin {
  range: string;
  bin_start: number;
  bin_end: number;
  count: number;
  percentage: number;
}

/**
 * スコア分布レスポンス
 */
export interface ScoreDistribution {
  bin_size: number;
  distributions: {
    [key: string]: DistributionBin[];
  };
}

/**
 * 相関マトリックス行
 */
export interface CorrelationRow {
  axis: string;
  記憶性スコア: number;
  共感性スコア: number;
  意外性スコア: number;
  生成品質スコア: number;
  教育的価値: number;
  ストーリー品質: number;
  事実密度: number;
}

/**
 * 相関マトリックスレスポンス
 */
export interface CorrelationMatrix {
  matrix: CorrelationRow[];
}

/**
 * トップパフォーマー
 */
export interface TopPerformer {
  person_name: string;
  age: string;
  episode: string;
  composite_score: number;
  memorability_score: number;
  empathy_score: number;
  surprise_score: number;
  generation_quality_score: number;
  educational_value: number;
  storytelling_quality: number;
  factual_density: number;
}

/**
 * トップパフォーマーレスポンス
 */
export interface TopPerformersResponse {
  total: number;
  top_n: number;
  performers: TopPerformer[];
}

// ========================================
// Phase 4: 高度な検索関連の型定義
// ========================================

/**
 * エピソード検索結果
 */
export interface EpisodeSearchResult {
  person_name: string;
  age: string;
  episode: string;
  composite_score: number;
  memorability_score: number;
  empathy_score: number;
  surprise_score: number;
  generation_quality_score: number;
  educational_value: number;
  storytelling_quality: number;
  factual_density: number;
}

/**
 * エピソード検索レスポンス
 */
export interface EpisodeSearchResponse {
  total: number;
  page: number;
  page_size: number;
  results: EpisodeSearchResult[];
}

/**
 * 検索統計レスポンス
 */
export interface SearchStatsResponse {
  total_episodes: number;
  score_ranges: {
    [key: string]: {
      min: number;
      max: number;
      mean: number;
      median: number;
    };
  };
  age_range: {
    min: number;
    max: number;
  };
}

/**
 * 高度な検索パラメータ
 */
export interface AdvancedSearchParams {
  query?: string;
  min_memorability_score?: number;
  max_memorability_score?: number;
  min_empathy_score?: number;
  max_empathy_score?: number;
  min_surprise_score?: number;
  max_surprise_score?: number;
  min_generation_quality?: number;
  max_generation_quality?: number;
  min_educational_value?: number;
  max_educational_value?: number;
  min_storytelling_quality?: number;
  max_storytelling_quality?: number;
  min_factual_density?: number;
  max_factual_density?: number;
  min_composite_score?: number;
  max_composite_score?: number;
  min_age?: number;
  max_age?: number;
  sort_by?: string;
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

/**
 * 重複情報
 */
export interface DuplicateInfo {
  person_name: string;
  age: string;
  count: number;
  row_numbers: number[];
}

/**
 * 外れ値情報
 */
export interface OutlierInfo {
  person_name: string;
  age: string;
  row_number: number;
  axis: string;
  score: number;
  mean: number;
  stdev: number;
  z_score: number;
}

/**
 * 完全性問題
 */
export interface CompletenessIssue {
  type: string;
  field?: string;
  axis?: string;
  count: number;
  percentage?: number;
  examples?: any[];
}

/**
 * 品質サマリー
 */
export interface QualitySummary {
  quality_score: number;
  total_episodes: number;
  duplicate_count: number;
  duplicate_rate: number;
  outlier_count: number;
  outlier_rate: number;
  completeness_issues: number;
  grade: string;
}

/**
 * 品質レポート
 */
export interface QualityReport {
  summary: QualitySummary;
  duplicates: {
    count: number;
    details: DuplicateInfo[];
  };
  outliers: {
    count: number;
    details: OutlierInfo[];
  };
  completeness: {
    total_episodes: number;
    issues: CompletenessIssue[];
    issues_count: number;
  };
}

// ========================================
// Phase 5: エピソード管理（CRUD）関連の型定義
// ========================================

/**
 * エピソード基本情報
 */
export interface EpisodeBase {
  person_name: string;
  age: string;
  episode_text: string;
  category?: string;
  episode_type?: string;
  person_type?: string;
  work_title?: string;
  group_name?: string;
  is_group_member?: boolean;
}

/**
 * エピソード作成リクエスト
 */
export interface EpisodeCreate extends EpisodeBase {
  memorability_score?: number;
  empathy_score?: number;
  surprise_score?: number;
  generation_quality_score?: number;
  educational_value?: number;
  storytelling_quality?: number;
  factual_density?: number;
  milestone_tags?: string;
}

/**
 * エピソード更新リクエスト
 */
export interface EpisodeUpdate {
  person_name?: string;
  age?: string;
  episode_text?: string;
  category?: string;
  episode_type?: string;
  person_type?: string;
  work_title?: string;
  group_name?: string;
  is_group_member?: boolean;
  memorability_score?: number;
  empathy_score?: number;
  surprise_score?: number;
  generation_quality_score?: number;
  educational_value?: number;
  storytelling_quality?: number;
  factual_density?: number;
  milestone_tags?: string;
  fact_check_result?: string;
}

/**
 * エピソード完全情報（読み取り用）
 */
export interface Episode {
  person_id: string;
  person_name: string;
  age: string;
  episode_text: string;
  category?: string;
  episode_type?: string;
  person_type?: string;
  work_title?: string;
  group_name?: string;
  is_group_member?: string;
  episode_count?: string;
  char_count?: string;
  fact_check_result?: string;
  quality_score?: string;
  slot?: string;
  source?: string;
  tier?: string;
  week?: string;
  generation_timestamp?: string;
  fame_tier?: string;
  wikipedia_ja?: string;
  textbook?: string;
  award_level?: string;
  notoriety?: string;
  fame_score?: string;
  composite_score?: string;
  fame_score_updated_at?: string;
  milestone_tags?: string;
  人生の節目タグ?: string;
  記憶性スコア?: string;
  共感性スコア?: string;
  意外性スコア?: string;
  生成品質スコア?: string;
  教育的価値?: string;
  ストーリー品質?: string;
  事実密度?: string;
  age_numeric?: string;
}

/**
 * エピソード一覧レスポンス
 */
export interface EpisodeList {
  total: number;
  page: number;
  page_size: number;
  episodes: Episode[];
}

/**
 * エピソード削除レスポンス
 */
export interface EpisodeDeleteResponse {
  success: boolean;
  message: string;
  deleted_person_id: string;
}
