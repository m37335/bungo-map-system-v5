#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DatabaseManager テストスクリプト
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent / "bungo-map-system-v4"))

from database.manager import DatabaseManager

def test_get_author():
    """作者取得テスト"""
    db_manager = DatabaseManager("bungo-map-system-v4/data/bungo_map.db")
    
    print("📊 作者検索テスト")
    print("=" * 50)
    
    # 夏目漱石を検索（複数パターン）
    test_names = [
        "夏目漱石",
        "夏目 漱石",
        "漱石"
    ]
    
    for name in test_names:
        print(f"\n🔍 検索: '{name}'")
        author = db_manager.get_author_by_name(name)
        
        if author:
            print(f"✅ 発見: ID={author.author_id}, 名前={author.author_name}")
            print(f"   生年: {author.birth_year}, 没年: {author.death_year}")
            print(f"   作品数: {author.works_count}")
        else:
            print(f"❌ 見つからず")
    
    # 全作者数確認
    print(f"\n📈 データベース統計:")
    all_authors = db_manager.get_all_authors()
    print(f"   総作者数: {len(all_authors)}名")
    
    # 作品数上位5名
    authors_with_works = []
    for author in all_authors[:5]:
        print(f"   {author.author_name}: {author.works_count}作品")

if __name__ == "__main__":
    test_get_author() 