# 文豪マップシステム V4 - データ統合ワークフロー仕様書

作成日: 2025-06-18  
対象リポジトリ: [bungo-map-system-v4](https://github.com/m37335/bungo-map-system-v4)

---

## 🎯 概要

このドキュメントは、青空文庫のデータを活用し、以下の流れで文豪作品の本文とセンテンスをデータベースに統合するワークフローの仕様を記述します。

---

## 🗂 作業フロー一覧

### ① 作者URLの取得

- **入力**: `authors` テーブル
  - 例: `author_id`, `name`, `url`
- **出力**: 各作者の青空文庫ページURL
- **目的**: 各作品一覧を取得するための入口となる

---

### ② 作品リストと作品URLの取得

- **入力**: 各作者ページのHTML
- **処理内容**:
  - `<ol>`タグや作品テーブルから作品名とリンクを抽出
- **出力**: 
  - `title`: 作品タイトル
  - `url`: 作品ページのURL
  - `genre`: ジャンル分類（分類不可時はnull）

---

### ③ 作品リストのデータベース保存

- **対象テーブル**: `works`
- **保存項目**:
  - `work_id`, `author_id`, `title`, `work_url`, `genre`, `created_at`
- **補足**: 重複登録防止のため、一意制約を検討

---

### ④ XHTMLリンクの取得と本文取得

- **入力**: 各作品ページのHTML
- **処理**:
  - 「XHTML版で読む」リンクを取得
  - 対象HTMLをダウンロードしローカル保存
- **出力**: XHTMLファイル本体

---

### ⑤ 本文テキストのクリーニング

- **入力**: XHTMLファイル
- **処理**:
  - HTMLタグ除去（`<ruby>`, `<rt>`, `<a>`など）
  - ノイズ（見出し・注釈・キャプションなど）の削除
- **出力**: プレーンテキストの本文

---

### ⑥ センテンス単位での分割

- **入力**: クリーニング済み本文テキスト
- **処理**:
  - `。`や改行による初期分割
  - 文末記号ベースの正規化処理 or LLM補助分割
- **出力**: センテンス配列（リスト）

例:
```json
[
  { "sentence_order": 1, "text": "吾輩は猫である。" },
  { "sentence_order": 2, "text": "名前はまだ無い。" }
]
```

---

### ⑦ センテンスのデータベース保存

- **対象テーブル**: `sentences`
- **保存項目**:
  - `sentence_id`, `work_id`, `sentence_order`, `text`, `created_at`
- **備考**:
  - `work_id` により作品と関連付け

---

## 🛠 推奨ファイル構成案

```
bungo-map-system-v4/
├── db/
│   └── schema.sql
├── notebooks/
│   └── aozora_author_database_integration_20250617.md
├── scripts/
│   ├── fetch_author_works.py        # ステップ①②③
│   ├── fetch_work_text.py           # ステップ④⑤
│   ├── segment_sentences.py         # ステップ⑥
│   └── save_sentences.py            # ステップ⑦
```

---

## 📋 ToDo一覧（YAML形式）

```yaml
todo:
  - task: 作者URL一覧の取得
    input: authorsテーブル
    output: 各URL

  - task: 作品タイトル・URL取得
    input: 作者個別ページ（HTML）
    output: worksテーブル用データ構造

  - task: 作品データベース登録
    input: 作品リスト
    output: worksテーブル保存

  - task: XHTML版本文リンクの取得
    input: 作品ページ（HTML）
    output: XHTMLファイルURL

  - task: 本文の取得とクリーニング
    input: XHTMLファイル
    output: プレーンテキスト本文

  - task: センテンスへの分割
    input: プレーンテキスト
    output: センテンスリスト

  - task: センテンスのDB登録
    input: センテンスリスト
    output: sentencesテーブル登録
```

---

## 🧠 備考

- センテンス分割処理は将来的に形態素解析（e.g., MeCab）や LLM 活用を前提とした拡張が可能。
- DB保存前にバリデーションチェック（空文字除外、同一文重複除去）を行うと安定運用が期待される。