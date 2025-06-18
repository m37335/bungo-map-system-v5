#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文豪マップシステム V4 - 作者作品収集スクリプト
ワークフロー ステップ①②③: 作者URL取得 → 作品リスト取得 → 作品DB保存

Legacy codes from bungo-map-v4を活用してv4システムに統合
"""

import sys
import os
import logging
import requests
import chardet
import unicodedata
import re
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import time

# v4システムのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.manager import DatabaseManager
from database.models import Author, Work

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthorWorksCollector:
    """作者作品収集システム（Legacy青空文庫スクレイパー改良版）"""
    
    def __init__(self, db_path: str = "data/bungo_map.db"):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.session = requests.Session()
        self.base_url = "https://www.aozora.gr.jp"
        self.author_list_url = "https://www.aozora.gr.jp/index_pages/person_all.html"
        
        # レート制限設定
        self.request_delay = 1.0  # 1秒間隔
        
        logger.info("📚 作者作品収集システム初期化完了")
    
    def collect_author_works(self, author_name: str) -> Tuple[bool, Dict]:
        """
        指定された作者の作品を収集してデータベースに保存
        
        Args:
            author_name: 作者名
            
        Returns:
            Tuple[bool, Dict]: (成功/失敗, 結果情報)
        """
        logger.info(f"🎯 作者作品収集開始: {author_name}")
        start_time = time.time()
        
        try:
            # ステップ①: 作者URLの取得
            author_url = self._get_author_url(author_name)
            if not author_url:
                return False, {"error": "作者ページが見つかりません"}
            
            logger.info(f"✅ 作者URL発見: {author_url}")
            
            # ステップ②: 作品リストと作品URLの取得
            works_list = self._get_works_list(author_url)
            if not works_list:
                return False, {"error": "作品リストが取得できません"}
            
            logger.info(f"✅ 作品リスト取得: {len(works_list)}件")
            
            # ステップ③: 作品リストのデータベース保存
            saved_count = self._save_works_to_database(author_name, author_url, works_list)
            
            elapsed_time = time.time() - start_time
            
            result = {
                "author_name": author_name,
                "author_url": author_url,
                "total_works": len(works_list),
                "saved_works": saved_count,
                "elapsed_time": elapsed_time
            }
            
            logger.info(f"🎉 作者作品収集完了: {saved_count}/{len(works_list)}件保存 ({elapsed_time:.2f}秒)")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ 作者作品収集エラー: {e}")
            return False, {"error": str(e)}
    
    def _get_author_url(self, author_name: str) -> Optional[str]:
        """
        ステップ①: 作者名から作者ページのURLを取得
        Legacy aozora_scraper.pyの get_author_url メソッドを改良
        """
        def normalize_name(name: str) -> str:
            """作者名を正規化"""
            return unicodedata.normalize('NFKC', name).replace('\u3000', ' ').strip()
        
        def is_valid_person_href(href: str) -> bool:
            """hrefが有効なpersonXX.html形式かチェック"""
            if not href:
                return False
            # #以降を除去
            href = href.split('#')[0]
            # personXX.htmlの形式かチェック
            return bool(re.match(r'^person\d+\.html$', href))
        
        try:
            logger.info(f"🔍 作者URL検索: {author_name}")
            
            # レート制限
            time.sleep(self.request_delay)
            
            # 作者リストページ取得
            response = self.session.get(self.author_list_url)
            response.raise_for_status()
            
            # エンコーディング検出
            detected = chardet.detect(response.content)
            encoding = detected["encoding"] or "shift_jis"
            
            # HTMLパース
            html = response.content.decode(encoding, errors="replace")
            soup = BeautifulSoup(html, 'html.parser', from_encoding=encoding)
            
            # 作者名の正規化
            target_name = normalize_name(author_name)
            
            # リンク検索
            for link in soup.find_all('a'):
                link_text = link.text
                normalized_text = normalize_name(link_text)
                href = link.get('href')
                
                # 作者名が一致し、かつ有効なpersonXX.htmlの場合
                if normalized_text == target_name and is_valid_person_href(href):
                    # #以降を除去
                    href_clean = href.split('#')[0]
                    
                    # index_pages/の重複を防ぐ
                    if href_clean.startswith("index_pages/"):
                        author_url = f"https://www.aozora.gr.jp/{href_clean}"
                    else:
                        author_url = f"https://www.aozora.gr.jp/index_pages/{href_clean}"
                    
                    return author_url
            
            return None
            
        except Exception as e:
            logger.error(f"作者URL取得エラー: {e}")
            return None
    
    def _get_works_list(self, author_url: str) -> List[Dict[str, str]]:
        """
        ステップ②: 作者ページから作品リストを取得
        Legacy aozora_scraper.pyの get_works_list メソッドを改良
        """
        logger.info(f"📖 作品リスト取得: {author_url}")
        works = []
        
        try:
            # レート制限
            time.sleep(self.request_delay)
            
            response = self.session.get(author_url)
            response.raise_for_status()
            
            # エンコーディング検出
            detected = chardet.detect(response.content)
            encoding = detected["encoding"] or "shift_jis"
            
            html = response.content.decode(encoding, errors="replace")
            soup = BeautifulSoup(html, 'html.parser', from_encoding=encoding)
            
            # 「公開中の作品」セクションを探す
            for h2 in soup.find_all('h2'):
                if h2.text.strip() == '公開中の作品':
                    ol = h2.find_next('ol')
                    if ol:
                        for li in ol.find_all('li'):
                            a_tag = li.find('a')
                            if a_tag:
                                title = a_tag.text.strip()
                                href = a_tag.get('href', '')
                                
                                if href.startswith('/cards/'):
                                    work_url = 'https://www.aozora.gr.jp' + href
                                    
                                    # ジャンル判定（簡易版）
                                    genre = self._detect_genre(title)
                                    
                                    works.append({
                                        'title': title,
                                        'url': work_url,
                                        'genre': genre
                                    })
            
            logger.info(f"✅ 作品リスト解析完了: {len(works)}件")
            return works
            
        except Exception as e:
            logger.error(f"作品リスト取得エラー: {e}")
            return []
    
    def _detect_genre(self, title: str) -> Optional[str]:
        """作品タイトルからジャンルを推定"""
        genre_keywords = {
            '小説': ['物語', '記', '日記', '記録'],
            '随筆': ['随筆', '雑感', '感想', '思い出'],
            '詩': ['詩', '詩集', '歌'],
            '戯曲': ['戯曲', '劇', '台本'],
            '評論': ['評論', '論', '批評', '解説']
        }
        
        for genre, keywords in genre_keywords.items():
            if any(keyword in title for keyword in keywords):
                return genre
        
        return '小説'  # デフォルト
    
    def _get_author_with_flexible_name(self, author_name: str) -> Optional:
        """
        柔軟な作者名検索（データベースの表記に合わせてスペースを追加）
        """
        # 検索パターンを構築
        search_patterns = [author_name]  # 入力そのまま
        
        # スペースがない場合、スペースを追加したパターンを試行
        if " " not in author_name and len(author_name) >= 3:
            # 一般的な分割パターン（姓2文字+名、姓1文字+名）
            if len(author_name) >= 4:
                search_patterns.append(f"{author_name[:2]} {author_name[2:]}")  # 夏目漱石 → 夏目 漱石
            if len(author_name) >= 3:
                search_patterns.append(f"{author_name[:1]} {author_name[1:]}")  # 夏目漱石 → 夏 目漱石
        
        # 各パターンで検索
        for pattern in search_patterns:
            logger.debug(f"🔍 検索パターン: '{pattern}'")
            author = self.db_manager.get_author_by_name(pattern)
            if author:
                logger.info(f"✅ 作者発見: '{pattern}' → {author.author_name}")
                return author
        
        # 部分一致検索（LIKE演算子）でより柔軟に検索
        try:
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 苗字部分での部分一致検索
                if " " in author_name:
                    lastname = author_name.split()[0]
                else:
                    lastname = author_name[:2] if len(author_name) >= 2 else author_name
                
                cursor = conn.execute(
                    "SELECT * FROM authors WHERE author_name LIKE ? LIMIT 5",
                    (f"%{lastname}%",)
                )
                results = cursor.fetchall()
                
                if results:
                    # 最初の候補を返す
                    result = results[0]
                    from database.models import Author
                    author = Author()
                    for key in result.keys():
                        setattr(author, key, result[key])
                    logger.info(f"🔍 部分一致で発見: '{author_name}' → {author.author_name}")
                    
                    # 複数の候補がある場合は警告
                    if len(results) > 1:
                        candidates = [r['author_name'] for r in results]
                        logger.warning(f"⚠️ 複数の候補が見つかりました: {candidates}")
                    
                    return author
                    
        except Exception as e:
            logger.warning(f"部分一致検索エラー: {e}")
        
        return None
    
    def _save_works_to_database(self, author_name: str, author_url: str, works_list: List[Dict]) -> int:
        """
        ステップ③: 作品リストをデータベースに保存
        """
        logger.info(f"💾 データベース保存開始: {len(works_list)}件")
        
        try:
            # 作者情報の取得
            author = self._get_author_with_flexible_name(author_name)
            if not author:
                logger.error(f"作者情報がデータベースに見つかりません: {author_name}")
                return 0
            
            saved_count = 0
            
            for work_data in works_list:
                try:
                    # 重複チェック
                    existing_work = self.db_manager.get_work_by_title_and_author(
                        work_data['title'], author.author_id
                    )
                    
                    if existing_work:
                        logger.debug(f"作品は既に存在: {work_data['title']}")
                        continue
                    
                    # 新規作品保存
                    work_info = {
                        'work_title': work_data['title'],
                        'author_id': author.author_id,
                        'genre': work_data.get('genre'),
                        'aozora_url': work_data['url'],
                        'source_system': 'v4.0',
                        'processing_status': 'pending',
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                    
                    work_id = self.db_manager.save_work(work_info)
                    if work_id:
                        saved_count += 1
                        logger.debug(f"作品保存成功: {work_data['title']} (ID: {work_id})")
                    
                except Exception as e:
                    logger.warning(f"作品保存エラー: {work_data['title']} - {e}")
                    continue
            
            logger.info(f"✅ データベース保存完了: {saved_count}件")
            return saved_count
            
        except Exception as e:
            logger.error(f"データベース保存エラー: {e}")
            return 0
    
    def collect_all_authors_works(self, limit: Optional[int] = None) -> Dict:
        """
        データベース内のすべての作者の作品を収集
        
        Args:
            limit: 処理する作者数の上限（None = 全作者）
            
        Returns:
            Dict: 収集結果の統計情報
        """
        logger.info("🌟 全作者作品収集開始")
        start_time = time.time()
        
        # データベースから作者リストを取得
        authors = self.db_manager.get_all_authors()
        if limit:
            authors = authors[:limit]
        
        total_authors = len(authors)
        successful_authors = 0
        total_works_collected = 0
        
        results = []
        
        for i, author in enumerate(authors, 1):
            logger.info(f"📚 処理中 [{i}/{total_authors}]: {author.author_name}")
            
            success, result = self.collect_author_works(author.author_name)
            
            if success:
                successful_authors += 1
                total_works_collected += result.get('saved_works', 0)
            
            results.append({
                'author_name': author.author_name,
                'success': success,
                **result
            })
            
            # 進捗表示
            if i % 10 == 0:
                logger.info(f"📊 進捗: {i}/{total_authors} 完了 ({successful_authors}人成功)")
        
        elapsed_time = time.time() - start_time
        
        summary = {
            'total_authors': total_authors,
            'successful_authors': successful_authors,
            'total_works_collected': total_works_collected,
            'elapsed_time': elapsed_time,
            'results': results
        }
        
        logger.info(f"🎉 全作者作品収集完了: {successful_authors}/{total_authors}人 "
                   f"({total_works_collected}作品, {elapsed_time:.2f}秒)")
        
        return summary


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="作者作品収集スクリプト")
    parser.add_argument("--author", "-a", help="収集する作者名")
    parser.add_argument("--all", action="store_true", help="全作者の作品を収集")
    parser.add_argument("--limit", "-l", type=int, help="処理する作者数の上限")
    parser.add_argument("--db", default="data/bungo_map.db", help="データベースファイルパス")
    
    args = parser.parse_args()
    
    collector = AuthorWorksCollector(args.db)
    
    if args.author:
        # 特定作者の作品収集
        success, result = collector.collect_author_works(args.author)
        if success:
            print(f"✅ 成功: {result}")
        else:
            print(f"❌ 失敗: {result}")
    
    elif args.all:
        # 全作者の作品収集
        summary = collector.collect_all_authors_works(args.limit)
        print(f"📊 収集結果: {summary}")
    
    else:
        print("--author または --all オプションを指定してください")
        parser.print_help()


if __name__ == "__main__":
    main() 