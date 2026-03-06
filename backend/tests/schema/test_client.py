import os

import psycopg2
import pytest

from backend.src.db.client import get_connection


def test_get_connection_returns_connection() -> None:
    conn = get_connection()
    try:
        assert conn is not None
        assert not conn.closed
    finally:
        conn.close()


def test_default_port_is_5433() -> None:
    original = os.environ.pop("PGPORT", None)
    try:
        conn = get_connection()
        # psycopg2 exposes connection info via dsn or get_dsn_parameters
        params = conn.get_dsn_parameters()
        assert params["port"] == "5433"
        conn.close()
    finally:
        if original is not None:
            os.environ["PGPORT"] = original


def test_can_execute_select_1() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
        assert row == (1,)
    finally:
        conn.close()
