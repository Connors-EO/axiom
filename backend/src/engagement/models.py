from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

VALID_MODEL_IDS: frozenset[str] = frozenset(
    {"us.anthropic.claude-sonnet-4-6", "amazon.nova-pro-v1:0"}
)


@dataclass
class CreateEngagementRequest:
    title: str
    client_name: str
    domain_tags: list[str]
    engagement_type: str
    model_id: str = field(default="us.anthropic.claude-sonnet-4-6")

    def __post_init__(self) -> None:
        if not self.domain_tags:
            raise ValueError("domain_tags must not be empty")
        if self.model_id not in VALID_MODEL_IDS:
            raise ValueError(
                f"model_id must be one of {sorted(VALID_MODEL_IDS)}, got '{self.model_id}'"
            )


@dataclass
class EngagementResponse:
    id: UUID
    title: str
    client_name: str
    engagement_type: str
    current_phase: str
    domain_tags: list[str]
    phase_context: dict[str, object]
    flags: dict[str, object]
    model_id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ListEngagementsResponse:
    engagements: list[EngagementResponse]
    total: int
