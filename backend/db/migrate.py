import os
import pathlib

from backend.src.db.client import get_connection


def _bootstrap_migrations_table(conn: object) -> None:
    import psycopg2.extensions
    c: psycopg2.extensions.connection = conn  # type: ignore[assignment]
    with c.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    c.commit()


def _applied_migrations(conn: object) -> set[str]:
    import psycopg2.extensions
    c: psycopg2.extensions.connection = conn  # type: ignore[assignment]
    with c.cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def run_migrations() -> None:
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    conn = get_connection()
    try:
        _bootstrap_migrations_table(conn)
        applied = _applied_migrations(conn)
        for sql_file in sql_files:
            if sql_file.name in applied:
                print(f"Skipping {sql_file.name} (already applied)")
                continue
            print(f"Applying {sql_file.name}...")
            sql = sql_file.read_text()
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (sql_file.name,),
                )
            conn.commit()
            print(f"Applied {sql_file.name}")
    finally:
        conn.close()


def main() -> None:
    run_migrations()
    print("Migrations complete.")


if __name__ == "__main__":
    main()
