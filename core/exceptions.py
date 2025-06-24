"""
文豪ゆかり地図システム - カスタム例外

システム全体で使用される例外クラスを定義
"""

from typing import Optional, Any

class BungoMapError(Exception):
    """文豪地図システムの基底例外クラス"""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

class DatabaseError(BungoMapError):
    """データベース関連エラー"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(message, code="DB_ERROR", **kwargs)
        self.query = query

class DataExtractionError(BungoMapError):
    """データ抽出関連エラー"""
    
    def __init__(self, message: str, source: Optional[str] = None, **kwargs):
        super().__init__(message, code="EXTRACTION_ERROR", **kwargs)
        self.source = source

class PlaceExtractionError(DataExtractionError):
    """地名抽出関連エラー"""
    
    def __init__(self, message: str, sentence: Optional[str] = None, **kwargs):
        super().__init__(message, code="PLACE_EXTRACTION_ERROR", **kwargs)
        self.sentence = sentence

class AIServiceError(BungoMapError):
    """AI サービス関連エラー"""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        super().__init__(message, code="AI_SERVICE_ERROR", **kwargs)
        self.service = service

class GeocodingError(BungoMapError):
    """ジオコーディング関連エラー"""
    
    def __init__(self, message: str, place_name: Optional[str] = None, **kwargs):
        super().__init__(message, code="GEOCODING_ERROR", **kwargs)
        self.place_name = place_name

class ConfigurationError(BungoMapError):
    """設定関連エラー"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key

class ValidationError(BungoMapError):
    """データ検証関連エラー"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)
        self.field = field
        self.value = value

class RateLimitError(BungoMapError):
    """レート制限エラー"""
    
    def __init__(self, message: str, service: Optional[str] = None, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, code="RATE_LIMIT_ERROR", **kwargs)
        self.service = service
        self.retry_after = retry_after

class AuthenticationError(BungoMapError):
    """認証関連エラー"""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        super().__init__(message, code="AUTH_ERROR", **kwargs)
        self.service = service 