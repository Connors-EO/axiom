from uuid import UUID

import psycopg2.extensions

from backend.src.engagement.db import (
    create_engagement,
    get_engagement,
    list_engagements,
)
from backend.src.engagement.models import CreateEngagementRequest

_FIXTURE_ENGAGEMENT_ID = "a0000000-0000-0000-0000-000000000001"

_CREATE_REQ = CreateEngagementRequest(
    title="New Engagement",
    client_name="Globex Corp",
    domain_tags=["cloud-platform", "security"],
    engagement_type="advisory",
)


def test_create_engagement_returns_response(db_conn: psycopg2.extensions.connection) -> None:
    result = create_engagement(_CREATE_REQ, "test", "practitioner-1", db_conn)

    assert result.title == "New Engagement"
    assert result.client_name == "Globex Corp"
    assert result.engagement_type == "advisory"
    assert result.domain_tags == ["cloud-platform", "security"]
    assert result.model_id == "us.anthropic.claude-sonnet-4-6"
    assert result.tenant_id == "test"
    assert result.id is not None
    assert isinstance(result.id, UUID)


def test_create_engagement_initializes_intake_phase(
    db_conn: psycopg2.extensions.connection,
) -> None:
    result = create_engagement(_CREATE_REQ, "test", "practitioner-1", db_conn)
    assert result.current_phase == "INTAKE"


def test_create_engagement_empty_phase_context_and_flags(
    db_conn: psycopg2.extensions.connection,
) -> None:
    result = create_engagement(_CREATE_REQ, "test", "practitioner-1", db_conn)
    assert result.phase_context == {}
    assert result.flags == {}


def test_create_engagement_timestamps_set(db_conn: psycopg2.extensions.connection) -> None:
    result = create_engagement(_CREATE_REQ, "test", "practitioner-1", db_conn)
    assert result.created_at is not None
    assert result.updated_at is not None


def test_get_engagement_returns_fixture(db_conn: psycopg2.extensions.connection) -> None:
    result = get_engagement(_FIXTURE_ENGAGEMENT_ID, "test", db_conn)

    assert result is not None
    assert str(result.id) == _FIXTURE_ENGAGEMENT_ID
    assert result.tenant_id == "test"
    assert result.model_id == "us.anthropic.claude-sonnet-4-6"


def test_get_engagement_not_found(db_conn: psycopg2.extensions.connection) -> None:
    result = get_engagement("00000000-0000-0000-0000-000000000000", "test", db_conn)
    assert result is None


def test_get_engagement_rls_isolation(db_conn: psycopg2.extensions.connection) -> None:
    result = get_engagement(_FIXTURE_ENGAGEMENT_ID, "other-tenant", db_conn)
    assert result is None


def test_list_engagements_returns_fixture(db_conn: psycopg2.extensions.connection) -> None:
    result = list_engagements("test", db_conn)

    assert result.total == 1
    assert len(result.engagements) == 1
    assert str(result.engagements[0].id) == _FIXTURE_ENGAGEMENT_ID


def test_list_engagements_empty_for_unknown_tenant(
    db_conn: psycopg2.extensions.connection,
) -> None:
    result = list_engagements("unknown-tenant", db_conn)
    assert result.total == 0
    assert result.engagements == []


def test_list_engagements_after_create(db_conn: psycopg2.extensions.connection) -> None:
    create_engagement(_CREATE_REQ, "test", "practitioner-1", db_conn)
    result = list_engagements("test", db_conn)
    assert result.total == 2
