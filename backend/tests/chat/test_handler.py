import json
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from backend.src.chat.errors import EngagementNotFoundError, TokenBudgetExceededError
from backend.src.chat.handler import lambda_handler
from backend.src.turn.handler import TurnResult

_TRACE_ID = UUID("c0000000-0000-0000-0000-000000000001")
_ENGAGEMENT_ID = "a0000000-0000-0000-0000-000000000001"
_SESSION_ID = str(uuid4())
_TENANT_ID = "tenant-from-jwt"

_MOCK_RESULT = TurnResult(
    response_text="The plan is solid.",
    intent_classified="recommendation",
    scope_check="PASS",
    trace_id=_TRACE_ID,
    turn_number=4,
)


def _post_event(
    engagement_id: str = _ENGAGEMENT_ID,
    body: dict | None = None,
    session_id: str | None = _SESSION_ID,
) -> dict:
    headers: dict = {"content-type": "application/json"}
    if session_id is not None:
        headers["X-Session-Id"] = session_id
    event: dict = {
        "requestContext": {
            "http": {"method": "POST", "path": f"/api/engagements/{engagement_id}/chat"},
            "authorizer": {"jwt": {"claims": {"sub": _TENANT_ID}}},
        },
        "pathParameters": {"id": engagement_id},
        "headers": headers,
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def _get_event(engagement_id: str = _ENGAGEMENT_ID) -> dict:
    return {
        "requestContext": {
            "http": {"method": "GET", "path": f"/api/engagements/{engagement_id}/chat"},
            "authorizer": {"jwt": {"claims": {"sub": _TENANT_ID}}},
        },
        "pathParameters": {"id": engagement_id},
        "headers": {},
    }


def test_chat_success() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.chat.handler.get_connection", return_value=mock_conn),
        patch("backend.src.chat.handler.process_turn", return_value=_MOCK_RESULT),
    ):
        result = lambda_handler(_post_event(body={"message": "What is the plan?"}), None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["response"] == "The plan is solid."
    assert body["intent"] == "recommendation"
    assert body["gate_evaluated"] is True
    mock_conn.close.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_chat_missing_message() -> None:
    mock_conn = MagicMock()
    with patch("backend.src.chat.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_post_event(body={}), None)

    assert result["statusCode"] == 400
    mock_conn.close.assert_called_once()


def test_chat_empty_message() -> None:
    mock_conn = MagicMock()
    with patch("backend.src.chat.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_post_event(body={"message": "   "}), None)

    assert result["statusCode"] == 400
    mock_conn.close.assert_called_once()


def test_chat_invalid_method() -> None:
    mock_conn = MagicMock()
    with patch("backend.src.chat.handler.get_connection", return_value=mock_conn):
        result = lambda_handler(_get_event(), None)

    assert result["statusCode"] == 405
    mock_conn.close.assert_called_once()


def test_chat_engagement_not_found() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.chat.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.chat.handler.process_turn",
            side_effect=EngagementNotFoundError("not found"),
        ),
    ):
        result = lambda_handler(_post_event(body={"message": "hi"}), None)

    assert result["statusCode"] == 404
    mock_conn.close.assert_called_once()


def test_chat_token_budget_exceeded() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.chat.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.chat.handler.process_turn",
            side_effect=TokenBudgetExceededError("over budget"),
        ),
    ):
        result = lambda_handler(_post_event(body={"message": "hi"}), None)

    assert result["statusCode"] == 429
    mock_conn.close.assert_called_once()


def test_session_id_generated_when_missing() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.chat.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.chat.handler.process_turn", return_value=_MOCK_RESULT
        ) as mock_pt,
    ):
        lambda_handler(_post_event(body={"message": "hello"}, session_id=None), None)

    call_args = mock_pt.call_args[0]
    assert isinstance(call_args[2], UUID)


def test_response_never_includes_traceback() -> None:
    mock_conn = MagicMock()
    with (
        patch("backend.src.chat.handler.get_connection", return_value=mock_conn),
        patch(
            "backend.src.chat.handler.process_turn",
            side_effect=RuntimeError("database exploded"),
        ),
    ):
        result = lambda_handler(_post_event(body={"message": "hi"}), None)

    assert result["statusCode"] == 500
    assert "Traceback" not in result["body"]
    assert "database exploded" not in result["body"]
    mock_conn.close.assert_called_once()


def test_gate_evaluated_false_when_scope_not_pass() -> None:
    mock_conn = MagicMock()
    out_of_scope_result = TurnResult(
        response_text="Out of scope.",
        intent_classified="out_of_scope",
        scope_check="OUT_OF_SCOPE",
        trace_id=_TRACE_ID,
        turn_number=1,
    )
    with (
        patch("backend.src.chat.handler.get_connection", return_value=mock_conn),
        patch("backend.src.chat.handler.process_turn", return_value=out_of_scope_result),
    ):
        result = lambda_handler(_post_event(body={"message": "irrelevant"}), None)

    body = json.loads(result["body"])
    assert body["gate_evaluated"] is False
