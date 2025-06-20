#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikipedia作者情報自動補完システム v4.0
既存の作者データベースの生年・没年等を自動補完
"""

import re
import requests
import wikipedia
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import sys
import os

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.manager import DatabaseManager


class WikipediaAuthorEnricher:
    """Wikipedia から作者情報を取得してデータベースを補完"""
    
    def __init__(self):
        # Wikipedia言語設定
        wikipedia.set_lang("ja")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BungoMapBot/4.0 (bungo-map@example.com)'
        })
        
        # データベース接続
        self.db = DatabaseManager()
        
        # 統計情報
        self.stats = {
            'total_authors': 0,
            'success_count': 0,
            'failure_count': 0,
            'birth_year_updated': 0,
            'death_year_updated': 0,
            'wikipedia_url_updated': 0,
            'processing_time': 0.0
        }
        
    def search_author_wikipedia(self, author_name: str) -> Optional[Dict]:
        """作者のWikipedia情報を詳細検索"""
        try:
            print(f"🔍 {author_name} の情報を検索中...")
            
            # Wikipedia検索
            page = wikipedia.page(author_name)
            
            # 基本情報抽出
            extract = page.summary
            birth_year, death_year = self._extract_life_years(extract, page.content)
            
            return {
                'title': page.title,
                'url': page.url,
                'extract': extract[:500],  # 要約（500文字）
                'content': page.content,
                'birth_year': birth_year,
                'death_year': death_year
            }
            
        except wikipedia.exceptions.DisambiguationError as e:
            # 曖昧さ回避ページの場合、最初の候補を試す
            try:
                page = wikipedia.page(e.options[0])
                extract = page.summary
                birth_year, death_year = self._extract_life_years(extract, page.content)
                
                return {
                    'title': page.title,
                    'url': page.url,
                    'extract': extract[:500],
                    'content': page.content,
                    'birth_year': birth_year,
                    'death_year': death_year
                }
            except Exception as e2:
                print(f"⚠️ 曖昧さ回避エラー ({author_name}): {e2}")
                
        except wikipedia.exceptions.PageError:
            print(f"⚠️ ページが見つかりません: {author_name}")
            
        except Exception as e:
            print(f"⚠️ Wikipedia検索エラー ({author_name}): {e}")
            
        return None
    
    def _extract_life_years(self, summary: str, content: str) -> Tuple[Optional[int], Optional[int]]:
        """テキストから生年・没年を抽出（改良版）"""
        # より多様なパターンに対応
        text = summary + " " + content[:2000]  # 最初の部分のみ使用
        
        # (年号 - 年号) パターンを最優先で探す
        life_span_patterns = [
            r'、(\d{4})年〈.*?〉.*?-.*?(\d{4})年〈.*?〉',  # 、1909年〈明治42年〉6月19日 - 1948年〈昭和23年〉 形式
            r'（(\d{4})年.*?-.*?(\d{4})年.*?）',
            r'(\d{4})年.*?-.*?(\d{4})年',
        ]
        
        for pattern in life_span_patterns:
            life_match = re.search(pattern, text)
            if life_match:
                birth_year = int(life_match.group(1))
                death_year = int(life_match.group(2))
                return birth_year, death_year
        
        # 個別パターンで探す
        birth_patterns = [
            r'（(\d{4})年.*?月.*?日.*?-',  # (1901年2月17日 - 形式
            r'（(\d{4})年.*?-',  # (1901年 - 形式
            r'(\d{4})年.*?月.*?日.*?生',
            r'(\d{4})年.*?生まれ',
            r'生年.*?(\d{4})年',
            r'(\d{4})年.*?誕生',
            r'明治(\d+)年.*?生',  # 明治年号
            r'大正(\d+)年.*?生',  # 大正年号
            r'昭和(\d+)年.*?生',  # 昭和年号
        ]
        
        death_patterns = [
            r'-.*?(\d{4})年.*?月.*?日.*?）',  # - 1932年3月24日） 形式
            r'-.*?(\d{4})年.*?）',  # - 1932年） 形式
            r'(\d{4})年.*?月.*?日.*?没',
            r'(\d{4})年.*?死去',
            r'没年.*?(\d{4})年',
            r'(\d{4})年.*?逝去',
            r'昭和(\d+)年.*?没',  # 昭和年号
            r'大正(\d+)年.*?没',  # 大正年号
            r'明治(\d+)年.*?没',  # 明治年号
        ]
        
        birth_year = self._extract_year_from_patterns(text, birth_patterns)
        death_year = self._extract_year_from_patterns(text, death_patterns)
        
        return birth_year, death_year
    
    def _extract_year_from_patterns(self, text: str, patterns: List[str]) -> Optional[int]:
        """パターンリストから年を抽出"""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    year_str = match.group(1)
                    year = int(year_str)
                    
                    # 年号変換（簡易版）
                    if '明治' in pattern:
                        year = 1867 + year
                    elif '大正' in pattern:
                        year = 1911 + year
                    elif '昭和' in pattern:
                        year = 1925 + year
                    
                    # 妥当な年の範囲チェック
                    if 1800 <= year <= 2100:
                        return year
                except (ValueError, IndexError):
                    continue
        return None
    
    def enrich_author_info(self, author_id: int, author_name: str) -> bool:
        """指定作者の情報をWikipediaから補完"""
        print(f"\n📝 {author_name} (ID: {author_id}) の情報を補完中...")
        
        # Wikipedia情報取得
        wiki_info = self.search_author_wikipedia(author_name)
        
        if not wiki_info:
            print(f"❌ {author_name} のWikipedia情報を取得できませんでした")
            self.stats['failure_count'] += 1
            return False
        
        # データベース更新
        update_fields = {}
        updates_made = []
        
        # 生年更新
        if wiki_info['birth_year']:
            update_fields['birth_year'] = wiki_info['birth_year']
            updates_made.append(f"生年: {wiki_info['birth_year']}年")
            self.stats['birth_year_updated'] += 1
        
        # 没年更新
        if wiki_info['death_year']:
            update_fields['death_year'] = wiki_info['death_year']
            updates_made.append(f"没年: {wiki_info['death_year']}年")
            self.stats['death_year_updated'] += 1
        
        # Wikipedia URL更新
        if wiki_info['url']:
            update_fields['wikipedia_url'] = wiki_info['url']
            updates_made.append(f"Wikipedia URL")
            self.stats['wikipedia_url_updated'] += 1
        
        if update_fields:
            try:
                # authors テーブル更新クエリ構築
                set_clause = ', '.join([f"{field} = ?" for field in update_fields.keys()])
                values = list(update_fields.values()) + [author_id]
                
                query = f"""
                UPDATE authors 
                SET {set_clause}
                WHERE author_id = ?
                """
                
                with self.db.get_connection() as conn:
                    cursor = conn.execute(query, values)
                    conn.commit()
                
                print(f"✅ {author_name} の情報を更新: {', '.join(updates_made)}")
                self.stats['success_count'] += 1
                return True
                
            except Exception as e:
                print(f"❌ データベース更新エラー ({author_name}): {e}")
                self.stats['failure_count'] += 1
                return False
        else:
            print(f"⚠️ {author_name} の追加情報が見つかりませんでした")
            self.stats['failure_count'] += 1
            return False
    
    def enrich_all_authors(self) -> Dict:
        """全作者の情報を一括補完"""
        print("🌟 全作者情報の一括補完を開始します...")
        start_time = time.time()
        
        try:
            # 全作者取得
            with self.db.get_connection() as conn:
                cursor = conn.execute("SELECT author_id, author_name FROM authors ORDER BY author_name")
                authors = cursor.fetchall()
            
            if not authors:
                print("❌ 作者データが見つかりません")
                return self.stats
            
            self.stats['total_authors'] = len(authors)
            print(f"📊 処理対象: {len(authors)} 人の作者")
            
            # 各作者について処理
            for i, (author_id, author_name) in enumerate(authors, 1):
                print(f"\n🔄 [{i}/{len(authors)}] 処理中...")
                
                # Wikipedia情報で補完
                self.enrich_author_info(author_id, author_name)
                
                # API制限対策（1秒間隔）
                time.sleep(1.0)
            
            # 統計情報更新
            self.stats['processing_time'] = time.time() - start_time
            
            return self.stats
            
        except Exception as e:
            print(f"❌ データベースエラー: {e}")
            self.stats['processing_time'] = time.time() - start_time
            return self.stats
    
    def enrich_specific_authors(self, author_names: List[str]) -> Dict:
        """指定した作者のみ情報補完"""
        print(f"🎯 指定作者の情報補完を開始: {', '.join(author_names)}")
        start_time = time.time()
        
        for author_name in author_names:
            try:
                # 作者ID取得
                with self.db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT author_id, author_name FROM authors WHERE author_name = ?", 
                        (author_name,)
                    )
                    author_data = cursor.fetchone()
                
                if not author_data:
                    print(f"❌ 作者 '{author_name}' が見つかりません")
                    self.stats['failure_count'] += 1
                    continue
                
                author_id, db_author_name = author_data
                self.stats['total_authors'] += 1
                
                # Wikipedia情報で補完
                self.enrich_author_info(author_id, db_author_name)
                
                # API制限対策
                time.sleep(1.0)
                
            except Exception as e:
                print(f"❌ 作者 '{author_name}' の処理でエラー: {e}")
                self.stats['failure_count'] += 1
        
        # 統計情報更新
        self.stats['processing_time'] = time.time() - start_time
        
        return self.stats
    
    def print_statistics(self):
        """処理統計を表示"""
        print("\n" + "="*60)
        print("📊 Wikipedia作者情報補完 - 処理結果")
        print("="*60)
        print(f"処理対象作者数: {self.stats['total_authors']} 人")
        print(f"成功: {self.stats['success_count']} 人")
        print(f"失敗: {self.stats['failure_count']} 人")
        print(f"成功率: {self.stats['success_count']/max(1, self.stats['total_authors'])*100:.1f}%")
        print("-"*60)
        print(f"生年補完: {self.stats['birth_year_updated']} 件")
        print(f"没年補完: {self.stats['death_year_updated']} 件")
        print(f"Wikipedia URL補完: {self.stats['wikipedia_url_updated']} 件")
        print(f"処理時間: {self.stats['processing_time']:.1f} 秒")
        print("="*60)
    
    def preview_missing_info(self) -> Dict:
        """不足している作者情報をプレビュー"""
        print("🔍 不足している作者情報を確認中...")
        
        query = """
        SELECT 
            author_id, 
            author_name,
            birth_year as author_birth_year,
            death_year as author_death_year,
            wikipedia_url
        FROM authors 
        WHERE birth_year IS NULL 
           OR death_year IS NULL 
           OR wikipedia_url IS NULL
        ORDER BY author_name
        """
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(query)
                missing_info_authors = cursor.fetchall()
            
            if not missing_info_authors:
                print("✅ 全ての作者情報が完全です！")
                return {'missing_count': 0, 'authors': []}
            
            print(f"📋 情報不足の作者: {len(missing_info_authors)} 人")
            print("-"*80)
            print(f"{'ID':<4} {'作者名':<20} {'生年':<8} {'没年':<8} {'Wikipedia':<10}")
            print("-"*80)
            
            for author_id, name, birth, death, wiki_url in missing_info_authors:
                birth_str = str(birth) if birth else "なし"
                death_str = str(death) if death else "なし"
                wiki_str = "あり" if wiki_url else "なし"
                print(f"{author_id:<4} {name:<20} {birth_str:<8} {death_str:<8} {wiki_str:<10}")
            
            return {
                'missing_count': len(missing_info_authors),
                'authors': missing_info_authors
            }
            
        except Exception as e:
            print(f"❌ データベースエラー: {e}")
            return {'missing_count': 0, 'authors': []}
    
    def close(self):
        """リソース解放"""
        # DatabaseManagerには明示的なcloseメソッドがないため、パス
        pass


def main():
    """メイン実行関数"""
    enricher = WikipediaAuthorEnricher()
    
    try:
        # 不足情報のプレビュー
        missing_info = enricher.preview_missing_info()
        
        if missing_info['missing_count'] == 0:
            print("✅ 処理は不要です")
            return
        
        # ユーザー確認
        print(f"\n🤔 {missing_info['missing_count']} 人の作者情報を補完しますか？")
        print("この処理には時間がかかる場合があります。")
        
        response = input("実行しますか？ (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            # 全作者の情報補完実行
            stats = enricher.enrich_all_authors()
            enricher.print_statistics()
        else:
            print("❌ 処理をキャンセルしました")
            
    except KeyboardInterrupt:
        print("\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
    finally:
        enricher.close()


if __name__ == "__main__":
    main() 