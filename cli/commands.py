#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データ抽出・処理の統合コマンドライン機能
青空文庫スクレイピング、テキスト処理、地名抽出の完全パイプライン
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import click
from pathlib import Path
import sys
import os

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..extractors.aozora_scraper import AozoraScraper
from ..extractors.text_processor import TextProcessor, ProcessingStats
from ..extractors.place_extractor import EnhancedPlaceExtractor
from ..database.manager import DatabaseManager
from ..core.cache import CacheManager
from ..quality.validator import QualityValidator

logger = logging.getLogger(__name__)

class DataProcessingPipeline:
    """データ処理パイプライン統合クラス"""
    
    def __init__(self, db_path: str = "data/db/bungo_v4.db"):
        """初期化"""
        self.db_path = db_path
        self.db_manager = DatabaseManager()
        self.aozora_scraper = AozoraScraper(db_manager=self.db_manager)
        self.text_processor = TextProcessor()
        self.place_extractor = EnhancedPlaceExtractor()
        self.cache_manager = CacheManager()
        self.quality_validator = QualityValidator()
        
        # 対象作品リスト（確実なURL使用）
        self.target_works = [
            {
                'author': '夏目漱石',
                'title': 'こころ',
                'url': 'https://www.aozora.gr.jp/cards/000148/files/773_14560.html'
            },
            {
                'author': '芥川龍之介',
                'title': '羅生門',
                'url': 'https://www.aozora.gr.jp/cards/000879/files/127_15260.html'
            },
            {
                'author': '太宰治',
                'title': '走れメロス',
                'url': 'https://www.aozora.gr.jp/cards/000035/files/1567_14913.html'
            },
            {
                'author': '宮沢賢治',
                'title': '注文の多い料理店',
                'url': 'https://www.aozora.gr.jp/cards/000081/files/43754_17659.html'
            },
            {
                'author': '樋口一葉',
                'title': 'たけくらべ',
                'url': 'https://www.aozora.gr.jp/cards/000064/files/893_14763.html'
            }
        ]
        
        logger.info("🗾 データ処理パイプライン初期化完了")
    
    async def process_complete_flow(self, limit_sentences: int = 500) -> Dict[str, Any]:
        """完全フロー処理"""
        print(f"\n🚀 文豪ゆかり地図システム - 完全データ処理開始")
        print("=" * 80)
        
        results = {
            'processed_works': [],
            'total_sentences': 0,
            'total_places': 0,
            'total_geocoded': 0,
            'errors': [],
            'start_time': datetime.now(),
            'end_time': None
        }
        
        try:
            # データベース初期化
            await self._initialize_database()
            
            # 各作品を順次処理
            for i, work_info in enumerate(self.target_works, 1):
                print(f"\n📖 {i}/{len(self.target_works)}: {work_info['author']} - {work_info['title']}")
                print("-" * 60)
                
                try:
                    work_result = await self._process_single_work(work_info, limit_sentences)
                    if work_result:
                        results['processed_works'].append(work_result)
                        results['total_sentences'] += work_result.get('sentences_count', 0)
                        results['total_places'] += work_result.get('places_count', 0)
                        results['total_geocoded'] += work_result.get('geocoded_count', 0)
                    else:
                        results['errors'].append(f"{work_info['author']} - {work_info['title']}")
                
                except Exception as e:
                    logger.error(f"❌ 作品処理エラー: {e}")
                    results['errors'].append(f"{work_info['author']} - {work_info['title']}: {str(e)}")
                
                time.sleep(1)  # レート制限
            
            results['end_time'] = datetime.now()
            
            # 最終レポート生成
            self._generate_final_report(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 完全フロー処理エラー: {e}")
            results['errors'].append(f"システムエラー: {str(e)}")
            return results
    
    async def _initialize_database(self):
        """データベース初期化"""
        print("💾 データベース初期化中...")
        try:
            await self.db_manager.initialize_database()
            print("✅ データベース初期化完了")
        except Exception as e:
            logger.error(f"❌ データベース初期化失敗: {e}")
            raise
    
    async def _process_single_work(self, work_info: Dict[str, str], limit_sentences: int) -> Optional[Dict[str, Any]]:
        """単一作品の完全処理"""
        
        # 1. テキスト取得
        print(f"  📄 テキスト取得中...")
        raw_content = self.aozora_scraper.fetch_work_content(work_info['url'])
        if not raw_content:
            print(f"  ❌ テキスト取得失敗")
            return None
        
        print(f"  📄 取得完了: {len(raw_content):,}文字")
        
        # 2. テキスト前処理
        print(f"  🧹 テキストクリーニング実行...")
        cleaned_content, processing_stats = self.text_processor.clean_aozora_text(raw_content)
        
        # 3. 品質検証
        quality_result = self.text_processor.validate_text_quality(cleaned_content)
        if not quality_result['is_valid']:
            print(f"  ⚠️ 品質検証警告: {quality_result['errors']}")
        
        # 4. 文分割
        sentences = self.text_processor.split_into_sentences(cleaned_content)
        print(f"  📝 文分割完了: {len(sentences)}文")
        
        # 5. データベース格納
        print(f"  💾 データベース格納...")
        work_id = await self._store_work_in_database(work_info, cleaned_content, sentences)
        if not work_id:
            print(f"  ❌ データベース格納失敗")
            return None
        
        print(f"  ✅ データベース格納完了: work_id={work_id}")
        
        # 6. 地名抽出（制限付き）
        print(f"  🗺️ 地名抽出実行（最大{limit_sentences}文）...")
        limited_sentences = sentences[:limit_sentences]
        places_count = await self._extract_places_for_work(work_id, work_info, limited_sentences)
        print(f"  🗺️ 地名抽出完了: {places_count}件")
        
        # 7. ジオコーディング
        print(f"  🌍 ジオコーディング実行...")
        geocoded_count = await self._geocode_places_for_work(work_id)
        print(f"  🌍 ジオコーディング完了: {geocoded_count}件")
        
        return {
            'work_id': work_id,
            'author': work_info['author'],
            'title': work_info['title'],
            'processing_stats': processing_stats,
            'quality_result': quality_result,
            'sentences_count': len(sentences),
            'places_count': places_count,
            'geocoded_count': geocoded_count
        }
    
    async def _store_work_in_database(self, work_info: Dict[str, str], content: str, sentences: List[str]) -> Optional[int]:
        """作品をデータベースに格納"""
        try:
            # 作者の取得または作成
            author_data = {
                'author_name': work_info['author'],
                'source_system': 'v4.0',
                'verification_status': 'pending'
            }
            author = await self.db_manager.get_or_create_author(author_data)
            
            # 作品の作成
            work_data = {
                'work_title': work_info['title'],
                'author_id': author.author_id,
                'aozora_url': work_info['url'],
                'content_length': len(content),
                'sentence_count': len(sentences),
                'source_system': 'v4.0',
                'processing_status': 'processing'
            }
            work = await self.db_manager.create_work(work_data)
            
            # センテンスの一括作成
            sentence_data_list = []
            for i, sentence_text in enumerate(sentences):
                sentence_data = {
                    'sentence_text': sentence_text,
                    'work_id': work.work_id,
                    'author_id': author.author_id,
                    'sentence_length': len(sentence_text),
                    'position_in_work': i
                }
                sentence_data_list.append(sentence_data)
            
            await self.db_manager.create_sentences_batch(sentence_data_list)
            
            return work.work_id
            
        except Exception as e:
            logger.error(f"❌ データベース格納エラー: {e}")
            return None
    
    async def _extract_places_for_work(self, work_id: int, work_info: Dict[str, str], sentences: List[str]) -> int:
        """作品の地名抽出"""
        places_count = 0
        
        try:
            # 全文をまとめて処理（効率化）
            full_text = ' '.join(sentences)
            
            # 地名抽出実行
            extracted_places = await self.place_extractor.extract_places(
                full_text, 
                work_info['title'], 
                work_info['author']
            )
            
            # データベースに格納
            for place in extracted_places:
                try:
                    # 地名の取得または作成
                    place_data = {
                        'place_name': place.name,
                        'canonical_name': place.name,
                        'place_type': self._map_place_category(place.category),
                        'confidence': place.confidence,
                        'source_system': 'v4.0',
                        'verification_status': 'auto'
                    }
                    place_obj = await self.db_manager.get_or_create_place(place_data)
                    
                    # センテンス-地名関連の作成
                    # 簡略化: 最初の文に関連付け
                    if sentences:
                        sentence_obj = await self.db_manager.get_sentence_by_text_and_work(
                            sentences[0], work_id
                        )
                        if sentence_obj:
                            relation_data = {
                                'sentence_id': sentence_obj.sentence_id,
                                'place_id': place_obj.place_id,
                                'extraction_method': place.source,
                                'confidence': place.confidence,
                                'matched_text': place.matched_text,
                                'verification_status': 'auto'
                            }
                            await self.db_manager.create_sentence_place(relation_data)
                            places_count += 1
                
                except Exception as e:
                    logger.warning(f"地名格納エラー: {place.name} - {e}")
            
        except Exception as e:
            logger.error(f"❌ 地名抽出エラー: {e}")
        
        return places_count
    
    async def _geocode_places_for_work(self, work_id: int) -> int:
        """作品の地名ジオコーディング"""
        # 基本実装（ジオコーディング機能が利用可能な場合）
        try:
            geocoded_count = 0
            places = await self.db_manager.get_places_by_work(work_id)
            
            for place in places:
                if not place.latitude or not place.longitude:
                    # 基本的なジオコーディング（仮実装）
                    # 実際のジオコーディングサービスが必要
                    # geocoded_data = await self.geocoding_service.geocode(place.place_name)
                    # if geocoded_data:
                    #     await self.db_manager.update_place_coordinates(
                    #         place.place_id, geocoded_data['lat'], geocoded_data['lng']
                    #     )
                    #     geocoded_count += 1
                    pass
            
            return geocoded_count
            
        except Exception as e:
            logger.error(f"❌ ジオコーディングエラー: {e}")
            return 0
    
    def _map_place_category(self, category: str) -> str:
        """地名カテゴリのマッピング"""
        mapping = {
            '完全地名': '市区町村',
            '都道府県': '都道府県',
            '市区町村': '市区町村',
            '有名地名': '有名地名',
            '自然地名': '有名地名',
            '歴史地名': '歴史地名',
            'nlp_entity': '有名地名'
        }
        return mapping.get(category, '有名地名')
    
    def _generate_final_report(self, results: Dict[str, Any]):
        """最終レポート生成"""
        print(f"\n📊 処理完了レポート")
        print("=" * 80)
        
        duration = results['end_time'] - results['start_time'] if results['end_time'] else None
        
        print(f"⏱️  処理時間: {duration}")
        print(f"📖 処理作品数: {len(results['processed_works'])}/{len(self.target_works)}")
        print(f"📝 総センテンス数: {results['total_sentences']:,}")
        print(f"🗺️ 総地名数: {results['total_places']:,}")
        print(f"🌍 ジオコーディング数: {results['total_geocoded']:,}")
        
        if results['errors']:
            print(f"\n❌ エラー ({len(results['errors'])}件):")
            for error in results['errors']:
                print(f"  - {error}")
        
        print(f"\n✅ データ処理パイプライン完了")
        print("=" * 80)

# CLIコマンド定義
@click.group()
def cli():
    """文豪ゆかり地図システム データ処理コマンド"""
    pass

@cli.command()
@click.option('--limit-sentences', default=500, help='処理する最大センテンス数')
@click.option('--db-path', default='data/db/bungo_v4.db', help='データベースパス')
def process_all(limit_sentences: int, db_path: str):
    """全作品の完全処理"""
    pipeline = DataProcessingPipeline(db_path)
    
    async def run():
        await pipeline.process_complete_flow(limit_sentences)
    
    asyncio.run(run())

@cli.command()
@click.argument('url')
@click.option('--author', required=True, help='作者名')
@click.option('--title', required=True, help='作品名')
@click.option('--db-path', default='data/db/bungo_v4.db', help='データベースパス')
def process_single(url: str, author: str, title: str, db_path: str):
    """単一作品の処理"""
    pipeline = DataProcessingPipeline(db_path)
    work_info = {'url': url, 'author': author, 'title': title}
    
    async def run():
        result = await pipeline._process_single_work(work_info, 500)
        if result:
            print(f"✅ 処理完了: {result}")
        else:
            print("❌ 処理失敗")
    
    asyncio.run(run())

@cli.command()
@click.argument('text')
def test_extraction(text: str):
    """地名抽出テスト"""
    async def run():
        extractor = EnhancedPlaceExtractor()
        places = await extractor.extract_places(text)
        
        print(f"🗺️ 抽出結果: {len(places)}件")
        for place in places:
            print(f"  - {place.name} (信頼度: {place.confidence:.2f}, ソース: {place.source})")
    
    asyncio.run(run())

@cli.command()
@click.option('--force-refresh', is_flag=True, help='強制的に全作家情報を更新')
@click.option('--section', help='特定セクションのみ同期（ア、カ、サ等）')
def sync_authors(force_refresh: bool, section: Optional[str]):
    """青空文庫作家リストをデータベースに同期"""
    import asyncio
    from ..extractors.author_database_service import AuthorDatabaseService
    
    print("🔄 作家リスト同期開始")
    
    async def run_sync():
        service = AuthorDatabaseService()
        
        if section:
            print(f"📚 セクション '{section}' の作家を同期中...")
            # セクション別同期は将来の拡張として実装
            print("⚠️ セクション別同期は現在未対応です。全体同期を実行します。")
        
        result = await service.sync_all_authors(force_refresh=force_refresh)
        
        if result['success']:
            print("\n✅ 作家リスト同期完了")
        else:
            print(f"\n❌ 作家リスト同期失敗: {result.get('error', '不明なエラー')}")
            exit(1)
    
    asyncio.run(run_sync())

@cli.command()
@click.argument('search_term')
@click.option('--limit', default=20, help='検索結果の最大件数')
@click.option('--section', help='検索対象セクション')
def search_authors(search_term: str, limit: int, section: Optional[str]):
    """作家名検索"""
    import asyncio
    from ..extractors.author_database_service import AuthorDatabaseService
    
    async def run_search():
        service = AuthorDatabaseService()
        
        if section:
            print(f"📚 セクション '{section}' で '{search_term}' を検索...")
            authors = await service.get_authors_by_section(section)
            # フィルタリング
            filtered_authors = [a for a in authors if search_term in a['name']][:limit]
        else:
            print(f"📚 '{search_term}' を検索...")
            filtered_authors = await service.search_authors(search_term, limit)
        
        if filtered_authors:
            print(f"\n📊 検索結果: {len(filtered_authors)}名")
            print("=" * 80)
            
            for i, author in enumerate(filtered_authors, 1):
                name = author['name']
                kana = author.get('name_kana', '')
                works_count = author.get('works_count', 0)
                copyright_status = author.get('copyright_status', 'unknown')
                section = author.get('section', '')
                
                status_icon = "⚖️" if copyright_status == "active" else "📚"
                kana_text = f" ({kana})" if kana else ""
                
                print(f"{i:3}. {status_icon} {name}{kana_text}")
                print(f"     作品数: {works_count}, セクション: {section}")
                
                if author.get('aozora_url'):
                    print(f"     URL: {author['aozora_url']}")
                print()
        else:
            print(f"❌ '{search_term}' に該当する作家が見つかりませんでした")
    
    asyncio.run(run_search())

@cli.command()
@click.option('--section', help='特定セクションの統計')
@click.option('--copyright', help='著作権状態別統計')
def author_stats(section: Optional[str], copyright: Optional[str]):
    """作家統計表示"""
    import asyncio
    from ..extractors.author_database_service import AuthorDatabaseService
    
    async def run_stats():
        service = AuthorDatabaseService()
        stats = await service.get_author_statistics()
        
        if not stats:
            print("❌ 統計情報を取得できませんでした")
            return
        
        print("📊 青空文庫作家統計")
        print("=" * 60)
        
        # 基本統計
        print(f"総作家数: {stats.get('total_authors', 0):,}名")
        print(f"総作品数: {stats.get('total_works', 0):,}作品")
        print(f"平均作品数: {stats.get('average_works_per_author', 0)}作品/作家")
        print(f"最終同期: {stats.get('last_sync', 'N/A')}")
        
        # 著作権状態別統計
        copyright_stats = stats.get('copyright_stats', {})
        if copyright_stats:
            print(f"\n⚖️ 著作権状態別統計:")
            for status, count in copyright_stats.items():
                status_name = {
                    'expired': '著作権満了',
                    'active': '著作権存続',
                    'unknown': '不明'
                }.get(status, status)
                print(f"  {status_name}: {count:,}名")
        
        # セクション別統計
        section_stats = stats.get('section_stats', {})
        if section_stats and not section:
            print(f"\n📚 セクション別統計:")
            for sec, count in sorted(section_stats.items()):
                print(f"  {sec}: {count:,}名")
        elif section and section in section_stats:
            print(f"\n📚 セクション '{section}' 統計:")
            print(f"  作家数: {section_stats[section]:,}名")
        
        # 作品数上位作家
        top_authors = stats.get('top_authors', [])
        if top_authors:
            print(f"\n🏆 作品数上位10名:")
            for i, (name, count) in enumerate(top_authors, 1):
                print(f"  {i:2}. {name}: {count}作品")
    
    asyncio.run(run_stats())

@cli.command()
def list_sections():
    """利用可能なセクション一覧"""
    sections = {
        'ア': 'あ行（ア〜オ）',
        'カ': 'か行（カ〜コ）',
        'サ': 'さ行（サ〜ソ）',
        'タ': 'た行（タ〜ト）',
        'ナ': 'な行（ナ〜ノ）',
        'ハ': 'は行（ハ〜ホ）',
        'マ': 'ま行（マ〜モ）',
        'ヤ': 'や行（ヤ〜ヨ）',
        'ラ': 'ら行（ラ〜ロ）',
        'ワ': 'わ行（ワ〜ン）',
        'その他': '外国人作家等'
    }
    
    print("📚 青空文庫作家セクション一覧")
    print("=" * 40)
    
    for section, description in sections.items():
        print(f"  {section}: {description}")
    
    print(f"\n💡 使用例:")
    print(f"  bungo-map sync-authors --section ア")
    print(f"  bungo-map search-authors 夏目 --section ナ")
    print(f"  bungo-map author-stats --section ア")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    cli()
