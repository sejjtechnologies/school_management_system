#!/usr/bin/env python
"""Verify timetable regeneration completed."""
import sys
import time

print("Starting verification...", flush=True)
time.sleep(1)

try:
    from app import app, db
    from models.timetable_model import TimeTableSlot
    from models.user_models import User
    
    print("✓ Database imports successful", flush=True)
    
    app.app_context().push()
    print("✓ App context pushed", flush=True)
    
    # Check slots count
    slot_count = db.session.query(TimeTableSlot).count()
    print(f"\n✓ Total timetable slots: {slot_count}", flush=True)
    
    if slot_count == 0:
        print("⚠ WARNING: No timetable slots found!", flush=True)
        sys.exit(1)
    
    # Sample a few teachers
    sample_slots = db.session.query(TimeTableSlot).limit(5).all()
    print(f"\nSample teachers in slots:", flush=True)
    for slot in sample_slots:
        teacher = User.query.get(slot.teacher_id)
        if teacher:
            email_type = "real" if "@example.local" not in teacher.email else "auto"
            print(f"  - ID {slot.teacher_id}: {teacher.first_name} {teacher.last_name} ({email_type})", flush=True)
    
    print("\n✓ Verification complete!", flush=True)
    
except Exception as e:
    print(f"\n✗ Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
