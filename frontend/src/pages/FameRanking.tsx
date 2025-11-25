/**
 * FameRanking ページ
 *
 * 有名度ランキング表示
 */

import { useEffect, useState } from 'react';
import { getFameRanking } from '../api/client';
import type { FameScore } from '../types/character';

type SortBy = 'fame_score' | 'composite_score';

export function FameRanking() {
  const [rankings, setRankings] = useState<FameScore[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<SortBy>('fame_score');
  const [limit, setLimit] = useState(100);

  const fetchRankings = async () => {
    setLoading(true);
    try {
      const data = await getFameRanking(limit, sortBy);
      setRankings(data.rankings);
      setTotal(data.total);
    } catch (error) {
      console.error('ランキング取得エラー:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRankings();
  }, [sortBy, limit]);

  const handleSortChange = (newSort: SortBy) => {
    setSortBy(newSort);
  };

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit);
  };

  // 有名度ティアのラベル
  const getTierLabel = (tier: number) => {
    switch (tier) {
      case 5: return '⭐⭐⭐⭐⭐ 国民的';
      case 4: return '⭐⭐⭐⭐ 非常に高い';
      case 3: return '⭐⭐⭐ 高い';
      case 2: return '⭐⭐ 中程度';
      case 1: return '⭐ 低い';
      default: return '未評価';
    }
  };

  // スコアの色分け
  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-purple-600 font-bold';
    if (score >= 80) return 'text-blue-600 font-bold';
    if (score >= 70) return 'text-green-600 font-semibold';
    if (score >= 60) return 'text-yellow-600';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-gray-600">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          🏆 有名度ランキング
        </h1>
        <p className="text-gray-600">
          一般的な日本人（10-50歳）にとっての有名度スコア順 - 全{total.toLocaleString()}件
        </p>
      </div>

      {/* コントロールパネル */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          {/* ソート選択 */}
          <div className="flex items-center gap-2">
            <label className="text-gray-700 font-medium">並び順:</label>
            <div className="flex gap-2">
              <button
                onClick={() => handleSortChange('fame_score')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  sortBy === 'fame_score'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                🌟 有名度スコア順
              </button>
              <button
                onClick={() => handleSortChange('composite_score')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  sortBy === 'composite_score'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                💎 総合スコア順
              </button>
            </div>
          </div>

          {/* 表示件数選択 */}
          <div className="flex items-center gap-2">
            <label className="text-gray-700 font-medium">表示件数:</label>
            <select
              value={limit}
              onChange={(e) => handleLimitChange(Number(e.target.value))}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            >
              <option value={50}>上位50件</option>
              <option value={100}>上位100件</option>
              <option value={200}>上位200件</option>
              <option value={500}>上位500件</option>
            </select>
          </div>
        </div>

        {/* スコア説明 */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            <span className="font-medium">📊 スコア算出:</span>
            有名度スコア = 基礎評価(60%) + データソース(25%) + 現代トピック(15%) |
            総合スコア = 有名度(60%) + 品質(40%)
          </p>
        </div>
      </div>

      {/* ランキングテーブル */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold">順位</th>
                <th className="px-6 py-4 text-left text-sm font-semibold">人物名</th>
                <th className="px-6 py-4 text-center text-sm font-semibold">有名度ティア</th>
                <th className="px-6 py-4 text-center text-sm font-semibold">有名度スコア</th>
                <th className="px-6 py-4 text-center text-sm font-semibold">総合スコア</th>
                <th className="px-6 py-4 text-center text-sm font-semibold">データソース</th>
                <th className="px-6 py-4 text-center text-sm font-semibold">受賞レベル</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {rankings.map((person, index) => (
                <tr
                  key={person.id}
                  className={`hover:bg-gray-50 transition-colors ${
                    person.notoriety ? 'bg-yellow-50' : ''
                  }`}
                >
                  {/* 順位 */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold text-gray-700">
                        {index + 1}
                      </span>
                      {index === 0 && <span className="text-2xl">🥇</span>}
                      {index === 1 && <span className="text-2xl">🥈</span>}
                      {index === 2 && <span className="text-2xl">🥉</span>}
                    </div>
                  </td>

                  {/* 人物名 */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">
                        {person.person_name}
                      </span>
                      {person.notoriety && (
                        <span className="text-xl" title="悪名での高知名度">
                          ⚠️
                        </span>
                      )}
                    </div>
                    {person.notoriety && (
                      <div className="text-xs text-yellow-700 mt-1">
                        教訓的価値のため掲載
                      </div>
                    )}
                  </td>

                  {/* 有名度ティア */}
                  <td className="px-6 py-4 text-center">
                    <span className="text-sm text-gray-700">
                      {getTierLabel(person.fame_tier)}
                    </span>
                  </td>

                  {/* 有名度スコア */}
                  <td className="px-6 py-4 text-center">
                    <span className={`text-2xl ${getScoreColor(person.fame_score)}`}>
                      {person.fame_score}
                    </span>
                  </td>

                  {/* 総合スコア */}
                  <td className="px-6 py-4 text-center">
                    <span className={`text-xl ${getScoreColor(person.composite_score)}`}>
                      {person.composite_score}
                    </span>
                  </td>

                  {/* データソース */}
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1 justify-center">
                      {person.wikipedia_ja && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded" title="Wikipedia日本語版に掲載">
                          📖 Wiki
                        </span>
                      )}
                      {person.textbook && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded" title="教科書に掲載">
                          📚 教科書
                        </span>
                      )}
                    </div>
                  </td>

                  {/* 受賞レベル */}
                  <td className="px-6 py-4 text-center">
                    {person.award_level > 0 ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="text-yellow-500">🏅</span>
                        <span className="font-semibold text-gray-700">
                          Lv.{person.award_level}
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* フッター情報 */}
      <div className="mt-6 text-sm text-gray-600 bg-blue-50 rounded-lg p-4">
        <p className="font-medium mb-2">📌 受賞レベルについて:</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>Lv.3: ノーベル賞級（国際的な最高峰賞）</li>
          <li>Lv.2: 文化勲章、国民栄誉賞級（国家レベルの栄誉）</li>
          <li>Lv.1: 業界トップ賞（分野で権威ある賞）</li>
          <li>Lv.0: 該当なし</li>
        </ul>
      </div>
    </div>
  );
}
