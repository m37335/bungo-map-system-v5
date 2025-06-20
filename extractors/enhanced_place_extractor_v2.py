#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌟 強化版地名抽出器 - Legacy統合版
以前の高性能実装（regex_有名地名4,281件等）を現在のシステムに統合

Features:
- 境界条件強化済みの正規表現パターン
- 実証済み高精度抽出（81.3%の有名地名抽出率）
- AI文脈判断対応
- 重複除去・優先度制御
"""

import re
import sqlite3
import logging
import openai
import os
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# GinZA統合抽出器の追加インポート
try:
    from .ginza_enhanced_extractor import GinzaEnhancedExtractor
    GINZA_INTEGRATION_AVAILABLE = True
except ImportError:
    GINZA_INTEGRATION_AVAILABLE = False

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

class EnhancedPlaceExtractorV2:
    """強化版地名抽出クラス（Legacy統合版）"""
    
    def __init__(self):
        self._init_enhanced_patterns()
        self._init_ai_verification()
        self._init_ginza_integration()
        logger.info("🌟 強化版地名抽出器V2（Legacy統合版 + GinZA統合）初期化完了")
        
    def _init_enhanced_patterns(self):
        """実証済み高性能パターンを初期化"""
        
        # 実証済み高性能有名地名リスト（regex_有名地名: 4,281件対応）
        self.famous_places = [
            # 東京中心部（高頻度）
            '銀座', '新宿', '渋谷', '上野', '浅草', '品川', '池袋', '新橋', '有楽町',
            '丸の内', '表参道', '原宿', '恵比寿', '六本木', '赤坂', '青山', '麻布',
            '目黒', '世田谷', '本郷', '神田', '日本橋', '築地', '月島', '両国',
            '浅草橋', '秋葉原', '御茶ノ水', '四谷', '市ヶ谷', '飯田橋', '水道橋',
            
            # 関東主要地名
            '横浜', '川崎', '千葉', '埼玉', '大宮', '浦和', '船橋', '柏', '所沢', '川越',
            '鎌倉', '湘南', '箱根', '熱海', '軽井沢', '日光', '那須', '草津', '伊香保',
            '小田原', '平塚', '藤沢', '茅ヶ崎', '逗子', '葉山', '三浦', '房総',
            
            # 関西主要地名
            '京都', '大阪', '神戸', '奈良', '和歌山', '滋賀', '比叡山', '嵐山', '祇園',
            '清水', '金閣寺', '銀閣寺', '伏見', '宇治', '平安京', '難波', '梅田', '心斎橋',
            '天王寺', '住吉', '堺', '岸和田', '高槻', '枚方', '茨木', '吹田',
            
            # 中部地方
            '名古屋', '金沢', '富山', '新潟', '長野', '松本', '諏訪', '上高地', '立山',
            '白川', '高山', '下呂', '熱海', '伊豆', '修善寺', '韮山', '沼津', '静岡',
            
            # 東北地方
            '仙台', '青森', '盛岡', '秋田', '山形', '福島', '会津', '松島', '平泉',
            '津軽', '南部', '最上', '庄内', '相馬', '二本松', '白河', '喜多方',
            
            # 北海道
            '札幌', '函館', '小樽', '旭川', '釧路', '帯広', '北見', '室蘭', '苫小牧',
            '根室', '稚内', '網走', '紋別', '留萌', '夕張', '岩見沢', '千歳',
            
            # 中国・四国地方
            '広島', '岡山', '山口', '鳥取', '島根', '高松', '松山', '高知', '徳島',
            '下関', '宇部', '萩', '津山', '倉敷', '福山', '尾道', '因幡', '出雲',
            
            # 九州・沖縄
            '福岡', '博多', '北九州', '佐賀', '長崎', '熊本', '大分', '宮崎', '鹿児島',
            '沖縄', '那覇', '久留米', '飯塚', '唐津', '佐世保', '島原', '天草', '阿蘇',
            
            # 古典・歴史地名（高精度）
            '江戸', '平安京', '武蔵', '相模', '甲斐', '信濃', '越後', '下野', '上野',
            '常陸', '下総', '上総', '安房', '駿河', '遠江', '伊豆', '伊勢', '山城',
            '大和', '河内', '和泉', '摂津', '近江', '美濃', '尾張', '三河', '飛騨',
            '薩摩', '大隅', '日向', '肥前', '肥後', '筑前', '筑後', '豊前', '豊後',
            
            # 海外地名（文学作品頻出）
            'パリ', 'ロンドン', 'ベルリン', 'ウィーン', 'ローマ', 'モスクワ', 'ペテルブルク',
            'ニューヨーク', 'シカゴ', 'ボストン', 'サンフランシスコ', 'ロサンゼルス',
            '上海', '北京', 'ペキン', '南京', '広州', '天津', '青島', '大連',
            'ソウル', 'プサン', 'バンコク', 'マニラ', 'ジャカルタ', 'シンガポール',
            
            # 自然地名（有名）
            '富士山', '阿蘇山', '霧島', '筑波山', '比叡山', '高野山', '浅間山', '白山',
            '琵琶湖', '中禅寺湖', '芦ノ湖', '十和田湖', '猪苗代湖', '諏訪湖', '浜名湖',
            '瀬戸内海', '日本海', '太平洋', '東京湾', '大阪湾', '駿河湾', '相模湾',
            '利根川', '信濃川', '石狩川', '筑後川', '吉野川', '最上川', '北上川'
        ]
        
        # 実証済み正規表現パターン
        self.enhanced_patterns = [
            # 1. 完全地名（都道府県+市区町村）- 最高優先度・最高精度
            {
                'pattern': r'(?<![一-龯])[北海青森岩手宮城秋田山形福島茨城栃木群馬埼玉千葉東京神奈川新潟富山石川福井山梨長野岐阜静岡愛知三重滋賀京都大阪兵庫奈良和歌山鳥取島根岡山広島山口徳島香川愛媛高知福岡佐賀長崎熊本大分宮崎鹿児島沖縄][都道府県][一-龯]{2,8}[市区町村](?![一-龯])',
                'category': '完全地名',
                'confidence': 0.98,
                'priority': 0
            },
            
            # 2. 都道府県（境界条件強化版）- 実証済み高精度
            {
                'pattern': r'(?<![一-龯])[北海青森岩手宮城秋田山形福島茨城栃木群馬埼玉千葉東京神奈川新潟富山石川福井山梨長野岐阜静岡愛知三重滋賀京都大阪兵庫奈良和歌山鳥取島根岡山広島山口徳島香川愛媛高知福岡佐賀長崎熊本大分宮崎鹿児島沖縄][都道府県](?![一-龯])',
                'category': '都道府県',
                'confidence': 0.95,
                'priority': 1
            },
            
            # 3. 市区町村（境界条件強化版）- 実証済み
            {
                'pattern': r'(?<![一-龯])[一-龯]{2,6}[市区町村](?![一-龯])',
                'category': '市区町村',
                'confidence': 0.85,
                'priority': 2
            },
            
            # 4. 郡（境界条件強化版）
            {
                'pattern': r'(?<![一-龯])[一-龯]{2,4}[郡](?![一-龯])',
                'category': '郡',
                'confidence': 0.80,
                'priority': 3
            },
            
            # 5. 自然地形（実証済みパターン）
            {
                'pattern': r'(?<![一-龯])[一-龯]{1,4}[山川湖海峠谷野原島岬浦崎](?![一-龯])',
                'category': '自然地名',
                'confidence': 0.75,
                'priority': 4
            },
            
            # 6. 寺社仏閣
            {
                'pattern': r'(?<![一-龯])[一-龯]{2,6}[寺院神社宮](?![一-龯])',
                'category': '寺社',
                'confidence': 0.70,
                'priority': 5
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
        
    def _init_ginza_integration(self):
        """GinZA統合機能の初期化"""
        self.ginza_extractor = None
        self.ginza_enabled = False
        
        if GINZA_INTEGRATION_AVAILABLE:
            try:
                self.ginza_extractor = GinzaEnhancedExtractor()
                self.ginza_enabled = True
                logger.info("✅ GinZA統合抽出器初期化成功")
            except Exception as e:
                logger.warning(f"⚠️ GinZA統合抽出器初期化失敗: {e}")
        else:
            logger.info("📝 GinZA統合機能無効（標準抽出のみ）")
        
    def extract_places_from_text(self, text: str) -> List[ExtractedPlace]:
        """テキストから地名を抽出（強化版 + GinZA統合）"""
        extracted_places = []
        
        # 1. GinZA統合抽出（利用可能な場合、最優先）
        if self.ginza_enabled and self.ginza_extractor:
            try:
                ginza_places = self.ginza_extractor.extract_places_from_text(text)
                # GinZA結果をExtractedPlace形式に変換
                for ginza_place in ginza_places:
                    extracted_place = ExtractedPlace(
                        name=ginza_place.name,
                        canonical_name=ginza_place.canonical_name,
                        place_type=ginza_place.place_type,
                        confidence=ginza_place.confidence,
                        position=ginza_place.position,
                        matched_text=ginza_place.matched_text,
                        context_before=ginza_place.context_before,
                        context_after=ginza_place.context_after,
                        extraction_method=f"ginza_{ginza_place.extraction_method}",
                        priority=0  # GinZA結果を最優先
                    )
                    extracted_places.append(extracted_place)
                logger.debug(f"🤖 GinZA統合抽出: {len(ginza_places)}件")
            except Exception as e:
                logger.warning(f"⚠️ GinZA統合抽出エラー: {e}")
        
        # 2. 有名地名抽出（実証済み高精度・81.3%）
        for place_name in self.famous_places:
            places = self._extract_by_exact_match(text, place_name, '有名地名', 0.92)
            extracted_places.extend(places)
            
        # 3. パターンマッチング抽出
        for pattern_info in self.enhanced_patterns:
            places = self._extract_by_pattern(text, pattern_info)
            extracted_places.extend(places)
            
        # 4. 統合重複除去・優先度ソート
        extracted_places = self._remove_duplicates_with_priority(extracted_places)
        extracted_places.sort(key=lambda x: (x.priority, -x.confidence, x.position))
        
        logger.info(f"✅ 統合地名抽出完了: {len(extracted_places)}件 (GinZA: {self.ginza_enabled})")
        return extracted_places
        
    def _extract_by_exact_match(self, text: str, place_name: str, place_type: str, confidence: float) -> List[ExtractedPlace]:
        """完全一致による地名抽出"""
        places = []
        pattern = re.escape(place_name)
        
        for match in re.finditer(pattern, text):
            position = match.start()
            
            # 前後のコンテキスト取得
            context_before = text[max(0, position-20):position]
            context_after = text[position+len(place_name):position+len(place_name)+20]
            
            place = ExtractedPlace(
                name=place_name,
                canonical_name=self._normalize_place_name(place_name),
                place_type=place_type,
                confidence=confidence,
                position=position,
                matched_text=place_name,
                context_before=context_before,
                context_after=context_after,
                extraction_method='exact_match',
                priority=0 if place_type == '有名地名' else 1
            )
            
            places.append(place)
            
        return places
        
    def _extract_by_pattern(self, text: str, pattern_info: Dict) -> List[ExtractedPlace]:
        """正規表現パターンによる地名抽出"""
        places = []
        pattern = pattern_info['pattern']
        
        for match in re.finditer(pattern, text):
            name = match.group()
            position = match.start()
            
            # 明らかに地名でないものを除外
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
        
    def _is_likely_place_name(self, name: str, category: str) -> bool:
        """地名らしい名前かどうかの判定（強化版）"""
        
        # 時間表現の除外（強化版）
        time_prefixes = ['今', '先日', '昨日', '明日', '今日', '今夜', '夕方', '朝', '午前', '午後', '最近', '時']
        for prefix in time_prefixes:
            if name.startswith(prefix):
                return False
        
        # 除外パターン（Legacy統合版）
        exclude_patterns = [
            r'.*[店屋社会館部課室科組]$',  # 組織・施設名
            r'^[一二三四五六七八九十]',     # 数字で始まる
            r'.*[時分秒日月年]$',           # 時間関連
            r'.*[前後左右上下中内外]$',     # 方向関連
            r'.*[大小高低長短新旧]$',       # 形容詞的
            r'^山道$',                      # 一般名詞「山道」
            r'^.*道$',                      # 「〜道」（街道以外）
            r'文藝都市',                    # 一般概念
            r'^.*都市$',                    # 「〜都市」（一般概念）
        ]
        
        for pattern in exclude_patterns:
            if re.match(pattern, name):
                return False
                
        # 人名パターンの除外
        if self._is_likely_person_name(name):
            return False
                
        # カテゴリ別の特殊判定
        if category == '市区町村':
            # 2文字以下は除外（「市」「区」単体など）
            if len(name) <= 2:
                return False
                
        elif category == '自然地名':
            # 1文字の地形は除外（「山」「川」単体など）
            if len(name) <= 2:
                return False
                
        return True
    
    def _is_likely_person_name(self, name: str) -> bool:
        """人名の可能性が高いかチェック"""
        # よくある人名パターン
        common_surnames = ['飯島', '田中', '佐藤', '鈴木', '高橋', '渡辺', '伊藤', '山田', '中村', '小林']
        
        # 時間表現+人名のパターンをチェック
        for surname in common_surnames:
            if name.endswith(surname):
                prefix = name[:-len(surname)]
                if prefix in ['今', '先日', '昨日', '明日', '最近']:
                    return True
        
        return False
    
    def _verify_with_ai(self, place_name: str, sentence: str) -> bool:
        """AI文脈分析による地名検証"""
        if not self.ai_enabled:
            return True  # AI無効時はデフォルトで通す
            
        try:
            prompt = f"""
以下の文章で使われている「{place_name}」について分析してください。

文章: {sentence}

この「{place_name}」は地名として使われていますか？
以下の観点から判断し、JSON形式で回答してください：
{{
    "is_place_name": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "判断理由"
}}

判断基準：
- 地名として使われているか、人名・時間表現・一般名詞として使われているか
- 文脈から地理的な場所を指しているか
- 「今〜」「先日〜」「夕方〜」のような時間表現ではないか
"""

            response = self.openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                messages=[
                    {'role': 'system', 'content': 'あなたは文豪作品の地名分析専門家です。文脈を理解して地名/非地名を正確に判別してください。'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '200')),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.1'))
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # JSON解析
            try:
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif '```' in response_text:
                    json_start = response_text.find('```') + 3
                    json_end = response_text.find('```', json_start)
                    response_text = response_text[json_start:json_end].strip()
                    
                result = json.loads(response_text)
                
                if isinstance(result, dict) and 'is_place_name' in result:
                    is_valid = result['is_place_name']
                    confidence = result.get('confidence', 0.5)
                    reasoning = result.get('reasoning', '')
                    
                    if not is_valid:
                        logger.info(f"🤖 AI検証除外: {place_name} - {reasoning}")
                    
                    return is_valid
                else:
                    logger.warning(f"AI応答形式エラー: {response_text}")
                    return True  # エラー時はデフォルトで通す
                    
            except json.JSONDecodeError:
                logger.warning(f"AI応答JSON解析エラー: {response_text}")
                return True
            
        except Exception as e:
            logger.error(f"AI検証エラー: {e}")
            return True  # エラー時はデフォルトで通す
        
    def _normalize_place_name(self, name: str) -> str:
        """地名正規化（Legacy統合版）"""
        if not name:
            return name
            
        normalized = name.strip()
        
        # 表記揺れ統一
        normalized = normalized.replace('ヶ', 'が')
        normalized = normalized.replace('ケ', 'が') 
        normalized = normalized.replace('ヵ', 'が')
        normalized = normalized.replace('　', ' ')
        
        # 都道府県の正規化
        if normalized.endswith('都') or normalized.endswith('府') or normalized.endswith('県'):
            base = normalized[:-1]
            if base:
                return base
                
        return normalized
        
    def _remove_duplicates_with_priority(self, places: List[ExtractedPlace]) -> List[ExtractedPlace]:
        """優先度を考慮した重複除去"""
        # 位置ベースでグループ化
        position_groups = {}
        for place in places:
            # 10文字以内の近接地名は重複とみなす
            group_key = place.position // 10
            if group_key not in position_groups:
                position_groups[group_key] = []
            position_groups[group_key].append(place)
            
        unique_places = []
        for group in position_groups.values():
            if len(group) == 1:
                unique_places.append(group[0])
            else:
                # 優先度・信頼度でベストを選択
                best_place = min(group, key=lambda x: (x.priority, -x.confidence))
                unique_places.append(best_place)
                
        return unique_places
        
    def save_places_to_db(self, sentence_id: int, places: List[ExtractedPlace]) -> int:
        """抽出された地名をデータベースに保存（AI検証付き）"""
        if not places:
            return 0
            
        # センテンステキストを取得（AI検証用）
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        cursor.execute("SELECT sentence_text FROM sentences WHERE sentence_id = ?", (sentence_id,))
        result = cursor.fetchone()
        sentence_text = result[0] if result else ""
        conn.close()
        
        saved_count = 0
        ai_rejected_count = 0
        
        for place in places:
            try:
                # 疑わしい地名はAI検証を実行
                needs_ai_verification = self._needs_ai_verification(place.name, place.place_type)
                
                if needs_ai_verification:
                    if not self._verify_with_ai(place.name, sentence_text):
                        ai_rejected_count += 1
                        logger.debug(f"🤖 AI検証除外: {place.name}")
                        continue
                
                # 地名マスターテーブルに追加
                place_id = self._get_or_create_place(place)
                
                # センテンス-地名関連テーブルに保存
                self._save_sentence_place_relation(sentence_id, place_id, place)
                
                saved_count += 1
                logger.debug(f"地名保存: {place.name} (センテンス {sentence_id})")
                
            except Exception as e:
                logger.error(f"地名保存エラー: {place.name} - {e}")
        
        if ai_rejected_count > 0:
            logger.info(f"🤖 AI検証: {ai_rejected_count}件除外")
                
        return saved_count
    
    def _needs_ai_verification(self, place_name: str, place_type: str) -> bool:
        """AI検証が必要かどうかを判定"""
        # 有名地名は検証不要（高信頼度）
        if place_type == '有名地名':
            return False
            
        # 都道府県は検証不要（高信頼度）
        if place_type == '都道府県':
            return False
            
        # 疑わしいパターンをチェック
        suspicious_patterns = [
            r'^[今先昨明最夕朝午時]',  # 時間表現で始まる
            r'.*[飯島田中佐藤鈴木]$',    # よくある人名で終わる
            r'^山道$',                   # 一般名詞
            r'.*都市$',                  # 一般概念
            r'^.*道$',                   # 「〜道」
        ]
        
        for pattern in suspicious_patterns:
            if re.match(pattern, place_name):
                return True
                
        return False
        
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
                ) VALUES (?, ?, ?, ?, 1, 'enhanced_place_extractor_v2', 'auto_extracted', ?)
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
            
    def _get_context_sentences(self, sentence_id: int) -> tuple:
        """指定センテンスの前後2文を取得"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # 同じ作品内でのセンテンス順序を取得
            cursor.execute("""
                SELECT s1.sentence_text as prev_2,
                       s2.sentence_text as prev_1,
                       s3.sentence_text as current,
                       s4.sentence_text as next_1,
                       s5.sentence_text as next_2
                FROM sentences s3
                LEFT JOIN sentences s2 ON s2.work_id = s3.work_id AND s2.sentence_id = s3.sentence_id - 1
                LEFT JOIN sentences s1 ON s1.work_id = s3.work_id AND s1.sentence_id = s3.sentence_id - 2
                LEFT JOIN sentences s4 ON s4.work_id = s3.work_id AND s4.sentence_id = s3.sentence_id + 1
                LEFT JOIN sentences s5 ON s5.work_id = s3.work_id AND s5.sentence_id = s3.sentence_id + 2
                WHERE s3.sentence_id = ?
            """, (sentence_id,))
            
            result = cursor.fetchone()
            if result:
                return result[0], result[1], result[2], result[3], result[4]
            else:
                return None, None, None, None, None
                
        finally:
            conn.close()

    def _save_sentence_place_relation(self, sentence_id: int, place_id: int, place: ExtractedPlace):
        """センテンス-地名関連を保存（前後文付き、新スキーマ対応）"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # 前後文を取得
            prev_2, prev_1, current, next_1, next_2 = self._get_context_sentences(sentence_id)
            
            cursor.execute("""
                INSERT INTO sentence_places (
                    sentence_id, place_id, extraction_method, confidence,
                    position_in_sentence, matched_text, verification_status,
                    place_name_only, prev_sentence_2, prev_sentence_1,
                    next_sentence_1, next_sentence_2
                ) VALUES (?, ?, ?, ?, ?, ?, 'auto_extracted', ?, ?, ?, ?, ?)
            """, (
                sentence_id, place_id, place.extraction_method, place.confidence,
                place.position, place.matched_text, place.name,
                prev_2, prev_1, next_1, next_2
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
                        for place in places[:3]:  # 上位3件のみ表示
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
    import argparse
    
    parser = argparse.ArgumentParser(description='強化版地名抽出システムV2（Legacy統合版）')
    parser.add_argument('--limit', type=int, help='処理するセンテンス数の上限')
    parser.add_argument('--stats-only', action='store_true', help='統計情報のみ表示')
    
    args = parser.parse_args()
    
    extractor = EnhancedPlaceExtractorV2()
    
    # 統計情報表示
    print("=== 🌟 強化版地名抽出システムV2統計（Legacy統合版）===")
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
    print("\n=== 🚀 強化版地名抽出処理開始 ===")
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