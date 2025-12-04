#!/usr/bin/env python3
"""Create expenses tables and seed common primary-school equipment/items, plus 200+ sample expense records."""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Ensure we can import from the parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from models.register_pupils import db
from models.expenses_model import ExpenseItem, ExpenseRecord
from app import app

def seed_expenses():
    """Seed expense items and 200+ sample records into the database."""
    with app.app_context():
        # Create tables
        db.create_all()
        print("✓ Tables created/verified.")
        
        # Seed expense items (equipment types) - just add without checking (assume fresh DB)
        items_list = [
            'Textbooks', 'Chairs', 'Desks', 'Whiteboard', 'Markers', 'Projector', 'Printer',
            'Stationery', 'Transport (Fuel)', 'Transport (Repairs)', 'Sports Equipment', 'Uniforms',
            'Cleaning Supplies', 'Computer', 'Router', 'Furniture', 'Stationery Pack'
        ]
        existing_count = ExpenseItem.query.count()
        if existing_count == 0:
            items_to_add = [ExpenseItem(name=name, description=f'School equipment: {name}') for name in items_list]
            db.session.add_all(items_to_add)
            db.session.commit()
            print(f"✓ {len(items_list)} expense item types created.")
        else:
            print(f"✓ {existing_count} expense item types already exist.")
        
        # Seed 200+ sample expense records (varied items, amounts, terms, years)
        records_created = 0
        terms = ['Term 1', 'Term 2', 'Term 3']
        years = [2023, 2024, 2025]
        staff_names = [
            'Adegi Dennis', 'Bursar1 Bursar', 'James Smith', 'Mary Johnson', 'Paul Ochieng'
        ]
        
        # Get all items for random selection
        all_items = ExpenseItem.query.all()
        
        if all_items:
            # Build records efficiently
            existing_count = ExpenseRecord.query.count()
            if existing_count < 210:
                print(f"  → Found {existing_count} existing records, adding more...")
                new_records = []
                
                for i in range(210 - existing_count):
                    item = all_items[i % len(all_items)]
                    amount = float((i + existing_count + 1) * 5)
                    term = terms[i % len(terms)]
                    year = years[i % len(years)]
                    staff = staff_names[i % len(staff_names)]
                    days_ago = (i % 180)
                    payment_date = datetime.utcnow() - timedelta(days=days_ago)
                    
                    rec = ExpenseRecord(
                        item_id=item.id,
                        amount=amount,
                        description=f'Sample expense record #{i+1}: {item.name}',
                        spent_by=staff,
                        payment_date=payment_date,
                        term=term,
                        year=year
                    )
                    new_records.append(rec)
                
                # Insert all at once
                db.session.add_all(new_records)
                db.session.commit()
                print(f"✓ {len(new_records)} expense records added.")
                records_created = existing_count + len(new_records)
            else:
                print(f"✓ {existing_count} expense records already exist.")
                records_created = existing_count
        else:
            print("⚠ No expense items found. Skipping expense records.")
        
        print("\n✅ Seeding complete!")
        print(f"   - Expense Items: {ExpenseItem.query.count()}")
        print(f"   - Expense Records: {ExpenseRecord.query.count()}")

if __name__ == '__main__':
    seed_expenses()
