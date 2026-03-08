"""Staging smoke tests.

Run with:
    poetry run pytest backend/tests/smoke/ -m smoke -v

All tests are marked @pytest.mark.smoke.

Tests that require Cognito or a live database are skipped automatically
when those resources are unavailable — see conftest.py fixtures for skip
conditions. Only test_origin_lock_rejects_direct_request runs in all
environments.
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.smoke
def test_origin_lock_rejects_direct_request(apigw_url: str) -> None:
    """Direct API Gateway call without x-origin-verify must return 401.

    API Gateway v2 with a Lambda REQUEST authorizer returns 401 when the
    required identity source header (x-origin-verify) is absent — without
    even invoking the Lambda. Callers who bypass CloudFront (which injects
    x-origin-verify automatically) are rejected at the gateway level.
    """
    response = httpx.get(f"{apigw_url}/health", timeout=10.0)
    # API GW v2 returns 401 when the required identity source header
    # (x-origin-verify) is missing — before the Lambda authorizer is invoked.
    assert response.status_code == 401, (
        f"Expected 401 from origin-lock but got {response.status_code}. "
        "The Lambda authorizer may not be configured correctly."
    )


@pytest.mark.smoke
def test_create_engagement(staging_url: str, cognito_token: str) -> None:
    """POST /api/engagements creates a new engagement and returns 201."""
    response = httpx.post(
        f"{staging_url}/api/engagements",
        headers={
            "Authorization": f"Bearer {cognito_token}",
            "Content-Type": "application/json",
        },
        json={
            "title": "Smoke Test Engagement",
            "client_name": "Smoke Test Client",
            "engagement_type": "advisory",
            "domain_tags": ["smoke"],
        },
        timeout=15.0,
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["current_phase"] == "INTAKE"


@pytest.mark.smoke
def test_get_engagement(staging_url: str, cognito_token: str, engagement_id: str) -> None:
    """GET /api/engagements/{id} returns the created engagement."""
    response = httpx.get(
        f"{staging_url}/api/engagements/{engagement_id}",
        headers={"Authorization": f"Bearer {cognito_token}"},
        timeout=15.0,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == engagement_id
    assert body["client_name"] == "Smoke Test Client"


@pytest.mark.smoke
def test_list_engagements(staging_url: str, cognito_token: str, engagement_id: str) -> None:
    """GET /api/engagements returns a list that includes the created engagement."""
    response = httpx.get(
        f"{staging_url}/api/engagements",
        headers={"Authorization": f"Bearer {cognito_token}"},
        timeout=15.0,
    )
    assert response.status_code == 200
    body = response.json()
    assert "engagements" in body
    ids = [e["id"] for e in body["engagements"]]
    assert engagement_id in ids, (
        f"Created engagement {engagement_id} not found in list"
    )


@pytest.mark.smoke
def test_chat_turn(staging_url: str, cognito_token: str, engagement_id: str) -> None:
    """POST /api/engagements/{id}/chat sends a message and returns a response."""
    response = httpx.post(
        f"{staging_url}/api/engagements/{engagement_id}/chat",
        headers={
            "Authorization": f"Bearer {cognito_token}",
            "Content-Type": "application/json",
        },
        json={"message": "What is the scope of this engagement?"},
        timeout=60.0,
    )
    assert response.status_code == 200
    body = response.json()
    assert "response" in body
    assert len(body["response"]) > 0
