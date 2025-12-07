"""
Connect to Postgres (Neon) using credentials from .env and print the structure of the `expense_items` table.
This script uses python-dotenv to load .env and psycopg2 to connect.

It will look for a DATABASE_URL in .env first, otherwise use individual DB_* vars.

Usage: python check_expense_items_structure.py
"""
import os
import sys
from urllib.parse import urlparse, parse_qs

try:
    from dotenv import load_dotenv
except Exception:
    print('Missing dependency: python-dotenv. Please install with: pip install python-dotenv')
    sys.exit(1)

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_SSLMODE = os.getenv('DB_SSLMODE', 'require')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'public')

conn_info = None
if DATABASE_URL:
    # Parse DATABASE_URL
    parsed = urlparse(DATABASE_URL)
    params = parse_qs(parsed.query)
    dbname = parsed.path.lstrip('/') or None
    conn_info = {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'dbname': dbname,
        'user': parsed.username,
        'password': parsed.password,
        'sslmode': params.get('sslmode', [DB_SSLMODE])[0]
    }
else:
    if not (DB_HOST and DB_NAME and DB_USER and DB_PASSWORD):
        print('Database credentials not found in environment. Set DATABASE_URL or DB_HOST/DB_NAME/DB_USER/DB_PASSWORD in .env')
        sys.exit(1)
    conn_info = {
        'host': DB_HOST,
        'port': DB_PORT,
        'dbname': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'sslmode': DB_SSLMODE
    }

print('Connecting using:')
print('  host:', conn_info.get('host'))
print('  port:', conn_info.get('port'))
print('  dbname:', conn_info.get('dbname'))
print('  user:', conn_info.get('user'))
print('  sslmode:', conn_info.get('sslmode'))

try:
    import psycopg2
except Exception:
    print('Missing dependency: psycopg2-binary. Please install with: pip install psycopg2-binary')
    sys.exit(1)

try:
    conn = psycopg2.connect(**conn_info)
except Exception as e:
    print('Failed to connect to the database:')
    print(e)
    sys.exit(1)

try:
    cur = conn.cursor()
    # Check if table exists
    cur.execute("""
      SELECT table_schema, table_name
      FROM information_schema.tables
      WHERE table_schema = %s AND table_name = %s
    """, (DB_SCHEMA, 'expense_items'))
    if cur.rowcount == 0:
        print(f"Table '{DB_SCHEMA}.expense_items' does not exist.")
        sys.exit(0)

    # Fetch columns
    cur.execute("""
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns
      WHERE table_schema = %s AND table_name = %s
      ORDER BY ordinal_position
    """, (DB_SCHEMA, 'expense_items'))
    rows = cur.fetchall()
    if not rows:
        print(f"No columns found for table {DB_SCHEMA}.expense_items")
    else:
        print(f"Structure of table {DB_SCHEMA}.expense_items:")
        max_col = max(len(r[0]) for r in rows)
        print(f"{'Column'.ljust(max_col)} | Type | Nullable | Default")
        print('-' * (max_col + 40))
        for col_name, data_type, is_nullable, column_default in rows:
            print(f"{col_name.ljust(max_col)} | {data_type} | {is_nullable} | {column_default}")
finally:
    try:
        cur.close()
    except Exception:
        pass
    conn.close()
