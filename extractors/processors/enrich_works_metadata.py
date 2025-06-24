#!/usr/bin/env python3
"""
全作品メタデータ一括補完スクリプト
"""

import sys
import os

# パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from ..aozora.aozora_metadata_extractor import AozoraMetadataExtractor

def main():
    """全作品のメタデータを一括補完"""
    print("🌟 全作品メタデータ一括補完システム開始")
    print("="*60)
    
    try:
        extractor = AozoraMetadataExtractor()
        
        # プレビュー表示
        print("📋 補完対象確認中...")
        preview_result = extractor.preview_missing_metadata()
        
        if preview_result['missing_count'] == 0:
            print("✅ 全ての作品メタデータが既に完全です！")
            return
        
        # 実行確認
        print(f"\n🚀 {preview_result['missing_count']} 件の作品を処理します")
        print("⏱️  処理時間の目安: 約 {} 秒".format(preview_result['missing_count']))
        
        # 一括処理実行（確認プロンプトをスキップ）
        print("\n🔄 メタデータ一括補完開始...")
        results = extractor.enrich_all_works()
        
        # 結果表示
        extractor.print_statistics()
        
        print(f"🎉 全作品メタデータ補完が完了しました！")
        
    except KeyboardInterrupt:
        print("\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main() 