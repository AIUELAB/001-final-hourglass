/**
 * CharacterDetail ページ
 *
 * キャラクター詳細表示
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getCharacterById } from '../api/client';
import type { Character } from '../types/character';

export function CharacterDetail() {
  const { id } = useParams<{ id: string }>();
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCharacter = async () => {
      if (!id) return;

      setLoading(true);
      try {
        const data = await getCharacterById(parseInt(id));
        setCharacter(data);
      } catch (error) {
        console.error('キャラクターの取得に失敗:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCharacter();
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-gray-600">読み込み中...</div>
      </div>
    );
  }

  if (!character) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-600 text-lg">キャラクターが見つかりませんでした</p>
          <Link to="/characters" className="text-blue-600 hover:underline mt-4 inline-block">
            一覧に戻る
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* パンくずリスト */}
      <div className="mb-6 text-sm text-gray-600">
        <Link to="/" className="hover:text-blue-600">統計</Link>
        <span className="mx-2">/</span>
        <Link to="/characters" className="hover:text-blue-600">キャラクター一覧</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{character.character_name}</span>
      </div>

      {/* メインカード */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* ヘッダー */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2">
                {character.character_name}
              </h1>
              <p className="text-xl opacity-90">
                {character.work_title}
              </p>
            </div>
            <div className="text-6xl">
              {character.genre.includes('野球') ? '⚾' :
               character.genre.includes('バスケ') ? '🏀' :
               character.genre.includes('サッカー') ? '⚽' :
               character.genre.includes('漫画') ? '📖' :
               character.genre.includes('音楽') ? '🎵' : '📚'}
            </div>
          </div>
        </div>

        {/* 基本情報 */}
        <div className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">ジャンル</div>
              <div className="text-lg font-bold text-blue-900">{character.genre}</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">エピソードカテゴリ</div>
              <div className="text-lg font-bold text-purple-900">{character.episode_category}</div>
            </div>
          </div>

          {/* エピソード本文 */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">📖</span>
              エピソード
            </h2>
            <div className="bg-gray-50 rounded-lg p-6 border-l-4 border-blue-500">
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap text-base">
                {character.episode_text}
              </p>
            </div>
          </section>

          {/* 戻るボタン */}
          <div className="pt-6 border-t border-gray-200">
            <Link
              to="/characters"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              ← キャラクター一覧に戻る
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
