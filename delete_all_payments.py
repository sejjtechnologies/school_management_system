#!/usr/bin/env python3
"""
Script to delete all salary payment records from Neon database.
This allows for a fresh start to test the salary management feature.
"""
import os
import sys
from dotenv import load_dotenv

# Load env
load_dotenv()

# Setup Flask app
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from models.salary_models import SalaryPayment

def delete_all_payments():
    """Delete all salary payment records"""
    
    with app.app_context():
        print("=" * 80)
        print("DELETE ALL SALARY PAYMENTS FROM NEON DATABASE")
        print("=" * 80)
        
        # Count existing payments
        count = SalaryPayment.query.count()
        print(f"\n📊 Current payments in database: {count}\n")
        
        if count == 0:
            print("✓ No payments to delete. Database is already clean.\n")
            return True
        
        # Show what will be deleted
        payments = SalaryPayment.query.all()
        print("Payments to be deleted:\n")
        for p in payments:
            from models.user_models import User
            user = User.query.get(p.user_id)
            staff_name = f"{user.first_name} {user.last_name}" if user else "Unknown"
            month = p.period_month or '?'
            year = p.period_year or '?'
            print(f"  • {staff_name} | {month}/{year} | UGX {p.amount:,.0f} | Status: {p.status}")
        
        # Ask for confirmation
        print(f"\n⚠️  WARNING: This will delete {count} payment record(s)!\n")
        confirm = input("Type 'DELETE' to confirm deletion: ").strip()
        
        if confirm != 'DELETE':
            print("\n❌ Deletion cancelled.\n")
            return False
        
        # Delete all payments
        try:
            SalaryPayment.query.delete()
            db.session.commit()
            print(f"\n✅ Successfully deleted {count} payment record(s)!\n")
            
            # Verify
            remaining = SalaryPayment.query.count()
            print(f"✓ Remaining payments: {remaining}\n")
            
            print("=" * 80)
            print("Database is now clean. You can test the salary form again from scratch.")
            print("=" * 80 + "\n")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during deletion: {e}\n")
            return False

if __name__ == '__main__':
    success = delete_all_payments()
    sys.exit(0 if success else 1)
