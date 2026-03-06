import psycopg2
import psycopg2.extensions
import psycopg2.errors
import pytest

ALL_TABLES = [
    "engagements",
    "messages",
    "traces",
    "quality_snapshots",
    "gate_decisions",
    "phase_transitions",
    "knowledge_sources",
    "knowledge_cache",
    "artifacts",
    "lessons",
    "model_pricing",
    "finetuning_runs",
]


@pytest.mark.parametrize("table_name", ALL_TABLES)
def test_table_exists(migrated_db: psycopg2.extensions.connection, table_name: str) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
            """,
            (table_name,),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] is True


@pytest.mark.parametrize("table_name", ALL_TABLES)
def test_rls_enabled(migrated_db: psycopg2.extensions.connection, table_name: str) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT relrowsecurity FROM pg_class
            WHERE relname = %s AND relnamespace = 'public'::regnamespace
            """,
            (table_name,),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] is True


def test_traces_expected_structured_output_column(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT data_type, is_nullable FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'traces'
              AND column_name = 'expected_structured_output'
            """,
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "boolean"
    assert row[1] == "NO"


def test_model_pricing_thinking_per_1k_nullable(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT is_nullable FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'model_pricing'
              AND column_name = 'thinking_per_1k'
            """,
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "YES"


def test_finetuning_runs_training_turn_ids(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'finetuning_runs'
                  AND column_name = 'training_turn_ids'
            )
            """,
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] is True


def test_finetuning_runs_holdout_turn_ids(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'finetuning_runs'
                  AND column_name = 'holdout_turn_ids'
            )
            """,
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] is True


def test_not_null_rejects_null_tenant_id(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    # With FORCE RLS on a non-superuser, NULL tenant_id hits the RLS
    # InsufficientPrivilege check before the NOT NULL constraint. Both
    # errors confirm that a NULL tenant_id cannot be stored.
    with pytest.raises(
        (psycopg2.errors.NotNullViolation, psycopg2.errors.InsufficientPrivilege)
    ):
        with migrated_db.cursor() as cur:
            cur.execute(
                "INSERT INTO engagements (id, tenant_id, current_phase) "
                "VALUES (gen_random_uuid(), NULL, 'P0')"
            )
    migrated_db.rollback()


def test_rls_cross_tenant_isolation(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    try:
        with migrated_db.cursor() as cur:
            cur.execute("SET LOCAL app.tenant_id = 'test_rls_tenant_a'")
            cur.execute(
                "INSERT INTO engagements (id, tenant_id, current_phase) "
                "VALUES (gen_random_uuid(), 'test_rls_tenant_a', 'P0')"
            )
        with migrated_db.cursor() as cur:
            cur.execute("SET LOCAL app.tenant_id = 'test_rls_tenant_b'")
            cur.execute(
                "SELECT count(*)::int FROM engagements "
                "WHERE tenant_id = 'test_rls_tenant_a'"
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == 0
    finally:
        migrated_db.rollback()


def test_fk_rejects_nonexistent_engagement_id(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    # Set tenant context so RLS allows the INSERT attempt;
    # the FK constraint fires because the engagement_id does not exist.
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        with migrated_db.cursor() as cur:
            cur.execute("SET LOCAL app.tenant_id = 'tenant_a'")
            cur.execute(
                """
                INSERT INTO messages
                    (id, engagement_id, tenant_id, role, content, phase, turn_number)
                VALUES
                    (gen_random_uuid(),
                     '00000000-0000-0000-0000-000000000000',
                     'tenant_a', 'user', 'hello', 'P0', 1)
                """
            )
    migrated_db.rollback()


def test_schema_migrations_table_exists(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'schema_migrations'
            )
            """,
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] is True


def test_schema_migrations_has_applied_entry(
    migrated_db: psycopg2.extensions.connection,
) -> None:
    with migrated_db.cursor() as cur:
        cur.execute(
            "SELECT filename FROM schema_migrations ORDER BY applied_at"
        )
        rows = cur.fetchall()
    assert len(rows) > 0
    assert "001_initial_schema" in rows[0][0]
