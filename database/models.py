from datetime import datetime
from typing import List, Optional

# データベース結果用の動的オブジェクト（SQLiteの結果をオブジェクトに変換）
class DynamicObject:
    """データベース結果を動的にオブジェクトに変換するクラス"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        attrs = ", ".join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

class Author(DynamicObject):
    """作者用の動的オブジェクト"""
    pass

class Work(DynamicObject):
    """作品用の動的オブジェクト"""
    @property
    def work_title(self):
        """titleのエイリアス（互換性用）"""
        return getattr(self, 'title', None)
        
    @work_title.setter
    def work_title(self, value):
        """work_titleへの値設定はtitleに反映"""
        setattr(self, 'title', value)
        
    @property  
    def aozora_work_url(self):
        """aozora_urlのエイリアス（互換性用）"""
        return getattr(self, 'aozora_url', None) or getattr(self, 'aozora_work_url', None)
        
    @aozora_work_url.setter
    def aozora_work_url(self, value):
        """aozora_work_urlへの値設定はaozora_urlに反映"""
        setattr(self, 'aozora_url', value)

class Sentence(DynamicObject):
    """センテンス用の動的オブジェクト"""
    pass

class Place(DynamicObject):
    """地名用の動的オブジェクト"""
    pass

class SentencePlace(DynamicObject):
    """センテンス-地名関連用の動的オブジェクト"""
    pass

# ========================================
# 新しいv5.0モデル
# ========================================

class Section(DynamicObject):
    """階層構造セクション用の動的オブジェクト"""
    @property
    def children(self):
        """子セクションのリスト（遅延読み込み対応）"""
        return getattr(self, '_children', [])
    
    @children.setter
    def children(self, value):
        """子セクションの設定"""
        setattr(self, '_children', value)

class AIVerification(DynamicObject):
    """AI検証結果用の動的オブジェクト"""
    @property
    def is_verified(self):
        """検証済みかどうかの判定"""
        return getattr(self, 'verification_status', None) == 'verified'
    
    @property
    def cost_per_request(self):
        """1リクエストあたりのコスト計算"""
        cost = getattr(self, 'api_cost', 0)
        return float(cost) if cost else 0.0

class StatisticsCache(DynamicObject):
    """統計キャッシュ用の動的オブジェクト"""
    @property
    def is_expired(self):
        """キャッシュが期限切れかどうかの判定"""
        expires_at = getattr(self, 'expires_at', None)
        if not expires_at:
            return False
        
        if isinstance(expires_at, str):
            from datetime import datetime
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        
        return datetime.now() > expires_at
    
    @property
    def cache_data(self):
        """キャッシュデータの取得（JSON解析）"""
        import json
        data = getattr(self, 'data', '{}')
        if isinstance(data, str):
            return json.loads(data)
        return data

class ProcessingLog(DynamicObject):
    """処理ログ用の動的オブジェクト"""
    @property
    def is_completed(self):
        """処理が完了しているかどうかの判定"""
        return getattr(self, 'status', None) == 'completed'
    
    @property
    def is_failed(self):
        """処理が失敗しているかどうかの判定"""
        return getattr(self, 'status', None) == 'failed'
    
    @property
    def duration_seconds(self):
        """処理時間を秒単位で取得"""
        duration_ms = getattr(self, 'processing_duration_ms', 0)
        return duration_ms / 1000 if duration_ms else 0
    
    @property
    def processing_stats(self):
        """処理統計の取得（JSON解析）"""
        import json
        stats = getattr(self, 'statistics', '{}')
        if isinstance(stats, str):
            return json.loads(stats)
        return stats or {}

# ========================================
# 互換性用エイリアス
# ========================================

# place_mentions テーブル用（旧sentence_places）
class PlaceMention(DynamicObject):
    """地名言及用の動的オブジェクト（旧SentencePlace）"""
    @property
    def relation_id(self):
        """旧relation_idとの互換性"""
        return getattr(self, 'mention_id', None)
    
    @relation_id.setter
    def relation_id(self, value):
        """relation_id設定の互換性"""
        setattr(self, 'mention_id', value)
