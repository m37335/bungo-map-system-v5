#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青空文庫スクレイパー

青空文庫から作品を取得し、データベースに保存する
"""

import requests
import time
import unicodedata
from typing import Dict, List, Optional, Tuple, Any, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging
import os
import chardet
import re
import json
from datetime import datetime, timedelta
import concurrent.futures
from tqdm import tqdm
import threading
from queue import Queue
import signal
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/../'))
from database.models import Author, Work, Sentence
from database.manager import DatabaseManager

logger = logging.getLogger(__name__)

class AozoraScraper:
    """青空文庫スクレイパー"""
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """初期化"""
        self.config = config or {}
        self.db_manager = db_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BungoMapBot/2.0 (Educational Research Purpose)'
        })
        self.author_list_url = self.config.get('author_list_url', 'https://www.aozora.gr.jp/index_pages/person_all.html')
        self.logger = logging.getLogger(__name__)
        
        # キャッシュディレクトリの設定
        self.cache_dir = self.config.get('cache_dir', 'data/aozora_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # レート制限の設定
        self.rate_limit = self.config.get('rate_limit', 1.0)  # 秒
        self.last_request_time = 0
        self.request_count = 0
        self.max_retries = self.config.get('max_retries', 3)
        
        # キャッシュの有効期限（デフォルト7日）
        self.cache_expiry = self.config.get('cache_expiry', 7)
        
        # 既知の作品URLデータベース
        self.known_works = self._load_known_works()
        
        # 並列処理の設定
        self.max_workers = self.config.get('max_workers', 4)
        self.thread_local = threading.local()
        
        # 進捗状況の設定
        self.progress_queue = Queue()
        self.total_works = 0
        self.processed_works = 0
        
        # エラーリカバリーの設定
        self.error_log_path = os.path.join(self.cache_dir, 'error_log.json')
        self.failed_works: Set[Tuple[str, str]] = set()
        self._load_error_log()
        
        # シグナルハンドラの設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラ"""
        self.logger.info("処理を中断します...")
        self._save_error_log()
        sys.exit(0)
    
    def _load_error_log(self):
        """エラーログを読み込む"""
        if os.path.exists(self.error_log_path):
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    error_data = json.load(f)
                    self.failed_works = {tuple(k.split('||')) for k in error_data.get('failed_works', [])}
            except Exception as e:
                self.logger.error(f"エラーログの読み込みに失敗: {e}")
    
    def _save_error_log(self):
        """エラーログを保存"""
        try:
            with open(self.error_log_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'failed_works': [f"{k[0]}||{k[1]}" for k in self.failed_works],
                    'timestamp': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"エラーログの保存に失敗: {e}")
    
    def _get_session(self):
        """スレッドローカルなセッションを取得"""
        if not hasattr(self.thread_local, 'session'):
            self.thread_local.session = requests.Session()
            self.thread_local.session.headers.update({
                'User-Agent': 'BungoMapBot/2.0 (Educational Research Purpose)'
            })
        return self.thread_local.session
    
    def _load_known_works(self) -> Dict[Tuple[str, str], str]:
        """既知の作品URLデータベースを読み込む"""
        known_works_path = os.path.join(self.cache_dir, 'known_works.json')
        if os.path.exists(known_works_path):
            try:
                with open(known_works_path, 'r', encoding='utf-8') as f:
                    return {tuple(k.split('||')): v for k, v in json.load(f).items()}
            except Exception as e:
                self.logger.error(f"既知の作品データベースの読み込みに失敗: {e}")
        
        return {}
    
    def _save_known_works(self):
        """既知の作品URLデータベースを保存"""
        known_works_path = os.path.join(self.cache_dir, 'known_works.json')
        try:
            with open(known_works_path, 'w', encoding='utf-8') as f:
                json.dump({f"{k[0]}||{k[1]}": v for k, v in self.known_works.items()}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"既知の作品データベースの保存に失敗: {e}")
    
    def _wait_for_rate_limit(self):
        """レート制限を考慮して待機"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # リクエスト数の制限（1分間に60リクエスト）
        if self.request_count >= 60:
            time.sleep(60)
            self.request_count = 0
        
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _get_cached_content(self, url: str) -> Optional[str]:
        """キャッシュからコンテンツを取得"""
        cache_path = os.path.join(self.cache_dir, f"{hash(url)}.txt")
        if os.path.exists(cache_path):
            # キャッシュの有効期限をチェック
            cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            if datetime.now() - cache_time < timedelta(days=self.cache_expiry):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # 期限切れのキャッシュを削除
                os.remove(cache_path)
        return None
    
    def _save_to_cache(self, url: str, content: str):
        """コンテンツをキャッシュに保存"""
        cache_path = os.path.join(self.cache_dir, f"{hash(url)}.txt")
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def fetch_author_list(self) -> List[Dict[str, str]]:
        """著者一覧を取得"""
        self._wait_for_rate_limit()
        
        for retry in range(self.max_retries):
            try:
                session = self._get_session()
                response = session.get(self.author_list_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                authors = []
                
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href and 'person' in href:
                        author_name = link.text.strip()
                        author_url = urljoin(self.author_list_url, href)
                        authors.append({
                            'name': author_name,
                            'url': author_url
                        })
                
                return authors
                
            except requests.exceptions.RequestException as e:
                if retry == self.max_retries - 1:
                    self.logger.error(f"著者一覧の取得に失敗: {e}")
                    return []
                time.sleep(2 ** retry)  # 指数バックオフ
    
    def fetch_author_works(self, author_url: str) -> List[Dict[str, str]]:
        """著者の作品一覧を取得"""
        self._wait_for_rate_limit()
        
        for retry in range(self.max_retries):
            try:
                session = self._get_session()
                response = session.get(author_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                works = []
                
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href and 'cards' in href:
                        work_title = link.text.strip()
                        work_url = urljoin(author_url, href)
                        works.append({
                            'title': work_title,
                            'url': work_url
                        })
                
                return works
                
            except requests.exceptions.RequestException as e:
                if retry == self.max_retries - 1:
                    self.logger.error(f"作品一覧の取得に失敗: {e}")
                    return []
                time.sleep(2 ** retry)  # 指数バックオフ
    
    def fetch_work_content(self, work_url: str) -> Optional[str]:
        """作品の本文を取得"""
        # キャッシュをチェック
        cached_content = self._get_cached_content(work_url)
        if cached_content:
            return cached_content
        
        self._wait_for_rate_limit()
        
        for retry in range(self.max_retries):
            try:
                session = self._get_session()
                response = session.get(work_url)
                response.raise_for_status()
                
                # 文字コードの判定
                encoding = chardet.detect(response.content)['encoding']
                if not encoding:
                    encoding = 'utf-8'
                
                content = response.content.decode(encoding)
                
                # 本文の抽出
                soup = BeautifulSoup(content, 'html.parser')
                main_text = soup.find('div', class_='main_text')
                
                if main_text:
                    text = main_text.get_text()
                    # 正規化
                    text = self._normalize_text(text)
                    # キャッシュに保存
                    self._save_to_cache(work_url, text)
                    return text
                
                return None
                
            except requests.exceptions.RequestException as e:
                if retry == self.max_retries - 1:
                    self.logger.error(f"作品本文の取得に失敗: {e}")
                    return None
                time.sleep(2 ** retry)  # 指数バックオフ
    
    def _normalize_text(self, text: str) -> str:
        """テキストの正規化"""
        # 改行の統一
        text = re.sub(r'\r\n|\r|\n', '\n', text)
        
        # 空白の正規化
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 全角文字の正規化
        text = unicodedata.normalize('NFKC', text)
        
        # ルビの削除
        text = re.sub(r'《[^》]*》', '', text)
        
        # 注釈の削除
        text = re.sub(r'［[^］]*］', '', text)
        
        # 空行の削除
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
    
    def process_work(self, author_name: str, work_title: str, work_url: str) -> bool:
        """作品の処理と保存"""
        if not self.db_manager:
            self.logger.error("データベースマネージャーが設定されていません")
            return False
        
        try:
            # 著者の取得または作成
            author = self.db_manager.get_or_create_author(author_name)
            
            # 作品の取得または作成
            work = self.db_manager.get_or_create_work(
                title=work_title,
                author_id=author.author_id,
                aozora_url=work_url
            )
            
            # 本文の取得
            content = self.fetch_work_content(work_url)
            if not content:
                self.failed_works.add((author_name, work_title))
                self._save_error_log()
                return False
            
            # 文の分割と保存
            sentences = self._split_into_sentences(content)
            for sentence in sentences:
                self.db_manager.create_sentence(
                    work_id=work.work_id,
                    content=sentence
                )
            
            # 既知の作品として保存
            self.known_works[(author_name, work_title)] = work_url
            self._save_known_works()
            
            # 進捗状況の更新
            self.processed_works += 1
            self.progress_queue.put({
                'processed': self.processed_works,
                'total': self.total_works,
                'current': f"{author_name} - {work_title}"
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"作品の処理に失敗: {e}")
            self.failed_works.add((author_name, work_title))
            self._save_error_log()
            return False
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """テキストを文に分割"""
        # 文末記号で分割
        sentences = re.split(r'[。．！？]', text)
        
        # 空の文を除去
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def add_new_work(self, author_name: str, work_title: str, work_url: str) -> bool:
        """新規作品を追加"""
        if (author_name, work_title) in self.known_works:
            self.logger.info(f"既に登録済みの作品です: {author_name} - {work_title}")
            return False
        
        success = self.process_work(author_name, work_title, work_url)
        if success:
            self.logger.info(f"新規作品を追加しました: {author_name} - {work_title}")
        return success
    
    def process_author_works(self, author_name: str, author_url: str) -> List[Dict[str, str]]:
        """著者の全作品を処理"""
        works = self.fetch_author_works(author_url)
        processed_works = []
        
        for work in works:
            if self.process_work(author_name, work['title'], work['url']):
                processed_works.append(work)
        
        return processed_works
    
    def batch_process(self, authors: List[Dict[str, str]], show_progress: bool = True):
        """複数の著者の作品を一括処理"""
        self.total_works = 0
        self.processed_works = 0
        
        # 総作品数の計算
        for author in authors:
            works = self.fetch_author_works(author['url'])
            self.total_works += len(works)
        
        # 進捗表示の設定
        if show_progress:
            pbar = tqdm(total=self.total_works, desc="作品処理")
        
        # 並列処理の実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for author in authors:
                future = executor.submit(self.process_author_works, author['name'], author['url'])
                futures.append(future)
            
            # 進捗状況の監視
            while futures:
                done, not_done = concurrent.futures.wait(
                    futures,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                for future in done:
                    try:
                        processed_works = future.result()
                        if show_progress:
                            pbar.update(len(processed_works))
                    except Exception as e:
                        self.logger.error(f"バッチ処理でエラーが発生: {e}")
                
                futures = list(not_done)
        
        if show_progress:
            pbar.close()
        
        # エラーリカバリー
        if self.failed_works:
            self.logger.info(f"失敗した作品数: {len(self.failed_works)}")
            self.logger.info("エラーログを保存しました: {self.error_log_path}")
    
    def retry_failed_works(self, show_progress: bool = True):
        """失敗した作品の再処理"""
        if not self.failed_works:
            self.logger.info("再処理が必要な作品はありません")
            return
        
        self.total_works = len(self.failed_works)
        self.processed_works = 0
        
        if show_progress:
            pbar = tqdm(total=self.total_works, desc="失敗作品の再処理")
        
        retried_works = set()
        for author_name, work_title in self.failed_works:
            work_url = self.known_works.get((author_name, work_title))
            if work_url and self.process_work(author_name, work_title, work_url):
                retried_works.add((author_name, work_title))
                if show_progress:
                    pbar.update(1)
        
        if show_progress:
            pbar.close()
        
        # 成功した作品を失敗リストから削除
        self.failed_works -= retried_works
        self._save_error_log()
        
        self.logger.info(f"再処理完了: {len(retried_works)}件成功, {len(self.failed_works)}件失敗") 