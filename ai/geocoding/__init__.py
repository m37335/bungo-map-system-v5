"""
ジオコーディングモジュール

Google Maps API統合、座標取得、品質検証機能を提供
"""

from .geocoding_engine import GeocodingEngine, GeocodingResult

__all__ = [
    'GeocodingEngine',
    'GeocodingResult'
] 