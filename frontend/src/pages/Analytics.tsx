/**
 * Analytics ページ - Phase 3: 7軸スコア統合分析
 *
 * 7軸評価スコアの統計分析・可視化ダッシュボード
 */

import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  getAnalyticsSummary,
  getScoreDistribution,
  getCorrelationMatrix,
  getTopPerformers,
} from '../api/client';
import type {
  ScoreSummary,
  ScoreDistribution,
  CorrelationMatrix,
  TopPerformersResponse,
  AxisStatistics,
} from '../types/character';

// グラフの色設定（7軸用）
const AXIS_COLORS: { [key: string]: string } = {
  '記憶性スコア': '#3B82F6',
  '共感性スコア': '#EF4444',
  '意外性スコア': '#10B981',
  '生成品質スコア': '#F59E0B',
  '教育的価値': '#8B5CF6',
  'ストーリー品質': '#EC4899',
  '事実密度': '#14B8A6',
};

// 相関係数のヒートマップ色
const getCorrelationColor = (value: number): string => {
  if (value >= 0.7) return '#10B981'; // Strong positive
  if (value >= 0.4) return '#3B82F6'; // Moderate positive
  if (value >= 0.1) return '#93C5FD'; // Weak positive
  if (value >= -0.1) return '#E5E7EB'; // Near zero
  if (value >= -0.4) return '#FCA5A5'; // Weak negative
  if (value >= -0.7) return '#EF4444'; // Moderate negative
  return '#991B1B'; // Strong negative
};

export function Analytics() {
  const [summary, setSummary] = useState<ScoreSummary | null>(null);
  const [distribution, setDistribution] = useState<ScoreDistribution | null>(null);
  const [correlation, setCorrelation] = useState<CorrelationMatrix | null>(null);
  const [topPerformers, setTopPerformers] = useState<TopPerformersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAxis, setSelectedAxis] = useState<string>('記憶性スコア');

  useEffect(() => {
    const fetchAnalytics = async () => {
      setLoading(true);
      try {
        const [summaryData, distributionData, correlationData, performersData] = await Promise.all([
          getAnalyticsSummary(),
          getScoreDistribution(0.5),
          getCorrelationMatrix(),
          getTopPerformers(50),
        ]);
        setSummary(summaryData);
        setDistribution(distributionData);
        setCorrelation(correlationData);
        setTopPerformers(performersData);
      } catch (error) {
        console.error('分析データの取得に失敗:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-gray-600">読み込み中...</div>
      </div>
    );
  }

  if (!summary || !distribution || !correlation || !topPerformers) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-red-600">分析データの取得に失敗しました</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* ヘッダー */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            7軸スコア統合分析
          </h1>
          <p className="text-gray-600">
            Phase 1（記憶性・共感性・意外性）+ Phase 2（生成品質・教育的価値・ストーリー品質・事実密度）の統合分析
          </p>
          <p className="text-sm text-gray-500 mt-2">
            総エピソード数: {summary.total_episodes.toLocaleString()}件
          </p>
        </div>

        {/* 7軸サマリーカード */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">7軸評価サマリー</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {summary.axes.map((axis: AxisStatistics) => (
              <div
                key={axis.name}
                className="bg-white rounded-lg shadow p-4 border-l-4"
                style={{ borderColor: AXIS_COLORS[axis.name] || '#6B7280' }}
              >
                <h3 className="text-sm font-medium text-gray-600 mb-2">{axis.name}</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">平均:</span>
                    <span className="font-semibold" style={{ color: AXIS_COLORS[axis.name] }}>
                      {axis.mean.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">中央値:</span>
                    <span className="font-medium">{axis.median.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">標準偏差:</span>
                    <span className="font-medium">{axis.stdev.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>範囲:</span>
                    <span>
                      {axis.min.toFixed(1)} - {axis.max.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* スコア分布ヒストグラム */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">スコア分布</h2>
          <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 mr-3">軸を選択:</label>
            <select
              value={selectedAxis}
              onChange={(e) => setSelectedAxis(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              {Object.keys(distribution.distributions).map((axisName) => (
                <option key={axisName} value={axisName}>
                  {axisName}
                </option>
              ))}
            </select>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={distribution.distributions[selectedAxis] || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="range"
                angle={-45}
                textAnchor="end"
                height={80}
                style={{ fontSize: '12px' }}
              />
              <YAxis label={{ value: '件数', angle: -90, position: 'insideLeft' }} />
              <Tooltip
                formatter={(value: any) => [`${value}件`, '件数']}
                labelFormatter={(label: string) => `スコア範囲: ${label}`}
              />
              <Legend />
              <Bar dataKey="count" fill={AXIS_COLORS[selectedAxis] || '#6B7280'} name="エピソード数">
                {(distribution.distributions[selectedAxis] || []).map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={AXIS_COLORS[selectedAxis] || '#6B7280'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 text-sm text-gray-600">
            <p>ビンサイズ: {distribution.bin_size} | 選択軸: {selectedAxis}</p>
          </div>
        </div>

        {/* 相関マトリックスヒートマップ */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">軸間相関マトリックス</h2>
          <p className="text-sm text-gray-600 mb-4">
            各軸間のPearson相関係数（-1〜1）。正の値は正の相関、負の値は負の相関を示す。
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse">
              <thead>
                <tr>
                  <th className="border border-gray-300 px-3 py-2 bg-gray-50 text-xs font-medium text-gray-700">
                    軸
                  </th>
                  {summary.axes.map((axis: AxisStatistics) => (
                    <th
                      key={axis.name}
                      className="border border-gray-300 px-2 py-2 bg-gray-50 text-xs font-medium text-gray-700"
                      style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
                    >
                      {axis.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {correlation.matrix.map((row) => (
                  <tr key={row.axis}>
                    <td className="border border-gray-300 px-3 py-2 bg-gray-50 text-xs font-medium text-gray-700">
                      {row.axis}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.記憶性スコア) }}
                    >
                      {row.記憶性スコア.toFixed(2)}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.共感性スコア) }}
                    >
                      {row.共感性スコア.toFixed(2)}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.意外性スコア) }}
                    >
                      {row.意外性スコア.toFixed(2)}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.生成品質スコア) }}
                    >
                      {row.生成品質スコア.toFixed(2)}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.教育的価値) }}
                    >
                      {row.教育的価値.toFixed(2)}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.ストーリー品質) }}
                    >
                      {row.ストーリー品質.toFixed(2)}
                    </td>
                    <td
                      className="border border-gray-300 px-2 py-2 text-center text-xs font-medium"
                      style={{ backgroundColor: getCorrelationColor(row.事実密度) }}
                    >
                      {row.事実密度.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center gap-4 text-xs">
            <span className="text-gray-600">相関強度:</span>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4" style={{ backgroundColor: '#10B981' }}></div>
              <span>強正 (≥0.7)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4" style={{ backgroundColor: '#3B82F6' }}></div>
              <span>中正 (0.4-0.7)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4" style={{ backgroundColor: '#E5E7EB' }}></div>
              <span>弱・ゼロ</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4" style={{ backgroundColor: '#EF4444' }}></div>
              <span>中負 (-0.7--0.4)</span>
            </div>
          </div>
        </div>

        {/* トップパフォーマー一覧 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">総合スコア上位エピソード</h2>
          <p className="text-sm text-gray-600 mb-4">
            7軸スコアの平均値によるランキング（Top {topPerformers.top_n}）
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    順位
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    人物名
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    年齢
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    総合スコア
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    記憶性
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    共感性
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    意外性
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    生成品質
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    教育価値
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    ストーリー
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    事実密度
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {topPerformers.performers.map((performer, index) => (
                  <tr key={`${performer.person_name}-${index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      {index + 1}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {performer.person_name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {performer.age}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-bold text-blue-600">
                      {performer.composite_score.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.memorability_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.empathy_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.surprise_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.generation_quality_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.educational_value.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.storytelling_quality.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {performer.factual_density.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
