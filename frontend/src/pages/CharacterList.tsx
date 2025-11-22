/**
 * CharacterList ページ
 *
 * キャラクター一覧表示・検索機能
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCharacters, searchCharacters } from '../api/client';
import type { Character } from '../types/character';

export function CharacterList() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchCharacters = async () => {
    setLoading(true);
    try {
      if (searchQuery.trim()) {
        const results = await searchCharacters(searchQuery);
        setCharacters(results);
        setTotal(results.length);
      } else {
        const data = await getCharacters(page, pageSize);
        setCharacters(data.characters);
        setTotal(data.total);
      }
    } catch (error) {
      console.error('キャラクターの取得に失敗:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCharacters();
  }, [page]);

  const handleSearch = () => {
    setPage(1);
    fetchCharacters();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const totalPages = Math.ceil(total / pageSize);

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
          キャラクター一覧
        </h1>
        <p className="text-gray-600">
          全{total.toLocaleString()}件のエピソードデータ
        </p>
      </div>

      {/* 検索バー */}
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="キャラクター名または作品名で検索..."
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          onClick={handleSearch}
          className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          🔍 検索
        </button>
        {searchQuery && (
          <button
            onClick={() => {
              setSearchQuery('');
              setPage(1);
              fetchCharacters();
            }}
            className="px-6 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            クリア
          </button>
        )}
      </div>

      {/* キャラクターカード */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {characters.map((character) => (
          <Link
            key={character.id}
            to={`/characters/${character.id}`}
            className="bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow p-6 border-l-4 border-blue-500"
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-xl font-bold text-gray-900">
                {character.character_name}
              </h3>
              <span className="text-2xl">
                {character.genre.includes('野球') ? '⚾' :
                 character.genre.includes('バスケ') ? '🏀' :
                 character.genre.includes('サッカー') ? '⚽' :
                 character.genre.includes('漫画') ? '📖' :
                 character.genre.includes('音楽') ? '🎵' : '📚'}
              </span>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center text-gray-600">
                <span className="font-medium mr-2">作品:</span>
                <span className="truncate">{character.work_title}</span>
              </div>

              <div className="flex items-center text-gray-600">
                <span className="font-medium mr-2">ジャンル:</span>
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                  {character.genre}
                </span>
              </div>

              <div className="flex items-center text-gray-600">
                <span className="font-medium mr-2">年齢:</span>
                <span>{character.age_in_story}</span>
              </div>

              <div className="mt-3 pt-3 border-t border-gray-200">
                <p className="text-gray-700 text-xs line-clamp-3">
                  {character.key_episode}
                </p>
              </div>
            </div>

            <div className="mt-4 text-blue-600 text-sm font-medium flex items-center">
              詳細を見る →
            </div>
          </Link>
        ))}
      </div>

      {/* ページネーション */}
      {!searchQuery && (
        <div className="flex justify-center items-center space-x-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← 前へ
          </button>

          <div className="text-gray-700">
            ページ {page} / {totalPages} ({total.toLocaleString()}件中 {((page - 1) * pageSize + 1).toLocaleString()}-{Math.min(page * pageSize, total).toLocaleString()}件)
          </div>

          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            次へ →
          </button>
        </div>
      )}
    </div>
  );
}
