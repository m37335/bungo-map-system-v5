from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os
from typing import Optional

# データベース接続設定
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/bungo_map.db"
)

# エンジン設定
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        echo=False
    )
else:
    # SQLite用設定
    engine = create_engine(
        DATABASE_URL,
        echo=False
    )

# セッションファクトリ
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ベースクラス
Base = declarative_base()

def get_db() -> Optional[SessionLocal]:
    """データベースセッションを取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """データベースの初期化"""
    from database.models import Base as ModelsBase
    ModelsBase.metadata.create_all(bind=engine) 