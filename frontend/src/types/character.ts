/**
 * キャラクター型定義
 */

export interface Character {
  id: number;
  character_name: string;
  work_title: string;
  genre: string;
  episode_category: string;
  episode_text: string;
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
  era_range?: string;
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
