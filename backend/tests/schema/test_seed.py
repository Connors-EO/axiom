import psycopg2.extensions

from backend.db.seed import run_seeds


def _query_as_tenant(
    conn: psycopg2.extensions.connection, sql: str, tenant: str
) -> list[tuple[object, ...]]:
    with conn.cursor() as cur:
        cur.execute(f"SET LOCAL app.tenant_id = '{tenant}'")
        cur.execute(sql)
        return cur.fetchall()  # type: ignore[return-value]


def test_knowledge_sources_row_count(
    seeded_db: psycopg2.extensions.connection,
) -> None:
    rows = _query_as_tenant(
        seeded_db, "SELECT count(*)::int FROM knowledge_sources", "everops"
    )
    seeded_db.rollback()
    assert rows[0][0] == 13


def test_knowledge_sources_domain_tags_non_empty(
    seeded_db: psycopg2.extensions.connection,
) -> None:
    rows = _query_as_tenant(
        seeded_db, "SELECT domain_tags FROM knowledge_sources", "everops"
    )
    seeded_db.rollback()
    assert len(rows) == 13
    for row in rows:
        assert len(row[0]) > 0  # type: ignore[arg-type]


def test_knowledge_sources_phase_relevance_non_empty(
    seeded_db: psycopg2.extensions.connection,
) -> None:
    rows = _query_as_tenant(
        seeded_db, "SELECT phase_relevance FROM knowledge_sources", "everops"
    )
    seeded_db.rollback()
    assert len(rows) == 13
    for row in rows:
        assert len(row[0]) > 0  # type: ignore[arg-type]


def test_knowledge_sources_retrieval_strategy_is_cag(
    seeded_db: psycopg2.extensions.connection,
) -> None:
    rows = _query_as_tenant(
        seeded_db, "SELECT retrieval_strategy FROM knowledge_sources", "everops"
    )
    seeded_db.rollback()
    assert len(rows) == 13
    for row in rows:
        assert row[0] == "cag"


def test_knowledge_sources_retrieval_config_keys(
    seeded_db: psycopg2.extensions.connection,
) -> None:
    rows = _query_as_tenant(
        seeded_db, "SELECT retrieval_config FROM knowledge_sources", "everops"
    )
    seeded_db.rollback()
    assert len(rows) == 13
    required_keys = {"repo_owner", "repo_name", "branch", "path"}
    for row in rows:
        config: dict[str, str] = row[0]  # type: ignore[assignment]
        assert required_keys.issubset(config.keys())


def test_model_pricing_row_count(seeded_db: psycopg2.extensions.connection) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("SELECT count(*)::int FROM model_pricing")
        row = cur.fetchone()
    assert row is not None
    assert row[0] == 2


def test_model_pricing_input_cost_positive(
    seeded_db: psycopg2.extensions.connection,
) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("SELECT input_cost_per_1k FROM model_pricing")
        rows = cur.fetchall()
    assert len(rows) == 2
    for row in rows:
        assert float(row[0]) > 0


def test_seed_idempotency(seeded_db: psycopg2.extensions.connection) -> None:
    run_seeds()
    ks_rows = _query_as_tenant(
        seeded_db, "SELECT count(*)::int FROM knowledge_sources", "everops"
    )
    seeded_db.rollback()
    with seeded_db.cursor() as cur:
        cur.execute("SELECT count(*)::int FROM model_pricing")
        mp_row = cur.fetchone()
    assert ks_rows[0][0] == 13
    assert mp_row is not None
    assert mp_row[0] == 2
