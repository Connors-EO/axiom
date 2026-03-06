import hashlib

import httpx
import pytest

from backend.src.adapters.exceptions import (
    AdapterAuthError,
    AdapterError,
    AdapterNotFoundError,
    AdapterRateLimitError,
)
from backend.src.adapters.github import AdapterResult, fetch

SAMPLE_SOURCE = {
    "retrieval_config": {
        "repo_owner": "Connors-EO",
        "repo_name": "solution-accelerator",
        "branch": "main",
        "path": "playbooks/existing/iac-terraform-multi-account.md",
    }
}


class _MockTransport(httpx.BaseTransport):
    def __init__(self, status_code: int, body: str = "") -> None:
        self._status_code = status_code
        self._body = body

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=self._status_code,
            text=self._body,
        )


def test_fetch_success_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    result = fetch(SAMPLE_SOURCE, _transport=_MockTransport(200, "# Hello World"))
    assert isinstance(result, AdapterResult)
    assert result.text == "# Hello World"


def test_fetch_content_hash_is_sha256(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    body = "# Hello World"
    result = fetch(SAMPLE_SOURCE, _transport=_MockTransport(200, body))
    expected = hashlib.sha256(body.encode()).hexdigest()
    assert result.content_hash == expected


def test_fetch_latency_ms_non_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    result = fetch(SAMPLE_SOURCE, _transport=_MockTransport(200, "content"))
    assert result.fetch_latency_ms >= 0


def test_fetch_404_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    with pytest.raises(AdapterNotFoundError):
        fetch(SAMPLE_SOURCE, _transport=_MockTransport(404))


def test_fetch_401_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    with pytest.raises(AdapterAuthError):
        fetch(SAMPLE_SOURCE, _transport=_MockTransport(401))


def test_fetch_403_raises_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    with pytest.raises(AdapterRateLimitError):
        fetch(SAMPLE_SOURCE, _transport=_MockTransport(403))


def test_fetch_429_raises_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    with pytest.raises(AdapterRateLimitError):
        fetch(SAMPLE_SOURCE, _transport=_MockTransport(429))


def test_fetch_500_raises_adapter_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "test-pat")
    with pytest.raises(AdapterError):
        fetch(SAMPLE_SOURCE, _transport=_MockTransport(500))


def test_fetch_missing_pat_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_PAT", raising=False)
    with pytest.raises(AdapterAuthError):
        fetch(SAMPLE_SOURCE)
