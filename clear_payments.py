#!/usr/bin/env python3
"""Check and delete all payments."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models.salary_models import SalaryPayment

with app.app_context():
    count = SalaryPayment.query.count()
    print(f"Payments: {count}")
    
    if count > 0:
        SalaryPayment.query.delete()
        db.session.commit()
        print(f"Deleted all. New count: {SalaryPayment.query.count()}")
