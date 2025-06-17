#!/usr/bin/env python3
"""
青空文庫作家情報のデータベース統合テストファイル

このスクリプトは以下の機能をテストします：
1. 作家情報のスクレイピング
2. データベースへの格納
3. データの検索と統計
4. CRUD操作
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.author_list_scraper import AuthorListScraper
from database.models import Author, Work, Base
from database.config import SessionLocal, engine, init_db
from database.crud import AuthorCRUD
from sqlalchemy.orm import Session

class AuthorDatabaseIntegrationTest:
    """作家情報データベース統合テストクラス"""
    
    def __init__(self):
        self.scraper = AuthorListScraper()
        self.db_session = None
        self.author_crud = None
    
    def _fetch_limited_authors(self, max_authors: int):
        """テスト用：限定数の作家情報を取得"""
        try:
            # 全取得してから限定
            all_authors = self.scraper.fetch_all_authors()
            return all_authors[:max_authors] if all_authors else []
        except Exception as e:
            print(f"限定取得エラー: {e}")
            return []
        
    def setup_database(self) -> bool:
        """データベースのセットアップ"""
        try:
            print("📊 データベースのセットアップを開始...")
            init_db()
            
            self.db_session = SessionLocal()
            self.author_crud = AuthorCRUD(self.db_session)
            
            print("✅ データベースのセットアップが完了しました")
            return True
            
        except Exception as e:
            print(f"❌ データベースセットアップエラー: {e}")
            return False
    
    def test_scrape_authors(self) -> list:
        """作家情報のスクレイピングテスト"""
        try:
            print("\n📚 青空文庫作家一覧の取得を開始...")
            
            # 限定数でテスト（フル実行は時間がかかるため）
            test_mode = True
            max_authors = 50 if test_mode else None
            
            # 限定取得の場合は実装を変更
            if test_mode:
                # テスト用：限定数取得（手動実装）
                authors = self._fetch_limited_authors(max_authors)
            else:
                authors = self.scraper.fetch_all_authors()
            
            if not authors:
                print("❌ 作家情報の取得に失敗しました")
                return []
            
            print(f"✅ {len(authors)}名の作家情報を取得しました")
            
            # サンプル情報表示
            if authors:
                sample = authors[0]
                print(f"📖 サンプル作家: {sample.name} ({sample.section})")
                print(f"   作品数: {sample.works_count}")
                print(f"   著作権: {sample.copyright_status}")
                
            return authors
            
        except Exception as e:
            print(f"❌ スクレイピングエラー: {e}")
            return []
    
    def test_save_authors_to_database(self, authors: list) -> bool:
        """作家情報のデータベース保存テスト"""
        try:
            print(f"\n💾 {len(authors)}名の作家情報をデータベースに保存中...")
            
            saved_count = 0
            error_count = 0
            
            for author_info in authors:
                try:
                    # Author モデルインスタンス作成
                    author_data = {
                        'author_name': author_info.name,
                        'aozora_author_url': author_info.author_url,
                        'copyright_status': author_info.copyright_status,
                        'aozora_works_count': author_info.works_count,
                        'section': author_info.section,
                        'source_system': 'aozora_scraper_v1.0',
                        'verification_status': 'auto_scraped'
                    }
                    
                    # データベースに保存
                    saved_author = self.author_crud.create_author(author_data)
                    if saved_author:
                        saved_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    print(f"⚠️  作家保存エラー ({author_info.name}): {e}")
                    error_count += 1
            
            print(f"✅ データベース保存完了:")
            print(f"   保存成功: {saved_count}名")
            print(f"   エラー: {error_count}名")
            
            return saved_count > 0
            
        except Exception as e:
            print(f"❌ データベース保存エラー: {e}")
            return False
    
    def test_database_operations(self) -> bool:
        """データベース操作テスト"""
        try:
            print("\n🔍 データベース操作のテスト...")
            
            # 総数確認
            total_authors = self.author_crud.get_total_authors()
            print(f"📊 総作家数: {total_authors}名")
            
            # 著作権別統計
            copyright_stats = self.author_crud.get_copyright_statistics()
            print(f"📈 著作権統計: {copyright_stats}")
            
            # セクション別統計
            section_stats = self.author_crud.get_section_statistics()
            print(f"📚 セクション別統計: {dict(list(section_stats.items())[:5])}...")
            
            # 作品数上位作家
            top_authors = self.author_crud.get_top_authors_by_works(limit=5)
            print("🏆 作品数上位作家:")
            for i, author in enumerate(top_authors, 1):
                print(f"   {i}. {author.author_name}: {author.aozora_works_count}作品")
            
            # 検索テスト
            search_results = self.author_crud.search_authors("夏目", limit=3)
            print(f"🔎 '夏目'検索結果: {len(search_results)}件")
            for author in search_results:
                print(f"   - {author.author_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ データベース操作エラー: {e}")
            return False
    
    def test_data_export(self) -> bool:
        """データエクスポートテスト"""
        try:
            print("\n📤 データエクスポートテスト...")
            
            # 全作家データ取得
            all_authors = self.author_crud.get_all_authors()
            
            export_data = []
            for author in all_authors:
                export_data.append({
                    'author_id': author.author_id,
                    'author_name': author.author_name,
                    'aozora_author_url': author.aozora_author_url,
                    'copyright_status': author.copyright_status,
                    'aozora_works_count': author.aozora_works_count,
                    'section': author.section,
                    'created_at': author.created_at.isoformat() if author.created_at else None
                })
            
            # JSONファイルに保存
            export_file = Path("data/database_authors_export.json")
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {len(export_data)}名の作家データを {export_file} にエクスポートしました")
            return True
            
        except Exception as e:
            print(f"❌ データエクスポートエラー: {e}")
            return False
    
    def run_full_integration_test(self):
        """フル統合テストの実行"""
        print("🚀 青空文庫作家情報データベース統合テスト開始")
        print("=" * 60)
        
        test_results = []
        
        # 1. データベースセットアップ
        result = self.setup_database()
        test_results.append(("データベースセットアップ", result))
        if not result:
            return self.print_final_results(test_results)
        
        # 2. 作家情報スクレイピング
        authors = self.test_scrape_authors()
        result = len(authors) > 0
        test_results.append(("作家情報スクレイピング", result))
        if not result:
            return self.print_final_results(test_results)
        
        # 3. データベース保存
        result = self.test_save_authors_to_database(authors)
        test_results.append(("データベース保存", result))
        if not result:
            return self.print_final_results(test_results)
        
        # 4. データベース操作
        result = self.test_database_operations()
        test_results.append(("データベース操作", result))
        
        # 5. データエクスポート
        result = self.test_data_export()
        test_results.append(("データエクスポート", result))
        
        # 最終結果表示
        self.print_final_results(test_results)
        
        # クリーンアップ
        if self.db_session:
            self.db_session.close()
    
    def print_final_results(self, test_results: list):
        """最終結果の表示"""
        print("\n" + "=" * 60)
        print("📋 テスト結果サマリー")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n📊 結果: {passed}件成功, {failed}件失敗")
        
        if failed == 0:
            print("🎉 全てのテストが成功しました！")
        else:
            print("⚠️  一部のテストが失敗しました。")

def main():
    """メイン実行関数"""
    tester = AuthorDatabaseIntegrationTest()
    tester.run_full_integration_test()

if __name__ == "__main__":
    main() 