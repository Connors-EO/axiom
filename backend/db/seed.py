import pathlib

from backend.src.db.client import get_connection


def run_seeds() -> None:
    seeds_dir = pathlib.Path(__file__).parent / "seeds"
    sql_files = sorted(seeds_dir.glob("*.sql"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET app.tenant_id = 'everops'")
        for sql_file in sql_files:
            print(f"Seeding {sql_file.name}...")
            sql = sql_file.read_text()
            with conn.cursor() as cur:
                cur.execute(sql)
        conn.commit()
        print("Seeds complete.")
    finally:
        conn.close()


def main() -> None:
    run_seeds()


if __name__ == "__main__":
    main()
