-- =============================================================================
-- Supabase Episodes Table: 欠落カラム追加スクリプト
-- =============================================================================
-- プロジェクト: 001-final-hourglass
-- 実行場所: Supabase ダッシュボード > SQL Editor
-- 目的: 既存のepisodesテーブルに13個の欠落カラムを安全に追加する
-- 作成日: 2026-02-03
-- =============================================================================
--
-- 使用方法:
--   1. Supabaseダッシュボードにログイン
--   2. 左メニューから「SQL Editor」を選択
--   3. 「New query」をクリック
--   4. このスクリプト全体をコピー&ペースト
--   5. 「Run」をクリックして実行
--
-- 注意:
--   - IF NOT EXISTS を使用しているため、既存カラムがあってもエラーになりません
--   - 本番環境で実行する前に、開発環境でテストしてください
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. スコア関連カラム（数値型）
-- -----------------------------------------------------------------------------

-- desirability_score: iOSアプリのソートキー（最重要）
-- 望ましさスコア。iOSアプリでエピソードをソートする際の主要キー
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS desirability_score NUMERIC(10,2);

-- event_magnitude: イベント規模スコア
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS event_magnitude NUMERIC(6,2);

-- recency_boost: 最新性ブースト
-- 最近のエピソードに対するスコア加算値
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS recency_boost NUMERIC(6,2);

-- heuristic_quality_score: ヒューリスティック品質スコア
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS heuristic_quality_score NUMERIC(6,2);

-- -----------------------------------------------------------------------------
-- 2. メタデータカラム（整数型）
-- -----------------------------------------------------------------------------

-- char_count: エピソードテキストの文字数
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS char_count INTEGER;

-- slot: スロット番号（表示位置など）
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS slot INTEGER;

-- -----------------------------------------------------------------------------
-- 3. 分類・カテゴリカラム（テキスト型）
-- -----------------------------------------------------------------------------

-- tier: エピソードのティア（品質レベル分類）
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS tier TEXT;

-- 年代: 時代区分（日本語カラム名、既存スキーマとの整合性維持）
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS "年代" TEXT;

-- narrative_tone: 物語のトーン（感動的、励まし、など）
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS narrative_tone TEXT;

-- cultural_context: 文化的背景・コンテキスト
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS cultural_context TEXT;

-- episode_source: エピソードの出典・ソース
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS episode_source TEXT;

-- episode_version: エピソードのバージョン
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS episode_version TEXT;

-- fact_check_result: ファクトチェック結果（verified, unverified, false等）
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS fact_check_result TEXT;

-- -----------------------------------------------------------------------------
-- 4. インデックス作成（パフォーマンス最適化）
-- -----------------------------------------------------------------------------

-- desirability_scoreのインデックス（iOSアプリのソート高速化用）
-- IF NOT EXISTSはPostgreSQLのCREATE INDEXでは直接使えないため、
-- DO ブロックで条件チェックを行う
DO $$
BEGIN
    -- 単一カラムインデックス
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_episodes_desirability_score'
    ) THEN
        CREATE INDEX idx_episodes_desirability_score
        ON episodes(desirability_score DESC NULLS LAST);
    END IF;

    -- 複合インデックス（タイブレーク用: desirability_score + episode_id）
    -- iOSアプリで決定論的ソートを実現するための重要なインデックス
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_episodes_desirability_episode_id'
    ) THEN
        CREATE INDEX idx_episodes_desirability_episode_id
        ON episodes(desirability_score DESC NULLS LAST, episode_id ASC);
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 5. カラムコメント追加（ドキュメント用）
-- -----------------------------------------------------------------------------

COMMENT ON COLUMN episodes.desirability_score IS 'iOSアプリのソートキー（望ましさスコア）';
COMMENT ON COLUMN episodes.event_magnitude IS 'イベント規模スコア';
COMMENT ON COLUMN episodes.recency_boost IS '最新性ブーストスコア';
COMMENT ON COLUMN episodes.char_count IS 'エピソードテキストの文字数';
COMMENT ON COLUMN episodes.slot IS 'スロット番号';
COMMENT ON COLUMN episodes.tier IS 'エピソードティア';
COMMENT ON COLUMN episodes."年代" IS '時代区分';
COMMENT ON COLUMN episodes.narrative_tone IS '物語のトーン';
COMMENT ON COLUMN episodes.cultural_context IS '文化的背景';
COMMENT ON COLUMN episodes.episode_source IS 'エピソードの出典';
COMMENT ON COLUMN episodes.episode_version IS 'エピソードバージョン';
COMMENT ON COLUMN episodes.heuristic_quality_score IS 'ヒューリスティック品質スコア';
COMMENT ON COLUMN episodes.fact_check_result IS 'ファクトチェック結果';

-- -----------------------------------------------------------------------------
-- 6. 確認用クエリ
-- -----------------------------------------------------------------------------

-- 追加したカラムの確認（実行後にコメントを外して確認可能）
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'episodes'
-- AND column_name IN (
--     'desirability_score', 'event_magnitude', 'recency_boost', 'char_count',
--     'slot', 'tier', '年代', 'narrative_tone', 'cultural_context',
--     'episode_source', 'episode_version', 'heuristic_quality_score', 'fact_check_result'
-- )
-- ORDER BY column_name;

-- インデックスの確認
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'episodes'
-- AND indexname = 'idx_episodes_desirability_score';

-- -----------------------------------------------------------------------------
-- 7. hybrid_score カラム追加 (Hybrid-C ソート方式)
-- -----------------------------------------------------------------------------
-- 追加日: 2026-02-04
-- 目的: iOSアプリでHybrid-Cソート方式を実現するための新しいスコアカラム

-- hybrid_score: Hybrid-C方式で計算されたソートスコア
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS hybrid_score DOUBLE PRECISION;

-- インデックス作成（タイブレーク用: hybrid_score + episode_id）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_episodes_hybrid_score'
    ) THEN
        CREATE INDEX idx_episodes_hybrid_score
        ON episodes(hybrid_score DESC NULLS LAST, episode_id ASC);
    END IF;
END $$;

-- カラムコメント
COMMENT ON COLUMN episodes.hybrid_score IS 'Hybrid-Cソート方式のスコア（iOSアプリ用）';

-- -----------------------------------------------------------------------------
-- 8. grammar_quality_score カラム追加（エピソード文法品質システム）
-- -----------------------------------------------------------------------------
-- 追加日: 2026-02-20
-- 目的: 体言止め検出・文の完結性・形式一貫性を数値化するスコアカラム

-- grammar_quality_score: 文法品質スコア
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS grammar_quality_score NUMERIC(4,2);

-- カラムコメント
COMMENT ON COLUMN episodes.grammar_quality_score IS '文法品質スコア（体言止め検出・文完結性・形式一貫性）';
