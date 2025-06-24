-- worksテーブルのクリーン化
-- バックアップは既に works_backup として保存済み

-- 1. 現在の状況確認
SELECT 'クリーン化前の状況' AS status;
SELECT COUNT(*) AS authors_count FROM authors;
SELECT COUNT(*) AS works_count FROM works;
SELECT COUNT(*) AS works_backup_count FROM works_backup;

-- 2. worksテーブルの中身を削除（テーブル構造は保持）
DELETE FROM works;

-- 3. AUTO_INCREMENTリセット
DELETE FROM sqlite_sequence WHERE name='works';

-- 4. 完了確認
SELECT 'worksテーブルクリーン化完了' AS status;
SELECT COUNT(*) AS authors_preserved FROM authors;
SELECT COUNT(*) AS works_cleaned FROM works;
SELECT COUNT(*) AS sentences_count FROM sentences;
SELECT COUNT(*) AS place_masters_count FROM place_masters;

-- 5. 完全クリーン状態の確認
SELECT 'システム状態: 完全クリーン（authorsのみ保持）' AS final_status; 