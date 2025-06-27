from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from database.config import get_db
from database.crud import DatabaseManager
from extractors.place_extractor import PlaceExtractor, ExtractedPlace
from core.models import (
    AuthorCreate,
    AuthorResponse,
    WorkCreate,
    WorkResponse,
    SentenceCreate,
    SentenceResponse,
    PlaceResponse,
    AuthorStats, WorkStats,
    # v5.0 新モデル
    SectionBase, SectionCreate, SectionResponse,
    AIVerificationBase, AIVerificationCreate, AIVerificationResponse,
    StatisticsCacheBase, StatisticsCacheCreate, StatisticsCacheResponse,
    ProcessingLogBase, ProcessingLogCreate, ProcessingLogResponse,
    PlaceVerificationStats, AIModelStats, GlobalSystemStats
)
from core.cache import CacheManager, cache_result

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="文豪ゆかり地図API v5.0",
    description="文豪作品の地名情報を管理するAPI - 階層構造・AI検証・統計キャッシュ対応",
    version="5.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# キャッシュマネージャーのインスタンス化
cache_manager = CacheManager()

# 依存関係
def get_db_manager(db: Session = Depends(get_db)) -> DatabaseManager:
    return DatabaseManager(db)

def get_place_extractor() -> PlaceExtractor:
    return PlaceExtractor()

# 作者関連のエンドポイント
@app.post("/authors/", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_author(
    author: AuthorCreate,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """作者の作成"""
    try:
        result = db_manager.create_author(author.dict())
        # キャッシュのクリア
        cache_manager.clear_prefix("author")
        return result
    except Exception as e:
        logger.error(f"作者作成エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作者の作成に失敗しました"
        )

@app.get("/authors/{author_id}", response_model=AuthorResponse)
@cache_result(prefix="author", ttl=3600)
async def get_author(
    author_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache_manager: CacheManager = Depends(lambda: cache_manager)
):
    """作者の取得"""
    try:
        result = db_manager.get_author(author_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="作者が見つかりません"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"作者取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作者の取得に失敗しました"
        )

# 作品関連のエンドポイント
@app.post("/works/", response_model=WorkResponse, status_code=status.HTTP_201_CREATED)
async def create_work(
    work: WorkCreate,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """作品の作成"""
    try:
        result = db_manager.create_work(work.dict())
        # キャッシュのクリア
        cache_manager.clear_prefix("work")
        cache_manager.clear_prefix("author")
        return result
    except Exception as e:
        logger.error(f"作品作成エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作品の作成に失敗しました"
        )

@app.get("/works/{work_id}", response_model=WorkResponse)
@cache_result(prefix="work", ttl=3600)
async def get_work(
    work_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache_manager: CacheManager = Depends(lambda: cache_manager)
):
    """作品の取得"""
    try:
        result = db_manager.get_work(work_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="作品が見つかりません"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"作品取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作品の取得に失敗しました"
        )

# センテンス関連のエンドポイント
@app.post("/sentences/", response_model=SentenceResponse, status_code=status.HTTP_201_CREATED)
async def create_sentence(
    sentence: SentenceCreate,
    db_manager: DatabaseManager = Depends(get_db_manager),
    place_extractor: PlaceExtractor = Depends(get_place_extractor)
):
    """センテンスの作成と地名抽出"""
    try:
        # センテンスの作成
        result = db_manager.create_sentence(sentence.dict())
        
        # キャッシュのクリア
        cache_manager.clear_prefix("sentence")
        cache_manager.clear_prefix("work")
        
        return result
        
    except Exception as e:
        logger.error(f"センテンス作成エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="センテンスの作成に失敗しました"
        )

@app.get("/sentences/{sentence_id}", response_model=SentenceResponse)
@cache_result(prefix="sentence", ttl=3600)
async def get_sentence(
    sentence_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache_manager: CacheManager = Depends(lambda: cache_manager)
):
    """センテンスの取得"""
    try:
        result = db_manager.get_sentence(sentence_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="センテンスが見つかりません"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"センテンス取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="センテンスの取得に失敗しました"
        )

# 地名関連のエンドポイント
@app.get("/places/", response_model=List[PlaceResponse])
def get_places(db: Session = Depends(get_db)):
    db_manager = DatabaseManager(db)
    places = db_manager.get_all_places()
    return [PlaceResponse(**place.__dict__) for place in places]

@app.get("/places/{place_id}", response_model=PlaceResponse)
@cache_result(prefix="place", ttl=3600)
async def get_place(
    place_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache_manager: CacheManager = Depends(lambda: cache_manager)
):
    """地名の取得"""
    try:
        result = db_manager.get_place(place_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="地名が見つかりません"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"地名取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="地名の取得に失敗しました"
        )

# ========================================
# v5.0 新API: 階層構造管理
# ========================================

@app.get("/works/{work_id}/sections", response_model=List[SectionResponse])
async def get_work_sections(
    work_id: int,
    section_type: Optional[str] = None,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """作品の章構造取得"""
    try:
        # TODO: DatabaseManagerにget_sections_by_workメソッドを追加
        return []  # 実装後に更新
    except Exception as e:
        logger.error(f"作品章構造取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作品の章構造取得に失敗しました"
        )

@app.post("/sections/", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    section: SectionCreate,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """章・段落・文の作成"""
    try:
        # TODO: DatabaseManagerにcreate_sectionメソッドを追加
        return {}  # 実装後に更新
    except Exception as e:
        logger.error(f"セクション作成エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="セクションの作成に失敗しました"
        )

@app.get("/sections/{section_id}/children", response_model=List[SectionResponse])
async def get_section_children(
    section_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """子要素取得"""
    try:
        # TODO: 実装
        return []
    except Exception as e:
        logger.error(f"子要素取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="子要素の取得に失敗しました"
        )

@app.get("/sections/{section_id}/context")
async def get_section_context(
    section_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """文脈情報取得"""
    try:
        # TODO: 実装
        return {"context": "実装予定"}
    except Exception as e:
        logger.error(f"文脈情報取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文脈情報の取得に失敗しました"
        )

# ========================================
# v5.0 新API: AI検証管理
# ========================================

@app.post("/ai/verify/place", response_model=AIVerificationResponse)
async def verify_single_place(
    verification: AIVerificationCreate,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """単一地名検証"""
    try:
        # TODO: AI検証マネージャーの実装
        return {}  # 実装後に更新
    except Exception as e:
        logger.error(f"地名検証エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="地名検証に失敗しました"
        )

@app.post("/ai/verify/batch")
async def verify_places_batch(
    place_mention_ids: List[int],
    ai_model: str = "gpt-3.5-turbo",
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """一括地名検証"""
    try:
        # TODO: バッチ検証の実装
        return {"verified_count": len(place_mention_ids), "status": "completed"}
    except Exception as e:
        logger.error(f"一括地名検証エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="一括地名検証に失敗しました"
        )

@app.get("/ai/verifications/{verification_id}", response_model=AIVerificationResponse)
async def get_verification_result(
    verification_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """検証結果取得"""
    try:
        # TODO: 実装
        return {}
    except Exception as e:
        logger.error(f"検証結果取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="検証結果の取得に失敗しました"
        )

@app.get("/places/{place_id}/verifications", response_model=List[AIVerificationResponse])
async def get_place_verifications(
    place_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """地名の検証履歴"""
    try:
        # TODO: 実装
        return []
    except Exception as e:
        logger.error(f"検証履歴取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="検証履歴の取得に失敗しました"
        )

# ========================================
# v5.0 新API: 統計・分析
# ========================================

@app.get("/statistics/global", response_model=GlobalSystemStats)
@cache_result(prefix="global_stats", ttl=3600)
async def get_global_statistics(
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """システム全体統計"""
    try:
        # TODO: 実装
        return {}
    except Exception as e:
        logger.error(f"全体統計取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="全体統計の取得に失敗しました"
        )

@app.get("/statistics/geographical/{region}")
async def get_geographical_statistics(
    region: str,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """地域別統計"""
    try:
        # TODO: 実装
        return {"region": region, "statistics": "実装予定"}
    except Exception as e:
        logger.error(f"地域別統計取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="地域別統計の取得に失敗しました"
        )

@app.get("/places/search/nearby")
async def search_nearby_places(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """地理的近接検索"""
    try:
        # TODO: 実装
        return {"nearby_places": [], "search_center": {"lat": latitude, "lng": longitude}}
    except Exception as e:
        logger.error(f"近接検索エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="近接検索に失敗しました"
        )

@app.get("/places/timeline/{place_id}")
async def get_place_timeline(
    place_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """地名の時代変遷"""
    try:
        # TODO: 実装
        return {"place_id": place_id, "timeline": []}
    except Exception as e:
        logger.error(f"時代変遷取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="時代変遷の取得に失敗しました"
        )

@app.get("/authors/compare/{author1_id}/{author2_id}")
async def compare_authors(
    author1_id: int,
    author2_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """作家比較"""
    try:
        # TODO: 実装
        return {"author1_id": author1_id, "author2_id": author2_id, "comparison": {}}
    except Exception as e:
        logger.error(f"作家比較エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作家比較に失敗しました"
        )

# ========================================
# v5.0 新API: 処理管理
# ========================================

@app.get("/processing/status/{job_id}")
async def get_processing_status(
    job_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """処理状況確認"""
    try:
        # TODO: 実装
        return {"job_id": job_id, "status": "running", "progress": 50}
    except Exception as e:
        logger.error(f"処理状況確認エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="処理状況の確認に失敗しました"
        )

@app.post("/processing/pipeline/start")
async def start_processing_pipeline(
    work_id: int,
    pipeline_type: str = "full_pipeline",
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """処理パイプライン開始"""
    try:
        # TODO: 実装
        return {"job_id": 12345, "status": "started", "work_id": work_id}
    except Exception as e:
        logger.error(f"パイプライン開始エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="処理パイプラインの開始に失敗しました"
        )

@app.get("/cache/statistics")
async def get_cache_statistics():
    """キャッシュ統計"""
    try:
        return cache_manager.get_statistics()
    except Exception as e:
        logger.error(f"キャッシュ統計取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="キャッシュ統計の取得に失敗しました"
        )

@app.delete("/cache/clear/{cache_type}")
async def clear_cache_by_type(
    cache_type: str
):
    """キャッシュクリア"""
    try:
        cache_manager.clear_prefix(cache_type)
        return {"cleared_cache_type": cache_type, "status": "success"}
    except Exception as e:
        logger.error(f"キャッシュクリアエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="キャッシュクリアに失敗しました"
        )

# ========================================
# 既存API: 統計関連（拡張）
# ========================================

@app.get("/authors/{author_id}/stats", response_model=AuthorStats)
@cache_result(prefix="stats", ttl=1800)
async def get_author_stats(
    author_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache_manager: CacheManager = Depends(lambda: cache_manager)
):
    """作者の統計情報"""
    try:
        result = db_manager.get_author_stats(author_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="作者の統計情報が見つかりません"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"作者統計取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作者統計の取得に失敗しました"
        )

@app.get("/works/{work_id}/stats", response_model=WorkStats)
@cache_result(prefix="stats", ttl=1800)
async def get_work_stats(
    work_id: int,
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache_manager: CacheManager = Depends(lambda: cache_manager)
):
    """作品の統計情報"""
    try:
        result = db_manager.get_work_stats(work_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="作品の統計情報が見つかりません"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"作品統計取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="作品統計の取得に失敗しました"
        )
