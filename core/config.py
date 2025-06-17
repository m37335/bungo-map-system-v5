#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文豪ゆかり地図システム v4.0 設定管理
システム全体の設定を一元管理
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """データベース設定"""
    db_url: str = "sqlite:///data/db/bungo_v4.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

@dataclass
class CacheConfig:
    """キャッシュ設定"""
    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 3600
    key_prefix: str = "bungo_v4"
    enabled: bool = True

@dataclass
class AozoraConfig:
    """青空文庫スクレイピング設定"""
    base_url: str = "https://www.aozora.gr.jp"
    rate_limit: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    cache_dir: str = "data/aozora_cache"
    cache_expiry_days: int = 7
    user_agent: str = "BungoMapBot/4.0 (Educational Research Purpose)"

@dataclass
class AIConfig:
    """AI機能設定"""
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.3
    enable_llm: bool = False
    enable_nlp: bool = True

@dataclass
class ProcessingConfig:
    """テキスト処理設定"""
    min_sentence_length: int = 5
    max_sentence_length: int = 500
    max_sentences_per_work: int = 1000
    enable_quality_check: bool = True
    quality_threshold: float = 0.7

@dataclass
class GeocodingConfig:
    """ジオコーディング設定"""
    google_api_key: Optional[str] = None
    enable_geocoding: bool = False
    rate_limit: float = 1.0
    max_requests_per_day: int = 2500
    cache_results: bool = True

@dataclass
class LoggingConfig:
    """ログ設定"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/bungo_v4.log"
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

class Config:
    """メイン設定クラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        """初期化"""
        self.config_file = config_file or os.getenv('BUNGO_CONFIG', 'config.json')
        
        # デフォルト設定
        self.database = DatabaseConfig()
        self.cache = CacheConfig()
        self.aozora = AozoraConfig()
        self.ai = AIConfig()
        self.processing = ProcessingConfig()
        self.geocoding = GeocodingConfig()
        self.logging = LoggingConfig()
        
        # 環境変数から設定を読み込み
        self._load_from_env()
        
        # 設定ファイルから読み込み（存在する場合）
        self._load_from_file()
        
        # ディレクトリの作成
        self._ensure_directories()
        
        logger.info("🔧 設定読み込み完了")
    
    def _load_from_env(self):
        """環境変数から設定を読み込み"""
        # データベース設定
        if os.getenv('DATABASE_URL'):
            self.database.db_url = os.getenv('DATABASE_URL')
        
        # キャッシュ設定
        if os.getenv('REDIS_URL'):
            self.cache.redis_url = os.getenv('REDIS_URL')
        
        # AI設定
        if os.getenv('OPENAI_API_KEY'):
            self.ai.openai_api_key = os.getenv('OPENAI_API_KEY')
            self.ai.enable_llm = True
        
        if os.getenv('CLAUDE_API_KEY'):
            self.ai.claude_api_key = os.getenv('CLAUDE_API_KEY')
            self.ai.enable_llm = True
        
        # ジオコーディング設定
        if os.getenv('GOOGLE_API_KEY'):
            self.geocoding.google_api_key = os.getenv('GOOGLE_API_KEY')
            self.geocoding.enable_geocoding = True
        
        # ログレベル
        if os.getenv('LOG_LEVEL'):
            self.logging.level = os.getenv('LOG_LEVEL')
    
    def _load_from_file(self):
        """設定ファイルから読み込み"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 各設定セクションを更新
                if 'database' in config_data:
                    self._update_dataclass(self.database, config_data['database'])
                
                if 'cache' in config_data:
                    self._update_dataclass(self.cache, config_data['cache'])
                
                if 'aozora' in config_data:
                    self._update_dataclass(self.aozora, config_data['aozora'])
                
                if 'ai' in config_data:
                    self._update_dataclass(self.ai, config_data['ai'])
                
                if 'processing' in config_data:
                    self._update_dataclass(self.processing, config_data['processing'])
                
                if 'geocoding' in config_data:
                    self._update_dataclass(self.geocoding, config_data['geocoding'])
                
                if 'logging' in config_data:
                    self._update_dataclass(self.logging, config_data['logging'])
                
                logger.info(f"✅ 設定ファイル読み込み完了: {self.config_file}")
                
            except Exception as e:
                logger.warning(f"⚠️ 設定ファイル読み込み失敗: {e}")
    
    def _update_dataclass(self, dataclass_obj, config_dict):
        """データクラスの値を辞書で更新"""
        for key, value in config_dict.items():
            if hasattr(dataclass_obj, key):
                setattr(dataclass_obj, key, value)
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        directories = [
            os.path.dirname(self.database.db_url.replace('sqlite:///', '')),
            self.aozora.cache_dir,
            os.path.dirname(self.logging.file_path),
            'data/export',
            'data/cache'
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    def save_to_file(self, file_path: Optional[str] = None):
        """設定をファイルに保存"""
        file_path = file_path or self.config_file
        
        config_data = {
            'database': self._dataclass_to_dict(self.database),
            'cache': self._dataclass_to_dict(self.cache),
            'aozora': self._dataclass_to_dict(self.aozora),
            'ai': self._dataclass_to_dict(self.ai),
            'processing': self._dataclass_to_dict(self.processing),
            'geocoding': self._dataclass_to_dict(self.geocoding),
            'logging': self._dataclass_to_dict(self.logging)
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 設定ファイル保存完了: {file_path}")
            
        except Exception as e:
            logger.error(f"❌ 設定ファイル保存失敗: {e}")
    
    def _dataclass_to_dict(self, dataclass_obj) -> Dict[str, Any]:
        """データクラスを辞書に変換"""
        return {
            field: getattr(dataclass_obj, field)
            for field in dataclass_obj.__dataclass_fields__
        }
    
    def get_database_url(self) -> str:
        """データベースURL取得"""
        return self.database.db_url
    
    def get_cache_config(self) -> Dict[str, Any]:
        """キャッシュ設定取得"""
        return self._dataclass_to_dict(self.cache)
    
    def get_aozora_config(self) -> Dict[str, Any]:
        """青空文庫設定取得"""
        return self._dataclass_to_dict(self.aozora)
    
    def get_ai_config(self) -> Dict[str, Any]:
        """AI設定取得"""
        return self._dataclass_to_dict(self.ai)
    
    def get_processing_config(self) -> Dict[str, Any]:
        """処理設定取得"""
        return self._dataclass_to_dict(self.processing)
    
    def is_ai_enabled(self) -> bool:
        """AI機能が有効かチェック"""
        return (
            self.ai.enable_llm and 
            (self.ai.openai_api_key or self.ai.claude_api_key)
        )
    
    def is_geocoding_enabled(self) -> bool:
        """ジオコーディングが有効かチェック"""
        return (
            self.geocoding.enable_geocoding and 
            self.geocoding.google_api_key
        )
    
    def setup_logging(self):
        """ログ設定のセットアップ"""
        # ログディレクトリの作成
        log_dir = os.path.dirname(self.logging.file_path)
        os.makedirs(log_dir, exist_ok=True)
        
        # ログレベルの設定
        level = getattr(logging, self.logging.level.upper(), logging.INFO)
        
        # ログフォーマッターの設定
        formatter = logging.Formatter(self.logging.format)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # 既存のハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラー
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.logging.file_path,
                maxBytes=self.logging.max_size,
                backupCount=self.logging.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"⚠️ ファイルログハンドラー設定失敗: {e}")
    
    def validate(self) -> Dict[str, Any]:
        """設定の妥当性チェック"""
        issues = {
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        # データベース設定チェック
        if not self.database.db_url:
            issues['errors'].append("データベースURLが設定されていません")
        
        # AI設定チェック
        if self.ai.enable_llm and not (self.ai.openai_api_key or self.ai.claude_api_key):
            issues['warnings'].append("AI機能が有効ですがAPIキーが設定されていません")
        
        # ジオコーディング設定チェック
        if self.geocoding.enable_geocoding and not self.geocoding.google_api_key:
            issues['warnings'].append("ジオコーディングが有効ですがAPIキーが設定されていません")
        
        # パフォーマンス推奨事項
        if self.processing.max_sentences_per_work > 2000:
            issues['recommendations'].append("大量のセンテンス処理はパフォーマンスに影響する可能性があります")
        
        return issues

# グローバル設定インスタンス
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """グローバル設定インスタンスを取得"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def init_config(config_file: Optional[str] = None) -> Config:
    """設定を初期化"""
    global _config_instance
    _config_instance = Config(config_file)
    _config_instance.setup_logging()
    return _config_instance

# 便利関数
def get_database_url() -> str:
    """データベースURL取得"""
    return get_config().get_database_url()

def is_ai_enabled() -> bool:
    """AI機能有効チェック"""
    return get_config().is_ai_enabled()

def is_geocoding_enabled() -> bool:
    """ジオコーディング有効チェック"""
    return get_config().is_geocoding_enabled()
