from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.src.engagement.models import (
    CreateEngagementRequest,
    EngagementResponse,
    ListEngagementsResponse,
)

_VALID_RESPONSE = EngagementResponse(
    id=UUID("a0000000-0000-0000-0000-000000000001"),
    title="Test Engagement",
    client_name="ACME Corp",
    engagement_type="standard",
    current_phase="INTAKE",
    domain_tags=["cloud-platform"],
    phase_context={},
    flags={},
    model_id="us.anthropic.claude-sonnet-4-6",
    tenant_id="test",
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
)


def test_create_request_default_model_id() -> None:
    req = CreateEngagementRequest(
        title="Test",
        client_name="ACME",
        domain_tags=["cloud"],
        engagement_type="standard",
    )
    assert req.model_id == "us.anthropic.claude-sonnet-4-6"


def test_create_request_accepts_nova_pro() -> None:
    req = CreateEngagementRequest(
        title="Test",
        client_name="ACME",
        domain_tags=["cloud"],
        engagement_type="standard",
        model_id="amazon.nova-pro-v1:0",
    )
    assert req.model_id == "amazon.nova-pro-v1:0"


def test_create_request_rejects_invalid_model_id() -> None:
    with pytest.raises(ValueError, match="model_id"):
        CreateEngagementRequest(
            title="Test",
            client_name="ACME",
            domain_tags=["cloud"],
            engagement_type="standard",
            model_id="gpt-4",
        )


def test_create_request_rejects_empty_domain_tags() -> None:
    with pytest.raises(ValueError, match="domain_tags"):
        CreateEngagementRequest(
            title="Test",
            client_name="ACME",
            domain_tags=[],
            engagement_type="standard",
        )


def test_engagement_response_fields() -> None:
    assert _VALID_RESPONSE.id == UUID("a0000000-0000-0000-0000-000000000001")
    assert _VALID_RESPONSE.title == "Test Engagement"
    assert _VALID_RESPONSE.client_name == "ACME Corp"
    assert _VALID_RESPONSE.engagement_type == "standard"
    assert _VALID_RESPONSE.current_phase == "INTAKE"
    assert _VALID_RESPONSE.domain_tags == ["cloud-platform"]
    assert _VALID_RESPONSE.phase_context == {}
    assert _VALID_RESPONSE.flags == {}
    assert _VALID_RESPONSE.model_id == "us.anthropic.claude-sonnet-4-6"
    assert _VALID_RESPONSE.tenant_id == "test"


def test_list_engagements_response() -> None:
    resp = ListEngagementsResponse(engagements=[_VALID_RESPONSE], total=1)
    assert resp.total == 1
    assert len(resp.engagements) == 1
    assert resp.engagements[0].title == "Test Engagement"
