# 文豪ゆかり地図システムv4 データベース再設計提案

## 🎯 設計思想の変更

### 現在（問題のあるアプローチ）
```
地名抽出 → places直接登録 → 重複ジオコーディング → 後処理統合
```

### 新設計（効率的アプローチ）
```
地名抽出 → マスター検索・参照 → 必要時のみジオコーディング
```

## 🏗️ 新テーブル設計

### 1. place_masters（地名マスターテーブル）
```sql
CREATE TABLE place_masters (
    master_id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_name VARCHAR(255) NOT NULL UNIQUE,  -- 正規化地名（検索キー）
    display_name VARCHAR(255) NOT NULL,            -- 表示用地名
    canonical_name VARCHAR(255),                    -- 標準表記
    
    -- ジオコーディング情報
    latitude FLOAT,
    longitude FLOAT,
    geocoding_source VARCHAR(100),                  -- 'google_maps', 'openai', 'manual'
    geocoding_confidence FLOAT,
    geocoding_timestamp DATETIME,
    
    -- 地名メタデータ
    place_type VARCHAR(50),                         -- '都市', '山', '川', '建物'等
    prefecture VARCHAR(100),
    municipality VARCHAR(100),
    district VARCHAR(100),
    
    -- 使用統計
    usage_count INTEGER DEFAULT 0,
    first_used_at DATETIME,
    last_used_at DATETIME,
    
    -- 管理情報
    validation_status VARCHAR(20) DEFAULT 'pending', -- 'validated', 'pending', 'rejected'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_normalized_name (normalized_name),
    INDEX idx_display_name (display_name),
    INDEX idx_place_type (place_type)
);
```

### 2. place_aliases（地名異表記テーブル）
```sql
CREATE TABLE place_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id INTEGER NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50),                         -- 'variation', 'historical', 'colloquial'
    confidence FLOAT DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (master_id) REFERENCES place_masters(master_id),
    UNIQUE (master_id, alias_name),
    INDEX idx_alias_name (alias_name)
);
```

### 3. sentence_places（センテンス地名関係テーブル）
```sql
CREATE TABLE sentence_places (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sentence_id INTEGER NOT NULL,
    master_id INTEGER NOT NULL,                     -- place_mastersを直接参照
    
    -- 抽出情報
    matched_text VARCHAR(255) NOT NULL,             -- 元の抽出テキスト
    start_position INTEGER,
    end_position INTEGER,
    extraction_confidence FLOAT,
    extraction_method VARCHAR(50),                  -- 'ginza', 'ai', 'manual'
    
    -- AI検証情報
    ai_verified BOOLEAN DEFAULT FALSE,
    ai_confidence FLOAT,
    ai_verification_date DATETIME,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sentence_id) REFERENCES sentences(sentence_id),
    FOREIGN KEY (master_id) REFERENCES place_masters(master_id),
    UNIQUE (sentence_id, master_id, matched_text),
    INDEX idx_sentence_id (sentence_id),
    INDEX idx_master_id (master_id)
);
```

### 4. places（簡素化・非正規化ビューテーブル）
```sql
-- 既存コードとの互換性のため、ビューとして維持
CREATE VIEW places AS
SELECT 
    CONCAT('pm_', pm.master_id) AS place_id,
    pm.display_name AS place_name,
    pm.canonical_name,
    pm.latitude,
    pm.longitude,
    pm.place_type,
    pm.geocoding_confidence AS confidence,
    pm.prefecture,
    pm.municipality,
    pm.district,
    pm.usage_count AS mention_count,
    pm.geocoding_source AS source_system,
    pm.created_at,
    pm.updated_at,
    pm.master_id
FROM place_masters pm;
```

## 🔧 新地名抽出フロー

### PlaceMasterManager v2.0
```python
class PlaceMasterManagerV2:
    def extract_and_register_place(self, place_text: str, sentence_id: int) -> Optional[int]:
        """地名抽出からマスター登録まで一括処理"""
        
        # 1. 地名正規化
        normalized = self.normalize_place_name(place_text)
        
        # 2. マスター検索
        master_id = self.find_master_by_name(normalized)
        
        if master_id:
            # 既存マスター使用
            self.update_usage_stats(master_id)
            return master_id
        else:
            # 新規マスター作成
            master_id = self.create_new_master(place_text, normalized)
            
            # ジオコーディング実行（新規のみ）
            self.geocode_master(master_id)
            
            return master_id
    
    def create_new_master(self, original_text: str, normalized: str) -> int:
        """新規マスター地名作成"""
        # AI判定でフィルタリング
        if not self.ai_validate_place_name(original_text):
            return None
            
        # マスター作成
        return self.insert_master_place(normalized, original_text)
    
    def geocode_master(self, master_id: int):
        """マスター地名のジオコーディング（キャッシュ優先）"""
        # レート制限・キャッシュ対応
        # Google Maps API呼び出し
        # 結果をマスターテーブルに保存
```

## 📈 期待される効果

### 🚀 性能向上
- **ジオコーディング削減**: 重複地名のAPI呼び出し完全回避
- **処理速度向上**: マスター検索による高速化
- **メモリ効率**: 重複データ排除

### 💰 コスト削減
- **API使用量**: 新規地名のみジオコーディング
- **ストレージ**: 重複座標データ排除
- **処理時間**: 後処理統合作業不要

### 🔧 保守性向上
- **データ一貫性**: 単一真実源（Single Source of Truth）
- **拡張性**: 地名メタデータの体系的管理
- **デバッグ容易性**: 明確なデータフロー

## 🔄 移行戦略

### Phase 1: 新テーブル作成
```sql
-- 新テーブル群作成
-- 既存データの移行準備
```

### Phase 2: データ移行
```python
# 既存placesデータをplace_mastersに統合
# 重複地名の自動統合
# sentence_placesの関係再構築
```

### Phase 3: システム書き換え
```python
# 地名抽出ロジック更新
# ジオコーディング処理変更
# API最適化実装
```

### Phase 4: 旧システム削除
```python
# 旧placesテーブル削除
# 不要コード削除
# 最終テスト
```

## 🎯 実装優先順位

### 緊急（今日実装）
1. **新テーブル設計・作成**
2. **PlaceMasterManagerV2実装**
3. **基本的な検索・登録機能**

### 重要（今週実装）
1. **既存データ移行スクリプト**
2. **ジオコーディング統合**
3. **AI検証機能統合**

### 改善（来週実装）
1. **パフォーマンス最適化**
2. **統計機能強化**
3. **管理画面・可視化**

この新設計により、効率性・保守性・拡張性すべてが大幅に向上します！ 