"""
データ処理モジュール

テキスト処理、作者データ統合、
メタデータ補完処理を提供
"""

from .text_processor import TextProcessor, ProcessingStats
from .author_database_service import AuthorDatabaseService
from .process_complete_author import CompleteAuthorProcessor

__all__ = [
    'TextProcessor',
    'ProcessingStats',
    'AuthorDatabaseService',
    'CompleteAuthorProcessor'
] 