#!/usr/bin/env python
"""Delete P2-P7 slots and regenerate with corrected constraint."""

from app import app, db
from models.timetable_model import TimeTableSlot
from models.class_model import Class
from models.stream_model import Stream
from routes.admin_routes import _generate_timetable_core

app.app_context().push()

# Delete P2-P7 slots
print("Deleting P2-P7 timetable slots...")
p2_to_p7 = db.session.query(Class).filter(Class.id > 1).all()
for c in p2_to_p7:
    deleted = db.session.query(TimeTableSlot).filter_by(class_id=c.id).delete()
    db.session.commit()
    print(f"  Deleted {deleted} slots for {c.name}")

print("\nRegenerating P2-P7 with corrected constraint...\n")
streams = Stream.query.all()

success_count = 0
for c in p2_to_p7:
    for s in streams:
        success, result = _generate_timetable_core(c.id, s.id)
        if success:
            print(f"✓ {c.name}-{s.name}: {result['slots_created']} slots")
            success_count += 1
        else:
            print(f"✗ {c.name}-{s.name}: {result}")

total = db.session.query(TimeTableSlot).count()
print(f"\n{'='*60}")
print(f"✓ Regeneration complete!")
print(f"Successfully generated: {success_count} class-stream timetables")
print(f"Total timetable slots in DB: {total}")
print(f"{'='*60}")
