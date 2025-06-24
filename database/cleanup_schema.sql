-- データベーススキーマクリーンアップ
-- 不要なテーブルの削除と最適化

-- 1. 現在の状況確認
SELECT 'スキーマクリーンアップ開始' AS status;
SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name;

-- 2. 古いFTS関連テーブルの削除
-- これらは新しいplace_search (FTS5) で代替されるため不要
DROP TABLE IF EXISTS place_search_config;
DROP TABLE IF EXISTS place_search_data;  
DROP TABLE IF EXISTS place_search_docsize;
DROP TABLE IF EXISTS place_search_idx;

-- 3. バックアップテーブルの整理確認
-- authors_backup と works_backup は保持（重要なバックアップ）

-- 4. 必要テーブル・ビューの存在確認
SELECT 'コアテーブル確認' AS check_core;
SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS authors_status
FROM sqlite_master WHERE name = 'authors' AND type = 'table';

SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS works_status  
FROM sqlite_master WHERE name = 'works' AND type = 'table';

SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS sentences_status
FROM sqlite_master WHERE name = 'sentences' AND type = 'table';

SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS place_masters_status
FROM sqlite_master WHERE name = 'place_masters' AND type = 'table';

SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS sentence_places_status
FROM sqlite_master WHERE name = 'sentence_places' AND type = 'table';

SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS place_aliases_status
FROM sqlite_master WHERE name = 'place_aliases' AND type = 'table';

-- 5. ビューの確認
SELECT 'ビュー確認' AS check_views;
SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS places_view_status
FROM sqlite_master WHERE name = 'places' AND type = 'view';

SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS statistics_view_status
FROM sqlite_master WHERE name = 'place_statistics' AND type = 'view';

-- 6. FTS5テーブルの確認
SELECT 'FTS5検索テーブル確認' AS check_fts;
SELECT 
    CASE WHEN COUNT(*) > 0 THEN '✅ 存在' ELSE '❌ 不在' END AS place_search_status
FROM sqlite_master WHERE name = 'place_search' AND type = 'table';

-- 7. 外部キー制約チェック
PRAGMA foreign_key_check;

-- 8. データベース最適化
VACUUM;
ANALYZE;

-- 9. 最終状況確認
SELECT 'クリーンアップ完了' AS final_status;
SELECT '最終テーブル・ビュー一覧:' AS final_list;
SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name;

-- 10. データ確認
SELECT 'データ保持状況:' AS data_status;
SELECT 'authors: ' || COUNT(*) || '件' FROM authors;
SELECT 'works: ' || COUNT(*) || '件' FROM works;
SELECT 'sentences: ' || COUNT(*) || '件' FROM sentences;
SELECT 'place_masters: ' || COUNT(*) || '件' FROM place_masters; 