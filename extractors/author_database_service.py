#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作家データベース統合サービス
青空文庫作家リストの取得とデータベース格納を統合
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .author_list_scraper import AuthorListScraper, AuthorInfo
from ..database.manager import DatabaseManager
from ..database.models import Author
from ..core.config import get_config

logger = logging.getLogger(__name__)

class AuthorDatabaseService:
    """作家データベース統合サービス"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """初期化"""
        self.config = get_config()
        self.db_manager = db_manager or DatabaseManager()
        self.scraper = AuthorListScraper(rate_limit=1.0)
        
        logger.info("📚 作家データベースサービス初期化完了")
    
    async def sync_all_authors(self, force_refresh: bool = False) -> Dict[str, Any]:
        """全作家情報の同期"""
        print("🔄 青空文庫作家データベース同期開始")
        print("=" * 60)
        
        try:
            # 1. 青空文庫から作家情報取得
            print("📚 青空文庫から作家情報取得中...")
            authors_info = self.scraper.fetch_all_authors()
            
            if not authors_info:
                print("❌ 作家情報取得失敗")
                return {'success': False, 'error': '作家情報取得失敗'}
            
            print(f"✅ 作家情報取得完了: {len(authors_info)}名")
            
            # 2. データベースへの格納
            print("💾 データベースへの格納中...")
            sync_result = await self._sync_authors_to_database(authors_info, force_refresh)
            
            # 3. 統計情報の更新
            print("📊 統計情報更新中...")
            await self._update_statistics()
            
            # 4. 結果レポート
            result = {
                'success': True,
                'total_authors': len(authors_info),
                'new_authors': sync_result['new_count'],
                'updated_authors': sync_result['updated_count'],
                'sync_time': datetime.now().isoformat()
            }
            
            self._print_sync_report(result)
            return result
            
        except Exception as e:
            logger.error(f"❌ 作家同期エラー: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _sync_authors_to_database(self, authors_info: List[AuthorInfo], force_refresh: bool) -> Dict[str, int]:
        """作家情報をデータベースに同期"""
        new_count = 0
        updated_count = 0
        
        try:
            # データベースに格納する形式に変換
            authors_data = []
            for author_info in authors_info:
                author_data = self._convert_to_db_format(author_info)
                authors_data.append(author_data)
            
            # 既存作家との比較・更新
            for author_data in authors_data:
                existing_author = self.db_manager.get_author_by_name(author_data['author_name'])
                
                if existing_author:
                    # 既存作家の更新判定
                    needs_update = (
                        force_refresh or
                        existing_author.aozora_works_count != author_data.get('aozora_works_count', 0) or
                        existing_author.copyright_status != author_data.get('copyright_status', 'expired')
                    )
                    
                    if needs_update:
                        # 既存作家の更新
                        await self._update_author_info(existing_author, author_data)
                        updated_count += 1
                else:
                    # 新作家の作成
                    self.db_manager.create_author(author_data)
                    new_count += 1
            
            return {'new_count': new_count, 'updated_count': updated_count}
            
        except Exception as e:
            logger.error(f"❌ データベース同期エラー: {e}")
            raise
    
    def _convert_to_db_format(self, author_info: AuthorInfo) -> Dict[str, Any]:
        """AuthorInfoをデータベース形式に変換"""
        return {
            'author_name': author_info.name,
            'author_name_kana': author_info.name_reading,
            'aozora_author_url': author_info.author_url,
            'copyright_status': author_info.copyright_status,
            'aozora_works_count': author_info.works_count,
            'alias_info': author_info.alias_info,
            'section': author_info.section,
            'source_system': 'aozora_v4.0',
            'verification_status': 'auto_scraped'
        }
    
    async def _update_author_info(self, author: Author, new_data: Dict[str, Any]):
        """既存作家情報の更新"""
        try:
            for key, value in new_data.items():
                if hasattr(author, key) and value is not None:
                    setattr(author, key, value)
            
            author.updated_at = datetime.utcnow()
            self.db_manager.update_author(author.author_id, new_data)
            
        except Exception as e:
            logger.error(f"❌ 作家情報更新エラー: {author.author_name} - {e}")
    
    async def _update_statistics(self):
        """統計情報の更新"""
        try:
            # 作家統計の再計算
            stats = self.db_manager.get_author_statistics()
            logger.info(f"📊 統計更新完了: {stats}")
            
        except Exception as e:
            logger.error(f"❌ 統計更新エラー: {e}")
    
    def _print_sync_report(self, result: Dict[str, Any]):
        """同期結果レポートの表示"""
        print(f"\n📊 同期完了レポート")
        print("=" * 60)
        print(f"総作家数: {result['total_authors']:,}名")
        print(f"新規作家: {result['new_authors']:,}名")
        print(f"更新作家: {result['updated_authors']:,}名")
        print(f"同期時刻: {result['sync_time']}")
        print("✅ 作家データベース同期完了")
    
    async def search_authors(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """作家検索"""
        try:
            authors = self.db_manager.search_authors_by_name(search_term, limit)
            
            result = []
            for author in authors:
                result.append({
                    'author_id': author.author_id,
                    'name': author.author_name,
                    'name_kana': author.author_name_kana,
                    'works_count': author.aozora_works_count,
                    'copyright_status': author.copyright_status,
                    'section': author.section,
                    'aozora_url': author.aozora_author_url
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 作家検索エラー: {e}")
            return []
    
    async def get_authors_by_section(self, section: str) -> List[Dict[str, Any]]:
        """セクション別作家取得"""
        try:
            # セクション検索機能をCRUDに追加する必要があります
            # 今回は簡易実装
            authors = self.db_manager.get_all_authors()
            filtered_authors = [a for a in authors if a.section == section]
            
            result = []
            for author in filtered_authors:
                result.append({
                    'author_id': author.author_id,
                    'name': author.author_name,
                    'works_count': author.aozora_works_count,
                    'copyright_status': author.copyright_status
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ セクション検索エラー: {e}")
            return []
    
    async def get_author_statistics(self) -> Dict[str, Any]:
        """作家統計取得"""
        try:
            base_stats = self.db_manager.get_author_statistics()
            
            # 追加統計
            all_authors = self.db_manager.get_all_authors()
            
            # 著作権状態別統計
            copyright_stats = {}
            section_stats = {}
            
            for author in all_authors:
                # 著作権統計
                copyright_status = author.copyright_status or 'unknown'
                copyright_stats[copyright_status] = copyright_stats.get(copyright_status, 0) + 1
                
                # セクション統計
                section = author.section or 'その他'
                section_stats[section] = section_stats.get(section, 0) + 1
            
            return {
                **base_stats,
                'copyright_stats': copyright_stats,
                'section_stats': section_stats,
                'last_sync': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 統計取得エラー: {e}")
            return {}

async def main():
    """メイン実行関数"""
    service = AuthorDatabaseService()
    
    # 全作家同期
    result = await service.sync_all_authors()
    
    if result['success']:
        # 統計表示
        stats = await service.get_author_statistics()
        print(f"\n📊 最終統計:")
        print(f"総作家数: {stats.get('total_authors', 0):,}名")
        print(f"総作品数: {stats.get('total_works', 0):,}作品")
        
        # セクション別統計
        section_stats = stats.get('section_stats', {})
        print(f"\n📚 セクション別統計:")
        for section, count in sorted(section_stats.items()):
            print(f"  {section}: {count:,}名")
        
        # 著作権状態別統計
        copyright_stats = stats.get('copyright_stats', {})
        print(f"\n⚖️ 著作権状態別統計:")
        for status, count in copyright_stats.items():
            print(f"  {status}: {count:,}名")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 