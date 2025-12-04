#!/usr/bin/env python3
"""
Test script to verify duplicate payment prevention works.
Uses Flask test client to simulate a POST to mark-paid twice for the same month.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load env
load_dotenv()

# Setup Flask app
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from models.user_models import User, Role
from models.salary_models import SalaryPayment, RoleSalary

def test_duplicate_payment():
    """Test that duplicate payments for same month/year are rejected"""

    with app.app_context():
        with app.test_client() as client:
            # Find a teacher user
            teacher = User.query.filter_by(role_id=3).first()  # Assuming Teacher role_id = 3
            if not teacher:
                print("❌ No teacher user found to test")
                return False

            print(f"✓ Testing with user: {teacher.first_name} {teacher.last_name} (ID: {teacher.id})")

            # First payment for Dec 2025
            payload1 = {
                "amount": 500000,
                "period_month": 12,
                "period_year": 2025,
                "reference": "TEST-1",
                "notes": "First payment test"
            }

            response1 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload1
            )
            data1 = response1.get_json()
            print(f"\n1️⃣ First payment POST:")
            print(f"   Status: {response1.status_code}")
            print(f"   Response: {data1}")

            if not data1.get('success'):
                print(f"❌ First payment failed unexpectedly: {data1.get('error')}")
                return False

            # Attempt duplicate payment for same month
            payload2 = {
                "amount": 500000,
                "period_month": 12,
                "period_year": 2025,
                "reference": "TEST-2",
                "notes": "Duplicate attempt"
            }

            response2 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload2
            )
            data2 = response2.get_json()
            print(f"\n2️⃣ Duplicate payment POST (same month/year):")
            print(f"   Status: {response2.status_code}")
            print(f"   Response: {data2}")

            if data2.get('success'):
                print(f"❌ Duplicate payment was allowed (should be rejected)")
                return False

            if 'already been marked as paid' in data2.get('error', ''):
                print(f"✓ Duplicate payment correctly rejected")
            else:
                print(f"⚠ Duplicate rejected but error message unexpected: {data2.get('error')}")

            # Try payment for different month (should succeed)
            payload3 = {
                "amount": 500000,
                "period_month": 11,
                "period_year": 2025,
                "reference": "TEST-3",
                "notes": "Different month test"
            }

            response3 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload3
            )
            data3 = response3.get_json()
            print(f"\n3️⃣ Payment for different month (Nov 2025):")
            print(f"   Status: {response3.status_code}")
            print(f"   Response: {data3}")

            if data3.get('success'):
                print(f"✓ Different month payment succeeded (as expected)")
            else:
                print(f"❌ Different month payment failed: {data3.get('error')}")
                return False

            print(f"\n✅ All tests passed!")
            return True

if __name__ == '__main__':
    success = test_duplicate_payment()
    sys.exit(0 if success else 1)
