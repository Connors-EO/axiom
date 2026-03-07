import json
import traceback
from typing import Any
from uuid import UUID, uuid4

from backend.src.chat.errors import EngagementNotFoundError, TokenBudgetExceededError
from backend.src.shared.db import get_connection
from backend.src.turn.handler import process_turn

_JSON_HEADERS = {"Content-Type": "application/json"}


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": _JSON_HEADERS, "body": json.dumps(body)}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    conn = get_connection()
    try:
        method: str = event["requestContext"]["http"]["method"]

        if method != "POST":
            return _response(405, {"error": "Method not allowed"})

        engagement_id: str = event["pathParameters"]["id"]
        headers = event.get("headers") or {}
        session_id_str: str = headers.get("X-Session-Id", str(uuid4()))

        raw = json.loads(event.get("body") or "{}")
        message: str = raw.get("message", "").strip()
        if not message:
            return _response(400, {"error": "message is required"})

        result = process_turn(UUID(engagement_id), message, UUID(session_id_str), conn)
        conn.commit()

        return _response(
            200,
            {
                "response": result.response_text,
                "intent": result.intent_classified,
                "gate_evaluated": result.scope_check == "PASS",
            },
        )

    except EngagementNotFoundError:
        return _response(404, {"error": "Engagement not found"})
    except TokenBudgetExceededError:
        return _response(429, {"error": "Token budget exceeded"})
    except Exception:
        traceback.print_exc()
        return _response(500, {"error": "Internal server error"})
    finally:
        conn.close()
