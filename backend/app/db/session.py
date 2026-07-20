from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_engine() -> Engine:
    return _get_engine(get_settings().database_url)


@lru_cache
def _get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def clear_engine_cache() -> None:
    _get_engine.cache_clear()
