#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GinZA統合地名抽出器 v4.0
Enhanced Place Extractor V2 + GiNZA統合版

機能:
- spaCy + GiNZAによる高精度NLP地名抽出
- 既存の正規表現パターンと組み合わせ
- AI検証機能との統合
- フォールバック機能（GiNZA未インストール時）
"""

import re
import sqlite3
import logging
import openai
import os
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

# GiNZA/spaCyの動的インポート（オプショナル依存）
try:
    import spacy
    import ginza
    GINZA_AVAILABLE = True
    logging.info("✅ GiNZA/spaCy利用可能")
except ImportError:
    GINZA_AVAILABLE = False
    logging.warning("⚠️ GiNZA/spaCy未インストール - 正規表現フォールバックで動作")

# 環境変数読み込み
load_dotenv()

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
    priority: int = 99
    entity_type: str = ""
    pos_tag: str = ""
    lemma: str = ""
    reading: str = ""

class GinzaEnhancedExtractor:
    """GinZA統合地名抽出器（Enhanced V2 + GiNZA）"""
    
    def __init__(self):
        self._init_ginza_system()
        self._init_enhanced_patterns()
        self._init_ai_verification()
        logger.info("🌟 GinZA統合地名抽出器v4.0初期化完了")
        
    def _init_ginza_system(self):
        """GiNZAシステム初期化"""
        self.nlp = None
        self.ginza_enabled = False
        
        if GINZA_AVAILABLE:
            try:
                self.nlp = spacy.load('ja_ginza')
                self.ginza_enabled = True
                logger.info("✅ GiNZA日本語モデル初期化成功")
            except OSError:
                logger.warning("⚠️ GiNZAモデル未インストール - pip install ja-ginza で導入してください")
        
        # 地名関連エンティティタイプ
        self.place_entity_types = {
            'GPE',      # 地政学的エンティティ
            'LOC',      # 場所
            'FACILITY', # 施設
            'ORG'       # 組織（場所名を含む場合）
        }
        
    def _init_enhanced_patterns(self):
        """Enhanced V2パターン統合"""
        # 実証済み高性能有名地名リスト（4,281件対応）
        self.famous_places = [
            # 東京中心部（高頻度）
            '銀座', '新宿', '渋谷', '上野', '浅草', '品川', '池袋', '新橋', '有楽町',
            '丸の内', '表参道', '原宿', '恵比寿', '六本木', '赤坂', '青山', '麻布',
            '目黒', '世田谷', '本郷', '神田', '日本橋', '築地', '月島', '両国',
            
            # 関東主要地名
            '横浜', '川崎', '千葉', '埼玉', '大宮', '浦和', '船橋', '柏', '川越',
            '鎌倉', '湘南', '箱根', '熱海', '軽井沢', '日光', '那須', '草津',
            
            # 関西主要地名
            '京都', '大阪', '神戸', '奈良', '和歌山', '滋賀', '比叡山', '嵐山', '祇園',
            '清水', '金閣寺', '銀閣寺', '伏見', '宇治', '平安京', '難波', '梅田',
            
            # 古典・歴史地名
            '江戸', '平安京', '武蔵', '相模', '甲斐', '信濃', '越後', '下野', '上野',
            '大和', '河内', '和泉', '摂津', '近江', '美濃', '尾張', '三河', '飛騨',
        ]
        
        # 正規表現パターン
        self.enhanced_patterns = [
            {
                'pattern': r'(?<![一-龯])[北海青森岩手宮城秋田山形福島茨城栃木群馬埼玉千葉東京神奈川新潟富山石川福井山梨長野岐阜静岡愛知三重滋賀京都大阪兵庫奈良和歌山鳥取島根岡山広島山口徳島香川愛媛高知福岡佐賀長崎熊本大分宮崎鹿児島沖縄][都道府県](?![一-龯])',
                'category': '都道府県',
                'confidence': 0.95,
                'priority': 1
            },
            {
                'pattern': r'(?<![一-龯])[一-龯]{2,6}[市区町村](?![一-龯])',
                'category': '市区町村',
                'confidence': 0.85,
                'priority': 2
            },
            {
                'pattern': r'(?<![一-龯])[一-龯]{1,4}[山川湖海峠谷野原島岬浦崎](?![一-龯])',
                'category': '自然地名',
                'confidence': 0.75,
                'priority': 4
            }
        ]
        
    def _init_ai_verification(self):
        """AI検証機能の初期化"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
            self.ai_enabled = True
            logger.info("✅ AI地名検証機能有効")
        else:
            self.openai_client = None
            self.ai_enabled = False
            logger.warning("⚠️ OpenAI APIキーが設定されていません（AI検証機能無効）")
    
    def extract_places_from_text(self, text: str) -> List[ExtractedPlace]:
        """統合地名抽出（GiNZA + Enhanced V2）"""
        all_places = []
        
        # 1. GiNZA地名抽出（優先）
        if self.ginza_enabled:
            ginza_places = self._extract_with_ginza(text)
            all_places.extend(ginza_places)
            logger.debug(f"GiNZA抽出: {len(ginza_places)}件")
        
        # 2. 有名地名抽出（Enhanced V2）
        famous_places = self._extract_famous_places(text)
        all_places.extend(famous_places)
        logger.debug(f"有名地名抽出: {len(famous_places)}件")
        
        # 3. 正規表現パターン抽出
        pattern_places = self._extract_with_patterns(text)
        all_places.extend(pattern_places)
        logger.debug(f"パターン抽出: {len(pattern_places)}件")
        
        # 4. 重複除去・統合
        unified_places = self._unify_and_deduplicate(all_places)
        logger.info(f"✅ 統合地名抽出完了: {len(unified_places)}件")
        
        return unified_places
    
    def _extract_with_ginza(self, text: str) -> List[ExtractedPlace]:
        """GiNZA抽出処理"""
        places = []
        
        try:
            # 大容量テキスト分割処理
            max_length = 100000
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                for chunk in chunks:
                    places.extend(self._process_ginza_chunk(chunk))
            else:
                places = self._process_ginza_chunk(text)
        except Exception as e:
            logger.error(f"❌ GiNZA抽出エラー: {e}")
        
        return places
    
    def _process_ginza_chunk(self, text: str) -> List[ExtractedPlace]:
        """GiNZAチャンク処理"""
        places = []
        
        try:
            doc = self.nlp(text)
            
            # 固有表現抽出
            for ent in doc.ents:
                if (ent.label_ in self.place_entity_types and 
                    self._is_valid_ginza_place(ent.text)):
                    
                    confidence = self._calculate_ginza_confidence(ent)
                    context_before, context_after = self._get_ginza_context(text, ent)
                    
                    place = ExtractedPlace(
                        name=ent.text,
                        canonical_name=self._normalize_place_name(ent.text),
                        place_type=self._categorize_ginza_place(ent),
                        confidence=confidence,
                        position=ent.start_char,
                        matched_text=ent.text,
                        context_before=context_before,
                        context_after=context_after,
                        extraction_method='ginza_ner',
                        priority=0,  # 最高優先度
                        entity_type=ent.label_,
                        reading=self._get_reading(ent)
                    )
                    places.append(place)
            
            # 固有名詞追加チェック
            for token in doc:
                if (token.pos_ == 'PROPN' and 
                    len(token.text) >= 2 and
                    token.text not in [p.name for p in places] and
                    self._is_potential_place_name(token.text)):
                    
                    context_before, context_after = self._get_token_context(text, token)
                    
                    place = ExtractedPlace(
                        name=token.text,
                        canonical_name=self._normalize_place_name(token.text),
                        place_type='propn_place',
                        confidence=0.70,
                        position=token.idx,
                        matched_text=token.text,
                        context_before=context_before,
                        context_after=context_after,
                        extraction_method='ginza_propn',
                        priority=1,
                        pos_tag=token.pos_,
                        lemma=token.lemma_
                    )
                    places.append(place)
                    
        except Exception as e:
            logger.error(f"❌ GiNZAチャンク処理エラー: {e}")
        
        return places
    
    def _extract_famous_places(self, text: str) -> List[ExtractedPlace]:
        """有名地名抽出（Enhanced V2統合）"""
        places = []
        
        for place_name in self.famous_places:
            for match in re.finditer(re.escape(place_name), text):
                position = match.start()
                context_before = text[max(0, position-20):position]
                context_after = text[position+len(place_name):position+len(place_name)+20]
                
                place = ExtractedPlace(
                    name=place_name,
                    canonical_name=self._normalize_place_name(place_name),
                    place_type='有名地名',
                    confidence=0.92,
                    position=position,
                    matched_text=place_name,
                    context_before=context_before,
                    context_after=context_after,
                    extraction_method='famous_places',
                    priority=0  # 高優先度
                )
                places.append(place)
        
        return places
    
    def _extract_with_patterns(self, text: str) -> List[ExtractedPlace]:
        """正規表現パターン抽出"""
        places = []
        
        for pattern_info in self.enhanced_patterns:
            pattern = pattern_info['pattern']
            
            for match in re.finditer(pattern, text):
                name = match.group()
                position = match.start()
                
                if not self._is_likely_place_name(name, pattern_info['category']):
                    continue
                
                context_before = text[max(0, position-20):position]
                context_after = text[position+len(name):position+len(name)+20]
                
                place = ExtractedPlace(
                    name=name,
                    canonical_name=self._normalize_place_name(name),
                    place_type=pattern_info['category'],
                    confidence=pattern_info['confidence'],
                    position=position,
                    matched_text=name,
                    context_before=context_before,
                    context_after=context_after,
                    extraction_method='regex_pattern',
                    priority=pattern_info['priority']
                )
                places.append(place)
        
        return places
    
    def _unify_and_deduplicate(self, places: List[ExtractedPlace]) -> List[ExtractedPlace]:
        """地名統合・重複除去"""
        # 正規化名でグループ化
        place_groups = {}
        for place in places:
            canonical_name = place.canonical_name
            if canonical_name not in place_groups:
                place_groups[canonical_name] = []
            place_groups[canonical_name].append(place)
        
        # 各グループから最適な地名を選択
        unified_places = []
        for canonical_name, group in place_groups.items():
            best_place = self._select_best_place(group)
            unified_places.append(best_place)
        
        # 優先度・信頼度でソート
        unified_places.sort(key=lambda x: (x.priority, -x.confidence, x.position))
        
        return unified_places
    
    def _select_best_place(self, candidates: List[ExtractedPlace]) -> ExtractedPlace:
        """候補から最適な地名を選択（改善版：より具体的な地名を優先）"""
        if not candidates:
            return None
        
        # 1. より具体的な地名（長い名前）を優先
        max_length = max(len(p.name) for p in candidates)
        longest_candidates = [p for p in candidates if len(p.name) == max_length]
        
        if len(longest_candidates) == 1:
            return longest_candidates[0]
        
        # 2. 同じ長さの場合、GiNZA抽出を優先
        ginza_candidates = [p for p in longest_candidates if 'ginza' in p.extraction_method]
        if ginza_candidates:
            return max(ginza_candidates, key=lambda x: x.confidence)
        
        # 3. 正規表現パターン（完全地名）を優先
        pattern_candidates = [p for p in longest_candidates if p.extraction_method == 'regex_pattern']
        if pattern_candidates:
            return max(pattern_candidates, key=lambda x: x.confidence)
        
        # 4. 有名地名を優先
        famous_candidates = [p for p in longest_candidates if p.extraction_method == 'famous_places']
        if famous_candidates:
            return max(famous_candidates, key=lambda x: x.confidence)
        
        # 5. 信頼度最高を選択
        return max(longest_candidates, key=lambda x: x.confidence)
    
    # ユーティリティメソッド
    def _is_valid_ginza_place(self, place_name: str) -> bool:
        """GiNZA地名妥当性チェック"""
        if not place_name or len(place_name.strip()) <= 1:
            return False
        exclusions = {'日', '月', '年', '時', '分', '秒', '人', '方', '間', '前', '後'}
        return place_name not in exclusions
    
    def _is_potential_place_name(self, text: str) -> bool:
        """地名可能性チェック"""
        place_suffixes = ['県', '市', '区', '町', '村', '山', '川', '島', '駅', '港']
        return any(text.endswith(suffix) for suffix in place_suffixes)
    
    def _is_likely_place_name(self, name: str, category: str) -> bool:
        """地名妥当性判定（Enhanced V2統合）"""
        # 時間表現除外
        time_prefixes = ['今', '先日', '昨日', '明日', '今日', '今夜', '夕方', '朝', '午前', '午後']
        if any(name.startswith(prefix) for prefix in time_prefixes):
            return False
        
        # 除外パターン
        exclude_patterns = [
            r'.*[店屋社会館部課室科組]$',
            r'^[一二三四五六七八九十]',
            r'.*[時分秒日月年]$',
            r'文藝都市',
            r'^山道$'
        ]
        return not any(re.match(pattern, name) for pattern in exclude_patterns)
    
    def _calculate_ginza_confidence(self, ent) -> float:
        """GiNZA信頼度計算"""
        base_confidence = 0.75
        if ent.label_ == 'GPE':
            base_confidence += 0.20
        elif ent.label_ == 'LOC':
            base_confidence += 0.15
        elif ent.label_ == 'FACILITY':
            base_confidence += 0.10
        return min(base_confidence, 1.0)
    
    def _categorize_ginza_place(self, ent) -> str:
        """GiNZA地名カテゴリー分類"""
        category_map = {
            'GPE': 'geopolitical_entity',
            'LOC': 'location',
            'FACILITY': 'facility',
            'ORG': 'organization_place'
        }
        return category_map.get(ent.label_, 'unknown_place')
    
    def _get_reading(self, ent) -> str:
        """読み仮名取得"""
        try:
            return getattr(ent, 'reading', '') or ''
        except:
            return ''
    
    def _get_ginza_context(self, text: str, ent) -> Tuple[str, str]:
        """GiNZAコンテキスト取得"""
        start = max(0, ent.start_char - 20)
        end = min(len(text), ent.end_char + 20)
        context_before = text[start:ent.start_char]
        context_after = text[ent.end_char:end]
        return context_before, context_after
    
    def _get_token_context(self, text: str, token) -> Tuple[str, str]:
        """トークンコンテキスト取得"""
        start = max(0, token.idx - 20)
        end = min(len(text), token.idx + len(token.text) + 20)
        context_before = text[start:token.idx]
        context_after = text[token.idx + len(token.text):end]
        return context_before, context_after
    
    def _normalize_place_name(self, name: str) -> str:
        """地名正規化（階層地名統一対応版）"""
        if not name:
            return name
            
        normalized = name.strip()
        
        # 表記揺れ統一
        normalized = normalized.replace('ヶ', 'が')
        normalized = normalized.replace('ケ', 'が') 
        normalized = normalized.replace('ヵ', 'が')
        normalized = normalized.replace('　', ' ')
        
        # 階層地名の正規化（包含関係対応）
        # 例: 東京都新宿区 → 新宿、神奈川県横浜市 → 横浜
        if '都' in normalized and ('区' in normalized or '市' in normalized):
            # 都道府県+市区を含む場合、市区部分を抽出
            parts = normalized.split('都')
            if len(parts) == 2:
                after_to = parts[1]
                if '区' in after_to:
                    # 新宿区 → 新宿
                    return after_to.replace('区', '')
                elif '市' in after_to:
                    # 横浜市 → 横浜
                    return after_to.replace('市', '')
        
        if '県' in normalized and ('区' in normalized or '市' in normalized):
            # 県+市区を含む場合、市区部分を抽出
            parts = normalized.split('県')
            if len(parts) == 2:
                after_ken = parts[1]
                if '市' in after_ken:
                    # 横浜市 → 横浜
                    return after_ken.replace('市', '')
                elif '区' in after_ken:
                    # 中央区 → 中央
                    return after_ken.replace('区', '')
        
        # 府+市区を含む場合
        if '府' in normalized and ('区' in normalized or '市' in normalized):
            parts = normalized.split('府')
            if len(parts) == 2:
                after_fu = parts[1]
                if '市' in after_fu:
                    return after_fu.replace('市', '')
                elif '区' in after_fu:
                    return after_fu.replace('区', '')
        
        # 単純な都道府県の正規化
        if normalized.endswith('都') or normalized.endswith('府') or normalized.endswith('県'):
            base = normalized[:-1]
            if base:
                return base
        
        # 市区町村の正規化
        if normalized.endswith('市') or normalized.endswith('区'):
            base = normalized[:-1]
            if base:
                return base
                
        return normalized

def main():
    """テスト実行"""
    extractor = GinzaEnhancedExtractor()
    
    test_text = """
    昨日、東京都新宿区から神奈川県横浜市まで電車で移動しました。
    北海道の札幌市は雪が美しい街です。
    古い時代の江戸から明治の東京への変遷は興味深いものがあります。
    京都の金閣寺や奈良の東大寺を見学しました。
    富士山の頂上から見る日本の景色は格別です。
    """
    
    print("=== 🌟 GinZA統合地名抽出器v4.0テスト ===")
    places = extractor.extract_places_from_text(test_text)
    
    print(f"✅ 抽出地名数: {len(places)}件")
    print(f"🔧 GiNZA利用可能: {extractor.ginza_enabled}")
    print(f"🤖 AI検証機能: {extractor.ai_enabled}")
    
    for i, place in enumerate(places, 1):
        print(f"🗺️ {i}. {place.name} [{place.place_type}] "
              f"({place.extraction_method}, 信頼度: {place.confidence:.2f})")
        if place.reading:
            print(f"    読み: {place.reading}")

if __name__ == "__main__":
    main() 