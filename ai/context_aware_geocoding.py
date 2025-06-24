#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 AI文脈判断型Geocodingシステム (Legacy統合版)
文脈を理解して地名の妥当性と座標を高精度で推定

Features:
- 文脈分析による地名/人名の判別
- 歴史的文脈での地域特定
- 曖昧地名の解決
- 複合地名の分析
- 実証済み高信頼度geocoding（0.92-0.98）
"""

import re
import sqlite3
import logging
import openai
import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from dotenv import load_dotenv
from threading import Lock

# 環境変数読み込み
load_dotenv()

logger = logging.getLogger(__name__)

# API制限管理用のグローバル変数
_api_cache = {}
_api_rate_limiter = {
    'openai': {'last_call': 0, 'min_interval': 1.0},  # 1秒間隔
    'google_maps': {'last_call': 0, 'min_interval': 0.1}  # 0.1秒間隔
}
_cache_lock = Lock()

def _rate_limit_api(api_name: str, min_interval: float = 1.0):
    """API レート制限管理"""
    current_time = time.time()
    last_call = _api_rate_limiter.get(api_name, {}).get('last_call', 0)
    time_since_last = current_time - last_call
    
    if time_since_last < min_interval:
        sleep_time = min_interval - time_since_last
        logger.info(f"🕒 {api_name} レート制限: {sleep_time:.2f}秒待機")
        time.sleep(sleep_time)
    
    _api_rate_limiter[api_name]['last_call'] = time.time()

def _get_cache_key(text: str, api_type: str) -> str:
    """キャッシュキー生成"""
    content = f"{api_type}:{text}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def _load_api_cache() -> Dict:
    """APIキャッシュをファイルから読み込み"""
    cache_file = "data/api_cache.json"
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"キャッシュ読み込みエラー: {e}")
    return {}

def _save_api_cache(cache: Dict):
    """APIキャッシュをファイルに保存"""
    cache_file = "data/api_cache.json"
    try:
        with _cache_lock:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"キャッシュ保存エラー: {e}")

# グローバルキャッシュ初期化
_api_cache = _load_api_cache()

@dataclass
class ContextAnalysisResult:
    """文脈分析結果"""
    is_place_name: bool  # 地名として使われているか
    confidence: float    # 信頼度
    place_type: str     # 地名の種類
    historical_context: str  # 歴史的文脈
    geographic_context: str  # 地理的文脈
    reasoning: str      # 判断理由
    suggested_location: Optional[str] = None  # 推定地域

@dataclass
class GeocodingResult:
    """Geocoding結果"""
    place_name: str
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: float
    source: str
    prefecture: Optional[str] = None
    city: Optional[str] = None
    context_analysis: Optional[ContextAnalysisResult] = None
    fallback_used: bool = False

class ContextAwareGeocoder:
    """AI文脈判断型Geocodingサービス（Legacy統合版）"""
    
    def __init__(self):
        """初期化"""
        self._init_knowledge_base()
        self._init_openai_client()
        logger.info("🤖 AI文脈判断型Geocodingサービス（Legacy統合版）初期化完了")
    
    def _init_openai_client(self):
        """OpenAI APIクライアント初期化"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
            self.openai_enabled = True
            logger.info("✅ OpenAI API接続準備完了")
        else:
            self.openai_client = None
            self.openai_enabled = False
            logger.warning("⚠️ OpenAI APIキーが設定されていません（ChatGPT機能無効）")
    
    def _init_knowledge_base(self):
        """文脈判断用知識ベースの初期化"""
        
        # 文脈判断パターン
        self.context_patterns = {
            # 地名を示唆する文脈パターン
            "place_indicators": [
                r"[へに]行", r"[をに]出", r"[に]住", r"[を]通", r"[から]来",
                r"[に]着", r"[を]訪", r"[に]向", r"[で]生", r"[を]発",
                r"街", r"町", r"村", r"里", r"国", r"県", r"市", r"区",
                r"滞在", r"旅行", r"参拝", r"見物", r"観光", r"散歩",
                r"出身", r"在住", r"移住", r"引越", r"帰郷", r"故郷",
                r"景色", r"風景", r"名所", r"遺跡", r"寺", r"神社",
                r"駅", r"港", r"橋", r"川", r"山", r"海", r"湖",
                r"から.*まで", r"を経由", r"経由して", r"通過", r"立ち寄"
            ],
            
            # 人名を示唆する文脈パターン
            "person_indicators": [
                r"さん$", r"君$", r"氏$", r"先生$", r"様$", r"殿$",
                r"は話", r"が言", r"と会", r"に聞", r"と話", r"を呼",
                r"の顔", r"の性格", r"の家族", r"の人", r"という人",
                r"名前", r"名前は", r"という名", r"呼ばれ", r"呼んで",
                r"機嫌", r"怒", r"笑", r"泣", r"悲し", r"喜", r"憤",
                r"は.*打つ", r"は.*叩", r"は.*殴", r"は.*怒鳴",
                r"は.*言った", r"は.*思った", r"は.*感じた"
            ],
            
            # 歴史的文脈パターン
            "historical_indicators": [
                r"国$", r"藩$", r"城$", r"宿場", r"街道",
                r"古く", r"昔", r"江戸時代", r"平安", r"鎌倉",
                r"時代", r"当時", r"昔の", r"古い", r"歴史"
            ]
        }
        
        # 曖昧地名データベース（人名の可能性がある地名）
        self.ambiguous_places = {
            "柏": {"人名可能性": 0.8, "地名": "千葉県柏市"},
            "清水": {"人名可能性": 0.7, "地名": "静岡県清水区"},
            "本郷": {"地域性": "東京", "地名": "東京都文京区本郷"},
            "神田": {"地域性": "東京", "地名": "東京都千代田区神田"},
            "青山": {"人名可能性": 0.6, "地名": "東京都港区青山"},
            "麻布": {"地域性": "東京", "地名": "東京都港区麻布"},
            "両国": {"地域性": "東京", "地名": "東京都墨田区両国"},
            "伏見": {"地域性": "京都", "地名": "京都府京都市伏見区"},
            "嵐山": {"地域性": "京都", "地名": "京都府京都市右京区嵐山"},
        }
        
        # 人名・学者名データベース（高精度フィルタ用）
        self.known_person_names = {
            # 植物学者・学者
            '松村', '松村任三', '牧野', '牧野富太郎', '湯川', '湯川秀樹',
            '朝比奈', '朝比奈泰彦', '木村', '木村陽二郎', '原', '原寛',
            '服部', '服部広太郎', '中井', '中井猛之進', '小泉', '小泉源一',
            
            # 文豪・作家（作品中に言及される可能性）
            '夏目', '夏目漱石', '芥川', '芥川龍之介', '太宰', '太宰治',
            '川端', '川端康成', '三島', '三島由紀夫', '谷崎', '谷崎潤一郎',
            
            # 一般的な姓
            '田中', '佐藤', '鈴木', '高橋', '渡辺', '伊藤', '山田',
            '中村', '小林', '加藤', '吉田', '山本', '佐々木', '山口',
            '松本', '井上', '木村', '林', '清水', '山崎', '池田',
        }
        
        # 学術・専門用語データベース
        self.academic_terms = {
            # 植物学用語
            '語原', '語源', '学名', '分類', '標本', '観察', '記録',
            '図鑑', '植物', '花', '葉', '茎', '根', '種子', '果実',
            '開花', '結実', '発芽', '生育', '分布', '生息', '自生',
            
            # 一般学術用語
            '研究', '調査', '実験', '観測', '分析', '考察', '論文',
            '報告', '発表', '講演', '会議', '学会', '協会', '団体',
            
            # 医学・科学用語
            '病原', '症状', '治療', '診断', '医学', '薬学',
            
            # 神話・宗教用語
            '牧羊神', '多分神',
            
            # 抽象概念・成句
            '理論', '概念', '思想', '哲学', '主義', '方法', '技術',
            '進退維谷', '最上',  # 最上級・成句として
        }
        
        # 一般名詞データベース
        self.general_nouns = {
            # 時間・状態・量詞
            '今日', '昨日', '明日', '今朝', '夕方', '深夜', '早朝',
            '沢山', '大勢', '少数', '多数', '全部', '一部', '半分',
            '時間', '時期', '期間', '瞬間', '永久', '一時',
            
            # 動作・行為
            '移動', '到着', '出発', '帰宅', '外出', '散歩', '旅行',
            '行動', '動作', '作業', '活動', '運動', '労働',
            
            # 建物・施設の一般名称
            '美容院', '理髪店', '病院', '学校', '図書館', '郵便局',
            '銀行', '会社', '工場', '店舗', '商店', '市場',
            
            # 自然・地形の一般名称
            '山野', '田野', '野原', '草原', '荒野', '平野',
            '水辺', '川辺', '海辺', '岸辺', '湖畔', '池畔',
            '森林', '竹林', '松林', '雑木林',
            
            # 抽象的概念
            '問題', '課題', '困難', '障害', '原因', '結果', '影響',
            '目的', '手段', '方法', '方式', '方向', '状況', '状態',
            '性質', '特徴', '性格', '個性', '人格', '品格',
            
            # 感情・心理
            '気持', '感情', '心情', '気分', '心境', '感覚',
            '印象', '感想', '意見', '考え', '思考', '判断',
            
            # 形容・程度
            '程度', '具合', '調子', '様子', '様相', '模様',
            '最上', '最高', '最低', '最大', '最小', '最多',
        }
        
        # 実証済み高信頼度都市データベース（0.92-0.98信頼度）
        self.high_confidence_cities = {
            # 東京詳細地名（信頼度0.95）
            "本郷": (35.7081, 139.7619, "東京都文京区", 0.95),
            "神田": (35.6918, 139.7648, "東京都千代田区", 0.95),
            "青山": (35.6736, 139.7263, "東京都港区", 0.95),
            "麻布": (35.6581, 139.7414, "東京都港区", 0.95),
            "両国": (35.6967, 139.7933, "東京都墨田区", 0.95),
            "赤坂": (35.6745, 139.7378, "東京都港区", 0.95),
            "日本橋": (35.6813, 139.7744, "東京都中央区", 0.95),
            "築地": (35.6654, 139.7707, "東京都中央区", 0.95),
            "新橋": (35.6665, 139.7580, "東京都港区", 0.95),
            "上野": (35.7136, 139.7772, "東京都台東区", 0.95),
            
            # 京都詳細地名（信頼度0.92-0.98）
            "伏見": (34.9393, 135.7578, "京都府京都市伏見区", 0.98),
            "嵐山": (35.0088, 135.6761, "京都府京都市右京区", 0.98),
            "清水": (34.9948, 135.7849, "京都府京都市東山区", 0.92),
            "祇園": (35.0037, 135.7744, "京都府京都市東山区", 0.98),
            "宇治": (34.8842, 135.7991, "京都府宇治市", 0.95),
            
            # 大阪主要地名（信頼度0.92）
            "難波": (34.6659, 135.5020, "大阪府大阪市浪速区", 0.92),
            "梅田": (34.7010, 135.4962, "大阪府大阪市北区", 0.92),
            "心斎橋": (34.6723, 135.5002, "大阪府大阪市中央区", 0.92),
            
            # 神奈川県主要地名（信頼度0.95）
            "横浜": (35.4478, 139.6425, "神奈川県横浜市", 0.95),
            "鎌倉": (35.3197, 139.5468, "神奈川県鎌倉市", 0.95),
            "箱根": (35.2322, 139.1069, "神奈川県足柄下郡箱根町", 0.95),
            
            # 九州地名（信頼度0.95）
            "鹿児島": (31.5966, 130.5571, "鹿児島県鹿児島市", 0.95),
            
            # 関東・中部観光地（信頼度0.93）
            "日光": (36.7581, 139.6014, "栃木県日光市", 0.93),
            
            # 北海道地名（信頼度0.95）
            "小樽": (43.1907, 140.9947, "北海道小樽市", 0.95),
            "函館": (41.7687, 140.7291, "北海道函館市", 0.95),
            "札幌": (43.0642, 141.3469, "北海道札幌市", 0.95),
        }
        
        # 歴史地名データベース（信頼度0.85）
        self.historical_places = {
            "江戸": (35.6762, 139.6503, "東京都", 0.85),
            "平安京": (35.0116, 135.7681, "京都府", 0.85),
            "伊勢": (34.4900, 136.7056, "三重県伊勢市", 0.85),
            "大和": (34.6851, 135.8325, "奈良県", 0.85),
            "美濃": (35.3912, 136.7223, "岐阜県", 0.85),
            "尾張": (35.1802, 136.9066, "愛知県西部", 0.85),
            "薩摩": (31.5966, 130.5571, "鹿児島県", 0.85),
            "伊豆": (34.9756, 138.9462, "静岡県伊豆半島", 0.85),
            "甲斐": (35.6635, 138.5681, "山梨県", 0.85),
            "信濃": (36.2048, 137.9677, "長野県", 0.85),
            "越後": (37.9026, 139.0235, "新潟県", 0.85),
            "近江": (35.0045, 135.8686, "滋賀県", 0.85),
        }
        
        # 都道府県データベース（信頼度0.95）
        self.prefecture_coords = {
            "北海道": (43.0642, 141.3469, 0.95),
            "青森県": (40.8244, 140.7400, 0.95),
            "岩手県": (39.7036, 141.1527, 0.95),
            "宮城県": (38.2682, 140.8721, 0.95),
            "秋田県": (39.7186, 140.1024, 0.95),
            "山形県": (38.2404, 140.3633, 0.95),
            "福島県": (37.7503, 140.4677, 0.95),
            "茨城県": (36.3417, 140.4468, 0.95),
            "栃木県": (36.5657, 139.8836, 0.95),
            "群馬県": (36.3911, 139.0608, 0.95),
            "埼玉県": (35.8572, 139.6489, 0.95),
            "千葉県": (35.6047, 140.1233, 0.95),
            "東京都": (35.6762, 139.6503, 0.95),
            "神奈川県": (35.4478, 139.6425, 0.95),
            "新潟県": (37.9026, 139.0235, 0.95),
            "富山県": (36.6953, 137.2113, 0.95),
            "石川県": (36.5945, 136.6256, 0.95),
            "福井県": (36.0652, 136.2216, 0.95),
            "山梨県": (35.6635, 138.5681, 0.95),
            "長野県": (36.2048, 137.9677, 0.95),
            "岐阜県": (35.3912, 136.7223, 0.95),
            "静岡県": (34.9766, 138.3831, 0.95),
            "愛知県": (35.1802, 136.9066, 0.95),
            "三重県": (34.7303, 136.5086, 0.95),
            "滋賀県": (35.0045, 135.8686, 0.95),
            "京都府": (35.0116, 135.7681, 0.95),
            "大阪府": (34.6937, 135.5023, 0.95),
            "兵庫県": (34.6913, 135.1830, 0.95),
            "奈良県": (34.6851, 135.8325, 0.95),
            "和歌山県": (34.2261, 135.1675, 0.95),
            "鳥取県": (35.5038, 134.2381, 0.95),
            "島根県": (35.4722, 133.0505, 0.95),
            "岡山県": (34.6617, 133.9345, 0.95),
            "広島県": (34.3966, 132.4596, 0.95),
            "山口県": (34.1861, 131.4706, 0.95),
            "徳島県": (34.0658, 134.5590, 0.95),
            "香川県": (34.3401, 134.0434, 0.95),
            "愛媛県": (33.8416, 132.7658, 0.95),
            "高知県": (33.5597, 133.5311, 0.95),
            "福岡県": (33.6064, 130.4181, 0.95),
            "佐賀県": (33.2494, 130.2989, 0.95),
            "長崎県": (32.7448, 129.8737, 0.95),
            "熊本県": (32.7898, 130.7417, 0.95),
            "大分県": (33.2382, 131.6126, 0.95),
            "宮崎県": (31.9111, 131.4239, 0.95),
            "鹿児島県": (31.5966, 130.5571, 0.95),
            "沖縄県": (26.2124, 127.6792, 0.95),
        }
        
        # 海外地名データベース（文学作品頻出）
        self.foreign_places = {
            "ローマ": (41.9028, 12.4964, "イタリア", 0.90),
            "パリ": (48.8566, 2.3522, "フランス", 0.90),
            "ロンドン": (51.5074, -0.1278, "イギリス", 0.90),
            "ベルリン": (52.5200, 13.4050, "ドイツ", 0.90),
            "ニューヨーク": (40.7128, -74.0060, "アメリカ", 0.90),
            "上海": (31.2304, 121.4737, "中国", 0.90),
            "ペキン": (39.9042, 116.4074, "中国", 0.90),
            "北京": (39.9042, 116.4074, "中国", 0.90),
            "モスクワ": (55.7558, 37.6176, "ロシア", 0.90),
            "ウィーン": (48.2082, 16.3738, "オーストリア", 0.90),
        }
    
    def analyze_context(self, place_name: str, sentence: str, before_text: str = "", after_text: str = "") -> ContextAnalysisResult:
        """文脈分析を実行（高精度フィルタ統合版）"""
        full_context = f"{before_text} {sentence} {after_text}"
        
        # 🚀 高精度フィルタ: 人名・学術用語・一般名詞チェック
        if place_name in self.known_person_names:
            return ContextAnalysisResult(
                is_place_name=False,
                confidence=0.95,
                place_type="人名",
                historical_context="",
                geographic_context="",
                reasoning=f"人名データベースに登録済み: {place_name}",
                suggested_location=None
            )
        
        if place_name in self.academic_terms:
            return ContextAnalysisResult(
                is_place_name=False,
                confidence=0.90,
                place_type="学術用語",
                historical_context="",
                geographic_context="",
                reasoning=f"学術・専門用語として識別: {place_name}",
                suggested_location=None
            )
        
        if place_name in self.general_nouns:
            return ContextAnalysisResult(
                is_place_name=False,
                confidence=0.85,
                place_type="一般名詞",
                historical_context="",
                geographic_context="",
                reasoning=f"一般名詞として識別: {place_name}",
                suggested_location=None
            )
        
        # 地名指標のスコア
        place_score = 0
        for pattern in self.context_patterns["place_indicators"]:
            if re.search(pattern, full_context):
                place_score += 1
        
        # 人名指標のスコア
        person_score = 0
        for pattern in self.context_patterns["person_indicators"]:
            if re.search(pattern, full_context):
                person_score += 1
        
        # 歴史的文脈のスコア
        historical_score = 0
        for pattern in self.context_patterns["historical_indicators"]:
            if re.search(pattern, full_context):
                historical_score += 1
        
        # 曖昧地名の特殊処理
        if place_name in self.ambiguous_places:
            ambiguous_info = self.ambiguous_places[place_name]
            person_possibility = ambiguous_info.get("人名可能性", 0)
            
            if person_score > place_score and person_possibility > 0.5:
                return ContextAnalysisResult(
                    is_place_name=False,
                    confidence=0.8,
                    place_type="人名可能性",
                    historical_context="",
                    geographic_context=ambiguous_info.get("地名", ""),
                    reasoning=f"人名指標が強く、人名可能性{person_possibility}",
                    suggested_location=None
                )
        
        # 総合判断
        total_place_indicators = place_score + historical_score
        is_place = total_place_indicators > person_score
        
        confidence = 0.5
        if total_place_indicators > 0:
            confidence = min(0.95, 0.5 + (total_place_indicators * 0.15))
        
        place_type = "一般地名"
        if historical_score > 0:
            place_type = "歴史地名"
        elif place_name in self.high_confidence_cities:
            place_type = "都市部"
        elif any(place_name.endswith(suffix) for suffix in ["都", "府", "県"]):
            place_type = "都道府県"
        
        # reasoning変数の初期化
        reasoning = f"地名指標{total_place_indicators}件 vs 人名指標{person_score}件"
        
        # ChatGPTによる追加分析（可能な場合）
        if self.openai_enabled:
            try:
                chatgpt_analysis = self._analyze_context_with_llm(place_name, sentence)
                if chatgpt_analysis:
                    # ChatGPT分析結果を統合
                    confidence = max(confidence, chatgpt_analysis.get('confidence', 0.0))
                    if chatgpt_analysis.get('is_place_name'):
                        is_place = True
                    
                    # 分析結果をreasoningに追加
                    chatgpt_reasoning = chatgpt_analysis.get('reasoning', '')
                    if chatgpt_reasoning:
                        reasoning += f" | ChatGPT: {chatgpt_reasoning}"
                        
                    logger.info(f"🤖 ChatGPT分析統合: {place_name} -> 信頼度{confidence:.2f}")
                        
            except Exception as e:
                logger.warning(f"ChatGPT分析エラー ({place_name}): {str(e)}")

        return ContextAnalysisResult(
            is_place_name=is_place,
            confidence=confidence,
            place_type=place_type,
            historical_context="歴史的文脈あり" if historical_score > 0 else "",
            geographic_context=f"地名指標{total_place_indicators}件",
            reasoning=reasoning,
            suggested_location=self.ambiguous_places.get(place_name, {}).get("地名")
        )
    
    def geocode_place(self, place_name: str, sentence: str = "", before_text: str = "", after_text: str = "") -> Optional[GeocodingResult]:
        """地名をGeocode（座標変換）"""
        
        # 文脈分析
        context_analysis = self.analyze_context(place_name, sentence, before_text, after_text)
        
        # 人名と判断された場合はスキップ
        if not context_analysis.is_place_name:
            return None
        
        # 1. 高信頼度都市データベースから検索
        if place_name in self.high_confidence_cities:
            lat, lon, location, confidence = self.high_confidence_cities[place_name]
            return GeocodingResult(
                place_name=place_name,
                latitude=lat,
                longitude=lon,
                confidence=confidence,
                source="high_confidence_cities",
                prefecture=location.split('都')[0] + '都' if '都' in location else 
                          location.split('府')[0] + '府' if '府' in location else
                          location.split('県')[0] + '県' if '県' in location else None,
                city=location,
                context_analysis=context_analysis
            )
        
        # 2. 歴史地名データベースから検索
        if place_name in self.historical_places:
            lat, lon, location, confidence = self.historical_places[place_name]
            return GeocodingResult(
                place_name=place_name,
                latitude=lat,
                longitude=lon,
                confidence=confidence,
                source="historical_places",
                prefecture=location if location.endswith(('都', '府', '県')) else None,
                city=location,
                context_analysis=context_analysis
            )
        
        # 3. 都道府県データベースから検索
        for pref_name, (lat, lon, confidence) in self.prefecture_coords.items():
            if place_name in pref_name or pref_name.replace('都', '').replace('府', '').replace('県', '') == place_name:
                return GeocodingResult(
                    place_name=place_name,
                    latitude=lat,
                    longitude=lon,
                    confidence=confidence,
                    source="prefecture_coords",
                    prefecture=pref_name,
                    city=pref_name,
                    context_analysis=context_analysis
                )
        
        # 4. 海外地名データベースから検索
        if place_name in self.foreign_places:
            lat, lon, country, confidence = self.foreign_places[place_name]
            return GeocodingResult(
                place_name=place_name,
                latitude=lat,
                longitude=lon,
                confidence=confidence,
                source="foreign_places",
                prefecture=country,
                city=place_name,
                context_analysis=context_analysis
            )
        
        # 5. フォールバック：部分マッチング
        fallback_result = self._fallback_geocoding(place_name, context_analysis)
        if fallback_result:
            fallback_result.fallback_used = True
            return fallback_result
        
        return None
    
    def _fallback_geocoding(self, place_name: str, context_analysis: ContextAnalysisResult) -> Optional[GeocodingResult]:
        """フォールバックGeocoding（部分マッチング + Google Maps API）"""
        
        # 1. 部分マッチング（都道府県）
        for pref_name, (lat, lon, confidence) in self.prefecture_coords.items():
            pref_base = pref_name.replace('都', '').replace('府', '').replace('県', '')
            if pref_base in place_name or place_name in pref_base:
                return GeocodingResult(
                    place_name=place_name,
                    latitude=lat,
                    longitude=lon,
                    confidence=max(0.3, confidence - 0.3),  # 信頼度を下げる
                    source="fallback_prefecture",
                    prefecture=pref_name,
                    city=f"{pref_name}内の地名",
                    context_analysis=context_analysis
                )
        
        # 2. 部分マッチング（高信頼度都市）
        for city_name, (lat, lon, location, confidence) in self.high_confidence_cities.items():
            if city_name in place_name or place_name in city_name:
                return GeocodingResult(
                    place_name=place_name,
                    latitude=lat,
                    longitude=lon,
                    confidence=max(0.4, confidence - 0.2),
                    source="fallback_city",
                    prefecture=location.split('都')[0] + '都' if '都' in location else 
                              location.split('府')[0] + '府' if '府' in location else
                              location.split('県')[0] + '県' if '県' in location else None,
                    city=location,
                    context_analysis=context_analysis
                )
        
        # 3. Google Maps API Geocoding（新機能）
        google_result = self._google_maps_geocoding(place_name, context_analysis)
        if google_result:
            return google_result
        
        return None

    def _google_maps_geocoding(self, place_name: str, context_analysis: ContextAnalysisResult) -> Optional[GeocodingResult]:
        """Google Maps API Geocoding"""
        google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not google_api_key:
            logger.debug("Google Maps APIキーが設定されていません")
            return None
        
        try:
            import googlemaps
            gmaps = googlemaps.Client(key=google_api_key)
            
            # 日本国内に限定してGeocoding
            search_query = f"{place_name}, 日本"
            
            geocode_result = gmaps.geocode(
                search_query,
                region='jp',
                language='ja'
            )
            
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                
                # 日本国内の座標かチェック
                if self._is_japan_coordinate(lat, lng):
                    # 住所コンポーネントから詳細情報を抽出
                    prefecture = None
                    city = None
                    formatted_address = geocode_result[0].get('formatted_address', '')
                    
                    for component in geocode_result[0].get('address_components', []):
                        types = component.get('types', [])
                        if 'administrative_area_level_1' in types:
                            prefecture = component['long_name']
                        elif 'locality' in types or 'administrative_area_level_2' in types:
                            city = component['long_name']
                    
                    # 信頼度計算（Google Maps APIは高信頼度だが、文脈分析結果も考慮）
                    confidence = 0.8  # Google Maps APIベース信頼度
                    if context_analysis.confidence > 0.8:
                        confidence = min(0.9, confidence + 0.1)
                    
                    logger.info(f"🌍 Google Maps成功: {place_name} → ({lat:.4f}, {lng:.4f})")
                    
                    return GeocodingResult(
                        place_name=place_name,
                        latitude=lat,
                        longitude=lng,
                        confidence=confidence,
                        source="google_maps_api",
                        prefecture=prefecture,
                        city=city or formatted_address,
                        context_analysis=context_analysis,
                        fallback_used=True
                    )
                else:
                    logger.debug(f"Google Maps結果が日本国外: {place_name} → ({lat:.4f}, {lng:.4f})")
            
        except ImportError:
            logger.warning("googlemapsライブラリがインストールされていません")
        except Exception as e:
            logger.error(f"Google Maps APIエラー ({place_name}): {str(e)}")
        
        return None

    def _is_japan_coordinate(self, lat: float, lng: float) -> bool:
        """座標が日本国内かチェック"""
        # 日本の大まかな座標範囲
        japan_bounds = {
            'north': 45.5,
            'south': 24.0,
            'east': 146.0,
            'west': 122.0
        }
        
        return (japan_bounds['south'] <= lat <= japan_bounds['north'] and
                japan_bounds['west'] <= lng <= japan_bounds['east'])
    
    def _analyze_context_with_llm(self, place_name: str, sentence: str) -> Optional[Dict[str, any]]:
        """ChatGPTによる文脈分析（キャッシュ対応）"""
        if not self.openai_enabled:
            return None
        
        # キャッシュチェック
        cache_key = _get_cache_key(f"{place_name}:{sentence}", "openai_context")
        if cache_key in _api_cache:
            logger.info(f"🎯 キャッシュヒット: {place_name}")
            return _api_cache[cache_key]
            
        try:
            # レート制限
            _rate_limit_api('openai', 1.0)
            
            prompt = f"""
以下の文章で使われている「{place_name}」について分析してください。

文章: {sentence}

以下の観点から分析し、JSON形式で回答してください：
{{
    "is_place_name": true/false,
    "confidence": 0.0-1.0,
    "place_type": "都市/地域/歴史地名/自然地名/人名など",
    "reasoning": "判断理由"
}}

判断基準：
- 地名として使われているか、人名として使われているか
- 文豪作品での文脈的意味
- 歴史的・文学的な背景
"""

            response = self.openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                messages=[
                    {'role': 'system', 'content': 'あなたは文豪作品の地名分析専門家です。文脈を理解して地名/人名を正確に判別してください。'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '300')),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.1'))
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # JSON解析試行
            try:
                # JSONブロックの抽出（```json ``` に囲まれている場合）
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif '```' in response_text:
                    json_start = response_text.find('```') + 3
                    json_end = response_text.find('```', json_start)
                    response_text = response_text[json_start:json_end].strip()
                    
                result = json.loads(response_text)
                
                # 結果の検証
                if isinstance(result, dict) and 'is_place_name' in result:
                    # キャッシュに保存
                    _api_cache[cache_key] = result
                    _save_api_cache(_api_cache)
                    logger.info(f"💾 結果をキャッシュ: {place_name}")
                    return result
                else:
                    logger.warning(f"ChatGPT応答の形式が不正: {response_text}")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.warning(f"ChatGPT応答のJSON解析エラー: {response_text}")
                return None
            
        except Exception as e:
            logger.error(f"ChatGPT API呼び出しエラー: {str(e)}")
            return None
    
    def geocode_places_batch(self, limit: Optional[int] = None) -> Dict[str, int]:
        """一括Geocoding処理"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # 未処理の地名-センテンス関連を取得（新スキーマ対応）
            query = """
                SELECT sp.sentence_id, sp.place_id, p.place_name, s.sentence_text,
                       sp.prev_sentence_1, sp.next_sentence_1
                FROM sentence_places sp
                JOIN places p ON sp.place_id = p.place_id
                JOIN sentences s ON sp.sentence_id = s.sentence_id
                WHERE p.latitude IS NULL OR p.longitude IS NULL
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor.execute(query)
            places_to_geocode = cursor.fetchall()
            
            logger.info(f"🎯 Geocoding対象: {len(places_to_geocode)}件")
            
            stats = {
                'processed_places': 0,
                'geocoded_places': 0,
                'skipped_places': 0,
                'errors': 0
            }
            
            for sentence_id, place_id, place_name, sentence_text, prev_sentence, next_sentence in places_to_geocode:
                try:
                    # Geocoding実行
                    result = self.geocode_place(place_name, sentence_text, prev_sentence or "", next_sentence or "")
                    
                    if result:
                        # データベース更新
                        self._update_place_coordinates(place_id, result)
                        stats['geocoded_places'] += 1
                        
                        logger.info(f"✅ Geocoding: {place_name} → {result.latitude:.4f}, {result.longitude:.4f} ({result.confidence:.2f})")
                    else:
                        stats['skipped_places'] += 1
                        logger.debug(f"⏭️ スキップ: {place_name} (文脈判断で除外)")
                    
                    stats['processed_places'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"❌ Geocodingエラー: {place_name} - {e}")
            
            return stats
            
        finally:
            conn.close()
    
    def _update_place_coordinates(self, place_id: int, result: GeocodingResult):
        """地名の座標情報を更新"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        try:
            # placesテーブル更新
            cursor.execute("""
                UPDATE places SET
                    latitude = ?, longitude = ?, confidence = ?,
                    source_system = ?, verification_status = 'auto_geocoded',
                    updated_at = ?
                WHERE place_id = ?
            """, (
                result.latitude, result.longitude, result.confidence,
                f"context_aware_geocoder_{result.source}", datetime.now(),
                place_id
            ))
            
            # sentence_placesテーブルにも座標情報を更新
            cursor.execute("""
                UPDATE sentence_places SET
                    latitude = ?, longitude = ?,
                    geocoding_source = ?, geocoding_confidence = ?
                WHERE place_id = ?
            """, (
                result.latitude, result.longitude,
                f"context_aware_geocoder_{result.source}", result.confidence,
                place_id
            ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def get_geocoding_statistics(self) -> Dict[str, any]:
        """Geocoding統計の取得"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM places')
        total_places = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
        geocoded_places = cursor.fetchone()[0]
        
        # ソース別統計
        cursor.execute('SELECT source_system, COUNT(*) FROM places WHERE source_system IS NOT NULL GROUP BY source_system')
        source_stats = {source: count for source, count in cursor.fetchall()}
        
        # 信頼度分布
        cursor.execute('SELECT COUNT(*) FROM places WHERE confidence >= 0.9 AND latitude IS NOT NULL')
        high_confidence = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM places WHERE confidence >= 0.7 AND confidence < 0.9 AND latitude IS NOT NULL')
        medium_confidence = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_places": total_places,
            "geocoded_places": geocoded_places,
            "geocoding_rate": geocoded_places / total_places * 100 if total_places > 0 else 0,
            "source_stats": source_stats,
            "confidence_distribution": {
                "high_confidence_count": high_confidence,
                "medium_confidence_count": medium_confidence
            }
        }

    def delete_invalid_places(self, place_names: List[str], reason: str = "管理者判断") -> Dict[str, any]:
        """無効な地名をデータベースから削除"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        deleted_places = []
        not_found_places = []
        
        for place_name in place_names:
            try:
                # place_mastersから地名の存在確認
                cursor.execute('SELECT master_id, display_name FROM place_masters WHERE display_name = ?', (place_name,))
                place_data = cursor.fetchone()
                
                if not place_data:
                    not_found_places.append(place_name)
                    continue
                
                master_id = place_data[0]
                
                # 関連するsentence_placesレコードを削除
                cursor.execute('DELETE FROM sentence_places WHERE master_id = ?', (master_id,))
                deleted_relations = cursor.rowcount
                
                # place_mastersのvalidation_statusを'rejected'に設定（論理削除）
                cursor.execute('UPDATE place_masters SET validation_status = ?, updated_at = CURRENT_TIMESTAMP WHERE master_id = ?', 
                             ('rejected', master_id))
                
                deleted_places.append({
                    "place_name": place_name,
                    "master_id": master_id,
                    "deleted_relations": deleted_relations,
                    "reason": reason
                })
                
                logger.info(f"🗑️ 地名削除完了: {place_name} (ID: {master_id}, 関連: {deleted_relations}件)")
                
            except Exception as e:
                logger.error(f"地名削除エラー ({place_name}): {str(e)}")
                not_found_places.append(place_name)
        
        conn.commit()
        conn.close()
        
        return {
            "deleted_places": deleted_places,
            "not_found_places": not_found_places,
            "total_deleted": len(deleted_places),
            "reason": reason
        }

    def cleanup_invalid_places(self, auto_confirm: bool = False) -> Dict[str, any]:
        """無効地名の自動クリーンアップ"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        # 未Geocodingの地名を取得
        cursor.execute('''
            SELECT p.place_id, p.place_name, p.place_type, p.confidence, p.source_system,
                   COUNT(sp.sentence_id) as usage_count,
                   MIN(s.sentence_text) as sample_sentence
            FROM places p
            LEFT JOIN sentence_places sp ON p.place_id = sp.place_id
            LEFT JOIN sentences s ON sp.sentence_id = s.sentence_id
            WHERE p.latitude IS NULL AND p.longitude IS NULL
            GROUP BY p.place_id, p.place_name
            ORDER BY usage_count ASC
        ''')
        
        ungeocoded_places = cursor.fetchall()
        conn.close()
        
        # 削除候補の分析
        candidates_for_deletion = []
        
        for place_id, place_name, place_type, confidence, source_system, usage_count, sample_sentence in ungeocoded_places:
            # 文脈分析による削除判定
            if sample_sentence:
                context_analysis = self.analyze_context(place_name, sample_sentence)
                
                # 人名と判定された場合
                if not context_analysis.is_place_name and "人名" in context_analysis.reasoning:
                    candidates_for_deletion.append({
                        "place_id": place_id,
                        "place_name": place_name,
                        "reason": "人名として判定",
                        "confidence": context_analysis.confidence,
                        "usage_count": usage_count,
                        "sample": sample_sentence[:50] + "..." if len(sample_sentence) > 50 else sample_sentence
                    })
                
                # 架空地名や抽象表現の判定
                elif place_name in ["自然町", "毎日海"] or any(keyword in place_name for keyword in ["毎日", "自然"]):
                    candidates_for_deletion.append({
                        "place_id": place_id,
                        "place_name": place_name,
                        "reason": "架空地名または抽象表現",
                        "confidence": confidence or 0.0,
                        "usage_count": usage_count,
                        "sample": sample_sentence[:50] + "..." if len(sample_sentence) > 50 else sample_sentence
                    })
        
        # 自動削除または確認
        if auto_confirm:
            place_names_to_delete = [candidate["place_name"] for candidate in candidates_for_deletion]
            deletion_result = self.delete_invalid_places(place_names_to_delete, "自動クリーンアップ")
            
            return {
                "candidates": candidates_for_deletion,
                "deletion_result": deletion_result,
                "auto_deleted": True
            }
        else:
            return {
                "candidates": candidates_for_deletion,
                "auto_deleted": False,
                "message": "削除候補が見つかりました。手動で確認・削除してください。"
            }

    def get_place_usage_analysis(self, place_name: str) -> Dict[str, any]:
        """特定地名の使用状況詳細分析"""
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        # 基本情報
        cursor.execute('SELECT * FROM places WHERE place_name = ?', (place_name,))
        place_data = cursor.fetchone()
        
        if not place_data:
            return {"error": f"地名 '{place_name}' が見つかりません"}
        
        # 使用文一覧
        cursor.execute('''
            SELECT s.sentence_text, w.title, a.name
            FROM sentences s
            JOIN sentence_places sp ON s.sentence_id = sp.sentence_id
            JOIN places p ON sp.place_id = p.place_id
            LEFT JOIN works w ON s.work_id = w.work_id
            LEFT JOIN authors a ON w.author_id = a.author_id
            WHERE p.place_name = ?
            ORDER BY s.sentence_id
        ''', (place_name,))
        
        usage_sentences = cursor.fetchall()
        conn.close()
        
        # 文脈分析
        context_analyses = []
        for sentence_text, work_title, author_name in usage_sentences:
            analysis = self.analyze_context(place_name, sentence_text)
            context_analyses.append({
                "sentence": sentence_text,
                "work_title": work_title,
                "author_name": author_name,
                "is_place_name": analysis.is_place_name,
                "confidence": analysis.confidence,
                "reasoning": analysis.reasoning
            })
        
        return {
            "place_data": {
                "place_id": place_data[0],
                "place_name": place_data[1],
                "place_type": place_data[2],
                "latitude": place_data[3],
                "longitude": place_data[4],
                "confidence": place_data[5],
                "source_system": place_data[6]
            },
            "usage_count": len(usage_sentences),
            "context_analyses": context_analyses,
            "recommended_action": self._get_recommended_action(context_analyses)
        }

    def _get_recommended_action(self, context_analyses: List[Dict]) -> str:
        """文脈分析結果に基づく推奨アクション"""
        if not context_analyses:
            return "削除推奨: 使用例なし"
        
        place_name_count = sum(1 for analysis in context_analyses if analysis["is_place_name"])
        total_count = len(context_analyses)
        
        if place_name_count == 0:
            return "削除推奨: 全て非地名として判定"
        elif place_name_count / total_count < 0.5:
            return "削除検討: 地名使用率が低い"
        else:
            return "保持推奨: 地名として適切に使用"

    def ai_mass_verification(self, limit: Optional[int] = None, confidence_threshold: float = 0.7) -> Dict[str, any]:
        """AI大量検証システム - 既存地名の再評価"""
        if not self.openai_enabled:
            return {"error": "OpenAI APIが利用できません"}
        
        conn = sqlite3.connect('data/bungo_map.db')
        cursor = conn.cursor()
        
        # 検証対象の地名を取得（使用頻度が低い・未検証の地名を優先）
        query = '''
            SELECT pm.master_id, pm.display_name, pm.geocoding_confidence, pm.geocoding_source,
                   COUNT(sp.sentence_id) as usage_count,
                   GROUP_CONCAT(s.sentence_text, '|||') as all_sentences
            FROM place_masters pm
            JOIN sentence_places sp ON pm.master_id = sp.master_id
            JOIN sentences s ON sp.sentence_id = s.sentence_id
            WHERE pm.verification_status IS NULL OR pm.verification_status != 'ai_verified'
            GROUP BY pm.master_id, pm.display_name
            ORDER BY usage_count ASC, pm.geocoding_confidence ASC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
            
        cursor.execute(query)
        places_to_verify = cursor.fetchall()
        
        verification_results = {
            'verified_places': [],
            'deletion_candidates': [],
            'total_processed': 0,
            'ai_errors': 0
        }
        
        logger.info(f"🤖 AI大量検証開始: {len(places_to_verify)}件")
        
        for master_id, place_name, confidence, source_system, usage_count, all_sentences in places_to_verify:
            try:
                sentences = all_sentences.split('|||') if all_sentences else []
                
                # 複数文脈でのAI分析
                ai_analyses = []
                for sentence in sentences[:5]:  # 最大5文まで
                    ai_result = self._enhanced_ai_analysis(place_name, sentence)
                    if ai_result:
                        ai_analyses.append(ai_result)
                
                if not ai_analyses:
                    verification_results['ai_errors'] += 1
                    continue
                
                # 総合判定
                overall_verdict = self._calculate_overall_verdict(ai_analyses)
                
                place_result = {
                    'master_id': master_id,
                    'place_name': place_name,
                    'usage_count': usage_count,
                    'current_confidence': confidence,
                    'ai_analyses': ai_analyses,
                    'overall_verdict': overall_verdict,
                    'recommendation': overall_verdict['recommendation']
                }
                
                # 削除候補の判定
                if overall_verdict['is_valid'] == False and overall_verdict['confidence'] >= confidence_threshold:
                    verification_results['deletion_candidates'].append(place_result)
                    logger.info(f"❌ 削除候補: {place_name} (AI確信度: {overall_verdict['confidence']:.2f})")
                else:
                    verification_results['verified_places'].append(place_result)
                    # データベースに検証済みマークを付与
                    cursor.execute(
                        "UPDATE place_masters SET verification_status = 'ai_verified', ai_confidence = ? WHERE master_id = ?",
                        (overall_verdict['confidence'], master_id)
                    )
                    logger.info(f"✅ 検証済み: {place_name} (AI確信度: {overall_verdict['confidence']:.2f})")
                
                verification_results['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"AI検証エラー ({place_name}): {str(e)}")
                verification_results['ai_errors'] += 1
        
        conn.commit()
        conn.close()
        
        return verification_results

    def _enhanced_ai_analysis(self, place_name: str, sentence: str) -> Optional[Dict[str, any]]:
        """強化されたAI分析 - より詳細な判定"""
        if not self.openai_enabled:
            return None
            
        try:
            prompt = f"""
以下の文章中の「{place_name}」について、地名としての妥当性を詳細に分析してください。

文章: {sentence}

以下の観点から総合的に判断し、JSON形式で回答してください：

{{
    "is_place_name": true/false,
    "confidence": 0.0-1.0,
    "place_type": "都市名/地域名/歴史地名/自然地名/人名/学術用語/一般名詞/その他",
    "reasoning": "詳細な判断理由",
    "context_clues": ["文脈手がかりのリスト"],
    "alternative_interpretation": "他の解釈の可能性",
    "literary_context": "文学作品での使用文脈"
}}

判断基準：
1. 文中での文法的役割（主語/目的語/修飾語等）
2. 周辺語句との関係性
3. 文豪作品での典型的な使用パターン
4. 地名として使われる際の文脈的特徴
5. 人名・一般名詞との区別

特に注意点：
- 植物学者・文豪の人名は地名ではない
- 「沢山」「様子」等の一般名詞は地名ではない
- 「語原」「病原」等の学術用語は地名ではない
- 文脈上明らかに人物を指す場合は人名判定
"""

            response = self.openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4'),  # より高性能なモデルを使用
                messages=[
                    {'role': 'system', 'content': '日本文学・地理・言語学の専門家として、文豪作品中の地名を正確に判別してください。文脈を深く理解し、誤判定を避けることが重要です。'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=500,
                temperature=0.1
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
                    return result
                else:
                    logger.warning(f"AI応答形式エラー: {response_text}")
                    return None
                    
            except json.JSONDecodeError:
                logger.warning(f"AI応答JSON解析エラー: {response_text}")
                return None
            
        except Exception as e:
            logger.error(f"強化AI分析エラー: {str(e)}")
            return None

    def _calculate_overall_verdict(self, ai_analyses: List[Dict[str, any]]) -> Dict[str, any]:
        """複数のAI分析結果から総合判定を計算"""
        if not ai_analyses:
            return {'is_valid': False, 'confidence': 0.0, 'recommendation': '不明'}
        
        # 地名判定の集計
        place_votes = sum(1 for analysis in ai_analyses if analysis.get('is_place_name', False))
        total_votes = len(ai_analyses)
        
        # 信頼度の平均
        avg_confidence = sum(analysis.get('confidence', 0.0) for analysis in ai_analyses) / total_votes  
        
        # 総合判定
        is_valid = place_votes / total_votes >= 0.5
        
        if place_votes == 0:
            recommendation = "削除推奨"
            final_confidence = avg_confidence
        elif place_votes / total_votes < 0.3:
            recommendation = "削除検討"
            final_confidence = avg_confidence * 0.8
        elif place_votes / total_votes < 0.7:
            recommendation = "要再検討"
            final_confidence = avg_confidence * 0.9
        else:
            recommendation = "保持推奨"
            final_confidence = avg_confidence
        
        # 判定理由の統合
        reasoning_summary = []
        place_types = [analysis.get('place_type', '') for analysis in ai_analyses]
        most_common_type = max(set(place_types), key=place_types.count) if place_types else '不明'
        
        return {
            'is_valid': is_valid,
            'confidence': final_confidence,
            'recommendation': recommendation,
            'place_name_ratio': place_votes / total_votes,
            'most_common_type': most_common_type,
            'analysis_count': total_votes,
            'detailed_analyses': ai_analyses
        }

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI文脈判断型Geocodingシステム（Legacy統合版）')
    parser.add_argument('--limit', type=int, help='処理する地名数の上限')
    parser.add_argument('--stats-only', action='store_true', help='統計情報のみ表示')
    parser.add_argument('--cleanup', action='store_true', help='無効地名の自動クリーンアップ実行')
    parser.add_argument('--cleanup-preview', action='store_true', help='無効地名の削除候補を表示（実行なし）')
    parser.add_argument('--delete', nargs='+', help='指定した地名を削除')
    parser.add_argument('--analyze', type=str, help='指定した地名の使用状況を詳細分析')
    parser.add_argument('--ai-verify', action='store_true', help='AI大量検証を実行')
    parser.add_argument('--ai-verify-limit', type=int, default=20, help='AI検証する地名数の上限（デフォルト: 20）')
    parser.add_argument('--confidence-threshold', type=float, default=0.7, help='削除候補とする信頼度の閾値（デフォルト: 0.7）')
    
    args = parser.parse_args()
    
    geocoder = ContextAwareGeocoder()
    
    # 統計情報表示
    print("=== 🤖 AI文脈判断型Geocodingシステム統計（Legacy統合版）===")
    stats = geocoder.get_geocoding_statistics()
    print(f"総地名数: {stats['total_places']:,}")
    print(f"Geocoding済み地名数: {stats['geocoded_places']:,}")
    print(f"未Geocoding地名数: {stats['geocoded_places'] - stats['total_places']:,}")
    print(f"Geocoding率: {stats['geocoding_rate']:.1f}%")
    
    if stats.get('source_stats'):
        print("\n🔧 Geocodingソース:")
        for source, count in stats['source_stats'].items():
            print(f"  {source}: {count}件")
    
    if stats.get('confidence_distribution'):
        print("\n📊 信頼度分布:")
        for confidence_level, count in stats['confidence_distribution'].items():
            print(f"  {confidence_level}: {count}件")
    
    # 地名使用状況分析
    if args.analyze:
        print(f"\n=== 🔍 地名使用状況分析: {args.analyze} ===")
        analysis_result = geocoder.get_place_usage_analysis(args.analyze)
        
        if "error" in analysis_result:
            print(f"❌ {analysis_result['error']}")
            return
        
        place_data = analysis_result["place_data"]
        print(f"📍 地名情報:")
        print(f"   ID: {place_data['place_id']}")
        print(f"   地名: {place_data['place_name']}")
        print(f"   種別: {place_data['place_type']}")
        print(f"   座標: ({place_data['latitude']}, {place_data['longitude']})")
        print(f"   信頼度: {place_data['confidence']}")
        print(f"   ソース: {place_data['source_system']}")
        
        print(f"\n📊 使用統計:")
        print(f"   使用回数: {analysis_result['usage_count']}回")
        print(f"   推奨アクション: {analysis_result['recommended_action']}")
        
        print(f"\n📝 使用例:")
        for i, context in enumerate(analysis_result["context_analyses"][:3]):
            print(f"   例{i+1}: {context['sentence'][:100]}...")
            print(f"        地名判定: {context['is_place_name']} (信頼度: {context['confidence']:.2f})")
            print(f"        理由: {context['reasoning']}")
            print()
        
        return
    
    # 削除候補プレビュー
    if args.cleanup_preview:
        print("\n=== 🔍 無効地名削除候補プレビュー ===")
        cleanup_result = geocoder.cleanup_invalid_places(auto_confirm=False)
        
        if not cleanup_result["candidates"]:
            print("✅ 削除候補の無効地名は見つかりませんでした")
            return
        
        print(f"📊 削除候補: {len(cleanup_result['candidates'])}件")
        for candidate in cleanup_result["candidates"]:
            print(f"   🗑️ {candidate['place_name']}")
            print(f"      理由: {candidate['reason']}")
            print(f"      使用回数: {candidate['usage_count']}回")
            print(f"      例: {candidate['sample']}")
            print()
        
        print("💡 削除を実行するには --cleanup オプションを使用してください")
        return
    
    # 自動クリーンアップ実行
    if args.cleanup:
        print("\n=== 🗑️ 無効地名自動クリーンアップ実行 ===")
        cleanup_result = geocoder.cleanup_invalid_places(auto_confirm=True)
        
        if cleanup_result["deletion_result"]["total_deleted"] > 0:
            print(f"✅ {cleanup_result['deletion_result']['total_deleted']}件の無効地名を削除しました")
            for deleted in cleanup_result["deletion_result"]["deleted_places"]:
                print(f"   🗑️ {deleted['place_name']} (理由: {deleted['reason']})")
        else:
            print("✅ 削除対象の無効地名は見つかりませんでした")
        
        return
    
    # 指定地名削除
    if args.delete:
        print(f"\n=== 🗑️ 指定地名削除: {', '.join(args.delete)} ===")
        deletion_result = geocoder.delete_invalid_places(args.delete, "手動削除")
        
        if deletion_result["total_deleted"] > 0:
            print(f"✅ {deletion_result['total_deleted']}件の地名を削除しました")
            for deleted in deletion_result["deleted_places"]:
                print(f"   🗑️ {deleted['place_name']} (関連: {deleted['deleted_relations']}件)")
        
        if deletion_result["not_found_places"]:
            print(f"⚠️ 見つからなかった地名: {', '.join(deletion_result['not_found_places'])}")
        
        return
    
    # AI大量検証
    if args.ai_verify:
        print(f"\n=== 🤖 AI大量検証開始 (上限: {args.ai_verify_limit}件, 信頼度閾値: {args.confidence_threshold}) ===")
        verification_result = geocoder.ai_mass_verification(
            limit=args.ai_verify_limit, 
            confidence_threshold=args.confidence_threshold
        )
        
        if "error" in verification_result:
            print(f"❌ {verification_result['error']}")
            return
        
        print(f"\n📊 AI検証結果:")
        print(f"処理済み: {verification_result['total_processed']}件")
        print(f"検証済み: {len(verification_result['verified_places'])}件")
        print(f"削除候補: {len(verification_result['deletion_candidates'])}件")
        print(f"AIエラー: {verification_result['ai_errors']}件")
        
        if verification_result['deletion_candidates']:
            print(f"\n🗑️ 削除候補地名:")
            for candidate in verification_result['deletion_candidates'][:10]:  # 上位10件表示
                verdict = candidate['overall_verdict']
                print(f"   ❌ {candidate['place_name']:12} (使用{candidate['usage_count']:2d}回)")
                print(f"      AI判定: {verdict['most_common_type']} | 地名率: {verdict['place_name_ratio']:.2f}")
                print(f"      推奨: {verdict['recommendation']} | 確信度: {verdict['confidence']:.2f}")
                if verdict['detailed_analyses']:
                    first_analysis = verdict['detailed_analyses'][0]
                    print(f"      理由: {first_analysis.get('reasoning', '不明')[:100]}...")
                print()
            
            if len(verification_result['deletion_candidates']) > 10:
                print(f"   ... 他 {len(verification_result['deletion_candidates']) - 10}件")
            
            # 削除確認
            print("💡 これらの地名を削除しますか？ (y/N): ", end="")
            try:
                user_input = input().strip().lower()
                if user_input in ['y', 'yes']:
                    delete_names = [candidate['place_name'] for candidate in verification_result['deletion_candidates']]
                    deletion_result = geocoder.delete_invalid_places(delete_names, "AI検証による削除")
                    print(f"✅ {deletion_result['total_deleted']}件の地名を削除しました")
                else:
                    print("🔄 削除をキャンセルしました")
            except (KeyboardInterrupt, EOFError):
                print("\n🔄 削除をキャンセルしました")
        
        return
    
    if args.stats_only:
        return
    
    # Geocoding処理実行
    print("\n=== 🚀 AI文脈判断型Geocoding処理開始 ===")
    result = geocoder.geocode_places_batch(limit=args.limit)
    
    print("\n=== 📊 処理結果 ===")
    print(f"処理地名数: {result['processed_places']:,}")
    print(f"Geocoding成功: {result['geocoded_places']:,}")
    print(f"スキップ: {result['skipped_places']:,}")
    print(f"エラー数: {result['errors']:,}")
    
    # 更新後統計
    if result['processed_places'] > 0:
        print("\n=== 📈 更新後統計 ===")
        final_stats = geocoder.get_geocoding_statistics()
        print(f"総地名数: {final_stats['total_places']:,}")
        print(f"Geocoding済み地名数: {final_stats['geocoded_places']:,}")
        print(f"Geocoding率: {final_stats['geocoding_rate']:.1f}%")
        
        if final_stats.get('confidence_distribution'):
            print("\n📊 信頼度分布（更新後）:")
            for confidence_level, count in final_stats['confidence_distribution'].items():
                print(f"  {confidence_level}: {count}件")

if __name__ == "__main__":
    main() 