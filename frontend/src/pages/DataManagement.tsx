/**
 * データ管理ダッシュボードページ
 *
 * データ品質レポート表示とエクスポート機能を提供
 */

import { useState, useEffect } from 'react';
import {
  getQualityReport,
  exportCSV,
  exportJSON,
  getEpisodes,
  searchEpisodes,
  createEpisode,
  updateEpisode,
  deleteEpisode
} from '../api/client';
import type {
  QualityReport,
  Episode,
  EpisodeList as EpisodeListType,
  EpisodeCreate,
  EpisodeUpdate
} from '../types/character';
import { SevenAxisScore } from '../components/SevenAxisScore';

export function DataManagement() {
  // 品質レポート状態
  const [report, setReport] = useState<QualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportFilter, setExportFilter] = useState<string>('all');

  // エピソード管理状態
  const [activeTab, setActiveTab] = useState<'quality' | 'episodes'>('quality');
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [episodesTotal, setEpisodesTotal] = useState(0);
  const [episodesPage, setEpisodesPage] = useState(1);
  const [episodesPageSize] = useState(10);
  const [episodesLoading, setEpisodesLoading] = useState(false);
  const [episodeSearchQuery, setEpisodeSearchQuery] = useState('');
  const [showEpisodeModal, setShowEpisodeModal] = useState(false);
  const [editingEpisode, setEditingEpisode] = useState<Episode | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingEpisodeId, setDeletingEpisodeId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    loadQualityReport();
  }, []);

  useEffect(() => {
    if (activeTab === 'episodes') {
      loadEpisodes();
    }
  }, [activeTab, episodesPage]);

  const loadQualityReport = async () => {
    try {
      setLoading(true);
      const data = await getQualityReport();
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'データ品質レポートの読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const loadEpisodes = async () => {
    try {
      setEpisodesLoading(true);
      let data: EpisodeListType;

      if (episodeSearchQuery.trim()) {
        data = await searchEpisodes(episodeSearchQuery, episodesPage, episodesPageSize);
      } else {
        data = await getEpisodes(episodesPage, episodesPageSize);
      }

      setEpisodes(data.episodes);
      setEpisodesTotal(data.total);
    } catch (err: any) {
      alert(`エピソードの読み込みに失敗しました: ${err.message}`);
    } finally {
      setEpisodesLoading(false);
    }
  };

  const handleSort = (field: string) => {
    if (sortField === field) {
      // 同じフィールドをクリックした場合は方向を反転
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // 新しいフィールドの場合は降順から開始
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSortedEpisodes = () => {
    if (!sortField) return episodes;

    return [...episodes].sort((a, b) => {
      if (sortField === 'composite_score') {
        const valA = a.composite_score ? parseFloat(a.composite_score) : 0;
        const valB = b.composite_score ? parseFloat(b.composite_score) : 0;
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }

      if (sortField === 'work_title') {
        const valA = (a.work_title || '').toLowerCase();
        const valB = (b.work_title || '').toLowerCase();
        if (sortDirection === 'asc') {
          return valA.localeCompare(valB, 'ja');
        } else {
          return valB.localeCompare(valA, 'ja');
        }
      }

      return 0;
    });
  };

  const handleSearchEpisodes = async () => {
    setEpisodesPage(1);
    loadEpisodes();
  };

  const handleCreateEpisode = () => {
    setEditingEpisode(null);
    setShowEpisodeModal(true);
  };

  const handleEditEpisode = (episode: Episode) => {
    setEditingEpisode(episode);
    setShowEpisodeModal(true);
  };

  const handleSaveEpisode = async (episodeData: EpisodeCreate | EpisodeUpdate) => {
    try {
      if (editingEpisode) {
        // 更新
        await updateEpisode(editingEpisode.person_id, episodeData as EpisodeUpdate);
        alert('エピソードを更新しました');
      } else {
        // 新規作成
        await createEpisode(episodeData as EpisodeCreate);
        alert('エピソードを作成しました');
      }
      setShowEpisodeModal(false);
      setEditingEpisode(null);
      loadEpisodes();
    } catch (err: any) {
      alert(`エピソードの保存に失敗しました: ${err.message}`);
    }
  };

  const handleDeleteClick = (personId: string) => {
    setDeletingEpisodeId(personId);
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = async () => {
    if (!deletingEpisodeId) return;

    try {
      await deleteEpisode(deletingEpisodeId);
      alert('エピソードを削除しました');
      setShowDeleteConfirm(false);
      setDeletingEpisodeId(null);
      loadEpisodes();
    } catch (err: any) {
      alert(`エピソードの削除に失敗しました: ${err.message}`);
    }
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      setExporting(true);
      const minScore = exportFilter === 'high' ? 9.0 : exportFilter === 'medium' ? 7.0 : undefined;

      if (format === 'csv') {
        await exportCSV(minScore);
      } else {
        await exportJSON(minScore);
      }

      alert(`${format.toUpperCase()}形式でエクスポートしました`);
    } catch (err: any) {
      alert(`エクスポートに失敗しました: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const getGradeColor = (grade: string): string => {
    switch (grade) {
      case 'A+':
      case 'A':
        return 'text-green-600';
      case 'B':
        return 'text-blue-600';
      case 'C':
        return 'text-yellow-600';
      case 'D':
        return 'text-orange-600';
      default:
        return 'text-red-600';
    }
  };

  const getGradeBg = (grade: string): string => {
    switch (grade) {
      case 'A+':
      case 'A':
        return 'bg-green-50';
      case 'B':
        return 'bg-blue-50';
      case 'C':
        return 'bg-yellow-50';
      case 'D':
        return 'bg-orange-50';
      default:
        return 'bg-red-50';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">読み込み中...</div>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-800 px-6 py-4 rounded-lg">
          ❌ {error || 'データの読み込みに失敗しました'}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🛠️ データ管理ダッシュボード
        </h1>
        <p className="text-gray-600">
          データ品質レポート、エクスポート機能、エピソード編集
        </p>
      </div>

      {/* タブナビゲーション */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('quality')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'quality'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📊 品質レポート
          </button>
          <button
            onClick={() => setActiveTab('episodes')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'episodes'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📝 エピソード管理
          </button>
        </nav>
      </div>

      {/* 品質レポートタブ */}
      {activeTab === 'quality' && (
        <>
          {/* 品質スコアカード */}
          <div className={`${getGradeBg(report.summary.grade)} rounded-lg shadow-lg p-8 mb-8 border-l-8 ${report.summary.grade === 'A+' || report.summary.grade === 'A' ? 'border-green-500' : report.summary.grade === 'B' ? 'border-blue-500' : 'border-yellow-500'}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">データ品質スコア</h2>
          <div className="text-right">
            <div className={`text-6xl font-bold ${getGradeColor(report.summary.grade)}`}>
              {report.summary.grade}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              グレード評価
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-white rounded-lg p-4 shadow">
            <div className="text-sm text-gray-600">スコア</div>
            <div className="text-3xl font-bold text-gray-900">{report.summary.quality_score}</div>
            <div className="text-xs text-gray-500">/ 100点</div>
          </div>

          <div className="bg-white rounded-lg p-4 shadow">
            <div className="text-sm text-gray-600">総エピソード数</div>
            <div className="text-3xl font-bold text-gray-900">{report.summary.total_episodes.toLocaleString()}</div>
            <div className="text-xs text-gray-500">件</div>
          </div>

          <div className="bg-white rounded-lg p-4 shadow">
            <div className="text-sm text-gray-600">重複率</div>
            <div className="text-3xl font-bold text-orange-600">{report.summary.duplicate_rate}%</div>
            <div className="text-xs text-gray-500">{report.summary.duplicate_count}件検出</div>
          </div>

          <div className="bg-white rounded-lg p-4 shadow">
            <div className="text-sm text-gray-600">外れ値率</div>
            <div className="text-3xl font-bold text-purple-600">{report.summary.outlier_rate}%</div>
            <div className="text-xs text-gray-500">{report.summary.outlier_count}件検出</div>
          </div>
        </div>
      </div>

      {/* エクスポート機能 */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">📥 データエクスポート</h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            エクスポート対象
          </label>
          <select
            value={exportFilter}
            onChange={(e) => setExportFilter(e.target.value)}
            className="w-full md:w-64 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">全データ</option>
            <option value="high">高品質（総合スコア≥9.0）</option>
            <option value="medium">中品質以上（総合スコア≥7.0）</option>
          </select>
        </div>

        <div className="flex gap-4">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting}
            className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {exporting ? 'エクスポート中...' : '📄 CSV形式でエクスポート'}
          </button>

          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {exporting ? 'エクスポート中...' : '📦 JSON形式でエクスポート'}
          </button>
        </div>
      </div>

      {/* 重複検出結果 */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">🔄 重複検出結果</h2>
          <p className="text-sm text-gray-600 mt-1">
            {report.duplicates.count}件の重複を検出（人物名+年齢の組み合わせ）
          </p>
        </div>

        {report.duplicates.details.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">人物名</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">年齢</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">重複数</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">行番号</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {report.duplicates.details.map((dup, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{dup.person_name}</td>
                    <td className="px-4 py-3 text-gray-700">{dup.age}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-sm">
                        {dup.count}件
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {dup.row_numbers.join(', ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-8 text-center text-gray-500">
            重複は検出されませんでした
          </div>
        )}
      </div>

      {/* 外れ値検出結果 */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">📊 統計的外れ値検出結果</h2>
          <p className="text-sm text-gray-600 mt-1">
            {report.outliers.count}件の外れ値を検出（平均±3標準偏差）
          </p>
        </div>

        {report.outliers.details.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">人物名</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">年齢</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">評価軸</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">スコア</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Z-Score</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">行番号</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {report.outliers.details.map((outlier, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{outlier.person_name}</td>
                    <td className="px-4 py-3 text-gray-700">{outlier.age}</td>
                    <td className="px-4 py-3 text-gray-700">{outlier.axis}</td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-purple-600">{outlier.score.toFixed(2)}</span>
                      <span className="text-xs text-gray-500 ml-2">
                        (平均: {outlier.mean.toFixed(2)})
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
                        {outlier.z_score.toFixed(2)}σ
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-sm">{outlier.row_number}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-8 text-center text-gray-500">
            統計的外れ値は検出されませんでした
          </div>
        )}
      </div>

      {/* 完全性チェック結果 */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">✅ データ完全性チェック</h2>
          <p className="text-sm text-gray-600 mt-1">
            {report.completeness.issues_count}種類の問題を検出
          </p>
        </div>

        {report.completeness.issues.length > 0 ? (
          <div className="p-6 space-y-4">
            {report.completeness.issues.map((issue, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">
                    {issue.type === 'missing_required_field' && '必須フィールド欠損'}
                    {issue.type === 'score_out_of_range' && 'スコア範囲外'}
                    {issue.type === 'missing_score' && 'スコア欠損'}
                  </h3>
                  <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                    {issue.count}件
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  {issue.field && `フィールド: ${issue.field}`}
                  {issue.axis && `評価軸: ${issue.axis}`}
                  {issue.percentage !== undefined && ` (${issue.percentage.toFixed(2)}%)`}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-8 text-center text-gray-500">
            データ完全性の問題は検出されませんでした
          </div>
        )}
      </div>
        </>
      )}

      {/* エピソード管理タブ */}
      {activeTab === 'episodes' && (
        <>
          {/* 検索と新規作成 */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center gap-4">
              <input
                type="text"
                value={episodeSearchQuery}
                onChange={(e) => setEpisodeSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearchEpisodes()}
                placeholder="人物名またはエピソードテキストで検索..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSearchEpisodes}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                🔍 検索
              </button>
              <button
                onClick={handleCreateEpisode}
                className="px-6 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
              >
                ➕ 新規作成
              </button>
            </div>
          </div>

          {/* エピソード一覧 */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold">エピソード一覧</h2>
              <div className="text-sm text-gray-600">
                全{episodesTotal.toLocaleString()}件
              </div>
            </div>

            {episodesLoading ? (
              <div className="px-6 py-12 text-center text-gray-600">
                読み込み中...
              </div>
            ) : episodes.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                エピソードが見つかりませんでした
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">人物名</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">年齢</th>
                        <th
                          className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                          onClick={() => handleSort('work_title')}
                        >
                          作品名 {sortField === 'work_title' && (sortDirection === 'asc' ? '▲' : '▼')}
                        </th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">エピソード</th>
                        <th
                          className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100"
                          onClick={() => handleSort('composite_score')}
                        >
                          7軸スコア {sortField === 'composite_score' && (sortDirection === 'asc' ? '▲' : '▼')}
                        </th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {getSortedEpisodes().map((episode) => (
                        <tr key={episode.person_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{episode.person_name}</td>
                          <td className="px-4 py-3 text-gray-700">{episode.age}</td>
                          <td className="px-4 py-3 text-gray-700">
                            <div className="truncate max-w-xs">{episode.work_title || '-'}</div>
                          </td>
                          <td className="px-4 py-3 text-gray-700 max-w-md">
                            <div className="truncate">{episode.episode_text || '-'}</div>
                          </td>
                          <td className="px-4 py-3">
                            <SevenAxisScore episode={episode} />
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleEditEpisode(episode)}
                                className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors text-sm font-medium"
                              >
                                編集
                              </button>
                              <button
                                onClick={() => handleDeleteClick(episode.person_id)}
                                className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors text-sm font-medium"
                              >
                                削除
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* ページネーション */}
                <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    {(episodesPage - 1) * episodesPageSize + 1} - {Math.min(episodesPage * episodesPageSize, episodesTotal)} 件目を表示
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEpisodesPage(Math.max(1, episodesPage - 1))}
                      disabled={episodesPage === 1}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      前へ
                    </button>
                    <div className="px-4 py-2 text-gray-700">
                      {episodesPage} / {Math.ceil(episodesTotal / episodesPageSize)}
                    </div>
                    <button
                      onClick={() => setEpisodesPage(episodesPage + 1)}
                      disabled={episodesPage >= Math.ceil(episodesTotal / episodesPageSize)}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      次へ
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* エピソード編集/作成モーダル */}
      {showEpisodeModal && (
        <EpisodeModal
          episode={editingEpisode}
          onSave={handleSaveEpisode}
          onClose={() => {
            setShowEpisodeModal(false);
            setEditingEpisode(null);
          }}
        />
      )}

      {/* 削除確認ダイアログ */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">エピソードを削除しますか？</h3>
            <p className="text-gray-600 mb-6">
              この操作は取り消せません。本当に削除してもよろしいですか？
            </p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeletingEpisodeId(null);
                }}
                className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-6 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
              >
                削除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// エピソード編集/作成モーダルコンポーネント
function EpisodeModal({
  episode,
  onSave,
  onClose,
}: {
  episode: Episode | null;
  onSave: (data: EpisodeCreate | EpisodeUpdate) => void;
  onClose: () => void;
}) {
  const [formData, setFormData] = useState<Partial<EpisodeCreate>>({
    person_name: episode?.person_name || '',
    age: episode?.age || '',
    episode_text: episode?.episode_text || '',
    category: episode?.category || '',
    person_type: episode?.person_type || 'REAL',
    memorability_score: episode?.記憶性スコア ? parseFloat(episode.記憶性スコア) : undefined,
    empathy_score: episode?.共感性スコア ? parseFloat(episode.共感性スコア) : undefined,
    surprise_score: episode?.意外性スコア ? parseFloat(episode.意外性スコア) : undefined,
    generation_quality_score: episode?.生成品質スコア ? parseFloat(episode.生成品質スコア) : undefined,
    educational_value: episode?.教育的価値 ? parseFloat(episode.教育的価値) : undefined,
    storytelling_quality: episode?.ストーリー品質 ? parseFloat(episode.ストーリー品質) : undefined,
    factual_density: episode?.事実密度 ? parseFloat(episode.事実密度) : undefined,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-lg p-6 max-w-3xl w-full mx-4 my-8">
        <h3 className="text-2xl font-bold text-gray-900 mb-6">
          {episode ? 'エピソード編集' : '新規エピソード作成'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 基本情報 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                人物名 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.person_name}
                onChange={(e) => setFormData({ ...formData, person_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                年齢 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              エピソードテキスト <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={4}
              value={formData.episode_text}
              onChange={(e) => setFormData({ ...formData, episode_text: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">カテゴリ</label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">人物タイプ</label>
              <select
                value={formData.person_type}
                onChange={(e) => setFormData({ ...formData, person_type: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="REAL">実在</option>
                <option value="FICTIONAL">架空</option>
              </select>
            </div>
          </div>

          {/* 7軸スコア */}
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-4">評価スコア（0-10）</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">記憶性</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.memorability_score || ''}
                  onChange={(e) => setFormData({ ...formData, memorability_score: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">共感性</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.empathy_score || ''}
                  onChange={(e) => setFormData({ ...formData, empathy_score: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">意外性</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.surprise_score || ''}
                  onChange={(e) => setFormData({ ...formData, surprise_score: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">生成品質</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.generation_quality_score || ''}
                  onChange={(e) => setFormData({ ...formData, generation_quality_score: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">教育的価値</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.educational_value || ''}
                  onChange={(e) => setFormData({ ...formData, educational_value: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">ストーリー品質</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.storytelling_quality || ''}
                  onChange={(e) => setFormData({ ...formData, storytelling_quality: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">事実密度</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.factual_density || ''}
                  onChange={(e) => setFormData({ ...formData, factual_density: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* ボタン */}
          <div className="flex gap-4 justify-end pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors"
            >
              キャンセル
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              {episode ? '更新' : '作成'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
