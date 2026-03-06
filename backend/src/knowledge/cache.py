from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import psycopg2.extensions

import backend.src.adapters.github as _github_module
from backend.src.adapters.github import AdapterResult


@dataclass
class RetrievalEvent:
    source_id: str
    adapter_type: str
    result: Literal["hit", "miss", "stale"]
    fetch_latency_ms: int


def resolve(
    source: dict[str, Any],
    conn: psycopg2.extensions.connection,
    adapter_fn: Callable[[dict[str, Any]], AdapterResult] | None = None,
) -> tuple[str, RetrievalEvent]:
    """Return (processed_text, RetrievalEvent) for the given knowledge source.

    Checks the knowledge_cache for a fresh (non-stale, non-expired) row first.
    On HIT the adapter is not called.  On MISS or STALE the adapter is called
    and the cache row is inserted or updated respectively.
    """
    if adapter_fn is None:
        adapter_fn = _github_module.fetch

    source_id: str = source["id"]

    # --- HIT: a fresh, non-expired row exists ---
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT processed_text
            FROM knowledge_cache
            WHERE source_id = %s
              AND is_stale = false
              AND expires_at > NOW()
            LIMIT 1
            """,
            (source_id,),
        )
        hit_row = cur.fetchone()

    if hit_row is not None:
        return str(hit_row[0]), RetrievalEvent(
            source_id=source_id,
            adapter_type="github",
            result="hit",
            fetch_latency_ms=0,
        )

    # --- Check whether any row exists (STALE vs MISS) ---
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM knowledge_cache WHERE source_id = %s LIMIT 1",
            (source_id,),
        )
        existing = cur.fetchone()

    # Fetch fresh content from GitHub
    adapter_result = adapter_fn(source)

    if existing is None:
        # MISS: insert a new cache row
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_cache
                    (source_id, processed_text, is_stale, expires_at,
                     content_hash, tenant_id)
                VALUES (
                    %s, %s, false,
                    NOW() + interval '24 hours',
                    %s,
                    current_setting('app.tenant_id')
                )
                """,
                (source_id, adapter_result.text, adapter_result.content_hash),
            )
        event_result: Literal["miss", "stale"] = "miss"
    else:
        # STALE: update the existing cache row
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE knowledge_cache
                SET processed_text = %s,
                    is_stale = false,
                    expires_at = NOW() + interval '24 hours',
                    content_hash = %s,
                    updated_at = NOW()
                WHERE source_id = %s
                """,
                (adapter_result.text, adapter_result.content_hash, source_id),
            )
        event_result = "stale"

    return adapter_result.text, RetrievalEvent(
        source_id=source_id,
        adapter_type="github",
        result=event_result,
        fetch_latency_ms=adapter_result.fetch_latency_ms,
    )
