from typing import List, Dict, Any, Optional, Tuple
import logging
import re
from dataclasses import dataclass
from ..ai.llm import LLMManager
from ..ai.nlp import NLPManager, NLPResult
import sqlite3
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class ExtractedPlace:
    """抽出された地名情報"""
    name: str
    context: str
    confidence: float
    source: str
    metadata: Dict[str, Any]
    position: int = 0
    sentence_index: int = 0
    category: str = ""
    matched_text: str = ""

class EnhancedPlaceExtractor:
    """強化版地名抽出エンジン（legacyからの改良統合版）"""
    
    def __init__(self):
        self.llm_manager = LLMManager()
        self.nlp_manager = NLPManager()
        self.db_manager = DatabaseManager()
        
        # 抽出レベルとその信頼度閾値
        self.extraction_levels = {
            "llm_context": 0.8,    # LLM文脈理解
            "famous_place": 0.7,   # 有名地名
            "complete_name": 0.95, # 完全地名（都道府県+市区町村）
            "city": 0.6,          # 市区町村
            "prefecture": 0.5,     # 都道府県
            "district": 0.4        # 郡
        }
        
        # 強化版正規表現パターン
        self.patterns = self._build_enhanced_patterns()
        
        logger.info("🗺️ 強化版地名抽出エンジン初期化完了")

    def _build_enhanced_patterns(self) -> List[Dict]:
        """強化された地名抽出パターン"""
        return [
            # 0. 完全地名（都道府県+市区町村） - 最高優先度
            {
                'pattern': r'(?<![一-龯])[北海青森岩手宮城秋田山形福島茨城栃木群馬埼玉千葉東京神奈川新潟富山石川福井山梨長野岐阜静岡愛知三重滋賀京都大阪兵庫奈良和歌山鳥取島根岡山広島山口徳島香川愛媛高知福岡佐賀長崎熊本大分宮崎鹿児島沖縄][都道府県][一-龯]{2,8}[市区町村](?![一-龯])',
                'category': '完全地名',
                'confidence': 0.98,
                'priority': 0
            },
            
            # 1. 都道府県（境界条件強化）
            {
                'pattern': r'(?<![一-龯])[北海青森岩手宮城秋田山形福島茨城栃木群馬埼玉千葉東京神奈川新潟富山石川福井山梨長野岐阜静岡愛知三重滋賀京都大阪兵庫奈良和歌山鳥取島根岡山広島山口徳島香川愛媛高知福岡佐賀長崎熊本大分宮崎鹿児島沖縄][都道府県](?![一-龯])',
                'category': '都道府県',
                'confidence': 0.95,
                'priority': 1
            },
            
            # 2. 市区町村（境界条件強化）
            {
                'pattern': r'(?<![一-龯])[一-龯]{2,6}[市区町村](?![一-龯])',
                'category': '市区町村',
                'confidence': 0.85,
                'priority': 2
            },
            
            # 3. 有名地名（明示リスト）
            {
                'pattern': r'(?:' + '|'.join([
                    '銀座', '新宿', '渋谷', '上野', '浅草', '品川', '池袋', '新橋', '有楽町',
                    '横浜', '川崎', '千葉', '船橋', '柏', '鎌倉', '湘南', '箱根',
                    '京都', '大阪', '神戸', '奈良', '江戸', '本郷', '神田', '日本橋',
                    '津軽', '松山', '四国', '九州', '本州', '北海道', '富士山', '琵琶湖'
                ]) + r')',
                'category': '有名地名',
                'confidence': 0.90,
                'priority': 3
            },
            
            # 4. 自然地名パターン
            {
                'pattern': r'(?<![一-龯])[一-龯]{1,4}[川山湖海峠谷野原島岬浦崎](?![一-龯])',
                'category': '自然地名',
                'confidence': 0.80,
                'priority': 4
            },
            
            # 5. 歴史地名・古い地名
            {
                'pattern': r'(?<![一-龯])[一-龯]{2,5}[国郡藩村宿駅関所城](?![一-龯])',
                'category': '歴史地名',
                'confidence': 0.75,
                'priority': 5
            }
        ]

    async def extract_places(
        self,
        text: str,
        work_title: str = "",
        author_name: str = ""
    ) -> List[ExtractedPlace]:
        """地名の抽出（統合版）"""
        try:
            if not text or len(text) < 10:
                logger.warning(f"テキストが短すぎます: {len(text)}文字")
                return []
            
            # 1. 正規表現による高速抽出
            regex_places = self._extract_with_regex(text)
            
            # 2. NLPによる基本的な地名抽出
            nlp_result = self.nlp_manager.analyze_text(text)
            nlp_places = self._process_nlp_entities(nlp_result, text)
            
            # 3. LLMによる文脈理解と地名抽出（サンプルテキストのみ）
            sample_text = text[:2000] if len(text) > 2000 else text
            llm_places = await self.llm_manager.extract_places(sample_text)
            
            # 4. 地名の統合と重複除去
            all_places = regex_places + nlp_places + llm_places
            merged_places = self._merge_and_deduplicate_places(all_places)
            
            # 5. 文脈分析の追加
            if work_title or author_name:
                places_with_context = await self._add_context_analysis(
                    merged_places,
                    work_title,
                    author_name
                )
            else:
                places_with_context = merged_places
            
            logger.info(f"✅ 地名抽出完了: {len(places_with_context)}件")
            return places_with_context
            
        except Exception as e:
            logger.error(f"地名抽出エラー: {str(e)}")
            return []

    def _extract_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """正規表現による地名抽出"""
        all_matches = []
        sentences = self._split_into_sentences(text)
        
        for sentence_idx, sentence in enumerate(sentences):
            sentence_matches = self._extract_from_sentence(
                sentence, sentence_idx, sentences
            )
            # 重複排除処理
            deduplicated_matches = self._deduplicate_overlapping_matches(sentence_matches)
            all_matches.extend(deduplicated_matches)
        
        # 辞書からExtractedPlaceオブジェクトへの変換
        places = []
        for match in all_matches:
            places.append({
                'name': match['text'],
                'context': match['sentence'],
                'confidence': match['confidence'],
                'source': 'regex',
                'metadata': {
                    'category': match['category'],
                    'priority': match['priority'],
                    'method': f"regex_{match['category']}"
                },
                'position': match.get('start', 0),
                'sentence_index': match.get('sentence_index', 0),
                'category': match['category'],
                'matched_text': match['text']
            })
        
        return places

    def _extract_from_sentence(self, sentence: str, sentence_idx: int, sentences: List[str]) -> List[Dict]:
        """単一文からの地名抽出"""
        matches = []
        
        for pattern_info in self.patterns:
            pattern_matches = list(re.finditer(pattern_info['pattern'], sentence))
            
            for match in pattern_matches:
                place_name = match.group(0)
                
                # 前後の文脈取得
                before_text = sentences[sentence_idx - 1] if sentence_idx > 0 else ""
                after_text = sentences[sentence_idx + 1] if sentence_idx < len(sentences) - 1 else ""
                
                matches.append({
                    'text': place_name,
                    'start': match.start(),
                    'end': match.end(),
                    'sentence': sentence,
                    'before_text': before_text,
                    'after_text': after_text,
                    'sentence_index': sentence_idx,
                    'category': pattern_info['category'],
                    'confidence': pattern_info['confidence'],
                    'priority': pattern_info['priority']
                })
        
        return matches

    def _deduplicate_overlapping_matches(self, matches: List[Dict]) -> List[Dict]:
        """重複する地名の排除"""
        if not matches:
            return []
        
        # 優先度順でソート（priority 0が最高優先度）
        matches.sort(key=lambda x: (x['priority'], -x['confidence'], -len(x['text'])))
        
        deduplicated = []
        used_ranges = []
        
        for match in matches:
            match_range = (match['start'], match['end'])
            
            # 既に使用された範囲と重複するかチェック
            is_overlapping = any(
                self._ranges_overlap(match_range, used_range) 
                for used_range in used_ranges
            )
            
            if not is_overlapping:
                deduplicated.append(match)
                used_ranges.append(match_range)
        
        return deduplicated

    def _ranges_overlap(self, range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
        """2つの範囲が重複するかチェック"""
        start1, end1 = range1
        start2, end2 = range2
        return not (end1 <= start2 or end2 <= start1)

    def _process_nlp_entities(self, nlp_result: NLPResult, text: str) -> List[Dict[str, Any]]:
        """NLPエンティティの処理"""
        places = []
        for entity in nlp_result.entities:
            if entity["label"] in ["地名", "国・地域", "LOC", "GPE"]:
                context_start = max(0, entity["start"] - 50)
                context_end = min(len(text), entity["end"] + 50)
                context = text[context_start:context_end]
                
                places.append({
                    'name': entity["text"],
                    'context': context,
                    'confidence': entity["confidence"] * 0.8,  # NLP結果の信頼度調整
                    'source': 'nlp',
                    'metadata': {
                        'category': 'nlp_entity',
                        'original_label': entity["label"]
                    },
                    'position': entity["start"],
                    'sentence_index': 0,
                    'category': 'nlp_entity',
                    'matched_text': entity["text"]
                })
        return places

    def _merge_and_deduplicate_places(self, all_places: List[Dict[str, Any]]) -> List[ExtractedPlace]:
        """地名の統合と重複除去"""
        merged = {}
        
        for place in all_places:
            name = place['name']
            
            if name in merged:
                # 既存の地名の場合、信頼度の高い方を採用
                if place['confidence'] > merged[name].confidence:
                    merged[name] = ExtractedPlace(**place)
                else:
                    # メタデータの統合
                    if place['source'] not in merged[name].source:
                        merged[name].source += f"+{place['source']}"
            else:
                merged[name] = ExtractedPlace(**place)
        
        return list(merged.values())

    async def _add_context_analysis(
        self,
        places: List[ExtractedPlace],
        work_title: str,
        author_name: str
    ) -> List[ExtractedPlace]:
        """文脈分析の追加"""
        result = []
        
        for place in places:
            try:
                # 文脈分析の取得
                context_analysis = await self.llm_manager.analyze_place_context(
                    place.name,
                    work_title,
                    author_name
                )
                
                # 総合信頼度の計算
                confidence = self._calculate_enhanced_confidence(place, context_analysis)
                
                # メタデータの更新
                enhanced_place = ExtractedPlace(
                    name=place.name,
                    context=place.context,
                    confidence=confidence,
                    source=place.source,
                    metadata={
                        **place.metadata,
                        'context_analysis': context_analysis,
                        'enhanced': True
                    },
                    position=place.position,
                    sentence_index=place.sentence_index,
                    category=place.category,
                    matched_text=place.matched_text
                )
                
                result.append(enhanced_place)
                
            except Exception as e:
                logger.warning(f"文脈分析失敗: {place.name} - {e}")
                result.append(place)  # 元の地名をそのまま追加
        
        return result

    def _calculate_enhanced_confidence(self, place: ExtractedPlace, context_analysis: Dict) -> float:
        """強化版信頼度計算"""
        base_confidence = place.confidence
        
        # 抽出レベルに基づく調整
        level = self._determine_extraction_level(place.name)
        level_multiplier = self.extraction_levels.get(level, 0.5)
        
        # ソースに基づく調整
        source_multiplier = 1.0
        if 'regex' in place.source:
            source_multiplier += 0.1
        if 'nlp' in place.source:
            source_multiplier += 0.05
        if 'llm' in place.source:
            source_multiplier += 0.15
        
        # 文脈分析に基づく調整
        context_multiplier = 1.0
        if context_analysis:
            relevance = context_analysis.get('relevance', 0.5)
            context_multiplier = 1.0 + (relevance - 0.5) * 0.3
        
        # 最終信頼度計算
        final_confidence = base_confidence * level_multiplier * source_multiplier * context_multiplier
        
        return min(1.0, max(0.0, final_confidence))

    def _determine_extraction_level(self, place_name: str) -> str:
        """抽出レベルの判定"""
        # 都道府県の判定
        if place_name.endswith(("都", "道", "府", "県")):
            return "prefecture"
            
        # 市区町村の判定
        if place_name.endswith(("市", "区", "町", "村")):
            return "city"
            
        # 郡の判定
        if place_name.endswith("郡"):
            return "district"
            
        # 有名地名の判定
        famous_places = {"東京", "京都", "大阪", "名古屋", "横浜", "神戸", "江戸", "本郷", "神田"}
        if place_name in famous_places:
            return "famous_place"
            
        # デフォルトはLLM文脈理解
        return "llm_context"

    def _split_into_sentences(self, text: str) -> List[str]:
        """テキストを文に分割"""
        sentences = re.split(r'[。．！？!?]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def extract_places_from_text(self, text: str) -> List[ExtractedPlace]:
        """テキストから地名を抽出する"""
        extracted_places = []
        
        # 都道府県抽出
        for pattern in self.prefecture_patterns:
            places = self._extract_by_pattern(text, pattern, '都道府県', 0.9)
            extracted_places.extend(places)
            
        # 主要都市抽出
        for pattern in self.city_patterns:
            places = self._extract_by_pattern(text, pattern, '市区町村', 0.85)
            extracted_places.extend(places)
            
        # 歴史地名抽出
        for pattern in self.historical_patterns:
            places = self._extract_by_pattern(text, pattern, '歴史地名', 0.8)
            extracted_places.extend(places)
            
        # 有名地名抽出
        for pattern in self.famous_patterns:
            places = self._extract_by_pattern(text, pattern, '有名地名', 0.85)
            extracted_places.extend(places)
            
        # 区・郡抽出
        for pattern in self.district_patterns:
            places = self._extract_by_pattern(text, pattern, '郡', 0.7)
            extracted_places.extend(places)
            
        # 重複除去
        extracted_places = self._remove_duplicates(extracted_places)
        
        return extracted_places
        
    def _extract_by_pattern(self, text: str, pattern: str, place_type: str, confidence: float) -> List[ExtractedPlace]:
        """指定されたパターンで地名を抽出する"""
        places = []
        
        for match in re.finditer(pattern, text):
            name = match.group()
            position = match.start()
            
            # 前後のコンテキストを取得
            context_before = text[max(0, position-20):position]
            context_after = text[position+len(name):position+len(name)+20]
            
            place = ExtractedPlace(
                name=name,
                canonical_name=self._normalize_place_name(name),
                place_type=place_type,
                confidence=confidence,
                position=position,
                matched_text=name,
                context_before=context_before,
                context_after=context_after,
                extraction_method='regex'
            )
            
            places.append(place)
            
        return places
        
    def _normalize_place_name(self, name: str) -> str:
        """地名を正規化する"""
        # 「県」「府」「都」などを除去して正規化
        normalized = re.sub(r'[県府都道]$', '', name)
        return normalized if normalized else name
        
    def _remove_duplicates(self, places: List[ExtractedPlace]) -> List[ExtractedPlace]:
        """重複する地名を除去する"""
        seen = set()
        unique_places = []
        
        for place in places:
            key = (place.canonical_name, place.position)
            if key not in seen:
                seen.add(key)
                unique_places.append(place)
                
        return unique_places
        
    def extract_places_from_sentence(self, sentence_id: int, sentence_text: str) -> List[ExtractedPlace]:
        """センテンスから地名を抽出し、結果を返す"""
        logger.info(f"センテンス {sentence_id} から地名抽出開始")
        
        places = self.extract_places_from_text(sentence_text)
        
        logger.info(f"センテンス {sentence_id}: {len(places)}件の地名を抽出")
        
        return places
        
    def save_extracted_places(self, sentence_id: int, places: List[ExtractedPlace]) -> int:
        """抽出された地名をデータベースに保存する"""
        if not places:
            return 0
            
        saved_count = 0
        
        for place in places:
            try:
                # 地名マスターに追加（存在しない場合）
                place_id = self._get_or_create_place_master(place)
                
                # センテンス-地名関連を保存
                self._save_sentence_place_relation(sentence_id, place_id, place)
                
                saved_count += 1
                
            except Exception as e:
                logger.error(f"地名保存エラー: {place.name} - {e}")
                
        return saved_count
        
    def _get_or_create_place_master(self, place: ExtractedPlace) -> int:
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
                ) VALUES (?, ?, ?, ?, 1, 'place_extractor', 'auto_extracted', ?)
            """, (
                place.name, place.canonical_name, place.place_type, 
                place.confidence, datetime.now()
            ))
            
            place_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"新規地名登録: {place.name} (ID: {place_id})")
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
            
            logger.info(f"処理対象センテンス: {len(sentences)}件")
            
            stats = {
                'processed_sentences': 0,
                'extracted_places': 0,
                'saved_places': 0,
                'errors': 0
            }
            
            for sentence_id, sentence_text in sentences:
                try:
                    # 地名抽出
                    places = self.extract_places_from_sentence(sentence_id, sentence_text)
                    
                    # データベース保存
                    saved_count = self.save_extracted_places(sentence_id, places)
                    
                    stats['processed_sentences'] += 1
                    stats['extracted_places'] += len(places)
                    stats['saved_places'] += saved_count
                    
                    if len(places) > 0:
                        logger.info(f"センテンス {sentence_id}: {len(places)}件抽出")
                        
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"センテンス {sentence_id} 処理エラー: {e}")
                    
            return stats
            
        finally:
            conn.close()
            
    def get_extraction_statistics(self) -> Dict[str, any]:
        """地名抽出の統計情報を取得"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 総センテンス数
            cursor.execute("SELECT COUNT(*) FROM sentences")
            stats['total_sentences'] = cursor.fetchone()[0]
            
            # 処理済みセンテンス数
            cursor.execute("SELECT COUNT(DISTINCT sentence_id) FROM sentence_places")
            stats['processed_sentences'] = cursor.fetchone()[0]
            
            # 抽出された地名数
            cursor.execute("SELECT COUNT(*) FROM places")
            stats['total_places'] = cursor.fetchone()[0]
            
            # 地名-センテンス関連数
            cursor.execute("SELECT COUNT(*) FROM sentence_places")
            stats['total_relations'] = cursor.fetchone()[0]
            
            # 地名種別統計
            cursor.execute("""
                SELECT place_type, COUNT(*) 
                FROM places 
                GROUP BY place_type
            """)
            stats['place_types'] = dict(cursor.fetchall())
            
            # 抽出手法統計
            cursor.execute("""
                SELECT extraction_method, COUNT(*) 
                FROM sentence_places 
                GROUP BY extraction_method
            """)
            stats['extraction_methods'] = dict(cursor.fetchall())
            
            return stats
            
        finally:
            conn.close()

# 下位互換のためのエイリアス
PlaceExtractor = EnhancedPlaceExtractor
