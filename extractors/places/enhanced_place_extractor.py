#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高精度地名抽出システム v3.0
地名マスター優先設計による効率的な抽出・管理システム

新機能:
1. 抽出時点でのマスター検索・参照
2. 重複ジオコーディング完全回避
3. AI検証統合による高品質保証
4. キャッシュ機能による高速処理
"""

import sys
import os
import sqlite3
import spacy
import re
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# パス設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .place_master_manager import PlaceMasterManagerV2


class EnhancedPlaceExtractorV3:
    """高精度地名抽出システム v3.0"""
    
    def __init__(self):
        # GinZA初期化
        try:
            self.nlp = spacy.load('ja_ginza')
        except Exception as e:
            print(f"⚠️ GinZAロードエラー: {e}")
            self.nlp = None
        
        # 地名マスターマネージャ
        self.place_manager = PlaceMasterManagerV2()
        
        # 統計情報
        self.stats = {
            'sentences_processed': 0,
            'places_extracted': 0,
            'masters_reused': 0,
            'masters_created': 0,
            'geocoding_skipped': 0,
            'processing_time': 0,
            'ai_validations': 0
        }
        
        # 地名パターン
        self.place_patterns = [
            r'[東西南北]?[都道府県市区町村郡]',
            r'.*[山川島湖港駅]$',
            r'.*[神社寺院]$',
            r'.*[大学高校]$',
            r'[0-9]*[丁目番地号]',
        ]
        
        print("🚀 高精度地名抽出システム v3.0 初期化完了")
        print("✅ 地名マスター優先設計による効率的な処理が可能です")
    
    def extract_places_from_sentence(self, sentence_id: int, sentence_text: str, 
                                   work_title: str = None) -> List[Dict]:
        """センテンスから地名抽出（マスター優先処理）"""
        start_time = time.time()
        extracted_places = []
        
        try:
            if not self.nlp:
                print("⚠️ GinZAが利用できません")
                return []
            
            self.stats['sentences_processed'] += 1
            
            # GinZAによる自然言語処理
            doc = self.nlp(sentence_text)
            
            # 地名候補抽出
            place_candidates = []
            
            # 1. 固有表現抽出
            for ent in doc.ents:
                if ent.label_ in ['GPE', 'LOC', 'FAC']:  # 地政学的実体、場所、施設
                    place_candidates.append({
                        'text': ent.text,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'label': ent.label_,
                        'confidence': 0.8
                    })
            
            # 2. 品詞ベース抽出
            for token in doc:
                if token.pos_ == 'PROPN':  # 固有名詞
                    # 地名パターンマッチング
                    for pattern in self.place_patterns:
                        if re.search(pattern, token.text):
                            place_candidates.append({
                                'text': token.text,
                                'start': token.idx,
                                'end': token.idx + len(token.text),
                                'label': 'PATTERN',
                                'confidence': 0.6
                            })
                            break
            
            # 3. 複合地名抽出
            place_candidates.extend(self.extract_compound_places(doc))
            
            # 重複除去
            unique_candidates = self.deduplicate_candidates(place_candidates)
            
            # 各候補をマスターシステムで処理
            for candidate in unique_candidates:
                place_text = candidate['text']
                
                print(f"🔍 地名候補処理: {place_text}")
                
                # マスター検索・登録
                master_id = self.place_manager.extract_and_register_place(
                    place_text=place_text,
                    sentence_id=sentence_id,
                    sentence_text=sentence_text,
                    extraction_method='ginza_v3'
                )
                
                if master_id:
                    place_info = {
                        'master_id': master_id,
                        'place_text': place_text,
                        'start_position': candidate['start'],
                        'end_position': candidate['end'],
                        'extraction_method': 'ginza_v3',
                        'confidence': candidate['confidence'],
                        'label': candidate['label']
                    }
                    
                    extracted_places.append(place_info)
                    self.stats['places_extracted'] += 1
                    
                    print(f"✅ 地名登録完了: {place_text} (master_id: {master_id})")
                else:
                    print(f"⚠️ 地名登録失敗: {place_text}")
            
            processing_time = time.time() - start_time
            self.stats['processing_time'] += processing_time
            
            print(f"📊 センテンス処理完了: {len(extracted_places)}件の地名抽出 ({processing_time:.3f}秒)")
            
            return extracted_places
            
        except Exception as e:
            print(f"❌ 地名抽出エラー (sentence_id: {sentence_id}): {e}")
            return []
    
    def extract_compound_places(self, doc) -> List[Dict]:
        """複合地名抽出（「東京都千代田区」等）"""
        compounds = []
        
        try:
            # 連続する地名要素を検出
            for i, token in enumerate(doc):
                if i < len(doc) - 1:
                    current = token.text
                    next_token = doc[i + 1].text
                    
                    # 都道府県 + 市区町村パターン
                    if (re.search(r'[都道府県]$', current) and 
                        re.search(r'[市区町村]', next_token)):
                        
                        compound_text = current + next_token
                        compounds.append({
                            'text': compound_text,
                            'start': token.idx,
                            'end': doc[i + 1].idx + len(next_token),
                            'label': 'COMPOUND',
                            'confidence': 0.9
                        })
            
            return compounds
            
        except Exception as e:
            print(f"⚠️ 複合地名抽出エラー: {e}")
            return []
    
    def deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """地名候補の重複除去"""
        unique_candidates = []
        seen_texts = set()
        
        # 信頼度の高い順にソート
        sorted_candidates = sorted(candidates, key=lambda x: x['confidence'], reverse=True)
        
        for candidate in sorted_candidates:
            text = candidate['text'].strip()
            
            if text and text not in seen_texts and len(text) > 1:
                # 基本的なフィルタリング
                if not self.is_invalid_place_candidate(text):
                    unique_candidates.append(candidate)
                    seen_texts.add(text)
        
        return unique_candidates
    
    def is_invalid_place_candidate(self, text: str) -> bool:
        """無効な地名候補の判定"""
        invalid_patterns = [
            r'^[0-9]+$',  # 数字のみ
            r'^[ぁ-ん]+$',  # ひらがなのみ
            r'^[一二三四五六七八九十]+$',  # 漢数字のみ
            r'^[、。！？]+$',  # 記号のみ
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, text):
                return True
        
        # 一般的な非地名語
        non_place_words = {
            'こと', 'もの', 'とき', 'ところ', 'あの', 'その', 'この',
            '私', '僕', '君', '彼', '彼女', '先生', '様', 'さん',
            '今日', '明日', '昨日', '今', '後', '前', '時'
        }
        
        return text in non_place_words
    
    def process_work_sentences(self, work_id: int, work_title: str = None) -> Dict:
        """作品の全センテンスから地名抽出"""
        print(f"📚 作品地名抽出開始: {work_title or work_id}")
        start_time = time.time()
        
        try:
            # センテンス取得
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'bungo_map.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT sentence_id, sentence_text 
                FROM sentences 
                WHERE work_id = ?
                ORDER BY sentence_order
            """, (work_id,))
            
            sentences = cursor.fetchall()
            conn.close()
            
            print(f"📊 処理対象センテンス: {len(sentences)}件")
            
            work_stats = {
                'work_id': work_id,
                'work_title': work_title,
                'total_sentences': len(sentences),
                'processed_sentences': 0,
                'total_places': 0,
                'unique_places': 0,
                'processing_time': 0
            }
            
            all_extracted_places = []
            unique_masters = set()
            
            for sentence_id, sentence_text in sentences:
                places = self.extract_places_from_sentence(
                    sentence_id=sentence_id,
                    sentence_text=sentence_text,
                    work_title=work_title
                )
                
                all_extracted_places.extend(places)
                work_stats['processed_sentences'] += 1
                work_stats['total_places'] += len(places)
                
                # ユニーク地名カウント
                for place in places:
                    unique_masters.add(place['master_id'])
                
                # 進捗表示
                if work_stats['processed_sentences'] % 100 == 0:
                    print(f"⏳ 進捗: {work_stats['processed_sentences']}/{len(sentences)} センテンス処理完了")
            
            work_stats['unique_places'] = len(unique_masters)
            work_stats['processing_time'] = time.time() - start_time
            
            print(f"✅ 作品地名抽出完了: {work_title or work_id}")
            print(f"📊 結果: {work_stats['total_places']}件の地名、{work_stats['unique_places']}のユニーク地名")
            print(f"⏱️ 処理時間: {work_stats['processing_time']:.2f}秒")
            
            return work_stats
            
        except Exception as e:
            print(f"❌ 作品地名抽出エラー: {e}")
            return {}
    
    def get_extraction_statistics(self) -> Dict:
        """抽出統計情報取得"""
        stats = self.stats.copy()
        stats.update(self.place_manager.get_master_statistics())
        
        return stats
    
    def print_statistics(self):
        """統計情報表示"""
        print("\n" + "="*60)
        print("📊 地名抽出システム v3.0 統計")
        print("="*60)
        
        print(f"処理センテンス数: {self.stats['sentences_processed']:,}")
        print(f"抽出地名数: {self.stats['places_extracted']:,}")
        print(f"総処理時間: {self.stats['processing_time']:.2f}秒")
        
        if self.stats['sentences_processed'] > 0:
            avg_time = self.stats['processing_time'] / self.stats['sentences_processed']
            print(f"平均処理時間: {avg_time:.3f}秒/センテンス")
        
        # マスター統計も表示
        self.place_manager.print_statistics()


def main():
    """テスト実行"""
    extractor = EnhancedPlaceExtractorV3()
    
    # テストセンテンス
    test_sentence = "私は東京から京都へ行き、金閣寺を見学した。"
    
    print("🧪 地名抽出システム v3.0 テスト")
    print(f"テストセンテンス: {test_sentence}")
    
    places = extractor.extract_places_from_sentence(
        sentence_id=999999,  # テスト用ID
        sentence_text=test_sentence
    )
    
    print(f"\n📍 抽出結果: {len(places)}件")
    for place in places:
        print(f"  - {place['place_text']} (master_id: {place['master_id']})")
    
    extractor.print_statistics()


if __name__ == "__main__":
    main() 