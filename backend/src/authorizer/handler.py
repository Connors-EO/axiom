"""Lambda authorizer — validates x-origin-verify header for HTTP API Gateway."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_secret_cache: str | None = None


def _get_secret() -> str:
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache
    client = boto3.client("secretsmanager", region_name="us-east-1")
    secret_name = os.environ["ORIGIN_VERIFY_SECRET_NAME"]
    response = client.get_secret_value(SecretId=secret_name)
    payload = json.loads(response["SecretString"])
    _secret_cache = payload["value"]
    return _secret_cache


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Return allow/deny policy for x-origin-verify header validation."""
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    origin_verify = headers.get("x-origin-verify", "")

    try:
        expected = _get_secret()
    except Exception:
        logger.exception("Failed to retrieve origin verify secret")
        return _deny()

    if origin_verify == expected:
        logger.info("x-origin-verify valid")
        return _allow()

    logger.warning("x-origin-verify invalid or missing")
    return _deny()


def _allow() -> dict[str, Any]:
    return {"isAuthorized": True}


def _deny() -> dict[str, Any]:
    return {"isAuthorized": False}
