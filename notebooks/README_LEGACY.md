# 文豪ゆかり地図システム v4.0 - 地名マスター優先設計版

## 🎯 概要

文豪作品に登場する地名を高精度で抽出・分析し、地名マスターデータベースによる効率的な管理を実現するシステムです。

### 🌟 v4.0の主要特徴

- **地名マスター優先設計**: 重複ジオコーディング完全回避
- **AI検証機能**: 高精度な地名品質保証
- **効率的なAPI利用**: コスト最適化とレート制限対応
- **完全自動化**: 作者指定でワンコマンド処理

## 🏗️ システム構成

### 地名マスター優先アーキテクチャ

```
📚 青空文庫作品 
    ↓
🔍 地名抽出（GinZA + AI）
    ↓
🗂️ 地名マスター検索
    ↓
⚡ 既存地名 → キャッシュ参照（高速）
🆕 新規地名 → マスター作成 → ジオコーディング
    ↓
💾 sentence_places保存（master_id参照）
```

### 主要コンポーネント

- **`run_pipeline.py`**: 統合パイプライン（v3対応）
- **`extractors/enhanced_place_extractor_v3.py`**: 地名抽出エンジン
- **`extractors/place_master_manager_v2.py`**: 地名マスター管理
- **`database/schema_v2.sql`**: 新しいデータベーススキーマ
- **`database/migrate_to_v2.py`**: マイグレーションツール

## 🚀 クイックスタート

### 1. 環境設定

```bash
# 必要パッケージのインストール
pip install -r requirements.txt

# 環境変数設定（.envファイル作成）
cp env.example .env
# OPENAI_API_KEY, GOOGLE_MAPS_API_KEYを設定
```

### 2. データベース初期化

```bash
# 新規データベース作成
python3 database/init_db_v2.py

# 既存データベースのマイグレーション
python3 database/init_db_v2.py --migrate

# データベース状況確認
python3 database/init_db_v2.py --status
```

### 3. 基本的な使用方法

```bash
# 作者の完全処理（地名マスター優先）
python3 run_pipeline.py --author "夏目漱石"

# 処理状況確認（地名マスター統計含む）
python3 run_pipeline.py --status "夏目漱石"

# AI地名品質検証
python3 run_pipeline.py --ai-verify

# 自動品質改善
python3 run_pipeline.py --ai-verify-delete
```

## 📊 性能・効率性

### 地名マスター効果

- **キャッシュヒット率**: 既存地名の瞬時検索
- **重複排除**: 同一地名の重複ジオコーディング回避
- **API効率化**: 新規地名のみAPI呼び出し
- **コスト削減**: 最大80%のAPI呼び出し削減

### 処理速度改善

- **従来方式**: 全地名をジオコーディング
- **新方式**: 既存地名はmaster_id参照（平均0.001秒）
- **新規地名**: マスター作成 + ジオコーディング（平均2秒）

## 🗂️ データベース構造

### 地名マスターテーブル

```sql
-- 地名マスター（正規化済み地名）
CREATE TABLE place_masters (
    master_id INTEGER PRIMARY KEY,
    normalized_name VARCHAR(255) UNIQUE,  -- 正規化名
    display_name VARCHAR(255),           -- 表示名
    latitude FLOAT,                      -- 緯度
    longitude FLOAT,                     -- 経度
    usage_count INTEGER DEFAULT 0,      -- 使用回数
    validation_status VARCHAR(20)       -- 検証状況
);

-- 地名異表記
CREATE TABLE place_aliases (
    alias_id INTEGER PRIMARY KEY,
    master_id INTEGER,                   -- マスターID参照
    alias_name VARCHAR(255),            -- 異表記
    alias_type VARCHAR(50)              -- 表記タイプ
);

-- センテンス地名関係
CREATE TABLE sentence_places (
    relation_id INTEGER PRIMARY KEY,
    sentence_id INTEGER,                 -- センテンスID
    master_id INTEGER,                   -- マスターID参照
    matched_text VARCHAR(255),          -- マッチしたテキスト
    extraction_confidence FLOAT,        -- 抽出信頼度
    ai_verified BOOLEAN DEFAULT FALSE   -- AI検証済み
);
```

### 互換性ビュー

```sql
-- 既存コード互換性のため
CREATE VIEW places AS
SELECT 
    'pm_' || master_id AS place_id,
    display_name AS place_name,
    latitude, longitude,
    usage_count AS mention_count
FROM place_masters;
```

## 🤖 AI検証機能

### 高精度地名判定

```bash
# 地名品質検証（20件）
python3 run_pipeline.py --ai-verify

# 大量検証（100件）
python3 run_pipeline.py --ai-verify --ai-verify-limit 100

# 高信頼度検証（0.9閾値）
python3 run_pipeline.py --ai-verify --ai-confidence-threshold 0.9

# 自動削除実行
python3 run_pipeline.py --ai-verify-delete --ai-verify-limit 50
```

### AI検証機能

- **複数文脈分析**: 最大5文での総合判定
- **詳細理由提供**: 判定根拠の明確化
- **信頼度評価**: 0.8-0.9の高確信度
- **自動削除**: 無効地名の自動クリーンアップ

## 📈 システム監視

### 統計情報確認

```bash
# 地名マスター統計
python3 -c "
from extractors.place_master_manager_v2 import PlaceMasterManagerV2
manager = PlaceMasterManagerV2()
manager.print_statistics()
"

# パイプライン統計
python3 -c "
from run_pipeline import BungoPipeline
pipeline = BungoPipeline()
pipeline.print_master_statistics()
"
```

### 典型的な統計情報

```
📊 地名マスター統計:
  総マスター数: 371
  ジオコーディング済み: 368 (99.2%)
  使用回数計: 2,458
  平均使用回数: 6.6

⚡ キャッシュ効率性:
  キャッシュヒット: 2,087 (85.0%)
  新規マスター: 371 (15.0%)
  API節約: 2,087回のジオコーディング回避
```

## 🔧 開発・保守

### データベースマイグレーション

```bash
# 現在のスキーマバージョン確認
python3 database/init_db_v2.py --status

# v1からv2へのマイグレーション
python3 database/migrate_to_v2.py

# 強制再作成（バックアップ付き）
python3 database/init_db_v2.py --force
```

### 統合テスト

```bash
# 包括的統合テスト
python3 test_integration_v2.py

# 基本テストのみ
python3 test_integration_v2.py --quick

# 詳細ログ付き
python3 test_integration_v2.py --verbose
```

## 📖 詳細ドキュメント

### 技術報告書

- **[地名マスター優先設計提案書](database_redesign_proposal.md)**
- **[AI検証機能統合報告書](notebooks/2025年6月23日_AI検証機能統合_高精度地名品質保証システム完成報告書.md)**
- **[総合機能・課題分析報告書](notebooks/2025年6月23日_文豪ゆかり地図システムv4_総合機能・課題分析報告書.md)**

### API・コードリファレンス

```python
# 地名マスター管理
from extractors.place_master_manager_v2 import PlaceMasterManagerV2

manager = PlaceMasterManagerV2()

# 地名マスター検索・作成
result = manager.find_or_create_master("東京")
print(f"Master ID: {result['master_id']}")

# 統計取得
stats = manager.get_master_statistics()
print(f"総マスター数: {stats['total_masters']}")

# 地名抽出v3
from extractors.enhanced_place_extractor_v3 import EnhancedPlaceExtractorV3

extractor = EnhancedPlaceExtractorV3()

# 作品の地名処理
stats = extractor.process_work_sentences(work_id=123, title="こころ")
print(f"処理センテンス: {stats['processed_sentences']}")
```

## 🎯 ロードマップ

### Phase 1: 完了 ✅
- [x] 地名マスター優先設計実装
- [x] 既存システムとの完全統合
- [x] パフォーマンス最適化

### Phase 2: 開発中 🚧
- [ ] フロントエンド地図表示
- [ ] REST API実装
- [ ] リアルタイム地名検索

### Phase 3: 計画中 📋
- [ ] 機械学習による地名分類
- [ ] 時代考証機能
- [ ] 多言語対応

## 🤝 コントリビューション

1. フォークしてブランチ作成
2. 変更を実装
3. 統合テスト実行: `python3 test_integration_v2.py`
4. プルリクエスト作成

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

## 🙏 謝辞

- 青空文庫プロジェクト
- GinZA（日本語自然言語処理）
- OpenAI GPT-4
- Google Maps API

---

**バージョン**: 4.0 (地名マスター優先設計)  
**最終更新**: 2025年6月23日  
**作成者**: AI Assistant  
**システム**: 文豪ゆかり地図システム v4.0 