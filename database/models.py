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
