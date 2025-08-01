-- 文豪ゆかり地図システムv4 選択的データベースリセット
-- authorsとworksテーブルを保持し、地名関連テーブルを初期化

-- 1. 作者・作品テーブルのバックアップ（念のため）
DROP TABLE IF EXISTS authors_backup;
CREATE TABLE authors_backup AS SELECT * FROM authors;

DROP TABLE IF EXISTS works_backup;
CREATE TABLE works_backup AS SELECT * FROM works;

-- 2. 地名関連テーブルの削除
DROP TABLE IF EXISTS sentence_places;
DROP TABLE IF EXISTS sentence_places_backup;
DROP TABLE IF EXISTS sentence_places_new;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS places_backup;
DROP TABLE IF EXISTS place_masters;
DROP TABLE IF EXISTS place_masters_new;
DROP TABLE IF EXISTS place_aliases;
DROP TABLE IF EXISTS place_aliases_new;

-- 3. 検索・統計関連テーブルの削除
DROP TABLE IF EXISTS place_search;
DROP TABLE IF EXISTS place_search_config;
DROP TABLE IF EXISTS place_search_data;
DROP TABLE IF EXISTS place_search_docsize;
DROP TABLE IF EXISTS place_search_idx;
DROP TABLE IF EXISTS place_statistics;

-- 4. sentencesテーブルも初期化（作品に紐づくため）
DROP TABLE IF EXISTS sentences;

-- 5. 新しいv2スキーマの適用

-- sentencesテーブル再作成
CREATE TABLE sentences (
    sentence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    sentence_order INTEGER NOT NULL,
    sentence_text TEXT NOT NULL,
    paragraph_number INTEGER,
    character_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (work_id) REFERENCES works(work_id),
    UNIQUE (work_id, sentence_order)
);

CREATE INDEX idx_sentences_work ON sentences(work_id);
CREATE INDEX idx_sentences_order ON sentences(sentence_order);

-- 地名マスターテーブル
CREATE TABLE place_masters (
    master_id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255),
    
    -- ジオコーディング情報
    latitude FLOAT,
    longitude FLOAT,
    geocoding_source VARCHAR(100),
    geocoding_confidence FLOAT,
    geocoding_timestamp DATETIME,
    
    -- 地名メタデータ
    place_type VARCHAR(50),
    prefecture VARCHAR(100),
    municipality VARCHAR(100),
    district VARCHAR(100),
    
    -- 使用統計
    usage_count INTEGER DEFAULT 0,
    first_used_at DATETIME,
    last_used_at DATETIME,
    
    -- 管理情報
    validation_status VARCHAR(20) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_place_masters_normalized ON place_masters(normalized_name);
CREATE INDEX idx_place_masters_display ON place_masters(display_name);
CREATE INDEX idx_place_masters_type ON place_masters(place_type);
CREATE INDEX idx_place_masters_validation ON place_masters(validation_status);

-- 地名異表記テーブル
CREATE TABLE place_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id INTEGER NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50),
    confidence FLOAT DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (master_id) REFERENCES place_masters(master_id),
    UNIQUE (master_id, alias_name)
);

CREATE INDEX idx_place_aliases_name ON place_aliases(alias_name);
CREATE INDEX idx_place_aliases_master ON place_aliases(master_id);

-- センテンス地名関係テーブル
CREATE TABLE sentence_places (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sentence_id INTEGER NOT NULL,
    master_id INTEGER NOT NULL,
    
    -- 抽出情報
    matched_text VARCHAR(255) NOT NULL,
    start_position INTEGER,
    end_position INTEGER,
    extraction_confidence FLOAT,
    extraction_method VARCHAR(50),
    
    -- AI検証情報
    ai_verified BOOLEAN DEFAULT FALSE,
    ai_confidence FLOAT,
    ai_verification_date DATETIME,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
    FOREIGN KEY (master_id) REFERENCES place_masters(master_id),
    UNIQUE (sentence_id, master_id, matched_text)
);

CREATE INDEX idx_sentence_places_sentence ON sentence_places(sentence_id);
CREATE INDEX idx_sentence_places_master ON sentence_places(master_id);
CREATE INDEX idx_sentence_places_method ON sentence_places(extraction_method);

-- 既存コード互換性ビュー
CREATE VIEW places AS
SELECT 
    'pm_' || pm.master_id AS place_id,
    pm.display_name AS place_name,
    pm.canonical_name,
    pm.latitude,
    pm.longitude,
    pm.place_type,
    pm.geocoding_confidence AS confidence,
    pm.prefecture,
    pm.municipality,
    pm.district,
    pm.usage_count AS mention_count,
    pm.geocoding_source AS source_system,
    pm.created_at,
    pm.updated_at,
    pm.master_id
FROM place_masters pm
WHERE pm.validation_status != 'rejected';

-- 統計ビュー
CREATE VIEW place_statistics AS
SELECT 
    pm.master_id,
    pm.normalized_name,
    pm.display_name,
    pm.place_type,
    pm.prefecture,
    pm.usage_count,
    COUNT(sp.relation_id) AS mention_count,
    COUNT(DISTINCT sp.sentence_id) AS sentence_count,
    COUNT(DISTINCT s.work_id) AS work_count,
    COUNT(DISTINCT w.author_id) AS author_count,
    pm.validation_status
FROM place_masters pm
LEFT JOIN sentence_places sp ON pm.master_id = sp.master_id
LEFT JOIN sentences s ON sp.sentence_id = s.sentence_id
LEFT JOIN works w ON s.work_id = w.work_id
GROUP BY pm.master_id;

-- 全文検索テーブル
CREATE VIRTUAL TABLE place_search USING fts5(
    master_id UNINDEXED,
    normalized_name,
    display_name,
    canonical_name,
    aliases,
    content=''
);

-- FTSトリガー
CREATE TRIGGER place_masters_fts_insert AFTER INSERT ON place_masters
BEGIN
    INSERT INTO place_search(master_id, normalized_name, display_name, canonical_name)
    VALUES (NEW.master_id, NEW.normalized_name, NEW.display_name, NEW.canonical_name);
END;

CREATE TRIGGER place_masters_fts_update AFTER UPDATE ON place_masters
BEGIN
    UPDATE place_search SET 
        normalized_name = NEW.normalized_name,
        display_name = NEW.display_name,
        canonical_name = NEW.canonical_name
    WHERE master_id = NEW.master_id;
END;

CREATE TRIGGER place_masters_fts_delete AFTER DELETE ON place_masters
BEGIN
    DELETE FROM place_search WHERE master_id = OLD.master_id;
END;

-- 6. 完了メッセージ
SELECT 'データベース選択的リセット完了' AS status;
SELECT COUNT(*) AS preserved_authors FROM authors;
SELECT COUNT(*) AS preserved_works FROM works; 