#!/usr/bin/env python3
"""
AI検証マネージャー (AIVerificationManager)
地名の AI による検証処理を管理する

作成日: 2025年6月25日
"""

import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
import asyncio
import openai
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VerificationRequest:
    """検証リクエスト"""
    place_mention_id: int
    place_name: str
    context: str
    ai_model: str = "gpt-3.5-turbo"
    verification_type: str = "place_validation"

@dataclass
class VerificationResult:
    """検証結果"""
    place_mention_id: int
    ai_model: str
    verification_type: str
    is_valid_place: bool
    confidence_score: float
    reasoning: str
    processing_time_ms: int
    api_cost: float
    raw_response: str

class AIVerificationManager:
    """AI検証マネージャー"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        if api_key:
            openai.api_key = api_key
        
        # 検証プロンプトテンプレート
        self.validation_prompts = {
            "place_validation": """
以下の文脈で言及されている「{place_name}」が実在する地名かどうかを判定してください。

文脈: {context}

判定基準:
1. 実在する地名（都市、山、川、建物等）かどうか
2. 文脈に適した地名かどうか
3. 架空の地名の可能性はないか

以下のJSON形式で回答してください:
{{
    "is_valid_place": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "判定理由"
}}
            """,
            
            "context_analysis": """
以下の文脈で「{place_name}」がどのような意味で使われているかを分析してください。

文脈: {context}

分析項目:
1. 地名としての使用か、比喩的使用か
2. 具体的な場所を指しているか
3. 文学的表現としての意図があるか

JSON形式で回答してください:
{{
    "usage_type": "literal/metaphorical/literary",
    "confidence": 0.0-1.0,
    "analysis": "分析結果"
}}
            """
        }
    
    async def verify_single_place(self, request: VerificationRequest) -> VerificationResult:
        """単一地名の検証"""
        start_time = time.time()
        
        try:
            # プロンプト生成
            prompt = self._generate_prompt(request)
            
            # AI API呼び出し
            response = await self._call_ai_api(request.ai_model, prompt)
            
            # レスポンス解析
            result = self._parse_response(response, request)
            
            # 処理時間計算
            processing_time = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time
            
            logger.info(f"地名検証完了: {request.place_name} -> {result.is_valid_place}")
            return result
            
        except Exception as e:
            logger.error(f"地名検証エラー: {e}")
            return self._create_error_result(request, str(e))
    
    async def batch_verify(self, requests: List[VerificationRequest]) -> List[VerificationResult]:
        """一括地名検証"""
        logger.info(f"一括検証開始: {len(requests)}件")
        
        results = []
        
        # 並列実行（レート制限を考慮して5並列に制限）
        semaphore = asyncio.Semaphore(5)
        
        async def verify_with_semaphore(request):
            async with semaphore:
                return await self.verify_single_place(request)
        
        tasks = [verify_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外をエラー結果に変換
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = self._create_error_result(requests[i], str(result))
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        logger.info(f"一括検証完了: {len(processed_results)}件")
        return processed_results
    
    def _generate_prompt(self, request: VerificationRequest) -> str:
        """プロンプト生成"""
        template = self.validation_prompts.get(request.verification_type, 
                                              self.validation_prompts["place_validation"])
        
        return template.format(
            place_name=request.place_name,
            context=request.context
        )
    
    async def _call_ai_api(self, model: str, prompt: str) -> Dict[str, Any]:
        """AI API呼び出し"""
        try:
            # OpenAI APIを模擬
            # 実際の実装では openai.ChatCompletion.acreate() を使用
            response = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "is_valid_place": True,
                            "confidence": 0.85,
                            "reasoning": "実在する地名として確認できます"
                        }, ensure_ascii=False)
                    }
                }],
                "usage": {
                    "total_tokens": 150
                }
            }
            
            # 模擬遅延
            await asyncio.sleep(0.1)
            
            return response
            
        except Exception as e:
            logger.error(f"AI API呼び出しエラー: {e}")
            raise
    
    def _parse_response(self, response: Dict[str, Any], request: VerificationRequest) -> VerificationResult:
        """レスポンス解析"""
        try:
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            
            # トークン数からコスト計算（概算）
            tokens = response.get("usage", {}).get("total_tokens", 0)
            cost = self._calculate_cost(request.ai_model, tokens)
            
            return VerificationResult(
                place_mention_id=request.place_mention_id,
                ai_model=request.ai_model,
                verification_type=request.verification_type,
                is_valid_place=parsed.get("is_valid_place", False),
                confidence_score=parsed.get("confidence", 0.0),
                reasoning=parsed.get("reasoning", ""),
                processing_time_ms=0,  # 後で設定
                api_cost=cost,
                raw_response=content
            )
            
        except Exception as e:
            logger.error(f"レスポンス解析エラー: {e}")
            raise
    
    def _calculate_cost(self, model: str, tokens: int) -> float:
        """API使用コスト計算"""
        # モデル別料金（概算・USD）
        rates = {
            "gpt-3.5-turbo": 0.002 / 1000,  # per token
            "gpt-4": 0.03 / 1000,
            "gpt-4-turbo": 0.01 / 1000
        }
        
        rate = rates.get(model, 0.002 / 1000)
        return tokens * rate
    
    def _create_error_result(self, request: VerificationRequest, error_msg: str) -> VerificationResult:
        """エラー結果の作成"""
        return VerificationResult(
            place_mention_id=request.place_mention_id,
            ai_model=request.ai_model,
            verification_type=request.verification_type,
            is_valid_place=False,
            confidence_score=0.0,
            reasoning=f"検証エラー: {error_msg}",
            processing_time_ms=0,
            api_cost=0.0,
            raw_response=""
        )
    
    def get_verification_stats(self, results: List[VerificationResult]) -> Dict[str, Any]:
        """検証統計の取得"""
        if not results:
            return {}
        
        total_count = len(results)
        valid_count = sum(1 for r in results if r.is_valid_place)
        total_cost = sum(r.api_cost for r in results)
        avg_confidence = sum(r.confidence_score for r in results) / total_count
        avg_processing_time = sum(r.processing_time_ms for r in results) / total_count
        
        return {
            "total_verifications": total_count,
            "valid_places": valid_count,
            "invalid_places": total_count - valid_count,
            "validity_rate": valid_count / total_count,
            "average_confidence": avg_confidence,
            "total_cost_usd": total_cost,
            "average_processing_time_ms": avg_processing_time,
            "models_used": list(set(r.ai_model for r in results))
        }

async def main():
    """テスト実行"""
    manager = AIVerificationManager()
    
    # テストリクエスト
    requests = [
        VerificationRequest(
            place_mention_id=1,
            place_name="東京",
            context="東京の街を歩いていると、多くの人々に出会った。"
        ),
        VerificationRequest(
            place_mention_id=2,
            place_name="桃源郷",
            context="彼は桃源郷のような美しい場所を夢見ていた。"
        )
    ]
    
    # 一括検証テスト
    results = await manager.batch_verify(requests)
    
    print("検証結果:")
    for result in results:
        print(f"- {result.place_mention_id}: {result.is_valid_place} (信頼度: {result.confidence_score})")
    
    # 統計取得
    stats = manager.get_verification_stats(results)
    print(f"\n統計: {json.dumps(stats, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
