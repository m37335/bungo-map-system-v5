#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スクレイピング結果の確認とDBへの投入
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

# プロジェクトルートをPYTHONPATHに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from database import DatabaseManager, Author, Work, Sentence
from extractors.aozora_scraper import AozoraScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # スクレイパーとDBマネージャーの初期化
    scraper = AozoraScraper()
    db_manager = DatabaseManager()

    # テスト用の作者と作品
    test_author = Author(
        author_name="夏目漱石",
        author_name_kana="なつめそうせき",
        birth_year=1867,
        death_year=1916,
        period="明治・大正",
        wikipedia_url="https://ja.wikipedia.org/wiki/夏目漱石",
        description="明治時代を代表する文豪。本名は夏目金之助。"
    )

    # 作者をDBに保存
    author_id = db_manager.save_author(test_author)
    if not author_id:
        logger.error("作者の保存に失敗しました")
        return

    logger.info(f"作者保存完了: ID = {author_id}")

    # 作者のURLを生成
    author_url = f"https://www.aozora.gr.jp/index_pages/person{author_id}.html"
    work_info = scraper.fetch_author_works(author_url)
    if not work_info:
        logger.error("作品情報の取得に失敗しました")
        return

    # 作品をDBに保存
    for work_data in work_info:
        work = Work(
            work_title=work_data["title"],
            author_id=author_id,
            publication_year=work_data.get("publication_year"),
            genre=work_data.get("genre", "小説"),
            aozora_url=work_data["url"],
            content_length=0,
            sentence_count=0
        )
        work_id = db_manager.save_work(work)
        if work_id:
            logger.info(f"作品保存完了: {work_data['title']} (ID = {work_id})")

    logger.info("スクレイピング結果の確認とDBへの投入が完了しました")

if __name__ == "__main__":
    main() 