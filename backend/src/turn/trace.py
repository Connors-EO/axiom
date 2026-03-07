import json
import uuid
from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

import psycopg2.extensions

from backend.src.turn.bedrock import BedrockResponse
from backend.src.turn.context import AssembledContext
from backend.src.turn.state import EngagementState


def expects_structured_output(phase: str, intent: str | None = None) -> bool:
    """Return True if this turn is expected to produce structured output."""
    if intent == "gate_request":
        return True
    if intent == "artifact_request":
        return True
    if phase in ("LESSONS", "RETRO"):
        return True
    if phase == "RESEARCH_DISCOVERY":
        return True
    return False


def create_trace(
    state: EngagementState,
    session_id: UUID,
    conn: psycopg2.extensions.connection,
) -> UUID:
    """Insert a trace row with Point 1 fields. Returns the new trace UUID."""
    trace_id = uuid.uuid4()
    structured = expects_structured_output(state.current_phase)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO traces (
                id, engagement_id, tenant_id, session_id,
                turn_number, phase, model_id, model_provider,
                expected_structured_output, created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, NOW()
            )
            """,
            (
                str(trace_id),
                str(state.engagement_id),
                state.tenant_id,
                str(session_id),
                state.turn_number,
                state.current_phase,
                state.model_id,
                "bedrock",
                structured,
            ),
        )

    return trace_id


def _fetch_cost_rates(
    model_id: str,
    conn: psycopg2.extensions.connection,
) -> tuple[Decimal, Decimal]:
    """Return (input_cost_per_1k, output_cost_per_1k) for the given model."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT input_cost_per_1k, output_cost_per_1k "
            "FROM model_pricing WHERE model_id = %s",
            (model_id,),
        )
        row = cur.fetchone()
    if row is None:
        return Decimal(0), Decimal(0)
    return Decimal(row[0]), Decimal(row[1])


def update_trace_post_call(
    trace_id: UUID,
    response: BedrockResponse,
    context: AssembledContext,
    total_latency_ms: int,
    conn: psycopg2.extensions.connection,
) -> None:
    """Update trace row with Point 4 fields after the Bedrock call."""
    # Fetch model pricing — model_id is on the engagement, not the trace.
    # We need to re-read model_id from the trace row to avoid an extra parameter.
    with conn.cursor() as cur:
        cur.execute("SELECT model_id, tenant_id FROM traces WHERE id = %s", (str(trace_id),))
        trace_row = cur.fetchone()

    model_id = str(trace_row[0]) if trace_row is not None else ""
    input_rate, output_rate = _fetch_cost_rates(model_id, conn)

    input_tokens = context.input_tokens_estimate
    output_tokens = response.output_tokens
    estimated_cost = (Decimal(input_tokens) * input_rate / 1000) + (
        Decimal(output_tokens) * output_rate / 1000
    )

    retrieval_events_json = json.dumps(
        [asdict(e) for e in context.retrieval_events]
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE traces SET
                intent_classified      = %s,
                scope_check            = %s,
                input_tokens           = %s,
                output_tokens          = %s,
                model_latency_ms       = %s,
                total_latency_ms       = %s,
                latency_ms             = %s,
                structured_output_compliance = %s,
                uncertainty_flag_count = %s,
                estimated_cost_usd     = %s,
                playbooks_selected     = %s,
                playbooks_failed       = %s,
                retrieval_events       = %s::jsonb
            WHERE id = %s
            """,
            (
                response.intent_classified,
                response.scope_check,
                input_tokens,
                output_tokens,
                response.model_latency_ms,
                total_latency_ms,
                total_latency_ms,
                True,
                0,
                estimated_cost,
                context.playbooks_selected,
                context.playbooks_failed,
                retrieval_events_json,
                str(trace_id),
            ),
        )
