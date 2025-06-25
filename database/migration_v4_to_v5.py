#!/usr/bin/env python3
"""
文豪地図システム v4.0 → v5.0 データベース移行スクリプト
データベース再設計提案に基づく段階的移行の実装

作成日: 2025年6月25日
"""

import sqlite3
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseMigrationV5:
    """v4からv5への移行を管理するクラス"""
    
    def __init__(self, db_path: str, backup_dir: str = "./backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_path = None
        self.migration_log = []
        
        os.makedirs(backup_dir, exist_ok=True)
        
    def create_backup(self) -> str:
        """既存データベースのバックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bungo_db_v4_backup_{timestamp}.db"
        self.backup_path = os.path.join(self.backup_dir, backup_filename)
        
        shutil.copy2(self.db_path, self.backup_path)
        logger.info(f"✅ バックアップ作成完了: {self.backup_path}")
        return self.backup_path
        
    def execute_migration(self) -> bool:
        """移行の実行"""
        try:
            logger.info("🚀 データベース移行開始")
            
            # 1. バックアップ作成
            self.create_backup()
            
            # 2. 新テーブル作成
            self._create_new_tables()
            
            # 3. データ移行
            self._migrate_data()
            
            # 4. インデックス作成
            self._create_indexes()
            
            logger.info("✅ データベース移行完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ 移行失敗: {e}")
            return False
            
    def _create_new_tables(self):
        """新テーブルの作成"""
        logger.info("📋 新テーブル作成中...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # sectionsテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sections (
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
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (work_id) REFERENCES works(work_id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_section_id) REFERENCES sections(section_id) ON DELETE CASCADE
                )
            """)
            
            # ai_verificationsテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_verifications (
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
                )
            """)
            
            # statistics_cacheテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics_cache (
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
                )
            """)
            
            # processing_logsテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id INTEGER,
                    process_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'started',
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    processing_duration_ms INTEGER,
                    error_message TEXT,
                    statistics JSON,
                    configuration JSON,
                    FOREIGN KEY (work_id) REFERENCES works(work_id) ON DELETE SET NULL
                )
            """)
            
        logger.info("✅ 新テーブル作成完了")
        
    def _migrate_data(self):
        """既存データの移行"""
        logger.info("📦 データ移行中...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 初期統計キャッシュ作成
            global_stats = {
                "migration_version": "5.0",
                "migration_date": datetime.now().isoformat()
            }
            
            cursor.execute("""
                INSERT INTO statistics_cache (cache_key, cache_type, data, expires_at)
                VALUES ('global_stats', 'global_stats', ?, datetime('now', '+7 days'))
            """, (json.dumps(global_stats),))
            
            # 移行ログエントリ作成
            cursor.execute("""
                INSERT INTO processing_logs 
                (process_type, status, statistics, completed_at)
                VALUES ('migration', 'completed', ?, CURRENT_TIMESTAMP)
            """, (json.dumps({"target_version": "5.0"}),))
            
        logger.info("✅ データ移行完了")
        
    def _create_indexes(self):
        """インデックスの作成"""
        logger.info("🔍 インデックス作成中...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_sections_work ON sections(work_id)",
                "CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections(parent_section_id)",
                "CREATE INDEX IF NOT EXISTS idx_ai_verifications_mention ON ai_verifications(place_mention_id)",
                "CREATE INDEX IF NOT EXISTS idx_statistics_cache_key ON statistics_cache(cache_key)",
                "CREATE INDEX IF NOT EXISTS idx_processing_logs_type ON processing_logs(process_type)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                
        logger.info("✅ インデックス作成完了")

def main():
    """メイン実行関数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用法: python migration_v4_to_v5.py <データベースパス>")
        return 1
        
    db_path = sys.argv[1]
    
    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return 1
        
    migrator = DatabaseMigrationV5(db_path)
    success = migrator.execute_migration()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
