#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorsテーブルスキーマ更新マイグレーション
青空文庫対応フィールドを追加
"""

import sqlite3
import sys
import os
from datetime import datetime

def migrate_authors_table(db_path: str = "data/bungo_map.db"):
    """authorsテーブルに青空文庫関連フィールドを追加"""
    print("🔧 authorsテーブルスキーマ更新開始")
    print("=" * 60)
    
    try:
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在のスキーマ確認
        print("📊 現在のテーブル構造:")
        cursor.execute("PRAGMA table_info(authors);")
        current_columns = cursor.fetchall()
        existing_column_names = [col[1] for col in current_columns]
        
        for col in current_columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PK' if col[5] else ''}")
        
        # 追加するカラム定義
        new_columns = [
            ("author_name_kana", "VARCHAR(255)"),
            ("period", "VARCHAR(50)"),
            ("description", "TEXT"),
            ("portrait_url", "VARCHAR(512)"),
            ("copyright_status", "VARCHAR(20)", "DEFAULT 'expired'"),
            ("aozora_works_count", "INTEGER", "DEFAULT 0"),
            ("alias_info", "TEXT"),
            ("section", "VARCHAR(10)"),
            ("works_count", "INTEGER", "DEFAULT 0"),
            ("total_sentences", "INTEGER", "DEFAULT 0"),
            ("source_system", "VARCHAR(50)", "DEFAULT 'v4.0'"),
            ("verification_status", "VARCHAR(20)", "DEFAULT 'pending'")
        ]
        
        # カラム追加実行
        print(f"\n🔨 カラム追加実行:")
        added_count = 0
        
        for column_def in new_columns:
            column_name = column_def[0]
            column_type = column_def[1]
            column_extra = column_def[2] if len(column_def) > 2 else ""
            
            if column_name not in existing_column_names:
                try:
                    alter_sql = f"ALTER TABLE authors ADD COLUMN {column_name} {column_type} {column_extra}"
                    print(f"  + {column_name} {column_type} {column_extra}")
                    cursor.execute(alter_sql)
                    added_count += 1
                except Exception as e:
                    print(f"  ❌ {column_name}: {e}")
            else:
                print(f"  ⏭️  {column_name}: 既存")
        
        # aozora_author_urlのサイズ拡張（既存カラムなので別途対応が必要）
        print(f"\n🔧 既存カラムの最適化:")
        try:
            # SQLiteではカラムサイズ変更が制限されているため、データが入っている場合は注意
            print(f"  ℹ️  aozora_author_url: サイズ拡張は既存データがある場合複雑なため、現在のまま使用")
        except Exception as e:
            print(f"  ⚠️  aozora_author_url最適化エラー: {e}")
        
        # インデックス追加
        print(f"\n📇 インデックス追加:")
        indexes_to_add = [
            ("idx_authors_section", "section"),
            ("idx_authors_copyright", "copyright_status"),
            ("idx_authors_source", "source_system")
        ]
        
        for index_name, column_name in indexes_to_add:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON authors({column_name})")
                print(f"  ✅ {index_name}: {column_name}")
            except Exception as e:
                print(f"  ❌ {index_name}: {e}")
        
        # 変更をコミット
        conn.commit()
        
        # 更新後のスキーマ確認
        print(f"\n📊 更新後のテーブル構造:")
        cursor.execute("PRAGMA table_info(authors);")
        updated_columns = cursor.fetchall()
        
        for col in updated_columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PK' if col[5] else ''}")
        
        print(f"\n✅ マイグレーション完了")
        print(f"  追加カラム: {added_count}個")
        print(f"  総カラム数: {len(updated_columns)}個")
        
        return True
        
    except Exception as e:
        print(f"❌ マイグレーションエラー: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

def verify_schema_compatibility():
    """SQLAlchemyモデルとの互換性確認"""
    print(f"\n🔍 スキーマ互換性確認:")
    
    try:
        # SQLAlchemyモデルから期待されるフィールド取得
        from database.models import Author
        
        # SQLAlchemyモデルのカラム一覧取得
        expected_columns = []
        for column in Author.__table__.columns:
            expected_columns.append(column.name)
        
        print(f"  SQLAlchemyモデル期待カラム: {len(expected_columns)}個")
        
        # データベースの実際のカラム確認
        conn = sqlite3.connect("data/bungo_map.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(authors);")
        actual_columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        print(f"  データベース実際カラム: {len(actual_columns)}個")
        
        # 差分確認
        missing_in_db = set(expected_columns) - set(actual_columns)
        extra_in_db = set(actual_columns) - set(expected_columns)
        
        if missing_in_db:
            print(f"  ❌ データベースに不足: {list(missing_in_db)}")
        
        if extra_in_db:
            print(f"  ℹ️  データベースに余分: {list(extra_in_db)}")
        
        if not missing_in_db and not extra_in_db:
            print(f"  ✅ 完全互換")
            return True
        else:
            print(f"  ⚠️  部分互換（機能上は問題ない可能性があります）")
            return len(missing_in_db) == 0  # 不足がなければOK
            
    except Exception as e:
        print(f"  ❌ 互換性確認エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='authorsテーブルスキーマ更新')
    parser.add_argument('--db-path', default='data/bungo_map.db', help='データベースファイルパス')
    parser.add_argument('--verify-only', action='store_true', help='互換性確認のみ実行')
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_schema_compatibility()
    else:
        print(f"🎯 データベース: {args.db_path}")
        
        # バックアップ推奨メッセージ
        print(f"\n⚠️  重要: データベースのバックアップを推奨します")
        print(f"  cp {args.db_path} {args.db_path}.backup_$(date +%Y%m%d_%H%M%S)")
        
        response = input(f"\n❓ マイグレーションを実行しますか？ (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ マイグレーションをキャンセルしました")
            return
        
        # マイグレーション実行
        success = migrate_authors_table(args.db_path)
        
        if success:
            print(f"\n🎉 マイグレーション成功！")
            verify_schema_compatibility()
        else:
            print(f"\n💥 マイグレーション失敗")

if __name__ == "__main__":
    main() 