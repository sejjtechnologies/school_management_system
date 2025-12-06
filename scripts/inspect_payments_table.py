"""
Inspect the `payments` table structure using DATABASE_URL from .env.
Usage: python scripts/inspect_payments_table.py

The script will:
- load .env from project root
- connect to the database using SQLAlchemy
- list columns for table 'payments' (information_schema)
- show a few sample rows (LIMIT 5)

Designed to run locally within the project's venv.
"""
import os
import sys
import traceback
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    print("ERROR: DATABASE_URL not found in environment. Please create a .env file with DATABASE_URL.")
    sys.exit(1)

print("Using DATABASE_URL (masked):", DB_URL[:50] + '...' if len(DB_URL) > 50 else DB_URL)

try:
    # Create engine with pool_pre_ping to avoid stale/SSL issues
    engine = create_engine(DB_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        print("\nQuerying information_schema for 'payments' table columns...\n")
        sql = text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'payments'
            ORDER BY ordinal_position
        """)
        res = conn.execute(sql)
        rows = res.fetchall()
        if not rows:
            print("No columns found for table 'payments'. The table may not exist or the schema name differs (e.g., public.payments).\n")
        else:
            print(f"Found {len(rows)} columns for 'payments':\n")
            for r in rows:
                print(f"- {r.column_name} | {r.data_type} | nullable={r.is_nullable} | default={r.column_default}")

        print("\nAttempting to fetch up to 5 rows from payments for inspection...\n")
        try:
            sample = conn.execute(text("SELECT * FROM payments LIMIT 5"))
            cols = sample.keys()
            sample_rows = sample.fetchall()
            if not sample_rows:
                print("No rows returned from payments (table may be empty).\n")
            else:
                print("Columns:", ', '.join(cols))
                for row in sample_rows:
                    # Print as dict for readability
                    print(dict(zip(cols, row)))
        except Exception as e:
            print("Could not SELECT from payments:", str(e))
            # Print minimal traceback
            traceback.print_exc()

except Exception as e:
    print("Error connecting or querying the database:", str(e))
    traceback.print_exc()
    sys.exit(1)

print("\nInspection complete.")
