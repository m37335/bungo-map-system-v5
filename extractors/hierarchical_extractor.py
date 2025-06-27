#!/usr/bin/env python3
"""
階層構造抽出器 (HierarchicalExtractor)
青空文庫形式のテキストから章・段落・文の階層構造を抽出する

作成日: 2025年6月25日
"""

import re
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SectionType(Enum):
    """セクションタイプ"""
    CHAPTER = "chapter"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"

@dataclass
class ExtractedSection:
    """抽出されたセクション"""
    section_type: SectionType
    content: str
    title: Optional[str] = None
    section_number: Optional[int] = None
    parent_id: Optional[int] = None
    character_position: int = 0
    character_length: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.character_length == 0:
            self.character_length = len(self.content)

class HierarchicalExtractor:
    """階層構造抽出器"""
    
    def __init__(self):
        # 青空文庫の章タイトル注記パターン
        self.chapter_patterns = [
            r'［＃「(.+?)」は大見出し］',
            r'［＃「(.+?)」は中見出し］',
            r'［＃「(.+?)」は小見出し］',
        ]
        
    def extract_structure(self, text: str, work_id: int) -> List[ExtractedSection]:
        """テキストから階層構造を抽出"""
        logger.info(f"作品ID {work_id} の階層構造抽出開始")
        
        sections = []
        
        try:
            # 章の抽出
            chapters = self._extract_chapters(text)
            
            for chapter_idx, chapter in enumerate(chapters):
                chapter_section = ExtractedSection(
                    section_type=SectionType.CHAPTER,
                    content=chapter['content'],
                    title=chapter['title'],
                    section_number=chapter_idx + 1,
                    character_position=chapter['start_pos'],
                    metadata={'work_id': work_id}
                )
                sections.append(chapter_section)
                
                # 章内の文抽出
                sentences = self._extract_sentences(chapter['content'])
                
                for sent_idx, sentence in enumerate(sentences):
                    sent_section = ExtractedSection(
                        section_type=SectionType.SENTENCE,
                        content=sentence['content'],
                        section_number=sent_idx + 1,
                        parent_id=len(sections) - 1,
                        character_position=chapter['start_pos'] + sentence['start_pos'],
                        metadata={'work_id': work_id}
                    )
                    sections.append(sent_section)
            
            logger.info(f"階層構造抽出完了: {len(sections)}セクション")
            return sections
            
        except Exception as e:
            logger.error(f"階層構造抽出エラー: {e}")
            return self._create_fallback_structure(text, work_id)
    
    def _extract_chapters(self, text: str) -> List[Dict[str, Any]]:
        """章の抽出"""
        chapters = []
        
        # 青空文庫注記による章抽出
        for pattern in self.chapter_patterns:
            matches = list(re.finditer(pattern, text))
            
            for match in matches:
                title = match.group(1)
                start_pos = match.start()
                
                # 次の章までの内容を取得
                next_chapter_pos = len(text)
                for next_match in re.finditer(pattern, text[match.end():]):
                    next_chapter_pos = match.end() + next_match.start()
                    break
                
                content = text[match.end():next_chapter_pos].strip()
                
                if content:
                    chapters.append({
                        'title': title,
                        'content': content,
                        'start_pos': start_pos
                    })
        
        # 章が見つからない場合、全体を1つの章として扱う
        if not chapters:
            chapters.append({
                'title': "本文",
                'content': self._clean_text(text),
                'start_pos': 0
            })
            
        return chapters
    
    def _extract_sentences(self, text: str) -> List[Dict[str, Any]]:
        """文の抽出"""
        sentences = []
        current_pos = 0
        
        # 句点・感嘆符・疑問符で分割
        sentence_parts = re.split(r'([。！？])', text)
        
        current_sentence = ""
        for i, part in enumerate(sentence_parts):
            current_sentence += part
            
            # 句点類の場合、文として確定
            if re.match(r'[。！？]', part):
                sentence_content = current_sentence.strip()
                if sentence_content:
                    sentences.append({
                        'content': sentence_content,
                        'start_pos': current_pos
                    })
                    current_pos += len(current_sentence)
                    current_sentence = ""
        
        # 残りの文があれば追加
        if current_sentence.strip():
            sentences.append({
                'content': current_sentence.strip(),
                'start_pos': current_pos
            })
        
        return sentences
    
    def _clean_text(self, text: str) -> str:
        """テキストのクリーニング"""
        # 青空文庫注記の除去
        text = re.sub(r'［＃.+?］', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _create_fallback_structure(self, text: str, work_id: int) -> List[ExtractedSection]:
        """フォールバック構造の作成"""
        logger.warning("フォールバック構造を作成中")
        
        sections = []
        
        # 全体を1つの章として作成
        chapter = ExtractedSection(
            section_type=SectionType.CHAPTER,
            content=self._clean_text(text),
            title="本文",
            section_number=1,
            character_position=0,
            metadata={'work_id': work_id}
        )
        sections.append(chapter)
        
        return sections

def main():
    """テスト実行"""
    extractor = HierarchicalExtractor()
    
    sample_text = """
［＃「第一章　はじめに」は大見出し］

　これは青空文庫形式のサンプルテキストです。章、段落、文の階層構造を持っています。

　「こんにちは」と彼は言った。「今日はいい天気ですね。」

［＃「第二章　続き」は大見出し］

　第二章の内容です。ここにも複数の段落があります。
    """
    
    sections = extractor.extract_structure(sample_text, 1)
    
    print(f"抽出されたセクション数: {len(sections)}")
    for i, section in enumerate(sections):
        print(f"{i}: {section.section_type.value} - {section.title or '無題'} ({len(section.content)}文字)")

if __name__ == "__main__":
    main()
