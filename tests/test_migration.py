"""
データベース移行テスト v4→v5
作成日: 2025年6月25日
目的: フェーズ1のデータ移行処理の完全テスト
"""

import pytest
import asyncio
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import json

from database.migration_v4_to_v5 import MigrationManager
from database.models import *
from core.models import *

class TestMigrationManager:
    """移行マネージャーのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テスト用の一時データベース"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_migration.db"
        yield str(db_path)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_v4_data(self, temp_db_path):
        """v4形式のサンプルデータを作成"""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # v4スキーマの簡易版作成
        cursor.execute("""
            CREATE TABLE authors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE works (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author_id INTEGER,
                publication_year INTEGER,
                content TEXT,
                FOREIGN KEY (author_id) REFERENCES authors(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE place_masters (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                prefecture TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE sentence_places (
                id INTEGER PRIMARY KEY,
                work_id INTEGER,
                sentence_text TEXT,
                place_name TEXT,
                place_master_id INTEGER,
                sentence_position INTEGER,
                FOREIGN KEY (work_id) REFERENCES works(id),
                FOREIGN KEY (place_master_id) REFERENCES place_masters(id)
            )
        """)
        
        # サンプルデータ挿入
        cursor.execute("INSERT INTO authors (id, name, birth_year, death_year) VALUES (1, '夏目漱石', 1867, 1916)")
        cursor.execute("INSERT INTO works (id, title, author_id, publication_year, content) VALUES (1, 'こころ', 1, 1914, 'sample content')")
        cursor.execute("INSERT INTO place_masters (id, name, latitude, longitude, prefecture) VALUES (1, '東京駅', 35.6812, 139.7671, '東京都')")
        cursor.execute("INSERT INTO sentence_places (id, work_id, sentence_text, place_name, place_master_id, sentence_position) VALUES (1, 1, '東京駅で待ち合わせをした。', '東京駅', 1, 100)")
        
        conn.commit()
        conn.close()
        return temp_db_path
    
    def test_migration_manager_initialization(self, temp_db_path):
        """移行マネージャーの初期化テスト"""
        manager = MigrationManager(
            source_db_path=temp_db_path,
            target_db_path=temp_db_path + "_v5"
        )
        
        assert manager.source_db_path == temp_db_path
        assert manager.target_db_path == temp_db_path + "_v5"
        assert manager.backup_path is None
    
    def test_backup_creation(self, sample_v4_data):
        """バックアップ作成のテスト"""
        manager = MigrationManager(
            source_db_path=sample_v4_data,
            target_db_path=sample_v4_data + "_v5"
        )
        
        # バックアップ作成
        backup_path = manager.create_backup()
        
        assert Path(backup_path).exists()
        assert Path(backup_path).stat().st_size > 0
        
        # バックアップからデータ読み取り確認
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = cursor.fetchone()[0]
        conn.close()
        
        assert author_count == 1
    
    def test_schema_validation(self, sample_v4_data):
        """スキーマ検証のテスト"""
        manager = MigrationManager(
            source_db_path=sample_v4_data,
            target_db_path=sample_v4_data + "_v5"
        )
        
        # v4スキーマの存在確認
        is_valid = manager.validate_v4_schema()
        assert is_valid is True
        
        # 存在しないテーブルのスキーマ確認
        conn = sqlite3.connect(sample_v4_data)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE sentence_places")
        conn.commit()
        conn.close()
        
        is_valid = manager.validate_v4_schema()
        assert is_valid is False
    
    def test_target_schema_creation(self, sample_v4_data):
        """ターゲットスキーマ作成のテスト"""
        target_path = sample_v4_data + "_v5"
        manager = MigrationManager(
            source_db_path=sample_v4_data,
            target_db_path=target_path
        )
        
        # v5スキーマ作成
        manager.create_v5_schema()
        
        # v5テーブルの存在確認
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        
        # 新テーブルの確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sections'")
        assert cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_verifications'")
        assert cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='statistics_cache'")
        assert cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processing_logs'")
        assert cursor.fetchone() is not None
        
        conn.close()


class TestDataMigration:
    """データ移行処理のテスト"""
    
    @pytest.fixture
    def migration_setup(self):
        """移行テストセットアップ"""
        temp_dir = tempfile.mkdtemp()
        source_path = Path(temp_dir) / "source.db"
        target_path = Path(temp_dir) / "target.db"
        
        # サンプルデータ準備
        conn = sqlite3.connect(str(source_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE authors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE works (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author_id INTEGER,
                publication_year INTEGER,
                content TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE place_masters (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                prefecture TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE sentence_places (
                id INTEGER PRIMARY KEY,
                work_id INTEGER,
                sentence_text TEXT,
                place_name TEXT,
                place_master_id INTEGER,
                sentence_position INTEGER,
                confidence_score REAL DEFAULT 0.5
            )
        """)
        
        # テストデータ挿入
        authors_data = [
            (1, '夏目漱石', 1867, 1916),
            (2, '森鴎外', 1862, 1922),
            (3, '芥川龍之介', 1892, 1927)
        ]
        cursor.executemany("INSERT INTO authors VALUES (?, ?, ?, ?)", authors_data)
        
        works_data = [
            (1, 'こころ', 1, 1914, '長い小説の内容...'),
            (2, '舞姫', 2, 1890, '舞姫の内容...'),
            (3, '羅生門', 3, 1915, '羅生門の内容...')
        ]
        cursor.executemany("INSERT INTO works VALUES (?, ?, ?, ?, ?)", works_data)
        
        places_data = [
            (1, '東京駅', 35.6812, 139.7671, '東京都'),
            (2, '新宿', 35.6896, 139.6917, '東京都'),
            (3, '京都', 35.0116, 135.7681, '京都府')
        ]
        cursor.executemany("INSERT INTO place_masters VALUES (?, ?, ?, ?, ?)", places_data)
        
        sentence_places_data = [
            (1, 1, '東京駅で先生と会った。', '東京駅', 1, 100, 0.95),
            (2, 1, '新宿の街を歩いた。', '新宿', 2, 200, 0.85),
            (3, 2, 'ベルリンでエリスと出会った。', 'ベルリン', None, 150, 0.70),
            (4, 3, '京都の古い寺を訪れた。', '京都', 3, 80, 0.90)
        ]
        cursor.executemany("INSERT INTO sentence_places VALUES (?, ?, ?, ?, ?, ?, ?)", sentence_places_data)
        
        conn.commit()
        conn.close()
        
        yield str(source_path), str(target_path)
        shutil.rmtree(temp_dir)
    
    def test_authors_migration(self, migration_setup):
        """著者データ移行のテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        manager.create_v5_schema()
        
        # 著者データ移行
        manager.migrate_authors()
        
        # 移行結果確認
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM authors")
        count = cursor.fetchone()[0]
        assert count == 3
        
        cursor.execute("SELECT name FROM authors WHERE id = 1")
        name = cursor.fetchone()[0]
        assert name == '夏目漱石'
        
        conn.close()
    
    def test_works_migration(self, migration_setup):
        """作品データ移行のテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        manager.create_v5_schema()
        manager.migrate_authors()  # 前提条件
        
        # 作品データ移行
        manager.migrate_works()
        
        # 移行結果確認
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM works")
        count = cursor.fetchone()[0]
        assert count == 3
        
        cursor.execute("SELECT title FROM works WHERE id = 1")
        title = cursor.fetchone()[0]
        assert title == 'こころ'
        
        conn.close()
    
    def test_place_masters_migration(self, migration_setup):
        """地名マスタ移行のテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        manager.create_v5_schema()
        
        # 地名マスタ移行
        manager.migrate_place_masters()
        
        # 移行結果確認
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM place_masters")
        count = cursor.fetchone()[0]
        assert count == 3
        
        cursor.execute("SELECT name, latitude, longitude FROM place_masters WHERE id = 1")
        place_data = cursor.fetchone()
        assert place_data[0] == '東京駅'
        assert abs(place_data[1] - 35.6812) < 0.0001
        assert abs(place_data[2] - 139.7671) < 0.0001
        
        conn.close()
    
    def test_sentence_places_to_place_mentions_migration(self, migration_setup):
        """sentence_places → place_mentions移行のテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        manager.create_v5_schema()
        manager.migrate_authors()
        manager.migrate_works()
        manager.migrate_place_masters()
        
        # sentence_places → place_mentions 移行
        manager.migrate_sentence_places()
        
        # 移行結果確認
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        
        # place_mentionsテーブルの確認
        cursor.execute("SELECT COUNT(*) FROM place_mentions")
        count = cursor.fetchone()[0]
        assert count == 4
        
        # 特定レコードの確認
        cursor.execute("""
            SELECT sentence_text, place_name, confidence_score 
            FROM place_mentions 
            WHERE place_name = '東京駅'
        """)
        mention_data = cursor.fetchone()
        assert mention_data[0] == '東京駅で先生と会った。'
        assert mention_data[1] == '東京駅'
        assert abs(mention_data[2] - 0.95) < 0.01
        
        conn.close()
    
    def test_sections_creation_from_works(self, migration_setup):
        """作品からセクション作成のテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        manager.create_v5_schema()
        manager.migrate_authors()
        manager.migrate_works()
        
        # セクション作成
        manager.create_sections_from_works()
        
        # 結果確認
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        
        # セクション数確認
        cursor.execute("SELECT COUNT(*) FROM sections")
        section_count = cursor.fetchone()[0]
        assert section_count >= 3  # 各作品から最低1つのセクション
        
        # 章レベルのセクション確認
        cursor.execute("""
            SELECT COUNT(*) FROM sections 
            WHERE section_type = 'chapter' AND parent_section_id IS NULL
        """)
        chapter_count = cursor.fetchone()[0]
        assert chapter_count >= 3  # 各作品に対して1つの章
        
        conn.close()


class TestMigrationIntegrity:
    """移行データ整合性のテスト"""
    
    def test_foreign_key_integrity(self, migration_setup):
        """外部キー整合性のテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        manager.run_full_migration()
        
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        
        # place_mentions の work_id 整合性
        cursor.execute("""
            SELECT COUNT(*) FROM place_mentions pm
            LEFT JOIN works w ON pm.work_id = w.id
            WHERE w.id IS NULL
        """)
        orphaned_mentions = cursor.fetchone()[0]
        assert orphaned_mentions == 0
        
        # works の author_id 整合性
        cursor.execute("""
            SELECT COUNT(*) FROM works w
            LEFT JOIN authors a ON w.author_id = a.id
            WHERE a.id IS NULL
        """)
        orphaned_works = cursor.fetchone()[0]
        assert orphaned_works == 0
        
        conn.close()
    
    def test_data_completeness(self, migration_setup):
        """データ完全性のテスト"""
        source_path, target_path = migration_setup
        
        # 移行前のデータ数取得
        source_conn = sqlite3.connect(source_path)
        source_cursor = source_conn.cursor()
        
        source_cursor.execute("SELECT COUNT(*) FROM authors")
        source_authors = source_cursor.fetchone()[0]
        
        source_cursor.execute("SELECT COUNT(*) FROM works")
        source_works = source_cursor.fetchone()[0]
        
        source_cursor.execute("SELECT COUNT(*) FROM place_masters")
        source_places = source_cursor.fetchone()[0]
        
        source_cursor.execute("SELECT COUNT(*) FROM sentence_places")
        source_mentions = source_cursor.fetchone()[0]
        
        source_conn.close()
        
        # 移行実行
        manager = MigrationManager(source_path, target_path)
        manager.run_full_migration()
        
        # 移行後のデータ数確認
        target_conn = sqlite3.connect(target_path)
        target_cursor = target_conn.cursor()
        
        target_cursor.execute("SELECT COUNT(*) FROM authors")
        target_authors = target_cursor.fetchone()[0]
        assert target_authors == source_authors
        
        target_cursor.execute("SELECT COUNT(*) FROM works")
        target_works = target_cursor.fetchone()[0]
        assert target_works == source_works
        
        target_cursor.execute("SELECT COUNT(*) FROM place_masters")
        target_places = target_cursor.fetchone()[0]
        assert target_places == source_places
        
        target_cursor.execute("SELECT COUNT(*) FROM place_mentions")
        target_mentions = target_cursor.fetchone()[0]
        assert target_mentions == source_mentions
        
        target_conn.close()
    
    def test_migration_rollback(self, migration_setup):
        """移行ロールバックのテスト"""
        source_path, target_path = migration_setup
        
        manager = MigrationManager(source_path, target_path)
        
        # バックアップ作成
        backup_path = manager.create_backup()
        
        # 元データベースを変更
        conn = sqlite3.connect(source_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM authors WHERE id = 1")
        conn.commit()
        conn.close()
        
        # ロールバック実行
        manager.rollback_from_backup(backup_path)
        
        # ロールバック確認
        conn = sqlite3.connect(source_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = cursor.fetchone()[0]
        conn.close()
        
        assert author_count == 3  # 元の状態に復元


class TestMigrationPerformance:
    """移行パフォーマンステスト"""
    
    def test_large_dataset_migration(self):
        """大量データ移行のパフォーマンステスト"""
        temp_dir = tempfile.mkdtemp()
        source_path = Path(temp_dir) / "large_source.db"
        target_path = Path(temp_dir) / "large_target.db"
        
        # 大量テストデータ作成
        conn = sqlite3.connect(str(source_path))
        cursor = conn.cursor()
        
        # テーブル作成
        cursor.execute("""
            CREATE TABLE authors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE works (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author_id INTEGER,
                publication_year INTEGER,
                content TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE sentence_places (
                id INTEGER PRIMARY KEY,
                work_id INTEGER,
                sentence_text TEXT,
                place_name TEXT,
                sentence_position INTEGER,
                confidence_score REAL DEFAULT 0.5
            )
        """)
        
        # 大量データ挿入（1000件ずつ）
        import time
        
        # 著者1000人
        authors_data = [(i, f'作家{i}', 1800 + i % 100, 1900 + i % 50) for i in range(1, 1001)]
        cursor.executemany("INSERT INTO authors VALUES (?, ?, ?, ?)", authors_data)
        
        # 作品5000作品
        works_data = [(i, f'作品{i}', (i-1) % 1000 + 1, 1900 + i % 50, f'作品{i}の内容') for i in range(1, 5001)]
        cursor.executemany("INSERT INTO works VALUES (?, ?, ?, ?, ?)", works_data)
        
        # 地名言及10000件
        mentions_data = [
            (i, (i-1) % 5000 + 1, f'文章{i}で地名が言及された。', f'地名{i%100}', i*10, 0.5 + (i % 50) / 100)
            for i in range(1, 10001)
        ]
        cursor.executemany("INSERT INTO sentence_places VALUES (?, ?, ?, ?, ?, ?)", mentions_data)
        
        conn.commit()
        conn.close()
        
        # 移行実行時間測定
        start_time = time.time()
        
        manager = MigrationManager(str(source_path), str(target_path))
        manager.run_full_migration()
        
        end_time = time.time()
        migration_time = end_time - start_time
        
        # パフォーマンス要件確認（10000件を30秒以内）
        assert migration_time < 30.0
        
        # データ数確認
        conn = sqlite3.connect(str(target_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM authors")
        assert cursor.fetchone()[0] == 1000
        
        cursor.execute("SELECT COUNT(*) FROM works")
        assert cursor.fetchone()[0] == 5000
        
        cursor.execute("SELECT COUNT(*) FROM place_mentions")
        assert cursor.fetchone()[0] == 10000
        
        conn.close()
        shutil.rmtree(temp_dir)
    
    def test_migration_memory_usage(self, migration_setup):
        """移行時メモリ使用量のテスト"""
        import psutil
        import os
        
        source_path, target_path = migration_setup
        
        # メモリ使用量監視開始
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 移行実行
        manager = MigrationManager(source_path, target_path)
        manager.run_full_migration()
        
        # メモリ使用量確認
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が100MB以内であることを確認
        assert memory_increase < 100


class TestMigrationErrorHandling:
    """移行エラーハンドリングのテスト"""
    
    def test_corrupted_source_database(self):
        """破損したソースDBの処理テスト"""
        temp_dir = tempfile.mkdtemp()
        source_path = Path(temp_dir) / "corrupted.db"
        target_path = Path(temp_dir) / "target.db"
        
        # 空ファイル（破損DB）を作成
        source_path.touch()
        
        manager = MigrationManager(str(source_path), str(target_path))
        
        # 移行実行（エラーが発生することを期待）
        with pytest.raises(Exception):
            manager.run_full_migration()
        
        shutil.rmtree(temp_dir)
    
    def test_insufficient_disk_space_simulation(self, migration_setup):
        """ディスク不足シミュレーションテスト"""
        source_path, target_path = migration_setup
        
        # 読み取り専用ディレクトリにターゲットを配置
        import stat
        target_dir = Path(target_path).parent
        target_dir.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        
        manager = MigrationManager(source_path, target_path)
        
        # 移行実行（権限エラーが発生することを期待）
        with pytest.raises(PermissionError):
            manager.run_full_migration()
        
        # 権限復元
        target_dir.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)


if __name__ == "__main__":
    # 基本的なテスト実行
    pytest.main([__file__, "-v"])