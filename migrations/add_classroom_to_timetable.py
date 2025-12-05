"""
Migration script to add classroom column to timetable_slots table.
Run this after updating the TimeTableSlot model.
"""

from app import app, db
from models.timetable_model import TimeTableSlot
import sqlalchemy as sa

def migrate_add_classroom():
    """Add classroom column to timetable_slots table if it doesn't exist."""
    with app.app_context():
        inspector = sa.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('timetable_slots')]
        
        if 'classroom' not in columns:
            print("Adding 'classroom' column to timetable_slots table...")
            with db.engine.connect() as conn:
                conn.execute(sa.text("""
                    ALTER TABLE timetable_slots
                    ADD COLUMN classroom VARCHAR(50) NULL
                """))
                conn.commit()
            print("✓ 'classroom' column added successfully!")
        else:
            print("✓ 'classroom' column already exists.")

if __name__ == '__main__':
    migrate_add_classroom()
