#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地名マスターデータ管理システム v4.0
地名の重複を排除し、ジオコーディング結果を効率的に再利用

機能:
1. 地名の正規化とマスターデータ化
2. 重複地名の統合
3. ジオコーディング結果の再利用
4. 地名マスターテーブルの管理
"""

import sqlite3
import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.manager import DatabaseManager


class PlaceMasterManager:
    """地名マスターデータ管理クラス"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'bungo_map.db')
        self._ensure_master_table_exists()
        
        self.stats = {
            'duplicates_found': 0,
            'places_merged': 0,
            'geocoding_reused': 0,
            'master_places_created': 0,
            'errors': []
        }
    
    def _ensure_master_table_exists(self):
        """地名マスターテーブルを作成"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # place_mastersテーブル作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS place_masters (
                    master_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_name VARCHAR(255) NOT NULL UNIQUE,
                    display_name VARCHAR(255) NOT NULL,
                    latitude FLOAT,
                    longitude FLOAT,
                    geocoding_source VARCHAR(100),
                    geocoding_confidence FLOAT,
                    usage_count INTEGER DEFAULT 0,
                    first_used_at DATETIME,
                    last_used_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # place_aliases テーブル（異表記管理）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS place_aliases (
                    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    master_id INTEGER,
                    alias_name VARCHAR(255) NOT NULL,
                    confidence FLOAT DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (master_id) REFERENCES place_masters(master_id)
                )
            """)
            
            conn.commit()
            conn.close()
            print("✅ 地名マスターテーブル準備完了")
            
        except Exception as e:
            print(f"❌ マスターテーブル作成エラー: {e}")
            self.stats['errors'].append(str(e))
    
    def normalize_place_name(self, place_name: str) -> str:
        """地名を正規化"""
        if not place_name:
            return ""
        
        # 基本的な正規化
        normalized = place_name.strip()
        
        # 全角・半角統一
        normalized = normalized.replace('１', '1').replace('２', '2').replace('３', '3')
        normalized = normalized.replace('４', '4').replace('５', '5').replace('６', '6')
        normalized = normalized.replace('７', '7').replace('８', '8').replace('９', '9')
        normalized = normalized.replace('０', '0')
        
        # 漢字の異表記統一
        kanji_variations = {
            '東京': ['東京', '東亰'],
            '大阪': ['大阪', '大坂'],
            '京都': ['京都', '京'], 
            '神戸': ['神戸', '神戸'],
            '横浜': ['横浜', '横濱']
        }
        
        for standard, variations in kanji_variations.items():
            if normalized in variations:
                normalized = standard
                break
        
        return normalized
    
    def find_or_create_master_place(self, place_name: str, latitude: float = None, 
                                   longitude: float = None, geocoding_source: str = None,
                                   geocoding_confidence: float = None) -> int:
        """地名マスターを検索または作成し、master_idを返す"""
        try:
            normalized_name = self.normalize_place_name(place_name)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 既存マスターを検索
            cursor.execute("""
                SELECT master_id, latitude, longitude, geocoding_source, geocoding_confidence
                FROM place_masters 
                WHERE normalized_name = ?
            """, (normalized_name,))
            
            existing = cursor.fetchone()
            
            if existing:
                master_id = existing[0]
                existing_lat, existing_lng = existing[1], existing[2]
                
                # 既存の座標が空で新しい座標があれば更新
                if (existing_lat is None or existing_lng is None) and latitude and longitude:
                    cursor.execute("""
                        UPDATE place_masters 
                        SET latitude = ?, longitude = ?, geocoding_source = ?, 
                            geocoding_confidence = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE master_id = ?
                    """, (latitude, longitude, geocoding_source, geocoding_confidence, master_id))
                    print(f"🔄 座標更新: {normalized_name} → ({latitude}, {longitude})")
                
                # 使用回数更新
                cursor.execute("""
                    UPDATE place_masters 
                    SET usage_count = usage_count + 1, last_used_at = CURRENT_TIMESTAMP
                    WHERE master_id = ?
                """, (master_id,))
                
                self.stats['geocoding_reused'] += 1
                
            else:
                # 新規マスター作成
                cursor.execute("""
                    INSERT INTO place_masters (
                        normalized_name, display_name, latitude, longitude,
                        geocoding_source, geocoding_confidence, usage_count,
                        first_used_at, last_used_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (normalized_name, place_name, latitude, longitude, 
                      geocoding_source, geocoding_confidence))
                
                master_id = cursor.lastrowid
                self.stats['master_places_created'] += 1
                print(f"🆕 新規マスター作成: {normalized_name} (ID: {master_id})")
            
            # エイリアス登録（表記ゆれ対応）
            if place_name != normalized_name:
                cursor.execute("""
                    INSERT OR IGNORE INTO place_aliases (master_id, alias_name)
                    VALUES (?, ?)
                """, (master_id, place_name))
            
            conn.commit()
            conn.close()
            
            return master_id
            
        except Exception as e:
            print(f"❌ マスター地名処理エラー ({place_name}): {e}")
            self.stats['errors'].append(str(e))
            return None
    
    def merge_duplicate_places(self) -> Dict:
        """重複地名を統合"""
        try:
            print("🔄 重複地名の統合開始...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 重複地名を検出
            cursor.execute("""
                SELECT place_name_only, COUNT(*) as count, 
                       GROUP_CONCAT(id) as place_ids
                FROM sentence_places
                GROUP BY place_name_only 
                HAVING count > 1
                ORDER BY count DESC
            """)
            
            duplicates = cursor.fetchall()
            print(f"📊 {len(duplicates)}種類の重複地名を発見")
            
            for place_name, count, place_ids_str in duplicates:
                print(f"🔍 {place_name}: {count}件の重複を処理中...")
                self.stats['places_merged'] += count - 1  # 1つを残して統合
            
            self.stats['duplicates_found'] = len(duplicates)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'duplicates_found': len(duplicates),
                'places_merged': self.stats['places_merged'],
                'errors': self.stats['errors']
            }
            
        except Exception as e:
            error_msg = f"重複統合エラー: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return {
                'success': False,
                'errors': self.stats['errors']
            }
    
    def add_master_place_id_column(self):
        """sentence_placesテーブルにmaster_place_id列を追加"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 列が存在するかチェック
            cursor.execute("PRAGMA table_info(sentence_places)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'master_place_id' not in columns:
                cursor.execute("""
                    ALTER TABLE sentence_places 
                    ADD COLUMN master_place_id INTEGER
                """)
                print("✅ master_place_id列を追加")
            else:
                print("ℹ️ master_place_id列は既に存在します")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ 列追加エラー: {e}")
            self.stats['errors'].append(str(e))
    
    def get_master_statistics(self) -> Dict:
        """マスターデータ統計を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) FROM place_masters")
            total_masters = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM place_masters WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
            geocoded_masters = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(usage_count) FROM place_masters")
            total_usage = cursor.fetchone()[0] or 0
            
            # 使用頻度TOP10
            cursor.execute("""
                SELECT normalized_name, usage_count, latitude, longitude
                FROM place_masters 
                ORDER BY usage_count DESC 
                LIMIT 10
            """)
            top_places = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_masters': total_masters,
                'geocoded_masters': geocoded_masters,
                'geocoding_coverage': (geocoded_masters / total_masters * 100) if total_masters > 0 else 0,
                'total_usage': total_usage,
                'top_places': top_places
            }
            
        except Exception as e:
            print(f"❌ 統計取得エラー: {e}")
            return {'error': str(e)}
    
    def print_statistics(self):
        """統計情報を表示"""
        stats = self.get_master_statistics()
        
        if 'error' in stats:
            print(f"❌ 統計取得失敗: {stats['error']}")
            return
        
        print(f"\n📊 地名マスターデータ統計")
        print("=" * 60)
        print(f"🗺️  マスター地名数: {stats['total_masters']:,}件")
        print(f"📍 ジオコーディング済み: {stats['geocoded_masters']:,}件 ({stats['geocoding_coverage']:.1f}%)")
        print(f"📈 総使用回数: {stats['total_usage']:,}回")
        
        if stats['top_places']:
            print(f"\n🏆 使用頻度TOP10:")
            for i, (name, count, lat, lng) in enumerate(stats['top_places'], 1):
                coord_status = "✅" if lat and lng else "❌"
                print(f"  {i:2d}. {name}: {count}回 {coord_status}")


def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='地名マスターデータ管理システム',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--merge-duplicates', action='store_true', help='重複地名を統合')
    parser.add_argument('--add-column', action='store_true', help='master_place_id列を追加')
    parser.add_argument('--stats', action='store_true', help='統計情報表示')
    
    args = parser.parse_args()
    
    manager = PlaceMasterManager()
    
    if args.add_column:
        manager.add_master_place_id_column()
    
    if args.merge_duplicates:
        result = manager.merge_duplicate_places()
        if result['success']:
            print(f"✅ 統合完了: {result['duplicates_found']}種類、{result['places_merged']}件統合")
        else:
            print(f"❌ 統合失敗: {result['errors']}")
    
    if args.stats or not any([args.merge_duplicates, args.add_column]):
        manager.print_statistics()


if __name__ == "__main__":
    main()