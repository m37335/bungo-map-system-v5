#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改良版テキスト前処理システム
青空文庫テキストの高品質クリーニングと正規化を実装
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProcessingStats:
    """処理統計"""
    original_length: int
    processed_length: int
    removed_ruby_count: int
    removed_html_count: int
    removed_annotation_count: int
    sentence_count: int

class TextProcessor:
    """改良版テキスト処理クラス"""
    
    def __init__(self):
        """初期化"""
        # 改良版テキストクリーニングパターン
        self.cleanup_patterns = [
            # rubyタグ（読み仮名）の適切な処理
            (r'<ruby><rb>([^<]+)</rb><rp>[（(]</rp><rt>([^<]*)</rt><rp>[）)]</rp></ruby>', r'\1（\2）'),
            (r'<ruby><rb>([^<]+)</rb><rp>（</rp><rt>([^<]*)</rt><rp>）</rp></ruby>', r'\1（\2）'),
            (r'<ruby>([^<]+)<rt>([^<]*)</rt></ruby>', r'\1（\2）'),
            
            # HTMLタグ除去
            (r'<br\s*/?\s*>', ''),
            (r'<[^>]+>', ''),
            
            # 青空文庫注釈記号除去
            (r'《[^》]*》', ''),
            (r'［[^］]*］', ''),
            (r'〔[^〕]*〕', ''),
            (r'［＃[^］]*］', ''),
            
            # 底本情報除去
            (r'底本：[^\n]*\n?', ''),
            (r'入力：[^\n]*\n?', ''),
            (r'校正：[^\n]*\n?', ''),
            (r'※[^\n]*\n?', ''),
            (r'初出：[^\n]*\n?', ''),
            
            # XMLヘッダー除去
            (r'<\?xml[^>]*\?>', ''),
            (r'<!DOCTYPE[^>]*>', ''),
            
            # 多重空白・改行の正規化
            (r'\n\s*\n\s*\n+', '\n\n'),
            (r'[ \t]+', ' '),
            (r'　+', '　'),
        ]
        
        # 文分割パターン
        self.sentence_pattern = re.compile(r'[。．！？!?]+')
        
        logger.info("📝 改良版テキスト処理システム初期化完了")
    
    def clean_aozora_text(self, raw_text: str) -> Tuple[str, ProcessingStats]:
        """青空文庫テキストの改良版クリーニング"""
        if not raw_text:
            return "", ProcessingStats(0, 0, 0, 0, 0, 0)
        
        original_length = len(raw_text)
        processed_text = raw_text
        
        # 各パターンの統計
        ruby_count = 0
        html_count = 0
        annotation_count = 0
        
        # クリーニングパターンを順次適用
        for pattern, replacement in self.cleanup_patterns:
            if 'ruby' in pattern.lower():
                matches = len(re.findall(pattern, processed_text))
                ruby_count += matches
            elif '<' in pattern and '>' in pattern:
                matches = len(re.findall(pattern, processed_text))
                html_count += matches
            elif any(char in pattern for char in ['《', '［', '〔']):
                matches = len(re.findall(pattern, processed_text))
                annotation_count += matches
            
            processed_text = re.sub(pattern, replacement, processed_text)
        
        # 最終的な正規化
        processed_text = self._final_normalization(processed_text)
        
        # 文分割
        sentences = self.split_into_sentences(processed_text)
        
        stats = ProcessingStats(
            original_length=original_length,
            processed_length=len(processed_text),
            removed_ruby_count=ruby_count,
            removed_html_count=html_count,
            removed_annotation_count=annotation_count,
            sentence_count=len(sentences)
        )
        
        logger.info(f"📝 テキストクリーニング完了: {original_length:,} → {len(processed_text):,}文字, {len(sentences)}文")
        
        return processed_text, stats
    
    def _final_normalization(self, text: str) -> str:
        """最終的な正規化処理"""
        # 連続する空白の正規化
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'　+', '　', text)
        
        # 連続する改行の正規化
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 行頭・行末の空白除去
        lines = text.split('\n')
        normalized_lines = [line.strip() for line in lines]
        text = '\n'.join(normalized_lines)
        
        # 文頭・文末の空白除去
        text = text.strip()
        
        return text
    
    def split_into_sentences(self, text: str) -> List[str]:
        """テキストを文に分割"""
        if not text:
            return []
        
        # 改行を空白に置換
        text = text.replace('\n', ' ')
        
        # 文末記号で分割
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if self.sentence_pattern.search(char):
                if current.strip() and len(current.strip()) > 5:  # 最小文長制限
                    sentences.append(current.strip())
                current = ""
        
        # 最後の文を追加
        if current.strip() and len(current.strip()) > 5:
            sentences.append(current.strip())
        
        # 短すぎる文や長すぎる文をフィルタリング
        filtered_sentences = []
        for sentence in sentences:
            if 5 <= len(sentence) <= 500:  # 適切な文の長さ
                filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    def extract_metadata(self, text: str) -> Dict[str, str]:
        """メタデータの抽出"""
        metadata = {}
        
        # タイトル
        title_patterns = [
            r'【タイトル】\s*(.*?)(?:\n|$)',
            r'作品名：\s*(.*?)(?:\n|$)',
            r'題名：\s*(.*?)(?:\n|$)'
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                metadata['title'] = match.group(1).strip()
                break
        
        # 作者
        author_patterns = [
            r'【作者】\s*(.*?)(?:\n|$)',
            r'著者：\s*(.*?)(?:\n|$)',
            r'作者：\s*(.*?)(?:\n|$)'
        ]
        for pattern in author_patterns:
            match = re.search(pattern, text)
            if match:
                metadata['author'] = match.group(1).strip()
                break
        
        # 底本
        source_match = re.search(r'底本：\s*(.*?)(?:\n|$)', text)
        if source_match:
            metadata['source'] = source_match.group(1).strip()
        
        # 入力
        input_match = re.search(r'入力：\s*(.*?)(?:\n|$)', text)
        if input_match:
            metadata['input'] = input_match.group(1).strip()
        
        # 校正
        proof_match = re.search(r'校正：\s*(.*?)(?:\n|$)', text)
        if proof_match:
            metadata['proof'] = proof_match.group(1).strip()
        
        # 初出
        debut_match = re.search(r'初出：\s*(.*?)(?:\n|$)', text)
        if debut_match:
            metadata['debut'] = debut_match.group(1).strip()
        
        return metadata
    
    def validate_text_quality(self, text: str) -> Dict[str, Any]:
        """テキスト品質の検証"""
        if not text:
            return {
                'is_valid': False,
                'errors': ['テキストが空です'],
                'warnings': [],
                'quality_score': 0.0
            }
        
        errors = []
        warnings = []
        quality_score = 1.0
        
        # 長さチェック
        if len(text) < 100:
            errors.append('テキストが短すぎます（100文字未満）')
            quality_score -= 0.3
        elif len(text) < 500:
            warnings.append('テキストが短めです（500文字未満）')
            quality_score -= 0.1
        
        # HTMLタグの残存チェック
        html_tags = re.findall(r'<[^>]+>', text)
        if html_tags:
            warnings.append(f'HTMLタグが残存しています: {len(html_tags)}個')
            quality_score -= 0.1
        
        # 青空文庫記号の残存チェック
        aozora_symbols = re.findall(r'[《》［］〔〕]', text)
        if aozora_symbols:
            warnings.append(f'青空文庫記号が残存しています: {len(aozora_symbols)}個')
            quality_score -= 0.1
        
        # 文字化けチェック
        mojibake_patterns = [r'[��]+', r'[\x00-\x08\x0B\x0C\x0E-\x1F]+']
        for pattern in mojibake_patterns:
            if re.search(pattern, text):
                errors.append('文字化けが検出されました')
                quality_score -= 0.5
                break
        
        # 改行の異常チェック
        excessive_newlines = re.search(r'\n{5,}', text)
        if excessive_newlines:
            warnings.append('異常な改行が検出されました')
            quality_score -= 0.05
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'quality_score': max(0.0, min(1.0, quality_score))
        }
    
    def get_text_statistics(self, text: str) -> Dict[str, Any]:
        """テキスト統計の取得"""
        if not text:
            return {}
        
        sentences = self.split_into_sentences(text)
        
        # 文字統計
        char_count = len(text)
        char_count_no_spaces = len(re.sub(r'\s', '', text))
        
        # 文統計
        sentence_count = len(sentences)
        avg_sentence_length = sum(len(s) for s in sentences) / sentence_count if sentence_count > 0 else 0
        
        # 段落統計
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        return {
            'char_count': char_count,
            'char_count_no_spaces': char_count_no_spaces,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'avg_sentence_length': round(avg_sentence_length, 2),
            'longest_sentence': max(len(s) for s in sentences) if sentences else 0,
            'shortest_sentence': min(len(s) for s in sentences) if sentences else 0
        } 