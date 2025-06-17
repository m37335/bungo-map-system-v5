#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging

# モジュールのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extractors.aozora_scraper import AozoraScraper

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # スクレイパーの初期化
    scraper = AozoraScraper()
    
    # 著者一覧の取得
    print("著者一覧を取得中...")
    authors = scraper.fetch_author_list()
    print(f"取得した著者数: {len(authors)}")
    
    # テスト用に最初の3人の著者を選択
    test_authors = authors[:3]
    
    # 各著者の作品を取得
    for author in test_authors:
        print(f"\n著者: {author['name']}")
        works = scraper.fetch_author_works(author['url'])
        print(f"作品数: {len(works)}")
        
        # 最初の作品の本文を取得
        if works:
            first_work = works[0]
            print(f"\n作品: {first_work['title']}")
            content = scraper.fetch_work_content(first_work['url'])
            if content:
                print(f"本文の長さ: {len(content)}文字")
                print("本文の最初の100文字:")
                print(content[:100])
            else:
                print("本文の取得に失敗しました")

if __name__ == "__main__":
    main() 