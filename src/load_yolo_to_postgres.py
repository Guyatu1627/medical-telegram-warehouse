import os
import csv
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
        logging.FileHandler("logs/load_yolo.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("load_yolo")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medical_warehouse")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres_password")
CSV_PATH = os.path.join("data", "yolo_detections.csv")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=int(DB_PORT),
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def setup_table(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.yolo_detections (
                message_id          TEXT NOT NULL,
                channel_name        TEXT NOT NULL,
                image_path          TEXT,
                detected_class      TEXT,
                confidence_score    FLOAT,
                image_category      TEXT,
                loaded_at           TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
    logger.info("Table raw.yolo_detections ensured.")


def load_csv(conn):
    if not os.path.exists(CSV_PATH):
        logger.error(f"CSV file not found at {CSV_PATH}. Run yolo_detect.py first.")
        sys.exit(1)

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((
                row["message_id"],
                row["channel_name"],
                row["image_path"],
                row["detected_class"],
                float(row["confidence_score"]),
                row["image_category"]
            ))

    with conn.cursor() as cur:
        # Clear existing data and reload (idempotent)
        cur.execute("TRUNCATE TABLE raw.yolo_detections;")
        execute_values(
            cur,
            """
            INSERT INTO raw.yolo_detections
                (message_id, channel_name, image_path, detected_class, confidence_score, image_category)
            VALUES %s
            """,
            rows
        )
    conn.commit()
    logger.info(f"Loaded {len(rows)} YOLO detection rows into raw.yolo_detections")


def main():
    try:
        conn = get_connection()
        logger.info("Connected to PostgreSQL.")
        setup_table(conn)
        load_csv(conn)
        conn.close()
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
