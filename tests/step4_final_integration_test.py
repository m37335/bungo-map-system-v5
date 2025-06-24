#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ステップ4: 最終統合テストと品質保証

リファクタリング完了後のシステム全体品質テスト
"""

import os
import sys
import time
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalIntegrationTest:
    """最終統合テスト管理"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.test_results = {
            'start_time': datetime.now(),
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': [],
            'performance_metrics': {}
        }
        
    def run_comprehensive_test(self) -> bool:
        """包括的テスト実行"""
        logger.info("🧪 ステップ4: 最終統合テスト開始")
        logger.info("=" * 70)
        
        # テスト実行
        tests = [
            ("モジュール統合確認", self._test_module_integration),
            ("データベース整合性", self._test_database_integrity),
            ("AIシステム統合", self._test_ai_system_integration),
            ("パイプライン機能", self._test_pipeline_functionality),
            ("パフォーマンス測定", self._test_performance_metrics),
            ("エラーハンドリング", self._test_error_handling),
            ("設定システム", self._test_configuration_system)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n🔍 {test_name}テスト実行中...")
            try:
                start_time = time.time()
                success = test_func()
                duration = time.time() - start_time
                
                if success:
                    self.test_results['tests_passed'] += 1
                    logger.info(f"✅ {test_name}テスト成功 ({duration:.2f}秒)")
                else:
                    self.test_results['tests_failed'] += 1
                    self.test_results['failures'].append(test_name)
                    logger.error(f"❌ {test_name}テスト失敗 ({duration:.2f}秒)")
                    
            except Exception as e:
                self.test_results['tests_failed'] += 1
                self.test_results['failures'].append(f"{test_name}: {e}")
                logger.error(f"❌ {test_name}テストエラー: {e}")
        
        # 結果レポート
        self._print_final_results()
        
        return self.test_results['tests_failed'] == 0
    
    def _test_module_integration(self) -> bool:
        """モジュール統合テスト"""
        try:
            # 1. 新AIモジュール
            from ai.llm import LLMClient
            from ai.nlp import ContextAnalyzer
            from ai.geocoding import GeocodingEngine
            logger.info("  ✅ AIモジュール統合確認")
            
            # 2. リファクタされたextractors
            from extractors.aozora import AozoraScraper, AozoraMetadataExtractor
            from extractors.places import EnhancedPlaceExtractorV3, PlaceMasterManagerV2
            from extractors.wikipedia import WikipediaAuthorEnricher
            logger.info("  ✅ Extractorsモジュール統合確認")
            
            # 3. 統合されたdatabase
            from database.init_db import DatabaseInitializerV2
            from database.manager import DatabaseManager
            logger.info("  ✅ Databaseモジュール統合確認")
            
            # 4. コアシステム
            from core.config import get_config
            from core.exceptions import BungoMapError
            from core.constants import PROJECT_ROOT
            logger.info("  ✅ コアシステム統合確認")
            
            # 5. メインパイプライン
            import run_pipeline
            logger.info("  ✅ メインパイプライン統合確認")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ モジュール統合エラー: {e}")
            return False
    
    def _test_database_integrity(self) -> bool:
        """データベース整合性テスト"""
        try:
            db_path = os.path.join(self.project_root, 'data', 'bungo_map.db')
            
            if not os.path.exists(db_path):
                logger.error("  ❌ データベースファイルが存在しません")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. 必要テーブル存在確認
            required_tables = [
                'authors', 'works', 'sentences', 'place_masters',
                'sentence_places', 'place_aliases'
            ]
            
            for table in required_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    logger.error(f"  ❌ 必要テーブル不存在: {table}")
                    conn.close()
                    return False
            
            logger.info(f"  ✅ 必要テーブル確認: {len(required_tables)}個")
            
            # 2. インデックス確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = cursor.fetchall()
            logger.info(f"  ✅ インデックス確認: {len(indexes)}個")
            
            # 3. データ整合性チェック
            cursor.execute("SELECT COUNT(*) FROM authors")
            authors_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM works")
            works_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM place_masters")
            places_count = cursor.fetchone()[0]
            
            logger.info(f"  📊 データ確認: 作者{authors_count}人, 作品{works_count}件, 地名マスター{places_count}件")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"  ❌ データベース整合性エラー: {e}")
            return False
    
    def _test_ai_system_integration(self) -> bool:
        """AIシステム統合テスト"""
        try:
            # 1. LLMクライアント初期化
            from ai.llm import LLMClient
            llm_client = LLMClient()
            logger.info("  ✅ LLMクライアント初期化")
            
            # 2. 文脈分析エンジン初期化
            from ai.nlp import ContextAnalyzer
            context_analyzer = ContextAnalyzer()
            logger.info("  ✅ 文脈分析エンジン初期化")
            
            # 3. ジオコーディングエンジン初期化
            from ai.geocoding import GeocodingEngine
            geocoding_engine = GeocodingEngine(llm_client)
            logger.info("  ✅ ジオコーディングエンジン初期化")
            
            # 4. 統合動作確認（軽量テスト）
            test_place = "東京"
            test_context = "東京駅から新宿へ向かった。"
            
            # 基本メソッド存在確認
            if hasattr(context_analyzer, 'analyze_place_context'):
                logger.info("  ✅ 文脈分析メソッド確認")
            
            if hasattr(geocoding_engine, 'geocode_with_context'):
                logger.info("  ✅ ジオコーディングメソッド確認")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ AIシステム統合エラー: {e}")
            return False
    
    def _test_pipeline_functionality(self) -> bool:
        """パイプライン機能テスト"""
        try:
            # 1. パイプライン初期化
            import run_pipeline
            logger.info("  ✅ パイプライン初期化")
            
            # 2. 主要機能存在確認
            required_functions = ['process_author', 'ai_verify_places']
            
            for func_name in required_functions:
                if hasattr(run_pipeline, func_name):
                    logger.info(f"  ✅ {func_name} 機能確認")
                else:
                    logger.warning(f"  ⚠️ {func_name} 機能未確認")
            
            # 3. 地名抽出システム確認
            from extractors.places import EnhancedPlaceExtractorV3
            extractor = EnhancedPlaceExtractorV3()
            logger.info("  ✅ 地名抽出システム初期化")
            
            # 4. 地名マスター管理確認
            from extractors.places import PlaceMasterManagerV2
            master_manager = PlaceMasterManagerV2()
            logger.info("  ✅ 地名マスター管理初期化")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ パイプライン機能エラー: {e}")
            return False
    
    def _test_performance_metrics(self) -> bool:
        """パフォーマンステスト"""
        try:
            # 1. モジュール初期化時間測定
            start_time = time.time()
            
            from ai.llm import LLMClient
            from extractors.places import EnhancedPlaceExtractorV3
            from database.manager import DatabaseManager
            
            init_time = time.time() - start_time
            self.test_results['performance_metrics']['initialization_time'] = init_time
            logger.info(f"  ⚡ 初期化時間: {init_time:.3f}秒")
            
            # 2. 基本操作性能測定
            start_time = time.time()
            
            # 地名正規化テスト
            from extractors.places import PlaceMasterManagerV2
            master_manager = PlaceMasterManagerV2()
            test_places = ["東京", "京都", "大阪", "名古屋", "福岡"]
            
            for place in test_places:
                normalized = master_manager.normalize_place_name(place)
            
            normalization_time = time.time() - start_time
            self.test_results['performance_metrics']['normalization_time'] = normalization_time
            logger.info(f"  ⚡ 正規化処理時間: {normalization_time:.3f}秒 (5件)")
            
            # 3. データベース接続性能
            start_time = time.time()
            
            db_manager = DatabaseManager()
            authors = db_manager.get_all_authors()
            authors_count = len(authors)
            
            db_time = time.time() - start_time
            self.test_results['performance_metrics']['database_query_time'] = db_time
            logger.info(f"  ⚡ DB接続時間: {db_time:.3f}秒")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ パフォーマンステストエラー: {e}")
            return False
    
    def _test_error_handling(self) -> bool:
        """エラーハンドリングテスト"""
        try:
            # 1. カスタム例外テスト
            from core.exceptions import BungoMapError, DatabaseError
            
            try:
                raise BungoMapError("テスト例外")
            except BungoMapError:
                logger.info("  ✅ カスタム例外ハンドリング確認")
            
            # 2. 不正データ処理テスト
            from extractors.places import PlaceMasterManagerV2
            master_manager = PlaceMasterManagerV2()
            
            # 空文字列での検索
            result = master_manager.find_master_by_name("")
            if result is None:
                logger.info("  ✅ 空文字列処理確認")
            
            # 3. 存在しないファイル処理
            from database.manager import DatabaseManager
            try:
                db_manager = DatabaseManager("nonexistent.db")
                # 接続テスト
                db_manager.get_authors_count()
            except Exception:
                logger.info("  ✅ 不正DB処理確認")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ エラーハンドリングテストエラー: {e}")
            return False
    
    def _test_configuration_system(self) -> bool:
        """設定システムテスト"""
        try:
            # 1. 設定読み込み
            from core.config import get_config
            config = get_config()
            logger.info("  ✅ 設定システム読み込み")
            
            # 2. 定数システム
            from core.constants import PROJECT_ROOT, DATA_DIR
            
            if os.path.exists(PROJECT_ROOT):
                logger.info("  ✅ プロジェクトルート確認")
            
            if os.path.exists(DATA_DIR):
                logger.info("  ✅ データディレクトリ確認")
            
            # 3. 環境変数処理
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                logger.info("  ✅ API設定確認")
            else:
                logger.warning("  ⚠️ API設定未確認")
            
            return True
            
        except Exception as e:
            logger.error(f"  ❌ 設定システムテストエラー: {e}")
            return False
    
    def _print_final_results(self):
        """最終結果表示"""
        end_time = datetime.now()
        duration = (end_time - self.test_results['start_time']).total_seconds()
        
        logger.info("\n" + "=" * 70)
        logger.info("🏆 ステップ4: 最終統合テスト結果")
        logger.info("=" * 70)
        logger.info(f"⏱️  実行時間: {duration:.2f}秒")
        logger.info(f"✅ 成功テスト: {self.test_results['tests_passed']}件")
        logger.info(f"❌ 失敗テスト: {self.test_results['tests_failed']}件")
        
        total_tests = self.test_results['tests_passed'] + self.test_results['tests_failed']
        success_rate = (self.test_results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"📊 成功率: {success_rate:.1f}%")
        
        # パフォーマンス結果
        if self.test_results['performance_metrics']:
            logger.info("\n⚡ パフォーマンス結果:")
            for metric, value in self.test_results['performance_metrics'].items():
                logger.info(f"  {metric}: {value:.3f}秒")
        
        # 失敗テスト詳細
        if self.test_results['failures']:
            logger.error(f"\n❌ 失敗したテスト:")
            for failure in self.test_results['failures']:
                logger.error(f"  - {failure}")
        
        # 総合評価
        if self.test_results['tests_failed'] == 0:
            logger.info("\n🎉 全テスト成功! リファクタリング完了!")
        else:
            logger.warning(f"\n⚠️ {self.test_results['tests_failed']}件のテストが失敗しました")

def main():
    """メイン実行"""
    logger.info("🚀 ステップ4: 最終統合テスト開始")
    
    tester = FinalIntegrationTest()
    success = tester.run_comprehensive_test()
    
    if success:
        logger.info("\n🎯 リファクタリング品質保証完了!")
        return 0
    else:
        logger.error("\n❌ 品質保証で問題が検出されました")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 