import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from backend.src.engagement.handler import lambda_handler
from backend.src.engagement.models import EngagementResponse, ListEngagementsResponse

_TENANT_ID = "tenant-from-jwt"

_MOCK_RESPONSE = EngagementResponse(
    id=UUID("a0000000-0000-0000-0000-000000000001"),
    title="Test Engagement",
    client_name="ACME Corp",
    engagement_type="standard",
    current_phase="INTAKE",
    domain_tags=["cloud-platform"],
    phase_context={},
    flags={},
    model_id="us.anthropic.claude-sonnet-4-6",
    tenant_id=_TENANT_ID,
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
)


def _jwt_event(method: str, path: str, body: dict | None = None) -> dict:
    event: dict = {
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {
                "jwt": {"claims": {"sub": _TENANT_ID}}
            },
        },
        "headers": {"content-type": "application/json"},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def _local_event(method: str, path: str, tenant_id: str, body: dict | None = None) -> dict:
    event: dict = {
        "requestContext": {"http": {"method": method, "path": path}},
        "headers": {"content-type": "application/json", "X-Tenant-Id": tenant_id},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


_VALID_BODY = {
    "title": "Test Engagement",
    "client_name": "ACME Corp",
    "domain_tags": ["cloud-platform"],
    "engagement_type": "standard",
}


def test_create_engagement_success() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.engagement.handler.create_engagement",
            return_value=_MOCK_RESPONSE,
        ) as mock_create,
    ):
        result = lambda_handler(_jwt_event("POST", "/api/engagements", _VALID_BODY), None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["title"] == "Test Engagement"
    assert body["tenant_id"] == _TENANT_ID
    mock_conn.close.assert_called_once()
    mock_create.assert_called_once()


def test_create_engagement_invalid_model() -> None:
    mock_conn = MagicMock()
    body = {**_VALID_BODY, "model_id": "gpt-4"}
    with patch("backend.src.engagement.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_jwt_event("POST", "/api/engagements", body), None)

    assert result["statusCode"] == 400
    assert "model_id" in json.loads(result["body"])["error"]
    mock_conn.close.assert_called_once()


def test_create_engagement_missing_domain_tags() -> None:
    mock_conn = MagicMock()
    body = {**_VALID_BODY, "domain_tags": []}
    with patch("backend.src.engagement.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_jwt_event("POST", "/api/engagements", body), None)

    assert result["statusCode"] == 400
    assert "domain_tags" in json.loads(result["body"])["error"]
    mock_conn.close.assert_called_once()


def test_create_engagement_missing_required_field() -> None:
    mock_conn = MagicMock()
    body = {"client_name": "ACME", "domain_tags": ["cloud"]}
    with patch("backend.src.engagement.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_jwt_event("POST", "/api/engagements", body), None)

    assert result["statusCode"] == 400
    mock_conn.close.assert_called_once()


def test_get_engagement_success() -> None:
    eid = "a0000000-0000-0000-0000-000000000001"
    mock_conn = MagicMock()
    with (
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.engagement.handler.get_engagement",
            return_value=_MOCK_RESPONSE,
        ),
    ):
        result = lambda_handler(_jwt_event("GET", f"/api/engagements/{eid}"), None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == eid
    mock_conn.close.assert_called_once()


def test_get_engagement_not_found() -> None:
    eid = "00000000-0000-0000-0000-000000000000"
    mock_conn = MagicMock()
    with (
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch("backend.src.engagement.handler.get_engagement", return_value=None),
    ):
        result = lambda_handler(_jwt_event("GET", f"/api/engagements/{eid}"), None)

    assert result["statusCode"] == 404
    mock_conn.close.assert_called_once()


def test_list_engagements() -> None:
    mock_conn = MagicMock()
    mock_list = ListEngagementsResponse(engagements=[_MOCK_RESPONSE], total=1)
    with (
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch("backend.src.engagement.handler.list_engagements", return_value=mock_list),
    ):
        result = lambda_handler(_jwt_event("GET", "/api/engagements"), None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["total"] == 1
    assert len(body["engagements"]) == 1
    mock_conn.close.assert_called_once()


def test_tenant_id_from_jwt_claim() -> None:
    mock_conn = MagicMock()
    body_with_tenant = {**_VALID_BODY, "tenant_id": "should-be-ignored"}
    with (
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.engagement.handler.create_engagement",
            return_value=_MOCK_RESPONSE,
        ) as mock_create,
    ):
        lambda_handler(_jwt_event("POST", "/api/engagements", body_with_tenant), None)

    _, call_kwargs = mock_create.call_args
    call_args = mock_create.call_args[0]
    assert call_args[1] == _TENANT_ID


def test_local_env_fallback() -> None:
    mock_conn = MagicMock()
    mock_list = ListEngagementsResponse(engagements=[], total=0)
    local_tenant = "local-test-tenant"
    with (
        patch.dict(os.environ, {"AXIOM_ENV": "local"}),
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.engagement.handler.list_engagements",
            return_value=mock_list,
        ) as mock_list_fn,
    ):
        lambda_handler(_local_event("GET", "/api/engagements", local_tenant), None)

    call_args = mock_list_fn.call_args[0]
    assert call_args[0] == local_tenant


def test_unknown_route_returns_404() -> None:
    mock_conn = MagicMock()
    with patch("backend.src.engagement.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_jwt_event("DELETE", "/api/engagements/123"), None)

    assert result["statusCode"] == 404
    mock_conn.close.assert_called_once()


def test_internal_error_returns_500() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.engagement.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.engagement.handler.list_engagements",
            side_effect=RuntimeError("db exploded"),
        ),
    ):
        result = lambda_handler(_jwt_event("GET", "/api/engagements"), None)

    assert result["statusCode"] == 500
    body = json.loads(result["body"])
    assert "error" in body
    assert "db exploded" not in body["error"]
    mock_conn.close.assert_called_once()
