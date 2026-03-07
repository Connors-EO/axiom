import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import boto3
from dotenv import load_dotenv
from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

from backend.src.turn.context import ContextPacket
from backend.src.turn.state import EngagementState

load_dotenv()

# Module-level Bedrock client — tests can wrap this with botocore.stub.Stubber
_bedrock_client: BedrockRuntimeClient = boto3.Session(
    profile_name=os.environ.get("AWS_PROFILE"),
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
).client("bedrock-runtime")

_AXIOM_META_PATTERN = re.compile(
    r"\s*<axiom_meta>\s*(.*?)\s*</axiom_meta>",
    re.DOTALL,
)

_AXIOM_META_INSTRUCTION = (
    "\n\nAt the end of every response, include an <axiom_meta> block containing "
    "a JSON object with exactly these two fields:\n"
    '  "intent_classified": one of scope_question | gate_request | phase_advance | '
    "clarification | artifact_request | lesson_capture | off_topic\n"
    '  "scope_check": one of PASS | WARN | FAIL\n\n'
    "Example:\n"
    "<axiom_meta>\n"
    '{"intent_classified": "scope_question", "scope_check": "PASS"}\n'
    "</axiom_meta>"
)


@dataclass
class BedrockResponse:
    response_text: str
    intent_classified: str
    scope_check: str
    output_tokens: int
    model_latency_ms: int
    raw_response: dict[str, Any]


def _parse_axiom_meta(text: str) -> tuple[str, str, str]:
    """Return (cleaned_text, intent_classified, scope_check).

    Falls back to ('clarification', 'WARN') if block is missing or unparseable.
    """
    match = _AXIOM_META_PATTERN.search(text)
    if match is None:
        return text, "clarification", "WARN"

    cleaned_text = _AXIOM_META_PATTERN.sub("", text).strip()
    raw_json = match.group(1)
    try:
        meta = json.loads(raw_json)
        intent = str(meta.get("intent_classified", "clarification"))
        scope = str(meta.get("scope_check", "WARN"))
        return cleaned_text, intent, scope
    except (json.JSONDecodeError, AttributeError):
        return cleaned_text, "clarification", "WARN"


def call_bedrock(packet: ContextPacket, state: EngagementState) -> BedrockResponse:
    """Invoke Bedrock with the assembled context packet.

    Returns BedrockResponse with intent classification and scope check extracted
    from the <axiom_meta> block embedded in the model's response.
    """
    augmented_system = packet.system_prompt + _AXIOM_META_INSTRUCTION

    messages: list[dict[str, Any]] = list(packet.conversation_history)
    messages.append({"role": "user", "content": packet.current_message})

    payload: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "system": augmented_system,
        "messages": messages,
    }

    t0 = time.monotonic()
    raw = _bedrock_client.invoke_model(
        modelId=state.model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    body: dict[str, Any] = json.loads(raw["body"].read())
    raw_text: str = body["content"][0]["text"]
    output_tokens: int = int(body.get("usage", {}).get("output_tokens", 0))

    response_text, intent_classified, scope_check = _parse_axiom_meta(raw_text)

    return BedrockResponse(
        response_text=response_text,
        intent_classified=intent_classified,
        scope_check=scope_check,
        output_tokens=output_tokens,
        model_latency_ms=latency_ms,
        raw_response=body,
    )
