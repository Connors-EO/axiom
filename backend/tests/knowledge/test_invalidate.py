import psycopg2.extensions

from backend.src.knowledge.invalidate import invalidate_paths

# Paths from seed data (001_knowledge_sources.sql)
IAC_001_PATH = "playbooks/existing/iac-terraform-multi-account.md"
IAC_002_PATH = "playbooks/existing/iac-atmos-foundations.md"
K8S_001_PATH = "playbooks/existing/k8s-cluster-deployment-hardening.md"


def _insert_cache_row(conn: psycopg2.extensions.connection, source_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_cache
                (source_id, processed_text, is_stale, expires_at,
                 content_hash, tenant_id)
            VALUES (%s, 'content', false, NOW() + interval '24 hours',
                    'hash', 'everops')
            """,
            (source_id,),
        )


def _is_stale(conn: psycopg2.extensions.connection, source_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT is_stale FROM knowledge_cache WHERE source_id = %s",
            (source_id,),
        )
        row = cur.fetchone()
    assert row is not None
    return bool(row[0])


def test_invalidate_single_path(seeded_conn: psycopg2.extensions.connection) -> None:
    _insert_cache_row(seeded_conn, "IAC-001")
    count = invalidate_paths([IAC_001_PATH], seeded_conn)
    assert count == 1
    assert _is_stale(seeded_conn, "IAC-001") is True


def test_invalidate_multiple_paths(seeded_conn: psycopg2.extensions.connection) -> None:
    _insert_cache_row(seeded_conn, "IAC-001")
    _insert_cache_row(seeded_conn, "IAC-002")
    count = invalidate_paths([IAC_001_PATH, IAC_002_PATH], seeded_conn)
    assert count == 2
    assert _is_stale(seeded_conn, "IAC-001") is True
    assert _is_stale(seeded_conn, "IAC-002") is True


def test_invalidate_no_cached_rows(seeded_conn: psycopg2.extensions.connection) -> None:
    # Source exists in knowledge_sources but has no cache row
    count = invalidate_paths([K8S_001_PATH], seeded_conn)
    assert count == 0


def test_invalidate_unknown_path(seeded_conn: psycopg2.extensions.connection) -> None:
    count = invalidate_paths(["nonexistent/path.md"], seeded_conn)
    assert count == 0


def test_invalidate_empty_list(seeded_conn: psycopg2.extensions.connection) -> None:
    count = invalidate_paths([], seeded_conn)
    assert count == 0


def test_invalidate_already_stale_row(
    seeded_conn: psycopg2.extensions.connection,
) -> None:
    with seeded_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_cache
                (source_id, processed_text, is_stale, expires_at,
                 content_hash, tenant_id)
            VALUES ('IAC-001', 'content', true, NOW() + interval '24 hours',
                    'hash', 'everops')
            """
        )
    count = invalidate_paths([IAC_001_PATH], seeded_conn)
    assert count == 1
