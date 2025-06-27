#!/usr/bin/env python3
"""
地理空間解析器 (GeoSpatialAnalyzer)
地名の地理的分析・近接検索・クラスター分析を行う

作成日: 2025年6月25日
"""

import math
import sqlite3
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class GeoPoint:
    """地理座標点"""
    latitude: float
    longitude: float
    place_id: Optional[int] = None
    place_name: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class NearbyResult:
    """近接検索結果"""
    place_id: int
    place_name: str
    distance_km: float
    coordinates: GeoPoint
    place_type: Optional[str] = None
    metadata: Dict[str, Any] = None

class GeoSpatialAnalyzer:
    """地理空間解析器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # 地球の半径（km）
        self.EARTH_RADIUS = 6371.0
    
    def nearby_search(self, center_lat: float, center_lng: float, 
                     radius_km: float = 10.0, 
                     place_type: Optional[str] = None,
                     limit: int = 50) -> List[NearbyResult]:
        """近接検索"""
        logger.info(f"近接検索: 中心({center_lat}, {center_lng}), 半径{radius_km}km")
        
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 基本クエリ
                query = """
                    SELECT master_id, display_name, latitude, longitude, 
                           place_type, usage_count
                    FROM place_masters 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                """
                params = []
                
                # 地名タイプフィルター
                if place_type:
                    query += " AND place_type = ?"
                    params.append(place_type)
                
                # 大まかな範囲フィルター（パフォーマンス向上）
                lat_delta = radius_km / 111.0  # 緯度1度≈111km
                lng_delta = radius_km / (111.0 * math.cos(math.radians(center_lat)))
                
                query += """
                    AND latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """
                params.extend([
                    center_lat - lat_delta, center_lat + lat_delta,
                    center_lng - lng_delta, center_lng + lng_delta
                ])
                
                query += " ORDER BY usage_count DESC LIMIT ?"
                params.append(limit * 2)  # 距離計算後に絞り込むため多めに取得
                
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    place_id, name, lat, lng, p_type, usage_count = row
                    
                    # 正確な距離計算
                    distance = self.calculate_distance(center_lat, center_lng, lat, lng)
                    
                    if distance <= radius_km:
                        result = NearbyResult(
                            place_id=place_id,
                            place_name=name,
                            distance_km=distance,
                            coordinates=GeoPoint(lat, lng),
                            place_type=p_type,
                            metadata={'usage_count': usage_count}
                        )
                        results.append(result)
                
                # 距離でソート
                results.sort(key=lambda x: x.distance_km)
                results = results[:limit]
                
        except Exception as e:
            logger.error(f"近接検索エラー: {e}")
        
        logger.info(f"近接検索完了: {len(results)}件")
        return results
    
    def calculate_distance(self, lat1: float, lng1: float, 
                          lat2: float, lng2: float) -> float:
        """2点間の距離計算（ハーバサイン公式）"""
        # 度をラジアンに変換
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # 差分計算
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # ハーバサイン公式
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return self.EARTH_RADIUS * c
    
    def cluster_analysis(self, max_distance_km: float = 50.0, 
                        min_cluster_size: int = 3) -> List[Dict[str, Any]]:
        """クラスター分析"""
        logger.info(f"クラスター分析開始: 最大距離{max_distance_km}km, 最小サイズ{min_cluster_size}")
        
        clusters = []
        
        try:
            # 全地名の座標を取得
            places = self._get_all_coordinates()
            
            if len(places) < min_cluster_size:
                return clusters
            
            # 単純なクラスタリング（距離ベース）
            visited = set()
            
            for i, place in enumerate(places):
                if i in visited:
                    continue
                
                cluster = [place]
                visited.add(i)
                
                # 近接する地名を探す
                for j, other_place in enumerate(places):
                    if j in visited or i == j:
                        continue
                    
                    distance = self.calculate_distance(
                        place.latitude, place.longitude,
                        other_place.latitude, other_place.longitude
                    )
                    
                    if distance <= max_distance_km:
                        cluster.append(other_place)
                        visited.add(j)
                
                # 最小サイズを満たすクラスターのみ追加
                if len(cluster) >= min_cluster_size:
                    cluster_info = self._analyze_cluster(cluster)
                    clusters.append(cluster_info)
            
        except Exception as e:
            logger.error(f"クラスター分析エラー: {e}")
        
        logger.info(f"クラスター分析完了: {len(clusters)}クラスター")
        return clusters
    
    def _get_all_coordinates(self) -> List[GeoPoint]:
        """全地名の座標を取得"""
        places = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT master_id, display_name, latitude, longitude, 
                           place_type, usage_count
                    FROM place_masters 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                    ORDER BY usage_count DESC
                """)
                
                for row in cursor.fetchall():
                    place_id, name, lat, lng, p_type, usage_count = row
                    
                    place = GeoPoint(
                        latitude=lat,
                        longitude=lng,
                        place_id=place_id,
                        place_name=name,
                        metadata={
                            'place_type': p_type,
                            'usage_count': usage_count
                        }
                    )
                    places.append(place)
                    
        except Exception as e:
            logger.error(f"座標取得エラー: {e}")
        
        return places
    
    def _analyze_cluster(self, cluster: List[GeoPoint]) -> Dict[str, Any]:
        """クラスターの分析"""
        if not cluster:
            return {}
        
        # 中心座標計算
        center_lat = sum(p.latitude for p in cluster) / len(cluster)
        center_lng = sum(p.longitude for p in cluster) / len(cluster)
        
        # 半径計算（最も遠い点までの距離）
        max_distance = 0
        for place in cluster:
            distance = self.calculate_distance(center_lat, center_lng, 
                                             place.latitude, place.longitude)
            max_distance = max(max_distance, distance)
        
        # 地名タイプ分布
        type_counts = {}
        total_usage = 0
        
        for place in cluster:
            p_type = place.metadata.get('place_type', 'unknown')
            type_counts[p_type] = type_counts.get(p_type, 0) + 1
            total_usage += place.metadata.get('usage_count', 0)
        
        # 代表地名（使用頻度最高）
        representative = max(cluster, key=lambda p: p.metadata.get('usage_count', 0))
        
        return {
            'cluster_id': f"cluster_{len(cluster)}_{int(center_lat * 1000)}_{int(center_lng * 1000)}",
            'center_coordinates': {
                'latitude': round(center_lat, 6),
                'longitude': round(center_lng, 6)
            },
            'radius_km': round(max_distance, 2),
            'place_count': len(cluster),
            'total_usage': total_usage,
            'representative_place': {
                'name': representative.place_name,
                'usage_count': representative.metadata.get('usage_count', 0)
            },
            'type_distribution': type_counts,
            'places': [
                {
                    'place_id': p.place_id,
                    'name': p.place_name,
                    'coordinates': {'lat': p.latitude, 'lng': p.longitude},
                    'type': p.metadata.get('place_type'),
                    'usage_count': p.metadata.get('usage_count', 0)
                }
                for p in cluster
            ]
        }
    
    def get_geographic_distribution(self) -> Dict[str, Any]:
        """地理的分布の分析"""
        logger.info("地理的分布分析開始")
        
        distribution = {
            'total_places': 0,
            'coordinate_coverage': 0.0,
            'regional_distribution': {},
            'coordinate_bounds': {},
            'density_analysis': {}
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 基本統計
                cursor.execute("SELECT COUNT(*) FROM place_masters")
                total_places = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM place_masters 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                """)
                places_with_coords = cursor.fetchone()[0]
                
                # 座標範囲
                cursor.execute("""
                    SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude)
                    FROM place_masters 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                """)
                bounds = cursor.fetchone()
                
                # 都道府県別分布
                cursor.execute("""
                    SELECT prefecture, COUNT(*) as count
                    FROM place_masters 
                    WHERE prefecture IS NOT NULL
                    GROUP BY prefecture
                    ORDER BY count DESC
                """)
                
                regional_dist = {row[0]: row[1] for row in cursor.fetchall()}
                
                distribution.update({
                    'total_places': total_places,
                    'coordinate_coverage': round(places_with_coords / max(total_places, 1), 3),
                    'regional_distribution': regional_dist,
                    'coordinate_bounds': {
                        'min_latitude': bounds[0],
                        'max_latitude': bounds[1],
                        'min_longitude': bounds[2],
                        'max_longitude': bounds[3]
                    } if bounds[0] else None
                })
                
        except Exception as e:
            logger.error(f"地理的分布分析エラー: {e}")
        
        logger.info("地理的分布分析完了")
        return distribution
    
    def find_outliers(self, threshold_km: float = 100.0) -> List[Dict[str, Any]]:
        """地理的外れ値の検出"""
        logger.info(f"外れ値検出開始: 閾値{threshold_km}km")
        
        outliers = []
        
        try:
            places = self._get_all_coordinates()
            
            for i, place in enumerate(places):
                # 最も近い3つの地名までの距離を計算
                distances = []
                
                for j, other_place in enumerate(places):
                    if i == j:
                        continue
                    
                    distance = self.calculate_distance(
                        place.latitude, place.longitude,
                        other_place.latitude, other_place.longitude
                    )
                    distances.append(distance)
                
                # 最も近い3つの平均距離
                distances.sort()
                avg_distance = sum(distances[:3]) / min(3, len(distances))
                
                # 閾値を超える場合は外れ値
                if avg_distance > threshold_km:
                    outliers.append({
                        'place_id': place.place_id,
                        'place_name': place.place_name,
                        'coordinates': {
                            'latitude': place.latitude,
                            'longitude': place.longitude
                        },
                        'avg_distance_to_nearest': round(avg_distance, 2),
                        'place_type': place.metadata.get('place_type'),
                        'usage_count': place.metadata.get('usage_count', 0)
                    })
                    
        except Exception as e:
            logger.error(f"外れ値検出エラー: {e}")
        
        # 距離順でソート
        outliers.sort(key=lambda x: x['avg_distance_to_nearest'], reverse=True)
        
        logger.info(f"外れ値検出完了: {len(outliers)}件")
        return outliers

def main():
    """テスト実行"""
    import tempfile
    import os
    
    # テスト用データベース作成
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    # テストデータ作成
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE place_masters (
                master_id INTEGER PRIMARY KEY,
                display_name VARCHAR(255),
                latitude FLOAT,
                longitude FLOAT,
                place_type VARCHAR(50),
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        # サンプルデータ
        test_places = [
            (1, "東京駅", 35.6812, 139.7671, "駅", 100),
            (2, "新宿", 35.6896, 139.6917, "地区", 80),
            (3, "渋谷", 35.6580, 139.7016, "地区", 75),
            (4, "大阪駅", 34.7024, 135.4959, "駅", 90),
            (5, "京都", 35.0116, 135.7681, "都市", 85)
        ]
        
        cursor.executemany("""
            INSERT INTO place_masters 
            (master_id, display_name, latitude, longitude, place_type, usage_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, test_places)
    
    analyzer = GeoSpatialAnalyzer(db_path)
    
    # 近接検索テスト（東京駅周辺）
    nearby = analyzer.nearby_search(35.6812, 139.7671, 20.0)
    print(f"東京駅周辺20km: {len(nearby)}件")
    for result in nearby:
        print(f"- {result.place_name}: {result.distance_km:.2f}km")
    
    # 地理的分布テスト
    distribution = analyzer.get_geographic_distribution()
    print(f"\n地理的分布: {distribution}")
    
    # クリーンアップ
    os.unlink(db_path)
    print("\nテスト完了")

if __name__ == "__main__":
    main()
