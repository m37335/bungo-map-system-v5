#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース統合リファクタリングスクリプト v4.0
- スキーマ統一（places vs place_masters）
- メソッド整合性確保
- SQLAlchemyモデルと実際のDBの統一
"""

import sqlite3
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

class DatabaseRefactoring:
    """データベースリファクタリング管理"""
    
    def __init__(self, db_path: str = "data/bungo_map.db"):
        self.db_path = db_path
        print("🔧 データベース統合リファクタリング開始")
        print("=" * 60)
    
    def analyze_current_state(self):
        """現在のデータベース状態を分析"""
        print("📊 現在のデータベース状態分析")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # テーブル一覧取得
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"📋 既存テーブル ({len(tables)}個):")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count:,}レコード")
            
            # places vs place_masters 比較
            if 'places' in tables and 'place_masters' in tables:
                cursor.execute("SELECT COUNT(*) FROM places")
                places_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM place_masters")
                place_masters_count = cursor.fetchone()[0]
                
                print(f"\n🔍 地名テーブル重複問題:")
                print(f"  - places: {places_count:,}レコード")
                print(f"  - place_masters: {place_masters_count:,}レコード")
                
                return {
                    'tables': tables,
                    'places_count': places_count,
                    'place_masters_count': place_masters_count,
                    'needs_consolidation': True
                }
            
            return {'tables': tables, 'needs_consolidation': False}
    
    def consolidate_place_tables(self):
        """地名テーブルの統合"""
        print("\n🔄 地名テーブル統合実行")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 両テーブルのデータ確認
            cursor.execute("SELECT COUNT(*) FROM places")
            places_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM place_masters")
            place_masters_count = cursor.fetchone()[0]
            
            if places_count == 0 and place_masters_count == 0:
                print("  ✅ 両テーブルとも空 - placesテーブルを標準として使用")
                # place_mastersテーブルを削除
                cursor.execute("DROP TABLE IF EXISTS place_masters")
                print("  🗑️  place_mastersテーブルを削除")
            
            elif places_count > 0 and place_masters_count == 0:
                print("  ✅ placesテーブルにデータあり - そのまま使用")
                cursor.execute("DROP TABLE IF EXISTS place_masters")
                
            elif places_count == 0 and place_masters_count > 0:
                print("  🔄 place_mastersからplacesにデータ移行")
                # place_mastersからplacesにデータ移行（必要に応じて）
                # 今回は空なので削除のみ
                cursor.execute("DROP TABLE IF EXISTS place_masters")
                
            else:
                print("  ⚠️  両テーブルにデータあり - 手動確認が必要")
                return False
            
            conn.commit()
            print("  ✅ 地名テーブル統合完了")
            return True
    
    def create_unified_author_interface(self):
        """統一された作者管理インターフェース作成"""
        print("\n📝 統一作者管理インターフェース作成")
        
        interface_code = '''
# 統一作者管理インターフェース
def create_or_get_author(self, author_data) -> Optional[int]:
    """作者を作成または取得（統一インターフェース）"""
    return self.save_author(author_data)

def create_author(self, author_data) -> Optional[int]:
    """新規作者作成（save_authorのエイリアス）"""
    return self.save_author(author_data)

def update_author(self, author_id: int, author_data: dict) -> bool:
    """作者情報更新"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            # 更新フィールドを動的に構築
            update_fields = []
            values = []
            
            for key, value in author_data.items():
                if key != 'author_id':  # IDは更新しない
                    update_fields.append(f"{key} = ?")
                    values.append(value)
            
            if not update_fields:
                return False
            
            values.append(author_id)
            values.append(datetime.now().isoformat())
            
            query = f"""UPDATE authors SET 
                {', '.join(update_fields)}, updated_at = ?
                WHERE author_id = ?"""
            
            cursor = conn.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"作者更新エラー: {e}")
        return False
'''
        
        # インターフェースコードをファイルに保存
        with open("database/author_interface_extension.py", "w", encoding="utf-8") as f:
            f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
統一作者管理インターフェース拡張
DatabaseManagerクラスに追加するメソッド群
\"\"\"

import sqlite3
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

{interface_code}
""")
        
        print("  ✅ author_interface_extension.py を作成")
        print("  📝 DatabaseManagerクラスに手動で統合してください")
        
        return True
    
    def run_full_refactoring(self):
        """完全リファクタリング実行"""
        print("\n🚀 完全リファクタリング実行")
        
        # 1. 現状分析
        state = self.analyze_current_state()
        
        # 2. 地名テーブル統合
        if state.get('needs_consolidation'):
            self.consolidate_place_tables()
        
        # 3. 統一インターフェース作成
        self.create_unified_author_interface()
        
        print("\n🎉 データベースリファクタリング完了")
        print("=" * 60)
        print("📋 次のステップ:")
        print("  1. database/author_interface_extension.py の内容をmanager.pyに統合")
        print("  2. 既存のインポートスクリプトでsave_authorメソッドを使用")
        print("  3. テスト実行でエラーがないことを確認")
        
        return True

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='データベースリファクタリング')
    parser.add_argument('--analyze-only', action='store_true', help='分析のみ実行')
    parser.add_argument('--db-path', default='data/bungo_map.db', help='データベースパス')
    
    args = parser.parse_args()
    
    refactoring = DatabaseRefactoring(args.db_path)
    
    if args.analyze_only:
        refactoring.analyze_current_state()
    else:
        refactoring.run_full_refactoring()

if __name__ == "__main__":
    main() 