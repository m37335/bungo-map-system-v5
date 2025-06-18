#!/usr/bin/env python3
"""
梶井基次郎のURL確認スクリプト
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.author_list_scraper import AuthorListScraper

def main():
    print("🔍 梶井基次郎のURL確認")
    print("=" * 40)
    
    try:
        scraper = AuthorListScraper(rate_limit=0.3)
        print("📚 作家情報取得中...")
        authors = scraper.fetch_all_authors()
        
        # 梶井基次郎を検索
        kajii_authors = [a for a in authors if '梶井' in a.name and '基次郎' in a.name]
        
        if kajii_authors:
            kajii = kajii_authors[0]
            print(f"✅ 梶井基次郎を発見")
            print(f"作家名: {kajii.name}")
            print(f"取得URL: {kajii.author_url}")
            print(f"期待URL: https://www.aozora.gr.jp/index_pages/person74.html")
            
            if kajii.author_url == "https://www.aozora.gr.jp/index_pages/person74.html":
                print("🎉 URLが正しく修正されています！")
                print("作品数:", kajii.works_count)
                print("著作権:", kajii.copyright_status)
            else:
                print("❌ URLが期待値と異なります")
        else:
            print("❌ 梶井基次郎が見つかりませんでした")
            
        # 他の梶井さんも確認
        all_kajii = [a for a in authors if '梶井' in a.name]
        if len(all_kajii) > 1:
            print(f"\n📖 その他の梶井さん ({len(all_kajii)-1}名):")
            for author in all_kajii:
                if author.name != "梶井 基次郎":
                    print(f"  - {author.name}: {author.author_url}")
                    
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 