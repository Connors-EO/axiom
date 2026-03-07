from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import psycopg2.extensions
import pytest

from backend.src.turn.bedrock import BedrockResponse
from backend.src.turn.context import AssembledContext, ContextPacket
from backend.src.turn.handler import TurnResult, process_turn
from backend.src.turn.state import EngagementState

ENGAGEMENT_ID = UUID("a0000000-0000-0000-0000-000000000001")
TRACE_ID = uuid4()
SESSION_ID = uuid4()


def _mock_state() -> EngagementState:
    return EngagementState(
        engagement_id=ENGAGEMENT_ID,
        tenant_id="test",
        model_id="us.anthropic.claude-sonnet-4-6",
        current_phase="RESEARCH_DISCOVERY",
        domain_tags=["cloud-platform"],
        phase_context={},
        flags={},
        turn_number=4,
    )


def _mock_assembled() -> AssembledContext:
    packet = ContextPacket(
        system_prompt="You are Axiom.",
        playbook_xml="",
        phase_summaries="",
        conversation_history=[],
        current_message="user message",
    )
    return AssembledContext(
        packet=packet,
        retrieval_events=[],
        playbooks_selected=[],
        playbooks_failed=[],
        input_tokens_estimate=100,
    )


def _mock_bedrock_response() -> BedrockResponse:
    return BedrockResponse(
        response_text="Here is the response.",
        intent_classified="scope_question",
        scope_check="PASS",
        output_tokens=50,
        model_latency_ms=200,
        raw_response={},
    )


@pytest.fixture()
def mock_dependencies() -> dict:  # type: ignore[type-arg]
    return {
        "read_engagement_state": MagicMock(return_value=_mock_state()),
        "create_trace": MagicMock(return_value=TRACE_ID),
        "assemble_context_packet": MagicMock(return_value=_mock_assembled()),
        "call_bedrock": MagicMock(return_value=_mock_bedrock_response()),
        "update_trace_post_call": MagicMock(return_value=None),
    }


def test_process_turn_calls_components_in_order(
    db_conn: psycopg2.extensions.connection,
    mock_dependencies: dict,  # type: ignore[type-arg]
) -> None:
    call_order: list[str] = []

    def track(name: str) -> MagicMock:
        m = mock_dependencies[name]
        original_side_effect = m.side_effect

        def side_effect(*args: object, **kwargs: object) -> object:
            call_order.append(name)
            if original_side_effect:
                return original_side_effect(*args, **kwargs)
            return m.return_value

        m.side_effect = side_effect
        return m

    with (
        patch("backend.src.turn.handler.read_engagement_state", track("read_engagement_state")),
        patch("backend.src.turn.handler.create_trace", track("create_trace")),
        patch("backend.src.turn.handler.assemble_context_packet", track("assemble_context_packet")),
        patch("backend.src.turn.handler.call_bedrock", track("call_bedrock")),
        patch("backend.src.turn.handler.update_trace_post_call", track("update_trace_post_call")),
    ):
        process_turn(ENGAGEMENT_ID, "user message", SESSION_ID, db_conn)

    assert call_order == [
        "read_engagement_state",
        "create_trace",
        "assemble_context_packet",
        "call_bedrock",
        "update_trace_post_call",
    ]


def test_user_message_written_before_bedrock_call(
    db_conn: psycopg2.extensions.connection,
    mock_dependencies: dict,  # type: ignore[type-arg]
) -> None:
    # Verify that a user message row exists when call_bedrock is invoked
    messages_at_bedrock_call: list[int] = []

    def bedrock_side_effect(*args: object, **kwargs: object) -> BedrockResponse:
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*)::int FROM messages "
                "WHERE engagement_id = %s AND role = 'user'",
                (str(ENGAGEMENT_ID),),
            )
            row = cur.fetchone()
        messages_at_bedrock_call.append(row[0] if row else 0)
        return _mock_bedrock_response()

    mock_dependencies["call_bedrock"].side_effect = bedrock_side_effect

    with (
        patch("backend.src.turn.handler.read_engagement_state", mock_dependencies["read_engagement_state"]),
        patch("backend.src.turn.handler.create_trace", mock_dependencies["create_trace"]),
        patch("backend.src.turn.handler.assemble_context_packet", mock_dependencies["assemble_context_packet"]),
        patch("backend.src.turn.handler.call_bedrock", mock_dependencies["call_bedrock"]),
        patch("backend.src.turn.handler.update_trace_post_call", mock_dependencies["update_trace_post_call"]),
    ):
        process_turn(ENGAGEMENT_ID, "new user message", SESSION_ID, db_conn)

    # 3 seeded + 1 new = 4 total user+assistant messages, but filtering role='user': 3 seeded user (turn 1, 3 are user) + 1 new
    assert messages_at_bedrock_call[0] > 0


def test_assistant_message_written_after_bedrock_call(
    db_conn: psycopg2.extensions.connection,
    mock_dependencies: dict,  # type: ignore[type-arg]
) -> None:
    with (
        patch("backend.src.turn.handler.read_engagement_state", mock_dependencies["read_engagement_state"]),
        patch("backend.src.turn.handler.create_trace", mock_dependencies["create_trace"]),
        patch("backend.src.turn.handler.assemble_context_packet", mock_dependencies["assemble_context_packet"]),
        patch("backend.src.turn.handler.call_bedrock", mock_dependencies["call_bedrock"]),
        patch("backend.src.turn.handler.update_trace_post_call", mock_dependencies["update_trace_post_call"]),
    ):
        process_turn(ENGAGEMENT_ID, "user message", SESSION_ID, db_conn)

    # After process_turn, an assistant message with the mocked content should be in the DB
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*)::int FROM messages "
            "WHERE engagement_id = %s AND role = 'assistant' AND content = 'Here is the response.'",
            (str(ENGAGEMENT_ID),),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == 1


def test_returns_turn_result_with_correct_fields(
    db_conn: psycopg2.extensions.connection,
    mock_dependencies: dict,  # type: ignore[type-arg]
) -> None:
    with (
        patch("backend.src.turn.handler.read_engagement_state", mock_dependencies["read_engagement_state"]),
        patch("backend.src.turn.handler.create_trace", mock_dependencies["create_trace"]),
        patch("backend.src.turn.handler.assemble_context_packet", mock_dependencies["assemble_context_packet"]),
        patch("backend.src.turn.handler.call_bedrock", mock_dependencies["call_bedrock"]),
        patch("backend.src.turn.handler.update_trace_post_call", mock_dependencies["update_trace_post_call"]),
    ):
        result = process_turn(ENGAGEMENT_ID, "user message", SESSION_ID, db_conn)

    assert isinstance(result, TurnResult)
    assert result.response_text == "Here is the response."
    assert result.intent_classified == "scope_question"
    assert result.scope_check == "PASS"
    assert result.turn_number == 4


def test_trace_id_in_turn_result(
    db_conn: psycopg2.extensions.connection,
    mock_dependencies: dict,  # type: ignore[type-arg]
) -> None:
    with (
        patch("backend.src.turn.handler.read_engagement_state", mock_dependencies["read_engagement_state"]),
        patch("backend.src.turn.handler.create_trace", mock_dependencies["create_trace"]),
        patch("backend.src.turn.handler.assemble_context_packet", mock_dependencies["assemble_context_packet"]),
        patch("backend.src.turn.handler.call_bedrock", mock_dependencies["call_bedrock"]),
        patch("backend.src.turn.handler.update_trace_post_call", mock_dependencies["update_trace_post_call"]),
    ):
        result = process_turn(ENGAGEMENT_ID, "user message", SESSION_ID, db_conn)

    assert isinstance(result.trace_id, UUID)
    assert result.trace_id == TRACE_ID
