#!/usr/bin/env python3
"""Check what payments were created and their details."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models.salary_models import SalaryPayment

with app.app_context():
    payments = SalaryPayment.query.all()
    print(f"\nTotal payments in DB: {len(payments)}\n")
    
    for p in payments:
        user = p.user
        print(f"Payment ID: {p.id}")
        print(f"  User: {user.first_name} {user.last_name} (ID: {user.id})")
        print(f"  Amount: {p.amount}")
        print(f"  Status: {p.status}")
        print(f"  Period: {p.period_month}/{p.period_year}")
        print(f"  Method: {p.payment_method}")
        print(f"  Date: {p.payment_date}")
        print()
