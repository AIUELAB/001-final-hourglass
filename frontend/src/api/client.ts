/**
 * API クライアント
 *
 * FastAPIバックエンドとの通信を管理
 */

import axios from 'axios';
import type { Character, CharacterList, StatsSummary, GenreStats, GenderStats, EpisodeCategoryStats, WorkStats } from '../types/character';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * キャラクター一覧取得
 */
export const getCharacters = async (page: number = 1, pageSize: number = 20): Promise<CharacterList> => {
  const response = await apiClient.get<CharacterList>('/characters', {
    params: { page, page_size: pageSize },
  });
  return response.data;
};

/**
 * キャラクター詳細取得
 */
export const getCharacterById = async (id: number): Promise<Character> => {
  const response = await apiClient.get<Character>(`/characters/${id}`);
  return response.data;
};

/**
 * キャラクター検索
 */
export const searchCharacters = async (query: string): Promise<Character[]> => {
  const response = await apiClient.get<Character[]>('/characters/search/', {
    params: { q: query },
  });
  return response.data;
};

/**
 * キャラクターフィルター
 */
export const filterCharacters = async (
  genre?: string,
  gender?: string
): Promise<Character[]> => {
  const response = await apiClient.get<Character[]>('/characters/filter/', {
    params: { genre, gender },
  });
  return response.data;
};

/**
 * 統計サマリー取得
 */
export const getStatsSummary = async (): Promise<StatsSummary> => {
  const response = await apiClient.get<StatsSummary>('/stats/summary');
  return response.data;
};

/**
 * ジャンル統計取得
 */
export const getGenreStats = async (): Promise<GenreStats[]> => {
  const response = await apiClient.get<GenreStats[]>('/stats/genres');
  return response.data;
};

/**
 * 性別統計取得
 */
export const getGenderStats = async (): Promise<GenderStats[]> => {
  const response = await apiClient.get<GenderStats[]>('/stats/gender');
  return response.data;
};

/**
 * エピソードカテゴリ統計取得
 */
export const getEpisodeCategoryStats = async (): Promise<EpisodeCategoryStats[]> => {
  const response = await apiClient.get<EpisodeCategoryStats[]>('/stats/episode-categories');
  return response.data;
};

/**
 * 作品統計取得（上位N件）
 */
export const getWorkStats = async (limit: number = 20): Promise<WorkStats[]> => {
  const response = await apiClient.get<WorkStats[]>('/stats/works', {
    params: { limit },
  });
  return response.data;
};

/**
 * ヘルスチェック
 */
export const healthCheck = async (): Promise<{ status: string; message: string }> => {
  const response = await apiClient.get('/health');
  return response.data;
};
