from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.kongming_agent.backend.app.core.config import settings


class Base(DeclarativeBase):
    pass


def _server_url(database: str | None = None) -> str:
    db_name = database or settings.mysql_database
    password = settings.mysql_password or ""
    return (
        f"mysql+pymysql://{settings.mysql_user}:{password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{db_name}"
        f"?charset={settings.mysql_charset}"
    )


def ensure_mysql_database() -> None:
    connection = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset=settings.mysql_charset,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                f"CHARACTER SET {settings.mysql_charset} COLLATE {settings.mysql_charset}_general_ci"
            )
    finally:
        connection.close()


ensure_mysql_database()
engine = create_engine(_server_url(), echo=settings.mysql_echo, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def init_db() -> None:
    from app.kongming_agent.backend.app.models import mysql  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE app_meta "
                "MODIFY COLUMN updated_at DATETIME NOT NULL "
                "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            )
        )
        conn.execute(
            text(
                "INSERT INTO app_meta (meta_key, meta_value, updated_at) "
                "VALUES ('schema_version', '1', CURRENT_TIMESTAMP) "
                "ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value), updated_at = CURRENT_TIMESTAMP"
            )
        )
        conn.execute(
            text(
                "INSERT INTO prompt_templates "
                "(template_code, template_name, template_type, system_prompt, user_prompt, variables_json, version, status, created_at, updated_at) "
                "VALUES "
                "('kongming_default', '孔明默认模板', 'system', '你是诸葛孔明，答复要沉稳、通透、善于概括。', NULL, JSON_OBJECT(), 'v1', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP"
            )
        )


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def inspect_database() -> dict[str, object]:
    inspector = sqlalchemy_inspect(engine)
    return {
        "database": settings.mysql_database,
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "charset": settings.mysql_charset,
        "tables": inspector.get_table_names(),
    }
