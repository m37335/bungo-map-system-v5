# 文豪ゆかり地図システム v4.0 - 全体リファクタリング計画

## 🎯 リファクタリングの目的

### 現在の課題
1. **コード構造の複雑化**: 65ファイル、extractorsに24ファイル集中
2. **バージョン混在**: v2, v3ファイルが共存
3. **巨大ファイル**: `ai/context_aware_geocoding.py` (1,489行)
4. **責任分散**: 機能が適切に分離されていない
5. **依存関係**: 複雑なインポート構造

### 目標
1. **保守性向上**: 明確なモジュール分離
2. **可読性向上**: 適切なファイルサイズ（<300行）
3. **一貫性確保**: 統一された命名規則
4. **拡張性向上**: 新機能追加の容易性
5. **テスト容易性**: 単体テスト可能な構造

## 🏗️ 新アーキテクチャ設計

### Phase 1: ディレクトリ構造再編

```
bungo-map-system-v4/
├── bungo_map/                      # メインパッケージ
│   ├── __init__.py
│   ├── core/                       # コアシステム
│   │   ├── __init__.py
│   │   ├── config.py               # 設定管理
│   │   ├── database.py             # DB接続管理
│   │   ├── exceptions.py           # カスタム例外
│   │   └── constants.py            # 定数定義
│   ├── models/                     # データモデル
│   │   ├── __init__.py
│   │   ├── author.py               # 作者モデル
│   │   ├── work.py                 # 作品モデル
│   │   ├── place.py                # 地名モデル
│   │   └── sentence.py             # センテンスモデル
│   ├── extractors/                 # データ抽出
│   │   ├── __init__.py
│   │   ├── aozora/                 # 青空文庫関連
│   │   │   ├── scraper.py          # スクレイピング
│   │   │   ├── metadata.py         # メタデータ抽出
│   │   │   └── processor.py        # テキスト処理
│   │   ├── places/                 # 地名抽出
│   │   │   ├── extractor.py        # 地名抽出エンジン
│   │   │   ├── normalizer.py       # 地名正規化
│   │   │   └── validator.py        # 地名検証
│   │   └── wikipedia/              # Wikipedia関連
│   │       └── enricher.py         # 情報補完
│   ├── ai/                         # AI機能
│   │   ├── __init__.py
│   │   ├── llm/                    # LLM関連
│   │   │   ├── client.py           # API接続
│   │   │   ├── prompts.py          # プロンプト管理
│   │   │   └── cache.py            # キャッシュ機能
│   │   ├── geocoding/              # ジオコーディング
│   │   │   ├── geocoder.py         # メインジオコーダー
│   │   │   ├── context.py          # 文脈分析
│   │   │   └── validation.py       # AI検証
│   │   └── nlp/                    # 自然言語処理
│   │       ├── ginza_processor.py  # GiNZA処理
│   │       └── text_analyzer.py    # テキスト分析
│   ├── database/                   # データベース管理
│   │   ├── __init__.py
│   │   ├── managers/               # データ管理
│   │   │   ├── author_manager.py   # 作者データ管理
│   │   │   ├── place_manager.py    # 地名データ管理
│   │   │   └── sentence_manager.py # センテンス管理
│   │   ├── migrations/             # マイグレーション
│   │   │   └── *.sql
│   │   └── schemas/                # スキーマ定義
│   │       └── schema.sql
│   ├── pipeline/                   # パイプライン実行
│   │   ├── __init__.py
│   │   ├── runner.py               # メインランナー
│   │   ├── steps/                  # 処理ステップ
│   │   │   ├── author_step.py      # 作者処理
│   │   │   ├── extraction_step.py  # 抽出処理
│   │   │   └── geocoding_step.py   # ジオコーディング
│   │   └── validators/             # 検証
│   │       └── quality_validator.py
│   ├── utils/                      # ユーティリティ
│   │   ├── __init__.py
│   │   ├── logging.py              # ログ設定
│   │   ├── text_utils.py           # テキスト処理
│   │   └── file_utils.py           # ファイル操作
│   └── cli/                        # CLI インターフェース
│       ├── __init__.py
│       ├── main.py                 # メインCLI
│       └── commands/               # コマンド定義
│           ├── author.py           # 作者コマンド
│           ├── extract.py          # 抽出コマンド
│           └── status.py           # ステータス確認
├── tests/                          # テスト
│   ├── unit/                       # 単体テスト
│   ├── integration/                # 統合テスト
│   └── fixtures/                   # テストデータ
├── configs/                        # 設定ファイル
│   ├── pipeline.yaml               # パイプライン設定
│   └── logging.yaml                # ログ設定
├── scripts/                        # 運用スクリプト
│   ├── setup.py                    # セットアップ
│   └── maintenance.py              # メンテナンス
├── docs/                           # ドキュメント
│   ├── api/                        # API文書
│   ├── guides/                     # ガイド
│   └── architecture.md             # アーキテクチャ
├── requirements.txt                # 依存関係
├── setup.py                        # パッケージ設定
└── README.md                       # プロジェクト概要
```

## 🔧 リファクタリング手順

### Phase 1: 構造準備 (Day 1)
1. **新ディレクトリ構造作成**
2. **core モジュール実装**
3. **設定システム統一**
4. **ログシステム整備**

### Phase 2: モデル分離 (Day 1-2)
1. **データモデル抽出**
2. **型定義統一**
3. **バリデーション統合**

### Phase 3: 機能分解 (Day 2-3)
1. **巨大ファイル分割**
   - `ai/context_aware_geocoding.py` → 複数ファイルに分割
   - `run_pipeline.py` → pipeline/runner.py + steps/
2. **責任分離**
3. **インターフェース定義**

### Phase 4: 依存関係整理 (Day 3-4)
1. **インポート構造最適化**
2. **循環依存解決**
3. **DI (Dependency Injection) 導入**

### Phase 5: テスト整備 (Day 4-5)
1. **単体テスト追加**
2. **統合テスト更新**
3. **カバレッジ向上**

### Phase 6: ドキュメント更新 (Day 5)
1. **API文書自動生成**
2. **アーキテクチャ文書**
3. **ガイド更新**

## 📋 実装優先順位

### 🚨 緊急 (即座に実施)
1. `ai/context_aware_geocoding.py` の分割
2. extractorsディレクトリの整理
3. 設定管理の統一

### ⚡ 重要 (1-2日以内)
1. モデル層の分離
2. パイプライン構造の整理
3. 依存関係の最適化

### 📈 改善 (1週間以内)
1. テスト構造の整備
2. CLI の再設計
3. ドキュメント更新

## 🎯 期待される効果

### 保守性
- **ファイルサイズ**: 平均200行以下
- **責任分離**: 単一責任原則の徹底
- **可読性**: 明確な命名とコメント

### 拡張性
- **モジュラー設計**: 新機能追加の容易性
- **プラグイン対応**: 抽出器・検証器の追加
- **API設計**: 外部連携の準備

### 品質
- **テストカバレッジ**: 80%以上
- **型安全性**: Type Hintsの徹底
- **エラーハンドリング**: 適切な例外処理

### 運用
- **設定管理**: 環境別設定対応
- **ログ管理**: 構造化ログ
- **監視**: メトリクス取得準備

## 🚀 移行戦略

### バックワード互換性
1. **既存API維持**: 段階的移行
2. **設定ファイル**: 自動変換スクリプト
3. **データベース**: マイグレーション対応

### リスク軽減
1. **段階実施**: 機能単位での移行
2. **テスト強化**: リグレッション防止
3. **ロールバック**: 緊急時の復旧計画

---

**作成日**: 2025年6月23日  
**対象**: 文豪ゆかり地図システム v4.0  
**期間**: 5日間の集中リファクタリング 