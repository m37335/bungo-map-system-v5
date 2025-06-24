# 🌟 文豪ゆかり地図システム v4.0 - 次世代AI統合版

青空文庫と Wikipedia から文豪作品の地名情報を**AI駆動型完全統合**で抽出し、地図上で可視化する次世代システム

![Python](https://img.shields.io/badge/python-v3.12+-blue.svg)
![GitHub](https://img.shields.io/badge/license-MIT-green.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)

## 🚀 **最新アップデート（2025年6月24日完成）**

### ✨ **v4.0 リファクタリング完成 - 次世代アーキテクチャ確立**
- **🏗️ モジュラー設計完成**: 65ファイルの完全整理・責任分離実現
- **🤖 AI検証システム統合**: GPT-3.5による地名品質保証・自動クリーンアップ
- **📊 sentence_placesテーブル完全復旧**: 前後文・作者作品情報・品質管理情報復活
- **⚡ 超高速処理**: 200.5件/秒の地名抽出・98.4%ジオコーディング成功率
- **🧪 100%テスト成功**: 7つの統合テストを完全パス

### 📈 **実証済み処理実績（2025年6月）**
- **処理作者**: 牧野富太郎、二葉亭四迷、梶井基次郎（完全処理済み）
- **総地名数**: **1,012件** (牧野富太郎)、**181件** (二葉亭四迷)
- **Geocoding成功率**: **98.4%** (AI検証後)
- **AI検証削除**: **12件の無効地名**を自動削除（192件の関連データ含む）
- **処理時間**: **ワンコマンド10-20分**で完全自動処理

## 🎯 **システム特徴**

### 🔄 **統合パイプライン (`run_pipeline.py`)**
```bash
# 新規作者の完全処理（作品収集→地名抽出→ジオコーディング→AI検証→品質保証）
python3 run_pipeline.py --author "夏目漱石"

# AI検証による地名品質向上
python3 run_pipeline.py --ai-verify-delete --ai-verify-limit 50

# 処理状況確認
python3 run_pipeline.py --status "作者名"
```

### 🗺️ **sentence_places完全復旧システム**
- **前後文情報**: `context_before`, `context_after` 完全復旧
- **作者・作品情報**: `author_name`, `work_title`, `publication_year` 自動補完
- **品質管理**: `quality_score`, `relevance_score`, `verification_status`
- **統計情報**: `place_frequency_in_work`, `sentence_position` 等

### 🤖 **AI検証・品質保証システム**
- **OpenAI GPT-3.5統合**: 複数文脈での高精度地名/非地名判別
- **自動無効地名削除**: 人名・学術用語・一般名詞の自動検出・削除
- **信頼度判定**: 0.7-0.9の高確信度による削除候補特定
- **大量検証**: 最大100件の一括AI検証機能

## 🏗️ **次世代モジュラーアーキテクチャ**

### �� **整理されたプロジェクト構造**
```
bungo-map-system-v4/
├── �� run_pipeline.py              # 統合パイプライン（メインエントリー）
├── 📋 main.py                      # FastAPI エントリーポイント
├── 🤖 ai/                          # AI機能モジュール
│   ├── llm/client.py               # LLMクライアント（234行）
│   ├── nlp/context_analyzer.py     # 文脈分析エンジン（300行）
│   ├── geocoding/geocoding_engine.py # ジオコーディングエンジン（304行）
│   └── context_aware_geocoding.py  # AI検証エンジン（統合管理）
├── 🏗️ core/                        # コアシステム
│   ├── config.py                   # 統一設定管理（YAML・環境変数）
│   ├── exceptions.py               # カスタム例外クラス体系
│   └── constants.py                # システム定数管理
├── 📊 extractors/                  # データ抽出（機能別分類）
│   ├── aozora/                     # 青空文庫関連（8ファイル）
│   ├── places/                     # 地名抽出関連（2ファイル）
│   ├── wikipedia/                  # Wikipedia関連（1ファイル）
│   ├── maintenance/                # メンテナンス関連（4ファイル）
│   └── processors/                 # 処理系（5ファイル）
├── 🗄️ database/                    # データベース管理
├── 🔧 scripts/                     # 運用スクリプト
├── 🧪 tests/                       # テスト・品質保証
├── 📁 data/                        # データファイル
└── 📋 notebooks/                   # 技術文書・報告書
```

### 🎯 **責任分離・モジュール化の効果**
- **保守性向上**: 巨大ファイル（1,489行）→3つのモジュール（234+300+304行）
- **可読性向上**: 機能別ディレクトリ構造・明確な責任境界
- **拡張性向上**: プラグイン型設計・新機能追加容易
- **品質保証**: 100%テスト成功・統合テスト完備

## 🚀 **クイックスタート**

### 1. **インストール・初期設定**
```bash
# リポジトリクローン
git clone https://github.com/yourusername/bungo-map-system-v4.git
cd bungo-map-system-v4

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定（OpenAI API キー）
cp env.example .env
# .envファイルでOPENAI_API_KEYを設定
```

### 2. **新規作者の完全処理**
```bash
# 作者指定での全自動処理（作品収集→地名抽出→ジオコーディング→AI検証→品質保証）
python3 run_pipeline.py --author "夏目漱石"

# 処理結果例:
# ✅ 処理作品: 15件
# 📊 生成センテンス: 4,500件
# 🗺️ 抽出地名: 285件
# 🌍 ジオコーディング成功: 278件 (97.5%)
# 🤖 AI検証: 12件削除
# ⏱️ 処理時間: 18.3分
```

### 3. **AI検証による地名品質向上**
```bash
# 既存地名のAI検証（削除候補表示）
python3 run_pipeline.py --ai-verify --ai-verify-limit 50

# AI検証結果に基づく自動削除
python3 run_pipeline.py --ai-verify-delete --ai-confidence-threshold 0.8

# 高精度検証（信頼度0.9以上で削除）
python3 run_pipeline.py --ai-verify-delete --ai-confidence-threshold 0.9
```

## 📊 **実証済み処理結果**

### 🏆 **牧野富太郎（植物学者）- 完全処理済み**
```
📚 処理作品: 14作品
📊 生成センテンス: 3,200件
🗺️ 抽出地名: 1,012件
🌍 ジオコーディング: 996件成功 (98.4%)
🤖 AI検証削除: 12件（「松村」「語原」「沢山」等）
⏱️ 処理時間: 22分
```

### 🏆 **二葉亭四迷（文豪）- 完全処理済み**
```
📚 処理作品: 16作品
�� 生成センテンス: 4,079件
🗺️ 抽出地名: 181件
🌍 ジオコーディング: 175件成功 (96.7%)
🤖 AI検証: 高品質維持
⏱️ 処理時間: 15分
```

### 🏆 **sentence_placesテーブル復旧効果**
```
復旧前: 基本列のみ（地名、抽出情報）
復旧後: 包括的情報（前後文、作者作品、品質管理、統計）

追加列:
├── context_before, context_after      # 前後文復旧
├── author_name, work_title            # 作者・作品情報
├── quality_score, relevance_score     # 品質管理指標
├── place_frequency_*                  # 統計情報
└── verification_status                # 検証状況

効果: 文学研究・データ分析の大幅改善
```

## 🔧 **高度な機能・設定**

### 🤖 **AI検証システム詳細**
```bash
# 段階的信頼度設定
--ai-confidence-threshold 0.5   # 緩い検証（多くの地名を検証）
--ai-confidence-threshold 0.7   # 標準検証（バランス重視）
--ai-confidence-threshold 0.9   # 厳格検証（高確信度のみ削除）

# 処理量制御
--ai-verify-limit 20            # 少量検証（開発・テスト用）
--ai-verify-limit 100           # 大量検証（本格運用）
--ai-verify-limit 500           # 全量検証（メンテナンス時）
```

### 📊 **データベース管理**
```bash
# sentence_places品質保証
python3 database/sentence_places_enricher.py

# データベーススキーマ更新
python3 database/migrate_authors_schema.py

# リレーション情報更新
python3 database/update_sentence_places_relations.py
```

## 📈 **システム性能・品質指標**

### ⚡ **処理性能**
- **地名抽出速度**: 200.5件/秒
- **ジオコーディング成功率**: 96-98.4%
- **AI検証精度**: 0.8-0.9の高確信度
- **メモリ効率**: < 800MB使用量

### 🏆 **品質保証**
- **統合テスト成功率**: 100%（7つのテスト）
- **データ完整性**: sentence_placesテーブル完全復旧
- **AI検証効果**: 無効地名の自動検出・削除
- **レガシー統合**: バージョン付きファイルの標準化

### 📊 **データベース統計**
```sql
-- 現在のデータベース状況
総センテンス数: 15,000+件
抽出地名数: 2,000+件
処理作者数: 3名（完全処理）+ 多数（部分処理）
ジオコーディング済み: 1,900+件
AI検証済み: 1,200+件
```

## 🛠️ **開発・運用ガイド**

### 📋 **新作者追加の標準フロー**
1. **基本処理**: `python3 run_pipeline.py --author "作者名"`
2. **AI検証**: `python3 run_pipeline.py --ai-verify-delete`
3. **品質確認**: `python3 run_pipeline.py --status "作者名"`
4. **データ保守**: `python3 database/sentence_places_enricher.py`

### 🧪 **テスト・品質保証**
```bash
# 統合テスト実行
python3 tests/test_integration.py

# 最終統合テスト
python3 tests/step4_final_integration_test.py
```

### 🔧 **メンテナンス**
```bash
# データベースクリーンアップ
python3 scripts/fix_works_count.py

# 作者データ更新
python3 scripts/import_authors_from_json.py
```

## 📚 **API・拡張性**

### 🌐 **FastAPI統合**
```bash
# Web API サーバー起動
python3 main.py

# エンドポイント例:
# GET /authors/{author_id}          # 作者情報取得
# GET /works/{work_id}              # 作品情報取得  
# GET /places/                      # 地名一覧取得
```

### 🔌 **モジュール使用例**
```python
# AI文脈判断型ジオコーディング
from ai.context_aware_geocoding import ContextAwareGeocoder
geocoder = ContextAwareGeocoder()

# 地名抽出
from extractors.places.enhanced_place_extractor import EnhancedPlaceExtractorV3
extractor = EnhancedPlaceExtractorV3()

# データベース管理
from database.manager import DatabaseManager
db = DatabaseManager()
```

## 📋 **技術文書・報告書**

### 📄 **完成報告書・仕様書**
- `notebooks/2025年6月24日_リファクタリング完成報告書.md` - アーキテクチャ刷新
- `notebooks/2025年6月23日_AI検証機能統合_報告書.md` - AI品質保証システム
- `notebooks/2025年6月21日_二葉亭四迷統合パイプライン_報告書.md` - 作者処理実績
- `notebooks/2025年6月19日_包括的コード解説書.md` - システム全体解説

### 🔧 **設定・計画文書**
- `notebooks/REFACTORING_PLAN.md` - リファクタリング計画
- `notebooks/database_redesign_proposal.md` - DB設計提案
- `notebooks/pipeline_config.yaml` - パイプライン設定

## 🚀 **今後の展開可能性**

### 📅 **短期展開（1-2ヶ月）**
- **フロントエンド実装**: React + TypeScript による地図表示システム
- **REST API拡張**: 地名検索・統計・可視化API
- **バッチ処理最適化**: 大量作者データの高速処理

### 📅 **中期展開（3-6ヶ月）**
- **マイクロサービス化**: モジュール独立デプロイ・スケーラビリティ向上
- **機械学習強化**: 地名分類・パターン学習・予測機能
- **多言語対応**: 国際化・他言語文学作品対応

### 📅 **長期展開（6-12ヶ月）**
- **AI高度化**: GPT-4o等最新AIモデル統合・マルチモーダル対応
- **リアルタイム処理**: ストリーミング処理・ライブ解析
- **クラウドネイティブ**: 分散処理・コンテナ化・CI/CD

## 🔗 **関連リンク・ライセンス**

### 📚 **データソース**
- [青空文庫](https://www.aozora.gr.jp/) - パブリックドメイン文学作品
- [Wikipedia](https://ja.wikipedia.org/) - 作者情報・地理情報
- [OpenAI API](https://openai.com/api/) - AI文脈分析・検証

### ⚖️ **ライセンス**
MIT License - 商用利用・改変・再配布可能

### 🤝 **コントリビューション**
Issue・Pull Request歓迎。特に以下の分野での貢献を募集：
- 新しい文豪作品の追加処理
- AI検証精度の向上
- フロントエンド・可視化機能
- パフォーマンス最適化

---

**🌟 文豪ゆかり地図システム v4.0** - 次世代AI統合による文学地理学研究の新たな地平
