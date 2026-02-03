-- Supabase Episodes Table Schema
-- プロジェクト: 001-final-hourglass
-- 実行場所: Supabaseダッシュボード > SQL Editor

-- 1. 既存テーブル削除（存在する場合）
DROP TABLE IF EXISTS episodes CASCADE;

-- 2. episodesテーブル作成
CREATE TABLE episodes (
  episode_id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  person_name TEXT NOT NULL,
  episode_count INTEGER,
  age INTEGER NOT NULL,
  category TEXT,
  episode_text TEXT NOT NULL,
  episode_type TEXT,
  group_name TEXT,
  is_group_member BOOLEAN DEFAULT FALSE,
  person_type TEXT DEFAULT 'REAL',
  source TEXT,
  work_title TEXT,
  generation_timestamp TIMESTAMPTZ,
  fame_tier TEXT,

  -- 旧スコア（互換性）
  episode_importance_score NUMERIC(6,2),
  episode_fame_score NUMERIC(10,2),
  impressiveness_score NUMERIC(6,2),
  generated_at TIMESTAMPTZ,
  verification_status TEXT,
  evidence_quality TEXT,
  総合品質 NUMERIC(6,2),                  -- overall_quality (legacy Japanese column name)
  感情インパクト NUMERIC(6,2),             -- emotional_impact (legacy Japanese column name)
  composite_score_5axis NUMERIC(6,2),

  -- 8軸スコア
  memorability_score NUMERIC(4,2),
  empathy_score NUMERIC(4,2),
  surprise_score NUMERIC(4,2),
  generation_quality_score NUMERIC(4,2),
  educational_value NUMERIC(4,2),
  storytelling_quality NUMERIC(4,2),
  factual_density NUMERIC(4,2),
  iconic_score NUMERIC(4,2),

  -- LLM評価日時
  llm_evaluated_at TIMESTAMPTZ,

  -- 有名度関連
  wikipedia_pv BIGINT,
  fame_score_v3 NUMERIC(12,2),
  fame_rank_v3 INTEGER,
  multi_lang_pv BIGINT,
  sitelinks_count INTEGER,
  google_hits BIGINT,
  is_japanese BOOLEAN,
  birth_year INTEGER,
  death_year INTEGER,
  is_fictional BOOLEAN DEFAULT FALSE,
  celebrity_score_v2 NUMERIC(12,2),
  celebrity_rank_v2 INTEGER,

  -- エピソードfameスコア
  episode_fame_v6 NUMERIC(10,2),
  episode_fame_tier_v6 INTEGER,
  episode_fame_v6_updated_at TIMESTAMPTZ,

  -- 複合スコア
  composite_score NUMERIC(10,2),
  super_total_score NUMERIC(14,2),

  -- 生成メタデータ
  model TEXT,
  generator_type TEXT,
  cost_usd NUMERIC(8,6),
  story_quality NUMERIC(4,2),

  -- スコア追加
  desirability_score NUMERIC(10,2),
  hybrid_score DOUBLE PRECISION,
  event_magnitude NUMERIC(6,2),
  recency_boost NUMERIC(6,2),
  heuristic_quality_score NUMERIC(6,2),

  -- メタデータ追加
  char_count INTEGER,
  slot INTEGER,
  tier TEXT,
  "年代" TEXT,

  -- その他テキストカラム
  narrative_tone TEXT,
  cultural_context TEXT,
  episode_source TEXT,
  episode_version TEXT,
  fact_check_result TEXT,

  -- Supabase管理
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. インデックス作成
CREATE INDEX idx_episodes_person_id ON episodes(person_id);
CREATE INDEX idx_episodes_person_age ON episodes(person_id, age);
CREATE INDEX idx_episodes_super_total ON episodes(super_total_score DESC NULLS LAST);
CREATE INDEX idx_episodes_category ON episodes(category);
CREATE INDEX idx_episodes_episode_fame ON episodes(episode_fame_v6 DESC NULLS LAST);
CREATE INDEX idx_episodes_person_type ON episodes(person_type);
CREATE INDEX idx_episodes_desirability_score ON episodes(desirability_score DESC NULLS LAST);
CREATE INDEX idx_episodes_desirability_episode_id ON episodes(desirability_score DESC NULLS LAST, episode_id ASC);
CREATE INDEX idx_episodes_hybrid_score ON episodes(hybrid_score DESC NULLS LAST, episode_id ASC);

-- 4. RLS（Row Level Security）有効化
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;

-- 5. 読み取りポリシー（anon: 全員読み取り可能）
CREATE POLICY "Public read access" ON episodes
  FOR SELECT
  TO anon
  USING (true);

-- 6. 書き込みポリシー（service_role: 管理者のみ書き込み可能、操作別に分割）
-- RLSポリシーを操作別に分割して粒度を改善（PRレビューH-1対応）

-- 6a. INSERT: episode_idとperson_nameが必須
CREATE POLICY "Service role insert" ON episodes
  FOR INSERT TO service_role
  WITH CHECK (episode_id IS NOT NULL AND person_name IS NOT NULL);

-- 6b. UPDATE: episode_idが存在するレコードのみ更新可能
CREATE POLICY "Service role update" ON episodes
  FOR UPDATE TO service_role
  USING (true)
  WITH CHECK (episode_id IS NOT NULL);

-- 6c. DELETE: 任意のレコードを削除可能
CREATE POLICY "Service role delete" ON episodes
  FOR DELETE TO service_role
  USING (true);

-- 7. updated_at自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER episodes_updated_at
  BEFORE UPDATE ON episodes
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- 8. カラム説明（ドキュメント用）
COMMENT ON COLUMN episodes.episode_fame_v6 IS 'エピソードfameスコア v6（0-100）';
COMMENT ON COLUMN episodes.super_total_score IS '超総合スコア（fame + quality）';
COMMENT ON COLUMN episodes.birth_year IS '人物の生年（西暦）';
COMMENT ON COLUMN episodes.death_year IS '人物の没年（西暦）';
COMMENT ON COLUMN episodes.is_fictional IS '架空キャラクターフラグ';
COMMENT ON COLUMN episodes.desirability_score IS 'エピソード望ましさスコア（検索・表示優先度）';
COMMENT ON COLUMN episodes.hybrid_score IS 'Hybrid-Cソート方式のスコア（iOSアプリ用）';

-- 確認用クエリ
-- SELECT COUNT(*) FROM episodes;
-- SELECT * FROM episodes ORDER BY super_total_score DESC LIMIT 10;
