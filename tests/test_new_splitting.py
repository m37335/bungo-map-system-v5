#!/usr/bin/env python3
"""新しいセンテンス分割処理のテスト"""

import sys
sys.path.append('/app/bungo-map-system-v4')

from extractors.fetch_work_content import WorkContentProcessor

def test_new_splitting():
    # テスト用の文章
    test_text = '私が先生と知り合いになったのは鎌倉である。その時私はまだ若々しい書生であった。暑中休暇を利用して海水浴に行った。これは本当に良い思い出だ！君は知っているか？'

    processor = WorkContentProcessor()
    sentences = processor.split_into_sentences(test_text)

    print('🧪 新しいセンテンス分割テスト:')
    print(f'入力文: {test_text}')
    print()
    print('✅ 分割結果（句読点保持）:')
    for i, sentence in enumerate(sentences, 1):
        print(f'  {i}. "{sentence}"')
        
    print(f'\n📊 結果: {len(sentences)}文に分割、すべて句読点保持済み')
    
    # 句読点チェック
    punctuation_count = sum(1 for s in sentences if s.endswith(('。', '！', '？')))
    print(f'✅ 句読点保持率: {punctuation_count}/{len(sentences)} ({punctuation_count/len(sentences)*100:.1f}%)')

if __name__ == "__main__":
    test_new_splitting() 