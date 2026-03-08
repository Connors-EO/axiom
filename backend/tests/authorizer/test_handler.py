"""Tests for the origin-verify Lambda authorizer."""
import json
from unittest.mock import MagicMock, patch

import pytest

import backend.src.authorizer.handler as handler_module
from backend.src.authorizer.handler import handler

_SECRET_NAME = "axiom-staging-origin-verify"
_SECRET_VALUE = "supersecretvalue32chars0000000000"


@pytest.fixture(autouse=True)
def reset_secret_cache():
    """Reset the module-level secret cache before and after each test."""
    handler_module._secret_cache = None
    yield
    handler_module._secret_cache = None


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET_NAME", _SECRET_NAME)


def _sm_client(secret_value: str = _SECRET_VALUE) -> MagicMock:
    mock = MagicMock()
    mock.get_secret_value.return_value = {
        "SecretString": json.dumps({"value": secret_value})
    }
    return mock


def _event(headers: dict | None = None) -> dict:
    return {"headers": headers}


# ─── Happy path ───────────────────────────────────────────────────────────────


def test_valid_header_allows(mock_env: None) -> None:
    with patch("backend.src.authorizer.handler.boto3.client", return_value=_sm_client()):
        result = handler(_event({"x-origin-verify": _SECRET_VALUE}), None)
    assert result == {"isAuthorized": True}


def test_header_case_insensitive_allows(mock_env: None) -> None:
    """CloudFront may canonicalize header names — mixed case must match."""
    with patch("backend.src.authorizer.handler.boto3.client", return_value=_sm_client()):
        result = handler(_event({"X-Origin-Verify": _SECRET_VALUE}), None)
    assert result == {"isAuthorized": True}


def test_secret_cached_after_first_call(mock_env: None) -> None:
    """Secrets Manager is called only once even across multiple invocations."""
    mock_sm = _sm_client()
    with patch(
        "backend.src.authorizer.handler.boto3.client", return_value=mock_sm
    ) as mock_client:
        handler(_event({"x-origin-verify": _SECRET_VALUE}), None)
        handler(_event({"x-origin-verify": _SECRET_VALUE}), None)

    mock_client.assert_called_once()
    mock_sm.get_secret_value.assert_called_once()


# ─── Deny paths ───────────────────────────────────────────────────────────────


def test_invalid_header_denies(mock_env: None) -> None:
    with patch("backend.src.authorizer.handler.boto3.client", return_value=_sm_client()):
        result = handler(_event({"x-origin-verify": "wrong-value"}), None)
    assert result == {"isAuthorized": False}


def test_missing_header_denies(mock_env: None) -> None:
    """Request with no x-origin-verify header is denied."""
    with patch("backend.src.authorizer.handler.boto3.client", return_value=_sm_client()):
        result = handler(_event({}), None)
    assert result == {"isAuthorized": False}


def test_null_headers_field_denies(mock_env: None) -> None:
    """Event with headers=None (e.g. synthetic test events) is denied safely."""
    with patch("backend.src.authorizer.handler.boto3.client", return_value=_sm_client()):
        result = handler(_event(None), None)
    assert result == {"isAuthorized": False}


def test_secret_fetch_failure_denies(mock_env: None) -> None:
    """Secrets Manager errors must not leak details; request is denied."""
    failing_sm = MagicMock()
    failing_sm.get_secret_value.side_effect = RuntimeError("network error")
    with patch("backend.src.authorizer.handler.boto3.client", return_value=failing_sm):
        result = handler(_event({"x-origin-verify": _SECRET_VALUE}), None)
    assert result == {"isAuthorized": False}
