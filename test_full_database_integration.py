#!/usr/bin/env python3
"""
青空文庫作家情報の大規模データベース統合テスト

このスクリプトは以下を実行します：
1. 全作家情報のスクレイピング（1,331名）
2. データベースへの一括保存
3. 詳細統計とレポート生成
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.author_list_scraper import AuthorListScraper
from database.models import Author
from database.config import SessionLocal, init_db
from database.crud import AuthorCRUD

def main():
    print("🚀 青空文庫全作家データベース統合テスト開始")
    print("=" * 60)
    
    try:
        # データベース初期化
        print("📊 データベースセットアップ...")
        init_db()
        session = SessionLocal()
        author_crud = AuthorCRUD(session)
        
        # 既存データ確認
        existing_count = author_crud.get_total_authors()
        if existing_count > 0:
            print(f"⚠️  既存データ: {existing_count}名（上書き更新されます）")
        
        # 全作家情報取得
        print("\n📚 全作家情報を取得中...")
        scraper = AuthorListScraper(rate_limit=0.5)  # 少し高速化
        authors = scraper.fetch_all_authors()
        
        if not authors:
            print("❌ 作家情報の取得に失敗しました")
            return
        
        print(f"✅ {len(authors)}名の作家情報を取得完了")
        
        # データベース一括保存
        print(f"\n💾 {len(authors)}名をデータベースに保存中...")
        start_time = datetime.now()
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        for i, author_info in enumerate(authors, 1):
            try:
                author_data = {
                    'author_name': author_info.name,
                    'author_name_kana': author_info.name_reading,
                    'aozora_author_url': author_info.author_url,
                    'copyright_status': author_info.copyright_status,
                    'aozora_works_count': author_info.works_count,
                    'alias_info': author_info.alias_info,
                    'section': author_info.section,
                    'source_system': 'aozora_scraper_v1.0',
                    'verification_status': 'auto_scraped'
                }
                
                # 既存チェック
                existing = session.query(Author).filter(
                    Author.author_name == author_info.name
                ).first()
                
                if existing:
                    updated_count += 1
                else:
                    saved_count += 1
                
                result = author_crud.create_author(author_data)
                
                # 進捗表示
                if i % 100 == 0:
                    print(f"   進捗: {i}/{len(authors)} ({i/len(authors)*100:.1f}%)")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 最初の5件だけエラー表示
                    print(f"⚠️  保存エラー ({author_info.name}): {e}")
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n✅ データベース保存完了 ({processing_time:.1f}秒)")
        print(f"   新規保存: {saved_count}名")
        print(f"   更新: {updated_count}名")
        print(f"   エラー: {error_count}名")
        
        # 詳細統計レポート
        print(f"\n📊 データベース統計レポート")
        print("=" * 40)
        
        total_authors = author_crud.get_total_authors()
        total_works = author_crud.get_total_works_count()
        
        print(f"総作家数: {total_authors:,}名")
        print(f"総作品数: {total_works:,}作品")
        print(f"平均作品数: {total_works/total_authors:.1f}作品/作家")
        
        # 著作権別統計
        copyright_stats = author_crud.get_copyright_statistics()
        print(f"\n📈 著作権別統計:")
        for status, count in copyright_stats.items():
            percentage = count / total_authors * 100
            print(f"  {status}: {count:,}名 ({percentage:.1f}%)")
        
        # セクション別統計
        section_stats = author_crud.get_section_statistics()
        print(f"\n📚 セクション別統計:")
        for section, count in sorted(section_stats.items()):
            print(f"  {section}: {count:,}名")
        
        # 作品数上位作家
        print(f"\n🏆 作品数上位10名:")
        top_authors = author_crud.get_top_authors_by_works(10)
        for i, author in enumerate(top_authors, 1):
            print(f"  {i:2}. {author.author_name}: {author.aozora_works_count:,}作品")
        
        # 検索テスト
        print(f"\n🔍 検索テスト:")
        test_keywords = ["夏目", "芥川", "太宰", "宮沢"]
        for keyword in test_keywords:
            results = author_crud.search_authors(keyword, limit=3)
            print(f"  '{keyword}': {len(results)}件")
            for author in results[:2]:  # 最初の2件表示
                print(f"    - {author.author_name}")
        
        # データエクスポート
        print(f"\n📤 全データエクスポート...")
        all_authors = author_crud.get_all_authors()
        
        export_data = []
        for author in all_authors:
            export_data.append({
                'author_id': author.author_id,
                'author_name': author.author_name,
                'author_name_kana': author.author_name_kana,
                'aozora_author_url': author.aozora_author_url,
                'copyright_status': author.copyright_status,
                'aozora_works_count': author.aozora_works_count,
                'section': author.section,
                'alias_info': author.alias_info,
                'created_at': author.created_at.isoformat() if author.created_at else None,
                'updated_at': author.updated_at.isoformat() if author.updated_at else None
            })
        
        # JSONファイルに保存
        export_file = Path("data/full_database_export.json")
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'total_authors': len(export_data),
                    'total_works': total_works,
                    'copyright_stats': copyright_stats,
                    'section_stats': section_stats
                },
                'authors': export_data
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 完全データを {export_file} にエクスポート完了")
        
        # 最終結果
        print(f"\n🎉 全作家データベース統合テスト完了！")
        print(f"処理時間: {processing_time:.1f}秒")
        print(f"処理速度: {len(authors)/processing_time:.1f}作家/秒")
        
        session.close()
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 