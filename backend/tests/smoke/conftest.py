"""Fixtures for staging smoke tests.

All session-scoped fixtures that require external resources (Cognito, API GW)
skip gracefully when the resource is not available, allowing the test suite to
run in environments where only partial infrastructure is deployed.
"""
from __future__ import annotations

import json
import os
from typing import Any

import boto3
import httpx
import pytest
from botocore.exceptions import ClientError


def pytest_sessionfinish(session: Any, exitstatus: Any) -> None:
    """Disable the 100% coverage threshold for smoke test runs.

    Smoke tests exercise live infrastructure, not source code paths.
    addopts sets --cov-fail-under=100 globally; clear it here (before
    pytest_terminal_summary runs) so the smoke suite does not fail on
    missing backend/src coverage.
    """
    for plugin in session.config.pluginmanager.get_plugins():
        if plugin.__class__.__name__ == "CovPlugin":
            opts = getattr(plugin, "options", None)
            if opts is not None and hasattr(opts, "cov_fail_under"):
                setattr(opts, "cov_fail_under", 0)


@pytest.fixture(scope="session")
def apigw_url() -> str:
    """Direct API Gateway invoke URL for origin-lock testing.

    Discovered at runtime via the AWS API — no hard-coded URLs.
    """
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    response = client.get_apis()
    for api in response.get("Items", []):
        if api["Name"] == "axiom-staging":
            return str(api["ApiEndpoint"])
    pytest.fail("axiom-staging HTTP API not found in us-east-1")


@pytest.fixture(scope="session")
def staging_url() -> str:
    """Public CloudFront URL (AXIOM_STAGING_URL env var).

    Skips all dependent tests when not set — used only when testing
    through the full CloudFront → API GW path.
    """
    url = os.environ.get("AXIOM_STAGING_URL", "").rstrip("/")
    if not url:
        pytest.skip("AXIOM_STAGING_URL not set — skipping CloudFront smoke tests")
    return url


@pytest.fixture(scope="session")
def cognito_creds() -> dict:  # type: ignore[type-arg]
    """M2M client credentials from axiom-staging-smoke-test-client secret.

    Skips all dependent tests when Cognito is not yet deployed.
    """
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    try:
        resp = sm.get_secret_value(SecretId="axiom-staging-smoke-test-client")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("ResourceNotFoundException", "AccessDeniedException"):
            pytest.skip(
                "axiom-staging-smoke-test-client secret not found "
                "— Cognito not yet deployed, skipping Cognito smoke tests"
            )
        raise
    return json.loads(resp["SecretString"])  # type: ignore[no-any-return]


@pytest.fixture(scope="session")
def cognito_token(cognito_creds: dict) -> str:  # type: ignore[type-arg]
    """Short-lived OAuth2 access token via client_credentials flow."""
    resp = httpx.post(
        cognito_creds["token_endpoint"],
        data={
            "grant_type": "client_credentials",
            "scope": cognito_creds.get("scope", ""),
        },
        auth=(cognito_creds["client_id"], cognito_creds["client_secret"]),
        timeout=15.0,
    )
    resp.raise_for_status()
    return str(resp.json()["access_token"])


@pytest.fixture
def engagement_id(staging_url: str, cognito_token: str) -> str:
    """Create a test engagement and return its ID.

    Does not clean up — test engagements are cheap and staging data is ephemeral.
    """
    resp = httpx.post(
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
    resp.raise_for_status()
    return str(resp.json()["id"])
