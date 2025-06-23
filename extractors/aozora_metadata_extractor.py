#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青空文庫メタデータ自動抽出システム v4.0
作品の出版年、カードID等を自動補完
"""

import re
import requests
import time
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import sys
import os

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.manager import DatabaseManager


class AozoraMetadataExtractor:
    """青空文庫からメタデータを自動抽出してデータベースを補完"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BungoMapBot/4.0 (bungo-map@example.com)'
        })
        
        # 統計情報
        self.stats = {
            'total_works': 0,
            'success_count': 0,
            'failure_count': 0,
            'publication_year_updated': 0,
            'card_id_updated': 0,
            'aozora_work_id_updated': 0,
            'processing_time': 0
        }
    
    def extract_metadata_from_url(self, aozora_url: str) -> Dict:
        """青空文庫URLからメタデータを抽出"""
        try:
            print(f"🔍 {aozora_url} からメタデータ抽出中...")
            
            # ページ取得
            response = self.session.get(aozora_url, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            metadata = {}
            
            # 1. URL解析でcard_idとaozora_work_idを抽出
            url_match = re.search(r'/cards/(\d+)/card(\d+)\.html', aozora_url)
            if url_match:
                metadata['aozora_work_id'] = url_match.group(1)
                metadata['card_id'] = url_match.group(2)
            
            # 2. 作品データテーブルから初出年を抽出
            metadata['publication_year'] = self._extract_publication_year(soup)
            
            # 3. その他メタデータ
            metadata['copyright_status'] = "パブリックドメイン"
            metadata['input_person'] = self._extract_input_person(soup)
            metadata['proof_person'] = self._extract_proof_person(soup)
            
            return metadata
            
        except Exception as e:
            print(f"❌ メタデータ抽出エラー ({aozora_url}): {e}")
            return {}
    
    def _extract_publication_year(self, soup: BeautifulSoup) -> Optional[int]:
        """初出年を抽出（改良版：複数パターン対応）"""
        try:
            # 作品データテーブルを探す
            tables = soup.find_all('table', {'summary': '作品データ'})
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        header = cells[0].get_text(strip=True)
                        content = cells[1].get_text(strip=True)
                        
                        # 複数の年情報パターンを試行
                        if any(keyword in header for keyword in ['初出', '発表', '発行', '出版']):
                            year = self._extract_year_from_text(content)
                            if year:
                                print(f"✅ {header}から年抽出: {year}年 ({content[:50]}...)")
                                return year
            
            # 作品データテーブルが見つからない場合、ページ全体から抽出
            print("⚠️ 作品データテーブルが見つかりません。ページ全体を検索...")
            page_text = soup.get_text()
            year = self._extract_year_from_text(page_text[:1000])  # 最初の1000文字のみ
            if year:
                print(f"✅ ページ全体から年抽出: {year}年")
                return year
            
            return None
            
        except Exception as e:
            print(f"⚠️ 初出年抽出エラー: {e}")
            return None
    
    def _extract_year_from_text(self, text: str) -> Optional[int]:
        """テキストから年を抽出（改良版：多様なパターン対応）"""
        # パターン1: 西暦年（1900-2100）
        year_patterns = [
            r'(\d{4})年',  # 1930年
            r'(\d{4})（.*?）年',  # 1930（昭和5）年
            r'「.*?」(\d{4})年',  # 「雑誌名」1930年
            r'『.*?』(\d{4})年',  # 『雑誌名』1930年
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    year = int(match)
                    if 1800 <= year <= 2100:  # 妥当な年の範囲
                        return year
                except ValueError:
                    continue
        
        # パターン2: 年号変換
        era_patterns = [
            (r'明治(\d+)年', 1867),  # 明治元年=1868年
            (r'大正(\d+)年', 1911),  # 大正元年=1912年
            (r'昭和(\d+)年', 1925),  # 昭和元年=1926年
        ]
        
        for pattern, base_year in era_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    era_year = int(match)
                    if era_year > 0:  # 0年は無効
                        year = base_year + era_year
                        if 1800 <= year <= 2100:
                            return year
                except ValueError:
                    continue
        
        return None
    
    def _extract_input_person(self, soup: BeautifulSoup) -> Optional[str]:
        """入力者を抽出"""
        try:
            tables = soup.find_all('table', {'summary': '工作員データ'})
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        header = cells[0].get_text(strip=True)
                        content = cells[1].get_text(strip=True)
                        
                        if '入力' in header:
                            return content
            
            return None
            
        except Exception as e:
            print(f"⚠️ 入力者抽出エラー: {e}")
            return None
    
    def _extract_proof_person(self, soup: BeautifulSoup) -> Optional[str]:
        """校正者を抽出"""
        try:
            tables = soup.find_all('table', {'summary': '工作員データ'})
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        header = cells[0].get_text(strip=True)
                        content = cells[1].get_text(strip=True)
                        
                        if '校正' in header:
                            return content
            
            return None
            
        except Exception as e:
            print(f"⚠️ 校正者抽出エラー: {e}")
            return None
    
    def update_work_metadata(self, work_id: int, work_title: str, aozora_url: str):
        """作品メタデータを更新"""
        try:
            print(f"\n📝 作品 '{work_title}' (ID: {work_id}) のメタデータ更新中...")
            
            # メタデータ抽出
            metadata = self.extract_metadata_from_url(aozora_url)
            
            if not metadata:
                print(f"❌ メタデータの抽出に失敗しました")
                self.stats['failure_count'] += 1
                return False
            
            # データベース更新
            update_fields = {}
            updates_made = []
            
            if metadata.get('publication_year'):
                update_fields['publication_year'] = metadata['publication_year']
                updates_made.append(f"出版年: {metadata['publication_year']}年")
                self.stats['publication_year_updated'] += 1
            
            if metadata.get('card_id'):
                update_fields['card_id'] = metadata['card_id']
                updates_made.append(f"カードID: {metadata['card_id']}")
                self.stats['card_id_updated'] += 1
            
            if metadata.get('aozora_work_id'):
                update_fields['aozora_work_id'] = metadata['aozora_work_id']
                updates_made.append(f"作品ID: {metadata['aozora_work_id']}")
                self.stats['aozora_work_id_updated'] += 1
            
            if metadata.get('copyright_status'):
                update_fields['copyright_status'] = metadata['copyright_status']
                updates_made.append(f"著作権: {metadata['copyright_status']}")
            
            if metadata.get('input_person'):
                update_fields['input_person'] = metadata['input_person']
                updates_made.append(f"入力者: {metadata['input_person']}")
            
            if metadata.get('proof_person'):
                update_fields['proof_person'] = metadata['proof_person']
                updates_made.append(f"校正者: {metadata['proof_person']}")
            
            if update_fields:
                # データベース更新
                set_clause = ', '.join([f"{field} = ?" for field in update_fields.keys()])
                values = list(update_fields.values()) + [work_id]
                
                query = f"""
                UPDATE works 
                SET {set_clause}
                WHERE work_id = ?
                """
                
                with self.db.get_connection() as conn:
                    cursor = conn.execute(query, values)
                    conn.commit()
                
                print(f"✅ {work_title} の情報を更新: {', '.join(updates_made)}")
                self.stats['success_count'] += 1
                return True
            else:
                print(f"⚠️ {work_title}: 更新可能な情報が見つかりませんでした")
                self.stats['failure_count'] += 1
                return False
                
        except Exception as e:
            print(f"❌ データベース更新エラー ({work_title}): {e}")
            self.stats['failure_count'] += 1
            return False
    
    def enrich_all_works(self) -> Dict:
        """全作品のメタデータを一括補完"""
        print("🌟 全作品メタデータの一括補完を開始します...")
        start_time = time.time()
        
        try:
            # 全作品取得
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT work_id, work_title, aozora_url 
                    FROM works 
                    WHERE aozora_url IS NOT NULL 
                    ORDER BY work_id
                """)
                works = cursor.fetchall()
            
            if not works:
                print("❌ 作品データが見つかりません")
                return self.stats
            
            self.stats['total_works'] = len(works)
            print(f"📊 処理対象: {len(works)} 件の作品")
            
            # 各作品について処理
            for i, (work_id, work_title, aozora_url) in enumerate(works, 1):
                print(f"\n🔄 [{i}/{len(works)}] 処理中...")
                
                # メタデータ更新
                self.update_work_metadata(work_id, work_title, aozora_url)
                
                # API制限対策（1秒間隔）
                time.sleep(1.0)
            
            # 統計情報更新
            self.stats['processing_time'] = time.time() - start_time
            
            return self.stats
            
        except Exception as e:
            print(f"❌ データベースエラー: {e}")
            self.stats['processing_time'] = time.time() - start_time
            return self.stats
    
    def preview_missing_metadata(self) -> Dict:
        """不足しているメタデータをプレビュー"""
        print("🔍 不足している作品メタデータを確認中...")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        work_id, 
                        work_title,
                        publication_year,
                        card_id,
                        aozora_work_id
                    FROM works 
                    WHERE publication_year IS NULL 
                       OR card_id IS NULL 
                       OR aozora_work_id IS NULL 
                    ORDER BY work_id
                """)
                missing_works = cursor.fetchall()
            
            if not missing_works:
                print("✅ 全ての作品メタデータが完全です！")
                return {'missing_count': 0, 'works': []}
            
            print(f"📋 メタデータ不足の作品: {len(missing_works)} 件")
            print("-"*80)
            print(f"{'ID':<4} {'作品名':<30} {'出版年':<8} {'カードID':<10} {'作品ID':<8}")
            print("-"*80)
            
            for work_id, title, pub_year, card_id, work_id_val in missing_works:
                pub_str = str(pub_year) if pub_year else "なし"
                card_str = str(card_id) if card_id else "なし"
                work_id_str = str(work_id_val) if work_id_val else "なし"
                title_truncated = title[:28] + ".." if len(title) > 30 else title
                print(f"{work_id:<4} {title_truncated:<30} {pub_str:<8} {card_str:<10} {work_id_str:<8}")
            
            return {
                'missing_count': len(missing_works),
                'works': missing_works
            }
            
        except Exception as e:
            print(f"❌ データベースエラー: {e}")
            return {'missing_count': 0, 'works': []}
    
    def print_statistics(self):
        """統計情報を表示"""
        print("="*60)
        print("📊 青空文庫メタデータ補完 - 処理結果")
        print("="*60)
        print(f"処理対象作品数: {self.stats['total_works']} 件")
        print(f"成功: {self.stats['success_count']} 件")
        print(f"失敗: {self.stats['failure_count']} 件")
        
        if self.stats['total_works'] > 0:
            success_rate = (self.stats['success_count'] / self.stats['total_works']) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        print("-"*60)
        print(f"出版年補完: {self.stats['publication_year_updated']} 件")
        print(f"カードID補完: {self.stats['card_id_updated']} 件")
        print(f"作品ID補完: {self.stats['aozora_work_id_updated']} 件")
        print(f"処理時間: {self.stats['processing_time']:.1f} 秒")
        print("="*60)


if __name__ == "__main__":
    # テスト実行
    extractor = AozoraMetadataExtractor()
    
    try:
        # プレビュー表示
        extractor.preview_missing_metadata()
        
        # テスト実行（最初の1件のみ）
        print("\n🧪 テスト実行（最初の1件）...")
        extractor.update_work_metadata(1, "テスト作品", "https://www.aozora.gr.jp/cards/000074/card411.html")
        
        # 統計表示
        extractor.print_statistics()
        
    except KeyboardInterrupt:
        print("\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}") 