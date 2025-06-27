"""
Redis専用キャッシュモジュール v5.0
作成日: 2025年6月25日
目的: Redisに特化した高性能キャッシュシステム
"""

import json
import pickle
import gzip
import logging
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis専用高性能キャッシュクラス"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
        key_prefix: str = "bungo_map_v5:",
        compression_threshold: int = 1024
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.compression_threshold = compression_threshold
        self._redis = None
        
        # キャッシュ種別定義
        self.cache_types = {
            "statistics": {"ttl": 7200, "compress": True},      # 統計情報：2時間
            "search": {"ttl": 1800, "compress": False},         # 検索結果：30分
            "geo": {"ttl": 3600, "compress": True},             # 地理情報：1時間
            "ai": {"ttl": 86400, "compress": True},             # AI結果：24時間
            "session": {"ttl": 1800, "compress": False},        # セッション：30分
            "analytics": {"ttl": 14400, "compress": True},      # 分析結果：4時間
        }
        
        # パフォーマンス統計
        self.performance_stats = {
            'operations': 0,
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_size': 0,
            'avg_response_time': 0.0
        }
    
    async def initialize(self):
        """Redis接続の初期化"""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(
                self.redis_url,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
                decode_responses=False  # バイナリデータ対応
            )
            # 接続テスト
            await self._redis.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            raise
    
    async def close(self):
        """Redis接続のクリーンアップ"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")
    
    def _make_key(self, key: str, cache_type: str = "default") -> str:
        """キーの正規化"""
        return f"{self.key_prefix}{cache_type}:{key}"
    
    def _serialize(self, data: Any, compress: bool = False) -> bytes:
        """データのシリアライゼーション"""
        try:
            # JSON可能なオブジェクトかチェック
            if isinstance(data, (dict, list, str, int, float, bool, type(None))):
                serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
                header = b'json:'
            else:
                serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
                header = b'pickle:'
            
            # 圧縮判定
            if compress and len(serialized) > self.compression_threshold:
                serialized = gzip.compress(serialized)
                header = b'gzip:' + header
            
            return header + serialized
            
        except Exception as e:
            logger.error(f"Serialization error: {str(e)}")
            raise
    
    def _deserialize(self, data: bytes) -> Any:
        """データのデシリアライゼーション"""
        try:
            # ヘッダー解析
            is_compressed = data.startswith(b'gzip:')
            if is_compressed:
                data = data[5:]  # 'gzip:'を除去
                
            is_json = data.startswith(b'json:')
            is_pickle = data.startswith(b'pickle:')
            
            if is_json:
                payload = data[5:]  # 'json:'を除去
            elif is_pickle:
                payload = data[7:]  # 'pickle:'を除去
            else:
                payload = data
            
            # 解凍
            if is_compressed:
                payload = gzip.decompress(payload)
            
            # デシリアライゼーション
            if is_json or (not is_pickle and not is_compressed):
                return json.loads(payload.decode('utf-8'))
            else:
                return pickle.loads(payload)
                
        except Exception as e:
            logger.error(f"Deserialization error: {str(e)}")
            return None
    
    async def get(self, key: str, cache_type: str = "default") -> Optional[Any]:
        """キャッシュからの取得"""
        if not self._redis:
            await self.initialize()
        
        start_time = asyncio.get_event_loop().time()
        try:
            full_key = self._make_key(key, cache_type)
            data = await self._redis.get(full_key)
            
            self.performance_stats['operations'] += 1
            
            if data:
                result = self._deserialize(data)
                self.performance_stats['hits'] += 1
                
                # レスポンス時間更新
                response_time = asyncio.get_event_loop().time() - start_time
                self._update_avg_response_time(response_time)
                
                return result
            else:
                self.performance_stats['misses'] += 1
                return None
                
        except Exception as e:
            self.performance_stats['errors'] += 1
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        compress: Optional[bool] = None
    ) -> bool:
        """キャッシュへの保存"""
        if not self._redis:
            await self.initialize()
        
        try:
            # キャッシュ種別の設定取得
            type_config = self.cache_types.get(cache_type, {})
            ttl = ttl or type_config.get('ttl', self.default_ttl)
            compress = compress if compress is not None else type_config.get('compress', False)
            
            full_key = self._make_key(key, cache_type)
            serialized_data = self._serialize(value, compress)
            
            result = await self._redis.setex(full_key, ttl, serialized_data)
            
            # 統計更新
            self.performance_stats['operations'] += 1
            self.performance_stats['total_size'] += len(serialized_data)
            
            return bool(result)
            
        except Exception as e:
            self.performance_stats['errors'] += 1
            logger.error(f"Redis set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str, cache_type: str = "default") -> bool:
        """キャッシュからの削除"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key, cache_type)
            result = await self._redis.delete(full_key)
            
            self.performance_stats['operations'] += 1
            return bool(result)
            
        except Exception as e:
            self.performance_stats['errors'] += 1
            logger.error(f"Redis delete error for key {key}: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計の取得"""
        if not self._redis:
            return self.performance_stats.copy()
        
        try:
            info = await self._redis.info()
            memory_info = await self._redis.info("memory")
            
            hit_rate = 0
            if self.performance_stats['operations'] > 0:
                hit_rate = self.performance_stats['hits'] / self.performance_stats['operations']
            
            return {
                **self.performance_stats,
                'hit_rate': round(hit_rate, 3),
                'memory_used_mb': round(memory_info.get('used_memory', 0) / 1024 / 1024, 2),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {str(e)}")
            return self.performance_stats.copy()
    
    def _update_avg_response_time(self, new_time: float):
        """平均レスポンス時間の更新"""
        current_avg = self.performance_stats['avg_response_time']
        operations = self.performance_stats['operations']
        
        if operations == 1:
            self.performance_stats['avg_response_time'] = new_time
        else:
            # 移動平均的な更新
            self.performance_stats['avg_response_time'] = \
                (current_avg * 0.9) + (new_time * 0.1)
    
    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        if not self._redis:
            try:
                await self.initialize()
            except Exception as e:
                return {"status": "error", "message": str(e)}
        
        try:
            start_time = asyncio.get_event_loop().time()
            await self._redis.ping()
            ping_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "status": "healthy",
                "ping_time_ms": round(ping_time * 1000, 2),
                "connection": "active"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }


def redis_cache_decorator(
    cache_type: str = "default",
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None
):
    """Redisキャッシュデコレータ"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Redisキャッシュインスタンスの取得
            redis_cache = kwargs.get('redis_cache')
            if not redis_cache or not isinstance(redis_cache, RedisCache):
                return await func(*args, **kwargs)
            
            # キャッシュキーの生成
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # デフォルトキー生成
                key_parts = []
                if args:
                    key_parts.extend(str(arg) for arg in args[:2])
                if kwargs:
                    relevant_kwargs = {k: v for k, v in kwargs.items() 
                                     if k not in ['redis_cache', 'force_refresh']}
                    key_parts.append(json.dumps(relevant_kwargs, sort_keys=True))
                cache_key = ":".join(key_parts) or func.__name__
            
            # 強制更新チェック
            force_refresh = kwargs.pop('force_refresh', False)
            
            # キャッシュから取得を試行
            if not force_refresh:
                cached_result = await redis_cache.get(cache_key, cache_type)
                if cached_result is not None:
                    return cached_result
            
            # 関数実行
            result = await func(*args, **kwargs)
            
            # 結果をキャッシュに保存
            if result is not None:
                await redis_cache.set(cache_key, result, cache_type, ttl)
            
            return result
        
        return wrapper
    return decorator


# 使用例
async def example_usage():
    """Redis キャッシュの使用例"""
    cache = RedisCache()
    
    try:
        await cache.initialize()
        
        # 基本操作
        await cache.set("test_key", {"message": "Hello Redis"}, "statistics")
        result = await cache.get("test_key", "statistics")
        print(f"Cached result: {result}")
        
        # 統計情報
        stats = await cache.get_stats()
        print(f"Cache stats: {stats}")
        
        # ヘルスチェック
        health = await cache.health_check()
        print(f"Health status: {health}")
        
    finally:
        await cache.close()

if __name__ == "__main__":
    asyncio.run(example_usage()) 