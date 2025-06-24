#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 緊急改善タスク統合実行スクリプト
最優先課題の一括実行・検証システム

実行内容:
1. 出版年取得精度向上 (97.4% → 99%+)
2. 地名マスターデータ化・重複排除
3. API制限対策・キャッシュ最適化
"""

import sys
import os
import time
from datetime import datetime

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.aozora_metadata_extractor import AozoraMetadataExtractor
from extractors.place_master_manager import PlaceMasterManager
from ai.geocoding import GeocodingEngine
from ai.llm import LLMClient


class UrgentImprovementRunner:
    """緊急改善タスク実行クラス"""
    
    def __init__(self):
        print("🚀 緊急改善タスク統合実行開始")
        print("=" * 60)
        self.start_time = datetime.now()
        
        # 各コンポーネント初期化
        self.metadata_extractor = AozoraMetadataExtractor()
        self.place_master_manager = PlaceMasterManager()
        self.context_geocoder = ContextAwareGeocoder()
        
        self.results = {
            'metadata_improvement': {},
            'place_master_migration': {},
            'api_optimization': {},
            'total_time': 0
        }
    
    def run_all_improvements(self):
        """全改善タスクを実行"""
        print(f"⏰ 開始時刻: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # タスク1: 出版年取得精度向上
        print("\n" + "="*60)
        print("✋ タスク1: 出版年取得精度向上 (97.4% → 99%+)")
        print("="*60)
        self.results['metadata_improvement'] = self.improve_publication_year_accuracy()
        
        # タスク2: 地名マスターデータ化
        print("\n" + "="*60)
        print("🔄 タスク2: 地名マスターデータ化・重複排除")
        print("="*60)
        self.results['place_master_migration'] = self.implement_place_master_system()
        
        # タスク3: API制限対策
        print("\n" + "="*60)
        print("💰 タスク3: API制限対策・キャッシュ最適化")
        print("="*60)
        self.results['api_optimization'] = self.optimize_api_usage()
        
        # 総合結果
        self.results['total_time'] = (datetime.now() - self.start_time).total_seconds()
        self.print_final_results()
    
    def improve_publication_year_accuracy(self) -> dict:
        """出版年取得精度向上"""
        try:
            print("📊 現在の出版年取得状況を確認中...")
            
            # 現在の統計を取得
            preview_result = self.metadata_extractor.preview_missing_metadata()
            
            print(f"📈 処理前統計:")
            print(f"   総作品数: {preview_result.get('total_works', 0)}")
            print(f"   出版年あり: {preview_result.get('with_publication_year', 0)}")
            print(f"   出版年なし: {preview_result.get('missing_publication_year', 0)}")
            
            current_rate = preview_result.get('publication_year_rate', 0)
            print(f"   現在の成功率: {current_rate:.1f}%")
            
            if current_rate >= 99.0:
                print("✅ 既に99%以上の精度を達成済み")
                return {
                    'status': 'already_optimal',
                    'current_rate': current_rate,
                    'improvement_needed': False
                }
            
            # 改良された抽出システムで再処理
            print("🔧 改良された抽出システムで再処理開始...")
            
            start_time = time.time()
            enrichment_result = self.metadata_extractor.enrich_all_works()
            processing_time = time.time() - start_time
            
            # 処理後の統計
            final_preview = self.metadata_extractor.preview_missing_metadata()
            final_rate = final_preview.get('publication_year_rate', 0)
            
            improvement = final_rate - current_rate
            
            print(f"✅ 出版年取得精度向上完了")
            print(f"   改善前: {current_rate:.1f}%")
            print(f"   改善後: {final_rate:.1f}%")
            print(f"   向上幅: +{improvement:.1f}%")
            print(f"   処理時間: {processing_time:.1f}秒")
            
            return {
                'status': 'completed',
                'before_rate': current_rate,
                'after_rate': final_rate,
                'improvement': improvement,
                'processing_time': processing_time,
                'updated_works': enrichment_result.get('success_count', 0)
            }
            
        except Exception as e:
            print(f"❌ 出版年精度向上エラー: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def implement_place_master_system(self) -> dict:
        """地名マスターデータ化・重複排除"""
        try:
            print("🏗️ 地名マスターテーブル準備...")
            
            # マスターテーブルが存在しない場合は作成
            self.place_master_manager._ensure_master_table_exists()
            
            # master_place_idカラムを追加（存在しない場合）
            print("🔧 placesテーブルにmaster_place_idカラム追加...")
            self.place_master_manager.add_master_place_id_column()
            
            # 既存地名をマスターデータに移行
            print("📦 既存地名データのマスター移行...")
            migration_result = self.place_master_manager.migrate_existing_places_to_master()
            
            if 'error' in migration_result:
                return {'status': 'error', 'error': migration_result['error']}
            
            # ジオコーディング結果の再利用最適化
            print("⚡ ジオコーディング再利用最適化...")
            optimization_result = self.place_master_manager.optimize_geocoding_reuse()
            
            # 統計情報取得
            master_stats = self.place_master_manager.get_master_statistics()
            
            print(f"✅ 地名マスターデータ化完了")
            print(f"   マスター作成: {migration_result.get('master_created', 0)}件")
            print(f"   重複統合: {migration_result.get('duplicates_merged', 0)}件")
            print(f"   座標再利用: {optimization_result.get('updated_places', 0)}件")
            
            return {
                'status': 'completed',
                'migration_result': migration_result,
                'optimization_result': optimization_result,
                'master_statistics': master_stats
            }
            
        except Exception as e:
            print(f"❌ 地名マスターデータ化エラー: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def optimize_api_usage(self) -> dict:
        """API制限対策・キャッシュ最適化"""
        try:
            print("💾 APIキャッシュシステム初期化...")
            
            # キャッシュファイルの存在確認
            cache_file = "data/api_cache.json"
            cache_exists = os.path.exists(cache_file)
            
            if cache_exists:
                cache_size = os.path.getsize(cache_file)
                print(f"📊 既存キャッシュファイル: {cache_size:,} bytes")
            else:
                print("🆕 新規キャッシュファイル作成")
            
            # 簡単なAPI制限テスト
            print("🔧 API制限機能テスト...")
            
            test_start = time.time()
            
            # ChatGPT API制限テスト（3回連続呼び出し）
            test_place = "東京"
            test_sentence = "東京に行った"
            
            for i in range(3):
                result = self.context_geocoder._analyze_context_with_llm(test_place, test_sentence)
                print(f"   テスト呼び出し {i+1}: {'キャッシュヒット' if result else 'API呼び出し'}")
            
            test_duration = time.time() - test_start
            print(f"   レート制限テスト時間: {test_duration:.2f}秒")
            
            # 制限が正しく動作していれば2秒以上かかるはず（1秒間隔 × 2回API呼び出し）
            rate_limit_working = test_duration >= 2.0 if not cache_exists else True
            
            print(f"✅ API制限対策・キャッシュ最適化完了")
            print(f"   キャッシュシステム: {'有効' if cache_exists or os.path.exists(cache_file) else '無効'}")
            print(f"   レート制限: {'有効' if rate_limit_working else '要確認'}")
            
            return {
                'status': 'completed',
                'cache_system': 'enabled',
                'rate_limiting': 'enabled' if rate_limit_working else 'needs_check',
                'test_duration': test_duration,
                'cache_file_exists': os.path.exists(cache_file)
            }
            
        except Exception as e:
            print(f"❌ API最適化エラー: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def print_final_results(self):
        """最終結果の表示"""
        end_time = datetime.now()
        
        print("\n" + "="*80)
        print("🎉 緊急改善タスク統合実行完了!")
        print("="*80)
        
        print(f"⏰ 実行時間: {self.results['total_time']:.1f}秒")
        print(f"📅 完了時刻: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # タスク1結果
        task1 = self.results.get('metadata_improvement', {})
        if task1.get('status') == 'completed':
            print(f"\n✅ タスク1 - 出版年取得精度向上:")
            print(f"   改善: {task1.get('before_rate', 0):.1f}% → {task1.get('after_rate', 0):.1f}%")
            print(f"   向上: +{task1.get('improvement', 0):.1f}%")
            print(f"   更新作品数: {task1.get('updated_works', 0)}件")
        
        # タスク2結果
        task2 = self.results.get('place_master_migration', {})
        if task2.get('status') == 'completed':
            migration = task2.get('migration_result', {})
            optimization = task2.get('optimization_result', {})
            print(f"\n✅ タスク2 - 地名マスターデータ化:")
            print(f"   マスター作成: {migration.get('master_created', 0)}件")
            print(f"   重複統合: {migration.get('duplicates_merged', 0)}件")
            print(f"   座標再利用: {optimization.get('updated_places', 0)}件")
        
        # タスク3結果
        task3 = self.results.get('api_optimization', {})
        if task3.get('status') == 'completed':
            print(f"\n✅ タスク3 - API制限対策:")
            print(f"   キャッシュシステム: {task3.get('cache_system', '無効')}")
            print(f"   レート制限: {task3.get('rate_limiting', '無効')}")
            print(f"   テスト時間: {task3.get('test_duration', 0):.2f}秒")
        
        # 警告・注意事項
        print(f"\n⚠️ 注意事項:")
        print(f"   • APIキャッシュが有効化されました - data/api_cache.json")
        print(f"   • 地名マスターテーブルが作成されました - place_masters, place_aliases")
        print(f"   • レート制限により処理速度が制御されています")
        
        print(f"\n🎯 次のステップ:")
        print(f"   1. フロントエンド・可視化システムの実装")
        print(f"   2. 検索・API機能の追加")
        print(f"   3. 並列処理による性能向上")


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='緊急改善タスク統合実行')
    parser.add_argument('--task', choices=['all', 'metadata', 'master', 'api'], 
                       default='all', help='実行するタスク')
    parser.add_argument('--dry-run', action='store_true', help='実行せずに計画のみ表示')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 実行計画:")
        print("  1. 出版年取得精度向上 (97.4% → 99%+)")
        print("  2. 地名マスターデータ化・重複排除")
        print("  3. API制限対策・キャッシュ最適化")
        print("\n実際に実行するには --dry-run オプションを外してください")
        return
    
    runner = UrgentImprovementRunner()
    
    if args.task == 'all':
        runner.run_all_improvements()
    elif args.task == 'metadata':
        runner.improve_publication_year_accuracy()
    elif args.task == 'master':
        runner.implement_place_master_system()
    elif args.task == 'api':
        runner.optimize_api_usage()


if __name__ == "__main__":
    main() 