from uuid import UUID, uuid4

import psycopg2.extensions
import pytest

from backend.src.turn.state import EngagementNotFoundError, EngagementState, read_engagement_state

ENGAGEMENT_ID = UUID("a0000000-0000-0000-0000-000000000001")


def test_read_engagement_state_returns_correct_fields(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = read_engagement_state(ENGAGEMENT_ID, db_conn)

    assert isinstance(state, EngagementState)
    assert state.engagement_id == ENGAGEMENT_ID
    assert state.tenant_id == "test"
    assert state.model_id == "us.anthropic.claude-sonnet-4-6"
    assert state.current_phase == "RESEARCH_DISCOVERY"


def test_turn_number_is_message_count_plus_one(
    db_conn: psycopg2.extensions.connection,
) -> None:
    # Fixture inserts 3 messages → turn_number should be 4
    state = read_engagement_state(ENGAGEMENT_ID, db_conn)
    assert state.turn_number == 4


def test_raises_engagement_not_found_for_unknown_id(
    db_conn: psycopg2.extensions.connection,
) -> None:
    unknown = uuid4()
    with pytest.raises(EngagementNotFoundError):
        read_engagement_state(unknown, db_conn)


def test_domain_tags_parsed_as_list(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = read_engagement_state(ENGAGEMENT_ID, db_conn)
    assert isinstance(state.domain_tags, list)
    assert state.domain_tags == ["cloud-platform"]


def test_phase_context_parsed_as_dict(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = read_engagement_state(ENGAGEMENT_ID, db_conn)
    assert isinstance(state.phase_context, dict)
    assert state.phase_context == {}


def test_flags_parsed_as_dict(
    db_conn: psycopg2.extensions.connection,
) -> None:
    state = read_engagement_state(ENGAGEMENT_ID, db_conn)
    assert isinstance(state.flags, dict)
    assert state.flags == {}
