import hashlib
from typing import Any
from uuid import UUID

import psycopg2.extensions

from backend.src.adapters.exceptions import AdapterError
from backend.src.adapters.github import AdapterResult
from backend.src.turn.context import AssembledContext, ContextPacket, assemble_context_packet
from backend.src.turn.state import EngagementState

ENGAGEMENT_ID = UUID("a0000000-0000-0000-0000-000000000001")
MOCK_TEXT = "# Mock Playbook Content"
MOCK_HASH = hashlib.sha256(MOCK_TEXT.encode()).hexdigest()


def _mock_adapter(source: dict[str, Any]) -> AdapterResult:
    return AdapterResult(
        text=MOCK_TEXT,
        content_hash=MOCK_HASH,
        fetch_latency_ms=5,
    )


def _make_state(
    phase: str = "RESEARCH_DISCOVERY",
    domain_tags: list[str] | None = None,
) -> EngagementState:
    return EngagementState(
        engagement_id=ENGAGEMENT_ID,
        tenant_id="test",
        model_id="us.anthropic.claude-sonnet-4-6",
        current_phase=phase,
        domain_tags=domain_tags if domain_tags is not None else ["cloud-platform"],
        phase_context={},
        flags={},
        turn_number=4,
    )


def test_returns_assembled_context_with_all_five_positions(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    result = assemble_context_packet(state, "Tell me about cloud.", db_conn, adapter_fn=_mock_adapter)

    assert isinstance(result, AssembledContext)
    assert isinstance(result.packet, ContextPacket)
    assert isinstance(result.packet.system_prompt, str)
    assert len(result.packet.system_prompt) > 0
    assert isinstance(result.packet.playbook_xml, str)
    assert isinstance(result.packet.phase_summaries, str)
    assert isinstance(result.packet.conversation_history, list)
    assert result.packet.current_message == "Tell me about cloud."


def test_playbook_xml_format(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    result = assemble_context_packet(state, "user msg", db_conn, adapter_fn=_mock_adapter)

    assert '<playbook id="cloud-001">' in result.packet.playbook_xml
    assert "</playbook>" in result.packet.playbook_xml
    assert MOCK_TEXT in result.packet.playbook_xml


def test_filters_by_domain_tags(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Insert a source with a different domain_tag
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_sources
                (id, source_type, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
            VALUES (
                'other-domain-001', 'github_file',
                ARRAY['security'], ARRAY['RESEARCH_DISCOVERY'],
                'cag',
                '{"repo_owner":"x","repo_name":"y","branch":"main","path":"p.md"}'::jsonb,
                'test'
            )
            """
        )
    state = _make_state(domain_tags=["cloud-platform"])
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=_mock_adapter)

    selected_ids = result.playbooks_selected
    assert "other-domain-001" not in selected_ids
    assert all(s in ["cloud-001", "cloud-002"] for s in selected_ids)


def test_filters_by_phase_relevance(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Insert a source matching domain_tag but wrong phase
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_sources
                (id, source_type, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
            VALUES (
                'wrong-phase-001', 'github_file',
                ARRAY['cloud-platform'], ARRAY['INTAKE'],
                'cag',
                '{"repo_owner":"x","repo_name":"y","branch":"main","path":"p.md"}'::jsonb,
                'test'
            )
            """
        )
    state = _make_state(phase="RESEARCH_DISCOVERY")
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=_mock_adapter)

    assert "wrong-phase-001" not in result.playbooks_selected


def test_max_four_playbooks_selected(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Insert 3 more sources so there are 5 matching total
    with db_conn.cursor() as cur:
        for i in range(3, 6):
            cur.execute(
                f"""
                INSERT INTO knowledge_sources
                    (id, source_type, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
                VALUES (
                    'cloud-extra-00{i}', 'github_file',
                    ARRAY['cloud-platform'], ARRAY['RESEARCH_DISCOVERY'],
                    'cag',
                    '{{"repo_owner":"x","repo_name":"y","branch":"main","path":"p{i}.md"}}'::jsonb,
                    'test'
                )
                """
            )
    state = _make_state()
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=_mock_adapter)

    assert len(result.playbooks_selected) <= 4


def test_cache_miss_triggers_adapter_call(
    db_conn: psycopg2.extensions.connection,
) -> None:
    call_count = 0

    def counting_adapter(source: dict[str, Any]) -> AdapterResult:
        nonlocal call_count
        call_count += 1
        return AdapterResult(text=MOCK_TEXT, content_hash=MOCK_HASH, fetch_latency_ms=5)

    state = _make_state()
    assemble_context_packet(state, "msg", db_conn, adapter_fn=counting_adapter)

    # cloud-001 and cloud-002 are both cache misses → adapter called twice
    assert call_count == 2


def test_cache_hit_skips_adapter_call(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Pre-populate cache for cloud-001 and cloud-002
    with db_conn.cursor() as cur:
        for source_id in ("cloud-001", "cloud-002"):
            cur.execute(
                """
                INSERT INTO knowledge_cache
                    (source_id, processed_text, is_stale, expires_at, content_hash, tenant_id)
                VALUES (%s, %s, false, NOW() + interval '24 hours', %s, 'test')
                """,
                (source_id, MOCK_TEXT, MOCK_HASH),
            )

    call_count = 0

    def counting_adapter(source: dict[str, Any]) -> AdapterResult:
        nonlocal call_count
        call_count += 1
        return AdapterResult(text=MOCK_TEXT, content_hash=MOCK_HASH, fetch_latency_ms=5)

    state = _make_state()
    assemble_context_packet(state, "msg", db_conn, adapter_fn=counting_adapter)

    assert call_count == 0


def test_conversation_history_current_phase_only(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Insert a message from a different phase
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (id, role, content, phase, engagement_id, tenant_id, turn_number)
            VALUES (
                'c0000000-0000-0000-0000-000000000001',
                'user', 'This is from INTAKE phase.', 'INTAKE',
                'a0000000-0000-0000-0000-000000000001', 'test', 0
            )
            """
        )

    state = _make_state(phase="RESEARCH_DISCOVERY")
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=_mock_adapter)

    # Conversation history should only contain messages from RESEARCH_DISCOVERY
    for msg in result.packet.conversation_history:
        assert msg.get("phase") != "INTAKE"


def test_input_tokens_estimate_is_positive(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = _make_state()
    result = assemble_context_packet(state, "user message", db_conn, adapter_fn=_mock_adapter)

    assert isinstance(result.input_tokens_estimate, int)
    assert result.input_tokens_estimate > 0


def test_playbooks_failed_populated_on_adapter_error(
    db_conn: psycopg2.extensions.connection,
) -> None:
    def failing_adapter(source: dict[str, Any]) -> AdapterResult:
        raise AdapterError("connection refused")

    state = _make_state()
    # Should not raise — just records failure
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=failing_adapter)

    assert len(result.playbooks_failed) == 2  # cloud-001 and cloud-002 both fail
    assert "cloud-001" in result.playbooks_failed
    assert "cloud-002" in result.playbooks_failed


def test_system_prompt_loaded_from_knowledge_source(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Insert a system_prompt knowledge source for RESEARCH_DISCOVERY
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_sources
                (id, source_type, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
            VALUES (
                'sysprompt-rd-001', 'system_prompt',
                ARRAY['cloud-platform'], ARRAY['RESEARCH_DISCOVERY'],
                'cag',
                '{"repo_owner":"x","repo_name":"y","branch":"main","path":"sp.md"}'::jsonb,
                'test'
            )
            """
        )

    prompt_text = "Custom system prompt for RESEARCH_DISCOVERY."

    def custom_adapter(source: dict[str, Any]) -> AdapterResult:
        return AdapterResult(
            text=prompt_text,
            content_hash=hashlib.sha256(prompt_text.encode()).hexdigest(),
            fetch_latency_ms=1,
        )

    state = _make_state()
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=custom_adapter)

    assert result.packet.system_prompt == prompt_text


def test_system_prompt_adapter_error_falls_back_to_placeholder(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Insert a system_prompt source but adapter will fail
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge_sources
                (id, source_type, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
            VALUES (
                'sysprompt-rd-002', 'system_prompt',
                ARRAY['cloud-platform'], ARRAY['RESEARCH_DISCOVERY'],
                'cag',
                '{"repo_owner":"x","repo_name":"y","branch":"main","path":"sp2.md"}'::jsonb,
                'test'
            )
            """
        )

    def failing_adapter(source: dict[str, Any]) -> AdapterResult:
        raise AdapterError("network error")

    state = _make_state()
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=failing_adapter)

    assert "Axiom" in result.packet.system_prompt
    assert "RESEARCH_DISCOVERY" in result.packet.system_prompt


def test_phase_summaries_formatted_when_non_empty(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = EngagementState(
        engagement_id=ENGAGEMENT_ID,
        tenant_id="test",
        model_id="us.anthropic.claude-sonnet-4-6",
        current_phase="RESEARCH_DISCOVERY",
        domain_tags=["cloud-platform"],
        phase_context={"INTAKE": "Completed intake with client."},
        flags={},
        turn_number=4,
    )
    result = assemble_context_packet(state, "msg", db_conn, adapter_fn=_mock_adapter)

    assert "INTAKE" in result.packet.phase_summaries
    assert "Completed intake with client." in result.packet.phase_summaries
