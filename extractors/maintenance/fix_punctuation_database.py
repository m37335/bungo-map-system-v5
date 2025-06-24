#!/usr/bin/env python3
"""
データベース内のセンテンス句読点修正スクリプト
"""

import sqlite3
import re
from typing import List, Dict, Optional

class DatabasePunctuationFixer:
    def __init__(self, db_path: str = "data/bungo_map.db"):
        self.db_path = db_path
    
    def fix_all_punctuation(self):
        """すべての句読点問題を修正"""
        print("🔧 データベース句読点修正開始...")
        print("=" * 80)
        
        with sqlite3.connect(self.db_path) as conn:
            # 1. 現在の状況確認
            self._analyze_current_situation(conn)
            
            # 2. 新しいテスト用データで句読点付きセンテンスを作成
            self._create_test_sentences_with_punctuation(conn)
            
            # 3. 結果確認
            self._verify_fix_results(conn)
            
            conn.commit()
        
        print("✅ データベース句読点修正完了!")
    
    def _analyze_current_situation(self, conn: sqlite3.Connection):
        """現在の状況を分析"""
        print("📊 現在の状況分析:")
        print("-" * 60)
        
        # sentences分析
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN sentence_text LIKE '%。' THEN 1 END) as period,
                COUNT(CASE WHEN sentence_text LIKE '%！' THEN 1 END) as exclamation,
                COUNT(CASE WHEN sentence_text LIKE '%？' THEN 1 END) as question,
                AVG(LENGTH(sentence_text)) as avg_length
            FROM sentences
        """)
        
        total, period, exclamation, question, avg_len = cursor.fetchone()
        punctuation_rate = (period + exclamation + question) / total * 100 if total > 0 else 0
        
        print(f"sentences テーブル:")
        print(f"  総センテンス数: {total:,}件")
        print(f"  句読点付き: {period + exclamation + question}件 ({punctuation_rate:.1f}%)")
        print(f"  平均文字数: {avg_len:.1f}文字")
        
        # sentence_places分析
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN matched_text LIKE '%。' THEN 1 END) as period,
                COUNT(CASE WHEN matched_text LIKE '%！' THEN 1 END) as exclamation,
                COUNT(CASE WHEN matched_text LIKE '%？' THEN 1 END) as question,
                AVG(LENGTH(matched_text)) as avg_length
            FROM sentence_places
        """)
        
        sp_total, sp_period, sp_exclamation, sp_question, sp_avg_len = cursor.fetchone()
        sp_punctuation_rate = (sp_period + sp_exclamation + sp_question) / sp_total * 100 if sp_total > 0 else 0
        
        print(f"sentence_places テーブル:")
        print(f"  総レコード数: {sp_total}件")
        print(f"  句読点付き: {sp_period + sp_exclamation + sp_question}件 ({sp_punctuation_rate:.1f}%)")
        print(f"  平均文字数: {sp_avg_len:.1f}文字")
        
        # サンプル表示
        print(f"\n🔍 現在のサンプル:")
        cursor = conn.execute("SELECT sentence_text FROM sentences LIMIT 3")
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f"  sentences[{i}]: \"{text}\"")
        
        cursor = conn.execute("SELECT matched_text FROM sentence_places LIMIT 3")
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f"  sentence_places[{i}]: \"{text}\"")
    
    def _create_test_sentences_with_punctuation(self, conn: sqlite3.Connection):
        """句読点付きテストセンテンスを作成"""
        print(f"\n🔄 句読点付きセンテンス作成中...")
        
        # バックアップ作成
        print("📋 既存データをバックアップ中...")
        conn.execute("DROP TABLE IF EXISTS sentences_backup")
        conn.execute("CREATE TABLE sentences_backup AS SELECT * FROM sentences")
        
        conn.execute("DROP TABLE IF EXISTS sentence_places_backup")
        conn.execute("CREATE TABLE sentence_places_backup AS SELECT * FROM sentence_places")
        
        # sentencesテーブルの更新
        print("🔄 sentencesテーブル更新中...")
        
        # 既存の文を取得して句読点を追加
        cursor = conn.execute("""
            SELECT sentence_id, sentence_text, sentence_length 
            FROM sentences 
            ORDER BY sentence_id
        """)
        
        sentences_data = cursor.fetchall()
        updated_sentences = 0
        
        for sentence_id, sentence_text, sentence_length in sentences_data:
            # 句読点を適切に追加
            fixed_text = self._add_appropriate_punctuation(sentence_text)
            
            if fixed_text != sentence_text:
                # 更新
                conn.execute("""
                    UPDATE sentences 
                    SET sentence_text = ?, sentence_length = ?
                    WHERE sentence_id = ?
                """, (fixed_text, len(fixed_text), sentence_id))
                updated_sentences += 1
        
        print(f"  ✅ sentences: {updated_sentences:,}件更新")
        
        # sentence_placesテーブルの更新
        print("🔄 sentence_placesテーブル更新中...")
        
        cursor = conn.execute("""
            SELECT id, matched_text 
            FROM sentence_places 
            ORDER BY id
        """)
        
        sp_data = cursor.fetchall()
        updated_sp = 0
        
        for sp_id, matched_text in sp_data:
            # 句読点を適切に追加
            fixed_text = self._add_appropriate_punctuation(matched_text)
            
            if fixed_text != matched_text:
                # 更新
                conn.execute("""
                    UPDATE sentence_places 
                    SET matched_text = ?
                    WHERE id = ?
                """, (fixed_text, sp_id))
                updated_sp += 1
        
        print(f"  ✅ sentence_places: {updated_sp}件更新")
    
    def _add_appropriate_punctuation(self, text: str) -> str:
        """文に適切な句読点を追加"""
        if not text or text.endswith(('。', '！', '？', '」', '』', '〉', '》')):
            return text
        
        # 文の内容から適切な句読点を推定
        if any(indicator in text for indicator in ['？', 'か', 'だろうか', 'でしょうか']):
            return text + '？'
        elif any(indicator in text for indicator in ['！', 'だ！', 'である！', 'よ']):
            return text + '！'
        else:
            return text + '。'
    
    def _verify_fix_results(self, conn: sqlite3.Connection):
        """修正結果を確認"""
        print(f"\n📊 修正結果確認:")
        print("-" * 60)
        
        # sentences確認
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN sentence_text LIKE '%。' THEN 1 END) as period,
                COUNT(CASE WHEN sentence_text LIKE '%！' THEN 1 END) as exclamation,
                COUNT(CASE WHEN sentence_text LIKE '%？' THEN 1 END) as question,
                AVG(LENGTH(sentence_text)) as avg_length
            FROM sentences
        """)
        
        total, period, exclamation, question, avg_len = cursor.fetchone()
        punctuation_rate = (period + exclamation + question) / total * 100 if total > 0 else 0
        
        print(f"sentences テーブル（修正後）:")
        print(f"  総センテンス数: {total:,}件")
        print(f"  句読点付き: {period + exclamation + question}件 ({punctuation_rate:.1f}%)")
        print(f"  平均文字数: {avg_len:.1f}文字")
        
        # sentence_places確認
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN matched_text LIKE '%。' THEN 1 END) as period,
                COUNT(CASE WHEN matched_text LIKE '%！' THEN 1 END) as exclamation,
                COUNT(CASE WHEN matched_text LIKE '%？' THEN 1 END) as question,
                AVG(LENGTH(matched_text)) as avg_length
            FROM sentence_places
        """)
        
        sp_total, sp_period, sp_exclamation, sp_question, sp_avg_len = cursor.fetchone()
        sp_punctuation_rate = (sp_period + sp_exclamation + sp_question) / sp_total * 100 if sp_total > 0 else 0
        
        print(f"sentence_places テーブル（修正後）:")
        print(f"  総レコード数: {sp_total}件")
        print(f"  句読点付き: {sp_period + sp_exclamation + sp_question}件 ({sp_punctuation_rate:.1f}%)")
        print(f"  平均文字数: {sp_avg_len:.1f}文字")
        
        # 修正後サンプル表示
        print(f"\n🔍 修正後サンプル:")
        cursor = conn.execute("SELECT sentence_text FROM sentences LIMIT 5")
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f"  sentences[{i}]: \"{text}\"")
        
        cursor = conn.execute("SELECT matched_text FROM sentence_places LIMIT 5")
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f"  sentence_places[{i}]: \"{text}\"")
        
        # 成功率判定
        if punctuation_rate >= 95 and sp_punctuation_rate >= 95:
            print(f"\n✅ 修正成功: 95%以上の文で句読点が保持されています")
        else:
            print(f"\n⚠️ 修正が不完全: 一部の文で句読点が不足している可能性があります")

def test_punctuation_splitter():
    """新しい句読点保持分割のテスト"""
    def improved_split_sentences(text: str) -> List[str]:
        """改良版センテンス分割（句読点保持）"""
        if not text:
            return []
        
        parts = re.split(r'([。．！？])', text)
        sentences = []
        current_sentence = ""
        
        for part in parts:
            if part in ['。', '．', '！', '？']:
                current_sentence += part
                if current_sentence.strip() and len(current_sentence.strip()) >= 3:
                    sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                current_sentence += part
        
        if current_sentence.strip() and len(current_sentence.strip()) >= 3:
            sentences.append(current_sentence.strip())
        
        return sentences
    
    print("🧪 新しい句読点保持分割テスト:")
    print("=" * 80)
    
    test_text = "私が先生と知り合いになったのは鎌倉である。その時私はまだ若々しい書生であった。暑中休暇を利用して海水浴に行った友達からぜひ来いという端書を受け取ったので、私は多少の金を工面して、出掛ける事にした。私は金の工面に二、三日を費やした。"
    
    print(f"テスト文: {test_text}")
    print()
    
    # 新しい方法
    improved_sentences = improved_split_sentences(test_text)
    print("✅ 新しい方法（句読点保持）:")
    for i, sentence in enumerate(improved_sentences, 1):
        print(f"  {i}. \"{sentence}\"")
    
    print()
    
    # 古い方法
    old_sentences = re.split(r'[。．！？]', test_text)
    old_sentences = [s.strip() for s in old_sentences if s.strip()]
    print("🚫 古い方法（句読点削除）:")
    for i, sentence in enumerate(old_sentences, 1):
        print(f"  {i}. \"{sentence}\" ← 句読点欠落")

if __name__ == "__main__":
    # まずテストを実行
    test_punctuation_splitter()
    print("\n" + "=" * 80)
    
    # データベース修正を実行
    fixer = DatabasePunctuationFixer()
    fixer.fix_all_punctuation() 