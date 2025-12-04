"""Small helper to add the `quantity` column to expense_records if it doesn't exist.

Run this from the project root (in the same venv) when the app is stopped:

powershell
python scripts\add_quantity_column.py

It reads DATABASE_URL from the environment. If you don't have one, set it first.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# load .env so DATABASE_URL is available when running locally
load_dotenv()


def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL environment variable not set.')
        print('Set it (e.g., export DATABASE_URL="postgresql://...") and re-run.')
        sys.exit(1)

    engine = create_engine(database_url)
    sql = "ALTER TABLE expense_records ADD COLUMN IF NOT EXISTS quantity integer;"
    print('Connecting to database...')
    with engine.begin() as conn:
        print('Adding column `quantity` to expense_records (if missing)...')
        conn.execute(text(sql))
        print('Done. Column ensured.')


if __name__ == '__main__':
    main()
