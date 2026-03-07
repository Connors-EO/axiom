import io
import json
from unittest.mock import ANY
from uuid import UUID

import pytest
from botocore.stub import Stubber

import backend.src.turn.bedrock as bedrock_module
from backend.src.turn.bedrock import BedrockResponse, call_bedrock
from backend.src.turn.context import ContextPacket
from backend.src.turn.state import EngagementState

ENGAGEMENT_ID = UUID("a0000000-0000-0000-0000-000000000001")
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

VALID_INTENTS = (
    "scope_question",
    "gate_request",
    "phase_advance",
    "clarification",
    "artifact_request",
    "lesson_capture",
    "off_topic",
)


def _make_state(model_id: str = MODEL_ID) -> EngagementState:
    return EngagementState(
        engagement_id=ENGAGEMENT_ID,
        tenant_id="test",
        model_id=model_id,
        current_phase="RESEARCH_DISCOVERY",
        domain_tags=["cloud-platform"],
        phase_context={},
        flags={},
        turn_number=4,
    )


def _make_packet(current_message: str = "Tell me about cloud.") -> ContextPacket:
    return ContextPacket(
        system_prompt="You are Axiom.",
        playbook_xml="<playbook id='cloud-001'>content</playbook>",
        phase_summaries="",
        conversation_history=[{"role": "user", "content": "Prior message."}],
        current_message=current_message,
    )


def _make_stub_response(text: str, output_tokens: int = 42) -> dict:  # type: ignore[type-arg]
    body = json.dumps(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "model": MODEL_ID,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": output_tokens},
        }
    ).encode()
    return {
        "body": io.BytesIO(body),
        "contentType": "application/json",
        "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "test-req"},
    }


_EXPECTED_PARAMS = {
    "modelId": MODEL_ID,
    "contentType": "application/json",
    "accept": "application/json",
    "body": ANY,
}


def test_happy_path_returns_bedrock_response() -> None:
    response_text = 'Hello from Axiom.\n<axiom_meta>\n{"intent_classified": "scope_question", "scope_check": "PASS"}\n</axiom_meta>'

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert isinstance(result, BedrockResponse)
    assert result.intent_classified == "scope_question"
    assert result.scope_check == "PASS"
    assert result.output_tokens == 42


def test_axiom_meta_stripped_from_response_text() -> None:
    response_text = 'Hello.\n<axiom_meta>\n{"intent_classified": "clarification", "scope_check": "WARN"}\n</axiom_meta>'

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert "<axiom_meta>" not in result.response_text
    assert "</axiom_meta>" not in result.response_text
    assert "Hello." in result.response_text


def test_missing_axiom_meta_degrades_gracefully() -> None:
    response_text = "Hello, I can help with that."

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert result.intent_classified == "clarification"
    assert result.scope_check == "WARN"
    assert result.response_text == response_text


def test_malformed_json_in_axiom_meta_degrades_gracefully() -> None:
    response_text = "Response.\n<axiom_meta>\n{not valid json\n</axiom_meta>"

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert result.intent_classified == "clarification"
    assert result.scope_check == "WARN"


@pytest.mark.parametrize("intent", VALID_INTENTS)
def test_all_seven_intent_values_accepted(intent: str) -> None:
    response_text = f'Response.\n<axiom_meta>\n{{"intent_classified": "{intent}", "scope_check": "PASS"}}\n</axiom_meta>'

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert result.intent_classified == intent


def test_output_tokens_populated_from_response() -> None:
    response_text = 'Resp.\n<axiom_meta>\n{"intent_classified": "clarification", "scope_check": "PASS"}\n</axiom_meta>'

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text, output_tokens=77), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert result.output_tokens == 77


def test_model_latency_ms_is_measured() -> None:
    response_text = 'Resp.\n<axiom_meta>\n{"intent_classified": "clarification", "scope_check": "PASS"}\n</axiom_meta>'

    with Stubber(bedrock_module._bedrock_client) as stubber:
        stubber.add_response("invoke_model", _make_stub_response(response_text), _EXPECTED_PARAMS)
        result = call_bedrock(_make_packet(), _make_state())

    assert result.model_latency_ms >= 0
