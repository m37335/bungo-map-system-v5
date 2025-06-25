from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# 作者関連のモデル
class AuthorBase(BaseModel):
    """作者の基本情報"""
    author_name: str = Field(..., description="作者名")
    birth_year: Optional[int] = Field(None, description="生年")
    death_year: Optional[int] = Field(None, description="没年")
    period: Optional[str] = Field(None, description="時代（明治・大正・昭和・平成）")
    wikipedia_url: Optional[str] = Field(None, description="WikipediaのURL")
    description: Optional[str] = Field(None, description="説明")

class AuthorCreate(AuthorBase):
    """作者作成用のモデル"""
    pass

class AuthorResponse(AuthorBase):
    """作者レスポンス用のモデル"""
    author_id: int
    works_count: int = 0
    total_sentences: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 作品関連のモデル
class WorkBase(BaseModel):
    """作品の基本情報"""
    work_title: str = Field(..., description="作品名")
    author_id: int = Field(..., description="作者ID")
    publication_year: Optional[int] = Field(None, description="出版年")
    genre: Optional[str] = Field(None, description="ジャンル")
    description: Optional[str] = Field(None, description="説明")

class WorkCreate(WorkBase):
    """作品作成用のモデル"""
    pass

class WorkResponse(WorkBase):
    """作品レスポンス用のモデル"""
    work_id: int
    sentence_count: int = 0
    place_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# センテンス関連のモデル
class SentenceBase(BaseModel):
    """センテンスの基本情報"""
    text: str = Field(..., description="テキスト")
    work_id: int = Field(..., description="作品ID")
    author_id: int = Field(..., description="作者ID")
    before_text: Optional[str] = Field(None, description="前の文脈")
    after_text: Optional[str] = Field(None, description="後の文脈")
    source_info: Optional[str] = Field(None, description="出典情報")
    sentence_length: int = Field(0, description="文の長さ")

class SentenceCreate(SentenceBase):
    """センテンス作成用のモデル"""
    work_title: str = Field(..., description="作品名")
    author_name: str = Field(..., description="作者名")

class SentenceResponse(SentenceBase):
    """センテンスレスポンス用のモデル"""
    sentence_id: int
    place_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 地名関連のモデル
class PlaceBase(BaseModel):
    """地名の基本情報"""
    place_name: str = Field(..., description="地名")
    latitude: Optional[float] = Field(None, description="緯度")
    longitude: Optional[float] = Field(None, description="経度")
    confidence: float = Field(0.0, description="信頼度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")

class PlaceResponse(PlaceBase):
    """地名レスポンス用のモデル"""
    place_id: int
    mention_count: int = 0
    author_count: int = 0
    work_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 統計情報のモデル
class AuthorStats(BaseModel):
    """作者の統計情報"""
    works_count: int
    total_sentences: int
    total_places: int
    unique_places: int

class WorkStats(BaseModel):
    """作品の統計情報"""
    sentence_count: int
    place_count: int
    unique_places: int
    average_confidence: float

# ========================================
# v5.0 新モデル - Enums
# ========================================

class SectionType(str, Enum):
    """セクションタイプ"""
    CHAPTER = "chapter"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"

class VerificationType(str, Enum):
    """AI検証タイプ"""
    PLACE_VALIDATION = "place_validation"
    CONTEXT_ANALYSIS = "context_analysis"
    FALSE_POSITIVE_CHECK = "false_positive_check"
    CONFIDENCE_BOOST = "confidence_boost"

class VerificationStatus(str, Enum):
    """検証ステータス"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"
    NEEDS_REVIEW = "needs_review"

class CacheType(str, Enum):
    """キャッシュタイプ"""
    AUTHOR_STATS = "author_stats"
    WORK_STATS = "work_stats"
    PLACE_STATS = "place_stats"
    GLOBAL_STATS = "global_stats"
    SEARCH_RESULTS = "search_results"

class ProcessType(str, Enum):
    """処理タイプ"""
    TEXT_EXTRACTION = "text_extraction"
    PLACE_EXTRACTION = "place_extraction"
    GEOCODING = "geocoding"
    AI_VERIFICATION = "ai_verification"
    FULL_PIPELINE = "full_pipeline"
    MIGRATION = "migration"
    MAINTENANCE = "maintenance"

class ProcessStatus(str, Enum):
    """処理ステータス"""
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

# ========================================
# v5.0 新モデル - Section（階層構造）
# ========================================

class SectionBase(BaseModel):
    """セクションの基本情報"""
    work_id: int = Field(..., description="作品ID")
    section_type: SectionType = Field(..., description="セクションタイプ")
    parent_section_id: Optional[int] = Field(None, description="親セクションID")
    section_number: Optional[int] = Field(None, description="セクション番号")
    title: Optional[str] = Field(None, description="タイトル")
    content: Optional[str] = Field(None, description="内容")
    character_position: Optional[int] = Field(None, description="文字位置")
    character_length: Optional[int] = Field(None, description="文字数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")

class SectionCreate(SectionBase):
    """セクション作成用のモデル"""
    pass

class SectionResponse(SectionBase):
    """セクションレスポンス用のモデル"""
    section_id: int
    children: List['SectionResponse'] = Field(default_factory=list, description="子セクション")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# 前方参照の解決
SectionResponse.model_rebuild()

# ========================================
# v5.0 新モデル - AIVerification（AI検証）
# ========================================

class AIVerificationBase(BaseModel):
    """AI検証の基本情報"""
    place_mention_id: int = Field(..., description="地名言及ID")
    ai_model: str = Field(..., description="AIモデル")
    verification_type: VerificationType = Field(..., description="検証タイプ")
    input_context: Optional[str] = Field(None, description="入力文脈")
    confidence_score: Optional[float] = Field(None, description="信頼度スコア")
    is_valid_place: Optional[bool] = Field(None, description="有効な地名かどうか")
    reasoning: Optional[str] = Field(None, description="推論内容")

class AIVerificationCreate(AIVerificationBase):
    """AI検証作成用のモデル"""
    pass

class AIVerificationResponse(AIVerificationBase):
    """AI検証レスポンス用のモデル"""
    verification_id: int
    ai_response: Dict[str, Any] = Field(default_factory=dict, description="AIレスポンス")
    raw_response: Optional[str] = Field(None, description="生のレスポンス")
    verification_status: VerificationStatus = Field(VerificationStatus.PENDING, description="検証ステータス")
    processing_time_ms: Optional[int] = Field(None, description="処理時間（ミリ秒）")
    api_cost: Optional[float] = Field(None, description="API使用コスト")
    verified_at: datetime

    class Config:
        orm_mode = True

# ========================================
# v5.0 新モデル - StatisticsCache（統計キャッシュ）
# ========================================

class StatisticsCacheBase(BaseModel):
    """統計キャッシュの基本情報"""
    cache_key: str = Field(..., description="キャッシュキー")
    cache_type: CacheType = Field(..., description="キャッシュタイプ")
    entity_id: Optional[int] = Field(None, description="エンティティID")
    data: Dict[str, Any] = Field(..., description="キャッシュデータ")
    expires_at: Optional[datetime] = Field(None, description="有効期限")

class StatisticsCacheCreate(StatisticsCacheBase):
    """統計キャッシュ作成用のモデル"""
    pass

class StatisticsCacheResponse(StatisticsCacheBase):
    """統計キャッシュレスポンス用のモデル"""
    cache_id: int
    hit_count: int = Field(0, description="アクセス回数")
    last_accessed: Optional[datetime] = Field(None, description="最終アクセス時刻")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# ========================================
# v5.0 新モデル - ProcessingLog（処理ログ）
# ========================================

class ProcessingLogBase(BaseModel):
    """処理ログの基本情報"""
    work_id: Optional[int] = Field(None, description="作品ID")
    process_type: ProcessType = Field(..., description="処理タイプ")
    status: ProcessStatus = Field(ProcessStatus.STARTED, description="ステータス")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")
    error_type: Optional[str] = Field(None, description="エラータイプ")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="処理統計")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="処理設定")

class ProcessingLogCreate(ProcessingLogBase):
    """処理ログ作成用のモデル"""
    pass

class ProcessingLogResponse(ProcessingLogBase):
    """処理ログレスポンス用のモデル"""
    log_id: int
    started_at: datetime
    completed_at: Optional[datetime] = Field(None, description="完了時刻")
    processing_duration_ms: Optional[int] = Field(None, description="処理時間（ミリ秒）")
    stack_trace: Optional[str] = Field(None, description="スタックトレース")
    user_agent: Optional[str] = Field(None, description="ユーザーエージェント")
    ip_address: Optional[str] = Field(None, description="IPアドレス")

    class Config:
        orm_mode = True

# ========================================
# v5.0 拡張統計モデル
# ========================================

class PlaceVerificationStats(BaseModel):
    """地名検証統計"""
    total_mentions: int
    verified_mentions: int
    rejected_mentions: int
    pending_mentions: int
    average_confidence: float
    verification_rate: float

class AIModelStats(BaseModel):
    """AIモデル統計"""
    model_name: str
    total_verifications: int
    success_rate: float
    average_processing_time: float
    total_cost: float
    average_confidence: float

class GlobalSystemStats(BaseModel):
    """システム全体統計"""
    total_authors: int
    total_works: int
    total_sentences: int
    total_places: int
    total_verifications: int
    cache_hit_rate: float
    average_response_time: float
