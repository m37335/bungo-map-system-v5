#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文豪ゆかり地図システム v4.0 - 統合パイプライン実行器
地名マスター優先設計による効率的な処理システム

使用例:
    python3 run_pipeline.py --author "梶井 基次郎"
    python3 run_pipeline.py --status "梶井 基次郎"
    python3 run_pipeline.py --ai-verify
    python3 run_pipeline.py --ai-verify-delete
"""

import sys
import os
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# リファクタリング後のモジュラーシステム
from extractors.processors import CompleteAuthorProcessor
from extractors.places.enhanced_place_extractor import EnhancedPlaceExtractorV3
from extractors.places.place_master_manager import PlaceMasterManagerV2
from ai.llm import LLMClient
from ai.nlp import ContextAnalyzer
from ai.geocoding import GeocodingEngine
from extractors.wikipedia import WikipediaAuthorEnricher
from database.sentence_places_enricher import SentencePlacesEnricher
from extractors.aozora import AozoraMetadataExtractor
from extractors.aozora.author_list_scraper import AuthorListScraper

class BungoPipeline:
    """文豪地図システム統合パイプライン（地名マスター優先版）"""
    
    def __init__(self):
        print("🚀 文豪ゆかり地図システム v4.0 - パイプライン初期化中...")
        print("✨ 地名マスター優先設計による効率的な処理")
        
        self.author_processor = CompleteAuthorProcessor()
        self.place_extractor = EnhancedPlaceExtractorV3()
        self.place_master_manager = PlaceMasterManagerV2()
        
        # 新しいモジュラーAIシステム
        self.llm_client = LLMClient()
        self.context_analyzer = ContextAnalyzer()
        self.geocoding_engine = GeocodingEngine(self.llm_client)
        
        self.wikipedia_enricher = WikipediaAuthorEnricher()
        self.sentence_places_enricher = SentencePlacesEnricher()
        self.metadata_extractor = AozoraMetadataExtractor()
        
        # 青空文庫URL自動取得機能
        self.author_list_scraper = AuthorListScraper()
        
        print("✅ パイプライン初期化完了")
        print("🎯 地名マスター検索 → 重複ジオコーディング回避 → API効率化")
    
    def check_and_set_aozora_url(self, author_name: str) -> bool:
        """青空文庫URL確認・自動設定"""
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bungo_map.db')
            
            # 現在のURL状況確認
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT author_id, author_name, aozora_author_url
                FROM authors 
                WHERE author_name = ?
            """, (author_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                print(f"❌ 作者 {author_name} がデータベースに見つかりません")
                return False
            
            author_id, db_author_name, current_url = result
            
            # 青空文庫URLが既に設定されている場合
            if current_url and current_url.strip():
                print(f"✅ 青空文庫URL設定済み: {current_url}")
                return True
            
            # 青空文庫URLが未設定の場合、自動取得
            print(f"🔍 青空文庫URL未設定 - 自動取得開始: {author_name}")
            
            success = self.author_list_scraper.update_single_author_url(author_name)
            
            if success:
                print(f"✅ 青空文庫URL自動設定完了")
                return True
            else:
                print(f"⚠️ 青空文庫URL取得失敗 - パイプライン継続（一部制限あり）")
                return False
                
        except Exception as e:
            print(f"❌ 青空文庫URLチェックエラー: {e}")
            return False
    
    def run_full_pipeline(self, author_name: str, include_places: bool = True, 
                         include_geocoding: bool = True, include_maintenance: bool = True) -> Dict[str, Any]:
        """完全パイプライン実行（地名マスター優先版）"""
        start_time = datetime.now()
        print(f"\n🌟 文豪ゆかり地図システム - 完全パイプライン開始")
        print(f"👤 対象作者: {author_name}")
        print(f"🎯 地名マスター優先設計による効率的な処理")
        print("=" * 80)
        
        results = {
            'author': author_name,
            'start_time': start_time,
            'success': False,
            'works_processed': 0,
            'sentences_created': 0,
            'places_extracted': 0,
            'places_saved': 0,
            'places_geocoded': 0,
            'geocoding_skipped': 0,
            'geocoding_success_rate': 0.0,
            'sentences_processed': 0,
            'master_cache_hits': 0,
            'new_masters_created': 0,
            'aozora_url_status': False,
            'errors': []
        }
        
        try:
            # 事前チェック: 青空文庫URL確認・自動設定
            print("🔄 事前チェック: 青空文庫URL確認...")
            url_status = self.check_and_set_aozora_url(author_name)
            results['aozora_url_status'] = url_status
            
            if not url_status:
                print("⚠️ 青空文庫URL取得失敗 - 作品収集に制限がかかる可能性があります")
            
            # ステップ1: 作者・作品処理
            print("\n🔄 ステップ1: 作者作品処理開始...")
            print("  📚 青空文庫から作品収集")
            print("  📄 本文取得・テキスト処理")
            print("  📝 センテンス分割・保存")
            
            step1_result = self.author_processor.process_author_complete(author_name, content_processing=True)
            
            if step1_result and step1_result.get('success', False):
                results['works_processed'] = step1_result.get('works_collection', {}).get('new_works', 0)
                results['sentences_created'] = step1_result.get('content_processing', {}).get('total_sentences', 0)
                print(f"✅ ステップ1完了: {results['works_processed']}作品、{results['sentences_created']:,}センテンス")
            else:
                raise Exception("作者・作品処理に失敗しました")
            
            # ステップ2: 地名マスター優先処理
            if include_places:
                print("\n🔄 ステップ2: 地名マスター優先抽出・処理開始...")
                print("  🔍 地名抽出 → マスター検索")
                print("  ⚡ 既存地名: キャッシュ参照（ジオコーディングスキップ）")
                print("  🆕 新規地名: マスター作成 → ジオコーディング実行")
                print("  🤖 AI検証統合による品質保証")
                
                # 作者のworksを取得してprocessing
                step2_result = self._process_author_places(author_name)
                
                results.update(step2_result)
                
                print(f"✅ ステップ2完了:")
                print(f"  📊 処理: {results['sentences_processed']}センテンス")
                print(f"  🗺️ 抽出: {results['places_extracted']}地名")
                print(f"  ⚡ キャッシュヒット: {results['master_cache_hits']}件")
                print(f"  🆕 新規マスター: {results['new_masters_created']}件")
                print(f"  🌍 ジオコーディング: {results['places_geocoded']}件")
                print(f"  📈 成功率: {results['geocoding_success_rate']:.1f}%")
            
            # ステップ3: データ品質保証（改良版）
            if include_maintenance:
                print("\n🔄 ステップ3: データ品質保証・メンテナンス...")
                print("  👤 Wikipedia作者情報自動補完")
                print("  📝 sentence_places作者・作品情報補完")
                print("  📚 worksメタデータ自動補完")
                print("  📅 出版年情報更新")
                print("  🏗️ 地名マスター統計更新")
                
                step3_result = self._run_data_quality_maintenance()
                results.update(step3_result)
                
                if step3_result['maintenance_success']:
                    print(f"✅ ステップ3完了: データ品質保証処理正常完了")
                else:
                    print(f"⚠️ ステップ3警告: 一部メンテナンス処理でエラーが発生しましたが、パイプラインは継続します")
            else:
                print("\n⏭️ ステップ3: データ品質保証・メンテナンス（スキップ）")
            
            results['success'] = True
            
        except Exception as e:
            print(f"❌ パイプライン実行エラー: {e}")
            results['errors'].append(str(e))
        
        # 最終レポート
        end_time = datetime.now()
        results['end_time'] = end_time
        results['duration'] = (end_time - start_time).total_seconds()
        
        self._print_report(results)
        return results
    
    def _process_author_places(self, author_name: str) -> Dict[str, Any]:
        """作者の地名処理（地名マスター優先）"""
        try:
            # 作者の作品ID取得
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bungo_map.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT w.work_id, w.title 
                FROM works w
                JOIN authors a ON w.author_id = a.author_id
                WHERE a.author_name = ?
                ORDER BY w.work_id
            """, (author_name,))
            
            works = cursor.fetchall()
            conn.close()
            
            if not works:
                print(f"⚠️ 作者 {author_name} の作品が見つかりません")
                return {}
            
            print(f"📚 処理対象: {len(works)}作品")
            
            total_stats = {
                'sentences_processed': 0,
                'places_extracted': 0,
                'places_saved': 0,
                'places_geocoded': 0,
                'geocoding_skipped': 0,
                'geocoding_success_rate': 0.0,
                'master_cache_hits': 0,
                'new_masters_created': 0
            }
            
            # 各作品を処理
            for work_id, title in works:
                print(f"\n📖 作品処理: {title}")
                
                work_stats = self.place_extractor.process_work_sentences(work_id, title)
                
                # 統計統合
                total_stats['sentences_processed'] += work_stats.get('processed_sentences', 0)
                total_stats['places_extracted'] += work_stats.get('total_places', 0)
                
                # マスター統計取得
                master_stats = self.place_master_manager.get_master_statistics()
                cache_stats = master_stats.get('cache_stats', {})
                
                total_stats['master_cache_hits'] += cache_stats.get('cache_hits', 0)
                total_stats['new_masters_created'] += cache_stats.get('new_masters', 0)
                total_stats['geocoding_skipped'] += cache_stats.get('geocoding_skipped', 0)
                total_stats['places_geocoded'] += cache_stats.get('geocoding_executed', 0)
            
            # 成功率計算
            if total_stats['places_extracted'] > 0:
                total_stats['geocoding_success_rate'] = (
                    total_stats['places_geocoded'] / 
                    max(1, total_stats['new_masters_created']) * 100
                )
            
            return total_stats
            
        except Exception as e:
            print(f"❌ 地名処理エラー: {e}")
            return {}
    
    def check_status(self, author_name: str):
        """作者の処理状況確認（地名マスター統計含む）"""
        print(f"🔍 {author_name} の処理状況確認")
        print("=" * 60)
        try:
            status = self.author_processor.get_author_processing_status(author_name)
            
            # 基本状況表示
            print(f"👤 作者: {status.get('author_name', 'N/A')}")
            print(f"📚 作品数: {status.get('total_works', 0)}件")
            print(f"📝 センテンス数: {status.get('total_sentences', 0):,}件")
            print(f"🗺️ 地名数: {status.get('total_places', 0)}件")
            print(f"✅ 処理状況: {status.get('status', 'N/A')}")
            
            # 地名マスター統計表示
            print(f"\n📊 地名マスター統計:")
            master_stats = self.place_master_manager.get_master_statistics()
            print(f"  総マスター数: {master_stats.get('total_masters', 0):,}")
            print(f"  ジオコーディング済み: {master_stats.get('geocoded_masters', 0):,} ({master_stats.get('geocoding_rate', 0):.1f}%)")
            print(f"  使用回数計: {master_stats.get('total_usage', 0):,}")
            
        except Exception as e:
            print(f"❌ 状況確認エラー: {e}")
    
    def ai_verify_places(self, limit: int = 20, confidence_threshold: float = 0.7, auto_delete: bool = False) -> Dict[str, Any]:
        """AI大量検証実行（新モジュラーシステム対応）"""
        print(f"🤖 AI大量検証開始 (上限: {limit}件, 信頼度閾値: {confidence_threshold})")
        print("🎯 新しいモジュラーAIシステムによる効率的な検証")
        
        # 新しいモジュラーシステムでAI検証を実装
        # 暫定的に基本的な結果を返す
        result = {
            'processed_count': 0,
            'verified_count': 0,
            'delete_candidates': [],
            'statistics': {}
        }
        
        try:
            # TODO: 新しいAIモジュールを使った検証ロジックを実装
            print("ℹ️ AI検証機能は新しいモジュラーシステムに移行中です")
            print("   現在は基本的な動作確認のみ実行されます")
            
            if auto_delete:
                print("✅ 自動削除対象なし（移行中）")
        
        except Exception as e:
            print(f"❌ AI検証エラー: {e}")
            result['error'] = str(e)
        
        return result
    
    def get_master_statistics(self) -> Dict[str, Any]:
        """地名マスター統計取得"""
        return self.place_master_manager.get_master_statistics()
    
    def print_master_statistics(self):
        """地名マスター統計表示"""
        self.place_master_manager.print_statistics()
    
    def _run_data_quality_maintenance(self) -> Dict[str, Any]:
        """データ品質保証・メンテナンス処理（地名マスター対応版）"""
        maintenance_results = {
            'maintenance_success': True,
            'wikipedia_enriched_authors': 0,
            'enriched_sentence_places': 0,
            'enriched_works': 0,
            'updated_publication_years': 0,
            'master_statistics_updated': True,
            'maintenance_errors': []
        }
        
        try:
            # 1. Wikipedia作者情報補完
            try:
                wikipedia_result = self._enrich_wikipedia_author_info()
                maintenance_results['wikipedia_enriched_authors'] = wikipedia_result.get('enriched_count', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"Wikipedia作者情報補完エラー: {e}")
                maintenance_results['maintenance_success'] = False
            
            # 2. sentence_places補完
            try:
                enrichment_result = self.sentence_places_enricher.run_full_enrichment()
                maintenance_results['enriched_sentence_places'] = enrichment_result.get('total_updates', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"sentence_places補完エラー: {e}")
                maintenance_results['maintenance_success'] = False
            
            # 3. worksメタデータ補完
            try:
                works_result = self._enrich_works_metadata()
                maintenance_results['enriched_works'] = works_result.get('enriched_count', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"worksメタデータ補完エラー: {e}")
                maintenance_results['maintenance_success'] = False
            
            # 4. work_publication_year更新
            try:
                publication_result = self._update_work_publication_years()
                maintenance_results['updated_publication_years'] = publication_result.get('updated_count', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"出版年更新エラー: {e}")
                maintenance_results['maintenance_success'] = False
                
        except Exception as e:
            maintenance_results['maintenance_errors'].append(f"メンテナンス処理全体エラー: {e}")
            maintenance_results['maintenance_success'] = False
        
        return maintenance_results
    
    def _enrich_works_metadata(self) -> Dict[str, Any]:
        """worksメタデータ補完"""
        import subprocess
        
        result = subprocess.run([
            'python3', 'extractors/enrich_works_metadata.py'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            enriched_count = 0
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if '件処理完了' in line:
                    try:
                        enriched_count = int(line.split('件処理完了')[0].split()[-1])
                    except:
                        pass
            
            return {'enriched_count': enriched_count}
        else:
            raise Exception(f"worksメタデータ補完失敗: {result.stderr}")
    
    def _update_work_publication_years(self) -> Dict[str, Any]:
        """work_publication_year更新"""
        import subprocess
        
        result = subprocess.run([
            'python3', 'extractors/update_work_publication_year.py'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            updated_count = 0
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if '件更新' in line:
                    try:
                        updated_count = int(line.split('件更新')[0].split()[-1])
                    except:
                        pass
            
            return {'updated_count': updated_count}
        else:
            raise Exception(f"出版年更新失敗: {result.stderr}")
    
    def _enrich_wikipedia_author_info(self) -> Dict[str, Any]:
        """Wikipedia作者情報補完"""
        try:
            missing_info = self.wikipedia_enricher.preview_missing_info()
            recent_authors = missing_info.get('missing_authors', [])
            
            if not recent_authors:
                return {'enriched_count': 0, 'errors': []}
            
            target_authors = [author['author_name'] for author in recent_authors[:3]]
            enrichment_result = self.wikipedia_enricher.enrich_specific_authors(target_authors)
            
            return {
                'enriched_count': enrichment_result.get('success_count', 0),
                'errors': enrichment_result.get('errors', [])
            }
        except Exception as e:
            raise Exception(f"Wikipedia作者情報補完失敗: {e}")
    
    def _print_report(self, results: Dict[str, Any]):
        """レポート表示（地名マスター統計含む）"""
        print(f"\n🎉 パイプライン完了レポート")
        print("=" * 80)
        print(f"👤 作者: {results['author']}")
        print(f"⏱️  実行時間: {results['duration']:.1f}秒")
        print(f"🏆 結果: {'成功' if results['success'] else '失敗'}")
        print(f"🔗 青空文庫URL: {'設定済み' if results.get('aozora_url_status', False) else '未設定/取得失敗'}")
        print(f"📚 処理作品: {results['works_processed']}件")
        print(f"📝 生成センテンス: {results['sentences_created']:,}件")
        print(f"📄 地名処理センテンス: {results.get('sentences_processed', 0)}件")
        print(f"🗺️  抽出地名: {results['places_extracted']}件")
        
        # 地名マスター統計
        print(f"\n⚡ 地名マスター効率性:")
        print(f"  キャッシュヒット: {results.get('master_cache_hits', 0)}件")
        print(f"  新規マスター作成: {results.get('new_masters_created', 0)}件")
        print(f"  ジオコーディングスキップ: {results.get('geocoding_skipped', 0)}件")
        print(f"  ジオコーディング実行: {results.get('places_geocoded', 0)}件")
        print(f"  📈 成功率: {results.get('geocoding_success_rate', 0):.1f}%")
        
        # メンテナンス結果
        if 'maintenance_success' in results:
            print(f"\n🔧 データ品質保証結果:")
            print(f"  👤 Wikipedia作者情報補完: {results.get('wikipedia_enriched_authors', 0)}件")
            print(f"  📝 sentence_places補完: {results.get('enriched_sentence_places', 0)}件")
            print(f"  📚 worksメタデータ補完: {results.get('enriched_works', 0)}件")
            print(f"  📅 出版年更新: {results.get('updated_publication_years', 0)}件")
            print(f"  🏆 メンテナンス結果: {'成功' if results.get('maintenance_success', False) else '一部エラー'}")
        
        # エラー表示
        if results['errors']:
            print(f"\n❌ パイプラインエラー: {len(results['errors'])}件")
            for error in results['errors']:
                print(f"  - {error}")
        
        if results.get('maintenance_errors'):
            print(f"\n⚠️ メンテナンスエラー: {len(results['maintenance_errors'])}件")
            for error in results['maintenance_errors']:
                print(f"  - {error}")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='文豪ゆかり地図システム v4.0 - 統合パイプライン',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本処理
  python3 run_pipeline.py --author "梶井 基次郎"
  python3 run_pipeline.py --author "夏目 漱石" --works-only
  python3 run_pipeline.py --author "芥川 龍之介" --no-geocoding
  python3 run_pipeline.py --author "太宰 治" --no-maintenance
  python3 run_pipeline.py --status "梶井 基次郎"
  
  # 地名管理
  python3 run_pipeline.py --stats
  python3 run_pipeline.py --analyze "山道"
  python3 run_pipeline.py --cleanup-preview
  python3 run_pipeline.py --cleanup
  python3 run_pipeline.py --delete "先日飯島" "今飯島" "夕方山"
  
  # Wikipedia作者情報補完
  python3 run_pipeline.py --enrich-preview
  python3 run_pipeline.py --enrich-authors
  python3 run_pipeline.py --enrich-specific "夏目 漱石" "芥川 龍之介"
  
  # AI検証機能
  python3 run_pipeline.py --ai-verify
  python3 run_pipeline.py --ai-verify-delete --ai-verify-limit 50
  python3 run_pipeline.py --ai-verify --ai-confidence-threshold 0.8
        """
    )
    
    # 処理対象
    parser.add_argument('--author', '-a', help='単一作者名')
    parser.add_argument('--status', '-s', help='作者の処理状況確認')
    
    # 実行制御
    parser.add_argument('--works-only', action='store_true', help='作品収集のみ（地名抽出なし）')
    parser.add_argument('--no-geocoding', action='store_true', help='地名抽出のみ（ジオコーディングなし）')
    parser.add_argument('--no-maintenance', action='store_true', help='データ品質保証・メンテナンス処理をスキップ')
    
    # 地名管理機能
    parser.add_argument('--delete', nargs='+', help='指定した地名を削除')
    parser.add_argument('--cleanup', action='store_true', help='無効地名の自動クリーンアップ実行')
    parser.add_argument('--cleanup-preview', action='store_true', help='無効地名の削除候補を表示（実行なし）')
    parser.add_argument('--analyze', type=str, help='指定した地名の使用状況を詳細分析')
    parser.add_argument('--stats', action='store_true', help='ジオコーディング統計表示')
    
    # Wikipedia作者情報補完機能
    parser.add_argument('--enrich-authors', action='store_true', help='Wikipedia作者情報自動補完（全作者）')
    parser.add_argument('--enrich-preview', action='store_true', help='作者情報不足状況をプレビュー表示')
    parser.add_argument('--enrich-specific', nargs='+', help='指定作者のみ情報補完（複数可）')
    
    # AI検証機能
    parser.add_argument('--ai-verify', action='store_true', help='AI大量検証を実行')
    parser.add_argument('--ai-verify-delete', action='store_true', help='AI検証で削除候補を自動削除')
    parser.add_argument('--ai-verify-limit', type=int, default=20, help='AI検証する地名数の上限（デフォルト: 20）')
    parser.add_argument('--ai-confidence-threshold', type=float, default=0.7, help='AI検証の信頼度閾値（デフォルト: 0.7）')
    
    args = parser.parse_args()
    
    # パイプライン初期化
    pipeline = BungoPipeline()
    
    # Wikipedia作者情報補完プレビュー
    if args.enrich_preview:
        print("=== 🔍 作者情報不足状況プレビュー ===")
        missing_info = pipeline.wikipedia_enricher.preview_missing_info()
        return
    
    # Wikipedia作者情報自動補完（全作者）
    if args.enrich_authors:
        print("=== 🌟 Wikipedia作者情報自動補完（全作者） ===")
        try:
            stats = pipeline.wikipedia_enricher.enrich_all_authors()
            pipeline.wikipedia_enricher.print_statistics()
        except KeyboardInterrupt:
            print("\n⚠️ 処理が中断されました")
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
        finally:
            pipeline.wikipedia_enricher.close()
        return
    
    # Wikipedia作者情報補完（指定作者のみ）
    if args.enrich_specific:
        print(f"=== 🎯 Wikipedia作者情報補完（指定作者: {', '.join(args.enrich_specific)}） ===")
        try:
            stats = pipeline.wikipedia_enricher.enrich_specific_authors(args.enrich_specific)
            pipeline.wikipedia_enricher.print_statistics()
        except KeyboardInterrupt:
            print("\n⚠️ 処理が中断されました")
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
        finally:
            pipeline.wikipedia_enricher.close()
        return
    
    # 統計表示
    if args.stats:
        print("=== 📊 ジオコーディング統計情報 ===")
        stats = pipeline.get_geocoding_stats()
        print(f"総地名数: {stats['total_places']:,}")
        print(f"Geocoding済み地名数: {stats['geocoded_places']:,}")
        print(f"Geocoding率: {stats['geocoding_rate']:.1f}%")
        if stats.get('source_stats'):
            print("\n🔧 Geocodingソース:")
            for source, count in stats['source_stats'].items():
                print(f"  {source}: {count}件")
        return
    
    # 地名使用状況分析
    if args.analyze:
        analysis_result = pipeline.analyze_place_usage(args.analyze)
        if "error" in analysis_result:
            print(f"❌ {analysis_result['error']}")
            return
        
        place_data = analysis_result["place_data"]
        print(f"=== 🔍 地名使用状況分析: {args.analyze} ===")
        print(f"📍 地名情報:")
        print(f"   ID: {place_data['place_id']}")
        print(f"   地名: {place_data['place_name']}")
        print(f"   種別: {place_data['place_type']}")
        print(f"   座標: ({place_data['latitude']}, {place_data['longitude']})")
        print(f"   信頼度: {place_data['confidence']}")
        print(f"   ソース: {place_data['source_system']}")
        
        print(f"\n📊 使用統計:")
        print(f"   使用回数: {analysis_result['usage_count']}回")
        print(f"   推奨アクション: {analysis_result['recommended_action']}")
        
        print(f"\n📝 使用例:")
        for i, context in enumerate(analysis_result["context_analyses"][:3]):
            print(f"   例{i+1}: {context['sentence'][:100]}...")
            print(f"        地名判定: {context['is_place_name']} (信頼度: {context['confidence']:.2f})")
            print(f"        理由: {context['reasoning']}")
        return
    
    # 削除候補プレビュー
    if args.cleanup_preview:
        print("=== 🔍 無効地名削除候補プレビュー ===")
        cleanup_result = pipeline.cleanup_invalid_places(auto_confirm=False)
        
        if not cleanup_result["candidates"]:
            print("✅ 削除候補の無効地名は見つかりませんでした")
            return
        
        print(f"📊 削除候補: {len(cleanup_result['candidates'])}件")
        for candidate in cleanup_result["candidates"]:
            print(f"   🗑️ {candidate['place_name']}")
            print(f"      理由: {candidate['reason']}")
            print(f"      使用回数: {candidate['usage_count']}回")
            print(f"      例: {candidate['sample']}")
        
        print("💡 削除を実行するには --cleanup オプションを使用してください")
        return
    
    # 自動クリーンアップ実行
    if args.cleanup:
        print("=== 🗑️ 無効地名自動クリーンアップ実行 ===")
        cleanup_result = pipeline.cleanup_invalid_places(auto_confirm=True)
        
        if cleanup_result["deletion_result"]["total_deleted"] > 0:
            print(f"✅ {cleanup_result['deletion_result']['total_deleted']}件の無効地名を削除しました")
            for deleted in cleanup_result["deletion_result"]["deleted_places"]:
                print(f"   🗑️ {deleted['place_name']} (理由: {deleted['reason']})")
        else:
            print("✅ 削除対象の無効地名は見つかりませんでした")
        return
    
    # 指定地名削除
    if args.delete:
        print(f"=== 🗑️ 指定地名削除: {', '.join(args.delete)} ===")
        deletion_result = pipeline.delete_invalid_places(args.delete, "手動削除")
        
        if deletion_result["total_deleted"] > 0:
            print(f"✅ {deletion_result['total_deleted']}件の地名を削除しました")
            for deleted in deletion_result["deleted_places"]:
                print(f"   🗑️ {deleted['place_name']} (関連: {deleted['deleted_relations']}件)")
        
        if deletion_result["not_found_places"]:
            print(f"⚠️ 見つからなかった地名: {', '.join(deletion_result['not_found_places'])}")
        return
    
    # AI検証機能
    if args.ai_verify or args.ai_verify_delete:
        print(f"=== 🤖 AI大量検証 (上限: {args.ai_verify_limit}件, 信頼度閾値: {args.ai_confidence_threshold}) ===")
        ai_result = pipeline.ai_verify_places(
            limit=args.ai_verify_limit,
            confidence_threshold=args.ai_confidence_threshold,
            auto_delete=args.ai_verify_delete
        )
        return
    
    # 処理状況確認
    if args.status:
        pipeline.check_status(args.status)
        return
    
    # 地名抽出を含むかどうか
    include_places = not args.works_only
    include_geocoding = not args.no_geocoding
    include_maintenance = not args.no_maintenance
    
    # 処理実行
    if args.author:
        # 単一作者処理
        pipeline.run_full_pipeline(args.author, include_places, include_geocoding, include_maintenance)
    else:
        print("❌ 処理対象作者を指定してください")
        parser.print_help()

if __name__ == '__main__':
    main() 