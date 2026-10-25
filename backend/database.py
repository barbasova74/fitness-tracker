
import os
import psycopg
from psycopg.rows import dict_row


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "fitness"),
        user=os.getenv("DB_USER", "fitness"),
        password=os.environ["DB_PASSWORD"],
        row_factory=dict_row
    )
