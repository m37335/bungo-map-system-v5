#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青空文庫作家リスト専用スクレイパー
作家一覧ページから詳細な作者情報を取得してデータベースに格納
"""

import requests
import re
import logging
import time
import sqlite3
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dataclasses import dataclass
import json
from datetime import datetime
import os
import argparse

logger = logging.getLogger(__name__)

@dataclass
class AuthorInfo:
    """作者情報データクラス"""
    name: str
    name_reading: Optional[str]
    works_count: int
    copyright_status: str  # 'expired', 'active', 'unknown'
    author_url: Optional[str]
    alias_info: Optional[str]  # 別名情報
    section: str  # あ、か、さ等のセクション

class AuthorListScraper:
    """青空文庫作家リスト専用スクレイパー"""
    
    def __init__(self, rate_limit: float = 1.0, db_path: str = "data/bungo_map.db"):
        """初期化"""
        self.base_url = "https://www.aozora.gr.jp"
        self.author_list_url = "https://www.aozora.gr.jp/index_pages/person_all.html"
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.db_path = db_path
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BungoMapBot/4.0 (Educational Research Purpose)'
        })
        
        # セクション別URL（50音順）
        self.section_urls = {
            'あ': f"{self.base_url}/index_pages/person_all_a.html",
            'か': f"{self.base_url}/index_pages/person_all_ka.html",
            'さ': f"{self.base_url}/index_pages/person_all_sa.html",
            'た': f"{self.base_url}/index_pages/person_all_ta.html",
            'な': f"{self.base_url}/index_pages/person_all_na.html",
            'は': f"{self.base_url}/index_pages/person_all_ha.html",
            'ま': f"{self.base_url}/index_pages/person_all_ma.html",
            'や': f"{self.base_url}/index_pages/person_all_ya.html",
            'ら': f"{self.base_url}/index_pages/person_all_ra.html",
            'わ': f"{self.base_url}/index_pages/person_all_wa.html",
        }
        
        logger.info("📚 青空文庫作家リストスクレイパー初期化完了")
    
    def _wait_for_rate_limit(self):
        """レート制限を考慮して待機"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        
        self.last_request_time = time.time()
    
    def fetch_all_authors(self, update_database: bool = True) -> List[AuthorInfo]:
        """全作家情報を取得"""
        print("📚 青空文庫全作家情報取得開始")
        print("=" * 60)
        
        all_authors = []
        
        # メインページから取得
        main_authors = self._fetch_authors_from_url(self.author_list_url, "全体")
        all_authors.extend(main_authors)
        
        print(f"✅ 全作家取得完了: {len(all_authors)}名")
        
        # データベース更新オプション
        if update_database and os.path.exists(self.db_path):
            print("\n📊 データベース青空文庫URL更新開始")
            self.update_database_urls(all_authors)
        
        return all_authors
    
    def update_database_urls(self, authors: List[AuthorInfo]) -> Dict[str, int]:
        """データベースの青空文庫URLを更新"""
        try:
            # 青空文庫作者データをマッピング作成
            aozora_urls = {}
            for author in authors:
                if author.author_url:
                    aozora_urls[author.name] = author.author_url
            
            print(f"青空文庫作者データ: {len(aozora_urls)}名のURL情報")
            
            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 青空文庫URL未設定の作者を取得
            cursor.execute('''
                SELECT author_id, author_name 
                FROM authors 
                WHERE aozora_author_url IS NULL OR aozora_author_url = ''
                ORDER BY author_name
            ''')
            authors_without_url = cursor.fetchall()
            
            print(f"URL未設定作者: {len(authors_without_url)}名")
            
            # マッチング・更新処理
            updated_count = 0
            matched_count = 0
            
            for author_id, author_name in authors_without_url:
                # 完全一致チェック
                if author_name in aozora_urls:
                    url = aozora_urls[author_name]
                    cursor.execute(
                        'UPDATE authors SET aozora_author_url = ? WHERE author_id = ?',
                        (url, author_id)
                    )
                    updated_count += 1
                    matched_count += 1
                    print(f'✅ 完全一致: {author_name} -> {url}')
                else:
                    # 部分一致チェック（スペース除去など）
                    author_name_clean = author_name.replace(' ', '').replace('　', '')
                    found = False
                    
                    for aozora_name, url in aozora_urls.items():
                        aozora_name_clean = aozora_name.replace(' ', '').replace('　', '')
                        if author_name_clean == aozora_name_clean:
                            cursor.execute(
                                'UPDATE authors SET aozora_author_url = ? WHERE author_id = ?',
                                (url, author_id)
                            )
                            updated_count += 1
                            matched_count += 1
                            print(f'🔄 部分一致: {author_name} -> {aozora_name} -> {url}')
                            found = True
                            break
                    
                    if not found:
                        print(f'❌ 未発見: {author_name}')
            
            # コミット
            conn.commit()
            conn.close()
            
            print(f'\n=== データベース更新結果 ===')
            print(f'処理対象: {len(authors_without_url)}名')
            print(f'マッチング成功: {matched_count}名')
            print(f'DB更新: {updated_count}名')
            print(f'未発見: {len(authors_without_url) - matched_count}名')
            print('✅ データベース青空文庫URL更新完了')
            
            return {
                'processed': len(authors_without_url),
                'matched': matched_count,
                'updated': updated_count,
                'not_found': len(authors_without_url) - matched_count
            }
            
        except Exception as e:
            logger.error(f"❌ データベース更新エラー: {e}")
            return {'error': str(e)}
    
    def _fetch_authors_from_url(self, url: str, section: str) -> List[AuthorInfo]:
        """指定URLから作家情報を取得"""
        self._wait_for_rate_limit()
        
        try:
            print(f"  📖 {section}セクション処理中...")
            response = self.session.get(url)
            response.raise_for_status()
            
            # 青空文庫の文字エンコーディング処理を改善
            # まずShift_JISでデコードしてからUTF-8に変換
            if response.encoding is None or response.encoding.lower() in ['iso-8859-1', 'ascii']:
                # レスポンスのバイト内容をShift_JISとしてデコード
                try:
                    content = response.content.decode('shift_jis')
                except UnicodeDecodeError:
                    # Shift_JISでデコードできない場合はEUC-JPを試す
                    try:
                        content = response.content.decode('euc-jp')
                    except UnicodeDecodeError:
                        # それでもダメな場合はUTF-8を試す
                        content = response.content.decode('utf-8', errors='ignore')
            else:
                content = response.text
            
            soup = BeautifulSoup(content, 'html.parser')
            authors = self._parse_author_list(soup, section)
            
            print(f"  ✅ {section}: {len(authors)}名取得")
            return authors
            
        except Exception as e:
            logger.error(f"❌ {section}セクション取得エラー: {e}")
            return []
    
    def _parse_author_list(self, soup: BeautifulSoup, section: str) -> List[AuthorInfo]:
        """HTMLから作家リストを解析"""
        authors = []
        
        # 直接ol要素内のli要素を解析（文字化けを考慮してパターンベースで判定）
        ol_elements = soup.find_all('ol')
        print(f"  🔍 検出されたol要素数: {len(ol_elements)}")
        
        # セクション名のマッピング（文字化け対応）
        section_mapping = {
            0: 'ア',  # 最初のolが「ア」セクション
            1: 'カ',
            2: 'サ',
            3: 'タ',
            4: 'ナ',
            5: 'ハ',
            6: 'マ',
            7: 'ヤ',
            8: 'ラ',
            9: 'ワ',
            10: 'その他'
        }
        
        for ol_index, ol in enumerate(ol_elements):
            li_elements = ol.find_all('li')
            current_section = section_mapping.get(ol_index, f"section_{ol_index+1}")
            
            print(f"    ol#{ol_index+1} ({current_section}): {len(li_elements)}個のli要素")
            
            for li in li_elements:
                text = li.get_text().strip()
                # 作家項目の判定：「(公開中：数字)」パターンを含む
                if '公開中：' in text and ')' in text:
                    author_info = self._parse_author_item(li, current_section)
                    if author_info:
                        authors.append(author_info)
        
        return authors
    
    def _parse_author_item(self, li_element, section: str) -> Optional[AuthorInfo]:
        """個別の作家項目を解析"""
        try:
            text = li_element.get_text()
            
            # 基本パターン：「作家名 (公開中：数字)」
            # 拡張パターン：「作家名 (公開中：数字) ＊著作権存続＊」
            # 別名パターン：「作家名 (公開中：数字) (→別名)」
            
            # 作家名とリンクを取得
            link = li_element.find('a')
            author_url = None
            if link and link.get('href'):
                href = link.get('href')
                # URLを正しい形式に変換
                # 例: ../person/person74.html#sakuhin_list_1 -> https://www.aozora.gr.jp/index_pages/person74.html
                if 'person' in href:
                    # person番号を抽出
                    import re as url_re
                    person_match = url_re.search(r'person(\d+)\.html', href)
                    if person_match:
                        person_id = person_match.group(1)
                        author_url = f"https://www.aozora.gr.jp/index_pages/person{person_id}.html"
                    else:
                        # フォールバック: 元のURL結合
                        author_url = urljoin(self.base_url, href)
                else:
                    author_url = urljoin(self.base_url, href)
            
            # テキストから情報を抽出
            # パターン: 基本形式
            match = re.match(r'(.+?)\s*\(公開中：(\d+)\)', text)
            if not match:
                return None
            
            author_name = match.group(1).strip()
            works_count = int(match.group(2))
            
            # 著作権状態を判定
            copyright_status = 'expired'  # デフォルト
            if '＊著作権存続＊' in text:
                copyright_status = 'active'
            
            # 別名情報を抽出
            alias_info = None
            alias_match = re.search(r'\(→(.+?)\)', text)
            if alias_match:
                alias_info = alias_match.group(1).strip()
            
            # 読み仮名を推定（簡易実装）
            name_reading = self._estimate_reading(author_name)
            
            return AuthorInfo(
                name=author_name,
                name_reading=name_reading,
                works_count=works_count,
                copyright_status=copyright_status,
                author_url=author_url,
                alias_info=alias_info,
                section=section
            )
            
        except Exception as e:
            logger.warning(f"作家項目解析エラー: {li_element.get_text()[:50]} - {e}")
            return None
    
    def _estimate_reading(self, name: str) -> Optional[str]:
        """作家名の読み仮名を推定（簡易版）"""
        # 有名作家の読み仮名マッピング
        known_readings = {
            '夏目 漱石': 'なつめ そうせき',
            '芥川 竜之介': 'あくたがわ りゅうのすけ',
            '太宰 治': 'だざい おさむ',
            '川端 康成': 'かわばた やすなり',
            '三島 由紀夫': 'みしま ゆきお',
            '森 鴎外': 'もり おうがい',
            '樋口 一葉': 'ひぐち いちよう',
            '宮沢 賢治': 'みやざわ けんじ',
            '谷崎 潤一郎': 'たにざき じゅんいちろう',
            '志賀 直哉': 'しが なおや'
        }
        
        return known_readings.get(name)
    
    def save_authors_to_json(self, authors: List[AuthorInfo], file_path: str = "data/aozora_authors.json"):
        """作家情報をJSONファイルに保存"""
        try:
            # AuthorInfoをディクショナリに変換
            authors_data = []
            for author in authors:
                authors_data.append({
                    'name': author.name,
                    'name_reading': author.name_reading,
                    'works_count': author.works_count,
                    'copyright_status': author.copyright_status,
                    'author_url': author.author_url,
                    'alias_info': author.alias_info,
                    'section': author.section,
                    'scraped_at': datetime.now().isoformat()
                })
            
            # ディレクトリ作成
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # JSON保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'authors': authors_data,
                    'total_count': len(authors_data),
                    'scraped_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 作家情報保存完了: {file_path} ({len(authors_data)}名)")
            
        except Exception as e:
            logger.error(f"❌ 作家情報保存エラー: {e}")
    
    def get_statistics(self, authors: List[AuthorInfo]) -> Dict[str, any]:
        """作家情報の統計を取得"""
        total_authors = len(authors)
        total_works = sum(author.works_count for author in authors)
        
        # 著作権状態別統計
        copyright_active = len([a for a in authors if a.copyright_status == 'active'])
        copyright_expired = len([a for a in authors if a.copyright_status == 'expired'])
        
        # セクション別統計
        section_stats = {}
        for author in authors:
            section = author.section
            if section not in section_stats:
                section_stats[section] = 0
            section_stats[section] += 1
        
        # 作品数上位作家
        top_authors = sorted(authors, key=lambda x: x.works_count, reverse=True)[:10]
        
        return {
            'total_authors': total_authors,
            'total_works': total_works,
            'copyright_active': copyright_active,
            'copyright_expired': copyright_expired,
            'section_stats': section_stats,
            'top_authors': [(a.name, a.works_count) for a in top_authors],
            'average_works_per_author': round(total_works / total_authors, 2) if total_authors > 0 else 0
        }
    
    def find_author_url(self, author_name: str) -> Optional[str]:
        """単一作者の青空文庫URLを検索"""
        try:
            # JSON設定ファイルから既存データを読み込み
            json_path = "data/aozora_authors.json"
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 既存データから検索
                for author in data.get('authors', []):
                    if author['name'] == author_name and author.get('author_url'):
                        return author['author_url']
                    
                    # 部分一致も試行
                    author_clean = author['name'].replace(' ', '').replace('　', '')
                    name_clean = author_name.replace(' ', '').replace('　', '')
                    if author_clean == name_clean and author.get('author_url'):
                        return author['author_url']
            
            # 既存データになければWebから取得
            print(f"🔍 {author_name}の青空文庫URL検索中...")
            authors = self.fetch_all_authors(update_database=False)
            
            for author in authors:
                if author.name == author_name and author.author_url:
                    return author.author_url
                    
                # 部分一致も試行
                author_clean = author.name.replace(' ', '').replace('　', '')
                name_clean = author_name.replace(' ', '').replace('　', '')
                if author_clean == name_clean and author.author_url:
                    return author.author_url
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 作者URL検索エラー: {e}")
            return None
    
    def update_single_author_url(self, author_name: str) -> bool:
        """単一作者の青空文庫URLをデータベースに更新"""
        try:
            # URLを検索
            author_url = self.find_author_url(author_name)
            
            if not author_url:
                print(f"❌ {author_name}の青空文庫URLが見つかりません")
                return False
            
            # データベース更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE authors SET aozora_author_url = ? WHERE author_name = ?',
                (author_url, author_name)
            )
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"✅ {author_name}の青空文庫URL更新: {author_url}")
                result = True
            else:
                print(f"❌ {author_name}がデータベースに見つかりません")
                result = False
            
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"❌ 単一作者URL更新エラー: {e}")
            return False

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='青空文庫作家リスト取得・データベース更新')
    parser.add_argument('--update-db', action='store_true', 
                        help='データベースの青空文庫URLを自動更新')
    parser.add_argument('--no-update-db', action='store_true', 
                        help='データベース更新をスキップ（JSONのみ保存）')
    parser.add_argument('--db-path', default='data/bungo_map.db', 
                        help='データベースファイルパス')
    parser.add_argument('--author', type=str, 
                        help='単一作者の青空文庫URL検索・更新')
    
    args = parser.parse_args()
    
    # スクレイパー初期化
    scraper = AuthorListScraper(rate_limit=1.0, db_path=args.db_path)
    
    # 単一作者モード
    if args.author:
        print(f"🔍 単一作者モード: {args.author}")
        print("=" * 60)
        
        success = scraper.update_single_author_url(args.author)
        if success:
            print(f"✅ {args.author}の青空文庫URL更新完了")
        else:
            print(f"❌ {args.author}の青空文庫URL更新失敗")
        return
    
    # データベース更新設定
    update_database = True  # デフォルト
    if args.no_update_db:
        update_database = False
    elif args.update_db:
        update_database = True
    
    print("🗾 青空文庫作家リスト取得開始")
    print("=" * 60)
    
    if update_database:
        print("📊 データベース更新: 有効")
    else:
        print("📊 データベース更新: 無効（JSONのみ保存）")
    
    # 全作家情報取得
    authors = scraper.fetch_all_authors(update_database=update_database)
    
    if authors:
        # 統計表示
        stats = scraper.get_statistics(authors)
        print(f"\n📊 取得統計")
        print(f"総作家数: {stats['total_authors']:,}名")
        print(f"総作品数: {stats['total_works']:,}作品")
        print(f"著作権存続: {stats['copyright_active']:,}名")
        print(f"著作権満了: {stats['copyright_expired']:,}名")
        print(f"平均作品数: {stats['average_works_per_author']}作品/作家")
        
        print(f"\n🏆 作品数上位10名:")
        for i, (name, count) in enumerate(stats['top_authors'], 1):
            print(f"  {i:2}. {name}: {count}作品")
        
        # JSON保存
        scraper.save_authors_to_json(authors)
        
        print(f"\n✅ 作家リスト取得完了")
    else:
        print(f"❌ 作家情報取得失敗")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 