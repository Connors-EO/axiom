from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import psycopg2.extensions

from backend.src.adapters.exceptions import AdapterError
from backend.src.adapters.github import AdapterResult
from backend.src.knowledge.cache import RetrievalEvent, resolve
from backend.src.turn.state import EngagementState

_MAX_PLAYBOOKS = 4


@dataclass
class ContextPacket:
    system_prompt: str
    playbook_xml: str
    phase_summaries: str
    conversation_history: list[dict[str, Any]]
    current_message: str


@dataclass
class AssembledContext:
    packet: ContextPacket
    retrieval_events: list[RetrievalEvent]
    playbooks_selected: list[str]
    playbooks_failed: list[str]
    input_tokens_estimate: int


def _load_system_prompt(
    phase: str,
    conn: psycopg2.extensions.connection,
    adapter_fn: Callable[[dict[str, Any]], AdapterResult] | None,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source_type, source_ref, domain_tags, phase_relevance,
                   retrieval_strategy, retrieval_config
            FROM knowledge_sources
            WHERE source_type = 'system_prompt'
              AND %s = ANY(phase_relevance)
            LIMIT 1
            """,
            (phase,),
        )
        row = cur.fetchone()

    if row is None:
        return f"You are Axiom, an AI consulting assistant. Current phase: {phase}."

    source: dict[str, Any] = {
        "id": row[0],
        "source_type": row[1],
        "source_ref": row[2],
        "domain_tags": row[3],
        "phase_relevance": row[4],
        "retrieval_strategy": row[5],
        "retrieval_config": row[6],
    }
    try:
        text, _ = resolve(source, conn, adapter_fn)
        return text
    except AdapterError:
        return f"You are Axiom, an AI consulting assistant. Current phase: {phase}."


def _load_matching_sources(
    state: EngagementState,
    conn: psycopg2.extensions.connection,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source_type, source_ref, domain_tags, phase_relevance,
                   retrieval_strategy, retrieval_config
            FROM knowledge_sources
            WHERE domain_tags && %s::text[]
              AND %s = ANY(phase_relevance)
              AND source_type != 'system_prompt'
            ORDER BY id
            LIMIT %s
            """,
            (state.domain_tags, state.current_phase, _MAX_PLAYBOOKS),
        )
        rows = cur.fetchall()

    sources: list[dict[str, Any]] = []
    for row in rows:
        sources.append(
            {
                "id": row[0],
                "source_type": row[1],
                "source_ref": row[2],
                "domain_tags": row[3],
                "phase_relevance": row[4],
                "retrieval_strategy": row[5],
                "retrieval_config": row[6],
            }
        )
    return sources


def _load_conversation_history(
    engagement_id: object,
    phase: str,
    conn: psycopg2.extensions.connection,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content, phase
            FROM messages
            WHERE engagement_id = %s
              AND phase = %s
            ORDER BY created_at
            """,
            (str(engagement_id), phase),
        )
        rows = cur.fetchall()

    return [{"role": row[0], "content": row[1], "phase": row[2]} for row in rows]


def _format_phase_summaries(phase_context: dict[str, object]) -> str:
    if not phase_context:
        return ""
    lines = []
    for phase, summary in phase_context.items():
        lines.append(f"{phase}: {summary}")
    return "\n".join(lines)


def _estimate_tokens(packet: ContextPacket) -> int:
    total_chars = (
        len(packet.system_prompt)
        + len(packet.playbook_xml)
        + len(packet.phase_summaries)
        + sum(len(m.get("content", "")) for m in packet.conversation_history)
        + len(packet.current_message)
    )
    return max(1, total_chars // 4)


def assemble_context_packet(
    state: EngagementState,
    user_message: str,
    conn: psycopg2.extensions.connection,
    adapter_fn: Callable[[dict[str, Any]], AdapterResult] | None = None,
) -> AssembledContext:
    """Assemble the five-position context packet for a Bedrock call."""
    retrieval_events: list[RetrievalEvent] = []
    playbooks_selected: list[str] = []
    playbooks_failed: list[str] = []
    playbook_parts: list[str] = []

    # Position 1 — system prompt
    system_prompt = _load_system_prompt(state.current_phase, conn, adapter_fn)

    # Positions 2 — playbook XML from matching knowledge sources
    sources = _load_matching_sources(state, conn)
    for source in sources:
        source_id: str = source["id"]
        try:
            text, event = resolve(source, conn, adapter_fn)
            retrieval_events.append(event)
            playbooks_selected.append(source_id)
            playbook_parts.append(f'<playbook id="{source_id}">{text}</playbook>')
        except AdapterError:
            playbooks_failed.append(source_id)

    playbook_xml = "\n".join(playbook_parts)

    # Position 3 — phase summaries from engagement state
    phase_summaries = _format_phase_summaries(state.phase_context)

    # Position 4 — conversation history for current phase
    conversation_history = _load_conversation_history(
        state.engagement_id, state.current_phase, conn
    )

    # Position 5 — current user message
    packet = ContextPacket(
        system_prompt=system_prompt,
        playbook_xml=playbook_xml,
        phase_summaries=phase_summaries,
        conversation_history=conversation_history,
        current_message=user_message,
    )

    input_tokens_estimate = _estimate_tokens(packet)

    return AssembledContext(
        packet=packet,
        retrieval_events=retrieval_events,
        playbooks_selected=playbooks_selected,
        playbooks_failed=playbooks_failed,
        input_tokens_estimate=input_tokens_estimate,
    )
