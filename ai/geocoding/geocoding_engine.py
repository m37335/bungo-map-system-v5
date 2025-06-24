"""
文豪ゆかり地図システム - ジオコーディングエンジン

Google Maps API統合、座標取得、品質検証機能を提供
"""

import os
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import googlemaps
    GOOGLEMAPS_AVAILABLE = True
except ImportError:
    GOOGLEMAPS_AVAILABLE = False

from ..llm.client import LLMClient, LLMRequest
from ..nlp.context_analyzer import ContextAnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class GeocodingResult:
    """Geocoding結果"""
    place_name: str
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: float
    source: str
    prefecture: Optional[str] = None
    city: Optional[str] = None
    context_analysis: Optional[ContextAnalysisResult] = None
    fallback_used: bool = False

class GeocodingEngine:
    """ジオコーディングエンジン"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初期化"""
        self.llm_client = llm_client or LLMClient()
        self._init_google_maps()
        logger.info("🗺️ ジオコーディングエンジン初期化完了")
    
    def _init_google_maps(self):
        """Google Maps API初期化"""
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if api_key and GOOGLEMAPS_AVAILABLE:
            try:
                self.gmaps = googlemaps.Client(key=api_key)
                self.google_maps_enabled = True
                logger.info("✅ Google Maps API接続準備完了")
            except Exception as e:
                logger.error(f"❌ Google Maps API初期化エラー: {e}")
                self.gmaps = None
                self.google_maps_enabled = False
        else:
            self.gmaps = None
            self.google_maps_enabled = False
            if not GOOGLEMAPS_AVAILABLE:
                logger.warning("⚠️ googlemaps パッケージがインストールされていません")
            else:
                logger.warning("⚠️ Google Maps APIキーが設定されていません")
    
    def geocode_place(self, place_name: str, context_analysis: Optional[ContextAnalysisResult] = None) -> Optional[GeocodingResult]:
        """地名のジオコーディング実行"""
        
        if not place_name:
            return None
        
        # まずGoogle Maps APIを試行
        result = self._google_maps_geocoding(place_name, context_analysis)
        
        # フォールバック処理
        if not result:
            result = self._fallback_geocoding(place_name, context_analysis)
        
        return result
    
    def _google_maps_geocoding(self, place_name: str, context_analysis: Optional[ContextAnalysisResult] = None) -> Optional[GeocodingResult]:
        """Google Maps APIでのジオコーディング"""
        
        if not self.google_maps_enabled:
            return None
        
        try:
            # レート制限
            time.sleep(0.1)
            
            # 検索クエリ構築
            search_query = self._build_search_query(place_name, context_analysis)
            
            # API実行
            results = self.gmaps.geocode(search_query)
            
            if not results:
                logger.debug(f"Google Maps: {search_query} の結果なし")
                return None
            
            # 最適な結果を選択
            best_result = self._select_best_result(results, place_name, context_analysis)
            
            if best_result:
                location = best_result['geometry']['location']
                lat, lng = location['lat'], location['lng']
                
                # 日本国内チェック
                if not self._is_japan_coordinate(lat, lng):
                    logger.debug(f"Google Maps: {place_name} は日本国外の座標")
                    return None
                
                # 住所情報解析
                prefecture, city = self._parse_address_components(best_result)
                
                confidence = self._calculate_confidence(best_result, place_name, context_analysis)
                
                logger.info(f"✅ Google Maps成功: {place_name} -> ({lat:.6f}, {lng:.6f})")
                
                return GeocodingResult(
                    place_name=place_name,
                    latitude=lat,
                    longitude=lng,
                    confidence=confidence,
                    source="google_maps",
                    prefecture=prefecture,
                    city=city,
                    context_analysis=context_analysis
                )
                
        except Exception as e:
            logger.error(f"❌ Google Maps API エラー ({place_name}): {e}")
        
        return None
    
    def _fallback_geocoding(self, place_name: str, context_analysis: Optional[ContextAnalysisResult] = None) -> Optional[GeocodingResult]:
        """フォールバックジオコーディング"""
        
        # 推定地域がある場合はそれを利用
        if context_analysis and context_analysis.suggested_location:
            suggested = context_analysis.suggested_location
            result = self._google_maps_geocoding(suggested, context_analysis)
            if result:
                result.fallback_used = True
                result.place_name = place_name  # 元の地名を保持
                return result
        
        # 地域文脈を利用した検索
        if context_analysis and context_analysis.geographic_context:
            context_query = f"{place_name} {context_analysis.geographic_context}"
            result = self._google_maps_geocoding(context_query, context_analysis)
            if result:
                result.fallback_used = True
                return result
        
        # 一般的な地名パターンで再試行
        fallback_queries = [
            f"{place_name} 日本",
            f"{place_name}市",
            f"{place_name}町",
            f"{place_name}駅"
        ]
        
        for query in fallback_queries:
            result = self._google_maps_geocoding(query, context_analysis)
            if result:
                result.fallback_used = True
                return result
        
        logger.debug(f"全てのジオコーディング手法が失敗: {place_name}")
        return None
    
    def _build_search_query(self, place_name: str, context_analysis: Optional[ContextAnalysisResult] = None) -> str:
        """検索クエリ構築"""
        query = place_name
        
        # 文脈情報を利用
        if context_analysis:
            if context_analysis.geographic_context:
                query += f" {context_analysis.geographic_context}"
            elif context_analysis.suggested_location:
                query = context_analysis.suggested_location
        
        # 日本限定検索
        if "日本" not in query:
            query += " 日本"
        
        return query
    
    def _select_best_result(self, results: List[Dict], place_name: str, context_analysis: Optional[ContextAnalysisResult] = None) -> Optional[Dict]:
        """最適な結果を選択"""
        
        if not results:
            return None
        
        # 完全一致を優先
        for result in results:
            if place_name in result.get('formatted_address', ''):
                return result
        
        # 日本国内の結果を優先
        japan_results = []
        for result in results:
            location = result['geometry']['location']
            if self._is_japan_coordinate(location['lat'], location['lng']):
                japan_results.append(result)
        
        if japan_results:
            return japan_results[0]
        
        return results[0]
    
    def _is_japan_coordinate(self, lat: float, lng: float) -> bool:
        """日本国内の座標かどうか判定"""
        # 日本の緯度経度範囲（少し余裕を持たせた範囲）
        return (24.0 <= lat <= 46.0) and (123.0 <= lng <= 146.0)
    
    def _parse_address_components(self, result: Dict) -> Tuple[Optional[str], Optional[str]]:
        """住所コンポーネントから都道府県・市区町村を抽出"""
        prefecture = None
        city = None
        
        components = result.get('address_components', [])
        
        for component in components:
            types = component.get('types', [])
            
            # 都道府県
            if 'administrative_area_level_1' in types:
                prefecture = component['long_name']
            
            # 市区町村
            elif any(t in types for t in ['locality', 'administrative_area_level_2']):
                city = component['long_name']
        
        return prefecture, city
    
    def _calculate_confidence(self, result: Dict, place_name: str, context_analysis: Optional[ContextAnalysisResult] = None) -> float:
        """信頼度計算"""
        confidence = 0.7  # 基本値
        
        # 完全一致ボーナス
        if place_name in result.get('formatted_address', ''):
            confidence += 0.2
        
        # 文脈分析結果を反映
        if context_analysis:
            if context_analysis.is_place_name:
                confidence += 0.1
            confidence += context_analysis.confidence * 0.1
        
        # Google Mapsの品質指標
        geometry_type = result.get('geometry', {}).get('location_type', '')
        if geometry_type == 'ROOFTOP':
            confidence += 0.1
        elif geometry_type == 'RANGE_INTERPOLATED':
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def analyze_with_llm(self, place_name: str, sentence: str) -> Optional[Dict]:
        """LLMを使った文脈分析"""
        
        if not self.llm_client.is_available():
            return None
        
        prompt = f"""
以下の文章中の「{place_name}」について分析してください。

文章: {sentence}

以下の点について判定してください：
1. 「{place_name}」は地名として使われているか？
2. 人名の可能性はないか？
3. もし地名なら、どの地域の可能性が高いか？
4. 判定の信頼度（0-1）は？

JSON形式で回答してください：
{{
    "is_place_name": true/false,
    "confidence": 0.0-1.0,
    "region_suggestion": "推定地域",
    "reasoning": "判定理由"
}}
"""
        
        request = LLMRequest(
            prompt=prompt,
            model="gpt-3.5-turbo",
            max_tokens=300,
            temperature=0.1
        )
        
        response = self.llm_client.generate(request)
        
        if response.error:
            logger.error(f"LLM分析エラー: {response.error}")
            return None
        
        try:
            import json
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"LLM応答パースエラー: {e}")
            return None 