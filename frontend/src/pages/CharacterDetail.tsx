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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">ジャンル</div>
              <div className="text-lg font-bold text-blue-900">{character.genre}</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">年齢</div>
              <div className="text-lg font-bold text-purple-900">{character.age_in_story}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">検証状態</div>
              <div className="text-lg font-bold text-green-900">{character.validation_status}</div>
            </div>
          </div>

          {/* 主要エピソード */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">🎯</span>
              主要エピソード
            </h2>
            <div className="bg-gray-50 rounded-lg p-6">
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {character.key_episode}
              </p>
            </div>
          </section>

          {/* 詳細な達成記録 */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">🏆</span>
              詳細な達成記録
            </h2>
            <div className="bg-yellow-50 rounded-lg p-6 border-l-4 border-yellow-400">
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {character.detailed_achievements}
              </p>
            </div>
          </section>

          {/* ストーリー展開 */}
          {character.story_events && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">📖</span>
                ストーリー展開
              </h2>
              <div className="bg-blue-50 rounded-lg p-6">
                <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {character.story_events}
                </p>
              </div>
            </section>
          )}

          {/* 成長物語 */}
          {character.growth_narrative && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">🌱</span>
                成長物語
              </h2>
              <div className="bg-green-50 rounded-lg p-6">
                <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {character.growth_narrative}
                </p>
              </div>
            </section>
          )}

          {/* キュレーターノート */}
          {character.curator_notes && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">📝</span>
                キュレーターノート
              </h2>
              <div className="bg-purple-50 rounded-lg p-6 border-l-4 border-purple-400">
                <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {character.curator_notes}
                </p>
              </div>
            </section>
          )}

          {/* Wikipedia リンク */}
          {character.wikipedia_url && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">🔗</span>
                外部リンク
              </h2>
              <a
                href={character.wikipedia_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                <span className="mr-2">📚</span>
                Wikipediaで詳細を見る
                <span className="ml-2">→</span>
              </a>
            </section>
          )}

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
