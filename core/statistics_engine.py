#!/usr/bin/env python3
"""
統計エンジン (StatisticsEngine)
統計情報の生成・キャッシュ・無効化を管理する

作成日: 2025年6月25日
"""

import json
import sqlite3
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    cache_key: str
    cache_type: str
    entity_id: Optional[int]
    data: Dict[str, Any]
    expires_at: Optional[datetime]
    hit_count: int = 0

class StatisticsEngine:
    """統計エンジン"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # キャッシュ有効期限設定（秒）
        self.cache_ttl = {
            'global_stats': 3600,      # 1時間
            'author_stats': 1800,      # 30分
            'work_stats': 1800,        # 30分
            'place_stats': 900,        # 15分
            'search_results': 300      # 5分
        }
    
    def generate_global_statistics(self) -> Dict[str, Any]:
        """グローバル統計の生成"""
        logger.info("グローバル統計生成開始")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) FROM authors")
            total_authors = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM works")
            total_works = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sentences")
            total_sentences = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM place_masters")
            total_places = cursor.fetchone()[0]
            
            # AI検証統計（新テーブルが存在する場合）
            total_verifications = 0
            verification_success_rate = 0
            try:
                cursor.execute("SELECT COUNT(*) FROM ai_verifications")
                total_verifications = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM ai_verifications 
                    WHERE verification_status = 'verified'
                """)
                verified_count = cursor.fetchone()[0]
                
                if total_verifications > 0:
                    verification_success_rate = verified_count / total_verifications
                    
            except sqlite3.OperationalError:
                logger.info("ai_verificationsテーブルが存在しません")
            
            # 地名統計
            cursor.execute("""
                SELECT 
                    AVG(CASE WHEN ai_verified = 1 THEN ai_confidence ELSE 0 END),
                    COUNT(CASE WHEN ai_verified = 1 THEN 1 END)
                FROM sentence_places
            """)
            avg_confidence, verified_mentions = cursor.fetchone()
            
            # 作品・作者別統計
            cursor.execute("""
                SELECT 
                    AVG(sentence_count),
                    AVG(place_count)
                FROM (
                    SELECT 
                        w.work_id,
                        COUNT(DISTINCT s.sentence_id) as sentence_count,
                        COUNT(DISTINCT sp.master_id) as place_count
                    FROM works w
                    LEFT JOIN sentences s ON w.work_id = s.work_id
                    LEFT JOIN sentence_places sp ON s.sentence_id = sp.sentence_id
                    GROUP BY w.work_id
                )
            """)
            avg_sentences_per_work, avg_places_per_work = cursor.fetchone()
            
            stats = {
                'generation_time': datetime.now().isoformat(),
                'database_info': {
                    'total_authors': total_authors,
                    'total_works': total_works,
                    'total_sentences': total_sentences,
                    'total_places': total_places,
                    'total_verifications': total_verifications
                },
                'averages': {
                    'sentences_per_work': round(avg_sentences_per_work or 0, 2),
                    'places_per_work': round(avg_places_per_work or 0, 2),
                    'verification_confidence': round(avg_confidence or 0, 2)
                },
                'quality_metrics': {
                    'verification_success_rate': round(verification_success_rate, 3),
                    'verified_mentions': verified_mentions,
                    'coverage_rate': round((verified_mentions / max(total_sentences, 1)), 3)
                },
                'system_health': {
                    'cache_hit_rate': self._calculate_cache_hit_rate(),
                    'average_response_time': 120  # ms（実装後に実測値を使用）
                }
            }
        
        logger.info("グローバル統計生成完了")
        return stats
    
    def generate_author_statistics(self, author_id: int) -> Dict[str, Any]:
        """作者統計の生成"""
        logger.info(f"作者統計生成開始: author_id={author_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本情報
            cursor.execute("""
                SELECT author_name, birth_year, death_year
                FROM authors WHERE author_id = ?
            """, (author_id,))
            
            author_info = cursor.fetchone()
            if not author_info:
                return {}
            
            author_name, birth_year, death_year = author_info
            
            # 作品統計
            cursor.execute("""
                SELECT 
                    COUNT(*) as work_count,
                    SUM(sentence_count) as total_sentences,
                    SUM(place_count) as total_places,
                    AVG(sentence_count) as avg_sentences_per_work,
                    AVG(place_count) as avg_places_per_work
                FROM (
                    SELECT 
                        w.work_id,
                        COUNT(DISTINCT s.sentence_id) as sentence_count,
                        COUNT(DISTINCT sp.master_id) as place_count
                    FROM works w
                    LEFT JOIN sentences s ON w.work_id = s.work_id
                    LEFT JOIN sentence_places sp ON s.sentence_id = sp.sentence_id
                    WHERE w.author_id = ?
                    GROUP BY w.work_id
                ) work_stats
            """, (author_id,))
            
            work_stats = cursor.fetchone()
            
            # 地名使用傾向
            cursor.execute("""
                SELECT 
                    pm.place_type,
                    COUNT(*) as usage_count
                FROM sentence_places sp
                JOIN sentences s ON sp.sentence_id = s.sentence_id
                JOIN works w ON s.work_id = w.work_id
                JOIN place_masters pm ON sp.master_id = pm.master_id
                WHERE w.author_id = ? AND pm.place_type IS NOT NULL
                GROUP BY pm.place_type
                ORDER BY usage_count DESC
                LIMIT 10
            """, (author_id,))
            
            place_type_usage = [
                {'place_type': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]
            
            # よく使用する地名
            cursor.execute("""
                SELECT 
                    pm.display_name,
                    COUNT(*) as usage_count,
                    pm.prefecture
                FROM sentence_places sp
                JOIN sentences s ON sp.sentence_id = s.sentence_id
                JOIN works w ON s.work_id = w.work_id
                JOIN place_masters pm ON sp.master_id = pm.master_id
                WHERE w.author_id = ?
                GROUP BY pm.master_id
                ORDER BY usage_count DESC
                LIMIT 10
            """, (author_id,))
            
            frequent_places = [
                {
                    'place_name': row[0],
                    'usage_count': row[1],
                    'prefecture': row[2]
                }
                for row in cursor.fetchall()
            ]
            
            stats = {
                'author_info': {
                    'author_id': author_id,
                    'author_name': author_name,
                    'birth_year': birth_year,
                    'death_year': death_year,
                    'generation_time': datetime.now().isoformat()
                },
                'work_statistics': {
                    'total_works': work_stats[0] or 0,
                    'total_sentences': work_stats[1] or 0,
                    'total_places': work_stats[2] or 0,
                    'avg_sentences_per_work': round(work_stats[3] or 0, 2),
                    'avg_places_per_work': round(work_stats[4] or 0, 2)
                },
                'place_usage_analysis': {
                    'place_type_distribution': place_type_usage,
                    'frequent_places': frequent_places
                }
            }
        
        logger.info(f"作者統計生成完了: author_id={author_id}")
        return stats
    
    def generate_place_statistics(self, place_id: int) -> Dict[str, Any]:
        """地名統計の生成"""
        logger.info(f"地名統計生成開始: place_id={place_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本情報
            cursor.execute("""
                SELECT display_name, normalized_name, place_type, 
                       prefecture, latitude, longitude, usage_count
                FROM place_masters WHERE master_id = ?
            """, (place_id,))
            
            place_info = cursor.fetchone()
            if not place_info:
                return {}
            
            # 使用作者・作品統計
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT w.author_id) as author_count,
                    COUNT(DISTINCT w.work_id) as work_count,
                    COUNT(DISTINCT s.sentence_id) as sentence_count,
                    COUNT(*) as mention_count
                FROM sentence_places sp
                JOIN sentences s ON sp.sentence_id = s.sentence_id
                JOIN works w ON s.work_id = w.work_id
                WHERE sp.master_id = ?
            """, (place_id,))
            
            usage_stats = cursor.fetchone()
            
            # 時代別使用傾向
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN w.publication_year < 1900 THEN '明治以前'
                        WHEN w.publication_year < 1926 THEN '大正'
                        WHEN w.publication_year < 1950 THEN '昭和前期'
                        WHEN w.publication_year < 1989 THEN '昭和後期'
                        ELSE '平成以降'
                    END as era,
                    COUNT(*) as usage_count
                FROM sentence_places sp
                JOIN sentences s ON sp.sentence_id = s.sentence_id
                JOIN works w ON s.work_id = w.work_id
                WHERE sp.master_id = ? AND w.publication_year IS NOT NULL
                GROUP BY era
                ORDER BY 
                    CASE era
                        WHEN '明治以前' THEN 1
                        WHEN '大正' THEN 2
                        WHEN '昭和前期' THEN 3
                        WHEN '昭和後期' THEN 4
                        WHEN '平成以降' THEN 5
                    END
            """, (place_id,))
            
            era_usage = [
                {'era': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]
            
            stats = {
                'place_info': {
                    'place_id': place_id,
                    'display_name': place_info[0],
                    'normalized_name': place_info[1],
                    'place_type': place_info[2],
                    'prefecture': place_info[3],
                    'coordinates': {
                        'latitude': place_info[4],
                        'longitude': place_info[5]
                    } if place_info[4] and place_info[5] else None,
                    'generation_time': datetime.now().isoformat()
                },
                'usage_statistics': {
                    'total_authors': usage_stats[0],
                    'total_works': usage_stats[1],
                    'total_sentences': usage_stats[2],
                    'total_mentions': usage_stats[3]
                },
                'temporal_analysis': {
                    'era_distribution': era_usage
                }
            }
        
        logger.info(f"地名統計生成完了: place_id={place_id}")
        return stats
    
    def cache_statistics(self, cache_key: str, cache_type: str, 
                        data: Dict[str, Any], entity_id: Optional[int] = None) -> bool:
        """統計のキャッシュ"""
        try:
            expires_at = datetime.now() + timedelta(seconds=self.cache_ttl.get(cache_type, 3600))
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 既存キャッシュを削除
                cursor.execute("DELETE FROM statistics_cache WHERE cache_key = ?", (cache_key,))
                
                # 新しいキャッシュを挿入
                cursor.execute("""
                    INSERT INTO statistics_cache 
                    (cache_key, cache_type, entity_id, data, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (cache_key, cache_type, entity_id, json.dumps(data), expires_at))
                
            logger.info(f"統計キャッシュ保存: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
            return False
    
    def get_cached_statistics(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """キャッシュされた統計の取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT data, expires_at, hit_count
                    FROM statistics_cache 
                    WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > ?)
                """, (cache_key, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    # ヒット数更新
                    cursor.execute("""
                        UPDATE statistics_cache 
                        SET hit_count = hit_count + 1, last_accessed = ?
                        WHERE cache_key = ?
                    """, (datetime.now(), cache_key))
                    
                    data = json.loads(result[0])
                    logger.info(f"キャッシュヒット: {cache_key}")
                    return data
                
            return None
            
        except Exception as e:
            logger.error(f"キャッシュ取得エラー: {e}")
            return None
    
    def invalidate_cache(self, cache_type: Optional[str] = None, 
                        entity_id: Optional[int] = None) -> int:
        """キャッシュの無効化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if cache_type and entity_id:
                    cursor.execute("""
                        DELETE FROM statistics_cache 
                        WHERE cache_type = ? AND entity_id = ?
                    """, (cache_type, entity_id))
                elif cache_type:
                    cursor.execute("""
                        DELETE FROM statistics_cache WHERE cache_type = ?
                    """, (cache_type,))
                else:
                    cursor.execute("DELETE FROM statistics_cache")
                
                deleted_count = cursor.rowcount
                logger.info(f"キャッシュ無効化: {deleted_count}件")
                return deleted_count
                
        except Exception as e:
            logger.error(f"キャッシュ無効化エラー: {e}")
            return 0
    
    def _calculate_cache_hit_rate(self) -> float:
        """キャッシュヒット率の計算"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT AVG(hit_count) FROM statistics_cache 
                    WHERE hit_count > 0
                """)
                
                result = cursor.fetchone()
                return round(result[0] or 0, 3)
                
        except Exception as e:
            logger.error(f"キャッシュヒット率計算エラー: {e}")
            return 0.0
    
    def cleanup_expired_cache(self) -> int:
        """期限切れキャッシュのクリーンアップ"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM statistics_cache 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now(),))
                
                deleted_count = cursor.rowcount
                logger.info(f"期限切れキャッシュクリーンアップ: {deleted_count}件")
                return deleted_count
                
        except Exception as e:
            logger.error(f"キャッシュクリーンアップエラー: {e}")
            return 0

def main():
    """テスト実行"""
    import tempfile
    import os
    
    # テスト用データベース作成
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    # 基本テーブル作成
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE statistics_cache (
                cache_id INTEGER PRIMARY KEY,
                cache_key VARCHAR(200) UNIQUE,
                cache_type VARCHAR(50),
                entity_id INTEGER,
                data JSON,
                expires_at DATETIME,
                hit_count INTEGER DEFAULT 0,
                last_accessed DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    engine = StatisticsEngine(db_path)
    
    # テストデータ
    test_stats = {"test": "data", "count": 123}
    
    # キャッシュテスト
    success = engine.cache_statistics("test_key", "global_stats", test_stats)
    print(f"キャッシュ保存: {success}")
    
    cached_data = engine.get_cached_statistics("test_key")
    print(f"キャッシュ取得: {cached_data}")
    
    # クリーンアップ
    os.unlink(db_path)
    print("テスト完了")

if __name__ == "__main__":
    main()
