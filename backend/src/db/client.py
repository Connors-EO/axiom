import os

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv

load_dotenv()


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5433")),
        dbname=os.environ.get("PGDATABASE", "axiom_dev"),
        user=os.environ.get("PGUSER", "axiom"),
        password=os.environ.get("PGPASSWORD", "axiom"),
    )
