"""
Wikipedia データ抽出モジュール

Wikipedia から作者情報の取得・補完を提供
"""

from .wikipedia_author_enricher import WikipediaAuthorEnricher

__all__ = [
    'WikipediaAuthorEnricher'
] 