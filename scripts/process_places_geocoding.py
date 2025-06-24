#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地名抽出→ジオコーディング統合処理システム
梶井基次郎のセンテンスから地名を抽出し、座標変換まで実行

Features:
- Legacy統合Enhanced地名抽出器使用（既存実装活用）
- 高精度地名抽出（4,281件有名地名対応）
- 座標データベース統合ジオコーディング
"""

import sys
import sqlite3
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

# 地名抽出器（既存実装を活用）
from extractors.enhanced_place_extractor_v2 import EnhancedPlaceExtractorV2

from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class GeocodingResult:
    """ジオコーディング結果"""
    place_name: str
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: float
    source: str
    prefecture: Optional[str] = None
    city: Optional[str] = None

class SimpleGeocoder:
    """シンプルなジオコーディングシステム"""
    
    def __init__(self):
        # 高信頼度都市データベース（実証済み）
        self.high_confidence_places = {
            # 東京詳細地名
            "本郷": (35.7081, 139.7619, "東京都文京区", 0.95),
            "神田": (35.6918, 139.7648, "東京都千代田区", 0.95),
            "青山": (35.6736, 139.7263, "東京都港区", 0.95),
            "麻布": (35.6581, 139.7414, "東京都港区", 0.95),
            "両国": (35.6967, 139.7933, "東京都墨田区", 0.95),
            "赤坂": (35.6745, 139.7378, "東京都港区", 0.95),
            "日本橋": (35.6813, 139.7744, "東京都中央区", 0.95),
            "築地": (35.6654, 139.7707, "東京都中央区", 0.95),
            "新橋": (35.6665, 139.7580, "東京都港区", 0.95),
            "上野": (35.7136, 139.7772, "東京都台東区", 0.95),
            "銀座": (35.6762, 139.7649, "東京都中央区", 0.95),
            "新宿": (35.6896, 139.7006, "東京都新宿区", 0.95),
            "渋谷": (35.6598, 139.7006, "東京都渋谷区", 0.95),
            "浅草": (35.7148, 139.7967, "東京都台東区", 0.95),
            "品川": (35.6284, 139.7387, "東京都港区", 0.95),
            "池袋": (35.7298, 139.7101, "東京都豊島区", 0.95),
            
            # 京都詳細地名
            "伏見": (34.9393, 135.7578, "京都府京都市伏見区", 0.98),
            "嵐山": (35.0088, 135.6761, "京都府京都市右京区", 0.98),
            "清水": (34.9948, 135.7849, "京都府京都市東山区", 0.92),
            "祇園": (35.0037, 135.7744, "京都府京都市東山区", 0.98),
            "宇治": (34.8842, 135.7991, "京都府宇治市", 0.95),
            "京都": (35.0116, 135.7681, "京都府京都市", 0.95),
            
            # 大阪主要地名
            "難波": (34.6659, 135.5020, "大阪府大阪市浪速区", 0.92),
            "梅田": (34.7010, 135.4962, "大阪府大阪市北区", 0.92),
            "心斎橋": (34.6723, 135.5002, "大阪府大阪市中央区", 0.92),
            "大阪": (34.6937, 135.5023, "大阪府大阪市", 0.95),
            
            # 関東主要地名
            "横浜": (35.4478, 139.6425, "神奈川県横浜市", 0.95),
            "鎌倉": (35.3197, 139.5468, "神奈川県鎌倉市", 0.95),
            "箱根": (35.2322, 139.1069, "神奈川県足柄下郡箱根町", 0.95),
            "川崎": (35.5309, 139.7029, "神奈川県川崎市", 0.95),
            "千葉": (35.6074, 140.1065, "千葉県千葉市", 0.95),
            "埼玉": (35.8617, 139.6455, "埼玉県さいたま市", 0.95),
            
            # 中部地方
            "名古屋": (35.1815, 136.9066, "愛知県名古屋市", 0.95),
            "金沢": (36.5945, 136.6256, "石川県金沢市", 0.95),
            "富山": (36.6953, 137.2113, "富山県富山市", 0.95),
            "新潟": (37.9026, 139.0235, "新潟県新潟市", 0.95),
            "長野": (36.6485, 138.1950, "長野県長野市", 0.95),
            
            # 北海道地名
            "小樽": (43.1907, 140.9947, "北海道小樽市", 0.95),
            "函館": (41.7687, 140.7291, "北海道函館市", 0.95),
            "札幌": (43.0642, 141.3469, "北海道札幌市", 0.95),
            
            # 東北地方（追加）
            "最上": (38.7583, 140.1761, "山形県最上郡", 0.90),
            
            # 九州地名
            "福岡": (33.5904, 130.4017, "福岡県福岡市", 0.95),
            "鹿児島": (31.5966, 130.5571, "鹿児島県鹿児島市", 0.95),
            "長崎": (32.7448, 129.8737, "長崎県長崎市", 0.95),
            
            # 歴史地名
            "江戸": (35.6762, 139.6503, "東京都", 0.85),
            "平安京": (35.0116, 135.7681, "京都府", 0.85),
            "大和": (34.6851, 135.8325, "奈良県", 0.85),
            "伊勢": (34.4900, 136.7056, "三重県伊勢市", 0.85),
            "甲斐": (35.6635, 138.5681, "山梨県", 0.85),
            "信濃": (36.2048, 137.9677, "長野県", 0.85),
        }
        
        # 都道府県データベース
        self.prefecture_coords = {
            "北海道": (43.0642, 141.3469, 0.95),
            "青森県": (40.8244, 140.7400, 0.95),
            "岩手県": (39.7036, 141.1527, 0.95),
            "宮城県": (38.2682, 140.8721, 0.95),
            "秋田県": (39.7186, 140.1024, 0.95),
            "山形県": (38.2404, 140.3633, 0.95),
            "福島県": (37.7503, 140.4677, 0.95),
            "茨城県": (36.3417, 140.4468, 0.95),
            "栃木県": (36.5657, 139.8836, 0.95),
            "群馬県": (36.3911, 139.0608, 0.95),
            "埼玉県": (35.8572, 139.6489, 0.95),
            "千葉県": (35.6047, 140.1233, 0.95),
            "東京都": (35.6762, 139.6503, 0.95),
            "神奈川県": (35.4478, 139.6425, 0.95),
            "新潟県": (37.9026, 139.0235, 0.95),
            "富山県": (36.6953, 137.2113, 0.95),
            "石川県": (36.5945, 136.6256, 0.95),
            "福井県": (36.0652, 136.2216, 0.95),
            "山梨県": (35.6635, 138.5681, 0.95),
            "長野県": (36.2048, 137.9677, 0.95),
            "岐阜県": (35.3912, 136.7223, 0.95),
            "静岡県": (34.9766, 138.3831, 0.95),
            "愛知県": (35.1802, 136.9066, 0.95),
            "三重県": (34.7303, 136.5086, 0.95),
            "滋賀県": (35.0045, 135.8686, 0.95),
            "京都府": (35.0116, 135.7681, 0.95),
            "大阪府": (34.6937, 135.5023, 0.95),
            "兵庫県": (34.6913, 135.1830, 0.95),
            "奈良県": (34.6851, 135.8325, 0.95),
            "和歌山県": (34.2261, 135.1675, 0.95),
            "鳥取県": (35.5038, 134.2381, 0.95),
            "島根県": (35.4722, 133.0505, 0.95),
            "岡山県": (34.6617, 133.9345, 0.95),
            "広島県": (34.3966, 132.4596, 0.95),
            "山口県": (34.1861, 131.4706, 0.95),
            "徳島県": (34.0658, 134.5590, 0.95),
            "香川県": (34.3401, 134.0434, 0.95),
            "愛媛県": (33.8416, 132.7658, 0.95),
            "高知県": (33.5597, 133.5311, 0.95),
            "福岡県": (33.6064, 130.4181, 0.95),
            "佐賀県": (33.2494, 130.2989, 0.95),
            "長崎県": (32.7448, 129.8737, 0.95),
            "熊本県": (32.7898, 130.7417, 0.95),
            "大分県": (33.2382, 131.6126, 0.95),
            "宮崎県": (31.9111, 131.4239, 0.95),
            "鹿児島県": (31.5966, 130.5571, 0.95),
            "沖縄県": (26.2124, 127.6792, 0.95),
        }

    def geocode_place(self, place_name: str) -> Optional[GeocodingResult]:
        """地名をジオコーディング"""
        
        # 1. 高信頼度地名データベースから検索
        if place_name in self.high_confidence_places:
            lat, lon, location, confidence = self.high_confidence_places[place_name]
            return GeocodingResult(
                place_name=place_name,
                latitude=lat,
                longitude=lon,
                confidence=confidence,
                source="high_confidence_database",
                prefecture=location.split('都')[0] + '都' if '都' in location else 
                          location.split('府')[0] + '府' if '府' in location else
                          location.split('県')[0] + '県' if '県' in location else None,
                city=location
            )
        
        # 2. 都道府県データベースから検索
        for pref_name, (lat, lon, confidence) in self.prefecture_coords.items():
            if place_name in pref_name or pref_name.replace('都', '').replace('府', '').replace('県', '') == place_name:
                return GeocodingResult(
                    place_name=place_name,
                    latitude=lat,
                    longitude=lon,
                    confidence=confidence,
                    source="prefecture_database",
                    prefecture=pref_name,
                    city=pref_name
                )
        
        # 3. 部分マッチング
        for pref_name, (lat, lon, confidence) in self.prefecture_coords.items():
            pref_base = pref_name.replace('都', '').replace('府', '').replace('県', '')
            if pref_base in place_name or place_name in pref_base:
                return GeocodingResult(
                    place_name=place_name,
                    latitude=lat,
                    longitude=lon,
                    confidence=max(0.3, confidence - 0.3),
                    source="fallback_prefecture",
                    prefecture=pref_name,
                    city=f"{pref_name}内の地名"
                )
        
        return None

class PlaceProcessingService:
    """地名抽出→ジオコーディング統合処理サービス"""
    
    def __init__(self):
        self.place_extractor = EnhancedPlaceExtractorV2()
        self.geocoder = SimpleGeocoder()
        logger.info("🚀 地名抽出→ジオコーディング統合処理サービス初期化完了")
    
    def process_author_places(self, author_name: str, limit: Optional[int] = None) -> Dict[str, int]:
        """指定作者のセンテンスから地名抽出→ジオコーディングまで実行"""
        
        start_time = time.time()
        
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # 対象センテンス取得
            query = """
                SELECT s.sentence_id, s.sentence_text, s.work_id, s.author_id
                FROM sentences s
                JOIN authors a ON s.author_id = a.author_id
                WHERE a.author_name = ?
                ORDER BY s.sentence_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor.execute(query, (author_name,))
            sentences = cursor.fetchall()
            
            logger.info(f"🎯 処理対象: {author_name} - {len(sentences):,}センテンス")
            
            stats = {
                'processed_sentences': 0,
                'extracted_places': 0,
                'geocoded_places': 0,
                'skipped_places': 0,
                'processing_time': 0.0
            }
            
            # 既存データクリア（再実行対応）
            cursor.execute("""
                DELETE FROM sentence_places 
                WHERE sentence_id IN (
                    SELECT s.sentence_id FROM sentences s
                    JOIN authors a ON s.author_id = a.author_id
                    WHERE a.author_name = ?
                )
            """, (author_name,))
            
            conn.commit()
            logger.info(f"🧹 既存地名データをクリア")
            
            for i, (sentence_id, sentence_text, work_id, author_id) in enumerate(sentences):
                try:
                    # 地名抽出（既存実装を活用）
                    extracted_places = self.place_extractor.extract_places_from_text(sentence_text)
                    
                    for place in extracted_places:
                        # 既存実装でplacesテーブルに保存
                        place_id = self.place_extractor._get_or_create_place(place)
                        
                        # ジオコーディング実行
                        geocoding_result = self.geocoder.geocode_place(place.name)
                        
                        if geocoding_result:
                            # placesテーブルに座標更新
                            self._update_place_coordinates(place_id, geocoding_result)
                            stats['geocoded_places'] += 1
                        else:
                            stats['skipped_places'] += 1
                        
                        # sentence_placesに関連保存（既存実装活用）
                        self.place_extractor._save_sentence_place_relation(sentence_id, place_id, place)
                        stats['extracted_places'] += 1
                    
                    stats['processed_sentences'] += 1
                    
                    # 進捗表示
                    if (i + 1) % 1000 == 0:
                        elapsed = time.time() - start_time
                        logger.info(f"進捗: {i+1:,}/{len(sentences):,} ({(i+1)/len(sentences)*100:.1f}%) - "
                                  f"地名抽出: {stats['extracted_places']:,}, "
                                  f"ジオコーディング: {stats['geocoded_places']:,} - "
                                  f"経過時間: {elapsed:.1f}秒")
                    
                except Exception as e:
                    logger.error(f"❌ センテンス処理エラー (ID: {sentence_id}): {e}")
                    continue
            
            conn.commit()
            
            stats['processing_time'] = time.time() - start_time
            
            logger.info(f"✅ {author_name} 処理完了")
            logger.info(f"   処理センテンス数: {stats['processed_sentences']:,}")
            logger.info(f"   抽出地名数: {stats['extracted_places']:,}")
            logger.info(f"   ジオコーディング成功: {stats['geocoded_places']:,}")
            logger.info(f"   ジオコーディング失敗: {stats['skipped_places']:,}")
            logger.info(f"   処理時間: {stats['processing_time']:.1f}秒")
            
            return stats
            
        finally:
            conn.close()
    
    def _update_place_coordinates(self, place_id: int, geocoding_result: GeocodingResult):
        """地名の座標情報を更新"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE places SET
                    latitude = ?, longitude = ?, 
                    prefecture = ?, municipality = ?,
                    country = 'Japan'
                WHERE place_id = ?
            """, (
                geocoding_result.latitude, geocoding_result.longitude,
                geocoding_result.prefecture, geocoding_result.city,
                place_id
            ))
            
            conn.commit()
            
            # sentence_placesテーブルにもジオコーディング情報を更新
            cursor.execute("""
                UPDATE sentence_places SET
                    latitude = ?, longitude = ?,
                    geocoding_source = ?, geocoding_confidence = ?
                WHERE place_id = ?
            """, (
                geocoding_result.latitude, geocoding_result.longitude,
                geocoding_result.source, geocoding_result.confidence,
                place_id
            ))
            
            conn.commit()
            
        finally:
            conn.close()

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='地名抽出→ジオコーディング統合処理')
    parser.add_argument('--author', default='梶井 基次郎', help='処理対象作者名')
    parser.add_argument('--limit', type=int, help='処理件数制限')
    args = parser.parse_args()
    
    service = PlaceProcessingService()
    
    logger.info(f"🌟 {args.author} の地名抽出→ジオコーディング処理を開始")
    
    result = service.process_author_places(args.author, args.limit)
    
    logger.info(f"🎉 処理完了! 統計:")
    logger.info(f"   処理センテンス数: {result['processed_sentences']:,}")
    logger.info(f"   抽出地名数: {result['extracted_places']:,}")
    logger.info(f"   ジオコーディング成功: {result['geocoded_places']:,}")
    logger.info(f"   ジオコーディング成功率: {result['geocoded_places']/result['extracted_places']*100:.1f}%" if result['extracted_places'] > 0 else "N/A")
    logger.info(f"   処理時間: {result['processing_time']:.1f}秒")

if __name__ == '__main__':
    main() 