#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースマネージャー v4
地名抽出・正規化システムと連携したデータベース管理
"""

import sqlite3
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from .models import Author, Work, Sentence, Place, SentencePlace

logger = logging.getLogger(__name__)

class DatabaseManager:
    """現行スキーマ対応 データベースマネージャー"""
    
    def __init__(self, db_path: str = 'data/db/bungo_map.sqlite3'):
        """初期化"""
        self.db_path = db_path
        logger.info(f"🌟 データベースマネージャーv4初期化: DBパス = {self.db_path}")
    
    def save_author(self, author: Author) -> Optional[int]:
        """作者情報を保存し、IDを返す。既存ならそのIDを返す"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT author_id FROM authors WHERE author_name = ?",
                    (author.author_name,)
                )
                result = cursor.fetchone()
                if result:
                    return result[0]
                # 新規作成
                cursor = conn.execute(
                    """
                    INSERT INTO authors (
                        author_name, author_name_kana, birth_year, death_year,
                        period, wikipedia_url, description, source_system,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        author.author_name,
                        author.author_name_kana,
                        author.birth_year,
                        author.death_year,
                        author.period,
                        author.wikipedia_url,
                        author.description,
                        getattr(author, 'source_system', 'manual'),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"作者保存エラー: {e}")
            return None

    def save_work(self, work: Work) -> Optional[int]:
        """作品情報を保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO works (
                        work_title, author_id, publication_year, genre, aozora_url, content_length, sentence_count, source_system, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        work.work_title,
                        work.author_id,
                        work.publication_year,
                        work.genre,
                        work.aozora_url,
                        work.content_length,
                        work.sentence_count,
                        getattr(work, 'source_system', 'manual'),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"作品保存エラー: {e}")
            return None

    def save_sentence(self, sentence: Sentence) -> Optional[int]:
        """センテンスを保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO sentences (
                        sentence_text, work_id, author_id, before_text, after_text, source_info, sentence_length, quality_score, place_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sentence.sentence_text,
                        sentence.work_id,
                        sentence.author_id,
                        sentence.before_text,
                        sentence.after_text,
                        sentence.source_info,
                        sentence.sentence_length,
                        sentence.quality_score,
                        sentence.place_count,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"センテンス保存エラー: {e}")
            return None

    def save_place(self, place: Place) -> Optional[int]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT place_id FROM places WHERE place_name = ?",
                    (place.place_name,)
                )
                result = cursor.fetchone()
                if result:
                    return result[0]
                cursor = conn.execute(
                    """
                    INSERT INTO places (
                        place_name, canonical_name, aliases, latitude, longitude, place_type, confidence, description, wikipedia_url, image_url, country, prefecture, municipality, district, mention_count, author_count, work_count, source_system, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        place.place_name,
                        place.canonical_name,
                        str(getattr(place, 'aliases', '[]')),
                        place.latitude,
                        place.longitude,
                        place.place_type,
                        place.confidence,
                        place.description,
                        place.wikipedia_url,
                        place.image_url,
                        place.country,
                        place.prefecture,
                        place.municipality,
                        place.district,
                        place.mention_count,
                        place.author_count,
                        place.work_count,
                        getattr(place, 'source_system', 'manual'),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"地名保存エラー: {e}")
            return None

    def save_sentence_place(self, sp: SentencePlace) -> Optional[int]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO sentence_places (
                        sentence_id, place_id, extraction_method, confidence, position_in_sentence, context_before, context_after, matched_text, verification_status, quality_score, relevance_score, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sp.sentence_id,
                        sp.place_id,
                        sp.extraction_method,
                        sp.confidence,
                        sp.position_in_sentence,
                        sp.context_before,
                        sp.context_after,
                        sp.matched_text,
                        sp.verification_status,
                        sp.quality_score,
                        sp.relevance_score,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"sentence_place保存エラー: {e}")
            return None

    def get_work_statistics(self, work_id: int) -> Dict[str, Any]:
        """作品の統計情報取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT w.work_title, w.place_count, w.sentence_count, a.author_name
                    FROM works w
                    JOIN authors a ON w.author_id = a.author_id
                    WHERE w.work_id = ?
                    """,
                    (work_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        'work_title': result[0],
                        'place_count': result[1],
                        'sentence_count': result[2],
                        'author_name': result[3]
                    }
                return {}
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {}

if __name__ == "__main__":
    # 簡単なテスト
    manager = DatabaseManager()
    
    # テスト用の作者データ
    author = Author(
        author_name="夏目漱石",
        author_name_kana="なつめそうせき",
        birth_year=1867,
        death_year=1916,
        period="明治・大正",
        wikipedia_url="https://ja.wikipedia.org/wiki/夏目漱石",
        description="明治時代を代表する文豪。本名は夏目金之助。"
    )
    
    # 作者を保存
    author_id = manager.save_author(author)
    print(f"✅ 作者保存完了: ID = {author_id}")
    
    if author_id:
        # テスト用の作品データ
        work = Work(
            work_title="吾輩は猫である",
            author_id=author_id,
            publication_year=1905,
            genre="小説",
            aozora_url="https://www.aozora.gr.jp/cards/000148/files/789_14547.html",
            content_length=0,
            sentence_count=0
        )
        
        # 作品を保存
        work_id = manager.save_work(work)
        print(f"✅ 作品保存完了: ID = {work_id}")
        
        if work_id:
            # 統計情報を取得
            stats = manager.get_work_statistics(work_id)
            print("\n📊 作品統計:")
            print(f"  タイトル: {stats.get('work_title')}")
            print(f"  作者: {stats.get('author_name')}")
            print(f"  地名数: {stats.get('place_count', 0)}")
            print(f"  センテンス数: {stats.get('sentence_count', 0)}") 