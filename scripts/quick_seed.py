#!/usr/bin/env python3
"""Quick seed script - insert 210 expense records using raw SQL for speed."""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from sqlalchemy import text, create_engine
from sqlalchemy.pool import NullPool

# Use raw engine for faster inserts (no ORM overhead)
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url, poolclass=NullPool, echo=False)

def quick_seed():
    """Insert 210 sample records using raw SQL."""
    with engine.begin() as conn:
        print("[OK] Connected to database.")
        
        # Ensure items table has at least 16 items
        items_to_add = [
            'Textbooks', 'Chairs', 'Desks', 'Whiteboard', 'Markers', 'Projector', 'Printer',
            'Stationery', 'Transport (Fuel)', 'Transport (Repairs)', 'Sports Equipment', 'Uniforms',
            'Cleaning Supplies', 'Computer', 'Router', 'Furniture', 'Stationery Pack'
        ]
        
        for name in items_to_add:
            conn.execute(text("""
                INSERT INTO expense_items (name, description)
                VALUES (:name, :desc)
                ON CONFLICT DO NOTHING
            """), {"name": name, "desc": f"School equipment: {name}"})
        print("[OK] Expense items prepared.")
        
        # Get existing item IDs
        result = conn.execute(text("SELECT id FROM expense_items ORDER BY id LIMIT 16"))
        item_ids = [row[0] for row in result.fetchall()]
        
        if not item_ids:
            print("⚠ No items found. Skipping records.")
            return
        
        print(f"  Using {len(item_ids)} item types for records.")
        
        # Check if we already have records
        count_result = conn.execute(text("SELECT COUNT(*) FROM expense_records"))
        existing = count_result.scalar() or 0
        
        if existing >= 210:
            print(f"[OK] Already have {existing} records. Skipping.")
            return
        
        print(f"[INFO] Inserting {210 - existing} records...")
        
        # Bulk insert via parameterized query
        terms = ['Term 1', 'Term 2', 'Term 3']
        years = [2023, 2024, 2025]
        staff = ['Adegi Dennis', 'Bursar1 Bursar', 'James Smith', 'Mary Johnson', 'Paul Ochieng']
        
        values_list = []
        for i in range(210 - existing):
            item_id = item_ids[i % len(item_ids)]
            amount = float((i + 1) * 5)
            term = terms[i % len(terms)]
            year = years[i % len(years)]
            staff_name = staff[i % len(staff)]
            days_ago = i % 180
            payment_date = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
            
            values_list.append({
                'item_id': item_id,
                'amount': amount,
                'description': f'Sample expense #{i+1}',
                'spent_by': staff_name,
                'payment_date': payment_date,
                'term': term,
                'year': year
            })
        
        # Insert in batches
        batch_size = 50
        for i in range(0, len(values_list), batch_size):
            batch = values_list[i:i+batch_size]
            for val in batch:
                conn.execute(text("""
                    INSERT INTO expense_records (item_id, amount, description, spent_by, payment_date, term, year)
                    VALUES (:item_id, :amount, :description, :spent_by, :payment_date, :term, :year)
                """), val)
            print(f"[INFO] Inserted {i + len(batch)} / {len(values_list)}")
        
        print(f"[OK] Inserted {len(values_list)} new records.")
        
        # Verify counts
        items_count = conn.execute(text("SELECT COUNT(*) FROM expense_items")).scalar()
        records_count = conn.execute(text("SELECT COUNT(*) FROM expense_records")).scalar()
        
        print(f"\n[DONE] Seeding complete!")
        print(f"[STAT] Expense Items: {items_count}")
        print(f"[STAT] Expense Records: {records_count}")

if __name__ == '__main__':
    quick_seed()
