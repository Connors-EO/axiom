from collections.abc import Generator

import psycopg2.extensions
import pytest

from backend.db.migrate import run_migrations
from backend.db.seed import run_seeds
from backend.src.db.client import get_connection


@pytest.fixture()
def db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def migrated_db() -> Generator[psycopg2.extensions.connection, None, None]:
    run_migrations()
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def seeded_db() -> Generator[psycopg2.extensions.connection, None, None]:
    run_migrations()
    run_seeds()
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
