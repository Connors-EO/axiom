import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

from backend.src.adapters.exceptions import (
    AdapterAuthError,
    AdapterError,
    AdapterNotFoundError,
    AdapterRateLimitError,
)

load_dotenv()


@dataclass
class AdapterResult:
    text: str
    content_hash: str
    fetch_latency_ms: int


def fetch(
    source: dict[str, Any],
    _transport: httpx.BaseTransport | None = None,
) -> AdapterResult:
    """Fetch raw file content from GitHub.

    source must contain retrieval_config with keys:
        repo_owner, repo_name, branch, path

    Reads GITHUB_PAT from environment.

    Raises:
        AdapterNotFoundError: GitHub returned 404
        AdapterAuthError: GitHub returned 401
        AdapterRateLimitError: GitHub returned 403 or 429
        AdapterError: any other error
    """
    pat = os.environ.get("GITHUB_PAT")
    if not pat:
        raise AdapterAuthError("GITHUB_PAT environment variable is not set")

    config: dict[str, str] = source["retrieval_config"]
    url = (
        f"https://api.github.com/repos/{config['repo_owner']}/{config['repo_name']}"
        f"/contents/{config['path']}?ref={config['branch']}"
    )
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github.raw+json",
    }

    t0 = time.monotonic()
    with httpx.Client(transport=_transport) as client:
        response = client.get(url, headers=headers)
    latency_ms = int((time.monotonic() - t0) * 1000)

    if response.status_code == 200:
        text = response.text
        return AdapterResult(
            text=text,
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
            fetch_latency_ms=latency_ms,
        )
    if response.status_code == 404:
        raise AdapterNotFoundError(f"GitHub returned 404 for {url}")
    if response.status_code == 401:
        raise AdapterAuthError(f"GitHub returned 401 for {url}")
    if response.status_code in (403, 429):
        raise AdapterRateLimitError(f"GitHub returned {response.status_code} for {url}")
    raise AdapterError(f"GitHub returned {response.status_code} for {url}")
