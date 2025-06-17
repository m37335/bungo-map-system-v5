#!/usr/bin/env python3
"""
URL修正テストスクリプト

青空文庫作家URLの形式が正しく修正されているかテストします
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.author_list_scraper import AuthorListScraper

def test_url_fix():
    """URL修正テスト"""
    print("🔗 青空文庫作家URL修正テスト開始")
    print("=" * 50)
    
    try:
        # スクレイパー初期化
        scraper = AuthorListScraper(rate_limit=0.5)
        
        # 少数の作家情報を取得してテスト
        print("📚 作家情報を取得中（最初の20名でテスト）...")
        authors = scraper.fetch_all_authors()
        
        if not authors:
            print("❌ 作家情報の取得に失敗しました")
            return
        
        # 最初の20名をテスト
        test_authors = authors[:20]
        print(f"✅ {len(test_authors)}名をテスト")
        
        print("\n🔍 URL検証結果:")
        print("-" * 80)
        
        correct_urls = 0
        incorrect_urls = 0
        
        for i, author in enumerate(test_authors, 1):
            url = author.author_url
            
            # 正しいURL形式かチェック
            expected_pattern = "https://www.aozora.gr.jp/index_pages/person"
            if url and expected_pattern in url:
                status = "✅"
                correct_urls += 1
            else:
                status = "❌"
                incorrect_urls += 1
            
            print(f"{i:2}. {status} {author.name}")
            print(f"    URL: {url}")
            
            # 梶井基次郎を特に確認
            if "梶井" in author.name:
                print(f"    🎯 梶井基次郎のURL確認:")
                expected_kajii_url = "https://www.aozora.gr.jp/index_pages/person74.html"
                if url == expected_kajii_url:
                    print(f"    ✅ 正しいURL: {url}")
                else:
                    print(f"    ❌ 期待値: {expected_kajii_url}")
                    print(f"    ❌ 実際値: {url}")
        
        print("\n" + "=" * 50)
        print("📊 URL検証サマリー")
        print("=" * 50)
        print(f"正しいURL: {correct_urls}件")
        print(f"間違ったURL: {incorrect_urls}件")
        print(f"成功率: {correct_urls/(correct_urls+incorrect_urls)*100:.1f}%")
        
        if incorrect_urls == 0:
            print("🎉 全てのURLが正しい形式です！")
        else:
            print("⚠️  いくつかのURLに問題があります。")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_url_fix() 