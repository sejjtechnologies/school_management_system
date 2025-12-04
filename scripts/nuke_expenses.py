"""Nuclear option: Connect to Neon DB using .env and DELETE ALL expense records.

WARNING: This will permanently delete all expense_records and expense_items.
Use only if you want a completely clean slate.

Run from repo root in venv:
    python scripts\nuke_expenses.py

It reads DATABASE_URL from .env and uses raw SQL for speed.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env so DATABASE_URL is available
load_dotenv()


def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL environment variable not set.')
        print('Set it in .env or environment and re-run.')
        sys.exit(1)

    engine = create_engine(database_url)
    
    print('⚠️  WARNING: This will DELETE ALL expense records and items from the database.')
    confirm = input('Type "YES" to confirm deletion: ')
    
    if confirm != 'YES':
        print('Cancelled. No data deleted.')
        sys.exit(0)
    
    print('\nConnecting to Neon database...')
    try:
        with engine.begin() as conn:
            print('Deleting all expense_records...')
            conn.execute(text("DELETE FROM expense_records;"))
            print('✓ All expense_records deleted.')
            
            print('Deleting all expense_items...')
            conn.execute(text("DELETE FROM expense_items;"))
            print('✓ All expense_items deleted.')
            
            print('\n✅ Done. Database cleaned.')
    except Exception as e:
        print(f'❌ Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
