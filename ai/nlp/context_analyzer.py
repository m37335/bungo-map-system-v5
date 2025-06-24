"""
文豪ゆかり地図システム - 文脈分析エンジン

文脈パターン分析による地名/人名判別機能を提供
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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

class ContextAnalyzer:
    """文脈分析エンジン"""
    
    def __init__(self):
        """初期化"""
        self._init_knowledge_base()
        logger.info("🔍 文脈分析エンジン初期化完了")
    
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
            '樹木', '草本', '苔類', '菌類', '藻類', '細胞', '組織',
            
            # 一般学術用語
            '研究', '論文', '学会', '発表', '実験', '調査', '分析',
            '結果', '考察', '結論', '仮説', '理論', '法則', '原理',
            
            # 時間・動作表現
            '沢山', '大分', '随分', '大抵', '大概', '大体', '最早',
            '漸く', '愈々', '段々', '次第', '次第に', '遂に', '到頭',
            '矢張', '矢張り', '如何', '如何にも', '何故', '何処',
        }
        
        # 無効パターン
        self.invalid_patterns = [
            # 短すぎる・意味のない文字列
            r"^[あ-ん]{1,2}$",  # ひらがな1-2文字
            r"^[ア-ン]{1,2}$",  # カタカナ1-2文字
            r"^[0-9]+$",        # 数字のみ
            r"^[ぁ-ん]*$",      # 小文字ひらがなのみ
            
            # 明らかに地名でない表現
            r"^(今日|昨日|明日|一昨日|明後日)$",
            r"^(朝|昼|夕方|夜|深夜|早朝)$",
            r"^(春|夏|秋|冬|正月|盆)$",
            r"^(こちら|そちら|あちら|どちら)$",
            r"^(ここ|そこ|あそこ|どこ)$",
        ]
    
    def analyze_context(self, place_name: str, sentence: str, before_text: str = "", after_text: str = "") -> ContextAnalysisResult:
        """文脈分析実行"""
        
        # 基本チェック
        if not place_name or not sentence:
            return ContextAnalysisResult(
                is_place_name=False,
                confidence=0.0,
                place_type="不明",
                historical_context="",
                geographic_context="",
                reasoning="入力データが不足"
            )
        
        # 無効パターンチェック
        if self._is_invalid_pattern(place_name):
            return ContextAnalysisResult(
                is_place_name=False,
                confidence=0.9,
                place_type="無効",
                historical_context="",
                geographic_context="",
                reasoning="無効パターンに該当"
            )
        
        # 人名・学術用語チェック
        if self._is_known_person_or_term(place_name):
            return ContextAnalysisResult(
                is_place_name=False,
                confidence=0.85,
                place_type="人名・学術用語",
                historical_context="",
                geographic_context="",
                reasoning="既知の人名・学術用語"
            )
        
        # 文脈パターン分析
        context_score = self._analyze_patterns(place_name, sentence, before_text, after_text)
        
        # 曖昧地名チェック
        ambiguity_info = self._check_ambiguous_place(place_name)
        
        # 歴史的文脈判定
        historical_context = self._detect_historical_context(sentence, before_text, after_text)
        
        # 地理的文脈判定
        geographic_context = self._detect_geographic_context(sentence, before_text, after_text)
        
        # 総合判定
        is_place = context_score["place_score"] > context_score["person_score"]
        confidence = max(context_score["place_score"], context_score["person_score"])
        
        # 曖昧地名の場合は信頼度を調整
        if ambiguity_info and ambiguity_info.get("人名可能性", 0) > 0.5:
            confidence *= 0.7
        
        place_type = self._determine_place_type(sentence, before_text, after_text)
        reasoning = self._generate_reasoning(context_score, ambiguity_info, historical_context)
        
        return ContextAnalysisResult(
            is_place_name=is_place,
            confidence=confidence,
            place_type=place_type,
            historical_context=historical_context,
            geographic_context=geographic_context,
            reasoning=reasoning,
            suggested_location=ambiguity_info.get("地名") if ambiguity_info else None
        )
    
    def _is_invalid_pattern(self, place_name: str) -> bool:
        """無効パターンかどうか判定"""
        for pattern in self.invalid_patterns:
            if re.match(pattern, place_name):
                return True
        return False
    
    def _is_known_person_or_term(self, place_name: str) -> bool:
        """既知の人名・学術用語かどうか判定"""
        return (place_name in self.known_person_names or 
                place_name in self.academic_terms)
    
    def _analyze_patterns(self, place_name: str, sentence: str, before_text: str, after_text: str) -> Dict[str, float]:
        """文脈パターン分析"""
        full_text = f"{before_text} {sentence} {after_text}"
        
        place_score = 0.0
        person_score = 0.0
        
        # 地名指標のスコア計算
        for pattern in self.context_patterns["place_indicators"]:
            if re.search(pattern, full_text):
                place_score += 0.1
        
        # 人名指標のスコア計算
        for pattern in self.context_patterns["person_indicators"]:
            if re.search(pattern, full_text):
                person_score += 0.15
        
        # 基準化
        place_score = min(place_score, 1.0)
        person_score = min(person_score, 1.0)
        
        return {
            "place_score": place_score,
            "person_score": person_score
        }
    
    def _check_ambiguous_place(self, place_name: str) -> Optional[Dict]:
        """曖昧地名チェック"""
        return self.ambiguous_places.get(place_name)
    
    def _detect_historical_context(self, sentence: str, before_text: str, after_text: str) -> str:
        """歴史的文脈検出"""
        full_text = f"{before_text} {sentence} {after_text}"
        
        historical_indicators = []
        for pattern in self.context_patterns["historical_indicators"]:
            if re.search(pattern, full_text):
                historical_indicators.append(pattern.replace("\\", ""))
        
        if historical_indicators:
            return f"歴史的文脈: {', '.join(historical_indicators)}"
        return ""
    
    def _detect_geographic_context(self, sentence: str, before_text: str, after_text: str) -> str:
        """地理的文脈検出"""
        full_text = f"{before_text} {sentence} {after_text}"
        
        # 地域キーワード検出
        regions = ["東京", "京都", "大阪", "関東", "関西", "九州", "北海道"]
        found_regions = [region for region in regions if region in full_text]
        
        if found_regions:
            return f"地域文脈: {', '.join(found_regions)}"
        return ""
    
    def _determine_place_type(self, sentence: str, before_text: str, after_text: str) -> str:
        """地名タイプ判定"""
        full_text = f"{before_text} {sentence} {after_text}"
        
        type_indicators = {
            "都市": ["市", "町", "村", "街", "都"],
            "建物": ["寺", "神社", "駅", "橋"],
            "自然": ["山", "川", "海", "湖", "谷"],
            "歴史": ["城", "宿場", "街道", "国", "藩"]
        }
        
        for place_type, indicators in type_indicators.items():
            for indicator in indicators:
                if indicator in full_text:
                    return place_type
        
        return "一般"
    
    def _generate_reasoning(self, context_score: Dict, ambiguity_info: Optional[Dict], historical_context: str) -> str:
        """判定理由生成"""
        reasoning_parts = []
        
        if context_score["place_score"] > context_score["person_score"]:
            reasoning_parts.append(f"地名文脈スコア: {context_score['place_score']:.2f}")
        else:
            reasoning_parts.append(f"人名文脈スコア: {context_score['person_score']:.2f}")
        
        if ambiguity_info:
            reasoning_parts.append("曖昧地名として登録済み")
        
        if historical_context:
            reasoning_parts.append(historical_context)
        
        return "; ".join(reasoning_parts) 