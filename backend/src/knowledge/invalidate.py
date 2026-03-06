import psycopg2.extensions


def invalidate_paths(
    paths: list[str],
    conn: psycopg2.extensions.connection,
) -> int:
    """Mark knowledge_cache rows stale for all sources matching the given paths.

    paths: list of retrieval_config->>'path' values from a webhook payload.
    Returns the number of cache rows updated.
    """
    if not paths:
        return 0

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM knowledge_sources
            WHERE retrieval_config->>'path' = ANY(%s)
            """,
            (paths,),
        )
        rows = cur.fetchall()

    if not rows:
        return 0

    source_ids = [row[0] for row in rows]

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE knowledge_cache
            SET is_stale = true,
                updated_at = NOW()
            WHERE source_id = ANY(%s)
            """,
            (source_ids,),
        )
        return cur.rowcount
