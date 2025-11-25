/**
 * 高度な検索ページ
 *
 * 7軸スコア、総合スコア、年齢範囲などの複数条件で検索可能
 */

import { useState, useEffect } from 'react';
import { advancedSearch, getSearchStats } from '../api/client';
import type {
  EpisodeSearchResponse,
  SearchStatsResponse,
  AdvancedSearchParams
} from '../types/character';

// 軸の色定義
const AXIS_COLORS: Record<string, string> = {
  '記憶性スコア': '#3b82f6',
  '共感性スコア': '#10b981',
  '意外性スコア': '#f59e0b',
  '生成品質スコア': '#8b5cf6',
  '教育的価値': '#ec4899',
  'ストーリー品質': '#06b6d4',
  '事実密度': '#f97316',
  'composite_score': '#6366f1',
};

export function AdvancedSearch() {
  const [stats, setStats] = useState<SearchStatsResponse | null>(null);
  const [searchResult, setSearchResult] = useState<EpisodeSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 検索パラメータ
  const [query, setQuery] = useState('');
  const [minMemorability, setMinMemorability] = useState<number | undefined>(undefined);
  const [maxMemorability, setMaxMemorability] = useState<number | undefined>(undefined);
  const [minEmpathy, setMinEmpathy] = useState<number | undefined>(undefined);
  const [maxEmpathy, setMaxEmpathy] = useState<number | undefined>(undefined);
  const [minSurprise, setMinSurprise] = useState<number | undefined>(undefined);
  const [maxSurprise, setMaxSurprise] = useState<number | undefined>(undefined);
  const [minGenQuality, setMinGenQuality] = useState<number | undefined>(undefined);
  const [maxGenQuality, setMaxGenQuality] = useState<number | undefined>(undefined);
  const [minEduValue, setMinEduValue] = useState<number | undefined>(undefined);
  const [maxEduValue, setMaxEduValue] = useState<number | undefined>(undefined);
  const [minStoryQuality, setMinStoryQuality] = useState<number | undefined>(undefined);
  const [maxStoryQuality, setMaxStoryQuality] = useState<number | undefined>(undefined);
  const [minFactDensity, setMinFactDensity] = useState<number | undefined>(undefined);
  const [maxFactDensity, setMaxFactDensity] = useState<number | undefined>(undefined);
  const [minComposite, setMinComposite] = useState<number | undefined>(undefined);
  const [maxComposite, setMaxComposite] = useState<number | undefined>(undefined);
  const [minAge, setMinAge] = useState<number | undefined>(undefined);
  const [maxAge, setMaxAge] = useState<number | undefined>(undefined);
  const [sortBy, setSortBy] = useState('composite_score');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // 統計情報読み込み
  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await getSearchStats();
        setStats(data);
      } catch (err) {
        console.error('統計情報の読み込みに失敗:', err);
      }
    };
    loadStats();
  }, []);

  // 検索実行
  const handleSearch = async () => {
    setLoading(true);
    setError(null);

    try {
      const params: AdvancedSearchParams = {
        query: query || undefined,
        min_memorability_score: minMemorability,
        max_memorability_score: maxMemorability,
        min_empathy_score: minEmpathy,
        max_empathy_score: maxEmpathy,
        min_surprise_score: minSurprise,
        max_surprise_score: maxSurprise,
        min_generation_quality: minGenQuality,
        max_generation_quality: maxGenQuality,
        min_educational_value: minEduValue,
        max_educational_value: maxEduValue,
        min_storytelling_quality: minStoryQuality,
        max_storytelling_quality: maxStoryQuality,
        min_factual_density: minFactDensity,
        max_factual_density: maxFactDensity,
        min_composite_score: minComposite,
        max_composite_score: maxComposite,
        min_age: minAge,
        max_age: maxAge,
        sort_by: sortBy,
        order: order,
        page: page,
        page_size: pageSize,
      };

      const result = await advancedSearch(params);
      setSearchResult(result);
    } catch (err: any) {
      setError(err.message || '検索に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // リセット
  const handleReset = () => {
    setQuery('');
    setMinMemorability(undefined);
    setMaxMemorability(undefined);
    setMinEmpathy(undefined);
    setMaxEmpathy(undefined);
    setMinSurprise(undefined);
    setMaxSurprise(undefined);
    setMinGenQuality(undefined);
    setMaxGenQuality(undefined);
    setMinEduValue(undefined);
    setMaxEduValue(undefined);
    setMinStoryQuality(undefined);
    setMaxStoryQuality(undefined);
    setMinFactDensity(undefined);
    setMaxFactDensity(undefined);
    setMinComposite(undefined);
    setMaxComposite(undefined);
    setMinAge(undefined);
    setMaxAge(undefined);
    setSortBy('composite_score');
    setOrder('desc');
    setPage(1);
    setSearchResult(null);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🔍 高度な検索
        </h1>
        <p className="text-gray-600">
          7軸スコア、総合スコア、年齢範囲などの複数条件でエピソードを検索
        </p>
        {stats && (
          <p className="text-sm text-gray-500 mt-2">
            検索対象: {stats.total_episodes.toLocaleString()}エピソード
          </p>
        )}
      </div>

      {/* 検索フォーム */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">検索条件</h2>

        {/* テキスト検索 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            人物名・エピソード検索
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="例: 羽生結弦, オリンピック"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* スコアレンジフィルター */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* 記憶性スコア */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['記憶性スコア'] }}>
              記憶性スコア
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minMemorability ?? ''}
                onChange={(e) => setMinMemorability(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxMemorability ?? ''}
                onChange={(e) => setMaxMemorability(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* 共感性スコア */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['共感性スコア'] }}>
              共感性スコア
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minEmpathy ?? ''}
                onChange={(e) => setMinEmpathy(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxEmpathy ?? ''}
                onChange={(e) => setMaxEmpathy(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* 意外性スコア */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['意外性スコア'] }}>
              意外性スコア
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minSurprise ?? ''}
                onChange={(e) => setMinSurprise(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxSurprise ?? ''}
                onChange={(e) => setMaxSurprise(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* 生成品質スコア */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['生成品質スコア'] }}>
              生成品質スコア
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minGenQuality ?? ''}
                onChange={(e) => setMinGenQuality(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxGenQuality ?? ''}
                onChange={(e) => setMaxGenQuality(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* 教育的価値 */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['教育的価値'] }}>
              教育的価値
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minEduValue ?? ''}
                onChange={(e) => setMinEduValue(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxEduValue ?? ''}
                onChange={(e) => setMaxEduValue(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* ストーリー品質 */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['ストーリー品質'] }}>
              ストーリー品質
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minStoryQuality ?? ''}
                onChange={(e) => setMinStoryQuality(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxStoryQuality ?? ''}
                onChange={(e) => setMaxStoryQuality(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* 事実密度 */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['事実密度'] }}>
              事実密度
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minFactDensity ?? ''}
                onChange={(e) => setMinFactDensity(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxFactDensity ?? ''}
                onChange={(e) => setMaxFactDensity(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          {/* 総合スコア */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: AXIS_COLORS['composite_score'] }}>
              総合スコア（7軸平均）
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={minComposite ?? ''}
                onChange={(e) => setMinComposite(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最小"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
              <span>〜</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={maxComposite ?? ''}
                onChange={(e) => setMaxComposite(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="最大"
                className="w-24 px-3 py-2 border border-gray-300 rounded"
              />
            </div>
          </div>
        </div>

        {/* 年齢範囲 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            年齢範囲
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="150"
              value={minAge ?? ''}
              onChange={(e) => setMinAge(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="最小年齢"
              className="w-32 px-3 py-2 border border-gray-300 rounded"
            />
            <span>〜</span>
            <input
              type="number"
              min="0"
              max="150"
              value={maxAge ?? ''}
              onChange={(e) => setMaxAge(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="最大年齢"
              className="w-32 px-3 py-2 border border-gray-300 rounded"
            />
          </div>
        </div>

        {/* ソート設定 */}
        <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ソート基準
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="composite_score">総合スコア</option>
              <option value="記憶性スコア">記憶性スコア</option>
              <option value="共感性スコア">共感性スコア</option>
              <option value="意外性スコア">意外性スコア</option>
              <option value="生成品質スコア">生成品質スコア</option>
              <option value="教育的価値">教育的価値</option>
              <option value="ストーリー品質">ストーリー品質</option>
              <option value="事実密度">事実密度</option>
              <option value="age_numeric">年齢</option>
              <option value="person_name">人物名</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              並び順
            </label>
            <select
              value={order}
              onChange={(e) => setOrder(e.target.value as 'asc' | 'desc')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="desc">降順（高い順）</option>
              <option value="asc">昇順（低い順）</option>
            </select>
          </div>
        </div>

        {/* 検索ボタン */}
        <div className="flex gap-4">
          <button
            onClick={handleSearch}
            disabled={loading}
            className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '検索中...' : '🔍 検索実行'}
          </button>
          <button
            onClick={handleReset}
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
          >
            🔄 リセット
          </button>
        </div>
      </div>

      {/* エラー表示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-6 py-4 rounded-lg mb-6">
          ❌ {error}
        </div>
      )}

      {/* 検索結果 */}
      {searchResult && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold">
              検索結果: {searchResult.total.toLocaleString()}件
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              ページ {searchResult.page} / {Math.ceil(searchResult.total / searchResult.page_size)}
            </p>
          </div>

          {searchResult.results.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              条件に一致するエピソードが見つかりませんでした
            </div>
          ) : (
            <>
              {/* テーブル表示 */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">人物名</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">年齢</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">エピソード</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['composite_score'] }}>総合</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['記憶性スコア'] }}>記憶</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['共感性スコア'] }}>共感</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['意外性スコア'] }}>意外</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['生成品質スコア'] }}>生成</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['教育的価値'] }}>教育</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['ストーリー品質'] }}>物語</th>
                      <th className="px-4 py-3 text-center text-sm font-medium" style={{ color: AXIS_COLORS['事実密度'] }}>事実</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {searchResult.results.map((result, index) => (
                      <tr key={`${result.person_name}-${index}`} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{result.person_name}</td>
                        <td className="px-4 py-3 text-gray-700">{result.age}</td>
                        <td className="px-4 py-3 text-gray-700 max-w-md truncate" title={result.episode}>
                          {result.episode}
                        </td>
                        <td className="px-4 py-3 text-center font-semibold" style={{ color: AXIS_COLORS['composite_score'] }}>
                          {result.composite_score.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-center">{result.memorability_score.toFixed(1)}</td>
                        <td className="px-4 py-3 text-center">{result.empathy_score.toFixed(1)}</td>
                        <td className="px-4 py-3 text-center">{result.surprise_score.toFixed(1)}</td>
                        <td className="px-4 py-3 text-center">{result.generation_quality_score.toFixed(1)}</td>
                        <td className="px-4 py-3 text-center">{result.educational_value.toFixed(1)}</td>
                        <td className="px-4 py-3 text-center">{result.storytelling_quality.toFixed(1)}</td>
                        <td className="px-4 py-3 text-center">{result.factual_density.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* ページネーション */}
              {searchResult.total > pageSize && (
                <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                  <button
                    onClick={() => {
                      setPage(Math.max(1, page - 1));
                      handleSearch();
                    }}
                    disabled={page === 1}
                    className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    前へ
                  </button>
                  <span className="text-sm text-gray-600">
                    {((page - 1) * pageSize + 1).toLocaleString()} - {Math.min(page * pageSize, searchResult.total).toLocaleString()} / {searchResult.total.toLocaleString()}件
                  </span>
                  <button
                    onClick={() => {
                      setPage(page + 1);
                      handleSearch();
                    }}
                    disabled={page >= Math.ceil(searchResult.total / pageSize)}
                    className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    次へ
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
