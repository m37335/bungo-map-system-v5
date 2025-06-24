#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青空文庫作家情報JSON一括インポートスクリプト
取得済みのJSONファイルからデータベースに作家情報を一括登録
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import DatabaseManager

class AuthorJSONImporter:
    """青空文庫作家情報JSON一括インポータ"""
    
    def __init__(self, db_path: str = "data/bungo_map.db"):
        self.db_manager = DatabaseManager(db_path)
        self.stats = {
            'total_processed': 0,
            'new_authors': 0,
            'updated_authors': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def import_from_json(self, json_file_path: str, force_update: bool = False) -> Dict[str, Any]:
        """JSONファイルから作家情報を一括インポート"""
        print("📥 青空文庫作家情報 JSON一括インポート開始")
        print("=" * 60)
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # JSONファイル読み込み
            print(f"📂 JSONファイル読み込み: {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            authors_data = data.get('authors', [])
            if not authors_data:
                print("❌ 作家データが見つかりません")
                return self.stats
            
            print(f"✅ {len(authors_data)}名の作家データを読み込み完了")
            
            # データベース一括インポート
            self._import_authors_to_database(authors_data, force_update)
            
            self.stats['end_time'] = datetime.now()
            elapsed = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            # 結果レポート表示
            self._print_import_report(elapsed)
            
            return self.stats
            
        except Exception as e:
            print(f"❌ インポートエラー: {e}")
            self.stats['errors'] += 1
            return self.stats
    
    def _import_authors_to_database(self, authors_data: List[Dict], force_update: bool):
        """作家データをデータベースに一括インポート"""
        print(f"💾 データベースインポート開始: {len(authors_data)}名")
        
        for i, author_data in enumerate(authors_data, 1):
            try:
                self.stats['total_processed'] += 1
                
                # データベース用の形式に変換
                db_author_data = self._convert_to_db_format(author_data)
                
                # 既存作家チェック
                existing_author = self.db_manager.get_author_by_name(db_author_data['author_name'])
                
                if existing_author:
                    if force_update:
                        # 既存作家更新（新しいupdate_authorメソッドを使用）
                        success = self.db_manager.update_author(existing_author.author_id, db_author_data)
                        if success:
                            self.stats['updated_authors'] += 1
                            print(f"  🔄 更新: {db_author_data['author_name']}")
                        else:
                            self.stats['errors'] += 1
                            print(f"  ❌ 更新失敗: {db_author_data['author_name']}")
                    else:
                        print(f"  ⏭️  スキップ（既存）: {db_author_data['author_name']}")
                else:
                    # 新規作家作成（統一インターフェース使用）
                    author_id = self.db_manager.create_author(db_author_data)
                    if author_id:
                        self.stats['new_authors'] += 1
                        print(f"  ✅ 新規: {db_author_data['author_name']} (ID: {author_id})")
                    else:
                        self.stats['errors'] += 1
                        print(f"  ❌ 作成失敗: {db_author_data['author_name']}")
                
                # 進捗表示
                if i % 100 == 0:
                    print(f"  📊 進捗: {i}/{len(authors_data)} ({(i/len(authors_data)*100):.1f}%)")
                
            except Exception as e:
                self.stats['errors'] += 1
                print(f"  ❌ エラー: {author_data.get('name', 'Unknown')} - {e}")
    
    def _convert_to_db_format(self, json_author: Dict) -> Dict[str, Any]:
        """JSON形式をデータベース形式に変換"""
        return {
            'author_name': json_author['name'],
            'author_name_kana': json_author.get('name_reading'),
            'aozora_author_url': json_author.get('author_url'),
            'copyright_status': json_author.get('copyright_status', 'expired'),
            'aozora_works_count': json_author.get('works_count', 0),
            'alias_info': json_author.get('alias_info'),
            'section': json_author.get('section', 'その他'),
            'source_system': 'aozora_json_import_v4.0',
            'verification_status': 'imported',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    
    def _print_import_report(self, elapsed_seconds: float):
        """インポート結果レポート表示"""
        print(f"\n📊 インポート完了レポート")
        print("=" * 60)
        print(f"処理対象: {self.stats['total_processed']:,}名")
        print(f"新規作家: {self.stats['new_authors']:,}名")
        print(f"更新作家: {self.stats['updated_authors']:,}名")
        print(f"エラー: {self.stats['errors']:,}件")
        print(f"処理時間: {elapsed_seconds:.1f}秒")
        print(f"処理速度: {self.stats['total_processed']/elapsed_seconds:.1f}件/秒")
        
        success_rate = (self.stats['new_authors'] + self.stats['updated_authors']) / max(1, self.stats['total_processed']) * 100
        print(f"成功率: {success_rate:.1f}%")
        print("✅ データベースインポート完了")
    
    def preview_json_data(self, json_file_path: str, limit: int = 10):
        """JSONデータのプレビュー表示"""
        print(f"👀 JSONデータプレビュー: {json_file_path}")
        print("=" * 60)
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            authors_data = data.get('authors', [])
            metadata = {k: v for k, v in data.items() if k != 'authors'}
            
            print(f"📊 メタデータ:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            
            print(f"\n👥 作家データサンプル (最初の{min(limit, len(authors_data))}名):")
            for i, author in enumerate(authors_data[:limit], 1):
                print(f"  {i:2}. {author['name']} - 作品数: {author['works_count']}, セクション: {author['section']}, 著作権: {author['copyright_status']}")
            
            if len(authors_data) > limit:
                print(f"  ... 他 {len(authors_data) - limit}名")
            
        except Exception as e:
            print(f"❌ プレビューエラー: {e}")


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='青空文庫作家情報JSON一括インポート')
    parser.add_argument('--json-file', default='extractors/aozora/data/aozora_authors.json', 
                       help='インポートするJSONファイルパス')
    parser.add_argument('--force-update', action='store_true', 
                       help='既存作家も強制更新')
    parser.add_argument('--preview', action='store_true', 
                       help='データのプレビューのみ表示')
    
    args = parser.parse_args()
    
    importer = AuthorJSONImporter()
    
    if args.preview:
        # プレビューモード
        importer.preview_json_data(args.json_file, limit=20)
    else:
        # インポート実行
        print(f"📥 インポート設定:")
        print(f"  JSONファイル: {args.json_file}")
        print(f"  強制更新: {args.force_update}")
        
        if not args.force_update:
            response = input(f"\n❓ インポートを実行しますか？ (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ インポートをキャンセルしました")
                return
        
        # インポート実行
        result = importer.import_from_json(args.json_file, args.force_update)


if __name__ == "__main__":
    main() 