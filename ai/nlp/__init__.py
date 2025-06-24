"""
自然言語処理（NLP）モジュール

文脈分析、地名判別、パターン認識機能を提供
"""

from .context_analyzer import ContextAnalyzer, ContextAnalysisResult

__all__ = [
    'ContextAnalyzer',
    'ContextAnalysisResult'
] 