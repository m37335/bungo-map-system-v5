#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
シンプル地名抽出機能

センテンスから地名を抽出し、データベースに保存する実用的な機能。
正規表現ベースの確実な抽出に特化。
"""

import re
import sqlite3
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import argparse

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ExtractedPlace:
    """抽出された地名の情報"""
    name: str
    canonical_name: str
    place_type: str
    confidence: float
    position: int
    matched_text: str
    context_before: str
    context_after: str
    extraction_method: str

class SimplePlaceExtractor:
    """シンプル地名抽出クラス"""
    
    def __init__(self):
        self._init_patterns()
        logger.info("🗺️ シンプル地名抽出システム初期化完了")
        
    def _init_patterns(self):
        """地名抽出用パターンを初期化"""
        
        # 都道府県パターン（県・府・都・道を含む）
        self.prefecture_list = [
            '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
            '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
            '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県',
            '岐阜県', '静岡県', '愛知県', '三重県',
            '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
            '鳥取県', '島根県', '岡山県', '広島県', '山口県',
            '徳島県', '香川県', '愛媛県', '高知県',
            '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
        ]
        
        # 主要都市・有名地名（確実に地名として認識できるもの）
        self.famous_places = [
            # 東京周辺
            '銀座', '新宿', '渋谷', '上野', '浅草', '品川', '池袋', '新橋', '有楽町',
            '神田', '日本橋', '本郷', '赤坂', '青山', '表参道', '恵比寿', '代官山',
            
            # 関東主要都市
            '横浜', '川崎', '千葉', '船橋', '柏', '鎌倉', '湘南', '箱根', '熱海',
            '宇都宮', '高崎', '水戸', 'つくば',
            
            # 関西
            '京都', '大阪', '神戸', '奈良', '和歌山', '姫路', 
            
            # その他主要都市
            '札幌', '仙台', '名古屋', '金沢', '福岡', '長崎', '熊本', '鹿児島',
            '広島', '岡山', '高松', '松山', '高知',
            
            # 歴史地名
            '江戸', '甲斐', '信濃', '近江', '山城', '大和', '河内', '和泉', '摂津',
            '伊勢', '尾張', '三河', '駿河', '遠江', '相模', '武蔵', '下野',
            '常陸', '下総', '上総', '安房', '越後', '越中', '越前', '加賀', '能登',
            
            # 自然地名
            '富士山', '琵琶湖', '瀬戸内海', '東京湾', '相模湾', '駿河湾'
        ]
        
        # 市区町村パターン（一般的な市区町村名）
        self.city_suffixes = ['市', '区', '町', '村']
        self.gun_suffixes = ['郡']
        
    def extract_places_from_text(self, text: str) -> List[ExtractedPlace]:
        """テキストから地名を抽出"""
        extracted_places = []
        
        # 1. 都道府県抽出
        for prefecture in self.prefecture_list:
            places = self._extract_by_exact_match(text, prefecture, '都道府県', 0.95)
            extracted_places.extend(places)
            
        # 2. 有名地名抽出
        for place_name in self.famous_places:
            places = self._extract_by_exact_match(text, place_name, '有名地名', 0.90)
            extracted_places.extend(places)
            
        # 3. 市区町村パターン抽出
        city_places = self._extract_cities(text)
        extracted_places.extend(city_places)
        
        # 4. 郡パターン抽出
        gun_places = self._extract_guns(text)
        extracted_places.extend(gun_places)
        
        # 重複除去とソート
        extracted_places = self._remove_duplicates(extracted_places)
        extracted_places.sort(key=lambda x: x.position)
        
        return extracted_places
        
    def _extract_by_exact_match(self, text: str, place_name: str, place_type: str, confidence: float) -> List[ExtractedPlace]:
        """完全一致による地名抽出"""
        places = []
        
        # エスケープして完全一致検索
        pattern = re.escape(place_name)
        
        for match in re.finditer(pattern, text):
            position = match.start()
            
            # 前後のコンテキスト取得
            context_before = text[max(0, position-15):position]
            context_after = text[position+len(place_name):position+len(place_name)+15]
            
            place = ExtractedPlace(
                name=place_name,
                canonical_name=self._normalize_place_name(place_name),
                place_type=place_type,
                confidence=confidence,
                position=position,
                matched_text=place_name,
                context_before=context_before,
                context_after=context_after,
                extraction_method='exact_match'
            )
            
            places.append(place)
            
        return places
        
    def _extract_cities(self, text: str) -> List[ExtractedPlace]:
        """市区町村パターンで地名抽出"""
        places = []
        
        # パターン: 2-8文字の漢字 + 市区町村
        for suffix in self.city_suffixes:
            pattern = f'[一-龯]{{2,8}}{re.escape(suffix)}'
            
            for match in re.finditer(pattern, text):
                name = match.group()
                position = match.start()
                
                # 明らかに地名でないものを除外
                if self._is_likely_place_name(name):
                    context_before = text[max(0, position-15):position]
                    context_after = text[position+len(name):position+len(name)+15]
                    
                    place = ExtractedPlace(
                        name=name,
                        canonical_name=self._normalize_place_name(name),
                        place_type='市区町村',
                        confidence=0.80,
                        position=position,
                        matched_text=name,
                        context_before=context_before,
                        context_after=context_after,
                        extraction_method='pattern_match'
                    )
                    
                    places.append(place)
                    
        return places
        
    def _extract_guns(self, text: str) -> List[ExtractedPlace]:
        """郡パターンで地名抽出"""
        places = []
        
        # パターン: 2-6文字の漢字 + 郡
        pattern = r'[一-龯]{2,6}郡'
        
        for match in re.finditer(pattern, text):
            name = match.group()
            position = match.start()
            
            context_before = text[max(0, position-15):position]
            context_after = text[position+len(name):position+len(name)+15]
            
            place = ExtractedPlace(
                name=name,
                canonical_name=self._normalize_place_name(name),
                place_type='郡',
                confidence=0.75,
                position=position,
                matched_text=name,
                context_before=context_before,
                context_after=context_after,
                extraction_method='pattern_match'
            )
            
            places.append(place)
            
        return places
        
    def _is_likely_place_name(self, name: str) -> bool:
        """地名らしい名前かどうかの簡単な判定"""
        # 除外パターン
        exclude_patterns = [
            r'.*[店屋社会館]$',  # 店舗名、施設名
            r'.*[部課室科]$',    # 組織名
            r'^[一二三四五六七八九十]',  # 数字で始まる
        ]
        
        for pattern in exclude_patterns:
            if re.match(pattern, name):
                return False
                
        return True
        
    def _normalize_place_name(self, name: str) -> str:
        """地名を正規化"""
        # 都道府県の正規化
        normalized = re.sub(r'[県府都道]$', '', name)
        return normalized if normalized else name
        
    def _remove_duplicates(self, places: List[ExtractedPlace]) -> List[ExtractedPlace]:
        """重複する地名を除去"""
        seen = set()
        unique_places = []
        
        for place in places:
            # 同一位置の同一地名は重複とみなす
            key = (place.canonical_name, place.position)
            if key not in seen:
                seen.add(key)
                unique_places.append(place)
                
        return unique_places
        
    def save_places_to_db(self, sentence_id: int, places: List[ExtractedPlace]) -> int:
        """抽出された地名をデータベースに保存"""
        if not places:
            return 0
            
        saved_count = 0
        
        for place in places:
            try:
                # 地名マスターテーブルに追加
                place_id = self._get_or_create_place(place)
                
                # センテンス-地名関連テーブルに保存
                self._save_sentence_place_relation(sentence_id, place_id, place)
                
                saved_count += 1
                logger.debug(f"地名保存: {place.name} (センテンス {sentence_id})")
                
            except Exception as e:
                logger.error(f"地名保存エラー: {place.name} - {e}")
                
        return saved_count
        
    def _get_or_create_place(self, place: ExtractedPlace) -> int:
        """地名マスターテーブルから地名IDを取得、存在しない場合は作成"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # 既存地名を検索
            cursor.execute("""
                SELECT place_id FROM places 
                WHERE canonical_name = ? OR place_name = ?
            """, (place.canonical_name, place.name))
            
            result = cursor.fetchone()
            if result:
                return result[0]
                
            # 新規地名を作成
            cursor.execute("""
                INSERT INTO places (
                    place_name, canonical_name, place_type, confidence,
                    mention_count, source_system, verification_status,
                    created_at
                ) VALUES (?, ?, ?, ?, 1, 'simple_place_extractor', 'auto_extracted', ?)
            """, (
                place.name, place.canonical_name, place.place_type, 
                place.confidence, datetime.now()
            ))
            
            place_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"新規地名登録: {place.name} (ID: {place_id}, タイプ: {place.place_type})")
            return place_id
            
        finally:
            conn.close()
            
    def _save_sentence_place_relation(self, sentence_id: int, place_id: int, place: ExtractedPlace):
        """センテンス-地名関連を保存"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO sentence_places (
                    sentence_id, place_id, extraction_method, confidence,
                    position_in_sentence, context_before, context_after,
                    matched_text, verification_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'auto_extracted', ?)
            """, (
                sentence_id, place_id, place.extraction_method, place.confidence,
                place.position, place.context_before, place.context_after,
                place.matched_text, datetime.now()
            ))
            
            conn.commit()
            
        finally:
            conn.close()
            
    def process_sentences_batch(self, limit: Optional[int] = None) -> Dict[str, int]:
        """センテンスを一括処理して地名抽出を実行"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # 未処理のセンテンスを取得
            query = """
                SELECT s.sentence_id, s.sentence_text 
                FROM sentences s
                LEFT JOIN sentence_places sp ON s.sentence_id = sp.sentence_id
                WHERE sp.sentence_id IS NULL
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor.execute(query)
            sentences = cursor.fetchall()
            
            logger.info(f"🎯 処理対象センテンス: {len(sentences)}件")
            
            stats = {
                'processed_sentences': 0,
                'extracted_places': 0,
                'saved_places': 0,
                'errors': 0
            }
            
            for sentence_id, sentence_text in sentences:
                try:
                    # 地名抽出
                    places = self.extract_places_from_text(sentence_text)
                    
                    # データベース保存
                    saved_count = self.save_places_to_db(sentence_id, places)
                    
                    stats['processed_sentences'] += 1
                    stats['extracted_places'] += len(places)
                    stats['saved_places'] += saved_count
                    
                    if len(places) > 0:
                        logger.info(f"✅ センテンス {sentence_id}: {len(places)}件抽出 → {saved_count}件保存")
                        for place in places:
                            logger.debug(f"   - {place.name} ({place.place_type}, {place.confidence:.2f})")
                        
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"❌ センテンス {sentence_id} 処理エラー: {e}")
                    
            return stats
            
        finally:
            conn.close()
            
    def get_statistics(self) -> Dict[str, any]:
        """地名抽出の統計情報を取得"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) FROM sentences")
            stats['total_sentences'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT sentence_id) FROM sentence_places")
            stats['processed_sentences'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM places")
            stats['total_places'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sentence_places")
            stats['total_relations'] = cursor.fetchone()[0]
            
            # 地名種別統計
            cursor.execute("""
                SELECT place_type, COUNT(*) 
                FROM places 
                GROUP BY place_type
                ORDER BY COUNT(*) DESC
            """)
            stats['place_types'] = dict(cursor.fetchall())
            
            # 抽出手法統計
            cursor.execute("""
                SELECT extraction_method, COUNT(*) 
                FROM sentence_places 
                GROUP BY extraction_method
                ORDER BY COUNT(*) DESC
            """)
            stats['extraction_methods'] = dict(cursor.fetchall())
            
            # 処理率
            if stats['total_sentences'] > 0:
                stats['processing_rate'] = stats['processed_sentences'] / stats['total_sentences'] * 100
            else:
                stats['processing_rate'] = 0
                
            return stats
            
        finally:
            conn.close()

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='シンプル地名抽出システム')
    parser.add_argument('--limit', type=int, help='処理するセンテンス数の上限')
    parser.add_argument('--stats-only', action='store_true', help='統計情報のみ表示')
    
    args = parser.parse_args()
    
    extractor = SimplePlaceExtractor()
    
    # 統計情報表示
    print("=== 🗺️  地名抽出システム統計 ===")
    stats = extractor.get_statistics()
    print(f"総センテンス数: {stats['total_sentences']:,}")
    print(f"処理済みセンテンス数: {stats['processed_sentences']:,}")
    print(f"処理率: {stats['processing_rate']:.1f}%")
    print(f"抽出済み地名数: {stats['total_places']:,}")
    print(f"地名-センテンス関連数: {stats['total_relations']:,}")
    
    if stats.get('place_types'):
        print("\n📍 地名種別:")
        for place_type, count in stats['place_types'].items():
            print(f"  {place_type}: {count}件")
    
    if stats.get('extraction_methods'):
        print("\n🔧 抽出手法:")
        for method, count in stats['extraction_methods'].items():
            print(f"  {method}: {count}件")
    
    if args.stats_only:
        return
    
    # 地名抽出処理実行
    print("\n=== 🚀 地名抽出処理開始 ===")
    result = extractor.process_sentences_batch(limit=args.limit)
    
    print("\n=== 📊 処理結果 ===")
    print(f"処理センテンス数: {result['processed_sentences']:,}")
    print(f"抽出地名数: {result['extracted_places']:,}")
    print(f"保存地名数: {result['saved_places']:,}")
    print(f"エラー数: {result['errors']:,}")
    
    # 更新後統計
    if result['processed_sentences'] > 0:
        print("\n=== 📈 更新後統計 ===")
        final_stats = extractor.get_statistics()
        print(f"総センテンス数: {final_stats['total_sentences']:,}")
        print(f"処理済みセンテンス数: {final_stats['processed_sentences']:,}")
        print(f"処理率: {final_stats['processing_rate']:.1f}%")
        print(f"抽出済み地名数: {final_stats['total_places']:,}")
        
        if final_stats.get('place_types'):
            print("\n📍 地名種別（更新後）:")
            for place_type, count in final_stats['place_types'].items():
                print(f"  {place_type}: {count}件")

if __name__ == "__main__":
    main() 