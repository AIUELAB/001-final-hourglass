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
}

export interface FameRanking {
  total: number;
  rankings: FameScore[];
}
