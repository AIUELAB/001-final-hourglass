-- ========================================
-- 括弧表示システム - データベースマイグレーション
-- ========================================
-- 作成日: 2025-10-02
-- 目的: グループ名・作品名の括弧表示に必要なカラムを追加
-- 対象テーブル: persons

-- ========================================
-- Step 1: 新規カラムの追加
-- ========================================

-- 人物の種類（実在人物 or 架空キャラクター）
ALTER TABLE persons ADD COLUMN entity_type TEXT DEFAULT 'real_person' CHECK(entity_type IN ('real_person', 'fictional_character'));

-- 所属グループ名（カンマ区切りで複数対応）
ALTER TABLE persons ADD COLUMN group_affiliation TEXT;

-- 架空キャラクターの作品名
ALTER TABLE persons ADD COLUMN primary_work TEXT;

-- 括弧表示フラグ（0: 非表示, 1: 表示）
ALTER TABLE persons ADD COLUMN show_group_in_bracket INTEGER DEFAULT 0 CHECK(show_group_in_bracket IN (0, 1));

-- グループ活動状態
ALTER TABLE persons ADD COLUMN group_status TEXT CHECK(group_status IN ('active', 'disbanded', 'hiatus', NULL));

-- 知名度レベル
ALTER TABLE persons ADD COLUMN fame_level TEXT CHECK(fame_level IN ('personal_more_famous', 'group_more_famous', 'equal', NULL));

-- 実際に表示する括弧内テキスト
ALTER TABLE persons ADD COLUMN bracket_display_text TEXT;

-- データ更新日時
ALTER TABLE persons ADD COLUMN bracket_data_updated_at TIMESTAMP;

-- ========================================
-- Step 2: インデックスの作成（パフォーマンス最適化）
-- ========================================

CREATE INDEX IF NOT EXISTS idx_persons_entity_type ON persons(entity_type);
CREATE INDEX IF NOT EXISTS idx_persons_show_bracket ON persons(show_group_in_bracket);
CREATE INDEX IF NOT EXISTS idx_persons_group_status ON persons(group_status);

-- ========================================
-- Step 3: 既存データの初期化
-- ========================================

-- すべて実在人物として初期化
UPDATE persons SET entity_type = 'real_person' WHERE entity_type IS NULL;

-- 括弧表示フラグを0に初期化
UPDATE persons SET show_group_in_bracket = 0 WHERE show_group_in_bracket IS NULL;

-- ========================================
-- 完了メッセージ
-- ========================================

-- SELECT 'Migration completed successfully!' AS status;
