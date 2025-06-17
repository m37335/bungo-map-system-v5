#!/usr/bin/env python3
"""
データベース内URL検証スクリプト
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import SessionLocal
from database.crud import AuthorCRUD

def main():
    print("🔍 データベース内URL検証")
    print("=" * 40)
    
    session = SessionLocal()
    crud = AuthorCRUD(session)
    
    # 梶井基次郎確認
    kajii_results = crud.search_authors("梶井 基次郎", limit=1)
    if kajii_results:
        kajii = kajii_results[0]
        print(f"✅ 梶井基次郎 データベース確認")
        print(f"作家名: {kajii.author_name}")
        print(f"URL: {kajii.aozora_author_url}")
        print(f"作品数: {kajii.aozora_works_count}")
        
        expected_url = "https://www.aozora.gr.jp/index_pages/person74.html"
        if kajii.aozora_author_url == expected_url:
            print("🎉 梶井基次郎のURLが正しく保存されています！")
        else:
            print("❌ 梶井基次郎のURLに問題があります")
            print(f"期待: {expected_url}")
            print(f"実際: {kajii.aozora_author_url}")
    else:
        print("❌ 梶井基次郎が見つかりません")
    
    print()
    
    # 他の有名作家も確認
    famous_authors = ["夏目 漱石", "芥川 竜之介", "太宰 治", "宮沢 賢治"]
    print("📚 有名作家URL確認:")
    
    for name in famous_authors:
        results = crud.search_authors(name, limit=1)
        if results:
            author = results[0]
            url = author.aozora_author_url
            has_correct_pattern = "https://www.aozora.gr.jp/index_pages/person" in url
            status = "✅" if has_correct_pattern else "❌"
            print(f"{status} {author.author_name}: {url}")
        else:
            print(f"❌ {name}: 見つからない")
    
    # 統計
    total = crud.get_total_authors()
    print(f"\n📊 データベース統計:")
    print(f"総作家数: {total:,}名")
    print(f"総作品数: {crud.get_total_works_count():,}作品")
    
    session.close()

if __name__ == "__main__":
    main() 