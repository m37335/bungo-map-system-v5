#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地名マスター管理システム v2.0
地名抽出時点からマスター管理を行う効率的なシステム

機能:
1. 地名抽出と同時にマスター検索・登録
2. 重複ジオコーディング完全回避
3. AI検証統合
4. 高速地名検索・正規化
"""

import sqlite3
import re
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import sys
import os

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.manager import DatabaseManager
from ai.geocoding import GeocodingEngine
from ai.llm import LLMClient


class PlaceMasterManagerV2:
    """地名マスター管理システム v2.0"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'bungo_map.db')
        self.llm_client = LLMClient()
        self.geocoder = GeocodingEngine(self.llm_client)
        
        # 正規化ルール
        self.normalization_rules = {
            # 全角・半角統一
            '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
            '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
            
            # 漢字異表記統一
            '東亰': '東京', '大坂': '大阪', '横濱': '横浜',
            
            # 地名接尾辞正規化
            '県': '', '府': '', '市': '', '区': '', '町': '', '村': ''
        }
        
        # キャッシュ
        self._master_cache = {}
        self._alias_cache = {}
        
        self.stats = {
            'cache_hits': 0,
            'new_masters': 0,
            'geocoding_skipped': 0,
            'geocoding_executed': 0,
            'ai_validations': 0,
            'processing_time': 0
        }
    
    def normalize_place_name(self, place_name: str) -> str:
        """地名の正規化（改良版）"""
        if not place_name:
            return ""
        
        normalized = place_name.strip()
        
        # 基本的な正規化
        for old, new in self.normalization_rules.items():
            normalized = normalized.replace(old, new)
        
        # 特殊パターンの処理
        # 「〜の」「〜に」等の助詞除去
        normalized = re.sub(r'[のにへでを]$', '', normalized)
        
        # 重複文字の統一
        normalized = re.sub(r'([山川島])\1+', r'\1', normalized)
        
        return normalized
    
    def find_master_by_name(self, place_name: str) -> Optional[int]:
        """地名でマスターIDを検索（キャッシュ対応）"""
        # キャッシュチェック
        if place_name in self._master_cache:
            self.stats['cache_hits'] += 1
            return self._master_cache[place_name]
        
        normalized = self.normalize_place_name(place_name)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 正規化名での直接検索
            cursor.execute("""
                SELECT master_id FROM place_masters 
                WHERE normalized_name = ? AND validation_status != 'rejected'
            """, (normalized,))
            
            result = cursor.fetchone()
            if result:
                master_id = result[0]
                self._master_cache[place_name] = master_id
                conn.close()
                return master_id
            
            # 2. 表示名での検索
            cursor.execute("""
                SELECT master_id FROM place_masters 
                WHERE display_name = ? AND validation_status != 'rejected'
            """, (place_name,))
            
            result = cursor.fetchone()
            if result:
                master_id = result[0]
                self._master_cache[place_name] = master_id
                conn.close()
                return master_id
            
            # 3. エイリアスでの検索
            cursor.execute("""
                SELECT pm.master_id FROM place_masters pm
                JOIN place_aliases pa ON pm.master_id = pa.master_id
                WHERE pa.alias_name = ? AND pm.validation_status != 'rejected'
            """, (place_name,))
            
            result = cursor.fetchone()
            if result:
                master_id = result[0]
                self._master_cache[place_name] = master_id
                conn.close()
                return master_id
            
            # 4. 部分マッチ検索（曖昧検索）
            cursor.execute("""
                SELECT master_id FROM place_masters 
                WHERE (normalized_name LIKE ? OR display_name LIKE ?)
                AND validation_status != 'rejected'
                ORDER BY 
                    CASE WHEN normalized_name = ? THEN 1 ELSE 2 END,
                    LENGTH(normalized_name)
                LIMIT 1
            """, (f'%{normalized}%', f'%{place_name}%', normalized))
            
            result = cursor.fetchone()
            if result:
                master_id = result[0]
                self._master_cache[place_name] = master_id
                conn.close()
                return master_id
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"❌ マスター検索エラー ({place_name}): {e}")
            return None
    
    def create_master_place(self, place_name: str, 
                           ai_context: str = None,
                           should_geocode: bool = True) -> Optional[int]:
        """新規マスター地名作成"""
        try:
            normalized = self.normalize_place_name(place_name)
            
            # AI検証（オプション）
            if ai_context and not self.ai_validate_place_name(place_name, ai_context):
                print(f"⚠️ AI検証により地名として認識されませんでした: {place_name}")
                return None
            
            # マスター作成
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO place_masters (
                    normalized_name, display_name, canonical_name,
                    validation_status, first_used_at, last_used_at, usage_count
                ) VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
            """, (normalized, place_name, place_name))
            
            master_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"🆕 新規マスター地名作成: {place_name} (ID: {master_id})")
            self.stats['new_masters'] += 1
            
            # キャッシュ更新
            self._master_cache[place_name] = master_id
            
            # ジオコーディング実行（新規のみ）
            if should_geocode:
                self.geocode_master_place(master_id, place_name, ai_context)
            
            return master_id
            
        except Exception as e:
            print(f"❌ マスター地名作成エラー ({place_name}): {e}")
            return None
    
    def geocode_master_place(self, master_id: int, place_name: str, context: str = None):
        """マスター地名のジオコーディング"""
        try:
            print(f"🌍 ジオコーディング実行: {place_name}")
            
            # ジオコーディング実行
            geocoding_result = self.geocoder.geocode_place(place_name)
            
            if geocoding_result and geocoding_result.latitude and geocoding_result.longitude:
                # 結果をマスターテーブルに保存
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE place_masters SET
                        latitude = ?, longitude = ?,
                        geocoding_source = ?, geocoding_confidence = ?,
                        geocoding_timestamp = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE master_id = ?
                """, (
                    geocoding_result.latitude,
                    geocoding_result.longitude,
                    geocoding_result.source,
                    geocoding_result.confidence,
                    master_id
                ))
                
                conn.commit()
                conn.close()
                
                print(f"✅ ジオコーディング完了: {place_name} → ({geocoding_result.latitude}, {geocoding_result.longitude})")
                self.stats['geocoding_executed'] += 1
            else:
                print(f"⚠️ ジオコーディング失敗: {place_name}")
                
        except Exception as e:
            print(f"❌ ジオコーディングエラー ({place_name}): {e}")
    
    def ai_validate_place_name(self, place_name: str, context: str) -> bool:
        """AI による地名検証"""
        try:
            self.stats['ai_validations'] += 1
            
            # AI検証実行
            ai_result = self.geocoder.analyze_with_llm(place_name, context)
            
            if ai_result and isinstance(ai_result, dict):
                is_place = ai_result.get('is_place_name', False)
                confidence = ai_result.get('confidence', 0.0)
                
                print(f"🤖 AI検証: {place_name} → {is_place} (信頼度: {confidence:.2f})")
                
                # 信頼度0.7以上で地名として判定
                return is_place and confidence >= 0.7
            
            # AI検証失敗時は地名として扱う（保守的）
            return True
            
        except Exception as e:
            print(f"⚠️ AI検証エラー ({place_name}): {e}")
            return True  # エラー時は地名として扱う
    
    def extract_and_register_place(self, place_text: str, sentence_id: int, 
                                  sentence_text: str = None,
                                  extraction_method: str = 'ginza') -> Optional[int]:
        """地名抽出からマスター登録まで一括処理"""
        start_time = time.time()
        
        try:
            # 1. マスター検索
            master_id = self.find_master_by_name(place_text)
            
            if master_id:
                # 既存マスター使用
                self.update_master_usage(master_id)
                self.stats['geocoding_skipped'] += 1
                print(f"🎯 既存マスター使用: {place_text} (ID: {master_id})")
            else:
                # 新規マスター作成
                master_id = self.create_master_place(
                    place_text, 
                    ai_context=sentence_text,
                    should_geocode=True
                )
                
                if not master_id:
                    return None
            
            # 2. センテンス関係登録
            self.register_sentence_place_relation(
                sentence_id=sentence_id,
                master_id=master_id,
                matched_text=place_text,
                extraction_method=extraction_method
            )
            
            processing_time = time.time() - start_time
            self.stats['processing_time'] += processing_time
            
            return master_id
            
        except Exception as e:
            print(f"❌ 地名登録エラー ({place_text}): {e}")
            return None
    
    def update_master_usage(self, master_id: int):
        """マスター地名の使用統計更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE place_masters SET
                    usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE master_id = ?
            """, (master_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ 使用統計更新エラー (master_id: {master_id}): {e}")
    
    def register_sentence_place_relation(self, sentence_id: int, master_id: int,
                                       matched_text: str, extraction_method: str = 'ginza'):
        """センテンス地名関係の登録"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # センテンス情報とコンテキスト取得
            cursor.execute("""
                SELECT s.sentence_text, s.work_id, s.sentence_order,
                       w.title, a.author_name, a.birth_year, a.death_year
                FROM sentences s
                JOIN works w ON s.work_id = w.work_id
                JOIN authors a ON w.author_id = a.author_id
                WHERE s.sentence_id = ?
            """, (sentence_id,))
            
            sentence_info = cursor.fetchone()
            if not sentence_info:
                print(f"⚠️ センテンス情報が見つかりません: sentence_id={sentence_id}")
                return
            
            sentence_text, work_id, sentence_order, work_title, author_name, birth_year, death_year = sentence_info
            
            # 前後２文ずつ取得
            cursor.execute("""
                SELECT GROUP_CONCAT(sentence_text, '') 
                FROM sentences 
                WHERE work_id = ? AND sentence_order >= ? AND sentence_order < ?
                ORDER BY sentence_order
            """, (work_id, sentence_order - 2, sentence_order))
            context_before_result = cursor.fetchone()
            context_before = context_before_result[0] if context_before_result and context_before_result[0] else ""
            
            cursor.execute("""
                SELECT GROUP_CONCAT(sentence_text, '') 
                FROM sentences 
                WHERE work_id = ? AND sentence_order > ? AND sentence_order <= ?
                ORDER BY sentence_order
            """, (work_id, sentence_order, sentence_order + 2))
            context_after_result = cursor.fetchone()
            context_after = context_after_result[0] if context_after_result and context_after_result[0] else ""
            
            # matched_textは地名のみにする（place_mastersから取得）
            cursor.execute("SELECT display_name FROM place_masters WHERE master_id = ?", (master_id,))
            place_result = cursor.fetchone()
            place_text = place_result[0] if place_result else matched_text
            
            # 文中位置計算（地名の位置）
            position_in_sentence = sentence_text.find(place_text) if sentence_text else -1
            
            cursor.execute("""
                INSERT OR REPLACE INTO sentence_places (
                    sentence_id, master_id, matched_text, place_name, full_sentence,
                    extraction_method, extraction_confidence,
                    context_before, context_after,
                    author_name, author_birth_year, author_death_year,
                    work_title, position_in_sentence,
                    quality_score, relevance_score, verification_status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0.8, ?, ?, ?, ?, ?, ?, ?, 0.8, 0.8, 'auto', CURRENT_TIMESTAMP)
            """, (sentence_id, master_id, place_text, place_text, sentence_text, extraction_method,
                  context_before, context_after, author_name, birth_year, death_year,
                  work_title, position_in_sentence))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ センテンス関係登録エラー: {e}")
    
    def get_master_statistics(self) -> Dict:
        """マスター統計情報取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_masters,
                    COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as geocoded_masters,
                    COUNT(CASE WHEN validation_status = 'validated' THEN 1 END) as validated_masters,
                    SUM(usage_count) as total_usage
                FROM place_masters
            """)
            
            basic_stats = cursor.fetchone()
            
            # 地名タイプ別統計
            cursor.execute("""
                SELECT place_type, COUNT(*) as count
                FROM place_masters
                WHERE place_type IS NOT NULL
                GROUP BY place_type
                ORDER BY count DESC
            """)
            
            type_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_masters': basic_stats[0],
                'geocoded_masters': basic_stats[1],
                'validated_masters': basic_stats[2],
                'total_usage': basic_stats[3],
                'geocoding_rate': (basic_stats[1] / basic_stats[0] * 100) if basic_stats[0] > 0 else 0,
                'type_distribution': dict(type_stats),
                'cache_stats': {
                    'cache_hits': self.stats['cache_hits'],
                    'new_masters': self.stats['new_masters'],
                    'geocoding_skipped': self.stats['geocoding_skipped'],
                    'geocoding_executed': self.stats['geocoding_executed'],
                    'ai_validations': self.stats['ai_validations'],
                    'avg_processing_time': self.stats['processing_time'] / max(1, self.stats['new_masters'])
                }
            }
            
        except Exception as e:
            print(f"❌ 統計情報取得エラー: {e}")
            return {}
    
    def print_statistics(self):
        """統計情報の表示"""
        stats = self.get_master_statistics()
        
        print("\n" + "="*60)
        print("📊 地名マスター統計")
        print("="*60)
        print(f"総マスター数: {stats.get('total_masters', 0):,}")
        print(f"ジオコーディング済み: {stats.get('geocoded_masters', 0):,} ({stats.get('geocoding_rate', 0):.1f}%)")
        print(f"検証済み: {stats.get('validated_masters', 0):,}")
        print(f"総使用回数: {stats.get('total_usage', 0):,}")
        
        cache_stats = stats.get('cache_stats', {})
        print(f"\n⚡ パフォーマンス:")
        print(f"キャッシュヒット: {cache_stats.get('cache_hits', 0):,}")
        print(f"新規作成: {cache_stats.get('new_masters', 0):,}")
        print(f"ジオコーディングスキップ: {cache_stats.get('geocoding_skipped', 0):,}")
        print(f"ジオコーディング実行: {cache_stats.get('geocoding_executed', 0):,}")
        print(f"平均処理時間: {cache_stats.get('avg_processing_time', 0):.3f}秒")


def main():
    """テスト実行"""
    manager = PlaceMasterManagerV2()
    
    # テスト地名
    test_places = ["東京", "京都", "大阪", "横浜", "東京", "神戸"]
    
    print("🧪 地名マスター管理システム v2.0 テスト")
    
    for place in test_places:
        print(f"\n📍 テスト: {place}")
        master_id = manager.extract_and_register_place(
            place_text=place,
            sentence_id=1,  # ダミー
            sentence_text=f"{place}に行った。",
            extraction_method='test'
        )
        print(f"結果: master_id = {master_id}")
    
    manager.print_statistics()


if __name__ == "__main__":
    main() 