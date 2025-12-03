#!/usr/bin/env python
"""Recreate timetable_slots table with new constraints"""

import sys
print("1. Importing app...", file=sys.stderr, flush=True)

from app import app
from models.user_models import db

print("2. App imported successfully", file=sys.stderr, flush=True)

from sqlalchemy import text, inspect

print("3. Starting app context...", file=sys.stderr, flush=True)

with app.app_context():
    print("4. Inside app context", file=sys.stderr, flush=True)
    
    # Check if table exists
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if 'timetable_slots' in tables:
        print("5. Dropping timetable_slots...", file=sys.stderr, flush=True)
        db.session.execute(text('DROP TABLE IF EXISTS timetable_slots CASCADE'))
        db.session.commit()
        print("✅ Old table dropped", file=sys.stderr, flush=True)
    
    print("6. Creating all tables...", file=sys.stderr, flush=True)
    db.create_all()
    print("✅ Tables created", file=sys.stderr, flush=True)
    
    # Verify the new constraint
    print("7. Verifying constraints...", file=sys.stderr, flush=True)
    if 'timetable_slots' in inspect(db.engine).get_table_names():
        table_constraints = inspector.get_unique_constraints('timetable_slots')
        for constraint in table_constraints:
            print(f"   - {constraint['name']}: {constraint['column_names']}", file=sys.stderr, flush=True)
    
    print("\n✅ SUCCESS! Timetable table recreated with new constraints!", file=sys.stderr, flush=True)

print("Script finished!")

