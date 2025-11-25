/**
 * API クライアント
 *
 * FastAPIバックエンドとの通信を管理
 */

import axios from 'axios';
import type {
  Character,
  CharacterList,
  StatsSummary,
  GenreStats,
  GenderStats,
  EpisodeCategoryStats,
  WorkStats,
  FameRanking,
  // Phase 3: 分析関連の型
  ScoreSummary,
  ScoreDistribution,
  CorrelationMatrix,
  TopPerformersResponse,
  // Phase 4: 高度な検索・品質管理関連の型
  EpisodeSearchResponse,
  SearchStatsResponse,
  AdvancedSearchParams,
  QualityReport,
  // Phase 5: エピソード管理（CRUD）関連の型
  Episode,
  EpisodeList,
  EpisodeCreate,
  EpisodeUpdate,
  EpisodeDeleteResponse
} from '../types/character';

// ========================================
// Phase 5: 認証関連の型定義
// ========================================

/**
 * ログインリクエスト
 */
export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * ログインレスポンス
 */
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

/**
 * ユーザー情報
 */
export interface UserInfo {
  username: string;
  email: string;
  full_name: string;
  role: 'admin' | 'editor' | 'viewer';
  disabled: boolean;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// JWTトークンを自動的にリクエストに付与
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

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

/**
 * 有名度ランキング取得
 */
export const getFameRanking = async (
  limit: number = 100,
  orderBy: 'fame_score' | 'composite_score' = 'fame_score'
): Promise<FameRanking> => {
  const response = await apiClient.get<FameRanking>('/stats/fame-ranking', {
    params: { limit, order_by: orderBy },
  });
  return response.data;
};

// ========================================
// Phase 3: 分析API
// ========================================

/**
 * 7軸スコアサマリー取得
 */
export const getAnalyticsSummary = async (): Promise<ScoreSummary> => {
  const response = await apiClient.get<ScoreSummary>('/analytics/summary');
  return response.data;
};

/**
 * スコア分布取得
 */
export const getScoreDistribution = async (binSize: number = 0.5): Promise<ScoreDistribution> => {
  const response = await apiClient.get<ScoreDistribution>('/analytics/distribution', {
    params: { bin_size: binSize },
  });
  return response.data;
};

/**
 * 相関マトリックス取得
 */
export const getCorrelationMatrix = async (): Promise<CorrelationMatrix> => {
  const response = await apiClient.get<CorrelationMatrix>('/analytics/correlation');
  return response.data;
};

/**
 * トップパフォーマー取得
 */
export const getTopPerformers = async (topN: number = 50): Promise<TopPerformersResponse> => {
  const response = await apiClient.get<TopPerformersResponse>('/analytics/top-performers', {
    params: { top_n: topN },
  });
  return response.data;
};

// ========================================
// Phase 4: 高度な検索API
// ========================================

/**
 * 高度な検索実行
 */
export const advancedSearch = async (params: AdvancedSearchParams): Promise<EpisodeSearchResponse> => {
  const response = await apiClient.get<EpisodeSearchResponse>('/search/advanced', {
    params: params,
  });
  return response.data;
};

/**
 * 検索統計情報取得
 */
export const getSearchStats = async (): Promise<SearchStatsResponse> => {
  const response = await apiClient.get<SearchStatsResponse>('/search/stats');
  return response.data;
};

// ========================================
// Phase 4: データ品質管理API
// ========================================

/**
 * データ品質レポート取得
 */
export const getQualityReport = async (): Promise<QualityReport> => {
  const response = await apiClient.get<QualityReport>('/quality/report');
  return response.data;
};

// ========================================
// Phase 4: データエクスポートAPI
// ========================================

/**
 * CSVエクスポート（ダウンロード）
 */
export const exportCSV = async (minCompositeScore?: number): Promise<void> => {
  const params = minCompositeScore !== undefined ? { min_composite_score: minCompositeScore } : {};
  const response = await apiClient.get('/export/csv', {
    params,
    responseType: 'blob',
  });

  // Blobからダウンロードリンクを作成
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'episodes_export.csv');
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * JSONエクスポート（ダウンロード）
 */
export const exportJSON = async (minCompositeScore?: number): Promise<void> => {
  const params = minCompositeScore !== undefined ? { min_composite_score: minCompositeScore } : {};
  const response = await apiClient.get('/export/json', {
    params,
    responseType: 'blob',
  });

  // Blobからダウンロードリンクを作成
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'episodes_export.json');
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ========================================
// Phase 5: エピソード管理（CRUD）API
// ========================================

/**
 * エピソード一覧取得
 */
export const getEpisodes = async (
  page: number = 1,
  pageSize: number = 20,
  personType?: string
): Promise<EpisodeList> => {
  const params: any = { page, page_size: pageSize };
  if (personType) {
    params.person_type = personType;
  }
  const response = await apiClient.get<EpisodeList>('/episodes', { params });
  return response.data;
};

/**
 * エピソード検索
 */
export const searchEpisodes = async (
  query: string,
  page: number = 1,
  pageSize: number = 20
): Promise<EpisodeList> => {
  const response = await apiClient.get<EpisodeList>('/episodes/search', {
    params: { q: query, page, page_size: pageSize },
  });
  return response.data;
};

/**
 * エピソード詳細取得
 */
export const getEpisodeById = async (personId: string): Promise<Episode> => {
  const response = await apiClient.get<Episode>(`/episodes/${personId}`);
  return response.data;
};

/**
 * エピソード作成
 */
export const createEpisode = async (episodeData: EpisodeCreate): Promise<Episode> => {
  const response = await apiClient.post<Episode>('/episodes', episodeData);
  return response.data;
};

/**
 * エピソード更新
 */
export const updateEpisode = async (
  personId: string,
  episodeData: EpisodeUpdate
): Promise<Episode> => {
  const response = await apiClient.put<Episode>(`/episodes/${personId}`, episodeData);
  return response.data;
};

/**
 * エピソード削除
 */
export const deleteEpisode = async (personId: string): Promise<EpisodeDeleteResponse> => {
  const response = await apiClient.delete<EpisodeDeleteResponse>(`/episodes/${personId}`);
  return response.data;
};

// ========================================
// Phase 5: 認証API
// ========================================

/**
 * ログイン
 *
 * @param username ユーザー名
 * @param password パスワード
 * @returns ログインレスポンス（JWTトークン）
 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  // OAuth2PasswordRequestFormの形式に合わせる
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await apiClient.post<LoginResponse>('/auth/token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  // トークンをlocalStorageに保存
  if (response.data.access_token) {
    localStorage.setItem('auth_token', response.data.access_token);
  }

  return response.data;
};

/**
 * 現在のユーザー情報取得
 *
 * @returns ユーザー情報
 */
export const getCurrentUser = async (): Promise<UserInfo> => {
  const response = await apiClient.get<UserInfo>('/auth/me');
  return response.data;
};

/**
 * ログアウト
 *
 * localStorageからトークンを削除
 */
export const logout = (): void => {
  localStorage.removeItem('auth_token');
};

/**
 * 認証トークンを設定
 *
 * @param token JWTトークン（nullの場合は削除）
 */
export const setAuthToken = (token: string | null): void => {
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
};

/**
 * 認証トークンを取得
 *
 * @returns 保存されているJWTトークン
 */
export const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token');
};
