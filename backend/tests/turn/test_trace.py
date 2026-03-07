from uuid import UUID, uuid4

import psycopg2.extensions

from backend.src.knowledge.cache import RetrievalEvent
from backend.src.turn.bedrock import BedrockResponse
from backend.src.turn.context import AssembledContext, ContextPacket
from backend.src.turn.state import EngagementState
from backend.src.turn.trace import create_trace, expects_structured_output, update_trace_post_call

ENGAGEMENT_ID = UUID("a0000000-0000-0000-0000-000000000001")


def _make_state(phase: str = "RESEARCH_DISCOVERY") -> EngagementState:
    return EngagementState(
        engagement_id=ENGAGEMENT_ID,
        tenant_id="test",
        model_id="us.anthropic.claude-sonnet-4-6",
        current_phase=phase,
        domain_tags=["cloud-platform"],
        phase_context={},
        flags={},
        turn_number=4,
    )


def _make_bedrock_response(
    intent: str = "scope_question",
    scope: str = "PASS",
    output_tokens: int = 50,
    model_latency_ms: int = 300,
) -> BedrockResponse:
    return BedrockResponse(
        response_text="Here is my response.",
        intent_classified=intent,
        scope_check=scope,
        output_tokens=output_tokens,
        model_latency_ms=model_latency_ms,
        raw_response={},
    )


def _make_assembled_context(
    playbooks_selected: list[str] | None = None,
    playbooks_failed: list[str] | None = None,
    input_tokens_estimate: int = 200,
) -> AssembledContext:
    packet = ContextPacket(
        system_prompt="You are Axiom.",
        playbook_xml="",
        phase_summaries="",
        conversation_history=[],
        current_message="Tell me about cloud.",
    )
    events = [
        RetrievalEvent(
            source_id="cloud-001",
            adapter_type="github",
            result="miss",
            fetch_latency_ms=10,
        )
    ]
    return AssembledContext(
        packet=packet,
        retrieval_events=events,
        playbooks_selected=playbooks_selected or ["cloud-001"],
        playbooks_failed=playbooks_failed or [],
        input_tokens_estimate=input_tokens_estimate,
    )


def test_create_trace_inserts_row_with_point1_fields(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    session_id = uuid4()
    trace_id = create_trace(state, session_id, db_conn)

    assert isinstance(trace_id, UUID)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT engagement_id, tenant_id, session_id, turn_number, phase, "
            "model_id, model_provider, expected_structured_output "
            "FROM traces WHERE id = %s",
            (str(trace_id),),
        )
        row = cur.fetchone()

    assert row is not None
    assert str(row[0]) == str(ENGAGEMENT_ID)
    assert row[1] == "test"
    assert str(row[2]) == str(session_id)
    assert row[3] == 4
    assert row[4] == "RESEARCH_DISCOVERY"
    assert row[5] == "us.anthropic.claude-sonnet-4-6"
    assert row[6] == "bedrock"
    assert row[7] is True  # RESEARCH_DISCOVERY → expected_structured_output=True


def test_expected_structured_output_true_for_research_discovery() -> None:
    assert expects_structured_output("RESEARCH_DISCOVERY") is True


def test_expected_structured_output_true_for_gate_request() -> None:
    assert expects_structured_output("INTAKE", "gate_request") is True


def test_expected_structured_output_true_for_artifact_request() -> None:
    assert expects_structured_output("INTAKE", "artifact_request") is True


def test_expected_structured_output_true_for_lessons_phase() -> None:
    assert expects_structured_output("LESSONS") is True


def test_expected_structured_output_true_for_retro_phase() -> None:
    assert expects_structured_output("RETRO") is True


def test_expected_structured_output_false_for_intake() -> None:
    assert expects_structured_output("INTAKE") is False


def test_update_trace_populates_point4_fields(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    trace_id = create_trace(state, uuid4(), db_conn)

    response = _make_bedrock_response(
        intent="scope_question", scope="PASS", output_tokens=60, model_latency_ms=250
    )
    context = _make_assembled_context(input_tokens_estimate=150)
    update_trace_post_call(trace_id, response, context, total_latency_ms=400, conn=db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT intent_classified, scope_check, input_tokens, output_tokens, "
            "model_latency_ms, total_latency_ms "
            "FROM traces WHERE id = %s",
            (str(trace_id),),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "scope_question"
    assert row[1] == "PASS"
    assert row[2] == 150
    assert row[3] == 60
    assert row[4] == 250
    assert row[5] == 400


def test_estimated_cost_usd_uses_model_pricing(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    trace_id = create_trace(state, uuid4(), db_conn)

    response = _make_bedrock_response(output_tokens=1000)
    context = _make_assembled_context(input_tokens_estimate=1000)
    update_trace_post_call(trace_id, response, context, total_latency_ms=500, conn=db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT estimated_cost_usd FROM traces WHERE id = %s",
            (str(trace_id),),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] is not None
    assert float(row[0]) > 0


def test_retrieval_events_stored_as_jsonb(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    trace_id = create_trace(state, uuid4(), db_conn)

    context = _make_assembled_context()
    update_trace_post_call(trace_id, _make_bedrock_response(), context, total_latency_ms=100, conn=db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT retrieval_events FROM traces WHERE id = %s",
            (str(trace_id),),
        )
        row = cur.fetchone()

    assert row is not None
    stored_events = row[0]
    # Should be a list (parsed from JSONB by psycopg2)
    assert isinstance(stored_events, list)
    assert len(stored_events) == 1
    assert stored_events[0]["source_id"] == "cloud-001"


def test_total_latency_ms_greater_than_model_latency(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    trace_id = create_trace(state, uuid4(), db_conn)

    response = _make_bedrock_response(model_latency_ms=200)
    context = _make_assembled_context()
    update_trace_post_call(trace_id, response, context, total_latency_ms=350, conn=db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT total_latency_ms, model_latency_ms FROM traces WHERE id = %s",
            (str(trace_id),),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] >= row[1]  # total >= model


def test_estimated_cost_zero_when_model_not_in_pricing(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Use a model_id that has no pricing row
    state = EngagementState(
        engagement_id=ENGAGEMENT_ID,
        tenant_id="test",
        model_id="unknown.model-xyz",
        current_phase="RESEARCH_DISCOVERY",
        domain_tags=[],
        phase_context={},
        flags={},
        turn_number=1,
    )
    # Insert a trace with the unknown model_id directly
    trace_id = create_trace(state, uuid4(), db_conn)
    context = _make_assembled_context(input_tokens_estimate=100)
    update_trace_post_call(trace_id, _make_bedrock_response(), context, total_latency_ms=100, conn=db_conn)

    with db_conn.cursor() as cur:
        cur.execute("SELECT estimated_cost_usd FROM traces WHERE id = %s", (str(trace_id),))
        row = cur.fetchone()

    assert row is not None
    assert float(row[0]) == 0.0


def test_playbooks_selected_and_failed_stored(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    trace_id = create_trace(state, uuid4(), db_conn)

    context = _make_assembled_context(
        playbooks_selected=["cloud-001", "cloud-002"],
        playbooks_failed=["cloud-003"],
    )
    update_trace_post_call(trace_id, _make_bedrock_response(), context, total_latency_ms=100, conn=db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT playbooks_selected, playbooks_failed FROM traces WHERE id = %s",
            (str(trace_id),),
        )
        row = cur.fetchone()

    assert row is not None
    assert list(row[0]) == ["cloud-001", "cloud-002"]
    assert list(row[1]) == ["cloud-003"]
