#!/usr/bin/env python3
"""Simple test for immediate DB save"""
import os, sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from app import app
from models.user_models import User
from models.salary_models import SalaryPayment

with app.app_context():
    with app.test_client() as client:
        teacher = User.query.filter_by(role_id=3).first()
        if not teacher:
            print("No teacher found")
            sys.exit(1)

        print("Test: Create payment and verify DB save\n")

        payload = {
            "amount": 650000,
            "period_month": 12,
            "period_year": 2025,
            "reference": "QUICK-TEST",
            "notes": "Quick test",
            "payment_method": "BANK",
            "bank_name": "Centenary"
        }

        # Create payment
        print("1. Posting payment...")
        response = client.post(f'/bursar/staff/{teacher.id}/mark-paid', json=payload)
        print(f"   Status: {response.status_code}")
        data = response.get_json()
        print(f"   Has payment data: {'payment' in data}")
        print(f"   Has staff_update: {'staff_update' in data}")

        if data.get('success') and 'payment' in data:
            pay = data['payment']
            print(f"\n2. Verifying DB entry...")
            db_pay = SalaryPayment.query.get(data.get('payment_id'))
            if db_pay:
                print(f"   Method: {db_pay.payment_method} (sent: {pay.get('payment_method')})")
                print(f"   Bank: {db_pay.bank_name} (sent: {pay.get('bank_name')})")
                print(f"   Status: {db_pay.status}")
                print(f"\n✓ SUCCESS: Immediate DB save working")
            else:
                print(f"   ✗ Not found in DB")
        else:
            print(f"   Error: {data.get('error')}")

        # Test unmark
        print(f"\n3. Testing unmark...")
        unmark = client.post(f'/bursar/staff/{teacher.id}/mark-unpaid', json={})
        print(f"   Status: {unmark.status_code}")
        unmark_data = unmark.get_json()
        if unmark_data and unmark_data.get('success'):
            print(f"   ✓ Unmark successful")
            print(f"   Has staff_update: {'staff_update' in unmark_data}")
        else:
            print(f"   Error: {unmark_data}")
