-- ========================================
-- インデックス最適化スクリプト v5.0
-- 作成日: 2025年6月25日  
-- 目的: パフォーマンス向上のための複合インデックス追加
-- ========================================

-- ----------------------------------------
-- 地名検索用複合インデックス
-- ----------------------------------------

-- place_mentions テーブル用インデックス（地名、作品、位置情報）
CREATE INDEX IF NOT EXISTS idx_place_mentions_search ON place_mentions (
    place_master_id, work_id, sentence_id, confidence_score DESC
);

-- place_mentions の検証済み地名検索用
CREATE INDEX IF NOT EXISTS idx_place_mentions_verified ON place_mentions (
    is_verified, place_master_id, work_id
) WHERE is_verified = 1;

-- place_masters の名前検索用（部分一致対応）
CREATE INDEX IF NOT EXISTS idx_place_masters_name_search ON place_masters (
    name_reading, standard_name, prefecture
);

-- 地理的検索用（緯度経度）
CREATE INDEX IF NOT EXISTS idx_place_masters_geo ON place_masters (
    latitude, longitude
) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- ----------------------------------------
-- AI検証用インデックス  
-- ----------------------------------------

-- ai_verifications テーブル用（検証状況別検索）
CREATE INDEX IF NOT EXISTS idx_ai_verifications_status ON ai_verifications (
    verification_status, place_mention_id, verified_at DESC
);

-- AI検証の信頼度順検索用
CREATE INDEX IF NOT EXISTS idx_ai_verifications_confidence ON ai_verifications (
    place_mention_id, confidence_score DESC, verification_type
);

-- モデル別検証履歴用
CREATE INDEX IF NOT EXISTS idx_ai_verifications_model ON ai_verifications (
    ai_model, verification_type, verified_at DESC
);

-- ----------------------------------------
-- 統計計算用インデックス
-- ----------------------------------------

-- 統計キャッシュ検索用
CREATE INDEX IF NOT EXISTS idx_statistics_cache_lookup ON statistics_cache (
    cache_type, entity_id, expires_at
);

-- 期限切れキャッシュクリーンアップ用
CREATE INDEX IF NOT EXISTS idx_statistics_cache_expired ON statistics_cache (
    expires_at
) WHERE expires_at IS NOT NULL;

-- 作家別統計用
CREATE INDEX IF NOT EXISTS idx_works_author_stats ON works (
    author_id, publication_year, status
);

-- 地域別統計用  
CREATE INDEX IF NOT EXISTS idx_place_mentions_region ON place_mentions 
JOIN place_masters ON place_mentions.place_master_id = place_masters.id (
    place_masters.prefecture, place_masters.city, place_mentions.work_id
);

-- ----------------------------------------
-- 階層構造検索用インデックス
-- ----------------------------------------

-- sections テーブルの階層検索用
CREATE INDEX IF NOT EXISTS idx_sections_hierarchy ON sections (
    work_id, section_type, parent_section_id, section_number
);

-- セクション内容検索用
CREATE INDEX IF NOT EXISTS idx_sections_content ON sections (
    work_id, section_type, character_position
);

-- 親子関係検索用
CREATE INDEX IF NOT EXISTS idx_sections_parent_child ON sections (
    parent_section_id, section_number
) WHERE parent_section_id IS NOT NULL;

-- ----------------------------------------
-- 処理ログ用インデックス
-- ----------------------------------------

-- 処理ログの状況別検索用
CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs (
    process_type, status, started_at DESC
);

-- 作品別処理履歴用
CREATE INDEX IF NOT EXISTS idx_processing_logs_work ON processing_logs (
    work_id, process_type, completed_at DESC
) WHERE work_id IS NOT NULL;

-- エラー分析用
CREATE INDEX IF NOT EXISTS idx_processing_logs_errors ON processing_logs (
    status, process_type, started_at
) WHERE status = 'failed';

-- ----------------------------------------
-- パフォーマンス分析用インデックス
-- ----------------------------------------

-- 文章と地名の関係検索用（高頻度クエリ対応）
CREATE INDEX IF NOT EXISTS idx_sentences_place_mentions ON sentences (
    id, work_id, content_hash
);

-- 作品内での地名出現頻度分析用
CREATE INDEX IF NOT EXISTS idx_place_frequency ON place_mentions (
    work_id, place_master_id, sentence_id
);

-- 時系列分析用（出版年度別）
CREATE INDEX IF NOT EXISTS idx_temporal_analysis ON works 
JOIN place_mentions ON works.id = place_mentions.work_id (
    works.publication_year, place_mentions.place_master_id
);

-- ----------------------------------------
-- 全文検索インデックス（FTS5）
-- ----------------------------------------

-- セクション内容の全文検索
CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
    title, content, 
    content='sections',
    content_rowid='id'
);

-- トリガーで自動更新
CREATE TRIGGER IF NOT EXISTS sections_fts_insert AFTER INSERT ON sections BEGIN
    INSERT INTO sections_fts(rowid, title, content) 
    VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS sections_fts_delete AFTER DELETE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, title, content) 
    VALUES('delete', old.id, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS sections_fts_update AFTER UPDATE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, title, content) 
    VALUES('delete', old.id, old.title, old.content);
    INSERT INTO sections_fts(rowid, title, content) 
    VALUES (new.id, new.title, new.content);
END;

-- 地名マスターの全文検索
CREATE VIRTUAL TABLE IF NOT EXISTS place_masters_fts USING fts5(
    standard_name, name_reading, name_variants,
    content='place_masters', 
    content_rowid='id'
);

-- ----------------------------------------
-- インデックス使用量分析ビュー
-- ----------------------------------------

-- インデックス効果測定用ビュー
CREATE VIEW IF NOT EXISTS index_usage_stats AS
SELECT 
    'place_search' as index_category,
    COUNT(*) as query_count,
    AVG(CASE WHEN confidence_score >= 0.8 THEN 1 ELSE 0 END) as success_rate
FROM place_mentions 
WHERE created_at >= datetime('now', '-1 day')

UNION ALL

SELECT 
    'ai_verification' as index_category,
    COUNT(*) as query_count,
    AVG(CASE WHEN verification_status = 'verified' THEN 1 ELSE 0 END) as success_rate
FROM ai_verifications
WHERE verified_at >= datetime('now', '-1 day')

UNION ALL  

SELECT
    'statistics_cache' as index_category,
    COUNT(*) as query_count,
    AVG(CASE WHEN expires_at > datetime('now') THEN 1 ELSE 0 END) as success_rate
FROM statistics_cache
WHERE created_at >= datetime('now', '-1 day');

-- ----------------------------------------
-- インデックスメンテナンス
-- ----------------------------------------

-- 統計情報更新（SQLiteの場合は ANALYZE）
-- 定期実行推奨（1日1回程度）
-- ANALYZE;

-- 期限切れキャッシュクリーンアップ用プロシージャ相当
-- DELETE FROM statistics_cache WHERE expires_at < datetime('now');

-- ----------------------------------------
-- パフォーマンス監視用クエリ例
-- ----------------------------------------

/*
-- 地名検索パフォーマンス確認
EXPLAIN QUERY PLAN
SELECT pm.*, pmr.standard_name 
FROM place_mentions pm
JOIN place_masters pmr ON pm.place_master_id = pmr.id
WHERE pmr.prefecture = '東京都' 
  AND pm.confidence_score >= 0.8
ORDER BY pm.sentence_id;

-- AI検証履歴検索パフォーマンス確認  
EXPLAIN QUERY PLAN
SELECT * FROM ai_verifications 
WHERE place_mention_id = ? 
  AND verification_status = 'verified'
ORDER BY verified_at DESC;

-- 統計キャッシュ検索パフォーマンス確認
EXPLAIN QUERY PLAN
SELECT data FROM statistics_cache
WHERE cache_type = 'author_stats' 
  AND entity_id = ?
  AND (expires_at IS NULL OR expires_at > datetime('now'));
*/ 