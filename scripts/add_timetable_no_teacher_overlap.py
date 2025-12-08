"""
Add a Postgres exclusion constraint to prevent a teacher being assigned to overlapping timetable slots
(across different streams/classes) at the same day/time.

This script is idempotent and safe to run multiple times. It requires that
- The DB is Postgres-compatible (Neon is OK)
- The `timetable_slots` table exists with `start_time` and `end_time` stored as 'HH:MM' text

It will:
- CREATE EXTENSION IF NOT EXISTS btree_gist;
- Add a generated int4range column `time_range` (minutes since midnight) if missing
- Add an exclusion constraint `no_teacher_overlap` that excludes overlapping time ranges
  for the same teacher on the same day_of_week.

Usage:
  python scripts/add_timetable_no_teacher_overlap.py

Make a DB backup or ensure migrations are in source control before running in production.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()


def get_database_url():
    url = os.getenv('NEON_DATABASE_URL') or os.getenv('DATABASE_URL')
    if url:
        return url
    user = os.getenv('NEON_USER') or os.getenv('DB_USER')
    pw = os.getenv('NEON_PASSWORD') or os.getenv('DB_PASSWORD')
    host = os.getenv('NEON_HOST') or os.getenv('DB_HOST')
    port = os.getenv('NEON_PORT') or os.getenv('DB_PORT') or '5432'
    db = os.getenv('NEON_DB') or os.getenv('DB_NAME') or os.getenv('POSTGRES_DB')
    sslmode = os.getenv('NEON_SSLMODE') or os.getenv('DB_SSLMODE') or 'require'
    if not (user and pw and host and db):
        return None
    return f'postgresql://{user}:{pw}@{host}:{port}/{db}?sslmode={sslmode}'


def column_exists(conn, schema, table, column):
    q = text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table AND column_name = :column
    """)
    r = conn.execute(q, {'schema': schema, 'table': table, 'column': column}).fetchone()
    return bool(r)


def constraint_exists(conn, schema, table, constraint_name):
    q = text("""
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = :schema AND table_name = :table AND constraint_name = :cname
    """)
    r = conn.execute(q, {'schema': schema, 'table': table, 'cname': constraint_name}).fetchone()
    return bool(r)


if __name__ == '__main__':
    database_url = get_database_url()
    if not database_url:
        print('No database URL found in environment. Set NEON_DATABASE_URL or DATABASE_URL or NEON_USER etc.')
        exit(2)

    schema = os.getenv('NEON_SCHEMA') or os.getenv('DB_SCHEMA') or 'public'
    table = os.getenv('TIMETABLE_TABLE') or 'timetable_slots'
    time_range_col = 'time_range'
    constraint_name = 'no_teacher_overlap'

    print('Connecting to', database_url.replace(os.getenv('NEON_PASSWORD') or os.getenv('DB_PASSWORD') or '', '***')[:200])

    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.begin() as conn:
            print('Ensuring btree_gist extension...')
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS btree_gist'))

            if not column_exists(conn, schema, table, time_range_col):
                print(f"Adding generated column '{time_range_col}' to {schema}.{table}...")
                # The expression converts 'HH:MM' to integer minutes since midnight
                add_col_sql = text(f"""
                    ALTER TABLE {schema}.{table}
                    ADD COLUMN {time_range_col} int4range
                      GENERATED ALWAYS AS (
                        int4range(
                          (split_part(start_time, ':', 1)::int * 60 + split_part(start_time, ':', 2)::int),
                          (split_part(end_time,   ':', 1)::int * 60 + split_part(end_time,   ':', 2)::int)
                        )
                      ) STORED
                """)
                conn.execute(add_col_sql)
            else:
                print(f"Column '{time_range_col}' already exists; skipping add.")

            if not constraint_exists(conn, schema, table, constraint_name):
                print(f"Adding exclusion constraint '{constraint_name}'...")
                # Exclude overlapping ranges for same teacher on same day_of_week
                add_constraint_sql = text(f"""
                    ALTER TABLE {schema}.{table}
                    ADD CONSTRAINT {constraint_name}
                    EXCLUDE USING gist (
                        teacher_id WITH =,
                        day_of_week WITH =,
                        {time_range_col} WITH &&
                    )
                """)
                conn.execute(add_constraint_sql)
                print('Constraint added.')
            else:
                print(f"Constraint '{constraint_name}' already exists; skipping.")

            print('All done.')
    except SQLAlchemyError as e:
        print('Failed to modify DB:', e)
        exit(1)

