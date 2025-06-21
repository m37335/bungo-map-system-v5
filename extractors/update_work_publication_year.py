#!/usr/bin/env python3
"""
sentence_placesテーブルのwork_publication_year更新スクリプト
"""

import sqlite3
import sys
from pathlib import Path

def update_work_publication_year():
    """sentence_placesテーブルのwork_publication_yearを更新"""
    
    db_path = Path("../data/bungo_map.db")
    if not db_path.exists():
        print(f"エラー: データベースファイル {db_path} が見つかりません")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📅 work_publication_year更新中...")
        
        # 現在の空欄状況確認
        cursor.execute("SELECT COUNT(*) FROM sentence_places WHERE work_publication_year IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"📊 更新対象: {null_count}件")
        
        if null_count == 0:
            print("✅ 既に全レコードが設定済みです")
            return True
        
        # work_publication_yearを更新
        update_query = """
        UPDATE sentence_places 
        SET work_publication_year = (
            SELECT w.publication_year 
            FROM sentences s
            JOIN works w ON s.work_id = w.work_id
            WHERE s.sentence_id = sentence_places.sentence_id
        )
        WHERE work_publication_year IS NULL
        """
        
        cursor.execute(update_query)
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ work_publication_year更新完了: {updated_count}件")
        
        # 更新後の確認
        cursor.execute("SELECT COUNT(*) FROM sentence_places WHERE work_publication_year IS NULL")
        remaining_null = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sentence_places WHERE work_publication_year IS NOT NULL")
        updated_total = cursor.fetchone()[0]
        
        print(f"\n更新後の状況:")
        print(f"  設定済み: {updated_total}件")
        print(f"  空欄: {remaining_null}件")
        
        # サンプル表示
        cursor.execute("""
        SELECT work_title, work_publication_year, place_name_only
        FROM sentence_places 
        WHERE work_publication_year IS NOT NULL
        LIMIT 5
        """)
        
        samples = cursor.fetchall()
        print(f"\n更新済みサンプル:")
        for i, (title, year, place) in enumerate(samples, 1):
            print(f"  {i}. {title} ({year}年) - {place}")
        
        conn.close()
        print("\n🎉 work_publication_year更新完了！")
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    success = update_work_publication_year()
    sys.exit(0 if success else 1) 