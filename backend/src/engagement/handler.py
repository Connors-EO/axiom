import json
import os
from typing import Any

from backend.src.db.client import get_connection
from backend.src.engagement.db import (
    create_engagement,
    get_engagement,
    list_engagements,
)
from backend.src.engagement.models import (
    CreateEngagementRequest,
    EngagementResponse,
    ListEngagementsResponse,
)

_JSON_HEADERS = {"Content-Type": "application/json"}


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": _JSON_HEADERS, "body": json.dumps(body)}


def _serialize_engagement(eng: EngagementResponse) -> dict[str, Any]:
    return {
        "id": str(eng.id),
        "title": eng.title,
        "client_name": eng.client_name,
        "engagement_type": eng.engagement_type,
        "current_phase": eng.current_phase,
        "domain_tags": eng.domain_tags,
        "phase_context": eng.phase_context,
        "flags": eng.flags,
        "model_id": eng.model_id,
        "tenant_id": eng.tenant_id,
        "created_at": eng.created_at.isoformat(),
        "updated_at": eng.updated_at.isoformat(),
    }


def _serialize_list(resp: ListEngagementsResponse) -> dict[str, Any]:
    return {
        "engagements": [_serialize_engagement(e) for e in resp.engagements],
        "total": resp.total,
    }


def _extract_tenant_id(event: dict[str, Any]) -> str:
    if os.environ.get("AXIOM_ENV") == "local":
        headers = event.get("headers") or {}
        return str(headers.get("X-Tenant-Id", ""))
    return str(
        event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    conn = get_connection()
    try:
        http = event["requestContext"]["http"]
        method: str = http["method"]
        path: str = http["path"]
        tenant_id = _extract_tenant_id(event)

        if method == "POST" and path == "/api/engagements":
            return _handle_create(event, tenant_id, conn)

        if method == "GET" and path == "/api/engagements":
            return _handle_list(tenant_id, conn)

        if method == "GET" and path.startswith("/api/engagements/"):
            engagement_id = path.removeprefix("/api/engagements/")
            return _handle_get(engagement_id, tenant_id, conn)

        return _response(404, {"error": "Not found"})

    except (ValueError, KeyError, TypeError) as exc:
        return _response(400, {"error": str(exc)})
    except Exception:
        return _response(500, {"error": "Internal server error"})
    finally:
        conn.close()


def _handle_create(
    event: dict[str, Any],
    tenant_id: str,
    conn: Any,
) -> dict[str, Any]:
    raw = json.loads(event.get("body") or "{}")
    if "title" not in raw or "client_name" not in raw or "engagement_type" not in raw:
        raise ValueError("Missing required fields: title, client_name, engagement_type")
    req = CreateEngagementRequest(
        title=raw["title"],
        client_name=raw["client_name"],
        domain_tags=raw.get("domain_tags", []),
        engagement_type=raw["engagement_type"],
        model_id=raw.get("model_id", "us.anthropic.claude-sonnet-4-6"),
    )
    result = create_engagement(req, tenant_id, tenant_id, conn)
    conn.commit()
    return _response(201, _serialize_engagement(result))


def _handle_get(
    engagement_id: str,
    tenant_id: str,
    conn: Any,
) -> dict[str, Any]:
    result = get_engagement(engagement_id, tenant_id, conn)
    if result is None:
        return _response(404, {"error": "Engagement not found"})
    return _response(200, _serialize_engagement(result))


def _handle_list(tenant_id: str, conn: Any) -> dict[str, Any]:
    result = list_engagements(tenant_id, conn)
    return _response(200, _serialize_list(result))
