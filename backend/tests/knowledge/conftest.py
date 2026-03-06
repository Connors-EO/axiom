from collections.abc import Generator

import psycopg2.extensions
import pytest

from backend.db.migrate import run_migrations
from backend.db.seed import run_seeds
from backend.src.db.client import get_connection


@pytest.fixture()
def seeded_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    run_migrations()
    run_seeds()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SET app.tenant_id = 'everops'")
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
