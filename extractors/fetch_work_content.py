#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作品本文取得・処理スクリプト

作品ページからXHTMLファイルを取得し、本文をクリーニングしてセンテンス分割してデータベースに保存
"""

import sys
import os
import time
import logging
import requests
import chardet
import re
import unicodedata
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# パスを追加
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/../'))

from database.manager import DatabaseManager
from database.models import Work, Sentence

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkContentProcessor:
    """作品本文処理クラス"""
    
    def __init__(self):
        """初期化"""
        self.db_manager = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BungoMapBot/2.0 (Educational Research Purpose)'
        })
        
    def fetch_xhtml_links(self, work_url: str) -> List[Dict[str, str]]:
        """作品ページからXHTMLファイルのリンクを取得
        
        Args:
            work_url: 作品ページのURL
            
        Returns:
            List[Dict[str, str]]: XHTMLリンクのリスト
        """
        try:
            response = self.session.get(work_url)
            response.raise_for_status()
            
            # エンコーディング処理
            encoding = chardet.detect(response.content)['encoding']
            if not encoding or encoding.lower() == 'ascii':
                encoding = 'shift_jis'
            
            content = response.content.decode(encoding)
            soup = BeautifulSoup(content, 'html.parser')
            
            xhtml_links = []
            
            # XHTMLファイルのリンクを探す
            for link in soup.find_all('a'):
                href = link.get('href', '')
                text = link.text.strip()
                
                # 数字_数字.htmlのパターンを探す
                if href.endswith('.html') and re.search(r'\d+_\d+\.html$', href):
                    full_url = urljoin(work_url, href)
                    xhtml_links.append({
                        'text': text,
                        'href': href,
                        'full_url': full_url
                    })
            
            logger.info(f"XHTMLリンク {len(xhtml_links)}件を発見: {work_url}")
            return xhtml_links
            
        except Exception as e:
            logger.error(f"XHTMLリンク取得エラー {work_url}: {e}")
            return []
    
    def fetch_xhtml_content(self, xhtml_url: str) -> Optional[str]:
        """XHTMLファイルから本文を取得
        
        Args:
            xhtml_url: XHTMLファイルのURL
            
        Returns:
            Optional[str]: クリーニングされた本文テキスト
        """
        try:
            response = self.session.get(xhtml_url)
            response.raise_for_status()
            
            # エンコーディング処理
            encoding = chardet.detect(response.content)['encoding']
            if not encoding:
                encoding = 'utf-8'
            
            content = response.content.decode(encoding)
            soup = BeautifulSoup(content, 'html.parser')
            
            # 本文テキストの抽出
            body_text = self.extract_main_text(soup)
            
            if body_text:
                # テキストクリーニング
                cleaned_text = self.clean_text(body_text)
                logger.info(f"本文取得成功 ({len(cleaned_text)}文字): {xhtml_url}")
                return cleaned_text
            else:
                logger.warning(f"本文が見つかりません: {xhtml_url}")
                return None
                
        except Exception as e:
            logger.error(f"本文取得エラー {xhtml_url}: {e}")
            return None
    
    def extract_main_text(self, soup: BeautifulSoup) -> str:
        """XHTMLから本文テキストを抽出
        
        Args:
            soup: BeautifulSoupオブジェクト
            
        Returns:
            str: 抽出されたテキスト
        """
        # パターン1: <div class="main_text">
        main_text = soup.find('div', class_='main_text')
        if main_text:
            return main_text.get_text()
        
        # パターン2: <body>内のテキスト（不要要素除去）
        body = soup.find('body')
        if body:
            # 不要な要素を除去
            for element in body.find_all(['script', 'style', 'header', 'footer', 'nav']):
                element.decompose()
            
            return body.get_text()
        
        # パターン3: 全体のテキスト
        return soup.get_text()
    
    def clean_text(self, text: str) -> str:
        """テキストのクリーニング（ワークフロー⑤）
        
        Args:
            text: 原文テキスト
            
        Returns:
            str: クリーニングされたテキスト
        """
        if not text:
            return ''
        
        # Unicode正規化
        text = unicodedata.normalize('NFKC', text)
        
        # 改行の正規化
        text = re.sub(r'\r\n|\r|\n', '\n', text)
        
        # 青空文庫形式の注釈・ルビ除去
        text = re.sub(r'《[^》]*》', '', text)      # ルビ
        text = re.sub(r'［[^］]*］', '', text)      # 注釈
        text = re.sub(r'〔[^〕]*〕', '', text)      # 編集者注
        text = re.sub(r'※[^※]*※', '', text)       # 特殊注釈
        
        # HTMLタグ除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 連続する空白・改行の正規化
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # 制御文字除去
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def split_into_sentences(self, text: str) -> List[str]:
        """テキストをセンテンス単位に分割（ワークフロー⑥）- 句読点保持版
        
        Args:
            text: クリーニング済みテキスト
            
        Returns:
            List[str]: センテンスのリスト（句読点保持）
        """
        if not text:
            return []
        
        # 句読点を保持しながら分割
        parts = re.split(r'([。．！？])', text)
        
        sentences = []
        current_sentence = ""
        
        for part in parts:
            if part in ['。', '．', '！', '？']:
                # 句読点を現在の文に追加
                current_sentence += part
                # 文が完成したので追加
                if current_sentence.strip() and len(current_sentence.strip()) >= 3:
                    sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                current_sentence += part
        
        # 最後の部分を処理（句読点なしで終わる場合）
        if current_sentence.strip() and len(current_sentence.strip()) >= 3:
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def process_work_content(self, work_id: int, work_title: str, work_url: str, author_id: int) -> Dict[str, int]:
        """作品の本文を処理してデータベースに保存
        
        Args:
            work_id: 作品ID
            work_title: 作品タイトル
            work_url: 作品ページURL
            
        Returns:
            Dict[str, int]: 処理結果統計
        """
        logger.info(f"作品本文処理開始: {work_title} (ID: {work_id})")
        
        result = {
            'xhtml_links': 0,
            'content_length': 0,
            'sentences_saved': 0,
            'success': False
        }
        
        try:
            # ステップ④: XHTMLリンクの取得
            xhtml_links = self.fetch_xhtml_links(work_url)
            result['xhtml_links'] = len(xhtml_links)
            
            if not xhtml_links:
                logger.warning(f"XHTMLリンクが見つかりません: {work_title}")
                return result
            
            # 最初のXHTMLファイルを使用（通常は1つのみ）
            xhtml_url = xhtml_links[0]['full_url']
            
            # ステップ⑤: 本文取得とクリーニング
            content = self.fetch_xhtml_content(xhtml_url)
            
            if not content:
                logger.warning(f"本文が取得できません: {work_title}")
                return result
            
            result['content_length'] = len(content)
            
            # ステップ⑥: センテンス分割
            sentences = self.split_into_sentences(content)
            
            if not sentences:
                logger.warning(f"センテンスが抽出できません: {work_title}")
                return result
            
            # ステップ⑦: センテンスのデータベース保存
            saved_count = 0
            for order, sentence_text in enumerate(sentences, 1):
                sentence_dict = {
                    'work_id': work_id,
                    'author_id': author_id,
                    'sentence_order': order,
                    'sentence_text': sentence_text,
                    'character_count': len(sentence_text),
                    'created_at': datetime.now()
                }
                
                sentence_id = self.db_manager.save_sentence(sentence_dict)
                if sentence_id:
                    saved_count += 1
                else:
                    logger.warning(f"センテンス保存失敗: {work_title} #{order}")
            
            result['sentences_saved'] = saved_count
            
            # 作品テーブルの統計情報を更新
            self.update_work_statistics(work_id, result['content_length'], saved_count)
            
            result['success'] = True
            logger.info(f"作品本文処理完了: {work_title} ({saved_count}センテンス保存)")
            
            return result
            
        except Exception as e:
            logger.error(f"作品本文処理エラー {work_title}: {e}")
            return result
    
    def update_work_statistics(self, work_id: int, content_length: int, sentence_count: int):
        """作品の統計情報を更新
        
        Args:
            work_id: 作品ID
            content_length: 本文文字数
            sentence_count: センテンス数
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE works 
                    SET content_length = ?, sentence_count = ?, processing_status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE work_id = ?
                    """,
                    (content_length, sentence_count, work_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"作品統計更新エラー (ID: {work_id}): {e}")
    
    def process_author_works(self, author_id: int, author_name: str, limit: Optional[int] = None) -> Dict[str, int]:
        """指定作者の全作品を処理
        
        Args:
            author_id: 作者ID
            author_name: 作者名
            limit: 処理作品数の上限
            
        Returns:
            Dict[str, int]: 処理結果統計
        """
        logger.info(f"作者作品処理開始: {author_name} (ID: {author_id})")
        
        # 作品リストを取得
        works = self.db_manager.get_works_by_author(author_id)
        if limit:
            works = works[:limit]
        
        logger.info(f"処理対象作品数: {len(works)}")
        
        total_stats = {
            'processed_works': 0,
            'successful_works': 0,
            'total_sentences': 0,
            'total_content_length': 0,
            'failed_works': 0
        }
        
        for work in works:
            try:
                result = self.process_work_content(
                    work.work_id,
                    work.work_title,
                    work.aozora_url,
                    work.author_id
                )
                
                total_stats['processed_works'] += 1
                
                if result['success']:
                    total_stats['successful_works'] += 1
                    total_stats['total_sentences'] += result['sentences_saved']
                    total_stats['total_content_length'] += result['content_length']
                else:
                    total_stats['failed_works'] += 1
                
                # レート制限
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"作品処理エラー {work.work_title}: {e}")
                total_stats['failed_works'] += 1
                continue
        
        logger.info(f"作者作品処理完了: {author_name} - {total_stats}")
        return total_stats

def main():
    """メイン処理"""
    processor = WorkContentProcessor()
    
    # 夏目漱石の「こころ」でテスト
    # まず「こころ」の実際のwork_idとauthor_idを取得
    works = processor.db_manager.get_works_by_author(862)  # 夏目漱石のID
    kokoro_work = None
    for work in works:
        if work.work_title == 'こころ':
            kokoro_work = work
            break
    
    if kokoro_work:
        logger.info("=== 単一作品テスト ===")
        result = processor.process_work_content(
            kokoro_work.work_id,
            kokoro_work.work_title,
            kokoro_work.aozora_url,
            kokoro_work.author_id
        )
        logger.info(f"テスト結果: {result}")
    else:
        logger.error("「こころ」の作品データが見つかりません")

if __name__ == '__main__':
    main() 