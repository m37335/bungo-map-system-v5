#!/usr/bin/env python3
"""句読点保持テストスクリプト"""

import re

def improved_split_sentences(text):
    """改良版センテンス分割（句読点保持）"""
    if not text:
        return []
    
    parts = re.split(r'([。．！？])', text)
    sentences = []
    current_sentence = ''
    
    for part in parts:
        if part in ['。', '．', '！', '？']:
            current_sentence += part
            if current_sentence.strip() and len(current_sentence.strip()) >= 3:
                sentences.append(current_sentence.strip())
            current_sentence = ''
        else:
            current_sentence += part
    
    if current_sentence.strip() and len(current_sentence.strip()) >= 3:
        sentences.append(current_sentence.strip())
    
    return sentences

def main():
    test_text = '私が先生と知り合いになったのは鎌倉である。その時私はまだ若々しい書生であった。'

    print('🧪 句読点保持分割テスト:')
    print(f'テスト文: {test_text}')
    print()

    # 新しい方法
    improved = improved_split_sentences(test_text)
    print('✅ 新しい方法（句読点保持）:')
    for i, s in enumerate(improved, 1):
        print(f'  {i}. "{s}"')

    print()

    # 古い方法
    old = re.split(r'[。．！？]', test_text)
    old = [s.strip() for s in old if s.strip()]
    print('🚫 古い方法（句読点削除）:')
    for i, s in enumerate(old, 1):
        print(f'  {i}. "{s}" ← 句読点欠落')

if __name__ == "__main__":
    main() 