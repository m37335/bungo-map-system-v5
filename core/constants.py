"""
文豪ゆかり地図システム - システム定数

システム全体で使用される定数を定義
"""

import os
from pathlib import Path

# プロジェクト基本パス
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CONFIG_DIR = PROJECT_ROOT / "configs"
LOGS_DIR = PROJECT_ROOT / "logs"

# データベース設定
DEFAULT_DB_PATH = DATA_DIR / "bungo_map.db"
BACKUP_DIR = DATA_DIR / "backups"

# API制限設定
OPENAI_LIMITS = {
    "rate_limit": 60,  # リクエスト/分
    "min_interval": 1.0,  # 秒
    "max_tokens": 4000,
    "timeout": 30
}

GOOGLE_MAPS_LIMITS = {
    "rate_limit": 600,  # リクエスト/分
    "min_interval": 0.1,  # 秒
    "timeout": 10
}

AOZORA_LIMITS = {
    "rate_limit": 10,  # リクエスト/分
    "min_interval": 6.0,  # 秒
    "timeout": 15
}

# 地名抽出設定
PLACE_EXTRACTION = {
    "min_confidence": 0.7,
    "max_places_per_sentence": 10,
    "filter_patterns": [
        r"^[あ-ん]{1,2}$",  # ひらがな1-2文字
        r"^[ア-ン]{1,2}$",  # カタカナ1-2文字
        r"^[0-9]+$",        # 数字のみ
    ]
}

# 地名タイプ
PLACE_TYPES = {
    "CITY": "都市",
    "PREFECTURE": "都道府県", 
    "DISTRICT": "地区",
    "MOUNTAIN": "山",
    "RIVER": "川",
    "STATION": "駅",
    "TEMPLE": "寺社",
    "BUILDING": "建物",
    "OTHER": "その他"
}

# AI検証設定
AI_VERIFICATION = {
    "default_confidence_threshold": 0.7,
    "min_context_sentences": 2,
    "max_context_sentences": 5,
    "batch_size": 10
}

# ログ設定
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_max_bytes": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# キャッシュ設定
CACHE_CONFIG = {
    "api_cache_file": DATA_DIR / "api_cache.json",
    "nlp_cache_file": CACHE_DIR / "nlp_cache.json",
    "max_cache_size": 10000,
    "cache_ttl": 7 * 24 * 3600  # 7日間（秒）
}

# バッチ処理設定
BATCH_CONFIG = {
    "default_batch_size": 100,
    "max_workers": 4,
    "chunk_size": 1000,
    "progress_interval": 10
}

# 品質保証設定
QUALITY_CONFIG = {
    "min_geocoding_success_rate": 0.8,
    "max_error_rate": 0.1,
    "validation_sample_size": 100
}

# 無効な地名パターン
INVALID_PLACE_PATTERNS = [
    # 時間表現
    r"^(今日|昨日|明日|一昨日|明後日)$",
    r"^(朝|昼|夕方|夜|深夜|早朝)$",
    r"^(春|夏|秋|冬|正月|盆)$",
    
    # 動作表現
    r"^(出発|到着|通過|経由)$",
    r"^(上る|下る|渡る|越える)$",
    
    # 抽象概念
    r"^(方向|方角|距離|時間)$",
    r"^(内部|外部|中央|周辺)$",
    
    # 一般名詞
    r"^(場所|地域|土地|地面)$",
    r"^(家|店|会社|学校)$"
]

# 人名データベース（基本セット）
PERSON_NAMES = {
    # 植物学者
    "牧野", "富太郎", "松村", "任三",
    
    # 文豪
    "夏目", "漱石", "森", "鴎外", "芥川", "龍之介",
    "太宰", "治", "川端", "康成", "三島", "由紀夫",
    
    # 一般姓名
    "田中", "佐藤", "鈴木", "高橋", "渡辺", "伊藤",
    "山田", "中村", "小林", "加藤", "吉田", "山本"
}

# 学術用語データベース
ACADEMIC_TERMS = {
    # 植物学
    "分類", "系統", "進化", "遺伝", "生態",
    "形態", "生理", "生化学", "分子", "細胞",
    "組織", "器官", "個体", "集団", "群落",
    
    # 一般学術
    "理論", "法則", "原理", "定理", "公式",
    "概念", "仮説", "実験", "観察", "分析"
}

# ファイルパス
FILE_PATHS = {
    "main_db": DEFAULT_DB_PATH,
    "config": CONFIG_DIR / "config.yaml",
    "env": PROJECT_ROOT / ".env",
    "logs": LOGS_DIR / "bungo_map.log"
}

# 環境変数キー
ENV_KEYS = {
    "openai_api_key": "OPENAI_API_KEY",
    "google_maps_key": "GOOGLE_MAPS_API_KEY",
    "db_path": "DATABASE_PATH",
    "log_level": "LOG_LEVEL"
} 