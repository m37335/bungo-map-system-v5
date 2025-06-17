# 青空文庫作家リスト機能

このドキュメントでは、青空文庫の作家リストページから作者情報を取得してデータベースに格納する機能について説明します。

## 機能概要

- **作家リスト取得**: 青空文庫の作家一覧ページから全作家情報を自動取得
- **詳細情報解析**: 作家名、作品数、著作権状態、別名情報などを構造化
- **データベース統合**: 取得した作家情報をデータベースに格納・管理
- **検索・統計**: 作家検索、セクション別表示、統計情報の提供

## 主要コンポーネント

### 1. AuthorListScraper (`extractors/author_list_scraper.py`)

青空文庫の作家リストページ（https://www.aozora.gr.jp/index_pages/person_all.html）を解析して作家情報を取得するクラス。

**特徴**:
- レート制限対応（サイトに負荷をかけない）
- 詳細な作家情報の構造化（作品数、著作権状態、別名等）
- 統計情報の自動計算
- JSON形式での出力対応

### 2. AuthorDatabaseService (`extractors/author_database_service.py`)

作家リストスクレイパーとデータベースを統合するサービスクラス。

**機能**:
- 全作家情報の同期
- 既存データとの差分更新
- 作家検索機能
- 統計情報の提供

### 3. 拡張データベースモデル

作家モデル（`database/models.py`）に青空文庫関連フィールドを追加：

```python
# 青空文庫関連フィールド
aozora_author_url = Column(String(512))  # 青空文庫作家ページURL
copyright_status = Column(String(20))    # 著作権状態
aozora_works_count = Column(Integer)     # 青空文庫の公開作品数
alias_info = Column(Text)                # 別名情報
section = Column(String(10))             # 50音順セクション
```

## 使用方法

### CLIコマンド

#### 1. 作家リスト同期

```bash
# 全作家情報をデータベースに同期
python -m bungo-map-system-v4.cli.commands sync-authors

# 強制的に全作家情報を更新
python -m bungo-map-system-v4.cli.commands sync-authors --force-refresh
```

#### 2. 作家検索

```bash
# 作家名で検索
python -m bungo-map-system-v4.cli.commands search-authors 夏目

# 検索結果数を制限
python -m bungo-map-system-v4.cli.commands search-authors 芥川 --limit 10

# 特定セクションで検索
python -m bungo-map-system-v4.cli.commands search-authors 森 --section ナ
```

#### 3. 統計情報表示

```bash
# 全体統計
python -m bungo-map-system-v4.cli.commands author-stats

# セクション別統計
python -m bungo-map-system-v4.cli.commands author-stats --section ア
```

#### 4. セクション一覧

```bash
# 利用可能なセクション一覧を表示
python -m bungo-map-system-v4.cli.commands list-sections
```

### プログラムからの使用

#### 基本的な使用例

```python
import asyncio
from extractors.author_database_service import AuthorDatabaseService

async def main():
    # サービス初期化
    service = AuthorDatabaseService()
    
    # 全作家同期
    result = await service.sync_all_authors()
    print(f"同期結果: {result}")
    
    # 作家検索
    authors = await service.search_authors("夏目", limit=5)
    for author in authors:
        print(f"{author['name']}: {author['works_count']}作品")
    
    # 統計取得
    stats = await service.get_author_statistics()
    print(f"総作家数: {stats['total_authors']}")

asyncio.run(main())
```

#### スクレイパー単体使用

```python
from extractors.author_list_scraper import AuthorListScraper

# スクレイパー初期化
scraper = AuthorListScraper(rate_limit=1.0)

# 作家情報取得
authors = scraper.fetch_all_authors()

# 統計表示
stats = scraper.get_statistics(authors)
print(f"総作家数: {stats['total_authors']}")

# JSON保存
scraper.save_authors_to_json(authors, "data/aozora_authors.json")
```

## データ構造

### AuthorInfo

作家情報のデータクラス：

```python
@dataclass
class AuthorInfo:
    name: str                    # 作家名
    name_reading: Optional[str]  # 読み仮名（推定）
    works_count: int            # 公開作品数
    copyright_status: str       # 著作権状態（'expired', 'active', 'unknown'）
    author_url: Optional[str]   # 青空文庫作家ページURL
    alias_info: Optional[str]   # 別名情報
    section: str                # 50音順セクション
```

### 統計情報

```python
{
    'total_authors': 1500,           # 総作家数
    'total_works': 15000,           # 総作品数
    'copyright_active': 100,        # 著作権存続作家数
    'copyright_expired': 1400,      # 著作権満了作家数
    'section_stats': {              # セクション別統計
        'ア': 150,
        'カ': 120,
        # ...
    },
    'top_authors': [                # 作品数上位作家
        ('芥川 竜之介', 379),
        ('太宰 治', 295),
        # ...
    ],
    'average_works_per_author': 10.0
}
```

## テスト

### テストスクリプト実行

```bash
# 総合テスト実行
python bungo-map-system-v4/test_author_scraper.py
```

テスト内容：
1. **基本スクレイパーテスト**: 作家情報取得の動作確認
2. **項目解析テスト**: HTML解析ロジックの動作確認
3. **データベース統合テスト**: データベース格納・検索の動作確認

## 設定

### レート制限

青空文庫サイトへの負荷を軽減するため、リクエスト間隔を制御：

```python
# デフォルト: 1秒間隔
scraper = AuthorListScraper(rate_limit=1.0)

# より慎重に: 2秒間隔
scraper = AuthorListScraper(rate_limit=2.0)
```

### データベース設定

`core/config.py`でデータベース接続を設定：

```python
DATABASE_URL = "sqlite:///data/bungo_map.db"  # SQLite
# DATABASE_URL = "postgresql://user:pass@localhost/bungo_map"  # PostgreSQL
```

## 注意事項

1. **利用規約の遵守**: 青空文庫の利用規約を確認し、適切な間隔でのアクセスを心がけてください
2. **レート制限**: デフォルトで1秒間隔のレート制限を設定していますが、必要に応じて調整してください
3. **エラーハンドリング**: ネットワークエラーやページ構造変更に対する適切な処理を実装しています
4. **データ整合性**: 同期時に既存データとの整合性を確認し、適切に更新します

## 今後の拡張予定

1. **セクション別同期**: 特定の50音順セクションのみの同期機能
2. **増分更新**: 変更された作家情報のみの効率的な更新
3. **作家詳細情報**: 個別作家ページからの詳細情報取得
4. **作品リスト連携**: 各作家の作品リストとの統合

## サポート

問題が発生した場合は、以下を確認してください：

1. ネットワーク接続の確認
2. 青空文庫サイトの可用性確認
3. データベース接続設定の確認
4. ログファイルでのエラー詳細確認

詳細なログは以下で確認できます：

```bash
# デバッグレベルでの実行
python bungo-map-system-v4/test_author_scraper.py --log-level DEBUG
``` 