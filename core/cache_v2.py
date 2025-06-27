"""
Redis統合キャッシュシステム v2.0
作成日: 2025年6月25日
目的: 高度なキャッシュ戦略とパフォーマンス最適化
"""

import json
import time
import logging
from typing import Any, Optional, Dict, List, Union, Callable, Tuple
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import pickle
import redis
from redis.exceptions import RedisError, ConnectionError
import asyncio

logger = logging.getLogger(__name__)

class AdvancedCacheManager:
    """高度なRedisキャッシュマネージャー"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
        max_connections: int = 10,
        enable_compression: bool = True,
        enable_monitoring: bool = True
    ):
        self.redis_pool = redis.ConnectionPool.from_url(
            redis_url, 
            max_connections=max_connections,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.redis = redis.Redis(connection_pool=self.redis_pool)
        self.default_ttl = default_ttl
        self.enable_compression = enable_compression
        self.enable_monitoring = enable_monitoring
        
        # キャッシュ統計
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }
        
        # キャッシュキーのプレフィックス定義
        self.key_prefixes = {
            "author_stats": "auth_stat:",
            "work_stats": "work_stat:",
            "place_stats": "place_stat:",
            "global_stats": "global_stat:",
            "search_results": "search:",
            "geo_search": "geo:",
            "ai_verification": "ai_verify:",
            "processing_log": "proc_log:",
            "api_response": "api:",
            "analytics": "analytics:"
        }
    
    def _get_key(self, prefix: str, identifier: Any, namespace: str = None) -> str:
        """階層的キャッシュキーの生成"""
        base_key = f"{self.key_prefixes.get(prefix, prefix)}{identifier}"
        if namespace:
            base_key = f"{namespace}:{base_key}"
        return base_key
    
    def _serialize_data(self, data: Any) -> bytes:
        """データシリアライゼーション（圧縮対応）"""
        try:
            if isinstance(data, (dict, list)):
                serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
            else:
                serialized = pickle.dumps(data)
            
            # 圧縮が有効で大きなデータの場合
            if self.enable_compression and len(serialized) > 1024:
                import gzip
                return b'compressed:' + gzip.compress(serialized)
            
            return serialized
        except Exception as e:
            logger.error(f"データシリアライゼーションエラー: {str(e)}")
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """データデシリアライゼーション（圧縮対応）"""
        try:
            # 圧縮されたデータの場合
            if data.startswith(b'compressed:'):
                import gzip
                data = gzip.decompress(data[11:])
            
            # JSON形式かpickle形式かを判定
            try:
                return json.loads(data.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"データデシリアライゼーションエラー: {str(e)}")
            return None
    
    def _update_stats(self, operation: str):
        """キャッシュ統計の更新"""
        if not self.enable_monitoring:
            return
        
        self.stats['total_requests'] += 1
        if operation in self.stats:
            self.stats[operation] += 1
    
    async def get(self, prefix: str, identifier: Any, namespace: str = None) -> Optional[Any]:
        """非同期キャッシュ取得"""
        try:
            key = self._get_key(prefix, identifier, namespace)
            data = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.get, key
            )
            
            if data:
                self._update_stats('hits')
                return self._deserialize_data(data)
            else:
                self._update_stats('misses')
                return None
                
        except RedisError as e:
            self._update_stats('errors')
            logger.error(f"Redisキャッシュ取得エラー: {str(e)}")
            return None
    
    async def set(
        self,
        prefix: str,
        identifier: Any,
        data: Any,
        ttl: Optional[int] = None,
        namespace: str = None,
        tags: List[str] = None
    ) -> bool:
        """非同期キャッシュ保存（タグ対応）"""
        try:
            key = self._get_key(prefix, identifier, namespace)
            ttl = ttl or self.default_ttl
            serialized_data = self._serialize_data(data)
            
            # メインデータの保存
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.setex, key, ttl, serialized_data
            )
            
            # タグ付きキャッシュの場合、タグインデックスも更新
            if tags:
                await self._update_tag_index(key, tags, ttl)
            
            return bool(result)
            
        except RedisError as e:
            self._update_stats('errors')
            logger.error(f"Redisキャッシュ保存エラー: {str(e)}")
            return False
    
    async def _update_tag_index(self, key: str, tags: List[str], ttl: int):
        """タグインデックスの更新"""
        try:
            pipeline = self.redis.pipeline()
            for tag in tags:
                tag_key = f"tag:{tag}"
                pipeline.sadd(tag_key, key)
                pipeline.expire(tag_key, ttl + 3600)  # タグは少し長めに保持
            await asyncio.get_event_loop().run_in_executor(None, pipeline.execute)
        except Exception as e:
            logger.error(f"タグインデックス更新エラー: {str(e)}")
    
    async def delete(self, prefix: str, identifier: Any, namespace: str = None) -> bool:
        """非同期キャッシュ削除"""
        try:
            key = self._get_key(prefix, identifier, namespace)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.delete, key
            )
            return bool(result)
        except RedisError as e:
            logger.error(f"Redisキャッシュ削除エラー: {str(e)}")
            return False
    
    async def delete_by_pattern(self, pattern: str) -> int:
        """パターン一致での一括削除"""
        try:
            keys = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.keys, pattern
            )
            if keys:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.delete, *keys
                )
                return int(result)
            return 0
        except RedisError as e:
            logger.error(f"パターン削除エラー: {str(e)}")
            return 0
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """タグ指定での一括削除"""
        try:
            keys_to_delete = set()
            for tag in tags:
                tag_key = f"tag:{tag}"
                tagged_keys = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.smembers, tag_key
                )
                keys_to_delete.update(tagged_keys)
            
            if keys_to_delete:
                # タグキーも削除
                all_keys = list(keys_to_delete) + [f"tag:{tag}" for tag in tags]
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.delete, *all_keys
                )
                return int(result)
            return 0
        except RedisError as e:
            logger.error(f"タグ削除エラー: {str(e)}")
            return 0
    
    async def get_many(
        self, 
        keys: List[Tuple[str, Any, Optional[str]]]
    ) -> Dict[str, Any]:
        """複数キーの一括取得"""
        try:
            redis_keys = [self._get_key(prefix, identifier, namespace) 
                         for prefix, identifier, namespace in keys]
            
            values = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.mget, redis_keys
            )
            
            result = {}
            for (prefix, identifier, namespace), value in zip(keys, values):
                key = f"{prefix}:{identifier}"
                if namespace:
                    key = f"{namespace}:{key}"
                
                if value:
                    result[key] = self._deserialize_data(value)
                    self._update_stats('hits')
                else:
                    result[key] = None
                    self._update_stats('misses')
            
            return result
            
        except RedisError as e:
            self._update_stats('errors')
            logger.error(f"複数キー取得エラー: {str(e)}")
            return {f"{prefix}:{identifier}": None for prefix, identifier, _ in keys}
    
    async def increment(
        self, 
        prefix: str, 
        identifier: Any, 
        amount: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """カウンター値のインクリメント"""
        try:
            key = self._get_key(prefix, identifier)
            pipeline = self.redis.pipeline()
            pipeline.incrby(key, amount)
            if ttl:
                pipeline.expire(key, ttl)
            
            results = await asyncio.get_event_loop().run_in_executor(
                None, pipeline.execute
            )
            return int(results[0])
            
        except RedisError as e:
            logger.error(f"インクリメントエラー: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報の取得"""
        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.info, "memory"
            )
            
            hit_rate = 0
            if self.stats['total_requests'] > 0:
                hit_rate = self.stats['hits'] / self.stats['total_requests']
            
            return {
                'hit_rate': round(hit_rate, 3),
                'total_requests': self.stats['total_requests'],
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'errors': self.stats['errors'],
                'memory_used': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'keys_count': await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.dbsize
                )
            }
        except Exception as e:
            logger.error(f"統計情報取得エラー: {str(e)}")
            return self.stats.copy()
    
    async def health_check(self) -> bool:
        """Redis接続ヘルスチェック"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.ping
            )
            return bool(result)
        except Exception:
            return False


class IntelligentCacheStrategy:
    """インテリジェントキャッシュ戦略"""
    
    def __init__(self, cache_manager: AdvancedCacheManager):
        self.cache_manager = cache_manager
        self.access_patterns = {}  # アクセスパターン分析用
    
    def _calculate_dynamic_ttl(
        self, 
        data_type: str, 
        data_size: int, 
        access_frequency: int = 1
    ) -> int:
        """動的TTL計算"""
        base_ttl = self.cache_manager.default_ttl
        
        # データ種別によるTTL調整
        type_multipliers = {
            'author_stats': 2.0,      # 作家統計は長期キャッシュ
            'place_stats': 1.5,       # 地名統計は中期キャッシュ
            'search_results': 0.5,    # 検索結果は短期キャッシュ
            'ai_verification': 3.0,   # AI検証結果は長期キャッシュ
            'api_response': 0.3       # API応答は短期キャッシュ
        }
        
        multiplier = type_multipliers.get(data_type, 1.0)
        
        # データサイズによる調整（大きなデータは短いTTL）
        size_factor = max(0.5, 1.0 - (data_size / 1048576))  # 1MB基準
        
        # アクセス頻度による調整
        frequency_factor = min(2.0, 1.0 + (access_frequency / 100))
        
        dynamic_ttl = int(base_ttl * multiplier * size_factor * frequency_factor)
        return max(300, min(86400, dynamic_ttl))  # 5分〜24時間の範囲
    
    async def smart_cache(
        self,
        key_parts: Tuple[str, Any, Optional[str]],
        data_generator: Callable,
        data_type: str,
        force_refresh: bool = False,
        tags: List[str] = None
    ) -> Any:
        """スマートキャッシュ（自動TTL調整）"""
        prefix, identifier, namespace = key_parts
        
        # 強制更新でない場合は既存キャッシュを確認
        if not force_refresh:
            cached_data = await self.cache_manager.get(prefix, identifier, namespace)
            if cached_data is not None:
                # アクセスパターンを記録
                pattern_key = f"{prefix}:{identifier}"
                self.access_patterns[pattern_key] = \
                    self.access_patterns.get(pattern_key, 0) + 1
                return cached_data
        
        # データ生成
        if asyncio.iscoroutinefunction(data_generator):
            fresh_data = await data_generator()
        else:
            fresh_data = data_generator()
        
        # データサイズとアクセス頻度に基づく動的TTL計算
        data_size = len(json.dumps(fresh_data, ensure_ascii=False).encode('utf-8'))
        pattern_key = f"{prefix}:{identifier}"
        access_frequency = self.access_patterns.get(pattern_key, 1)
        
        dynamic_ttl = self._calculate_dynamic_ttl(data_type, data_size, access_frequency)
        
        # キャッシュに保存
        await self.cache_manager.set(
            prefix, identifier, fresh_data, 
            ttl=dynamic_ttl, namespace=namespace, tags=tags
        )
        
        return fresh_data


def advanced_cache_decorator(
    prefix: str,
    data_type: str = "api_response",
    ttl: Optional[int] = None,
    tags: List[str] = None,
    key_func: Optional[Callable] = None,
    namespace_func: Optional[Callable] = None
):
    """高度なキャッシュデコレータ"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # キャッシュマネージャーの取得
            cache_manager = kwargs.get('cache_manager')
            if not cache_manager or not isinstance(cache_manager, AdvancedCacheManager):
                return await func(*args, **kwargs)
            
            # キャッシュキーの生成
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # デフォルトのキー生成ロジック
                key_parts = []
                if args:
                    key_parts.extend(str(arg) for arg in args[:3])  # 最初の3つの引数
                if kwargs:
                    sorted_kwargs = sorted(kwargs.items())
                    key_parts.extend(f"{k}={v}" for k, v in sorted_kwargs[:3])
                cache_key = ":".join(key_parts) or "default"
            
            # ネームスペースの生成
            namespace = None
            if namespace_func:
                namespace = namespace_func(*args, **kwargs)
            
            # スマートキャッシュ戦略を使用
            strategy = IntelligentCacheStrategy(cache_manager)
            
            def data_generator():
                return func(*args, **kwargs)
            
            return await strategy.smart_cache(
                (prefix, cache_key, namespace),
                data_generator,
                data_type,
                force_refresh=kwargs.get('force_refresh', False),
                tags=tags
            )
        
        return wrapper
    return decorator


# 使用例とテスト用のヘルパー関数
async def test_advanced_cache():
    """高度なキャッシュシステムのテスト"""
    cache = AdvancedCacheManager(enable_monitoring=True)
    
    # 基本的なキャッシュ操作
    await cache.set("test", "key1", {"data": "test_value"}, ttl=300)
    result = await cache.get("test", "key1")
    print(f"Basic cache test: {result}")
    
    # タグ付きキャッシュ
    await cache.set("author_stats", "author1", {"name": "夏目漱石"}, 
                   tags=["author", "statistics"], ttl=600)
    
    # 統計情報の確認
    stats = await cache.get_cache_stats()
    print(f"Cache stats: {stats}")
    
    # ヘルスチェック
    health = await cache.health_check()
    print(f"Redis health: {health}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_advanced_cache()) 