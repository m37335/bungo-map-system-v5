#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文豪ゆかり地図システム v4.0 - メンテナンスパイプライン
データベースの修正・補完作業を一括実行

機能:
1. sentence_placesテーブルの作者・作品情報補完
2. worksテーブルのメタデータ補完（出版年等）
3. sentence_placesテーブルのwork_publication_year補完
4. matched_textフィールドの修正（地名のみ→文全体）

使用例:
    python3 maintenance_pipeline.py --all
    python3 maintenance_pipeline.py --enrich-sentence-places
    python3 maintenance_pipeline.py --enrich-works-metadata
    python3 maintenance_pipeline.py --update-publication-year
    python3 maintenance_pipeline.py --fix-matched-text
"""

import sys
import os
import argparse
import sqlite3
import subprocess
from datetime import datetime
from typing import Dict, Any

# パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from database.sentence_places_enricher import SentencePlacesEnricher
from ..aozora.aozora_metadata_extractor import AozoraMetadataExtractor

class MaintenancePipeline:
    """メンテナンスパイプライン実行器"""
    
    def __init__(self):
        print("🔧 文豪ゆかり地図システム - メンテナンスパイプライン初期化中...")
        self.db_path = os.path.join(parent_dir, 'data', 'bungo_map.db')
        self.enricher = SentencePlacesEnricher()
        self.metadata_extractor = AozoraMetadataExtractor()
        print("✅ メンテナンスパイプライン初期化完了")
    
    def run_all_maintenance(self) -> Dict[str, Any]:
        """全メンテナンス作業を一括実行"""
        start_time = datetime.now()
        print(f"\n🚀 全メンテナンス作業開始 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        results = {
            'start_time': start_time,
            'success': False,
            'steps_completed': [],
            'steps_failed': [],
            'enriched_sentence_places': 0,
            'enriched_works': 0,
            'updated_publication_years': 0,
            'fixed_matched_texts': 0,
            'errors': []
        }
        
        try:
            # ステップ1: sentence_placesテーブル補完
            print("\n🔄 ステップ1: sentence_placesテーブル作者・作品情報補完...")
            step1_result = self.enrich_sentence_places()
            if step1_result['success']:
                results['enriched_sentence_places'] = step1_result['enriched_count']
                results['steps_completed'].append('sentence_places_enrichment')
                print(f"✅ ステップ1完了: {step1_result['enriched_count']}件補完")
            else:
                results['steps_failed'].append('sentence_places_enrichment')
                results['errors'].extend(step1_result['errors'])
                print(f"❌ ステップ1失敗: {step1_result['errors']}")
            
            # ステップ2: worksメタデータ補完
            print("\n🔄 ステップ2: worksテーブルメタデータ補完...")
            step2_result = self.enrich_works_metadata()
            if step2_result['success']:
                results['enriched_works'] = step2_result['enriched_count']
                results['steps_completed'].append('works_metadata_enrichment')
                print(f"✅ ステップ2完了: {step2_result['enriched_count']}件補完")
            else:
                results['steps_failed'].append('works_metadata_enrichment')
                results['errors'].extend(step2_result['errors'])
                print(f"❌ ステップ2失敗: {step2_result['errors']}")
            
            # ステップ3: work_publication_year更新
            print("\n🔄 ステップ3: sentence_placesのwork_publication_year補完...")
            step3_result = self.update_publication_years()
            if step3_result['success']:
                results['updated_publication_years'] = step3_result['updated_count']
                results['steps_completed'].append('publication_year_update')
                print(f"✅ ステップ3完了: {step3_result['updated_count']}件更新")
            else:
                results['steps_failed'].append('publication_year_update')
                results['errors'].extend(step3_result['errors'])
                print(f"❌ ステップ3失敗: {step3_result['errors']}")
            
            # ステップ4: matched_text修正
            print("\n🔄 ステップ4: matched_textフィールド修正（地名のみ→文全体）...")
            step4_result = self.fix_matched_text()
            if step4_result['success']:
                results['fixed_matched_texts'] = step4_result['fixed_count']
                results['steps_completed'].append('matched_text_fix')
                print(f"✅ ステップ4完了: {step4_result['fixed_count']}件修正")
            else:
                results['steps_failed'].append('matched_text_fix')
                results['errors'].extend(step4_result['errors'])
                print(f"❌ ステップ4失敗: {step4_result['errors']}")
            
            results['success'] = len(results['steps_failed']) == 0
            
        except Exception as e:
            print(f"❌ メンテナンスパイプライン実行エラー: {e}")
            results['errors'].append(str(e))
        
        # 最終レポート
        end_time = datetime.now()
        results['end_time'] = end_time
        results['duration'] = (end_time - start_time).total_seconds()
        
        self._print_report(results)
        return results
    
    def enrich_sentence_places(self) -> Dict[str, Any]:
        """sentence_placesテーブルの作者・作品情報補完"""
        try:
            result = self.enricher.run_full_enrichment()
            return {
                'success': True,
                'enriched_count': result.get('enriched_count', 0),
                'errors': []
            }
        except Exception as e:
            return {
                'success': False,
                'enriched_count': 0,
                'errors': [str(e)]
            }
    
    def enrich_works_metadata(self) -> Dict[str, Any]:
        """worksテーブルのメタデータ補完"""
        try:
            # enrich_works_metadata.pyを実行
            result = subprocess.run([
                'python3', 'enrich_works_metadata.py'
            ], capture_output=True, text=True, cwd=current_dir)
            
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
                
                return {
                    'success': True,
                    'enriched_count': enriched_count,
                    'errors': []
                }
            else:
                return {
                    'success': False,
                    'enriched_count': 0,
                    'errors': [result.stderr]
                }
        except Exception as e:
            return {
                'success': False,
                'enriched_count': 0,
                'errors': [str(e)]
            }
    
    def update_publication_years(self) -> Dict[str, Any]:
        """sentence_placesのwork_publication_year補完"""
        try:
            # update_work_publication_year.pyを実行
            result = subprocess.run([
                'python3', 'update_work_publication_year.py'
            ], capture_output=True, text=True, cwd=current_dir)
            
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
                
                return {
                    'success': True,
                    'updated_count': updated_count,
                    'errors': []
                }
            else:
                return {
                    'success': False,
                    'updated_count': 0,
                    'errors': [result.stderr]
                }
        except Exception as e:
            return {
                'success': False,
                'updated_count': 0,
                'errors': [str(e)]
            }
    
    def fix_matched_text(self) -> Dict[str, Any]:
        """matched_textフィールドの修正（地名のみ→文全体）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 修正前の状態確認
            cursor.execute("SELECT COUNT(*) FROM sentence_places")
            total_count = cursor.fetchone()[0]
            
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
            
            return {
                'success': True,
                'fixed_count': fixed_count,
                'errors': []
            }
        except Exception as e:
            return {
                'success': False,
                'fixed_count': 0,
                'errors': [str(e)]
            }
    
    def get_database_status(self) -> Dict[str, Any]:
        """データベース状況確認"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            status = {}
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) FROM authors")
            status['total_authors'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM works")
            status['total_works'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sentences")
            status['total_sentences'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sentence_places")
            status['total_sentence_places'] = cursor.fetchone()[0]
            
            # sentence_placesの補完状況
            cursor.execute("SELECT COUNT(*) FROM sentence_places WHERE author_name IS NOT NULL")
            status['enriched_sentence_places'] = cursor.fetchone()[0]
            
            # worksのメタデータ補完状況
            cursor.execute("SELECT COUNT(*) FROM works WHERE publication_year IS NOT NULL")
            status['works_with_publication_year'] = cursor.fetchone()[0]
            
            # matched_textの状況（サンプル確認）
            cursor.execute("SELECT matched_text, place_name_only FROM sentence_places LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                status['matched_text_fixed'] = sample[0] != sample[1]
            else:
                status['matched_text_fixed'] = False
            
            conn.close()
            return status
            
        except Exception as e:
            return {'error': str(e)}
    
    def _print_report(self, results: Dict[str, Any]):
        """レポート表示"""
        print(f"\n🎉 メンテナンスパイプライン完了レポート")
        print("=" * 80)
        print(f"⏱️  実行時間: {results['duration']:.1f}秒")
        print(f"🏆 総合結果: {'成功' if results['success'] else '失敗'}")
        print(f"✅ 成功ステップ: {len(results['steps_completed'])}件")
        print(f"❌ 失敗ステップ: {len(results['steps_failed'])}件")
        
        print(f"\n📊 処理結果:")
        print(f"  📝 sentence_places補完: {results['enriched_sentence_places']}件")
        print(f"  📚 worksメタデータ補完: {results['enriched_works']}件")
        print(f"  📅 出版年更新: {results['updated_publication_years']}件")
        print(f"  🔧 matched_text修正: {results['fixed_matched_texts']}件")
        
        if results['steps_completed']:
            print(f"\n✅ 成功ステップ:")
            for step in results['steps_completed']:
                print(f"  - {step}")
        
        if results['steps_failed']:
            print(f"\n❌ 失敗ステップ:")
            for step in results['steps_failed']:
                print(f"  - {step}")
        
        if results['errors']:
            print(f"\n❌ エラー詳細: {len(results['errors'])}件")
            for error in results['errors']:
                print(f"  - {error}")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='文豪ゆかり地図システム v4.0 - メンテナンスパイプライン',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全メンテナンス作業実行
  python3 maintenance_pipeline.py --all
  
  # 個別作業実行
  python3 maintenance_pipeline.py --enrich-sentence-places
  python3 maintenance_pipeline.py --enrich-works-metadata
  python3 maintenance_pipeline.py --update-publication-year
  python3 maintenance_pipeline.py --fix-matched-text
  
  # データベース状況確認
  python3 maintenance_pipeline.py --status
        """
    )
    
    parser.add_argument('--all', action='store_true', help='全メンテナンス作業を実行')
    parser.add_argument('--enrich-sentence-places', action='store_true', help='sentence_places補完のみ実行')
    parser.add_argument('--enrich-works-metadata', action='store_true', help='worksメタデータ補完のみ実行')
    parser.add_argument('--update-publication-year', action='store_true', help='出版年更新のみ実行')
    parser.add_argument('--fix-matched-text', action='store_true', help='matched_text修正のみ実行')
    parser.add_argument('--status', action='store_true', help='データベース状況確認のみ')
    
    args = parser.parse_args()
    
    pipeline = MaintenancePipeline()
    
    if args.status:
        print("🔍 データベース状況確認")
        print("=" * 60)
        status = pipeline.get_database_status()
        
        if 'error' in status:
            print(f"❌ エラー: {status['error']}")
        else:
            print(f"👤 作者数: {status['total_authors']:,}件")
            print(f"📚 作品数: {status['total_works']:,}件")
            print(f"📝 センテンス数: {status['total_sentences']:,}件")
            print(f"🗺️ 地名関連数: {status['total_sentence_places']:,}件")
            print(f"✅ sentence_places補完済み: {status['enriched_sentence_places']:,}件")
            print(f"📅 出版年あり作品: {status['works_with_publication_year']:,}件")
            print(f"🔧 matched_text修正済み: {'はい' if status['matched_text_fixed'] else 'いいえ'}")
        
    elif args.all:
        pipeline.run_all_maintenance()
        
    elif args.enrich_sentence_places:
        print("🔄 sentence_places補完実行...")
        result = pipeline.enrich_sentence_places()
        if result['success']:
            print(f"✅ 完了: {result['enriched_count']}件補完")
        else:
            print(f"❌ 失敗: {result['errors']}")
            
    elif args.enrich_works_metadata:
        print("🔄 worksメタデータ補完実行...")
        result = pipeline.enrich_works_metadata()
        if result['success']:
            print(f"✅ 完了: {result['enriched_count']}件補完")
        else:
            print(f"❌ 失敗: {result['errors']}")
            
    elif args.update_publication_year:
        print("🔄 出版年更新実行...")
        result = pipeline.update_publication_years()
        if result['success']:
            print(f"✅ 完了: {result['updated_count']}件更新")
        else:
            print(f"❌ 失敗: {result['errors']}")
            
    elif args.fix_matched_text:
        print("🔄 matched_text修正実行...")
        result = pipeline.fix_matched_text()
        if result['success']:
            print(f"✅ 完了: {result['fixed_count']}件修正")
        else:
            print(f"❌ 失敗: {result['errors']}")
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 