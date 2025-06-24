#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者全作品統合処理スクリプト

指定作者または全作者について、作品リスト取得から本文処理まで
ワークフロー①〜⑦を完全実行するマスタースクリプト
"""

import sys
import os
import time
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Any

# パスを追加
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/../'))

from database.manager import DatabaseManager
from ..aozora.collect_author_works import AuthorWorksCollector
from ..aozora.fetch_work_content import WorkContentProcessor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteAuthorProcessor:
    """作者全作品統合処理クラス"""
    
    def __init__(self):
        """初期化"""
        self.db_manager = DatabaseManager()
        self.works_collector = AuthorWorksCollector()
        self.content_processor = WorkContentProcessor()
        
    def process_author_complete(self, author_name: str, content_processing: bool = True) -> Dict[str, Any]:
        """指定作者の完全処理（ワークフロー①〜⑦）
        
        Args:
            author_name: 作者名
            content_processing: 本文処理も実行するか
            
        Returns:
            Dict[str, Any]: 処理結果統計
        """
        logger.info(f"作者完全処理開始: {author_name}")
        
        start_time = datetime.now()
        result = {
            'author_name': author_name,
            'author_found': False,
            'works_collection': {},
            'content_processing': {},
            'total_time': 0,
            'success': False
        }
        
        try:
            # 作者情報の取得
            author = self.db_manager.get_author_by_name(author_name)
            if not author:
                logger.error(f"作者が見つかりません: {author_name}")
                return result
            
            result['author_found'] = True
            logger.info(f"作者発見: {author.author_name} (ID: {author.author_id})")
            
            if not author.aozora_author_url:
                logger.warning(f"青空文庫URLが設定されていません: {author_name}")
                return result
            
            # ステップ①②③: 作品リスト収集
            logger.info("=== ステップ①②③: 作品リスト収集 ===")
            new_works_count = self.works_collector.collect_works_for_author(
                author.author_id,
                author.author_name,
                author.aozora_author_url
            )
            
            result['works_collection'] = {
                'new_works': new_works_count,
                'completed': True
            }
            
            if content_processing:
                # ステップ④⑤⑥⑦: 本文処理
                logger.info("=== ステップ④⑤⑥⑦: 本文処理 ===")
                content_stats = self.content_processor.process_author_works(
                    author.author_id,
                    author.author_name
                )
                result['content_processing'] = content_stats
                result['content_processing']['completed'] = True
            else:
                logger.info("本文処理はスキップされました")
                result['content_processing'] = {'skipped': True}
            
            # 最終統計
            end_time = datetime.now()
            result['total_time'] = (end_time - start_time).total_seconds()
            result['success'] = True
            
            logger.info(f"作者完全処理完了: {author_name} ({result['total_time']:.1f}秒)")
            return result
            
        except Exception as e:
            logger.error(f"作者完全処理エラー {author_name}: {e}")
            return result
    
    def process_multiple_authors(self, author_names: List[str], content_processing: bool = True) -> Dict[str, Any]:
        """複数作者の一括処理
        
        Args:
            author_names: 作者名のリスト
            content_processing: 本文処理も実行するか
            
        Returns:
            Dict[str, Any]: 全体の処理結果統計
        """
        logger.info(f"複数作者一括処理開始: {len(author_names)}名")
        
        start_time = datetime.now()
        results = {
            'total_authors': len(author_names),
            'successful_authors': 0,
            'failed_authors': 0,
            'total_new_works': 0,
            'total_sentences': 0,
            'author_results': [],
            'total_time': 0
        }
        
        for i, author_name in enumerate(author_names, 1):
            logger.info(f"進捗: {i}/{len(author_names)} - {author_name}")
            
            try:
                author_result = self.process_author_complete(author_name, content_processing)
                results['author_results'].append(author_result)
                
                if author_result['success']:
                    results['successful_authors'] += 1
                    results['total_new_works'] += author_result['works_collection'].get('new_works', 0)
                    
                    if content_processing and 'total_sentences' in author_result['content_processing']:
                        results['total_sentences'] += author_result['content_processing']['total_sentences']
                else:
                    results['failed_authors'] += 1
                    
            except Exception as e:
                logger.error(f"作者処理エラー {author_name}: {e}")
                results['failed_authors'] += 1
                continue
                
            # 作者間のレート制限
            time.sleep(2.0)
        
        end_time = datetime.now()
        results['total_time'] = (end_time - start_time).total_seconds()
        
        logger.info(f"複数作者一括処理完了: {results}")
        return results
    
    def process_all_authors(self, limit: Optional[int] = None, content_processing: bool = True) -> Dict[str, Any]:
        """全作者の一括処理
        
        Args:
            limit: 処理する作者数の上限
            content_processing: 本文処理も実行するか
            
        Returns:
            Dict[str, Any]: 全体の処理結果統計
        """
        logger.info("全作者一括処理開始")
        
        # aozora_author_urlが設定されている作者を取得
        authors = self.db_manager.get_authors_with_aozora_url()
        if limit:
            authors = authors[:limit]
        
        author_names = [author.author_name for author in authors]
        logger.info(f"対象作者数: {len(author_names)}")
        
        return self.process_multiple_authors(author_names, content_processing)
    
    def get_author_processing_status(self, author_name: str) -> Dict[str, Any]:
        """作者の処理状況を確認
        
        Args:
            author_name: 作者名
            
        Returns:
            Dict[str, Any]: 処理状況
        """
        author = self.db_manager.get_author_by_name(author_name)
        if not author:
            return {'error': f'作者が見つかりません: {author_name}'}
        
        works = self.db_manager.get_works_by_author(author.author_id)
        
        # 本文処理済み作品を確認
        completed_works = 0
        total_sentences = 0
        
        for work in works:
            if hasattr(work, 'processing_status') and work.processing_status == 'completed':
                completed_works += 1
                if hasattr(work, 'sentence_count') and work.sentence_count:
                    total_sentences += work.sentence_count
        
        status = {
            'author_name': author.author_name,
            'author_id': author.author_id,
            'has_aozora_url': bool(author.aozora_author_url),
            'total_works': len(works),
            'completed_works': completed_works,
            'pending_works': len(works) - completed_works,
            'total_sentences': total_sentences,
            'completion_rate': (completed_works / len(works) * 100) if works else 0
        }
        
        return status

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='作者全作品統合処理')
    parser.add_argument('--author', '-a', type=str, help='処理対象作者名')
    parser.add_argument('--authors', '-m', nargs='+', help='複数作者名（スペース区切り）')
    parser.add_argument('--all', action='store_true', help='全作者を処理')
    parser.add_argument('--limit', '-l', type=int, help='処理作者数の上限')
    parser.add_argument('--no-content', action='store_true', help='本文処理をスキップ（作品リストのみ）')
    parser.add_argument('--status', '-s', type=str, help='指定作者の処理状況を確認')
    
    args = parser.parse_args()
    
    processor = CompleteAuthorProcessor()
    
    # 処理状況確認
    if args.status:
        status = processor.get_author_processing_status(args.status)
        print("\n=== 作者処理状況 ===")
        for key, value in status.items():
            print(f"{key}: {value}")
        return
    
    content_processing = not args.no_content
    
    # 単一作者処理
    if args.author:
        result = processor.process_author_complete(args.author, content_processing)
        print(f"\n=== 処理結果: {args.author} ===")
        print(f"成功: {result['success']}")
        if result['success']:
            print(f"新規作品: {result['works_collection'].get('new_works', 0)}件")
            if content_processing and 'total_sentences' in result.get('content_processing', {}):
                print(f"総センテンス数: {result['content_processing']['total_sentences']}")
        
    # 複数作者処理
    elif args.authors:
        results = processor.process_multiple_authors(args.authors, content_processing)
        print(f"\n=== 複数作者処理結果 ===")
        print(f"成功: {results['successful_authors']}/{results['total_authors']}名")
        print(f"新規作品: {results['total_new_works']}件")
        if content_processing:
            print(f"総センテンス数: {results['total_sentences']}")
    
    # 全作者処理
    elif args.all:
        results = processor.process_all_authors(args.limit, content_processing)
        print(f"\n=== 全作者処理結果 ===")
        print(f"成功: {results['successful_authors']}/{results['total_authors']}名")
        print(f"新規作品: {results['total_new_works']}件")
        if content_processing:
            print(f"総センテンス数: {results['total_sentences']}")
    
    # デフォルト: 夏目漱石でテスト
    else:
        logger.info("デフォルト: 夏目漱石でテスト実行")
        result = processor.process_author_complete('夏目 漱石', content_processing)
        print(f"\n=== 夏目漱石テスト結果 ===")
        print(f"成功: {result['success']}")
        if result['success']:
            print(f"新規作品: {result['works_collection'].get('new_works', 0)}件")
            if content_processing and 'total_sentences' in result.get('content_processing', {}):
                print(f"総センテンス数: {result['content_processing']['total_sentences']}")

if __name__ == '__main__':
    main() 