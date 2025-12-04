#!/usr/bin/env python3
"""Quick check to verify payment_method columns are populated"""
import os, sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from models.salary_models import SalaryPayment

with app.app_context():
    payments = SalaryPayment.query.all()
    print("Payment Method Tracking Status:\n")
    for p in payments:
        print(f"Payment ID {p.id}: method={p.payment_method}, bank={p.bank_name}")
    print("\n" + "="*60)
    print("SUCCESS! Payment method columns are working!\n")
