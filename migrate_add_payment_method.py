#!/usr/bin/env python3
"""
Database migration script to add payment_method and bank_name columns
to the salary_payments table in Neon.
"""
import os
import sys
from dotenv import load_dotenv

# Load env
load_dotenv()

# Setup Flask app
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from sqlalchemy import text

def migrate_add_payment_method():
    """Add payment_method and bank_name columns to salary_payments"""
    
    with app.app_context():
        print("=" * 80)
        print("MIGRATE: Add payment_method and bank_name to salary_payments")
        print("=" * 80 + "\n")
        
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('salary_payments')]
            
            if 'payment_method' in columns and 'bank_name' in columns:
                print("✓ Columns payment_method and bank_name already exist.\n")
                return True
            
            print("📝 Adding columns to salary_payments table...\n")
            
            # Add payment_method column
            if 'payment_method' not in columns:
                db.session.execute(text(
                    "ALTER TABLE salary_payments ADD COLUMN payment_method VARCHAR(20) DEFAULT 'CASH'"
                ))
                print("✓ Added column: payment_method (VARCHAR(20), default='CASH')")
            
            # Add bank_name column
            if 'bank_name' not in columns:
                db.session.execute(text(
                    "ALTER TABLE salary_payments ADD COLUMN bank_name VARCHAR(100)"
                ))
                print("✓ Added column: bank_name (VARCHAR(100))")
            
            db.session.commit()
            
            print("\n✅ Migration completed successfully!\n")
            print("=" * 80)
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Migration failed: {e}\n")
            print("=" * 80)
            return False

if __name__ == '__main__':
    success = migrate_add_payment_method()
    sys.exit(0 if success else 1)
