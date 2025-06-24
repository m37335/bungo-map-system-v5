#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者作品収集スクリプト

データベース内のaozora_author_urlから作品を収集し、worksテーブルに保存
"""

import sys
import os
import time
import logging
import unicodedata
import re
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional

# パスを追加
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/../'))

from database.manager import DatabaseManager
from .aozora_scraper import AozoraScraper

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthorWorksCollector:
    """作者作品収集クラス"""
    
    def __init__(self):
        """初期化"""
        self.db_manager = DatabaseManager()
        self.scraper = AozoraScraper(db_manager=self.db_manager)
        
    def collect_works_for_author(self, author_id: int, author_name: str, author_url: str) -> int:
        """指定作者の作品を収集してデータベースに保存
        
        Args:
            author_id: 作者ID
            author_name: 作者名
            author_url: 青空文庫の作者ページURL
            
        Returns:
            int: 新規保存した作品数
        """
        logger.info(f"作者「{author_name}」の作品収集開始: {author_url}")
        
        try:
            # 既存作品をチェック
            existing_works = self.db_manager.get_works_by_author(author_id)
            existing_titles = {work.title for work in existing_works}
            logger.info(f"既存作品数: {len(existing_titles)}")
            
            # 作者ページから作品リストを取得
            works_data = self.scraper.fetch_author_works(author_url)
            logger.info(f"青空文庫から取得した作品数: {len(works_data)}")
            
            new_works_count = 0
            
            for work_data in works_data:
                title = work_data.get('title', '').strip()
                work_url = work_data.get('url', '')
                
                if not title or not work_url:
                    continue
                
                # テキスト正規化（文字化け対策）
                title = self._normalize_text(title)
                
                # 重複チェック
                if title in existing_titles:
                    logger.debug(f"既存作品をスキップ: {title}")
                    continue
                
                # 作品をデータベースに保存
                work_dict = {
                    'author_id': author_id,
                    'title': title,
                    'aozora_url': urljoin(author_url, work_url),
                    'created_at': datetime.now()
                }
                
                try:
                    work_id = self.db_manager.save_work(work_dict)
                    if work_id:
                        new_works_count += 1
                        logger.info(f"新規作品保存: {title} (ID: {work_id})")
                    else:
                        logger.warning(f"作品保存失敗: {title}")
                        
                except Exception as e:
                    logger.error(f"作品保存エラー「{title}」: {e}")
                    continue
                
                # レート制限
                time.sleep(0.1)
                
            logger.info(f"作者「{author_name}」の作品収集完了: 新規{new_works_count}作品")
            return new_works_count
            
        except Exception as e:
            logger.error(f"作者「{author_name}」の作品収集エラー: {e}")
            return 0
    
    def _detect_genre(self, title: str) -> Optional[str]:
        """タイトルからジャンルを推測（簡易版）
        
        Args:
            title: 作品タイトル
            
        Returns:
            Optional[str]: ジャンル名（小説/随筆/詩/戯曲/評論）またはNone
        """
        title_lower = title.lower()
        
        # 詩のキーワード
        if any(keyword in title_lower for keyword in ['詩', '歌', '俳句', '短歌', 'うた']):
            return '詩'
        
        # 戯曲のキーワード  
        if any(keyword in title_lower for keyword in ['戯曲', '脚本', '劇', '一幕']):
            return '戯曲'
            
        # 評論のキーワード
        if any(keyword in title_lower for keyword in ['論', '評', '批評', '研究', '考察', '序文', '解説']):
            return '評論'
            
        # 随筆のキーワード
        if any(keyword in title_lower for keyword in ['随筆', '日記', '記', '雑記', '感想', '印象']):
            return '随筆'
            
        # デフォルトは小説
        return '小説'
    
    def _normalize_text(self, text: str) -> str:
        """テキストの正規化（文字化け対策）
        
        Args:
            text: 正規化するテキスト
            
        Returns:
            str: 正規化されたテキスト
        """
        if not text:
            return ''
        
        # Unicode正規化（文字化け修正）
        text = unicodedata.normalize('NFKC', text)
        
        # 制御文字の除去
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # 不正な文字の除去
        text = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF々〆〤、。・！？「」『』（）【】〔〕《》]', '', text)
        
        # 連続する空白の正規化
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def collect_all_authors_works(self, limit: Optional[int] = None) -> Dict[str, int]:
        """全作者の作品を収集
        
        Args:
            limit: 処理する作者数の上限（Noneで全作者）
            
        Returns:
            Dict[str, int]: 結果統計
        """
        logger.info("全作者の作品収集開始")
        
        # aozora_author_urlが設定されている作者を取得
        authors = self.db_manager.get_authors_with_aozora_url()
        logger.info(f"対象作者数: {len(authors)}")
        
        if limit:
            authors = authors[:limit]
            logger.info(f"処理制限により{limit}名に制限")
            
        total_new_works = 0
        processed_authors = 0
        failed_authors = 0
        
        for author in authors:
            try:
                new_works = self.collect_works_for_author(
                    author.author_id, 
                    author.author_name, 
                    author.aozora_author_url
                )
                total_new_works += new_works
                processed_authors += 1
                
                # 進捗表示
                if processed_authors % 10 == 0:
                    logger.info(f"進捗: {processed_authors}/{len(authors)}作者処理完了")
                    
            except Exception as e:
                logger.error(f"作者処理エラー「{author.author_name}」: {e}")
                failed_authors += 1
                continue
                
            # レート制限（サーバー負荷軽減）
            time.sleep(1.0)
            
        results = {
            'processed_authors': processed_authors,
            'failed_authors': failed_authors, 
            'total_new_works': total_new_works
        }
        
        logger.info(f"全作者の作品収集完了: {results}")
        return results

def main():
    """メイン処理"""
    collector = AuthorWorksCollector()
    
    # 夏目漱石でテスト
    author = collector.db_manager.get_author_by_name('夏目 漱石')
    if author:
        logger.info("夏目漱石でテスト実行")
        new_works = collector.collect_works_for_author(
            author.author_id,
            author.author_name,
            author.aozora_author_url
        )
        logger.info(f"テスト完了: 新規作品{new_works}件")
    else:
        logger.error("夏目漱石が見つかりません")

if __name__ == '__main__':
    main() 