"""
文豪ゆかり地図システム - LLM クライアント

OpenAI API との接続、レート制限、キャッシュ管理を提供
"""

import os
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any
from threading import Lock
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class LLMRequest:
    """LLM リクエスト"""
    prompt: str
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.1
    cache_key: Optional[str] = None

@dataclass
class LLMResponse:
    """LLM レスポンス"""
    content: str
    model: str
    tokens_used: int
    cached: bool = False
    error: Optional[str] = None

class RateLimiter:
    """API レート制限管理"""
    
    def __init__(self):
        self._limits = {
            'openai': {'last_call': 0, 'min_interval': 1.0},
            'google_maps': {'last_call': 0, 'min_interval': 0.1}
        }
        self._lock = Lock()
    
    def wait_if_needed(self, api_name: str, min_interval: float = None) -> None:
        """必要に応じて待機"""
        if min_interval is None:
            min_interval = self._limits.get(api_name, {}).get('min_interval', 1.0)
        
        with self._lock:
            current_time = time.time()
            last_call = self._limits.get(api_name, {}).get('last_call', 0)
            time_since_last = current_time - last_call
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.info(f"🕒 {api_name} レート制限: {sleep_time:.2f}秒待機")
                time.sleep(sleep_time)
            
            self._limits.setdefault(api_name, {})['last_call'] = time.time()

class APICache:
    """API キャッシュ管理"""
    
    def __init__(self, cache_file: str = "data/api_cache.json"):
        self.cache_file = Path(cache_file)
        self._cache = {}
        self._lock = Lock()
        self._load_cache()
    
    def _load_cache(self) -> None:
        """キャッシュファイルから読み込み"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"📁 APIキャッシュ読み込み: {len(self._cache)}件")
        except Exception as e:
            logger.warning(f"キャッシュ読み込みエラー: {e}")
            self._cache = {}
    
    def _save_cache(self) -> None:
        """キャッシュをファイルに保存"""
        try:
            # ディレクトリが存在しない場合は作成
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {e}")
    
    def get_cache_key(self, text: str, api_type: str) -> str:
        """キャッシュキー生成"""
        content = f"{api_type}:{text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから取得"""
        return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """キャッシュに保存"""
        self._cache[key] = value
        self._save_cache()
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        self._cache.clear()
        self._save_cache()
    
    def size(self) -> int:
        """キャッシュサイズ"""
        return len(self._cache)

class LLMClient:
    """LLM クライアント（OpenAI API）"""
    
    def __init__(self, api_key: Optional[str] = None, cache_file: str = "data/api_cache.json"):
        """初期化"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None
        self.enabled = False
        
        # レート制限とキャッシュ初期化
        self.rate_limiter = RateLimiter()
        self.cache = APICache(cache_file)
        
        # OpenAI クライアント初期化
        self._init_client()
    
    def _init_client(self) -> None:
        """OpenAI クライアント初期化"""
        if not OPENAI_AVAILABLE:
            logger.warning("⚠️ OpenAI パッケージがインストールされていません")
            return
        
        if not self.api_key:
            logger.warning("⚠️ OpenAI APIキーが設定されていません")
            return
        
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            self.enabled = True
            logger.info("✅ OpenAI API接続準備完了")
        except Exception as e:
            logger.error(f"❌ OpenAI API初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """API利用可能性チェック"""
        return self.enabled and self.client is not None
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """テキスト生成（同期版）"""
        if not self.is_available():
            return LLMResponse(
                content="",
                model=request.model,
                tokens_used=0,
                error="OpenAI API が利用できません"
            )
        
        # キャッシュチェック
        cache_key = request.cache_key or self.cache.get_cache_key(request.prompt, "openai")
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            logger.info("📁 キャッシュヒット")
            return LLMResponse(
                content=cached_result.get("content", ""),
                model=cached_result.get("model", request.model),
                tokens_used=cached_result.get("tokens_used", 0),
                cached=True
            )
        
        # レート制限チェック
        self.rate_limiter.wait_if_needed("openai")
        
        try:
            # API 呼び出し
            response = self.client.chat.completions.create(
                model=request.model,
                messages=[{"role": "user", "content": request.prompt}],
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # 結果をキャッシュ
            cache_data = {
                "content": content,
                "model": request.model,
                "tokens_used": tokens_used,
                "timestamp": time.time()
            }
            self.cache.set(cache_key, cache_data)
            
            logger.info(f"🤖 OpenAI API成功: {tokens_used} tokens")
            
            return LLMResponse(
                content=content,
                model=request.model,
                tokens_used=tokens_used,
                cached=False
            )
            
        except Exception as e:
            logger.error(f"❌ OpenAI API エラー: {e}")
            return LLMResponse(
                content="",
                model=request.model,
                tokens_used=0,
                error=str(e)
            )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計"""
        return {
            "cache_size": self.cache.size(),
            "cache_file": str(self.cache.cache_file),
            "api_available": self.is_available()
        } 