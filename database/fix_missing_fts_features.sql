-- 文豪ゆかり地図システムv4 FTS機能修正スクリプト
-- 設計書との差分を修正

-- 1. 既存のplace_searchテーブルを削除
DROP TABLE IF EXISTS place_search;

-- 2. 正しいFTS5テーブルとして再作成
CREATE VIRTUAL TABLE place_search USING fts5(
    master_id UNINDEXED,
    normalized_name,
    display_name,
    canonical_name,
    aliases,
    content=''
);

-- 3. FTS初期化トリガー作成
CREATE TRIGGER place_masters_fts_insert AFTER INSERT ON place_masters
BEGIN
    INSERT INTO place_search(master_id, normalized_name, display_name, canonical_name, aliases)
    VALUES (
        NEW.master_id, 
        NEW.normalized_name, 
        NEW.display_name, 
        NEW.canonical_name,
        COALESCE((
            SELECT GROUP_CONCAT(alias_name, ' ')
            FROM place_aliases 
            WHERE master_id = NEW.master_id
        ), '')
    );
END;

CREATE TRIGGER place_masters_fts_update AFTER UPDATE ON place_masters
BEGIN
    UPDATE place_search SET 
        normalized_name = NEW.normalized_name,
        display_name = NEW.display_name,
        canonical_name = NEW.canonical_name,
        aliases = COALESCE((
            SELECT GROUP_CONCAT(alias_name, ' ')
            FROM place_aliases 
            WHERE master_id = NEW.master_id
        ), '')
    WHERE master_id = NEW.master_id;
END;

CREATE TRIGGER place_masters_fts_delete AFTER DELETE ON place_masters
BEGIN
    DELETE FROM place_search WHERE master_id = OLD.master_id;
END;

-- 4. place_aliases変更時のFTS更新トリガー
CREATE TRIGGER place_aliases_fts_update AFTER INSERT ON place_aliases
BEGIN
    UPDATE place_search SET 
        aliases = (
            SELECT GROUP_CONCAT(alias_name, ' ')
            FROM place_aliases 
            WHERE master_id = NEW.master_id
        )
    WHERE master_id = NEW.master_id;
END;

CREATE TRIGGER place_aliases_fts_delete AFTER DELETE ON place_aliases
BEGIN
    UPDATE place_search SET 
        aliases = COALESCE((
            SELECT GROUP_CONCAT(alias_name, ' ')
            FROM place_aliases 
            WHERE master_id = OLD.master_id
        ), '')
    WHERE master_id = OLD.master_id;
END;

-- 5. 既存データでFTSテーブルを初期化
INSERT INTO place_search(master_id, normalized_name, display_name, canonical_name, aliases)
SELECT 
    pm.master_id,
    pm.normalized_name,
    pm.display_name,
    pm.canonical_name,
    COALESCE((
        SELECT GROUP_CONCAT(pa.alias_name, ' ')
        FROM place_aliases pa
        WHERE pa.master_id = pm.master_id
    ), '') as aliases
FROM place_masters pm;

-- 6. 統計・確認クエリ
SELECT 'FTS修正完了統計' as info;
SELECT 
    'place_masters' as table_name,
    COUNT(*) as count
FROM place_masters

UNION ALL

SELECT 
    'place_search' as table_name,
    COUNT(*) as count
FROM place_search

UNION ALL

SELECT 
    'トリガー数' as table_name,
    COUNT(*) as count
FROM sqlite_master 
WHERE type = 'trigger' AND name LIKE '%fts%'; 