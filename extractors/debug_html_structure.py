#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青空文庫HTMLの構造調査
"""

import requests
from bs4 import BeautifulSoup
import re

def analyze_html_structure():
    """HTMLの構造を分析"""
    print("🔍 青空文庫HTMLの構造調査")
    print("=" * 60)
    
    try:
        # ページ取得
        url = "https://www.aozora.gr.jp/index_pages/person_all.html"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 青空文庫の文字エンコーディング処理を改善
        if response.encoding is None or response.encoding.lower() in ['iso-8859-1', 'ascii']:
            # レスポンスのバイト内容をShift_JISとしてデコード
            try:
                content = response.content.decode('shift_jis')
            except UnicodeDecodeError:
                # Shift_JISでデコードできない場合はEUC-JPを試す
                try:
                    content = response.content.decode('euc-jp')
                except UnicodeDecodeError:
                    # それでもダメな場合はUTF-8を試す
                    content = response.content.decode('utf-8', errors='ignore')
        else:
            content = response.text
        
        soup = BeautifulSoup(content, 'html.parser')
        
        print(f"✅ ページ取得成功")
        print(f"エンコーディング: {response.encoding}")
        print(f"コンテンツサイズ: {len(response.text):,} 文字")
        
        # 基本構造の調査
        print(f"\n📋 基本構造:")
        print(f"h1タグ数: {len(soup.find_all('h1'))}")
        print(f"h2タグ数: {len(soup.find_all('h2'))}")
        print(f"h3タグ数: {len(soup.find_all('h3'))}")
        print(f"olタグ数: {len(soup.find_all('ol'))}")
        print(f"liタグ数: {len(soup.find_all('li'))}")
        
        # h2タグの内容確認
        h2_tags = soup.find_all('h2')
        print(f"\n📚 h2タグの内容:")
        for i, h2 in enumerate(h2_tags):
            text = h2.get_text().strip()
            print(f"  {i+1}. '{text}'")
        
        # セクション別の構造確認
        print(f"\n🔍 最初のセクションの詳細調査:")
        
        # 「ア」セクションを探す
        for element in soup.find_all(['h2', 'h3']):
            text = element.get_text().strip()
            if text == 'ア':
                print(f"✅ 「ア」セクション発見: {element.name}タグ")
                
                # 次の要素を調査
                next_elements = []
                current = element.next_sibling
                count = 0
                while current and count < 10:
                    if hasattr(current, 'name') and current.name:
                        next_elements.append((current.name, current.get_text()[:100] if current.get_text() else ""))
                    current = current.next_sibling
                    count += 1
                
                print(f"次の要素:")
                for name, text in next_elements:
                    print(f"  {name}: {text[:50]}...")
                break
        
        # ol要素の詳細調査
        ol_elements = soup.find_all('ol')
        if ol_elements:
            print(f"\n📝 ol要素の詳細:")
            for i, ol in enumerate(ol_elements[:3]):  # 最初の3つのみ
                li_elements = ol.find_all('li')
                print(f"  ol#{i+1}: {len(li_elements)}個のli要素")
                
                # 最初の数個のli要素を表示
                for j, li in enumerate(li_elements[:5]):
                    text = li.get_text().strip()
                    print(f"    li#{j+1}: {text}")
        
        # 作家項目のパターン分析
        print(f"\n🎯 作家項目パターン分析:")
        all_li = soup.find_all('li')
        
        # 「(公開中：数字)」パターンを含むli要素を探す
        import re
        author_pattern = re.compile(r'\(公開中：\d+\)')
        author_items = []
        
        for li in all_li:
            text = li.get_text().strip()
            if author_pattern.search(text):
                author_items.append(text)
        
        print(f"作家項目と思われるli要素: {len(author_items)}個")
        
        # 最初の10個を表示
        print(f"\n📋 作家項目サンプル:")
        for i, item in enumerate(author_items[:10], 1):
            print(f"  {i:2}. {item}")
        
        # 正しい日本語パターンの詳細分析
        if author_items:
            print(f"\n🔍 パターン分析:")
            sample_text = author_items[0] if author_items else ""
            print(f"サンプルテキスト: {sample_text}")
            
            # 「公開中」パターンの確認
            if '公開中：' in sample_text:
                print(f"✅ 正常パターン検出: '公開中：'")
            
            # 数字抽出テスト
            numbers = re.findall(r'\d+', sample_text)
            if numbers:
                print(f"✅ 数字パターン検出: {numbers}")
        
        return author_items
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    author_items = analyze_html_structure()
    print(f"\n📊 調査完了: {len(author_items)}個の作家項目を発見") 