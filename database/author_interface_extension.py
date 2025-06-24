#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一作者管理インターフェース拡張
DatabaseManagerクラスに追加するメソッド群
"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# 統一作者管理インターフェース
def create_or_get_author(self, author_data) -> Optional[int]:
    """作者を作成または取得（統一インターフェース）"""
    return self.save_author(author_data)

def create_author(self, author_data) -> Optional[int]:
    """新規作者作成（save_authorのエイリアス）"""
    return self.save_author(author_data)

def update_author(self, author_id: int, author_data: dict) -> bool:
    """作者情報更新"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            # 更新フィールドを動的に構築
            update_fields = []
            values = []
            
            for key, value in author_data.items():
                if key != 'author_id':  # IDは更新しない
                    update_fields.append(f"{key} = ?")
                    values.append(value)
            
            if not update_fields:
                return False
            
            values.append(author_id)
            values.append(datetime.now().isoformat())
            
            query = f"""UPDATE authors SET 
                {', '.join(update_fields)}, updated_at = ?
                WHERE author_id = ?"""
            
            cursor = conn.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"作者更新エラー: {e}")
        return False

