import os
import json
import glob
import logging
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/load_to_postgres.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("load_to_postgres")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medical_warehouse")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres_password")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=int(DB_PORT),
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def setup_database(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.telegram_messages (
                message_id      TEXT,
                channel_name    TEXT,
                message_date    TIMESTAMPTZ,
                message_text    TEXT,
                has_media       BOOLEAN,
                image_path      TEXT,
                views           INTEGER,
                forwards        INTEGER,
                scraped_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (message_id, channel_name)
            );
        """)
        conn.commit()
    logger.info("Schema and raw.telegram_messages table ensured.")


def load_json_files(conn):
    pattern = os.path.join("data", "raw", "telegram_messages", "**", "*.json")
    json_files = glob.glob(pattern, recursive=True)
    if not json_files:
        logger.warning("No JSON files found in data lake. Run scraper first.")
        return
    total_inserted = 0
    for filepath in json_files:
        logger.info(f"Processing: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            records = json.load(f)
        rows = []
        for r in records:
            rows.append((
                r.get("message_id"),
                r.get("channel_name"),
                r.get("message_date"),
                r.get("message_text"),
                r.get("has_media", False),
                r.get("image_path"),
                r.get("views", 0),
                r.get("forwards", 0)
            ))
        if rows:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO raw.telegram_messages
                        (message_id, channel_name, message_date, message_text,
                         has_media, image_path, views, forwards)
                    VALUES %s
                    ON CONFLICT (message_id, channel_name) DO NOTHING
                    """,
                    rows
                )
            conn.commit()
            total_inserted += len(rows)
            logger.info(f"Inserted {len(rows)} rows from {filepath}")
    logger.info(f"Done. Total rows processed: {total_inserted}")


def main():
    try:
        conn = get_connection()
        logger.info("Connected to PostgreSQL successfully.")
        setup_database(conn)
        load_json_files(conn)
        conn.close()
    except Exception as e:
        logger.error(f"Failed to connect or load data: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
