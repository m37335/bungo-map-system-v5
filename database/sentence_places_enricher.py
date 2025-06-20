#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 SentencePlaces データ補完システム v4.0

機能:
- sentence_placesテーブルの作者・作品関連情報を自動補完
- authors・worksテーブルからのJOIN処理
- 統計情報（地名頻度・センテンス位置）の自動計算
- データ整合性チェック・品質管理
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SentencePlaceEnrichment:
    """sentence_places補完データ"""
    sentence_place_id: int
    author_name: str
    author_birth_year: Optional[int]
    author_death_year: Optional[int]
    work_title: str
    work_genre: str
    work_publication_year: Optional[int]
    sentence_position: int
    place_frequency_in_work: int
    place_frequency_by_author: int

class SentencePlacesEnricher:
    """sentence_placesデータ補完クラス"""
    
    def __init__(self, db_path: str = 'data/bungo_map.db'):
        self.db_path = db_path
        logger.info("🔧 SentencePlaces データ補完システム初期化")
        
    def enrich_author_work_info(self) -> Dict[str, int]:
        """作者・作品情報を補完"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 補完対象のレコード数確認
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sentence_places 
                WHERE author_name IS NULL OR work_title IS NULL
            """)
            target_count = cursor.fetchone()[0]
            
            logger.info(f"📊 補完対象レコード数: {target_count}件")
            
            if target_count == 0:
                logger.info("✅ 既に全レコードが補完済みです")
                return {'updated': 0, 'errors': 0}
            
            # JOINで作者・作品情報を取得して更新
            update_query = """
                UPDATE sentence_places 
                SET 
                    author_name = (
                        SELECT a.author_name 
                        FROM sentences s
                        JOIN works w ON s.work_id = w.work_id
                        JOIN authors a ON w.author_id = a.author_id
                        WHERE s.sentence_id = sentence_places.sentence_id
                    ),
                    author_birth_year = (
                        SELECT a.birth_year 
                        FROM sentences s
                        JOIN works w ON s.work_id = w.work_id
                        JOIN authors a ON w.author_id = a.author_id
                        WHERE s.sentence_id = sentence_places.sentence_id
                    ),
                    author_death_year = (
                        SELECT a.death_year 
                        FROM sentences s
                        JOIN works w ON s.work_id = w.work_id
                        JOIN authors a ON w.author_id = a.author_id
                        WHERE s.sentence_id = sentence_places.sentence_id
                    ),
                    work_title = (
                        SELECT w.work_title 
                        FROM sentences s
                        JOIN works w ON s.work_id = w.work_id
                        WHERE s.sentence_id = sentence_places.sentence_id
                    ),
                    work_genre = (
                        SELECT w.genre 
                        FROM sentences s
                        JOIN works w ON s.work_id = w.work_id
                        WHERE s.sentence_id = sentence_places.sentence_id
                    ),
                    work_publication_year = (
                        SELECT w.publication_year 
                        FROM sentences s
                        JOIN works w ON s.work_id = w.work_id
                        WHERE s.sentence_id = sentence_places.sentence_id
                    )
                WHERE author_name IS NULL OR work_title IS NULL
            """
            
            cursor.execute(update_query)
            updated_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"✅ 作者・作品情報補完完了: {updated_count}件更新")
            
            return {'updated': updated_count, 'errors': 0}
            
        except Exception as e:
            logger.error(f"❌ 作者・作品情報補完エラー: {e}")
            conn.rollback()
            return {'updated': 0, 'errors': 1}
        finally:
            conn.close()
    
    def calculate_sentence_positions(self) -> Dict[str, int]:
        """センテンス位置を計算・更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # センテンス位置未設定のレコード確認
            cursor.execute("SELECT COUNT(*) FROM sentence_places WHERE sentence_position IS NULL")
            target_count = cursor.fetchone()[0]
            
            logger.info(f"📍 センテンス位置計算対象: {target_count}件")
            
            if target_count == 0:
                logger.info("✅ 既に全センテンス位置が設定済みです")
                return {'updated': 0, 'errors': 0}
            
            # 作品内でのセンテンス位置を計算
            # sentence_orderがない場合、sentence_idの順序で代用
            update_query = """
                UPDATE sentence_places 
                SET sentence_position = (
                    SELECT COUNT(*) 
                    FROM sentences s2 
                    JOIN sentences s1 ON s1.sentence_id = sentence_places.sentence_id
                    WHERE s2.work_id = s1.work_id 
                    AND s2.sentence_id <= s1.sentence_id
                )
                WHERE sentence_position IS NULL
            """
            
            cursor.execute(update_query)
            updated_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"✅ センテンス位置計算完了: {updated_count}件更新")
            
            return {'updated': updated_count, 'errors': 0}
            
        except Exception as e:
            logger.error(f"❌ センテンス位置計算エラー: {e}")
            conn.rollback()
            return {'updated': 0, 'errors': 1}
        finally:
            conn.close()
    
    def calculate_place_frequencies(self) -> Dict[str, int]:
        """地名頻度を計算・更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 地名頻度未設定のレコード確認
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sentence_places 
                WHERE place_frequency_in_work IS NULL OR place_frequency_by_author IS NULL
            """)
            target_count = cursor.fetchone()[0]
            
            logger.info(f"📊 地名頻度計算対象: {target_count}件")
            
            if target_count == 0:
                logger.info("✅ 既に全地名頻度が設定済みです")
                return {'updated': 0, 'errors': 0}
            
            # 作品内地名頻度を計算
            logger.info("🔄 作品内地名頻度を計算中...")
            update_work_frequency_query = """
                UPDATE sentence_places 
                SET place_frequency_in_work = (
                    SELECT COUNT(*) 
                    FROM sentence_places sp2
                    JOIN sentences s1 ON s1.sentence_id = sentence_places.sentence_id
                    JOIN sentences s2 ON s2.sentence_id = sp2.sentence_id
                    WHERE s1.work_id = s2.work_id 
                    AND sp2.place_id = sentence_places.place_id
                )
                WHERE place_frequency_in_work IS NULL
            """
            
            cursor.execute(update_work_frequency_query)
            work_freq_updated = cursor.rowcount
            
            # 作者別地名頻度を計算
            logger.info("🔄 作者別地名頻度を計算中...")
            update_author_frequency_query = """
                UPDATE sentence_places 
                SET place_frequency_by_author = (
                    SELECT COUNT(*) 
                    FROM sentence_places sp2
                    JOIN sentences s1 ON s1.sentence_id = sentence_places.sentence_id
                    JOIN sentences s2 ON s2.sentence_id = sp2.sentence_id
                    WHERE s1.author_id = s2.author_id 
                    AND sp2.place_id = sentence_places.place_id
                )
                WHERE place_frequency_by_author IS NULL
            """
            
            cursor.execute(update_author_frequency_query)
            author_freq_updated = cursor.rowcount
            
            conn.commit()
            
            total_updated = work_freq_updated + author_freq_updated
            logger.info(f"✅ 地名頻度計算完了: 作品内{work_freq_updated}件, 作者別{author_freq_updated}件")
            
            return {'updated': total_updated, 'errors': 0}
            
        except Exception as e:
            logger.error(f"❌ 地名頻度計算エラー: {e}")
            conn.rollback()
            return {'updated': 0, 'errors': 1}
        finally:
            conn.close()
    
    def run_full_enrichment(self) -> Dict[str, any]:
        """完全補完処理を実行"""
        logger.info("🚀 sentence_places 完全データ補完開始")
        
        results = {
            'start_time': datetime.now(),
            'author_work_info': {},
            'sentence_positions': {},
            'place_frequencies': {},
            'total_updated': 0,
            'total_errors': 0
        }
        
        # 1. 作者・作品情報補完
        logger.info("📚 ステップ1: 作者・作品情報補完")
        results['author_work_info'] = self.enrich_author_work_info()
        
        # 2. センテンス位置計算
        logger.info("📍 ステップ2: センテンス位置計算")
        results['sentence_positions'] = self.calculate_sentence_positions()
        
        # 3. 地名頻度計算
        logger.info("📊 ステップ3: 地名頻度計算")
        results['place_frequencies'] = self.calculate_place_frequencies()
        
        # 統計集計
        results['total_updated'] = (
            results['author_work_info']['updated'] +
            results['sentence_positions']['updated'] +
            results['place_frequencies']['updated']
        )
        results['total_errors'] = (
            results['author_work_info']['errors'] +
            results['sentence_positions']['errors'] +
            results['place_frequencies']['errors']
        )
        
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        
        # 結果レポート
        self._print_enrichment_report(results)
        
        return results
    
    def _print_enrichment_report(self, results: Dict[str, any]):
        """補完結果レポート表示"""
        print("\n" + "="*60)
        print("🎉 sentence_places データ補完完了レポート")
        print("="*60)
        
        print(f"⏱️ 処理時間: {results['duration']}")
        print(f"✅ 総更新件数: {results['total_updated']:,}件")
        print(f"❌ 総エラー数: {results['total_errors']}件")
        print()
        
        print("📊 詳細結果:")
        print(f"  📚 作者・作品情報: {results['author_work_info']['updated']}件更新")
        print(f"  📍 センテンス位置: {results['sentence_positions']['updated']}件更新")
        print(f"  📊 地名頻度: {results['place_frequencies']['updated']}件更新")
        print()
        
        if results['total_errors'] == 0:
            print("🎯 全ての補完処理が正常に完了しました！")
        else:
            print(f"⚠️ {results['total_errors']}件のエラーが発生しました")
    
    def verify_enrichment(self) -> Dict[str, any]:
        """補完結果の検証"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 各列の入力状況確認
            cursor.execute("SELECT COUNT(*) FROM sentence_places")
            total_count = cursor.fetchone()[0]
            
            verification = {
                'total_records': total_count,
                'null_counts': {},
                'completion_rates': {}
            }
            
            columns_to_check = [
                'author_name', 'author_birth_year', 'author_death_year',
                'work_title', 'work_genre', 'work_publication_year',
                'sentence_position', 'place_frequency_in_work', 'place_frequency_by_author'
            ]
            
            for column in columns_to_check:
                cursor.execute(f"SELECT COUNT(*) FROM sentence_places WHERE {column} IS NULL")
                null_count = cursor.fetchone()[0]
                completion_rate = ((total_count - null_count) / total_count * 100) if total_count > 0 else 0
                
                verification['null_counts'][column] = null_count
                verification['completion_rates'][column] = completion_rate
            
            return verification
            
        finally:
            conn.close()

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='sentence_places データ補完システム')
    parser.add_argument('--verify-only', action='store_true', help='検証のみ実行')
    parser.add_argument('--author-work-only', action='store_true', help='作者・作品情報のみ補完')
    parser.add_argument('--frequencies-only', action='store_true', help='頻度計算のみ実行')
    
    args = parser.parse_args()
    
    enricher = SentencePlacesEnricher()
    
    # 検証のみ
    if args.verify_only:
        verification = enricher.verify_enrichment()
        
        print("=== 📊 sentence_places 補完状況検証 ===")
        print(f"総レコード数: {verification['total_records']:,}件")
        print()
        
        for column, completion_rate in verification['completion_rates'].items():
            null_count = verification['null_counts'][column]
            print(f"{column}: {completion_rate:.1f}% 完了 (NULL: {null_count}件)")
        
        return
    
    # 部分補完
    if args.author_work_only:
        result = enricher.enrich_author_work_info()
        print(f"作者・作品情報補完: {result['updated']}件更新")
        return
    
    if args.frequencies_only:
        result = enricher.calculate_place_frequencies()
        print(f"地名頻度計算: {result['updated']}件更新")
        return
    
    # 完全補完実行
    enricher.run_full_enrichment()

if __name__ == "__main__":
    main() 