#!/usr/bin/env python
"""Drop old constraint and recreate timetable_slots table with corrected unique constraint."""

from app import app, db
from sqlalchemy import text

app.app_context().push()

print("Dropping old constraint and recreating table...")

try:
    # Drop the old constraint
    with db.engine.connect() as conn:
        conn.execute(text("ALTER TABLE timetable_slots DROP CONSTRAINT IF EXISTS unique_teacher_stream_slot"))
        conn.commit()
        print("✓ Dropped old constraint")
    
    # Create new constraint
    with db.engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE timetable_slots ADD CONSTRAINT unique_teacher_class_slot "
            "UNIQUE (teacher_id, class_id, stream_id, day_of_week, start_time)"
        ))
        conn.commit()
        print("✓ Created new constraint with class_id included")
    
    print("\n✓ Table structure updated successfully!")
    print("Now timetables can be generated for all classes without conflicts.")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
