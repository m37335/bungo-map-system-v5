#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文豪ゆかり地図システム v4.0 - 統合パイプライン実行器
作者指定で青空文庫→センテンス分割→地名抽出まで完全自動化

使用例:
    python3 run_pipeline.py --author "梶井 基次郎"
    python3 run_pipeline.py --status "梶井 基次郎"
"""

import sys
import os
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 既存の処理クラス
from extractors.process_complete_author import CompleteAuthorProcessor
from extractors.enhanced_place_extractor_v2 import EnhancedPlaceExtractorV2
from ai.context_aware_geocoding import ContextAwareGeocoder
from extractors.wikipedia_author_enricher import WikipediaAuthorEnricher
from database.sentence_places_enricher import SentencePlacesEnricher
from extractors.aozora_metadata_extractor import AozoraMetadataExtractor

class BungoPipeline:
    """文豪地図システム統合パイプライン"""
    
    def __init__(self):
        print("🚀 文豪ゆかり地図システム v4.0 - パイプライン初期化中...")
        self.author_processor = CompleteAuthorProcessor()
        self.place_extractor = EnhancedPlaceExtractorV2()
        self.context_aware_geocoder = ContextAwareGeocoder()
        self.wikipedia_enricher = WikipediaAuthorEnricher()
        self.sentence_places_enricher = SentencePlacesEnricher()
        self.metadata_extractor = AozoraMetadataExtractor()
        print("✅ パイプライン初期化完了")
    
    def run_full_pipeline(self, author_name: str, include_places: bool = True, include_geocoding: bool = True, include_maintenance: bool = True) -> Dict[str, Any]:
        """完全パイプライン実行"""
        start_time = datetime.now()
        print(f"\n🌟 文豪ゆかり地図システム - 完全パイプライン開始")
        print(f"👤 対象作者: {author_name}")
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
            'errors': []
        }
        
        try:
            # ステップ1: 作者・作品処理
            print("🔄 ステップ1: 作者作品処理開始...")
            print("  📚 青空文庫から作品収集")
            print("  📄 本文取得・テキスト処理")
            print("  📝 センテンス分割・保存")
            
            step1_result = self.author_processor.process_author_complete(author_name, content_processing=True)
            
            if step1_result and step1_result.get('success', False):
                # 正しい結果から情報を取得
                results['works_processed'] = step1_result.get('works_collection', {}).get('new_works', 0)
                results['sentences_created'] = step1_result.get('content_processing', {}).get('total_sentences', 0)
                print(f"✅ ステップ1完了: {results['works_processed']}作品、{results['sentences_created']:,}センテンス")
            else:
                raise Exception("作者・作品処理に失敗しました")
            
            # ステップ2: 地名処理
            if include_places:
                if include_geocoding:
                    print("\n🔄 ステップ2: 地名抽出→AI文脈判断型ジオコーディング開始...")
                    print("  🗺️  センテンスから地名抽出（前後文付き）")
                    print("  🤖 AI文脈分析によるジオコーディング")
                    print("  🌍 Google Maps API統合座標取得")
                    print("  💾 高精度データベース保存")
                    
                    # ステップ2A: 地名抽出
                    step2a_result = self.place_extractor.process_sentences_batch()
                    results['sentences_processed'] = step2a_result.get('processed_sentences', 0)
                    results['places_extracted'] = step2a_result.get('extracted_places', 0)
                    results['places_saved'] = step2a_result.get('saved_places', 0)
                    
                    print(f"✅ ステップ2A完了: {results['sentences_processed']}センテンス処理、{results['places_extracted']}地名抽出")
                    
                    # ステップ2B: AI文脈判断型ジオコーディング
                    if results['places_extracted'] > 0:
                        print("\n🔄 ステップ2B: AI文脈判断型ジオコーディング開始...")
                        step2b_result = self.context_aware_geocoder.geocode_places_batch()
                        
                        results['places_geocoded'] = step2b_result.get('geocoded_places', 0)
                        
                        if results['places_extracted'] > 0:
                            results['geocoding_success_rate'] = (results['places_geocoded'] / results['places_extracted']) * 100
                        else:
                            results['geocoding_success_rate'] = 0.0
                        
                        print(f"✅ ステップ2B完了: {results['places_geocoded']}件ジオコーディング成功 ({results['geocoding_success_rate']:.1f}%)")
                    
                    print(f"✅ ステップ2統合完了: {results['sentences_processed']}センテンス処理、{results['places_extracted']}地名抽出、{results['places_geocoded']}件ジオコーディング成功 ({results['geocoding_success_rate']:.1f}%)")
                else:
                    print("\n🔄 ステップ2: 地名抽出開始...")
                    print("  🗺️  センテンスから地名抽出（前後文付き）")
                    
                    # 地名抽出のみ実行
                    step2_result = self.place_extractor.process_sentences_batch()
                    
                    results['sentences_processed'] = step2_result.get('processed_sentences', 0)
                    results['places_extracted'] = step2_result.get('extracted_places', 0)
                    results['places_saved'] = step2_result.get('saved_places', 0)
                    print(f"✅ ステップ2完了: {results['sentences_processed']}センテンス処理、{results['places_extracted']}地名抽出、{results['places_saved']}件保存")
            
            # ステップ3: データ品質保証（新機能）
            if include_maintenance:
                print("\n🔄 ステップ3: データ品質保証・メンテナンス...")
                print("  📝 sentence_places作者・作品情報補完")
                print("  📚 worksメタデータ自動補完")
                print("  📅 出版年情報更新")
                print("  🔧 matched_text文全体修正")
                
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
    
    def check_status(self, author_name: str):
        """作者の処理状況確認"""
        print(f"🔍 {author_name} の処理状況確認")
        print("=" * 60)
        try:
            status = self.author_processor.get_author_processing_status(author_name)
            
            # 状況表示
            print(f"👤 作者: {status.get('author_name', 'N/A')}")
            print(f"📚 作品数: {status.get('total_works', 0)}件")
            print(f"📝 センテンス数: {status.get('total_sentences', 0):,}件")
            print(f"🗺️ 地名数: {status.get('total_places', 0)}件")
            print(f"✅ 処理状況: {status.get('status', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 状況確認エラー: {e}")
    
    def delete_invalid_places(self, place_names: List[str], reason: str = "パイプライン管理") -> Dict[str, Any]:
        """無効地名削除"""
        print(f"🗑️ 無効地名削除: {len(place_names)}件")
        return self.context_aware_geocoder.delete_invalid_places(place_names, reason)
    
    def cleanup_invalid_places(self, auto_confirm: bool = False) -> Dict[str, Any]:
        """無効地名自動クリーンアップ"""
        print("🧹 無効地名自動クリーンアップ実行...")
        return self.context_aware_geocoder.cleanup_invalid_places(auto_confirm)
    
    def analyze_place_usage(self, place_name: str) -> Dict[str, Any]:
        """地名使用状況分析"""
        print(f"🔍 地名使用状況分析: {place_name}")
        return self.context_aware_geocoder.get_place_usage_analysis(place_name)
    
    def get_geocoding_stats(self) -> Dict[str, Any]:
        """ジオコーディング統計取得"""
        return self.context_aware_geocoder.get_geocoding_statistics()
    
    def _run_data_quality_maintenance(self) -> Dict[str, Any]:
        """データ品質保証・メンテナンス処理"""
        maintenance_results = {
            'maintenance_success': True,
            'enriched_sentence_places': 0,
            'enriched_works': 0,
            'updated_publication_years': 0,
            'fixed_matched_texts': 0,
            'maintenance_errors': []
        }
        
        try:
            # 1. sentence_places補完
            try:
                enrichment_result = self.sentence_places_enricher.run_full_enrichment()
                maintenance_results['enriched_sentence_places'] = enrichment_result.get('total_updates', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"sentence_places補完エラー: {e}")
                maintenance_results['maintenance_success'] = False
            
            # 2. worksメタデータ補完
            try:
                works_result = self._enrich_works_metadata()
                maintenance_results['enriched_works'] = works_result.get('enriched_count', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"worksメタデータ補完エラー: {e}")
                maintenance_results['maintenance_success'] = False
            
            # 3. work_publication_year更新
            try:
                publication_result = self._update_work_publication_years()
                maintenance_results['updated_publication_years'] = publication_result.get('updated_count', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"出版年更新エラー: {e}")
                maintenance_results['maintenance_success'] = False
            
            # 4. matched_text修正
            try:
                matched_text_result = self._fix_matched_text()
                maintenance_results['fixed_matched_texts'] = matched_text_result.get('fixed_count', 0)
            except Exception as e:
                maintenance_results['maintenance_errors'].append(f"matched_text修正エラー: {e}")
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
            # 成功時の処理件数を出力から抽出
            output_lines = result.stdout.split('\n')
            enriched_count = 0
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
            # 成功時の処理件数を出力から抽出
            output_lines = result.stdout.split('\n')
            updated_count = 0
            for line in output_lines:
                if '件更新' in line:
                    try:
                        updated_count = int(line.split('件更新')[0].split()[-1])
                    except:
                        pass
            
            return {'updated_count': updated_count}
        else:
            raise Exception(f"出版年更新失敗: {result.stderr}")
    
    def _fix_matched_text(self) -> Dict[str, Any]:
        """matched_text修正"""
        import sqlite3
        
        try:
            conn = sqlite3.connect('data/bungo_map.db')
            cursor = conn.cursor()
            
            # matched_textを対応するsentence_textで更新
            cursor.execute("""
                UPDATE sentence_places 
                SET matched_text = (
                    SELECT sentence_text 
                    FROM sentences 
                    WHERE sentences.sentence_id = sentence_places.sentence_id
                )
            """)
            
            fixed_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return {'fixed_count': fixed_count}
        except Exception as e:
            raise Exception(f"matched_text修正失敗: {e}")
    
    def _print_report(self, results: Dict[str, Any]):
        """レポート表示"""
        print(f"\n🎉 パイプライン完了レポート")
        print("=" * 80)
        print(f"👤 作者: {results['author']}")
        print(f"⏱️  実行時間: {results['duration']:.1f}秒")
        print(f"🏆 結果: {'成功' if results['success'] else '失敗'}")
        print(f"📚 処理作品: {results['works_processed']}件")
        print(f"📝 生成センテンス: {results['sentences_created']:,}件")
        print(f"📄 地名処理センテンス: {results.get('sentences_processed', 0)}件")
        print(f"🗺️  抽出地名: {results['places_extracted']}件")
        print(f"💾 保存地名: {results.get('places_saved', 0)}件")
        print(f"🌍 ジオコーディング成功: {results.get('places_geocoded', 0)}件")
        print(f"📊 ジオコーディング成功率: {results.get('geocoding_success_rate', 0):.1f}%")
        
        # メンテナンス結果
        if 'maintenance_success' in results:
            print(f"\n🔧 データ品質保証結果:")
            print(f"  📝 sentence_places補完: {results.get('enriched_sentence_places', 0)}件")
            print(f"  📚 worksメタデータ補完: {results.get('enriched_works', 0)}件")
            print(f"  📅 出版年更新: {results.get('updated_publication_years', 0)}件")
            print(f"  🔧 matched_text修正: {results.get('fixed_matched_texts', 0)}件")
            print(f"  🏆 メンテナンス結果: {'成功' if results.get('maintenance_success', False) else '一部エラー'}")
        
        # 通常のエラー
        if results['errors']:
            print(f"\n❌ パイプラインエラー: {len(results['errors'])}件")
            for error in results['errors']:
                print(f"  - {error}")
        
        # メンテナンスエラー
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