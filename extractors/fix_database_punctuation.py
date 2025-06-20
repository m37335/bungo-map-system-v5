#!/usr/bin/env python3
"""
データベース内のセンテンス句読点修正スクリプト
"""

import sqlite3
import re

def add_appropriate_punctuation(text):
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

def fix_database_punctuation():
    """データベースの句読点を修正"""
    print('🔧 データベース句読点修正開始...')
    print('=' * 80)

    # データベース接続
    conn = sqlite3.connect('data/bungo_map.db')

    try:
        # 現在の状況確認
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN sentence_text LIKE "%。" THEN 1 END) as period,
                COUNT(CASE WHEN sentence_text LIKE "%！" THEN 1 END) as exclamation,
                COUNT(CASE WHEN sentence_text LIKE "%？" THEN 1 END) as question
            FROM sentences
        ''')
        
        total, period, exclamation, question = cursor.fetchone()
        punctuation_before = period + exclamation + question
        
        print(f'📊 修正前の状況:')
        print(f'  総センテンス数: {total:,}件')
        print(f'  句読点付き: {punctuation_before}件 ({punctuation_before/total*100:.1f}%)')
        print(f'    句点(.): {period}件')
        print(f'    感嘆符(!): {exclamation}件')
        print(f'    疑問符(?): {question}件')

        # バックアップ作成
        print('\n📋 既存データをバックアップ中...')
        conn.execute('DROP TABLE IF EXISTS sentences_backup_punctuation')
        conn.execute('CREATE TABLE sentences_backup_punctuation AS SELECT * FROM sentences')
        print('  ✅ sentences_backup_punctuation テーブル作成完了')

        # 句読点修正処理
        print('\n🔄 句読点修正処理中...')
        
        cursor = conn.execute('SELECT sentence_id, sentence_text FROM sentences ORDER BY sentence_id')
        sentences_data = cursor.fetchall()

        updated_count = 0
        for sentence_id, sentence_text in sentences_data:
            fixed_text = add_appropriate_punctuation(sentence_text)
            
            if fixed_text != sentence_text:
                conn.execute('''
                    UPDATE sentences 
                    SET sentence_text = ?, sentence_length = ? 
                    WHERE sentence_id = ?
                ''', (fixed_text, len(fixed_text), sentence_id))
                updated_count += 1

        conn.commit()
        
        print(f'  ✅ {updated_count:,}件のセンテンスを更新しました')

        # 修正後の状況確認
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN sentence_text LIKE "%。" THEN 1 END) as period,
                COUNT(CASE WHEN sentence_text LIKE "%！" THEN 1 END) as exclamation,
                COUNT(CASE WHEN sentence_text LIKE "%？" THEN 1 END) as question
            FROM sentences
        ''')
        
        total_after, period_after, exclamation_after, question_after = cursor.fetchone()
        punctuation_after = period_after + exclamation_after + question_after
        
        print(f'\n📊 修正後の状況:')
        print(f'  総センテンス数: {total_after:,}件')
        print(f'  句読点付き: {punctuation_after}件 ({punctuation_after/total_after*100:.1f}%)')
        print(f'    句点(.): {period_after}件')
        print(f'    感嘆符(!): {exclamation_after}件')
        print(f'    疑問符(?): {question_after}件')

        # 修正効果
        improvement = punctuation_after - punctuation_before
        print(f'\n📈 修正効果:')
        print(f'  句読点付き文の増加: +{improvement:,}件')
        print(f'  句読点付き率の向上: {punctuation_before/total*100:.1f}% → {punctuation_after/total_after*100:.1f}% (+{(punctuation_after/total_after - punctuation_before/total)*100:.1f}%)')

        # サンプル表示
        print('\n🔍 修正後サンプル:')
        cursor = conn.execute('SELECT sentence_text FROM sentences LIMIT 10')
        for i, (text,) in enumerate(cursor.fetchall(), 1):
            print(f'  {i:2d}. "{text}"')

        # sentence_placesテーブルも修正
        print('\n🔄 sentence_placesテーブルも修正中...')
        
        # バックアップ作成
        conn.execute('DROP TABLE IF EXISTS sentence_places_backup_punctuation')
        conn.execute('CREATE TABLE sentence_places_backup_punctuation AS SELECT * FROM sentence_places')
        
        cursor = conn.execute('SELECT id, matched_text FROM sentence_places ORDER BY id')
        sp_data = cursor.fetchall()

        sp_updated_count = 0
        for sp_id, matched_text in sp_data:
            fixed_text = add_appropriate_punctuation(matched_text)
            
            if fixed_text != matched_text:
                conn.execute('''
                    UPDATE sentence_places 
                    SET matched_text = ? 
                    WHERE id = ?
                ''', (fixed_text, sp_id))
                sp_updated_count += 1

        conn.commit()
        
        print(f'  ✅ sentence_places: {sp_updated_count}件を更新しました')

        # sentence_placesの結果確認
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN matched_text LIKE "%。" THEN 1 END) as period,
                COUNT(CASE WHEN matched_text LIKE "%！" THEN 1 END) as exclamation,
                COUNT(CASE WHEN matched_text LIKE "%？" THEN 1 END) as question
            FROM sentence_places
        ''')
        
        sp_total, sp_period, sp_exclamation, sp_question = cursor.fetchone()
        sp_punctuation = sp_period + sp_exclamation + sp_question
        
        print(f'\nsentence_placesテーブル修正結果:')
        print(f'  総レコード数: {sp_total}件')
        print(f'  句読点付き: {sp_punctuation}件 ({sp_punctuation/sp_total*100:.1f}%)')

        if punctuation_after >= total_after * 0.95:
            print(f'\n✅ 修正成功: 95%以上のセンテンスで句読点が保持されています')
        else:
            print(f'\n⚠️ 修正が不完全: 一部のセンテンスで句読点が不足している可能性があります')

    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        conn.rollback()
    
    finally:
        conn.close()
        
    print('\n✅ データベース句読点修正処理完了!')

if __name__ == "__main__":
    fix_database_punctuation() 