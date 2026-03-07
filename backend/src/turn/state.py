from dataclasses import dataclass
from uuid import UUID

import psycopg2.extensions


class EngagementNotFoundError(Exception):
    pass


@dataclass
class EngagementState:
    engagement_id: UUID
    tenant_id: str
    model_id: str
    current_phase: str
    domain_tags: list[str]
    phase_context: dict[str, object]
    flags: dict[str, object]
    turn_number: int


def read_engagement_state(
    engagement_id: UUID,
    conn: psycopg2.extensions.connection,
) -> EngagementState:
    """Return EngagementState for the given engagement_id.

    Raises EngagementNotFoundError if no row exists.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tenant_id, model_id, current_phase, domain_tags,
                   phase_context, flags
            FROM engagements
            WHERE id = %s
            """,
            (str(engagement_id),),
        )
        row = cur.fetchone()

    if row is None:
        raise EngagementNotFoundError(f"No engagement found with id={engagement_id}")

    tenant_id, model_id, current_phase, domain_tags, phase_context, flags = row

    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*)::int FROM messages WHERE engagement_id = %s",
            (str(engagement_id),),
        )
        count_row = cur.fetchone()

    turn_number = (count_row[0] if count_row is not None else 0) + 1

    return EngagementState(
        engagement_id=engagement_id,
        tenant_id=str(tenant_id),
        model_id=str(model_id) if model_id is not None else "",
        current_phase=str(current_phase),
        domain_tags=list(domain_tags) if domain_tags is not None else [],
        phase_context=dict(phase_context) if phase_context is not None else {},
        flags=dict(flags) if flags is not None else {},
        turn_number=turn_number,
    )
