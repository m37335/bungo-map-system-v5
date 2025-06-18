#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者検索テスト（柔軟性確認）
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent / "bungo-map-system-v4"))

from database.manager import DatabaseManager

def test_flexible_author_search():
    """柔軟な作者検索のテスト"""
    
    # 柔軟検索の実装（fetch_author_works.pyから抜粋）
    def get_author_with_flexible_name(db_manager, author_name):
        """柔軟な作者名検索"""
        # 検索パターンを構築
        search_patterns = [author_name]  # 入力そのまま
        
        # スペースがない場合、スペースを追加したパターンを試行
        if " " not in author_name and len(author_name) >= 3:
            # 一般的な分割パターン（姓2文字+名、姓1文字+名）
            if len(author_name) >= 4:
                search_patterns.append(f"{author_name[:2]} {author_name[2:]}")  # 夏目漱石 → 夏目 漱石
            if len(author_name) >= 3:
                search_patterns.append(f"{author_name[:1]} {author_name[1:]}")  # 夏目漱石 → 夏 目漱石
        
        # 各パターンで検索
        for pattern in search_patterns:
            print(f"  🔍 検索パターン: '{pattern}'")
            author = db_manager.get_author_by_name(pattern)
            if author:
                print(f"  ✅ 作者発見: '{pattern}' → {author.author_name}")
                return author
        
        return None
    
    db_manager = DatabaseManager("bungo-map-system-v4/data/bungo_map.db")
    
    print("📚 柔軟作者検索テスト")
    print("=" * 50)
    
    # テストケース
    test_cases = [
        "夏目漱石",      # スペースなし
        "夏目 漱石",     # スペースあり
        "芥川龍之介",    # スペースなし
        "太宰治",        # 短い名前
        "宮本百合子"     # 女性作家
    ]
    
    for test_name in test_cases:
        print(f"\n🎯 テスト: '{test_name}'")
        author = get_author_with_flexible_name(db_manager, test_name)
        
        if author:
            print(f"  📊 結果: 成功 (ID: {author.author_id})")
        else:
            print(f"  ❌ 結果: 見つからず")

if __name__ == "__main__":
    test_flexible_author_search() 