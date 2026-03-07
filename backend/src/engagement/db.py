from typing import Any
from uuid import UUID

import psycopg2.extensions

from backend.src.engagement.models import (
    CreateEngagementRequest,
    EngagementResponse,
    ListEngagementsResponse,
)

_SELECT_COLUMNS = """
    id, title, client_name, engagement_type, current_phase,
    domain_tags, phase_context, flags, model_id, tenant_id,
    created_at, updated_at
"""


def _row_to_response(row: Any) -> EngagementResponse:
    return EngagementResponse(
        id=UUID(str(row[0])),
        title=str(row[1]),
        client_name=str(row[2]),
        engagement_type=str(row[3]),
        current_phase=str(row[4]),
        domain_tags=list(row[5]) if row[5] else [],
        phase_context=dict(row[6]) if row[6] else {},
        flags=dict(row[7]) if row[7] else {},
        model_id=str(row[8]),
        tenant_id=str(row[9]),
        created_at=row[10],
        updated_at=row[11],
    )


def create_engagement(
    req: CreateEngagementRequest,
    tenant_id: str,
    practitioner_id: str,
    conn: psycopg2.extensions.connection,
) -> EngagementResponse:
    with conn.cursor() as cur:
        cur.execute("SET app.tenant_id = %s", (tenant_id,))
        cur.execute(
            f"""
            INSERT INTO engagements
                (title, client_name, engagement_type, domain_tags,
                 model_id, tenant_id, current_phase, phase_context, flags)
            VALUES (%s, %s, %s, %s, %s, %s, 'INTAKE', '{{}}'::jsonb, '{{}}'::jsonb)
            RETURNING {_SELECT_COLUMNS}
            """,
            (
                req.title,
                req.client_name,
                req.engagement_type,
                req.domain_tags,
                req.model_id,
                tenant_id,
            ),
        )
        row = cur.fetchone()
    return _row_to_response(row)


def get_engagement(
    engagement_id: str,
    tenant_id: str,
    conn: psycopg2.extensions.connection,
) -> EngagementResponse | None:
    with conn.cursor() as cur:
        cur.execute("SET app.tenant_id = %s", (tenant_id,))
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} FROM engagements WHERE id = %s",
            (engagement_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_response(row)


def list_engagements(
    tenant_id: str,
    conn: psycopg2.extensions.connection,
) -> ListEngagementsResponse:
    with conn.cursor() as cur:
        cur.execute("SET app.tenant_id = %s", (tenant_id,))
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} FROM engagements ORDER BY created_at DESC",
        )
        rows = cur.fetchall()
    engagements = [_row_to_response(row) for row in rows]
    return ListEngagementsResponse(engagements=engagements, total=len(engagements))
