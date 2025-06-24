#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース初期化スクリプト v2.0
地名マスター優先設計対応

機能:
1. 新しいテーブル構造での初期化
2. 既存データベースの自動マイグレーション
3. インデックス・トリガー・ビューの自動設定
"""

import os
import sys
import sqlite3
from datetime import datetime

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabaseInitializerV2:
    """データベース初期化クラス v2.0"""
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'bungo_map.db')
        self.schema_version = "2.0"
        
    def initialize_database(self, force_recreate: bool = False):
        """データベースの初期化"""
        print("🚀 文豪ゆかり地図システム v4.0 データベース初期化")
        print(f"📁 データベースパス: {self.db_path}")
        print(f"🏗️ スキーマバージョン: {self.schema_version}")
        print("=" * 60)
        
        # データベースディレクトリ作成
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 既存データベースの確認
        db_exists = os.path.exists(self.db_path)
        
        if db_exists and not force_recreate:
            print("📋 既存データベースを検出")
            choice = input("既存データベースをマイグレーションしますか？ (y/n): ")
            if choice.lower() == 'y':
                return self._migrate_existing_database()
            else:
                print("⏭️ 初期化をスキップします")
                return False
        
        if force_recreate and db_exists:
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"💾 既存データベースをバックアップ: {backup_path}")
            import shutil
            shutil.copy2(self.db_path, backup_path)
            os.remove(self.db_path)
        
        # 新規データベース作成
        return self._create_new_database()
    
    def _create_new_database(self):
        """新規データベース作成"""
        print("🆕 新規データベース作成...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 基本テーブル作成
            print("📋 基本テーブル作成...")
            self._create_basic_tables(cursor)
            
            # 2. 地名マスターテーブル作成
            print("🗺️ 地名マスターテーブル作成...")
            self._create_place_master_tables(cursor)
            
            # 3. インデックス作成
            print("⚡ インデックス作成...")
            self._create_indexes(cursor)
            
            # 4. ビュー作成
            print("👁️ ビュー作成...")
            self._create_views(cursor)
            
            # 5. トリガー作成
            print("🔧 トリガー作成...")
            self._create_triggers(cursor)
            
            # 6. メタデータ保存
            print("📝 メタデータ保存...")
            self._save_metadata(cursor)
            
            conn.commit()
            conn.close()
            
            print("✅ 新規データベース作成完了！")
            print(f"📁 場所: {self.db_path}")
            print("🎯 地名マスター優先設計による効率的な処理が可能です")
            
            return True
            
        except Exception as e:
            print(f"❌ データベース作成エラー: {e}")
            return False
    
    def _migrate_existing_database(self):
        """既存データベースのマイグレーション"""
        print("🔄 既存データベースをマイグレーション...")
        
        try:
            from database.migrate_to_v2 import DatabaseMigration
            
            migration = DatabaseMigration()
            success = migration.run_migration()
            
            if success:
                print("✅ マイグレーション完了！")
                print("🎯 地名マスター優先設計に正常に移行されました")
                return True
            else:
                print("❌ マイグレーションに失敗しました")
                return False
                
        except Exception as e:
            print(f"❌ マイグレーションエラー: {e}")
            return False
    
    def _create_basic_tables(self, cursor):
        """基本テーブル作成"""
        # authorsテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_name VARCHAR(255) NOT NULL UNIQUE,
                aozora_author_url VARCHAR(500),
                birth_year INTEGER,
                death_year INTEGER,
                wikipedia_url VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # worksテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS works (
                work_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(500) NOT NULL,
                author_id INTEGER NOT NULL,
                aozora_work_url VARCHAR(500),
                card_id VARCHAR(50),
                publication_year INTEGER,
                content_length INTEGER,
                sentence_count INTEGER,
                processed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES authors(author_id)
            )
        """)
        
        # sentencesテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentences (
                sentence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER NOT NULL,
                sentence_order INTEGER NOT NULL,
                sentence_text TEXT NOT NULL,
                char_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_id) REFERENCES works(work_id),
                UNIQUE(work_id, sentence_order)
            )
        """)
    
    def _create_place_master_tables(self, cursor):
        """地名マスターテーブル作成"""
        # place_mastersテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS place_masters (
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
            )
        """)
        
        # place_aliasesテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS place_aliases (
                alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_id INTEGER NOT NULL,
                alias_name VARCHAR(255) NOT NULL,
                alias_type VARCHAR(50) DEFAULT 'variation',
                confidence FLOAT DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (master_id) REFERENCES place_masters(master_id),
                UNIQUE (master_id, alias_name)
            )
        """)
        
        # sentence_placesテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentence_places (
                relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                master_id INTEGER NOT NULL,
                
                -- 抽出情報
                matched_text VARCHAR(255) NOT NULL,
                start_position INTEGER,
                end_position INTEGER,
                extraction_confidence FLOAT,
                extraction_method VARCHAR(50) DEFAULT 'ginza',
                
                -- AI検証情報
                ai_verified BOOLEAN DEFAULT FALSE,
                ai_confidence FLOAT,
                ai_verification_date DATETIME,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
                FOREIGN KEY (master_id) REFERENCES place_masters(master_id),
                UNIQUE (sentence_id, master_id, matched_text)
            )
        """)
    
    def _create_indexes(self, cursor):
        """インデックス作成"""
        indexes = [
            # authorsテーブル
            "CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(author_name)",
            
            # worksテーブル
            "CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id)",
            "CREATE INDEX IF NOT EXISTS idx_works_title ON works(title)",
            
            # sentencesテーブル
            "CREATE INDEX IF NOT EXISTS idx_sentences_work ON sentences(work_id)",
            "CREATE INDEX IF NOT EXISTS idx_sentences_order ON sentences(work_id, sentence_order)",
            
            # place_mastersテーブル
            "CREATE INDEX IF NOT EXISTS idx_place_masters_normalized ON place_masters(normalized_name)",
            "CREATE INDEX IF NOT EXISTS idx_place_masters_display ON place_masters(display_name)",
            "CREATE INDEX IF NOT EXISTS idx_place_masters_type ON place_masters(place_type)",
            "CREATE INDEX IF NOT EXISTS idx_place_masters_validation ON place_masters(validation_status)",
            "CREATE INDEX IF NOT EXISTS idx_place_masters_usage ON place_masters(usage_count)",
            
            # place_aliasesテーブル
            "CREATE INDEX IF NOT EXISTS idx_place_aliases_name ON place_aliases(alias_name)",
            "CREATE INDEX IF NOT EXISTS idx_place_aliases_master ON place_aliases(master_id)",
            
            # sentence_placesテーブル
            "CREATE INDEX IF NOT EXISTS idx_sentence_places_sentence ON sentence_places(sentence_id)",
            "CREATE INDEX IF NOT EXISTS idx_sentence_places_master ON sentence_places(master_id)",
            "CREATE INDEX IF NOT EXISTS idx_sentence_places_method ON sentence_places(extraction_method)"
        ]
        
        for index in indexes:
            cursor.execute(index)
    
    def _create_views(self, cursor):
        """ビュー作成"""
        # 互換性のためのplacesビュー
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS places AS
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
            WHERE pm.validation_status != 'rejected'
        """)
        
        # 地名統計ビュー
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS place_statistics AS
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
            GROUP BY pm.master_id
        """)
    
    def _create_triggers(self, cursor):
        """トリガー作成"""
        # place_mastersのupdated_at自動更新
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS place_masters_update_timestamp
            AFTER UPDATE ON place_masters
            BEGIN
                UPDATE place_masters 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE master_id = NEW.master_id;
            END
        """)
        
        # 地名使用統計の自動更新
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_place_usage_stats
            AFTER INSERT ON sentence_places
            BEGIN
                UPDATE place_masters 
                SET 
                    usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP,
                    first_used_at = COALESCE(first_used_at, CURRENT_TIMESTAMP)
                WHERE master_id = NEW.master_id;
            END
        """)
    
    def _save_metadata(self, cursor):
        """メタデータ保存"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metadata (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        metadata = [
            ('schema_version', self.schema_version),
            ('created_at', datetime.now().isoformat()),
            ('system_type', '地名マスター優先設計'),
            ('description', '文豪ゆかり地図システム v4.0')
        ]
        
        for key, value in metadata:
            cursor.execute("""
                INSERT OR REPLACE INTO system_metadata (key, value)
                VALUES (?, ?)
            """, (key, value))
    
    def check_database_status(self):
        """データベース状況確認"""
        if not os.path.exists(self.db_path):
            print("❌ データベースが存在しません")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # スキーマバージョン確認
            cursor.execute("""
                SELECT value FROM system_metadata 
                WHERE key = 'schema_version'
            """)
            
            version_result = cursor.fetchone()
            current_version = version_result[0] if version_result else "不明"
            
            # テーブル確認
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            # 統計情報
            statistics = {}
            for table in ['authors', 'works', 'sentences', 'place_masters', 'sentence_places']:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    statistics[table] = cursor.fetchone()[0]
            
            conn.close()
            
            print("📊 データベース状況:")
            print(f"  📁 パス: {self.db_path}")
            print(f"  🏗️ スキーマバージョン: {current_version}")
            print(f"  📋 テーブル数: {len(tables)}")
            print(f"  📊 データ統計:")
            for table, count in statistics.items():
                print(f"    {table}: {count:,}件")
            
            # 地名マスター確認
            if 'place_masters' in tables:
                cursor = sqlite3.connect(self.db_path).cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as geocoded,
                        COUNT(CASE WHEN validation_status = 'validated' THEN 1 END) as validated
                    FROM place_masters
                """)
                master_stats = cursor.fetchone()
                print(f"  🗺️ 地名マスター:")
                print(f"    総数: {master_stats[0]:,}")
                print(f"    ジオコーディング済み: {master_stats[1]:,}")
                print(f"    検証済み: {master_stats[2]:,}")
            
            return True
            
        except Exception as e:
            print(f"❌ データベース確認エラー: {e}")
            return False


def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='データベース初期化ツール v2.0')
    parser.add_argument('--force', action='store_true', help='既存データベースを強制再作成')
    parser.add_argument('--status', action='store_true', help='データベース状況確認のみ')
    parser.add_argument('--migrate', action='store_true', help='マイグレーションのみ実行')
    
    args = parser.parse_args()
    
    initializer = DatabaseInitializerV2()
    
    if args.status:
        initializer.check_database_status()
    elif args.migrate:
        initializer._migrate_existing_database()
    else:
        initializer.initialize_database(force_recreate=args.force)


if __name__ == "__main__":
    main() 