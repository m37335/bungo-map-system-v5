#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作品数データ修正スクリプト
JSONデータから正しい作品数でauthorsテーブルを更新
"""

import json
import sqlite3
import sys
import os

def fix_works_count():
    """JSONファイルから作品数を読み取ってデータベースを更新"""
    print("🔧 作品数データ修正開始")
    print("=" * 50)
    
    # JSONファイル読み込み
    json_file = "extractors/aozora/data/aozora_authors.json"
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    authors_data = data.get('authors', [])
    print(f"📂 {len(authors_data)}名の作家データを読み込み")
    
    # データベース接続
    db_path = "data/bungo_map.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updated_count = 0
    error_count = 0
    
    try:
        for author in authors_data:
            name = author['name']
            works_count = author['works_count']
            
            try:
                # 作品数を更新
                cursor.execute("""
                    UPDATE authors 
                    SET aozora_works_count = ? 
                    WHERE author_name = ?
                """, (works_count, name))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"  📊 進捗: {updated_count}/{len(authors_data)} ({updated_count/len(authors_data)*100:.1f}%)")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ エラー: {name} - {e}")
        
        # 変更をコミット
        conn.commit()
        print(f"\n✅ 修正完了:")
        print(f"  更新作家数: {updated_count}")
        print(f"  エラー数: {error_count}")
        
        # 結果確認
        cursor.execute("SELECT COUNT(*) FROM authors WHERE aozora_works_count > 0")
        works_count_authors = cursor.fetchone()[0]
        print(f"  作品数>0の作家: {works_count_authors}名")
        
        # トップ10表示
        print(f"\n📊 作品数トップ10:")
        cursor.execute("""
            SELECT author_name, aozora_works_count 
            FROM authors 
            WHERE aozora_works_count > 0 
            ORDER BY aozora_works_count DESC 
            LIMIT 10
        """)
        
        for i, (name, count) in enumerate(cursor.fetchall(), 1):
            print(f"  {i:2}. {name}: {count}作品")
        
    finally:
        conn.close()

if __name__ == "__main__":
    fix_works_count() 