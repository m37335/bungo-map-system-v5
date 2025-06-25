#!/usr/bin/env python3
"""
v5.0移行テストスクリプト
新テーブル、モデル、基本機能のテスト

作成日: 2025年6月25日
"""

import os
import sys
import tempfile
import sqlite3
import json
from datetime import datetime

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_schema_creation():
    """スキーマ作成テスト"""
    print("🧪 スキーマ作成テスト開始...")
    
    # 一時データベース作成
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # schema_v5.sqlの内容を実行
            schema_sql = """
            CREATE TABLE sections (
                section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER NOT NULL,
                section_type VARCHAR(20) NOT NULL CHECK (section_type IN ('chapter', 'paragraph', 'sentence')),
                parent_section_id INTEGER,
                section_number INTEGER,
                title VARCHAR(200),
                content TEXT,
                character_position INTEGER,
                character_length INTEGER,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE ai_verifications (
                verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_mention_id INTEGER NOT NULL,
                ai_model VARCHAR(50) NOT NULL,
                verification_type VARCHAR(50) NOT NULL,
                input_context TEXT,
                ai_response JSON,
                confidence_score DECIMAL(3, 2),
                is_valid_place BOOLEAN,
                reasoning TEXT,
                verification_status VARCHAR(20) DEFAULT 'pending',
                processing_time_ms INTEGER,
                api_cost DECIMAL(8, 6),
                verified_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE statistics_cache (
                cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key VARCHAR(200) NOT NULL UNIQUE,
                cache_type VARCHAR(50) NOT NULL,
                entity_id INTEGER,
                data JSON NOT NULL,
                expires_at DATETIME,
                hit_count INTEGER DEFAULT 0,
                last_accessed DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE processing_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER,
                process_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'started',
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                processing_duration_ms INTEGER,
                error_message TEXT,
                statistics JSON,
                configuration JSON
            );
            """
            
            cursor.executescript(schema_sql)
            
            # テーブル存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['sections', 'ai_verifications', 'statistics_cache', 'processing_logs']
            for table in expected_tables:
                assert table in tables, f"テーブル {table} が作成されていません"
                
            print("✅ スキーマ作成テスト成功")
            
    finally:
        # 一時ファイル削除
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_models_import():
    """モデルインポートテスト"""
    print("🧪 モデルインポートテスト開始...")
    
    try:
        # データベースモデル
        from database.models import Section, AIVerification, StatisticsCache, ProcessingLog
        print("✅ データベースモデルインポート成功")
        
        # Pydanticモデル
        from core.models import (
            SectionBase, SectionCreate, SectionResponse,
            AIVerificationBase, AIVerificationCreate, AIVerificationResponse,
            StatisticsCacheBase, StatisticsCacheCreate, StatisticsCacheResponse,
            ProcessingLogBase, ProcessingLogCreate, ProcessingLogResponse,
            SectionType, VerificationType, VerificationStatus, CacheType, ProcessType, ProcessStatus
        )
        print("✅ Pydanticモデルインポート成功")
        
        # Enumテスト
        assert SectionType.CHAPTER == "chapter"
        assert VerificationType.PLACE_VALIDATION == "place_validation"
        assert VerificationStatus.VERIFIED == "verified"
        print("✅ Enum値テスト成功")
        
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        raise

def test_data_operations():
    """データ操作テスト"""
    print("🧪 データ操作テスト開始...")
    
    # 一時データベース作成
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # テーブル作成
            cursor.execute("""
                CREATE TABLE statistics_cache (
                    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key VARCHAR(200) NOT NULL UNIQUE,
                    cache_type VARCHAR(50) NOT NULL,
                    entity_id INTEGER,
                    data JSON NOT NULL,
                    expires_at DATETIME,
                    hit_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # データ挿入テスト
            test_data = {"test": "value", "count": 123}
            cursor.execute("""
                INSERT INTO statistics_cache (cache_key, cache_type, data)
                VALUES (?, ?, ?)
            """, ("test_key", "global_stats", json.dumps(test_data)))
            
            # データ取得テスト
            cursor.execute("SELECT cache_key, cache_type, data FROM statistics_cache WHERE cache_key = ?", ("test_key",))
            row = cursor.fetchone()
            
            assert row is not None, "データが挿入されていません"
            assert row[0] == "test_key", "cache_keyが正しくありません"
            assert row[1] == "global_stats", "cache_typeが正しくありません"
            
            retrieved_data = json.loads(row[2])
            assert retrieved_data == test_data, "JSONデータが正しく保存・取得されていません"
            
            print("✅ データ操作テスト成功")
            
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_migration_script():
    """移行スクリプトテスト"""
    print("🧪 移行スクリプトテスト開始...")
    
    try:
        from database.migration_v4_to_v5 import DatabaseMigrationV5
        
        # 一時データベース作成
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
            
        # 基本テーブル作成（移行元）
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE authors (
                    author_id INTEGER PRIMARY KEY,
                    author_name VARCHAR(255)
                )
            """)
            cursor.execute("INSERT INTO authors (author_name) VALUES ('テスト作者')")
        
        # 移行テスト
        migrator = DatabaseMigrationV5(db_path, tempfile.mkdtemp())
        
        # バックアップ作成テスト
        backup_path = migrator.create_backup()
        assert os.path.exists(backup_path), "バックアップが作成されていません"
        
        # 新テーブル作成テスト
        migrator._create_new_tables()
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'sections' in tables, "sectionsテーブルが作成されていません"
            assert 'ai_verifications' in tables, "ai_verificationsテーブルが作成されていません"
            
        print("✅ 移行スクリプトテスト成功")
        
        # クリーンアップ
        os.unlink(db_path)
        os.unlink(backup_path)
        
    except Exception as e:
        print(f"❌ 移行スクリプトテストエラー: {e}")
        raise

def main():
    """テスト実行"""
    print("🚀 v5.0移行テスト開始")
    print("=" * 50)
    
    try:
        test_schema_creation()
        test_models_import()
        test_data_operations()
        test_migration_script()
        
        print("=" * 50)
        print("✅ 全テスト成功！v5.0移行準備完了")
        return 0
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main()) 