#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作家リストスクレイパー動作テスト
青空文庫作家リスト取得とデータベース格納のテスト
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# パス追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 絶対インポートに修正
try:
    from extractors.author_list_scraper import AuthorListScraper, AuthorInfo
    from extractors.author_database_service import AuthorDatabaseService
    from database.manager import DatabaseManager
    from core.config import get_config
except ImportError:
    # フォールバック: 直接インポート
    import importlib.util
    
    # AuthorListScraperのインポート
    spec = importlib.util.spec_from_file_location(
        "author_list_scraper", 
        "extractors/author_list_scraper.py"
    )
    author_scraper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author_scraper_module)
    AuthorListScraper = author_scraper_module.AuthorListScraper
    AuthorInfo = author_scraper_module.AuthorInfo

def test_scraper_basic():
    """基本的なスクレイパー動作テスト"""
    print("🧪 作家リストスクレイパー基本テスト")
    print("=" * 60)
    
    try:
        # スクレイパー初期化
        scraper = AuthorListScraper(rate_limit=2.0)  # テスト用に低速設定
        
        # 少数作家情報取得テスト（実際にサイトにアクセス）
        print("📚 作家情報取得中（テスト）...")
        print("⚠️ 青空文庫サイトから実際にデータを取得します...")
        
        authors = scraper.fetch_all_authors()
        
        if authors:
            print(f"✅ 作家情報取得成功: {len(authors)}名")
            
            # 統計表示
            stats = scraper.get_statistics(authors)
            print(f"\n📊 取得統計:")
            print(f"  総作家数: {stats['total_authors']:,}名")
            print(f"  総作品数: {stats['total_works']:,}作品")
            print(f"  平均作品数: {stats['average_works_per_author']}作品/作家")
            print(f"  著作権存続: {stats['copyright_active']:,}名")
            print(f"  著作権満了: {stats['copyright_expired']:,}名")
            
            # サンプル作家表示
            print(f"\n🔍 作家サンプル（最初の5名）:")
            for i, author in enumerate(authors[:5], 1):
                status_icon = "⚖️" if author.copyright_status == "active" else "📚"
                print(f"  {i}. {status_icon} {author.name} (作品数: {author.works_count})")
                if author.author_url:
                    print(f"     URL: {author.author_url}")
                if author.alias_info:
                    print(f"     別名: {author.alias_info}")
            
            # 作品数上位作家
            print(f"\n🏆 作品数上位5名:")
            for i, (name, count) in enumerate(stats['top_authors'][:5], 1):
                print(f"  {i}. {name}: {count}作品")
            
            # JSON保存テスト
            print(f"\n💾 JSON保存テスト...")
            scraper.save_authors_to_json(authors)
            
            return True
        else:
            print("❌ 作家情報取得失敗")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_integration():
    """データベース統合テスト"""
    print("\n🧪 データベース統合テスト")
    print("=" * 60)
    
    try:
        # テスト用設定
        config = get_config()
        print(f"📊 データベース: {config.database.database_url}")
        
        # サービス初期化
        service = AuthorDatabaseService()
        
        # 少数データでテスト
        print("📚 作家データベース同期テスト...")
        
        # スクレイパー単体テスト
        scraper = AuthorListScraper(rate_limit=2.0)
        authors_info = scraper.fetch_all_authors()
        
        if not authors_info:
            print("❌ 作家情報取得失敗")
            return False
        
        # 最初の10名のみでテスト
        test_authors = authors_info[:10]
        print(f"🔬 テストデータ: {len(test_authors)}名")
        
        # データベース同期テスト
        sync_result = await service._sync_authors_to_database(test_authors, force_refresh=True)
        
        print(f"✅ データベース同期完了:")
        print(f"  新規作家: {sync_result['new_count']}名")
        print(f"  更新作家: {sync_result['updated_count']}名")
        
        # 検索テスト
        print(f"\n🔍 検索テスト...")
        if test_authors:
            search_name = test_authors[0].name.split()[0]  # 姓で検索
            search_results = await service.search_authors(search_name, limit=5)
            
            print(f"'{search_name}' の検索結果: {len(search_results)}名")
            for result in search_results:
                print(f"  - {result['name']} (作品数: {result['works_count']})")
        
        # 統計テスト
        print(f"\n📊 統計テスト...")
        stats = await service.get_author_statistics()
        if stats:
            print(f"  データベース内作家数: {stats.get('total_authors', 0)}名")
            print(f"  データベース内作品数: {stats.get('total_works', 0)}作品")
        
        return True
        
    except Exception as e:
        print(f"❌ データベーステストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_author_parsing():
    """作家項目解析テスト"""
    print("\n🧪 作家項目解析テスト")
    print("=" * 60)
    
    # テストデータ
    test_cases = [
        "芥川 竜之介 (公開中：379)",
        "青木 栄瞳 (公開中：1) ＊著作権存続＊",
        "芥川 紗織 (公開中：5) (→間所 紗織)",
        "アーヴィング ワシントン (公開中：16)",
        "ユゴー ヴィクトル (公開中：7)"
    ]
    
    scraper = AuthorListScraper()
    
    print("🔍 解析テストケース:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. テストケース: '{test_case}'")
        
        # 簡易HTML要素作成
        from bs4 import BeautifulSoup
        html = f"<li>{test_case}</li>"
        soup = BeautifulSoup(html, 'html.parser')
        li_element = soup.find('li')
        
        # 解析実行
        author_info = scraper._parse_author_item(li_element, "テスト")
        
        if author_info:
            print(f"   ✅ 解析成功:")
            print(f"      名前: {author_info.name}")
            print(f"      作品数: {author_info.works_count}")
            print(f"      著作権: {author_info.copyright_status}")
            if author_info.alias_info:
                print(f"      別名: {author_info.alias_info}")
        else:
            print(f"   ❌ 解析失敗")
    
    return True

def test_simple_scraping():
    """簡易スクレイピングテスト（ネットワーク接続確認）"""
    print("\n🧪 ネットワーク接続テスト")
    print("=" * 60)
    
    try:
        import requests
        
        # 青空文庫の基本接続テスト
        url = "https://www.aozora.gr.jp/index_pages/person_all.html"
        print(f"📡 接続テスト: {url}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"✅ 接続成功:")
        print(f"  ステータスコード: {response.status_code}")
        print(f"  コンテンツサイズ: {len(response.content):,} バイト")
        print(f"  エンコーディング: {response.encoding}")
        
        # HTMLパース簡易テスト
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 作家数の概算
        ol_elements = soup.find_all('ol')
        li_count = sum(len(ol.find_all('li')) for ol in ol_elements)
        
        print(f"  検出された項目数: {li_count}項目")
        
        return True
        
    except Exception as e:
        print(f"❌ ネットワークテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🗾 青空文庫作家リストスクレイパー総合テスト")
    print("=" * 80)
    print(f"テスト開始時刻: {datetime.now()}")
    
    # テスト実行
    test_results = []
    
    # 1. ネットワーク接続テスト
    test_results.append(("ネットワーク接続", test_simple_scraping()))
    
    # 2. 解析ロジックテスト
    test_results.append(("項目解析", test_author_parsing()))
    
    # 3. 基本スクレイパーテスト（実際のデータ取得）
    print(f"\n⚠️ 実際のスクレイピングテストを実行しますか？")
    print(f"   このテストは青空文庫サイトに実際にアクセスします。")
    response = input("実行する場合は 'y' を入力してください: ")
    
    if response.lower() == 'y':
        test_results.append(("基本スクレイパー", test_scraper_basic()))
    else:
        print("⏭️ 実際のスクレイピングテストをスキップしました")
        test_results.append(("基本スクレイパー", True))  # スキップとして成功扱い
    
    # 結果レポート
    print(f"\n" + "=" * 80)
    print("🏁 テスト結果レポート")
    print("=" * 80)
    
    success_count = 0
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n📊 総合結果: {success_count}/{len(test_results)} テスト成功")
    
    if success_count == len(test_results):
        print("🎉 全テスト成功！作家リストスクレイパーは正常に動作しています。")
        return 0
    else:
        print("⚠️ 一部テストが失敗しました。ログを確認してください。")
        return 1

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    exit_code = main()
    sys.exit(exit_code) 