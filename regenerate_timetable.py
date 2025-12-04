#!/usr/bin/env python
"""Regenerate timetable slots with corrected teacher filter (excludes auto-created teachers)."""

from app import app, db
from models.timetable_model import TimeTableSlot
from models.class_model import Class
from models.stream_model import Stream
from routes.admin_routes import _generate_timetable_core

app.app_context().push()

# Delete all existing slots
print("Deleting old timetable slots...")
deleted = db.session.query(TimeTableSlot).delete()
db.session.commit()
print(f"✓ Deleted {deleted} old timetable slots\n")

# Regenerate with corrected teacher filter
print("Regenerating timetables with real teachers (excluding auto-created)...\n")
classes = Class.query.all()
streams = Stream.query.all()

success_count = 0
for c in classes:
    for s in streams:
        success, result = _generate_timetable_core(c.id, s.id)
        if success:
            print(f"✓ {c.name}-{s.name}: {result['slots_created']} slots")
            success_count += 1
        else:
            print(f"✗ {c.name}-{s.name}: {result}")

# Verify
total = db.session.query(TimeTableSlot).count()
print(f"\n{'='*60}")
print(f"Regeneration complete!")
print(f"Successfully generated: {success_count} class-stream timetables")
print(f"Total timetable slots in DB: {total}")
print(f"{'='*60}")
