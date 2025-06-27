"""
API v5.0 エンドポイントテスト
作成日: 2025年6月25日
目的: フェーズ2で追加された新APIエンドポイントの包括的テスト
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, patch

from main import app
from core.models import *
from database.models import *

# テストクライアント
client = TestClient(app)

class TestHierarchicalStructureAPI:
    """階層構造API のテスト"""
    
    def test_get_work_sections(self):
        """GET /works/{work_id}/sections - 作品の章構造取得"""
        work_id = 1
        
        # モックデータでテスト
        with patch('database.crud.get_work_sections') as mock_get_sections:
            mock_sections = [
                {
                    "id": 1,
                    "work_id": work_id,
                    "section_type": "chapter",
                    "title": "第一章",
                    "section_number": 1,
                    "parent_section_id": None,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": 2,
                    "work_id": work_id,
                    "section_type": "sentence",
                    "content": "これは最初の文です。",
                    "section_number": 1,
                    "parent_section_id": 1,
                    "created_at": datetime.now().isoformat()
                }
            ]
            mock_get_sections.return_value = mock_sections
            
            response = client.get(f"/works/{work_id}/sections")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["section_type"] == "chapter"
            assert data[1]["section_type"] == "sentence"
            assert data[1]["parent_section_id"] == 1
    
    def test_create_section(self):
        """POST /sections/ - 章・段落・文の作成"""
        section_data = {
            "work_id": 1,
            "section_type": "chapter",
            "title": "新しい章",
            "content": "章の内容",
            "section_number": 2,
            "character_position": 1000
        }
        
        with patch('database.crud.create_section') as mock_create:
            mock_create.return_value = {
                "id": 10,
                **section_data,
                "created_at": datetime.now().isoformat()
            }
            
            response = client.post("/sections/", json=section_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 10
            assert data["title"] == "新しい章"
            assert data["section_type"] == "chapter"
    
    def test_get_section_children(self):
        """GET /sections/{section_id}/children - 子要素取得"""
        section_id = 1
        
        with patch('database.crud.get_section_children') as mock_get_children:
            mock_children = [
                {
                    "id": 2,
                    "section_type": "sentence",
                    "content": "子要素の文1",
                    "parent_section_id": section_id
                },
                {
                    "id": 3,
                    "section_type": "sentence", 
                    "content": "子要素の文2",
                    "parent_section_id": section_id
                }
            ]
            mock_get_children.return_value = mock_children
            
            response = client.get(f"/sections/{section_id}/children")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(child["parent_section_id"] == section_id for child in data)
    
    def test_get_section_context(self):
        """GET /sections/{section_id}/context - 文脈情報取得"""
        section_id = 5
        
        with patch('database.crud.get_section_context') as mock_get_context:
            mock_context = {
                "current_section": {
                    "id": section_id,
                    "content": "現在の文",
                    "section_type": "sentence"
                },
                "parent_section": {
                    "id": 1,
                    "title": "第一章",
                    "section_type": "chapter"
                },
                "previous_section": {
                    "id": 4,
                    "content": "前の文",
                    "section_type": "sentence"
                },
                "next_section": {
                    "id": 6,
                    "content": "次の文",
                    "section_type": "sentence"
                }
            }
            mock_get_context.return_value = mock_context
            
            response = client.get(f"/sections/{section_id}/context")
            
            assert response.status_code == 200
            data = response.json()
            assert data["current_section"]["id"] == section_id
            assert "parent_section" in data
            assert "previous_section" in data
            assert "next_section" in data


class TestAIVerificationAPI:
    """AI検証API のテスト"""
    
    def test_verify_single_place(self):
        """POST /ai/verify/place - 単一地名検証"""
        verification_request = {
            "place_mention_id": 1,
            "ai_model": "gpt-4",
            "verification_type": "place_validation",
            "input_context": "東京駅で待ち合わせをした。"
        }
        
        with patch('ai.verification_manager.AIVerificationManager.verify_place') as mock_verify:
            mock_verify.return_value = {
                "id": 1,
                "confidence_score": 0.95,
                "is_valid_place": True,
                "reasoning": "東京駅は明確な地名・駅名",
                "verification_status": "verified",
                **verification_request
            }
            
            response = client.post("/ai/verify/place", json=verification_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["confidence_score"] == 0.95
            assert data["is_valid_place"] is True
            assert "東京駅" in data["reasoning"]
    
    def test_verify_batch_places(self):
        """POST /ai/verify/batch - 一括地名検証"""
        batch_request = {
            "place_mention_ids": [1, 2, 3],
            "ai_model": "gpt-4",
            "verification_type": "place_validation"
        }
        
        with patch('ai.verification_manager.AIVerificationManager.batch_verify') as mock_batch:
            mock_batch.return_value = {
                "job_id": "batch_001",
                "total_places": 3,
                "status": "started",
                "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            
            response = client.post("/ai/verify/batch", json=batch_request)
            
            assert response.status_code == 202  # Accepted
            data = response.json()
            assert data["total_places"] == 3
            assert data["status"] == "started"
            assert "job_id" in data
    
    def test_get_verification_result(self):
        """GET /ai/verifications/{verification_id} - 検証結果取得"""
        verification_id = 1
        
        with patch('database.crud.get_ai_verification') as mock_get:
            mock_verification = {
                "id": verification_id,
                "place_mention_id": 1,
                "ai_model": "gpt-4",
                "verification_type": "place_validation",
                "confidence_score": 0.85,
                "is_valid_place": True,
                "reasoning": "検証完了",
                "verification_status": "verified",
                "verified_at": datetime.now().isoformat()
            }
            mock_get.return_value = mock_verification
            
            response = client.get(f"/ai/verifications/{verification_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == verification_id
            assert data["verification_status"] == "verified"
    
    def test_get_place_verification_history(self):
        """GET /places/{place_id}/verifications - 地名の検証履歴"""
        place_id = 1
        
        with patch('database.crud.get_place_verification_history') as mock_get_history:
            mock_history = [
                {
                    "id": 1,
                    "ai_model": "gpt-3.5-turbo",
                    "confidence_score": 0.75,
                    "verified_at": (datetime.now() - timedelta(days=1)).isoformat()
                },
                {
                    "id": 2,
                    "ai_model": "gpt-4",
                    "confidence_score": 0.95,
                    "verified_at": datetime.now().isoformat()
                }
            ]
            mock_get_history.return_value = mock_history
            
            response = client.get(f"/places/{place_id}/verifications")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[1]["ai_model"] == "gpt-4"  # 最新のもの


class TestStatisticsAnalysisAPI:
    """統計・分析API のテスト"""
    
    def test_get_global_statistics(self):
        """GET /statistics/global - システム全体統計"""
        with patch('core.statistics_engine.StatisticsEngine.get_global_stats') as mock_stats:
            mock_global_stats = {
                "total_works": 150,
                "total_places": 2500,
                "verified_places": 2100,
                "accuracy_rate": 0.84,
                "ai_verifications": 1800,
                "cache_hit_rate": 0.65,
                "last_updated": datetime.now().isoformat()
            }
            mock_stats.return_value = mock_global_stats
            
            response = client.get("/statistics/global")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_works"] == 150
            assert data["accuracy_rate"] == 0.84
            assert "last_updated" in data
    
    def test_get_geographical_statistics(self):
        """GET /statistics/geographical/{region} - 地域別統計"""
        region = "tokyo"
        
        with patch('core.statistics_engine.StatisticsEngine.get_regional_stats') as mock_regional:
            mock_regional_stats = {
                "region": region,
                "place_count": 450,
                "work_count": 75,
                "most_mentioned_places": [
                    {"name": "東京駅", "count": 45},
                    {"name": "新宿", "count": 32},
                    {"name": "渋谷", "count": 28}
                ],
                "top_authors": [
                    {"name": "夏目漱石", "mention_count": 25},
                    {"name": "森鴎外", "mention_count": 18}
                ]
            }
            mock_regional.return_value = mock_regional_stats
            
            response = client.get(f"/statistics/geographical/{region}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["region"] == region
            assert data["place_count"] == 450
            assert len(data["most_mentioned_places"]) == 3
    
    def test_nearby_place_search(self):
        """GET /places/search/nearby - 地理的近接検索"""
        params = {
            "latitude": 35.6762,
            "longitude": 139.6503,
            "radius_km": 5,
            "limit": 10
        }
        
        with patch('ai.geospatial_analyzer.GeoSpatialAnalyzer.find_nearby_places') as mock_nearby:
            mock_nearby_places = [
                {
                    "id": 1,
                    "name": "東京駅",
                    "latitude": 35.6812,
                    "longitude": 139.7671,
                    "distance_km": 1.2,
                    "mention_count": 45
                },
                {
                    "id": 2,
                    "name": "皇居",
                    "latitude": 35.6852,
                    "longitude": 139.7528,
                    "distance_km": 2.1,
                    "mention_count": 12
                }
            ]
            mock_nearby.return_value = mock_nearby_places
            
            response = client.get("/places/search/nearby", params=params)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["distance_km"] == 1.2
            assert all(place["distance_km"] <= 5 for place in data)
    
    def test_place_timeline(self):
        """GET /places/timeline/{place_id} - 地名の時代変遷"""
        place_id = 1
        
        with patch('core.statistics_engine.StatisticsEngine.get_place_timeline') as mock_timeline:
            mock_timeline_data = {
                "place_id": place_id,
                "place_name": "東京",
                "timeline": [
                    {
                        "period": "明治時代",
                        "mention_count": 15,
                        "representative_works": ["こころ", "坊っちゃん"]
                    },
                    {
                        "period": "大正時代", 
                        "mention_count": 28,
                        "representative_works": ["羅生門", "鼻"]
                    },
                    {
                        "period": "昭和時代",
                        "mention_count": 42,
                        "representative_works": ["雪国", "伊豆の踊子"]
                    }
                ]
            }
            mock_timeline.return_value = mock_timeline_data
            
            response = client.get(f"/places/timeline/{place_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["place_id"] == place_id
            assert len(data["timeline"]) == 3
            assert data["timeline"][2]["period"] == "昭和時代"
    
    def test_author_comparison(self):
        """GET /authors/compare/{author1_id}/{author2_id} - 作家比較"""
        author1_id, author2_id = 1, 2
        
        with patch('core.statistics_engine.StatisticsEngine.compare_authors') as mock_compare:
            mock_comparison = {
                "author1": {
                    "id": author1_id,
                    "name": "夏目漱石",
                    "total_places": 150,
                    "unique_places": 85,
                    "most_mentioned_region": "東京"
                },
                "author2": {
                    "id": author2_id,
                    "name": "森鴎外",
                    "total_places": 120,
                    "unique_places": 78,
                    "most_mentioned_region": "東京"
                },
                "comparison": {
                    "common_places": 45,
                    "similarity_score": 0.72,
                    "distinctive_places_author1": ["神田", "本郷"],
                    "distinctive_places_author2": ["上野", "浅草"]
                }
            }
            mock_compare.return_value = mock_comparison
            
            response = client.get(f"/authors/compare/{author1_id}/{author2_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["author1"]["name"] == "夏目漱石"
            assert data["author2"]["name"] == "森鴎外"
            assert data["comparison"]["common_places"] == 45


class TestProcessingManagementAPI:
    """処理管理API のテスト"""
    
    def test_get_processing_status(self):
        """GET /processing/status/{job_id} - 処理状況確認"""
        job_id = "job_12345"
        
        with patch('core.processing_manager.ProcessingManager.get_job_status') as mock_status:
            mock_job_status = {
                "job_id": job_id,
                "status": "processing",
                "progress_percentage": 65,
                "current_step": "ai_verification",
                "estimated_completion": (datetime.now() + timedelta(minutes=10)).isoformat(),
                "processed_items": 650,
                "total_items": 1000
            }
            mock_status.return_value = mock_job_status
            
            response = client.get(f"/processing/status/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == job_id
            assert data["progress_percentage"] == 65
            assert data["current_step"] == "ai_verification"
    
    def test_start_processing_pipeline(self):
        """POST /processing/pipeline/start - 処理パイプライン開始"""
        pipeline_config = {
            "work_id": 1,
            "pipeline_type": "full_pipeline",
            "ai_model": "gpt-4",
            "batch_size": 50,
            "enable_verification": True
        }
        
        with patch('core.processing_manager.ProcessingManager.start_pipeline') as mock_start:
            mock_start.return_value = {
                "job_id": "pipeline_67890",
                "status": "started",
                "estimated_duration_minutes": 15,
                "started_at": datetime.now().isoformat()
            }
            
            response = client.post("/processing/pipeline/start", json=pipeline_config)
            
            assert response.status_code == 202  # Accepted
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "started"
    
    def test_get_cache_statistics(self):
        """GET /cache/statistics - キャッシュ統計"""
        with patch('core.cache_v2.CacheManager.get_cache_stats') as mock_cache_stats:
            mock_stats = {
                "total_entries": 1500,
                "hit_rate": 0.78,
                "memory_usage_mb": 256,
                "expired_entries": 45,
                "cache_types": {
                    "global_stats": {"entries": 5, "hit_rate": 0.95},
                    "author_stats": {"entries": 150, "hit_rate": 0.82},
                    "place_stats": {"entries": 800, "hit_rate": 0.75}
                }
            }
            mock_cache_stats.return_value = mock_stats
            
            response = client.get("/cache/statistics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["hit_rate"] == 0.78
            assert data["total_entries"] == 1500
            assert "cache_types" in data
    
    def test_clear_cache(self):
        """DELETE /cache/clear/{cache_type} - キャッシュクリア"""
        cache_type = "global_stats"
        
        with patch('core.cache_v2.CacheManager.clear_cache_type') as mock_clear:
            mock_clear.return_value = {
                "cache_type": cache_type,
                "cleared_entries": 5,
                "status": "success"
            }
            
            response = client.delete(f"/cache/clear/{cache_type}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["cache_type"] == cache_type
            assert data["cleared_entries"] == 5


class TestAPIErrorHandling:
    """API エラーハンドリングテスト"""
    
    def test_not_found_errors(self):
        """404エラーのテスト"""
        # 存在しない作品
        response = client.get("/works/99999/sections")
        assert response.status_code == 404
        
        # 存在しない検証結果
        response = client.get("/ai/verifications/99999")
        assert response.status_code == 404
        
        # 存在しない処理ジョブ
        response = client.get("/processing/status/nonexistent_job")
        assert response.status_code == 404
    
    def test_validation_errors(self):
        """バリデーションエラーのテスト"""
        # 無効なセクションデータ
        invalid_section = {
            "work_id": "invalid",  # 数値でない
            "section_type": "invalid_type",  # 無効な列挙値
            "content": "",  # 空文字
        }
        
        response = client.post("/sections/", json=invalid_section)
        assert response.status_code == 422
        
        # 無効な座標での近接検索
        invalid_params = {
            "latitude": 200,  # 無効な緯度
            "longitude": -200,  # 無効な経度
            "radius_km": -5  # 負の半径
        }
        
        response = client.get("/places/search/nearby", params=invalid_params)
        assert response.status_code == 422
    
    def test_rate_limiting(self):
        """レート制限のテスト"""
        # AI検証APIのレート制限をテスト
        verification_request = {
            "place_mention_id": 1,
            "ai_model": "gpt-4",
            "verification_type": "place_validation"
        }
        
        with patch('ai.verification_manager.AIVerificationManager.verify_place') as mock_verify:
            # レート制限エラーをシミュレート
            mock_verify.side_effect = Exception("Rate limit exceeded")
            
            response = client.post("/ai/verify/place", json=verification_request)
            assert response.status_code == 429  # Too Many Requests


class TestAPIPerformance:
    """API パフォーマンステスト"""
    
    def test_response_time_requirements(self):
        """レスポンス時間要件のテスト"""
        import time
        
        # 統計APIのレスポンス時間テスト
        with patch('core.statistics_engine.StatisticsEngine.get_global_stats') as mock_stats:
            mock_stats.return_value = {"total_works": 100}
            
            start_time = time.time()
            response = client.get("/statistics/global")
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            assert response_time < 0.2  # 200ms以内の要件
    
    def test_concurrent_requests(self):
        """同時リクエストのテスト"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            response = client.get("/statistics/global")
            results.put(response.status_code)
        
        # 10の同時リクエスト
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 全てのリクエストが成功することを確認
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        assert len(status_codes) == 10
        assert all(code == 200 for code in status_codes)


if __name__ == "__main__":
    # 基本的なテスト実行
    pytest.main([__file__, "-v"]) 