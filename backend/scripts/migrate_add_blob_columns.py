"""
Simple migration script to add `image_data` to `jobs` and `heatmap_data` to `model_results`.

Run from the `backend` folder with:

  python scripts/migrate_add_blob_columns.py

The script reads `DATABASE_URL` from `app.config` (and therefore `.env`).
It works for PostgreSQL and SQLite.
"""
import sys
import os
import logging
from sqlalchemy import inspect, text

# Ensure backend folder is on sys.path so `import app` works when running from
# `backend` or `backend/scripts` regardless of current working directory.
HERE = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

logging.basicConfig(level=logging.INFO, format="[migrate] %(message)s")

def main():
    # Ensure we can import app package when running from backend/ or repo root
    try:
        from app.config import DATABASE_URL
        from app.database import engine
    except Exception as e:
        logging.error("Failed to import app modules: %s", e)
        logging.error("Run this script from the `backend` folder (python scripts/migrate_add_blob_columns.py)")
        sys.exit(1)

    insp = inspect(engine)

    # Check jobs table
    jobs_cols = [c['name'] for c in insp.get_columns('jobs')]
    results_cols = [c['name'] for c in insp.get_columns('model_results')]

    with engine.connect() as conn:
        # PostgreSQL uses BYTEA, SQLite uses BLOB
        dialect = engine.dialect.name
        if 'image_data' not in jobs_cols:
            if dialect.startswith('postgres'):
                sql = "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS image_data BYTEA"
            else:
                sql = "ALTER TABLE jobs ADD COLUMN image_data BLOB"
            logging.info("Adding column `image_data` to `jobs` using SQL: %s", sql)
            try:
                conn.execute(text(sql))
                logging.info("Added `jobs.image_data`")
            except Exception as e:
                logging.error("Failed to add jobs.image_data: %s", e)

        else:
            logging.info("Column `jobs.image_data` already exists — skipping")

        if 'heatmap_data' not in results_cols:
            if dialect.startswith('postgres'):
                sql = "ALTER TABLE model_results ADD COLUMN IF NOT EXISTS heatmap_data BYTEA"
            else:
                sql = "ALTER TABLE model_results ADD COLUMN heatmap_data BLOB"
            logging.info("Adding column `heatmap_data` to `model_results` using SQL: %s", sql)
            try:
                conn.execute(text(sql))
                logging.info("Added `model_results.heatmap_data`")
            except Exception as e:
                logging.error("Failed to add model_results.heatmap_data: %s", e)
        else:
            logging.info("Column `model_results.heatmap_data` already exists — skipping")

    logging.info("Migration complete. Restart the backend to pick up changes.")


if __name__ == '__main__':
    main()
