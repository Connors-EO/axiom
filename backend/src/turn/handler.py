import time
from dataclasses import dataclass
from uuid import UUID

import psycopg2.extensions

from backend.src.turn.bedrock import call_bedrock
from backend.src.turn.context import assemble_context_packet
from backend.src.turn.state import EngagementState, read_engagement_state
from backend.src.turn.trace import create_trace, update_trace_post_call


@dataclass
class TurnResult:
    response_text: str
    intent_classified: str
    scope_check: str
    trace_id: UUID
    turn_number: int


def _write_message(
    engagement_id: UUID,
    tenant_id: str,
    role: str,
    content: str,
    phase: str,
    turn_number: int,
    conn: psycopg2.extensions.connection,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (role, content, phase, engagement_id, tenant_id, turn_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (role, content, phase, str(engagement_id), tenant_id, turn_number),
        )


def process_turn(
    engagement_id: UUID,
    user_message: str,
    session_id: UUID,
    conn: psycopg2.extensions.connection,
) -> TurnResult:
    """Run the full per-turn pipeline and return a TurnResult."""
    t0 = time.monotonic()

    # Step 1: Read engagement state
    state: EngagementState = read_engagement_state(engagement_id, conn)

    # Step 2: Write user message to messages table
    _write_message(
        engagement_id=engagement_id,
        tenant_id=state.tenant_id,
        role="user",
        content=user_message,
        phase=state.current_phase,
        turn_number=state.turn_number,
        conn=conn,
    )

    # Step 3: Create trace row (Point 1 fields)
    trace_id: UUID = create_trace(state, session_id, conn)

    # Step 4: Assemble context packet
    assembled = assemble_context_packet(state, user_message, conn)

    # Step 5: Call Bedrock
    bedrock_response = call_bedrock(assembled.packet, state)

    # Step 6: Write assistant message to messages table
    _write_message(
        engagement_id=engagement_id,
        tenant_id=state.tenant_id,
        role="assistant",
        content=bedrock_response.response_text,
        phase=state.current_phase,
        turn_number=state.turn_number,
        conn=conn,
    )

    total_latency_ms = int((time.monotonic() - t0) * 1000)

    # Step 7: Update trace row (Point 4 fields)
    update_trace_post_call(
        trace_id=trace_id,
        response=bedrock_response,
        context=assembled,
        total_latency_ms=total_latency_ms,
        conn=conn,
    )

    return TurnResult(
        response_text=bedrock_response.response_text,
        intent_classified=bedrock_response.intent_classified,
        scope_check=bedrock_response.scope_check,
        trace_id=trace_id,
        turn_number=state.turn_number,
    )
