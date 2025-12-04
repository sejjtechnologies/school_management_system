#!/usr/bin/env python3
"""
Seed script to populate default role salaries.
Run this after creating the salary tables to set initial salary amounts for each role.

Usage:
  python seed_role_salaries.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal

# Setup Flask app context
from app import app, db
from models.user_models import Role
from models.salary_models import RoleSalary

# Load environment
load_dotenv('.env')


def seed_role_salaries():
    """Add default salaries for each role - real Ugandan primary school salaries."""
    
    with app.app_context():
        # Real Ugandan Primary School Monthly Salaries (2024-2025)
        # Salary hierarchy: Admin > Headteacher > Bursar > Teacher > Secretary
        default_salaries = {
            'Admin': Decimal('1200000.00'),           # Highest: Administrative Officer (~UGX 1.2M/month)
            'Headteacher': Decimal('1000000.00'),     # Second: HEAD (~UGX 1M/month)
            'Bursar': Decimal('850000.00'),           # Third: Finance Officer (~UGX 850k/month)
            'Teacher': Decimal('650000.00'),          # Fourth: Teacher (~UGX 650k/month)
            'Secretary': Decimal('520000.00'),        # Lowest: Secretary (~UGX 520k/month)
        }
        
        print("\n" + "="*60)
        print("Seeding Real Ugandan Primary School Salaries")
        print("="*60 + "\n")
        
        # Step 1: Delete existing salaries
        print("Step 1: Clearing existing salary configurations...")
        try:
            deleted_count = RoleSalary.query.delete()
            db.session.commit()
            print(f"✓ Deleted {deleted_count} existing salary records\n")
        except Exception as e:
            print(f"⚠ Error deleting existing salaries: {e}\n")
            db.session.rollback()
        
        # Step 2: Seed new salaries
        print("Step 2: Seeding new salaries...")
        for role_name, salary_amount in default_salaries.items():
            # Check if role exists
            role = Role.query.filter_by(role_name=role_name).first()
            
            if not role:
                print(f"⚠ Role '{role_name}' not found in database. Skipping.")
                continue
            
            # Create new role salary with min/max ranges
            new_salary = RoleSalary(
                role_id=role.id,
                amount=salary_amount,
                min_amount=salary_amount * Decimal('0.9'),    # 90% of base (deductions)
                max_amount=salary_amount * Decimal('1.15')    # 115% of base (bonuses/allowances)
            )
            
            db.session.add(new_salary)
            print(f"✓ {role_name:15} → UGX {float(salary_amount):>12,.0f}/month")
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "="*60)
        print("✓ Role salaries seeded successfully!")
        print("="*60)
        print("\nMonthly Payment Summary:")
        for role_name, salary_amount in default_salaries.items():
            print(f"  • {role_name:15} UGX {float(salary_amount):>12,.0f}")
        print("\nYou can now:")
        print("1. Navigate to Bursar Dashboard → Manage Staff Salaries")
        print("2. Select a role and month to view staff")
        print("3. Mark staff as paid for the selected period")
        print("4. View reports and payment history")


if __name__ == '__main__':
    try:
        seed_role_salaries()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
