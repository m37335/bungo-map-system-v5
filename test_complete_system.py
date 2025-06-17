#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完全なデータ処理システムテスト
改良されたシステムの動作確認
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# パス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.text_processor import TextProcessor
from extractors.place_extractor import EnhancedPlaceExtractor
from core.config import init_config

async def test_text_processing():
    """テキスト処理のテスト"""
    print("\n🧹 テキスト処理テスト")
    print("-" * 40)
    
    # サンプルテキスト（青空文庫風）
    sample_text = """
    <ruby><rb>夏目</rb><rp>（</rp><rt>なつめ</rt><rp>）</rp></ruby>漱石の「こころ」は、
    東京帝国大学の学生が、鎌倉で出会った<ruby><rb>先生</rb><rp>（</rp><rt>せんせい</rt><rp>）</rp></ruby>との
    交流を描いた作品である。《注釈》物語は明治時代の東京を舞台に展開される。
    ［＃ここから本文］
    私は<ruby><rb>銀座</rb><rp>（</rp><rt>ぎんざ</rt><rp>）</rp></ruby>を歩いていた。
    """
    
    processor = TextProcessor()
    
    # テキストクリーニング
    cleaned_text, stats = processor.clean_aozora_text(sample_text)
    
    print(f"✅ 元テキスト: {len(sample_text)}文字")
    print(f"✅ クリーニング後: {len(cleaned_text)}文字")
    print(f"✅ 除去されたrubyタグ: {stats.removed_ruby_count}個")
    print(f"✅ 除去されたHTMLタグ: {stats.removed_html_count}個")
    print(f"✅ 除去された注釈: {stats.removed_annotation_count}個")
    
    # 文分割
    sentences = processor.split_into_sentences(cleaned_text)
    print(f"✅ 分割された文数: {len(sentences)}文")
    
    # 品質検証
    quality = processor.validate_text_quality(cleaned_text)
    print(f"✅ 品質スコア: {quality['quality_score']:.2f}")
    
    # 統計情報
    stats_info = processor.get_text_statistics(cleaned_text)
    print(f"✅ 統計: {stats_info}")
    
    print("\n🔍 クリーニング後テキスト:")
    print(cleaned_text[:200] + "..." if len(cleaned_text) > 200 else cleaned_text)

async def test_place_extraction():
    """地名抽出のテスト"""
    print("\n🗺️ 地名抽出テスト")
    print("-" * 40)
    
    # サンプルテキスト
    sample_text = """
    私は東京駅から新幹線に乗り、京都に向かった。
    京都府京都市の清水寺を見学した後、大阪府大阪市の通天閣を見に行った。
    奈良県奈良市の東大寺も素晴らしかった。
    富士山の麓の河口湖で一泊し、横浜の中華街で食事をした。
    最後に神奈川県鎌倉市の大仏を見て帰った。
    """
    
    extractor = EnhancedPlaceExtractor()
    
    # 地名抽出実行
    places = await extractor.extract_places(sample_text, "テスト作品", "テスト作者")
    
    print(f"✅ 抽出された地名数: {len(places)}件")
    print("\n📍 抽出結果:")
    
    for i, place in enumerate(places, 1):
        print(f"  {i}. {place.name}")
        print(f"     信頼度: {place.confidence:.2f}")
        print(f"     ソース: {place.source}")
        print(f"     カテゴリ: {place.category}")
        print(f"     文脈: {place.context[:50]}..." if len(place.context) > 50 else f"     文脈: {place.context}")
        print()

async def test_integration():
    """統合テスト"""
    print("\n🔄 統合テスト")
    print("-" * 40)
    
    # 青空文庫風の完全なサンプル
    aozora_sample = """
    <ruby><rb>夏目</rb><rp>（</rp><rt>なつめ</rt><rp>）</rp></ruby>漱石
    
    こころ
    
    ［＃ここから本文］
    
    私はその人を常に先生と呼んでいた。だからここでもただ先生と書くだけで本名は打ち明けない。
    これは世間を憚（はば）かる遠慮というよりも、その方が私にとって自然だからである。
    私はその人の記憶を呼び起こすごとに、すぐ「先生」といいたくなる。
    筆を執（と）っても心持ちは同じ事である。よそよそしい頭文字などはとても使う気になれない。
    
    私が先生と知り合いになったのは鎌倉である。その時私はまだ若い大学生であった。
    暑中休暇を利用して海水浴に行った友達からぽつんと取り残された。
    友達はみな帰ってしまったあとで、私は一人で海岸にいた。
    
    底本：岩波文庫
    入力：青空文庫
    校正：青空文庫
    """
    
    # 1. テキスト処理
    processor = TextProcessor()
    cleaned_text, stats = processor.clean_aozora_text(aozora_sample)
    sentences = processor.split_into_sentences(cleaned_text)
    
    print(f"✅ テキスト処理完了")
    print(f"   元文字数: {len(aozora_sample):,}")
    print(f"   処理後文字数: {len(cleaned_text):,}")
    print(f"   文数: {len(sentences)}")
    
    # 2. 地名抽出
    extractor = EnhancedPlaceExtractor()
    places = await extractor.extract_places(cleaned_text, "こころ", "夏目漱石")
    
    print(f"✅ 地名抽出完了")
    print(f"   抽出地名数: {len(places)}")
    
    # 3. 結果表示
    if places:
        print("\n📍 抽出された地名:")
        for place in places:
            print(f"   - {place.name} (信頼度: {place.confidence:.2f}, {place.source})")
    
    print(f"\n✅ 統合テスト完了")

async def main():
    """メインテスト関数"""
    print("🗾 文豪ゆかり地図システム v4.0 - 完全システムテスト")
    print("=" * 80)
    
    # 設定初期化
    config = init_config()
    print("✅ 設定初期化完了")
    
    try:
        # 各テスト実行
        await test_text_processing()
        await test_place_extraction()
        await test_integration()
        
        print("\n🎉 全テスト完了！")
        print("=" * 80)
        print("✅ データ抽出・処理機能が正常に動作しています")
        
    except Exception as e:
        print(f"\n❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    asyncio.run(main()) 