-- 文豪ゆかり地図システムv5 データベーススキーマ
-- 階層構造・AI検証・統計キャッシュ・処理ログ統合設計
-- 作成日: 2025年6月25日

-- ========================================
-- 1. 新テーブル（sections: 階層構造）
-- ========================================
CREATE TABLE sections (
    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    section_type VARCHAR(20) NOT NULL CHECK (section_type IN ('chapter', 'paragraph', 'sentence')),
    parent_section_id INTEGER,
    section_number INTEGER,
    title VARCHAR(200),
    content TEXT,
    character_position INTEGER,
    character_length INTEGER,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (work_id) REFERENCES works(work_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_section_id) REFERENCES sections(section_id) ON DELETE CASCADE
);

-- ========================================
-- 2. 新テーブル（ai_verifications: AI検証）
-- ========================================
CREATE TABLE ai_verifications (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_mention_id INTEGER NOT NULL,
    ai_model VARCHAR(50) NOT NULL,
    verification_type VARCHAR(50) NOT NULL CHECK (verification_type IN 
        ('place_validation', 'context_analysis', 'false_positive_check', 'confidence_boost')),
    
    input_context TEXT,
    ai_response JSON,
    raw_response TEXT,
    
    confidence_score DECIMAL(3, 2),
    is_valid_place BOOLEAN,
    reasoning TEXT,
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN 
        ('pending', 'verified', 'rejected', 'uncertain', 'needs_review')),
    
    processing_time_ms INTEGER,
    api_cost DECIMAL(8, 6),
    verified_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 3. 新テーブル（statistics_cache: 統計キャッシュ）
-- ========================================
CREATE TABLE statistics_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key VARCHAR(200) NOT NULL UNIQUE,
    cache_type VARCHAR(50) NOT NULL CHECK (cache_type IN 
        ('author_stats', 'work_stats', 'place_stats', 'global_stats', 'search_results')),
    entity_id INTEGER,
    data JSON NOT NULL,
    
    expires_at DATETIME,
    hit_count INTEGER DEFAULT 0,
    last_accessed DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 4. 新テーブル（processing_logs: 処理ログ）
-- ========================================
CREATE TABLE processing_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER,
    process_type VARCHAR(50) NOT NULL CHECK (process_type IN 
        ('text_extraction', 'place_extraction', 'geocoding', 'ai_verification', 
         'full_pipeline', 'migration', 'maintenance')),
    
    status VARCHAR(20) NOT NULL DEFAULT 'started' CHECK (status IN 
        ('started', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
    
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    processing_duration_ms INTEGER,
    
    error_message TEXT,
    error_type VARCHAR(100),
    stack_trace TEXT,
    
    statistics JSON,
    configuration JSON,
    
    user_agent VARCHAR(200),
    ip_address VARCHAR(45),
    
    FOREIGN KEY (work_id) REFERENCES works(work_id) ON DELETE SET NULL
);

-- ========================================
-- 5. インデックス（新テーブル用）
-- ========================================
CREATE INDEX idx_sections_work ON sections(work_id);
CREATE INDEX idx_sections_parent ON sections(parent_section_id);
CREATE INDEX idx_sections_type ON sections(section_type);
CREATE INDEX idx_sections_work_type ON sections(work_id, section_type);

CREATE INDEX idx_ai_verifications_mention ON ai_verifications(place_mention_id);
CREATE INDEX idx_ai_verifications_model ON ai_verifications(ai_model);
CREATE INDEX idx_ai_verifications_type ON ai_verifications(verification_type);
CREATE INDEX idx_ai_verifications_status ON ai_verifications(verification_status);

CREATE INDEX idx_statistics_cache_key ON statistics_cache(cache_key);
CREATE INDEX idx_statistics_cache_type ON statistics_cache(cache_type);
CREATE INDEX idx_statistics_cache_expires ON statistics_cache(expires_at);

CREATE INDEX idx_processing_logs_work ON processing_logs(work_id);
CREATE INDEX idx_processing_logs_type ON processing_logs(process_type);
CREATE INDEX idx_processing_logs_status ON processing_logs(status);
CREATE INDEX idx_processing_logs_started ON processing_logs(started_at);
