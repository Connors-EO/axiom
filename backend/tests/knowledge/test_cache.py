import hashlib
from typing import Any

import psycopg2.extensions
import pytest

import backend.src.adapters.github as _github_module
from backend.src.adapters.github import AdapterResult
from backend.src.knowledge.cache import RetrievalEvent, resolve

IAC_001_SOURCE = {
    "id": "IAC-001",
    "retrieval_config": {
        "repo_owner": "Connors-EO",
        "repo_name": "solution-accelerator",
        "branch": "main",
        "path": "playbooks/existing/iac-terraform-multi-account.md",
    },
}

MOCK_TEXT = "# IaC Terraform Multi-Account Playbook"
MOCK_HASH = hashlib.sha256(MOCK_TEXT.encode()).hexdigest()


class _CountingAdapter:
    def __init__(self, text: str = MOCK_TEXT) -> None:
        self._text = text
        self.call_count = 0

    def __call__(self, source: dict[str, Any]) -> AdapterResult:
        self.call_count += 1
        return AdapterResult(
            text=self._text,
            content_hash=hashlib.sha256(self._text.encode()).hexdigest(),
            fetch_latency_ms=5,
        )


def test_cache_miss_result(seeded_conn: psycopg2.extensions.connection) -> None:
    adapter = _CountingAdapter()
    text, event = resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)
    assert text == MOCK_TEXT
    assert isinstance(event, RetrievalEvent)
    assert event.result == "miss"
    assert adapter.call_count == 1


def test_cache_miss_inserts_row(seeded_conn: psycopg2.extensions.connection) -> None:
    adapter = _CountingAdapter()
    resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)
    with seeded_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*)::int FROM knowledge_cache WHERE source_id = 'IAC-001'"
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == 1


def test_cache_hit_skips_adapter(seeded_conn: psycopg2.extensions.connection) -> None:
    adapter = _CountingAdapter()
    resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)  # MISS — populate cache
    text, event = resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)  # HIT
    assert event.result == "hit"
    assert adapter.call_count == 1  # adapter called only once total
    assert text == MOCK_TEXT


def test_cache_stale_flag_calls_adapter(
    seeded_conn: psycopg2.extensions.connection,
) -> None:
    with seeded_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_cache
                (source_id, processed_text, is_stale, expires_at,
                 content_hash, tenant_id)
            VALUES ('IAC-001', 'old content', true,
                    NOW() + interval '24 hours',
                    'oldhash', 'everops')
            """
        )
    adapter = _CountingAdapter()
    text, event = resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)
    assert event.result == "stale"
    assert text == MOCK_TEXT
    assert adapter.call_count == 1


def test_cache_expired_row_calls_adapter(
    seeded_conn: psycopg2.extensions.connection,
) -> None:
    with seeded_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_cache
                (source_id, processed_text, is_stale, expires_at,
                 content_hash, tenant_id)
            VALUES ('IAC-001', 'old content', false,
                    NOW() - interval '1 hour',
                    'oldhash', 'everops')
            """
        )
    adapter = _CountingAdapter()
    text, event = resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)
    assert event.result == "stale"
    assert text == MOCK_TEXT
    assert adapter.call_count == 1


def test_cache_stores_content_hash(seeded_conn: psycopg2.extensions.connection) -> None:
    adapter = _CountingAdapter()
    resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)
    with seeded_conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash FROM knowledge_cache WHERE source_id = 'IAC-001'"
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == MOCK_HASH


def test_cache_sets_expires_at_24h(seeded_conn: psycopg2.extensions.connection) -> None:
    adapter = _CountingAdapter()
    resolve(IAC_001_SOURCE, seeded_conn, adapter_fn=adapter)
    with seeded_conn.cursor() as cur:
        cur.execute(
            """
            SELECT expires_at > NOW() + interval '23 hours'
               AND expires_at < NOW() + interval '25 hours'
            FROM knowledge_cache WHERE source_id = 'IAC-001'
            """
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] is True


def test_resolve_defaults_to_github_adapter(
    seeded_conn: psycopg2.extensions.connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patched_result = AdapterResult(
        text="patched text",
        content_hash=hashlib.sha256("patched text".encode()).hexdigest(),
        fetch_latency_ms=5,
    )
    monkeypatch.setattr(_github_module, "fetch", lambda source: patched_result)
    text, event = resolve(IAC_001_SOURCE, seeded_conn)
    assert event.result == "miss"
    assert text == "patched text"
