#!/usr/bin/env python3
"""
sentence_placesテーブルのリレーション情報を更新するスクリプト
"""

import sqlite3
import sys
from pathlib import Path

def update_sentence_places_relations():
    """sentence_placesテーブルの空欄フィールドを他テーブルとのリレーションで更新"""
    
    db_path = Path("data/bungo_map.db")
    if not db_path.exists():
        print(f"エラー: データベースファイル {db_path} が見つかりません")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("sentence_placesテーブルのリレーション情報を更新中...")
        
        # 1. author_name, author_birth_year, author_death_year の更新
        update_author_query = """
        UPDATE sentence_places 
        SET 
            author_name = (
                SELECT a.author_name 
                FROM sentences s 
                JOIN works w ON s.work_id = w.work_id 
                JOIN authors a ON w.author_id = a.author_id 
                WHERE s.id = sentence_places.sentence_id
            ),
            author_birth_year = (
                SELECT a.birth_year 
                FROM sentences s 
                JOIN works w ON s.work_id = w.work_id 
                JOIN authors a ON w.author_id = a.author_id 
                WHERE s.id = sentence_places.sentence_id
            ),
            author_death_year = (
                SELECT a.death_year 
                FROM sentences s 
                JOIN works w ON s.work_id = w.work_id 
                JOIN authors a ON w.author_id = a.author_id 
                WHERE s.id = sentence_places.sentence_id
            )
        WHERE author_name IS NULL OR author_birth_year IS NULL OR author_death_year IS NULL
        """
        
        cursor.execute(update_author_query)
        author_updated = cursor.rowcount
        print(f"作者情報を更新: {author_updated}件")
        
        # 2. work_title, work_publication_year の更新
        update_work_query = """
        UPDATE sentence_places 
        SET 
            work_title = (
                SELECT w.work_title 
                FROM sentences s 
                JOIN works w ON s.work_id = w.work_id 
                WHERE s.id = sentence_places.sentence_id
            ),
            work_publication_year = (
                SELECT w.publication_year 
                FROM sentences s 
                JOIN works w ON s.work_id = w.work_id 
                WHERE s.id = sentence_places.sentence_id
            )
        WHERE work_title IS NULL OR work_publication_year IS NULL
        """
        
        cursor.execute(update_work_query)
        work_updated = cursor.rowcount
        print(f"作品情報を更新: {work_updated}件")
        
        # 変更をコミット
        conn.commit()
        
        # 更新後の状況確認
        cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            SUM(CASE WHEN author_birth_year IS NULL THEN 1 ELSE 0 END) as null_birth_year,
            SUM(CASE WHEN author_death_year IS NULL THEN 1 ELSE 0 END) as null_death_year,
            SUM(CASE WHEN work_publication_year IS NULL THEN 1 ELSE 0 END) as null_publication_year,
            SUM(CASE WHEN author_name IS NULL THEN 1 ELSE 0 END) as null_author_name,
            SUM(CASE WHEN work_title IS NULL THEN 1 ELSE 0 END) as null_work_title
        FROM sentence_places
        """)
        
        result = cursor.fetchone()
        print(f"\n更新後の状況:")
        print(f"  総レコード数: {result[0]}")
        print(f"  author_birth_year 空欄: {result[1]}件 ({result[1]/result[0]*100:.1f}%)")
        print(f"  author_death_year 空欄: {result[2]}件 ({result[2]/result[0]*100:.1f}%)")
        print(f"  work_publication_year 空欄: {result[3]}件 ({result[3]/result[0]*100:.1f}%)")
        print(f"  author_name 空欄: {result[4]}件 ({result[4]/result[0]*100:.1f}%)")
        print(f"  work_title 空欄: {result[5]}件 ({result[5]/result[0]*100:.1f}%)")
        
        # サンプルデータを表示
        cursor.execute("""
        SELECT 
            author_name, 
            author_birth_year, 
            author_death_year, 
            work_title, 
            work_publication_year,
            place_name
        FROM sentence_places 
        LIMIT 5
        """)
        
        samples = cursor.fetchall()
        print(f"\n更新後のサンプルデータ:")
        for i, sample in enumerate(samples, 1):
            print(f"  {i}. {sample[0]} ({sample[1]}-{sample[2]}) - {sample[3]} ({sample[4]}) - {sample[5]}")
        
        conn.close()
        print("\nリレーション更新が完了しました！")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    success = update_sentence_places_relations()
    sys.exit(0 if success else 1) 