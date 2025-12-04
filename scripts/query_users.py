#!/usr/bin/env python3
"""Query users and roles from the configured DATABASE_URL.

Usage:
  python scripts/query_users.py            # show bursar(s)
  python scripts/query_users.py --all      # list all users + roles
  python scripts/query_users.py --role R   # list users matching role R (case-insensitive)

This script reads DATABASE_URL from .env or environment and uses SQLAlchemy to connect.
"""
import os
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load .env (if present)
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not found in environment. Please set it in your .env or environment variables.")

parser = argparse.ArgumentParser(description="Query users and roles from the database")
parser.add_argument('--all', action='store_true', help='List all users and roles')
parser.add_argument('--role', '-r', type=str, help='Filter by role name (case-insensitive, partial match)')
parser.add_argument('--limit', '-n', type=int, default=100, help='Limit number of rows (default 100)')
args = parser.parse_args()

engine = create_engine(DATABASE_URL)

def query_users(role_filter=None, limit=100):
    sql = text(
        "SELECT u.id AS user_id, u.first_name, u.last_name, u.email, r.role_name "
        "FROM users u LEFT JOIN roles r ON u.role_id = r.id "
    )
    params = {}
    if role_filter:
        sql = text(sql.text + " WHERE lower(r.role_name) LIKE :role")
        params['role'] = f"%{role_filter.lower()}%"
    sql = text(sql.text + " ORDER BY u.id LIMIT :limit")
    params['limit'] = limit

    with engine.connect() as conn:
        try:
            result = conn.execute(sql, params)
            rows = result.fetchall()
            return rows
        except SQLAlchemyError as e:
            raise

if __name__ == '__main__':
    role_filter = None
    if args.all:
        role_filter = None
    elif args.role:
        role_filter = args.role
    else:
        # default: show bursar roles
        role_filter = 'bursar'

    try:
        rows = query_users(role_filter=role_filter, limit=args.limit)
    except Exception as e:
        print(f"Error querying database: {e}")
        raise SystemExit(1)

    if not rows:
        print('No users found matching the criteria.')
        raise SystemExit(0)

    # Print table
    print(f"Found {len(rows)} user(s):\n")
    # compute column widths
    cols = ['user_id', 'first_name', 'last_name', 'email', 'role_name']
    col_widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            val = str(getattr(r, c) if getattr(r, c) is not None else '')
            col_widths[c] = max(col_widths[c], len(val))

    sep = ' | '
    header = sep.join(c.ljust(col_widths[c]) for c in cols)
    print(header)
    print('-' * len(header))
    for r in rows:
        line = sep.join((str(getattr(r, c) if getattr(r, c) is not None else '')).ljust(col_widths[c]) for c in cols)
        print(line)

    print('\nTip: run with --all to list all users or --role "admin" to filter by role name.')
