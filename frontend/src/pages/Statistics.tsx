/**
 * Statistics ページ
 *
 * データベース統計情報の可視化
 */

import { useEffect, useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getStatsSummary, getGenreStats, getGenderStats, getEpisodeCategoryStats, getWorkStats } from '../api/client';
import type { StatsSummary, GenreStats, GenderStats, EpisodeCategoryStats, WorkStats } from '../types/character';

// グラフの色設定
const COLORS = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];

export function Statistics() {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [genreStats, setGenreStats] = useState<GenreStats[]>([]);
  const [genderStats, setGenderStats] = useState<GenderStats[]>([]);
  const [categoryStats, setCategoryStats] = useState<EpisodeCategoryStats[]>([]);
  const [workStats, setWorkStats] = useState<WorkStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatistics = async () => {
      setLoading(true);
      try {
        const [summaryData, genreData, genderData, categoryData, workData] = await Promise.all([
          getStatsSummary(),
          getGenreStats(),
          getGenderStats(),
          getEpisodeCategoryStats(),
          getWorkStats(20),
        ]);
        setSummary(summaryData);
        setGenreStats(genreData);
        setGenderStats(genderData);
        setCategoryStats(categoryData);
        setWorkStats(workData);
      } catch (error) {
        console.error('統計データの取得に失敗:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatistics();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-gray-600">読み込み中...</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-red-600">統計データの取得に失敗しました</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* ヘッダー */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            データベース統計
          </h1>
          <p className="text-gray-600">
            キャラクターデータの全体像を可視化
          </p>
        </div>

        {/* サマリーカード */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* 総キャラクター数 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">総キャラクター数</p>
                <p className="text-3xl font-bold text-blue-600 mt-2">
                  {summary.total_characters.toLocaleString()}
                </p>
              </div>
              <div className="text-blue-600 text-4xl">
                👥
              </div>
            </div>
          </div>

          {/* ジャンル数 */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">ジャンル数</p>
                <p className="text-3xl font-bold text-purple-600 mt-2">
                  {summary.total_genres}
                </p>
              </div>
              <div className="text-purple-600 text-4xl">
                📚
              </div>
            </div>
          </div>

          {/* 女性キャラクター */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">女性キャラクター</p>
                <p className="text-3xl font-bold text-pink-600 mt-2">
                  {summary.female_count.toLocaleString()}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  ({summary.female_ratio.toFixed(1)}%)
                </p>
              </div>
              <div className="text-pink-600 text-4xl">
                👩
              </div>
            </div>
          </div>

          {/* 男性キャラクター */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">男性キャラクター</p>
                <p className="text-3xl font-bold text-blue-600 mt-2">
                  {summary.male_count.toLocaleString()}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  ({(100 - summary.female_ratio).toFixed(1)}%)
                </p>
              </div>
              <div className="text-blue-600 text-4xl">
                👨
              </div>
            </div>
          </div>
        </div>

        {/* グラフセクション */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* ジャンル分布グラフ */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              ジャンル分布
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={genreStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="genre"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  interval={0}
                  style={{ fontSize: '12px' }}
                />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#3B82F6" name="キャラクター数">
                  {genreStats.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {genreStats.map((stat, index) => (
                <div key={stat.genre} className="flex items-center text-sm">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-gray-700">
                    {stat.genre}: {stat.count}件 ({stat.percentage.toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 性別分布グラフ */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              性別分布
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={genderStats as any}
                  dataKey="count"
                  nameKey="gender"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry: any) => `${entry.gender}: ${entry.percentage.toFixed(1)}%`}
                >
                  {genderStats.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              {genderStats.map((stat, index) => (
                <div key={stat.gender} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className="w-4 h-4 rounded-full mr-3"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-gray-700 font-medium">{stat.gender}</span>
                  </div>
                  <span className="text-gray-600">
                    {stat.count.toLocaleString()}件 ({stat.percentage.toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 追加グラフセクション */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          {/* エピソードカテゴリ分布グラフ */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              エピソードカテゴリ分布
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryStats as any}
                  dataKey="count"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry: any) => `${entry.category}: ${entry.percentage.toFixed(1)}%`}
                >
                  {categoryStats.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              {categoryStats.map((stat, index) => (
                <div key={stat.category} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className="w-4 h-4 rounded-full mr-3"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-gray-700 font-medium">{stat.category}</span>
                  </div>
                  <span className="text-gray-600">
                    {stat.count.toLocaleString()}件 ({stat.percentage.toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 作品別キャラクター数グラフ（TOP 20） */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              作品別キャラクター数（TOP 20）
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={workStats} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis
                  dataKey="work_title"
                  type="category"
                  width={150}
                  style={{ fontSize: '11px' }}
                  tick={{ width: 150 }}
                />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#10B981" name="キャラクター数">
                  {workStats.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 年代範囲 */}
        {summary.era_range && (
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              年代範囲
            </h2>
            <p className="text-lg text-gray-700">
              {summary.era_range}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
