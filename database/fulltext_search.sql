-- ========================================
-- 全文検索最適化スクリプト v5.0
-- 作成日: 2025年6月25日
-- 目的: FTS5を活用した高速全文検索システム
-- ========================================

-- ----------------------------------------
-- セクション内容の全文検索テーブル
-- ----------------------------------------

-- sectionsテーブル用のFTS5テーブル（階層的文書構造対応）
DROP TABLE IF EXISTS sections_fts;
CREATE VIRTUAL TABLE sections_fts USING fts5(
    title,           -- セクションタイトル
    content,         -- セクション内容
    section_type,    -- セクション種別（chapter/paragraph/sentence）
    work_title,      -- 作品タイトル
    author_name,     -- 作家名
    
    -- FTS5設定
    content='sections',  -- 元テーブル
    content_rowid='id'   -- ROWIDマッピング
);

-- ----------------------------------------
-- place_mastersの全文検索テーブル
-- ----------------------------------------

-- 地名マスター用のFTS5テーブル（地名検索最適化）
DROP TABLE IF EXISTS place_masters_fts;
CREATE VIRTUAL TABLE place_masters_fts USING fts5(
    standard_name,   -- 標準地名
    name_reading,    -- 読み方
    name_variants,   -- 異表記（JSON配列を文字列として格納）
    prefecture,      -- 都道府県
    city,           -- 市区町村
    description,    -- 説明
    
    -- FTS5設定
    content='place_masters',
    content_rowid='id'
);

-- ----------------------------------------
-- 作品内容の全文検索テーブル  
-- ----------------------------------------

-- works テーブル用のFTS5テーブル（作品メタデータ検索）
DROP TABLE IF EXISTS works_fts;
CREATE VIRTUAL TABLE works_fts USING fts5(
    title,          -- 作品タイトル
    author_name,    -- 作家名
    genre,          -- ジャンル
    description,    -- 説明
    
    content='works',
    content_rowid='id'
);

-- ----------------------------------------
-- 文章内容の全文検索テーブル
-- ----------------------------------------

-- sentences テーブル用のFTS5テーブル（文章内容検索）
DROP TABLE IF EXISTS sentences_fts;
CREATE VIRTUAL TABLE sentences_fts USING fts5(
    content,        -- 文章内容
    work_title,     -- 作品タイトル  
    author_name,    -- 作家名
    chapter_title,  -- 章タイトル
    
    content='sentences',
    content_rowid='id'
);

-- ----------------------------------------
-- 検索結果ランキング用カスタム関数
-- ----------------------------------------

-- FTS5でのランキング改善用（BM25スコア調整）
-- rank列でスコアリング、より関連性の高い結果を上位に

-- ----------------------------------------
-- FTS5自動更新トリガー（sections）
-- ----------------------------------------

-- sections_fts 挿入トリガー
CREATE TRIGGER sections_fts_insert AFTER INSERT ON sections 
BEGIN
    INSERT INTO sections_fts(
        rowid, title, content, section_type, work_title, author_name
    ) 
    SELECT 
        NEW.id,
        NEW.title,
        NEW.content,
        NEW.section_type,
        w.title,
        a.name
    FROM works w
    JOIN authors a ON w.author_id = a.id
    WHERE w.id = NEW.work_id;
END;

-- sections_fts 更新トリガー
CREATE TRIGGER sections_fts_update AFTER UPDATE ON sections
BEGIN
    -- 古いレコードを削除
    DELETE FROM sections_fts WHERE rowid = OLD.id;
    
    -- 新しいレコードを挿入
    INSERT INTO sections_fts(
        rowid, title, content, section_type, work_title, author_name
    )
    SELECT 
        NEW.id,
        NEW.title,
        NEW.content,
        NEW.section_type,
        w.title,
        a.name
    FROM works w
    JOIN authors a ON w.author_id = a.id
    WHERE w.id = NEW.work_id;
END;

-- sections_fts 削除トリガー
CREATE TRIGGER sections_fts_delete AFTER DELETE ON sections
BEGIN
    DELETE FROM sections_fts WHERE rowid = OLD.id;
END;

-- ----------------------------------------
-- FTS5自動更新トリガー（place_masters）
-- ----------------------------------------

CREATE TRIGGER place_masters_fts_insert AFTER INSERT ON place_masters
BEGIN
    INSERT INTO place_masters_fts(
        rowid, standard_name, name_reading, name_variants, 
        prefecture, city, description
    ) VALUES (
        NEW.id, NEW.standard_name, NEW.name_reading, 
        COALESCE(NEW.name_variants, ''), NEW.prefecture, 
        NEW.city, NEW.description
    );
END;

CREATE TRIGGER place_masters_fts_update AFTER UPDATE ON place_masters
BEGIN
    DELETE FROM place_masters_fts WHERE rowid = OLD.id;
    INSERT INTO place_masters_fts(
        rowid, standard_name, name_reading, name_variants,
        prefecture, city, description
    ) VALUES (
        NEW.id, NEW.standard_name, NEW.name_reading,
        COALESCE(NEW.name_variants, ''), NEW.prefecture,
        NEW.city, NEW.description
    );
END;

CREATE TRIGGER place_masters_fts_delete AFTER DELETE ON place_masters
BEGIN
    DELETE FROM place_masters_fts WHERE rowid = OLD.id;
END;

-- ----------------------------------------
-- FTS5自動更新トリガー（works）
-- ----------------------------------------

CREATE TRIGGER works_fts_insert AFTER INSERT ON works
BEGIN
    INSERT INTO works_fts(rowid, title, author_name, genre, description)
    SELECT NEW.id, NEW.title, a.name, NEW.genre, NEW.description
    FROM authors a WHERE a.id = NEW.author_id;
END;

CREATE TRIGGER works_fts_update AFTER UPDATE ON works
BEGIN
    DELETE FROM works_fts WHERE rowid = OLD.id;
    INSERT INTO works_fts(rowid, title, author_name, genre, description)
    SELECT NEW.id, NEW.title, a.name, NEW.genre, NEW.description
    FROM authors a WHERE a.id = NEW.author_id;
END;

CREATE TRIGGER works_fts_delete AFTER DELETE ON works
BEGIN
    DELETE FROM works_fts WHERE rowid = OLD.id;
END;

-- ----------------------------------------
-- FTS5自動更新トリガー（sentences）
-- ----------------------------------------

CREATE TRIGGER sentences_fts_insert AFTER INSERT ON sentences
BEGIN
    INSERT INTO sentences_fts(rowid, content, work_title, author_name, chapter_title)
    SELECT 
        NEW.id, 
        NEW.content,
        w.title,
        a.name,
        COALESCE(s.title, '')
    FROM works w
    JOIN authors a ON w.author_id = a.id
    LEFT JOIN sections s ON s.work_id = w.id 
        AND s.section_type = 'chapter'
        AND NEW.character_position >= s.character_position
    WHERE w.id = NEW.work_id
    ORDER BY s.character_position DESC
    LIMIT 1;
END;

CREATE TRIGGER sentences_fts_update AFTER UPDATE ON sentences
BEGIN
    DELETE FROM sentences_fts WHERE rowid = OLD.id;
    INSERT INTO sentences_fts(rowid, content, work_title, author_name, chapter_title)
    SELECT 
        NEW.id,
        NEW.content,
        w.title,
        a.name,
        COALESCE(s.title, '')
    FROM works w
    JOIN authors a ON w.author_id = a.id
    LEFT JOIN sections s ON s.work_id = w.id
        AND s.section_type = 'chapter'
        AND NEW.character_position >= s.character_position
    WHERE w.id = NEW.work_id
    ORDER BY s.character_position DESC
    LIMIT 1;
END;

CREATE TRIGGER sentences_fts_delete AFTER DELETE ON sentences
BEGIN
    DELETE FROM sentences_fts WHERE rowid = OLD.id;
END;

-- ----------------------------------------
-- 検索最適化ビュー
-- ----------------------------------------

-- 統合全文検索ビュー（複数テーブル横断検索）
CREATE VIEW unified_search_view AS
SELECT 
    'section' as result_type,
    sections_fts.rowid as id,
    sections_fts.title as title,
    sections_fts.content as content,
    sections_fts.work_title,
    sections_fts.author_name,
    sections_fts.section_type as category,
    rank as relevance_score
FROM sections_fts
WHERE sections_fts MATCH ?

UNION ALL

SELECT
    'place' as result_type,
    place_masters_fts.rowid as id,
    place_masters_fts.standard_name as title,
    place_masters_fts.description as content,
    place_masters_fts.prefecture || place_masters_fts.city as work_title,
    '' as author_name,
    'place' as category,
    rank as relevance_score
FROM place_masters_fts
WHERE place_masters_fts MATCH ?

UNION ALL

SELECT
    'work' as result_type,
    works_fts.rowid as id,
    works_fts.title as title,
    works_fts.description as content,
    works_fts.title as work_title,
    works_fts.author_name,
    works_fts.genre as category,
    rank as relevance_score
FROM works_fts
WHERE works_fts MATCH ?

ORDER BY relevance_score DESC;

-- ----------------------------------------
-- FTS5設定の最適化
-- ----------------------------------------

-- FTS5の設定変更（検索精度向上）
-- rank関数のカスタマイズは、検索クエリ実行時に指定

-- 例：bm25(sections_fts, 1.2, 0.75) -- BM25パラメータ調整
-- 例：highlight(sections_fts, 1, '<mark>', '</mark>') -- ハイライト

-- ----------------------------------------
-- インデックス再構築用スクリプト
-- ----------------------------------------

-- FTS5テーブルの再構築（大量データ投入後に実行）
-- INSERT INTO sections_fts(sections_fts) VALUES('rebuild');
-- INSERT INTO place_masters_fts(place_masters_fts) VALUES('rebuild');
-- INSERT INTO works_fts(works_fts) VALUES('rebuild');
-- INSERT INTO sentences_fts(sentences_fts) VALUES('rebuild');

-- FTS5統計情報の更新
-- INSERT INTO sections_fts(sections_fts) VALUES('optimize');

-- ----------------------------------------
-- 検索パフォーマンス測定用クエリ例
-- ----------------------------------------

/*
-- 複合検索（作家名 + 地名）
SELECT * FROM sections_fts 
WHERE sections_fts MATCH 'author_name:夏目 AND content:東京'
ORDER BY rank;

-- フレーズ検索（完全一致）
SELECT * FROM sections_fts
WHERE sections_fts MATCH '"坊っちゃん"'
ORDER BY rank;

-- ワイルドカード検索（前方一致）
SELECT * FROM place_masters_fts
WHERE place_masters_fts MATCH 'standard_name:東京*'
ORDER BY rank;

-- ブール検索（OR条件）
SELECT * FROM works_fts
WHERE works_fts MATCH 'title:(小説 OR 物語)'
ORDER BY rank;

-- 近接検索（単語間距離指定）
SELECT * FROM sentences_fts
WHERE sentences_fts MATCH 'content:NEAR(夏目 漱石, 5)'
ORDER BY rank;
*/

-- ----------------------------------------
-- 検索API用補助関数（ビュー）
-- ----------------------------------------

-- 人気検索キーワード統計ビュー
CREATE VIEW popular_search_terms AS
SELECT 
    search_term,
    search_count,
    last_searched_at
FROM (
    -- 実際の検索ログテーブルがあれば、そこから集計
    -- 今回は例として作成
    SELECT 'placeholder' as search_term, 0 as search_count, datetime('now') as last_searched_at
) 
WHERE search_count > 0
ORDER BY search_count DESC, last_searched_at DESC
LIMIT 100;

-- 関連検索語推奨ビュー  
CREATE VIEW related_search_suggestions AS
SELECT 
    original_term,
    suggested_term,
    similarity_score
FROM (
    -- 検索語の類似性分析結果
    -- 実装時には機械学習ベースの推奨システムを統合
    SELECT 'placeholder' as original_term, 'suggestion' as suggested_term, 0.0 as similarity_score
)
WHERE similarity_score > 0.3
ORDER BY similarity_score DESC; 