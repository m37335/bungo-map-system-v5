#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文豪ゆかり地図システム v4.0 統合テストスクリプト
地名マスター優先設計対応版

機能:
1. 新しいシステムの動作確認
2. 地名マスター機能のテスト
3. パイプライン全体の検証
"""

import os
import sys
import sqlite3
from datetime import datetime

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_pipeline import BungoPipeline
from extractors.places import PlaceMasterManagerV2
from extractors.places import EnhancedPlaceExtractorV3
from database.init_db import DatabaseInitializerV2

class IntegrationTestV2:
    """統合テストクラス v2.0"""
    
    def __init__(self):
        self.pipeline = BungoPipeline()
        self.place_master_manager = PlaceMasterManagerV2()
        self.place_extractor = EnhancedPlaceExtractorV3()
        self.db_initializer = DatabaseInitializerV2()
        
    def run_comprehensive_test(self):
        """包括的なテストの実行"""
        print("🧪 文豪ゆかり地図システム v4.0 統合テスト開始")
        print("🎯 地名マスター優先設計の検証")
        print("=" * 70)
        
        test_results = {
            'start_time': datetime.now(),
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': []
        }
        
        # テスト1: データベース構造確認
        print("\n🔍 テスト1: データベース構造確認")
        if self._test_database_structure():
            test_results['tests_passed'] += 1
            print("✅ パス")
        else:
            test_results['tests_failed'] += 1
            test_results['failures'].append("データベース構造確認")
            print("❌ 失敗")
        
        # テスト2: 地名マスター機能確認
        print("\n🏗️ テスト2: 地名マスター機能確認")
        if self._test_place_master_functionality():
            test_results['tests_passed'] += 1
            print("✅ パス")
        else:
            test_results['tests_failed'] += 1
            test_results['failures'].append("地名マスター機能")
            print("❌ 失敗")
        
        # テスト3: 地名抽出システムv3確認
        print("\n🗺️ テスト3: 地名抽出システムv3確認")
        if self._test_place_extraction_v3():
            test_results['tests_passed'] += 1
            print("✅ パス")
        else:
            test_results['tests_failed'] += 1
            test_results['failures'].append("地名抽出システムv3")
            print("❌ 失敗")
        
        # テスト4: パイプライン統合確認
        print("\n🚀 テスト4: パイプライン統合確認")
        if self._test_pipeline_integration():
            test_results['tests_passed'] += 1
            print("✅ パス")
        else:
            test_results['tests_failed'] += 1
            test_results['failures'].append("パイプライン統合")
            print("❌ 失敗")
        
        # テスト5: 性能・効率性確認
        print("\n⚡ テスト5: 性能・効率性確認")
        if self._test_performance_efficiency():
            test_results['tests_passed'] += 1
            print("✅ パス")
        else:
            test_results['tests_failed'] += 1
            test_results['failures'].append("性能・効率性")
            print("❌ 失敗")
        
        # 結果レポート
        self._print_test_results(test_results)
        
        return test_results['tests_failed'] == 0
    
    def _test_database_structure(self):
        """データベース構造のテスト"""
        try:
            print("  📋 必要なテーブルの存在確認...")
            
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bungo_map.db')
            
            if not os.path.exists(db_path):
                print("  ⚠️ データベースが存在しません - 初期化を実行してください")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 必要なテーブルの確認
            required_tables = [
                'authors', 'works', 'sentences',
                'place_masters', 'place_aliases', 'sentence_places'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = []
            for table in required_tables:
                if table not in existing_tables:
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"  ❌ 不足テーブル: {', '.join(missing_tables)}")
                conn.close()
                return False
            
            # 新しいテーブル構造の確認
            cursor.execute("PRAGMA table_info(place_masters)")
            place_masters_cols = [col[1] for col in cursor.fetchall()]
            
            required_cols = ['master_id', 'normalized_name', 'display_name', 'latitude', 'longitude']
            missing_cols = [col for col in required_cols if col not in place_masters_cols]
            
            if missing_cols:
                print(f"  ❌ place_mastersテーブルの不足カラム: {', '.join(missing_cols)}")
                conn.close()
                return False
            
            # ビューの確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='places'")
            if not cursor.fetchone():
                print("  ❌ 互換性ビュー 'places' が存在しません")
                conn.close()
                return False
            
            conn.close()
            print("  ✅ データベース構造確認完了")
            return True
            
        except Exception as e:
            print(f"  ❌ データベース構造テストエラー: {e}")
            return False
    
    def _test_place_master_functionality(self):
        """地名マスター機能のテスト"""
        try:
            print("  🔍 地名マスター機能テスト...")
            
            # 1. 統計取得テスト
            stats = self.place_master_manager.get_master_statistics()
            if not isinstance(stats, dict):
                print("  ❌ 統計取得失敗")
                return False
            
            print(f"  📊 現在のマスター数: {stats.get('total_masters', 0)}")
            
            # 2. 地名検索テスト
            test_places = ['東京', '京都', '大阪']
            
            for place_name in test_places:
                try:
                    # マスター検索または作成
                    master_id = self.place_master_manager.find_master_by_name(place_name)
                    if not master_id:
                        master_id = self.place_master_manager.create_master_place(place_name)
                    result = {'master_id': master_id} if master_id else {'error': 'Failed to create master'}
                    
                    if 'master_id' not in result:
                        print(f"  ❌ 地名マスター処理失敗: {place_name}")
                        return False
                    
                    print(f"  ✅ 地名マスター処理成功: {place_name} (ID: {result['master_id']})")
                    
                except Exception as e:
                    print(f"  ❌ 地名マスター処理エラー: {place_name} - {e}")
                    return False
            
            # 3. 重複処理テスト
            try:
                # 同じ地名で再度処理（キャッシュ効果確認）
                # 重複処理テスト用の統一メソッド
                def get_or_create_master(name):
                    master_id = self.place_master_manager.find_master_by_name(name)
                    if not master_id:
                        master_id = self.place_master_manager.create_master_place(name)
                    return {'master_id': master_id} if master_id else {'error': 'Failed'}
                
                result1 = get_or_create_master('東京')
                result2 = get_or_create_master('東京')
                
                if result1['master_id'] != result2['master_id']:
                    print("  ❌ 重複処理で異なるmaster_idが返されました")
                    return False
                
                print("  ✅ 重複処理テスト成功")
                
            except Exception as e:
                print(f"  ❌ 重複処理テストエラー: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"  ❌ 地名マスター機能テストエラー: {e}")
            return False
    
    def _test_place_extraction_v3(self):
        """地名抽出システムv3のテスト"""
        try:
            print("  🗺️ 地名抽出システムv3テスト...")
            
            # テスト用センテンス
            test_sentences = [
                "東京駅から新宿へ向かった。",
                "京都の清水寺を訪れた。",
                "大阪城の桜が美しい。"
            ]
            
            for sentence in test_sentences:
                try:
                    # GinZA解析テスト
                    ginza_results = self.place_extractor._extract_places_with_ginza(sentence)
                    
                    if not isinstance(ginza_results, list):
                        print(f"  ❌ GinZA解析結果が正しくありません: {sentence}")
                        return False
                    
                    print(f"  ✅ GinZA解析成功: {sentence} → {len(ginza_results)}件")
                    
                    # 地名マスター連携テスト
                    for place_result in ginza_results:
                        if 'place_name' in place_result:
                            # マスター検索または作成
                            master_id = self.place_master_manager.find_master_by_name(place_result['place_name'])
                            if not master_id:
                                master_id = self.place_master_manager.create_master_place(place_result['place_name'])
                            master_result = {'master_id': master_id} if master_id else {'error': 'Failed'}
                            
                            if 'master_id' not in master_result:
                                print(f"  ❌ 地名マスター連携失敗: {place_result['place_name']}")
                                return False
                    
                except Exception as e:
                    print(f"  ❌ 地名抽出エラー: {sentence} - {e}")
                    return False
            
            print("  ✅ 地名抽出システムv3テスト完了")
            return True
            
        except Exception as e:
            print(f"  ❌ 地名抽出システムv3テストエラー: {e}")
            return False
    
    def _test_pipeline_integration(self):
        """パイプライン統合のテスト"""
        try:
            print("  🚀 パイプライン統合テスト...")
            
            # 1. パイプライン初期化確認
            if not hasattr(self.pipeline, 'place_master_manager'):
                print("  ❌ パイプラインに地名マスター管理機能がありません")
                return False
            
            # 2. 新しいメソッドの存在確認
            required_methods = [
                'get_master_statistics',
                'print_master_statistics',
                '_process_author_places'
            ]
            
            for method in required_methods:
                if not hasattr(self.pipeline, method):
                    print(f"  ❌ パイプラインに必要なメソッドがありません: {method}")
                    return False
            
            # 3. 統計取得テスト
            try:
                stats = self.pipeline.get_master_statistics()
                if not isinstance(stats, dict):
                    print("  ❌ パイプライン統計取得失敗")
                    return False
                
                print(f"  📊 パイプライン統計取得成功: {len(stats)}項目")
                
            except Exception as e:
                print(f"  ❌ パイプライン統計取得エラー: {e}")
                return False
            
            # 4. コンポーネント連携確認
            if not isinstance(self.pipeline.place_extractor, EnhancedPlaceExtractorV3):
                print("  ❌ パイプラインが正しい地名抽出システムを使用していません")
                return False
            
            if not isinstance(self.pipeline.place_master_manager, PlaceMasterManagerV2):
                print("  ❌ パイプラインが正しい地名マスター管理システムを使用していません")
                return False
            
            print("  ✅ パイプライン統合テスト完了")
            return True
            
        except Exception as e:
            print(f"  ❌ パイプライン統合テストエラー: {e}")
            return False
    
    def _test_performance_efficiency(self):
        """性能・効率性のテスト"""
        try:
            print("  ⚡ 性能・効率性テスト...")
            
            # 1. キャッシュ効果テスト
            start_time = datetime.now()
            
            # 同じ地名を複数回処理
            test_place = "東京"
            results = []
            
            for i in range(5):
                # マスター検索または作成
                master_id = self.place_master_manager.find_master_by_name(test_place)
                if not master_id:
                    master_id = self.place_master_manager.create_master_place(test_place)
                result = {'master_id': master_id} if master_id else {'error': 'Failed'}
                results.append(result)
            
            # すべて同じmaster_idであることを確認
            master_ids = [result['master_id'] for result in results]
            if len(set(master_ids)) != 1:
                print("  ❌ キャッシュ効果が正しく動作していません")
                return False
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"  ✅ キャッシュ効果確認: 5回処理で{duration:.3f}秒")
            
            # 2. データベース効率確認
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bungo_map.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # インデックス存在確認
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_place_masters%'
            """)
            
            indexes = cursor.fetchall()
            if len(indexes) < 3:  # 最低3つのインデックスは必要
                print(f"  ❌ 地名マスターのインデックスが不足: {len(indexes)}個")
                conn.close()
                return False
            
            print(f"  ✅ データベースインデックス確認: {len(indexes)}個")
            
            # 3. クエリ性能テスト
            start_time = datetime.now()
            
            cursor.execute("""
                SELECT COUNT(*) FROM place_masters 
                WHERE normalized_name LIKE '%東%'
            """)
            
            result = cursor.fetchone()
            end_time = datetime.now()
            query_duration = (end_time - start_time).total_seconds()
            
            print(f"  ✅ クエリ性能確認: {query_duration:.3f}秒 ({result[0]}件)")
            
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"  ❌ 性能・効率性テストエラー: {e}")
            return False
    
    def _print_test_results(self, results):
        """テスト結果の表示"""
        end_time = datetime.now()
        duration = (end_time - results['start_time']).total_seconds()
        
        print("\n" + "=" * 70)
        print("🧪 統合テスト結果レポート")
        print("=" * 70)
        print(f"⏱️  実行時間: {duration:.2f}秒")
        print(f"✅ 成功テスト: {results['tests_passed']}件")
        print(f"❌ 失敗テスト: {results['tests_failed']}件")
        print(f"📊 成功率: {results['tests_passed']/(results['tests_passed']+results['tests_failed'])*100:.1f}%")
        
        if results['failures']:
            print(f"\n❌ 失敗したテスト:")
            for failure in results['failures']:
                print(f"  - {failure}")
        
        if results['tests_failed'] == 0:
            print("\n🎉 すべてのテストが成功しました！")
            print("✨ 地名マスター優先設計は正常に動作しています")
        else:
            print(f"\n⚠️ {results['tests_failed']}件のテストが失敗しました")
            print("🔧 問題を修正してから再度テストしてください")


def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='文豪ゆかり地図システム v4.0 統合テスト')
    parser.add_argument('--quick', action='store_true', help='基本テストのみ実行')
    parser.add_argument('--verbose', action='store_true', help='詳細ログ表示')
    
    args = parser.parse_args()
    
    tester = IntegrationTestV2()
    
    if args.quick:
        print("🚀 基本テストのみ実行...")
        # 基本テストのみ実装
        success = tester._test_database_structure() and tester._test_place_master_functionality()
        if success:
            print("✅ 基本テスト成功")
        else:
            print("❌ 基本テスト失敗")
    else:
        success = tester.run_comprehensive_test()
    
    exit_code = 0 if success else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 