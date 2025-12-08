import os
from sqlalchemy import create_engine, inspect

db_url = os.getenv('DATABASE_URL')
print('DATABASE_URL present:', bool(db_url))
if not db_url:
    print('No DATABASE_URL found in environment; aborting schema inspect')
else:
    eng = create_engine(db_url)
    insp = inspect(eng)
    tables = insp.get_table_names()
    print('Tables found (count):', len(tables))
    for t in ['staff_attendance','salary_history','staff_profiles']:
        if t in tables:
            cols = [c['name'] for c in insp.get_columns(t)]
            print(f"Table {t} exists; columns: {cols}")
        else:
            print(f"Table {t} does NOT exist")
