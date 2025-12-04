#!/usr/bin/env python3
"""
Script to check existing salary payments in Neon database
and verify duplicate prevention logic.
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

def check_existing_payments():
    """Check all existing salary payments in database"""
    
    with app.app_context():
        print("=" * 80)
        print("NEON DATABASE - EXISTING SALARY PAYMENTS")
        print("=" * 80)
        
        # Get all payments
        payments = SalaryPayment.query.order_by(
            SalaryPayment.user_id,
            SalaryPayment.period_year.desc(),
            SalaryPayment.period_month.desc()
        ).all()
        
        if not payments:
            print("\n✓ No payments found in database.")
            return
        
        print(f"\n📊 Total payments in database: {len(payments)}\n")
        
        # Group by user
        by_user = {}
        for p in payments:
            uid = p.user_id
            if uid not in by_user:
                by_user[uid] = []
            by_user[uid].append(p)
        
        # Display grouped by user
        for user_id, user_payments in sorted(by_user.items()):
            user = User.query.get(user_id)
            if not user:
                continue
            
            print(f"\n👤 Staff: {user.first_name} {user.last_name}")
            print(f"   ID: {user_id} | Role: {user.role.role_name if user.role else 'N/A'}")
            print(f"   Total payments: {len(user_payments)}")
            print()
            
            for p in sorted(user_payments, key=lambda x: (x.period_year or 0, x.period_month or 0), reverse=True):
                month = p.period_month or '?'
                year = p.period_year or '?'
                status = p.status.upper()
                amount = f"UGX {p.amount:,.0f}" if p.amount else "N/A"
                ref = p.reference or "(no ref)"
                
                status_icon = "✓" if status == "PAID" else "✗" if status == "REVERSED" else "?"
                print(f"   {status_icon} {month:>2}/{year} | {amount:>15} | {status:>8} | ID: {p.id} | Ref: {ref}")
        
        print("\n" + "=" * 80)
        
        # Now test duplicate prevention
        print("\n🧪 TESTING DUPLICATE PREVENTION\n")
        print("=" * 80)
        
        with app.test_client() as client:
            # Find a teacher
            teacher = User.query.filter_by(role_id=3).first()
            if not teacher:
                print("❌ No teacher found")
                return
            
            print(f"\nTesting with: {teacher.first_name} {teacher.last_name} (ID: {teacher.id})")
            
            # Check if this teacher already has a payment for Dec 2025
            existing_dec = SalaryPayment.query.filter_by(
                user_id=teacher.id,
                period_month=12,
                period_year=2025,
                status='paid'
            ).first()
            
            if existing_dec:
                print(f"\n✓ Found existing payment for Dec 2025:")
                print(f"  Payment ID: {existing_dec.id}")
                print(f"  Amount: UGX {existing_dec.amount:,.0f}")
                print(f"  Status: {existing_dec.status}")
                print(f"  Reference: {existing_dec.reference or 'N/A'}")
                print(f"\n  Now attempting to create DUPLICATE payment for Dec 2025...")
                
                # Try to create duplicate
                payload = {
                    "amount": 500000,
                    "period_month": 12,
                    "period_year": 2025,
                    "reference": "DUPLICATE-TEST",
                    "notes": "This should be rejected"
                }
                
                response = client.post(
                    f'/bursar/staff/{teacher.id}/mark-paid',
                    json=payload
                )
                data = response.get_json()
                
                print(f"\n  Response Status: {response.status_code}")
                print(f"  Success: {data.get('success')}")
                print(f"  Message: {data.get('error') or data.get('message')}")
                
                if not data.get('success') and response.status_code in [400, 409]:
                    print(f"\n  ✅ DUPLICATE CORRECTLY REJECTED!")
                else:
                    print(f"\n  ❌ DUPLICATE WAS ALLOWED (PROBLEM!)")
            else:
                print(f"\n⚠ No existing payment for Dec 2025.")
                print(f"  Creating first payment for testing...")
                
                payload = {
                    "amount": 500000,
                    "period_month": 12,
                    "period_year": 2025,
                    "reference": "TEST-FIRST",
                    "notes": "First test payment"
                }
                
                response = client.post(
                    f'/bursar/staff/{teacher.id}/mark-paid',
                    json=payload
                )
                data = response.get_json()
                
                print(f"  Response Status: {response.status_code}")
                print(f"  Success: {data.get('success')}")
                
                if data.get('success'):
                    print(f"  Payment ID: {data.get('payment_id')}")
                    print(f"\n  Now attempting DUPLICATE for same month...")
                    
                    payload2 = {
                        "amount": 500000,
                        "period_month": 12,
                        "period_year": 2025,
                        "reference": "TEST-DUPLICATE",
                        "notes": "Duplicate attempt"
                    }
                    
                    response2 = client.post(
                        f'/bursar/staff/{teacher.id}/mark-paid',
                        json=payload2
                    )
                    data2 = response2.get_json()
                    
                    print(f"  Response Status: {response2.status_code}")
                    print(f"  Success: {data2.get('success')}")
                    print(f"  Message: {data2.get('error') or data2.get('message')}")
                    
                    if not data2.get('success') and response2.status_code in [400, 409]:
                        print(f"\n  ✅ DUPLICATE CORRECTLY REJECTED!")
                    else:
                        print(f"\n  ❌ DUPLICATE WAS ALLOWED (PROBLEM!)")
                else:
                    print(f"  Error: {data.get('error')}")
        
        print("\n" + "=" * 80)

if __name__ == '__main__':
    check_existing_payments()
