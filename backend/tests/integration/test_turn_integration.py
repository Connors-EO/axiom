import os
import pathlib
from uuid import UUID, uuid4

import psycopg2.extensions
import pytest

from backend.db.migrate import run_migrations
from backend.db.seed import run_seeds
from backend.src.db.client import get_connection
from backend.src.turn.handler import process_turn

_FIXTURE_SQL = pathlib.Path(__file__).parent.parent / "fixtures" / "engagement.sql"
_FIXTURE_ENGAGEMENT_ID = UUID("a0000000-0000-0000-0000-000000000001")
_VALID_INTENTS = frozenset(
    {
        "scope_question",
        "gate_request",
        "phase_advance",
        "clarification",
        "artifact_request",
        "lesson_capture",
        "off_topic",
    }
)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests",
)
def test_process_turn_end_to_end() -> None:
    run_migrations()
    run_seeds()

    conn: psycopg2.extensions.connection = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET app.tenant_id = 'test'")
            cur.execute(_FIXTURE_SQL.read_text())

        session_id = uuid4()
        result = process_turn(
            engagement_id=_FIXTURE_ENGAGEMENT_ID,
            user_message="We need to understand the current cloud architecture before we design anything.",
            session_id=session_id,
            conn=conn,
        )

        # Assertions on TurnResult
        assert isinstance(result.response_text, str)
        assert len(result.response_text) > 20
        assert result.intent_classified in _VALID_INTENTS
        assert result.scope_check in ("PASS", "WARN", "FAIL")
        assert isinstance(result.trace_id, UUID)

        # Trace row should have all Point 4 fields populated
        with conn.cursor() as cur:
            cur.execute(
                "SELECT output_tokens, estimated_cost_usd, intent_classified, scope_check "
                "FROM traces WHERE id = %s",
                (str(result.trace_id),),
            )
            trace_row = cur.fetchone()

        assert trace_row is not None
        assert trace_row[0] > 0                     # output_tokens
        assert float(trace_row[1]) > 0              # estimated_cost_usd
        assert trace_row[2] in _VALID_INTENTS       # intent_classified
        assert trace_row[3] in ("PASS", "WARN", "FAIL")  # scope_check

        # Messages table: 3 seeded + 1 user + 1 assistant = 5 total
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*)::int FROM messages WHERE engagement_id = %s",
                (str(_FIXTURE_ENGAGEMENT_ID),),
            )
            count_row = cur.fetchone()

        assert count_row is not None
        assert count_row[0] == 5

    finally:
        conn.rollback()
        conn.close()
