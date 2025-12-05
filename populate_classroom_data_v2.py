"""
Script to populate classroom data for primary school timetable.
Assigns realistic classroom numbers to timetable slots based on class/stream.
Optimized version with batch processing and progress tracking.
"""

from app import app, db
from models.timetable_model import TimeTableSlot
from models.class_model import Class
from models.stream_model import Stream

def populate_classroom_data():
    """Populate classroom field with realistic primary school room assignments."""
    with app.app_context():
        print("Populating classroom data for primary school...")
        
        # Define room mapping for primary school classes
        room_mapping = {
            # Primary Classes (Forms)
            'Form 1': {
                'A': 'Room 101',
                'B': 'Room 102',
                'C': 'Room 103',
            },
            'Form 2': {
                'A': 'Room 201',
                'B': 'Room 202',
                'C': 'Room 203',
            },
            'Form 3': {
                'A': 'Room 301',
                'B': 'Room 302',
                'C': 'Room 303',
            },
            'Form 4': {
                'A': 'Room 401',
                'B': 'Room 402',
                'C': 'Room 403',
            },
            'Form 5': {
                'A': 'Room 501',
                'B': 'Room 502',
                'C': 'Room 503',
            },
            'Form 6': {
                'A': 'Room 601',
                'B': 'Room 602',
                'C': 'Room 603',
            },
        }
        
        # Get all timetable slots without classroom assignments
        slots = TimeTableSlot.query.filter(
            (TimeTableSlot.classroom == None) | (TimeTableSlot.classroom == '')
        ).all()
        
        print(f"Found {len(slots)} slots to update...")
        
        updated_count = 0
        skipped_count = 0
        batch_size = 100
        
        for idx, slot in enumerate(slots):
            try:
                # Get class name and stream name
                class_name = slot.class_.name if slot.class_ else None
                stream_name = slot.stream.name if slot.stream else None
                
                if not class_name or not stream_name:
                    skipped_count += 1
                    continue
                
                # Look up classroom from mapping
                classroom = None
                if class_name in room_mapping:
                    if stream_name in room_mapping[class_name]:
                        classroom = room_mapping[class_name][stream_name]
                
                # If not found in mapping, use default naming
                if not classroom:
                    classroom = f"{class_name} {stream_name}"
                
                # Update slot
                slot.classroom = classroom
                updated_count += 1
                
                # Batch commit every 100 slots
                if (idx + 1) % batch_size == 0:
                    db.session.commit()
                    print(f"  ✓ Committed {updated_count} updates ({idx + 1}/{len(slots)})")
                
            except Exception as e:
                print(f"  ✗ Error processing slot {slot.id}: {e}")
                skipped_count += 1
                continue
        
        # Final commit
        db.session.commit()
        print(f"\n✓ Completed!")
        print(f"  Updated: {updated_count} slots")
        print(f"  Skipped: {skipped_count} slots")

if __name__ == '__main__':
    populate_classroom_data()
