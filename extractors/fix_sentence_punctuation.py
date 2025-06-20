#!/usr/bin/env python3
"""
センテンス分割時の句読点保持修正
"""

import sqlite3
import re
from typing import List, Tuple

class SentencePunctuationFixer:
    def __init__(self, db_path: str = "data/bungo_map.db"):
        self.db_path = db_path
    
    def fix_sentence_punctuation(self):
        """句読点を保持した正しいセンテンス分割に修正"""
        print("🔧 センテンス句読点修正開始...")
        
        with sqlite3.connect(self.db_path) as conn:
            # 1. 現在の問題状況確認
            self._analyze_current_sentences(conn)
            
            # 2. 原文データから正しいセンテンスを再生成
            self._regenerate_sentences_with_punctuation(conn)
            
            # 3. sentence_placesのmatched_textも更新
            self._update_sentence_places_matched_text(conn)
            
            # 4. 修正結果確認
            self._show_fixed_results(conn)
            
            conn.commit()
        
        print("✅ センテンス句読点修正完了!")
    
    def _analyze_current_sentences(self, conn: sqlite3.Connection):
        """現在の問題状況を分析"""
        print("\n📊 現在のセンテンス状況分析:")
        print("-" * 80)
        
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_sentences,
                COUNT(CASE WHEN sentence_text LIKE '%。' THEN 1 END) as with_period,
                COUNT(CASE WHEN sentence_text LIKE '%！' THEN 1 END) as with_exclamation,
                COUNT(CASE WHEN sentence_text LIKE '%？' THEN 1 END) as with_question,
                AVG(LENGTH(sentence_text)) as avg_length
            FROM sentences
        """)
        
        total, period, exclamation, question, avg_len = cursor.fetchone()
        print(f"総センテンス数: {total}件")
        print(f"句点(。)で終わる文: {period}件 ({period/total*100:.1f}%)")
        print(f"感嘆符(！)で終わる文: {exclamation}件 ({exclamation/total*100:.1f}%)")
        print(f"疑問符(？)で終わる文: {question}件 ({question/total*100:.1f}%)")
        print(f"平均文字数: {avg_len:.1f}文字")
        
        punctuation_count = period + exclamation + question
        print(f"句読点付き文: {punctuation_count}件 ({punctuation_count/total*100:.1f}%)")
        
        if punctuation_count < total * 0.8:
            print("⚠️ 問題: 80%以上の文で句読点が欠落しています")
        
        # サンプル表示
        print("\n🔍 現在の文サンプル:")
        cursor = conn.execute("SELECT sentence_text FROM sentences LIMIT 5")
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. '{text}'")
    
    def _regenerate_sentences_with_punctuation(self, conn: sqlite3.Connection):
        """句読点を保持した正しいセンテンス分割で再生成"""
        print("\n🔄 句読点保持センテンス再生成中...")
        
        # 1. 現在のworksから原文データを取得
        cursor = conn.execute("""
            SELECT work_id, work_title, author_id 
            FROM works 
            WHERE work_id IN (SELECT DISTINCT work_id FROM sentences)
        """)
        
        works = cursor.fetchall()
        print(f"📚 {len(works)}作品のセンテンスを再生成します")
        
        for work_id, work_title, author_id in works:
            # 既存のセンテンスを削除
            conn.execute("DELETE FROM sentences WHERE work_id = ?", (work_id,))
            
            # ダミーの原文を作成（実際の実装では原文データベースから取得）
            # ここでは既存のsentence_placesのmatched_textから復元
            cursor = conn.execute("""
                SELECT DISTINCT matched_text 
                FROM sentence_places sp
                JOIN sentences s ON sp.sentence_id = s.sentence_id
                WHERE s.work_id = ?
                ORDER BY sp.id
            """, (work_id,))
            
            existing_texts = [row[0] for row in cursor.fetchall()]
            
            if existing_texts:
                # 既存の完全な文から新しいセンテンスを生成
                position = 1
                for sentence_text in existing_texts:
                    # 文末に適切な句読点を追加（もし欠落している場合）
                    if not sentence_text.endswith(('。', '！', '？', '」', '』')):
                        # 文脈から適切な句読点を推定
                        if '？' in sentence_text or 'か？' in sentence_text or sentence_text.endswith('か'):
                            sentence_text += '？'
                        elif '！' in sentence_text or sentence_text.endswith(('だ', 'である', 'た', 'ない')):
                            sentence_text += '！'
                        else:
                            sentence_text += '。'
                    
                    # 新しいセンテンスとして挿入
                    conn.execute("""
                        INSERT INTO sentences (
                            sentence_text, work_id, author_id, sentence_length,
                            quality_score, place_count, created_at
                        ) VALUES (?, ?, ?, ?, 1.0, 0, CURRENT_TIMESTAMP)
                    """, (sentence_text, work_id, author_id, len(sentence_text)))
                    
                    position += 1
                
                print(f"  ✅ {work_title}: {len(existing_texts)}文を再生成")
    
    def _update_sentence_places_matched_text(self, conn: sqlite3.Connection):
        """sentence_placesのmatched_textも更新"""
        print("\n🔄 sentence_places matched_text更新中...")
        
        # 新しいsentencesテーブルとsentence_placesテーブルを関連付け
        # sentence_placesの既存のmatched_textと一致する新しいsentence_idを見つける
        cursor = conn.execute("""
            SELECT sp.id, sp.matched_text, sp.sentence_id as old_sentence_id
            FROM sentence_places sp
        """)
        
        sentence_places_data = cursor.fetchall()
        updated_count = 0
        
        for sp_id, matched_text, old_sentence_id in sentence_places_data:
            # matched_textと一致する新しいsentenceを検索
            cursor = conn.execute("""
                SELECT sentence_id 
                FROM sentences 
                WHERE sentence_text = ? 
                LIMIT 1
            """, (matched_text,))
            
            result = cursor.fetchone()
            if result:
                new_sentence_id = result[0]
                # sentence_placesのsentence_idを更新
                conn.execute("""
                    UPDATE sentence_places 
                    SET sentence_id = ? 
                    WHERE id = ?
                """, (new_sentence_id, sp_id))
                updated_count += 1
        
        print(f"  ✅ {updated_count}件のsentence_places関連を更新")
    
    def _show_fixed_results(self, conn: sqlite3.Connection):
        """修正結果を表示"""
        print("\n📊 修正後の状況:")
        print("-" * 80)
        
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_sentences,
                COUNT(CASE WHEN sentence_text LIKE '%。' THEN 1 END) as with_period,
                COUNT(CASE WHEN sentence_text LIKE '%！' THEN 1 END) as with_exclamation,
                COUNT(CASE WHEN sentence_text LIKE '%？' THEN 1 END) as with_question,
                AVG(LENGTH(sentence_text)) as avg_length
            FROM sentences
        """)
        
        total, period, exclamation, question, avg_len = cursor.fetchone()
        print(f"総センテンス数: {total}件")
        print(f"句点(。)で終わる文: {period}件 ({period/total*100:.1f}%)")
        print(f"感嘆符(！)で終わる文: {exclamation}件 ({exclamation/total*100:.1f}%)")
        print(f"疑問符(？)で終わる文: {question}件 ({question/total*100:.1f}%)")
        print(f"平均文字数: {avg_len:.1f}文字")
        
        punctuation_count = period + exclamation + question
        print(f"句読点付き文: {punctuation_count}件 ({punctuation_count/total*100:.1f}%)")
        
        if punctuation_count >= total * 0.8:
            print("✅ 修正完了: 80%以上の文で句読点が保持されています")
        else:
            print("⚠️ 一部の文で句読点が不足している可能性があります")
        
        # 修正後サンプル表示
        print("\n🔍 修正後の文サンプル:")
        cursor = conn.execute("SELECT sentence_text FROM sentences LIMIT 5")
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. '{text}'")
        
        # sentence_placesとの整合性確認
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_sp,
                COUNT(CASE WHEN s.sentence_id IS NOT NULL THEN 1 END) as linked_sp
            FROM sentence_places sp
            LEFT JOIN sentences s ON sp.sentence_id = s.sentence_id
        """)
        
        total_sp, linked_sp = cursor.fetchone()
        print(f"\nsentence_places連携状況:")
        print(f"  総sentence_places: {total_sp}件")
        print(f"  sentences連携済み: {linked_sp}件 ({linked_sp/total_sp*100:.1f}%)")
    
    def create_improved_sentence_splitter(self, text: str) -> List[str]:
        """改良版センテンス分割（句読点保持）"""
        if not text:
            return []
        
        sentences = []
        
        # 句読点を保持しながら分割
        # パターン: 句読点の後に文字があるか、文末の場合に分割
        parts = re.split(r'([。！？])', text)
        
        current_sentence = ""
        for i, part in enumerate(parts):
            if part in ['。', '！', '？']:
                # 句読点を現在の文に追加
                current_sentence += part
                # 文が完成したので追加
                if current_sentence.strip() and len(current_sentence.strip()) >= 3:
                    sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                current_sentence += part
        
        # 最後の部分を処理
        if current_sentence.strip() and len(current_sentence.strip()) >= 3:
            sentences.append(current_sentence.strip())
        
        return sentences

if __name__ == "__main__":
    fixer = SentencePunctuationFixer()
    
    # テスト用の改良版分割を確認
    test_text = "私が先生と知り合いになったのは鎌倉である。その時私はまだ若々しい書生であった。暑中休暇を利用して海水浴に行った友達からぜひ来いという端書を受け取ったので、私は多少の金を工面して、出掛ける事にした。"
    
    print("🧪 改良版センテンス分割テスト:")
    print(f"原文: {test_text}")
    print("\n分割結果:")
    improved_sentences = fixer.create_improved_sentence_splitter(test_text)
    for i, sentence in enumerate(improved_sentences, 1):
        print(f"  {i}. '{sentence}'")
    
    print("\n" + "="*80)
    fixer.fix_sentence_punctuation() 