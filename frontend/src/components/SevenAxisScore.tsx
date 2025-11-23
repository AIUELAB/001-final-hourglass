/**
 * 7軸スコア表示コンポーネント
 *
 * バックエンドダッシュボードと同じ縦積みレイアウトで7軸スコアを表示
 */

import type { Episode } from '../types/character';

interface SevenAxisScoreProps {
  episode: Episode;
}

export function SevenAxisScore({ episode }: SevenAxisScoreProps) {
  const compositeScore = episode.composite_score ? parseFloat(episode.composite_score) : null;
  const memorabilityScore = episode['記憶性スコア'] ? parseFloat(episode['記憶性スコア']) : null;
  const empathyScore = episode['共感性スコア'] ? parseFloat(episode['共感性スコア']) : null;
  const surpriseScore = episode['意外性スコア'] ? parseFloat(episode['意外性スコア']) : null;
  const qualityScore = episode['生成品質スコア'] ? parseFloat(episode['生成品質スコア']) : null;
  const educationalValue = episode['教育的価値'] ? parseFloat(episode['教育的価値']) : null;
  const storytellingQuality = episode['ストーリー品質'] ? parseFloat(episode['ストーリー品質']) : null;
  const factualDensity = episode['事実密度'] ? parseFloat(episode['事実密度']) : null;

  const formatScore = (score: number | null): string => {
    return score !== null ? score.toFixed(1) : '-';
  };

  if (!compositeScore) {
    return (
      <div className="text-center text-gray-400 italic py-2">
        <div className="font-semibold text-gray-500">総合: <span className="text-gray-300">-</span></div>
        <div className="text-xs mt-1">スコア未算出</div>
      </div>
    );
  }

  return (
    <div className="py-1 px-2 text-sm">
      {/* 総合スコア */}
      <div className="font-bold text-blue-600 mb-2">
        総合: <span className="text-base">{compositeScore.toFixed(1)}</span>
      </div>

      {/* 7軸スコア */}
      <div className="text-xs text-gray-600 space-y-0.5">
        {/* 行1 */}
        <div className="flex justify-between gap-2">
          <span>
            <span className="text-gray-500">記憶:</span> {formatScore(memorabilityScore)}
          </span>
          <span>
            <span className="text-gray-500">共感:</span> {formatScore(empathyScore)}
          </span>
        </div>

        {/* 行2 */}
        <div className="flex justify-between gap-2">
          <span>
            <span className="text-gray-500">意外:</span> {formatScore(surpriseScore)}
          </span>
          <span>
            <span className="text-gray-500">品質:</span> {formatScore(qualityScore)}
          </span>
        </div>

        {/* 行3 */}
        <div className="flex justify-between gap-2">
          <span>
            <span className="text-gray-500">教育:</span> {formatScore(educationalValue)}
          </span>
          <span>
            <span className="text-gray-500">物語:</span> {formatScore(storytellingQuality)}
          </span>
        </div>

        {/* 行4 */}
        <div className="flex justify-between gap-2">
          <span>
            <span className="text-gray-500">事実:</span> {formatScore(factualDensity)}
          </span>
          <span className="opacity-0">-</span> {/* スペーサー */}
        </div>
      </div>
    </div>
  );
}
