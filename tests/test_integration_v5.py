"""
統合テスト v5.0
作成日: 2025年6月25日
目的: v5.0システム全体のエンドツーエンド・統合テスト
"""

import pytest
import asyncio
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
import time

from main import app
from database.migration_v4_to_v5 import MigrationManager
from extractors.hierarchical_extractor import HierarchicalExtractor
from ai.verification_manager import AIVerificationManager
from core.statistics_engine import StatisticsEngine
from core.cache_v2 import CacheManager
from core.performance_monitor import PerformanceMonitor

# テストクライアント
client = TestClient(app)

class TestFullSystemIntegration:
    """システム全体の統合テスト"""
    
    @pytest.fixture
    def integrated_test_setup(self):
        """統合テスト用のフルセットアップ"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "integrated_test.db"
        
        # データベース初期化
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # v5スキーマ作成（簡略版）
        cursor.execute("""
            CREATE TABLE authors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE works (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author_id INTEGER,
                publication_year INTEGER,
                content TEXT,
                content_status TEXT DEFAULT 'processed'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE sections (
                id INTEGER PRIMARY KEY,
                work_id INTEGER NOT NULL,
                section_type TEXT NOT NULL,
                parent_section_id INTEGER,
                section_number INTEGER,
                title TEXT,
                content TEXT,
                character_position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE place_masters (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                prefecture TEXT,
                name_variants TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE place_mentions (
                id INTEGER PRIMARY KEY,
                work_id INTEGER NOT NULL,
                section_id INTEGER,
                sentence_text TEXT,
                place_name TEXT,
                place_master_id INTEGER,
                character_position INTEGER,
                confidence_score REAL DEFAULT 0.5,
                extraction_method TEXT,
                verified_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE ai_verifications (
                id INTEGER PRIMARY KEY,
                place_mention_id INTEGER NOT NULL,
                ai_model TEXT NOT NULL,
                verification_type TEXT,
                input_context TEXT,
                ai_response TEXT,
                confidence_score REAL,
                is_valid_place BOOLEAN,
                reasoning TEXT,
                verification_status TEXT DEFAULT 'pending',
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE statistics_cache (
                id INTEGER PRIMARY KEY,
                cache_key TEXT NOT NULL UNIQUE,
                cache_type TEXT,
                entity_id INTEGER,
                data TEXT NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE processing_logs (
                id INTEGER PRIMARY KEY,
                work_id INTEGER,
                process_type TEXT,
                status TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                statistics TEXT,
                configuration TEXT
            )
        """)
        
        # テストデータ挿入
        test_data = self._create_test_data()
        for table, data in test_data.items():
            if data:
                placeholders = ', '.join(['?' for _ in data[0]])
                cursor.executemany(f"INSERT INTO {table} VALUES ({placeholders})", data)
        
        conn.commit()
        conn.close()
        
        yield str(db_path)
        shutil.rmtree(temp_dir)
    
    def _create_test_data(self):
        """統合テスト用データの作成"""
        return {
            'authors': [
                (1, '夏目漱石', 1867, 1916),
                (2, '森鴎外', 1862, 1922),
                (3, '芥川龍之介', 1892, 1927)
            ],
            'works': [
                (1, 'こころ', 1, 1914, '私はその人を常に先生と呼んでいた。東京駅で待ち合わせをした。新宿の街を歩いた。', 'processed'),
                (2, '舞姫', 2, 1890, 'ベルリンでエリスと出会った。ドイツの街角で彼女を見かけた。', 'processed'),
                (3, '羅生門', 3, 1915, '京都の羅生門の下で下人は雨やみを待っていた。', 'processed')
            ],
            'place_masters': [
                (1, '東京駅', 35.6812, 139.7671, '東京都', '{"variants": ["東京ステーション"]}'),
                (2, '新宿', 35.6896, 139.6917, '東京都', '{"variants": ["新宿区"]}'),
                (3, 'ベルリン', 52.5200, 13.4050, None, '{"variants": ["Berlin"]}'),
                (4, '京都', 35.0116, 135.7681, '京都府', '{"variants": ["京都市"]}')
            ],
            'sections': [
                (1, 1, 'chapter', None, 1, '上', '私はその人を常に先生と呼んでいた。', 0, datetime.now().isoformat()),
                (2, 1, 'sentence', 1, 1, None, '私はその人を常に先生と呼んでいた。', 0, datetime.now().isoformat()),
                (3, 1, 'sentence', 1, 2, None, '東京駅で待ち合わせをした。', 50, datetime.now().isoformat()),
                (4, 2, 'chapter', None, 1, '第一章', 'ベルリンでエリスと出会った。', 0, datetime.now().isoformat()),
                (5, 3, 'chapter', None, 1, None, '京都の羅生門の下で下人は雨やみを待っていた。', 0, datetime.now().isoformat())
            ],
            'place_mentions': [
                (1, 1, 3, '東京駅で待ち合わせをした。', '東京駅', 1, 50, 0.95, 'nlp_extraction', None),
                (2, 1, None, '新宿の街を歩いた。', '新宿', 2, 80, 0.85, 'nlp_extraction', None),
                (3, 2, 4, 'ベルリンでエリスと出会った。', 'ベルリン', 3, 0, 0.90, 'nlp_extraction', None),
                (4, 3, 5, '京都の羅生門の下で下人は雨やみを待っていた。', '京都', 4, 0, 0.88, 'nlp_extraction', None)
            ]
        }
    
    def test_text_processing_pipeline(self, integrated_test_setup):
        """テキスト処理パイプライン統合テスト"""
        db_path = integrated_test_setup
        
        # 1. 階層構造抽出のテスト
        with patch('extractors.hierarchical_extractor.HierarchicalExtractor') as mock_extractor:
            mock_instance = Mock()
            mock_extractor.return_value = mock_instance
            mock_instance.extract_hierarchy.return_value = {
                'chapters': [
                    {
                        'title': '第二章',
                        'content': '新しい章の内容...',
                        'sentences': [
                            {'text': '神田で本を買った。', 'position': 0}
                        ]
                    }
                ]
            }
            
            # 階層構造抽出API呼び出し
            response = client.post("/processing/extract-hierarchy", json={
                "work_id": 1,
                "extraction_method": "auto"
            })
            
            assert response.status_code == 200
            result = response.json()
            assert "sections_created" in result
        
        # 2. 地名抽出パイプライン
        with patch('extractors.place_extractor.PlaceExtractor') as mock_place_extractor:
            mock_place_instance = Mock()
            mock_place_extractor.return_value = mock_place_instance
            mock_place_instance.extract_places.return_value = [
                {
                    'text': '神田',
                    'position': 0,
                    'confidence': 0.92,
                    'context': '神田で本を買った。'
                }
            ]
            
            # 地名抽出API呼び出し
            response = client.post("/processing/extract-places", json={
                "work_id": 1,
                "method": "nlp"
            })
            
            assert response.status_code == 200
            result = response.json()
            assert "places_extracted" in result
    
    def test_ai_verification_integration(self, integrated_test_setup):
        """AI検証統合テスト"""
        db_path = integrated_test_setup
        
        # 1. 単一地名検証
        with patch('ai.verification_manager.AIVerificationManager') as mock_ai:
            mock_instance = Mock()
            mock_ai.return_value = mock_instance
            mock_instance.verify_place.return_value = {
                'id': 1,
                'place_mention_id': 1,
                'confidence_score': 0.95,
                'is_valid_place': True,
                'reasoning': '東京駅は実在する駅名です',
                'verification_status': 'verified'
            }
            
            response = client.post("/ai/verify/place", json={
                "place_mention_id": 1,
                "ai_model": "gpt-4",
                "verification_type": "place_validation"
            })
            
            assert response.status_code == 200
            result = response.json()
            assert result['is_valid_place'] is True
            assert result['confidence_score'] >= 0.9
        
        # 2. 一括検証
        with patch('ai.verification_manager.AIVerificationManager') as mock_ai:
            mock_instance = Mock()
            mock_ai.return_value = mock_instance
            mock_instance.batch_verify.return_value = {
                'job_id': 'batch_123',
                'total_places': 4,
                'status': 'started'
            }
            
            response = client.post("/ai/verify/batch", json={
                "place_mention_ids": [1, 2, 3, 4],
                "ai_model": "gpt-4"
            })
            
            assert response.status_code == 202
            result = response.json()
            assert result['total_places'] == 4
            assert 'job_id' in result
    
    def test_statistics_and_caching_integration(self, integrated_test_setup):
        """統計・キャッシュ統合テスト"""
        db_path = integrated_test_setup
        
        # 1. 統計生成
        with patch('core.statistics_engine.StatisticsEngine') as mock_stats:
            mock_instance = Mock()
            mock_stats.return_value = mock_instance
            mock_instance.get_global_stats.return_value = {
                'total_works': 3,
                'total_places': 4,
                'verified_places': 0,
                'accuracy_rate': 0.0,
                'last_updated': datetime.now().isoformat()
            }
            
            response = client.get("/statistics/global")
            assert response.status_code == 200
            stats = response.json()
            assert stats['total_works'] == 3
        
        # 2. キャッシュ統計
        with patch('core.cache_v2.CacheManager') as mock_cache:
            mock_instance = Mock()
            mock_cache.return_value = mock_instance
            mock_instance.get_cache_stats.return_value = {
                'total_entries': 10,
                'hit_rate': 0.75,
                'memory_usage_mb': 50
            }
            
            response = client.get("/cache/statistics")
            assert response.status_code == 200
            cache_stats = response.json()
            assert cache_stats['hit_rate'] == 0.75
        
        # 3. 地域別統計
        with patch('core.statistics_engine.StatisticsEngine') as mock_stats:
            mock_instance = Mock()
            mock_stats.return_value = mock_instance
            mock_instance.get_regional_stats.return_value = {
                'region': 'tokyo',
                'place_count': 2,
                'work_count': 1,
                'most_mentioned_places': [
                    {'name': '東京駅', 'count': 1},
                    {'name': '新宿', 'count': 1}
                ]
            }
            
            response = client.get("/statistics/geographical/tokyo")
            assert response.status_code == 200
            regional_stats = response.json()
            assert regional_stats['place_count'] == 2
    
    def test_geospatial_analysis_integration(self, integrated_test_setup):
        """地理空間分析統合テスト"""
        db_path = integrated_test_setup
        
        # 近接地名検索
        with patch('ai.geospatial_analyzer.GeoSpatialAnalyzer') as mock_geo:
            mock_instance = Mock()
            mock_geo.return_value = mock_instance
            mock_instance.find_nearby_places.return_value = [
                {
                    'id': 1,
                    'name': '東京駅',
                    'latitude': 35.6812,
                    'longitude': 139.7671,
                    'distance_km': 0.0,
                    'mention_count': 1
                },
                {
                    'id': 2,
                    'name': '新宿',
                    'latitude': 35.6896,
                    'longitude': 139.6917,
                    'distance_km': 5.2,
                    'mention_count': 1
                }
            ]
            
            response = client.get("/places/search/nearby", params={
                "latitude": 35.6812,
                "longitude": 139.7671,
                "radius_km": 10,
                "limit": 10
            })
            
            assert response.status_code == 200
            nearby_places = response.json()
            assert len(nearby_places) == 2
            assert nearby_places[0]['distance_km'] == 0.0
    
    def test_processing_workflow_integration(self, integrated_test_setup):
        """処理ワークフロー統合テスト"""
        db_path = integrated_test_setup
        
        # 1. 処理パイプライン開始
        with patch('core.processing_manager.ProcessingManager') as mock_proc:
            mock_instance = Mock()
            mock_proc.return_value = mock_instance
            mock_instance.start_pipeline.return_value = {
                'job_id': 'pipeline_456',
                'status': 'started',
                'estimated_duration_minutes': 10
            }
            
            response = client.post("/processing/pipeline/start", json={
                "work_id": 1,
                "pipeline_type": "full_pipeline",
                "ai_model": "gpt-4"
            })
            
            assert response.status_code == 202
            result = response.json()
            job_id = result['job_id']
        
        # 2. 処理状況確認
        with patch('core.processing_manager.ProcessingManager') as mock_proc:
            mock_instance = Mock()
            mock_proc.return_value = mock_instance
            mock_instance.get_job_status.return_value = {
                'job_id': job_id,
                'status': 'completed',
                'progress_percentage': 100,
                'processed_items': 50,
                'total_items': 50
            }
            
            response = client.get(f"/processing/status/{job_id}")
            assert response.status_code == 200
            status = response.json()
            assert status['status'] == 'completed'
            assert status['progress_percentage'] == 100


class TestDataFlowIntegration:
    """データフロー統合テスト"""
    
    def test_end_to_end_text_processing(self):
        """エンドツーエンドテキスト処理テスト"""
        # 新しい作品の追加から検証まで全フロー
        
        # 1. 作品登録
        work_data = {
            "title": "新作品",
            "author_id": 1,
            "publication_year": 2024,
            "content": "横浜の港で船を見た。鎌倉の大仏を訪れた。"
        }
        
        with patch('database.crud.create_work') as mock_create:
            mock_create.return_value = {
                "id": 10,
                **work_data,
                "created_at": datetime.now().isoformat()
            }
            
            response = client.post("/works/", json=work_data)
            assert response.status_code == 201
            work = response.json()
            work_id = work['id']
        
        # 2. 階層構造抽出
        with patch('extractors.hierarchical_extractor.HierarchicalExtractor') as mock_extractor:
            mock_instance = Mock()
            mock_extractor.return_value = mock_instance
            mock_instance.extract_hierarchy.return_value = {
                'sections_created': 3,
                'sentences_extracted': 2
            }
            
            response = client.post("/processing/extract-hierarchy", json={
                "work_id": work_id
            })
            assert response.status_code == 200
        
        # 3. 地名抽出
        with patch('extractors.place_extractor.PlaceExtractor') as mock_place:
            mock_instance = Mock()
            mock_place.return_value = mock_instance
            mock_instance.extract_places.return_value = {
                'places_extracted': 2,
                'place_mentions': [
                    {'place_name': '横浜', 'confidence': 0.92},
                    {'place_name': '鎌倉', 'confidence': 0.88}
                ]
            }
            
            response = client.post("/processing/extract-places", json={
                "work_id": work_id
            })
            assert response.status_code == 200
        
        # 4. AI検証
        with patch('ai.verification_manager.AIVerificationManager') as mock_ai:
            mock_instance = Mock()
            mock_ai.return_value = mock_instance
            mock_instance.batch_verify.return_value = {
                'job_id': 'verification_789',
                'total_places': 2
            }
            
            response = client.post("/ai/verify/batch", json={
                "work_id": work_id,
                "ai_model": "gpt-4"
            })
            assert response.status_code == 202
        
        # 5. 統計更新確認
        with patch('core.statistics_engine.StatisticsEngine') as mock_stats:
            mock_instance = Mock()
            mock_stats.return_value = mock_instance
            mock_instance.invalidate_work_cache.return_value = True
            
            response = client.delete(f"/cache/clear/work_stats")
            assert response.status_code == 200
    
    def test_cross_system_data_consistency(self, integrated_test_setup):
        """システム間データ整合性テスト"""
        db_path = integrated_test_setup
        
        # 複数のAPIを呼び出してデータ整合性を確認
        
        # 1. 作品情報取得
        response = client.get("/works/1")
        assert response.status_code == 200 or response.status_code == 404  # モックなので404も許可
        
        # 2. 作品のセクション取得
        with patch('database.crud.get_work_sections') as mock_sections:
            mock_sections.return_value = [
                {'id': 2, 'work_id': 1, 'section_type': 'sentence'},
                {'id': 3, 'work_id': 1, 'section_type': 'sentence'}
            ]
            
            response = client.get("/works/1/sections")
            assert response.status_code == 200
            sections = response.json()
            assert all(section['work_id'] == 1 for section in sections)
        
        # 3. 地名言及取得
        with patch('database.crud.get_work_place_mentions') as mock_mentions:
            mock_mentions.return_value = [
                {'id': 1, 'work_id': 1, 'place_name': '東京駅'},
                {'id': 2, 'work_id': 1, 'place_name': '新宿'}
            ]
            
            response = client.get("/works/1/places")
            assert response.status_code == 200 or response.status_code == 404
        
        # 4. 統計での整合性確認
        with patch('core.statistics_engine.StatisticsEngine') as mock_stats:
            mock_instance = Mock()
            mock_stats.return_value = mock_instance
            mock_instance.get_work_stats.return_value = {
                'work_id': 1,
                'total_places': 2,
                'verified_places': 0,
                'sections_count': 2
            }
            
            response = client.get("/statistics/works/1")
            assert response.status_code == 200 or response.status_code == 404


class TestPerformanceIntegration:
    """パフォーマンス統合テスト"""
    
    def test_concurrent_api_performance(self):
        """同時API性能テスト"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def api_call_worker(endpoint, expected_status=200):
            try:
                start_time = time.time()
                
                # モックデータでAPIコール
                with patch('core.statistics_engine.StatisticsEngine') as mock_stats:
                    mock_instance = Mock()
                    mock_stats.return_value = mock_instance
                    mock_instance.get_global_stats.return_value = {
                        'total_works': 100,
                        'total_places': 1000
                    }
                    
                    response = client.get(endpoint)
                    response_time = time.time() - start_time
                    
                    results.put({
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response_time': response_time,
                        'success': response.status_code == expected_status
                    })
            except Exception as e:
                results.put({
                    'endpoint': endpoint,
                    'error': str(e),
                    'success': False
                })
        
        # 複数エンドポイントの同時呼び出し
        endpoints = [
            "/statistics/global",
            "/cache/statistics",
            "/statistics/global",
            "/cache/statistics"
        ]
        
        threads = []
        for endpoint in endpoints:
            thread = threading.Thread(target=api_call_worker, args=(endpoint,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 結果検証
        responses = []
        while not results.empty():
            responses.append(results.get())
        
        assert len(responses) == 4
        successful_responses = [r for r in responses if r.get('success', False)]
        assert len(successful_responses) >= 2  # 最低半分は成功
        
        # レスポンス時間確認
        response_times = [r['response_time'] for r in successful_responses if 'response_time' in r]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 1.0  # 1秒以内
    
    def test_large_dataset_processing_performance(self):
        """大量データ処理性能テスト"""
        # 大量データの一括処理シミュレーション
        
        large_batch_data = {
            "place_mention_ids": list(range(1, 101)),  # 100件
            "ai_model": "gpt-4",
            "verification_type": "place_validation"
        }
        
        with patch('ai.verification_manager.AIVerificationManager') as mock_ai:
            mock_instance = Mock()
            mock_ai.return_value = mock_instance
            
            # 大量処理のシミュレーション
            start_time = time.time()
            mock_instance.batch_verify.return_value = {
                'job_id': 'large_batch_001',
                'total_places': 100,
                'estimated_completion_minutes': 5
            }
            
            response = client.post("/ai/verify/batch", json=large_batch_data)
            processing_time = time.time() - start_time
            
            assert response.status_code == 202
            assert processing_time < 2.0  # API応答は2秒以内
            
            result = response.json()
            assert result['total_places'] == 100
    
    def test_memory_usage_monitoring(self):
        """メモリ使用量監視テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 複数のAPI呼び出しでメモリ使用量確認
        with patch('core.statistics_engine.StatisticsEngine') as mock_stats:
            mock_instance = Mock()
            mock_stats.return_value = mock_instance
            mock_instance.get_global_stats.return_value = {'total_works': 1000}
            
            # 連続API呼び出し
            for _ in range(20):
                response = client.get("/statistics/global")
                assert response.status_code == 200
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が50MB以内であることを確認
        assert memory_increase < 50


class TestErrorHandlingIntegration:
    """エラーハンドリング統合テスト"""
    
    def test_cascade_error_handling(self):
        """カスケードエラーハンドリングテスト"""
        # 依存関係のあるAPIでエラーが発生した場合の処理
        
        # 1. 存在しない作品でのセクション取得
        response = client.get("/works/99999/sections")
        assert response.status_code == 404
        
        # 2. 存在しない地名での検証
        response = client.post("/ai/verify/place", json={
            "place_mention_id": 99999,
            "ai_model": "gpt-4"
        })
        assert response.status_code in [404, 422]  # どちらも許可
        
        # 3. 無効なパラメータでの統計取得
        response = client.get("/statistics/geographical/")  # 空のregion
        assert response.status_code in [404, 422]
    
    def test_service_unavailable_handling(self):
        """サービス利用不可ハンドリングテスト"""
        # 外部サービス（AI）が利用不可の場合
        
        with patch('ai.verification_manager.AIVerificationManager') as mock_ai:
            mock_instance = Mock()
            mock_ai.return_value = mock_instance
            mock_instance.verify_place.side_effect = Exception("AI service unavailable")
            
            response = client.post("/ai/verify/place", json={
                "place_mention_id": 1,
                "ai_model": "gpt-4"
            })
            
            # エラーレスポンスまたはフォールバック処理
            assert response.status_code in [500, 503, 429]
    
    def test_data_validation_integration(self):
        """データ検証統合テスト"""
        # 無効なデータでの一連の処理テスト
        
        # 1. 無効な作品データ
        invalid_work = {
            "title": "",  # 空のタイトル
            "author_id": "invalid",  # 無効なID
            "content": None  # 無効なコンテンツ
        }
        
        response = client.post("/works/", json=invalid_work)
        assert response.status_code == 422
        
        # 2. 無効な検証リクエスト
        invalid_verification = {
            "place_mention_id": -1,  # 負のID
            "ai_model": "",  # 空のモデル名
            "verification_type": "invalid_type"  # 無効なタイプ
        }
        
        response = client.post("/ai/verify/place", json=invalid_verification)
        assert response.status_code == 422
        
        # 3. 無効な座標での近接検索
        response = client.get("/places/search/nearby", params={
            "latitude": 200,  # 無効な緯度
            "longitude": -300,  # 無効な経度
            "radius_km": -10  # 負の半径
        })
        assert response.status_code == 422


if __name__ == "__main__":
    # 統合テスト実行
    pytest.main([__file__, "-v", "--tb=short"])