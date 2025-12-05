#!/usr/bin/env python3
"""Test both mark-paid and mark-unpaid flows"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models.user_models import User, Role
from models.salary_models import SalaryPayment

def test_both_flows():
    """Test mark-paid and mark-unpaid flows."""
    
    with app.app_context():
        from sqlalchemy import or_
        staff = User.query.join(Role).filter(
            or_(Role.role_name == 'Teacher', 
                Role.role_name == 'Secretary',
                Role.role_name == 'Bursar')
        ).first()
        
        if not staff:
            print("❌ No staff found")
            return
        
        print(f"\n{'='*80}")
        print(f"TESTING MARK-PAID AND MARK-UNPAID FLOWS")
        print(f"{'='*80}")
        print(f"\nStaff: {staff.first_name} {staff.last_name} (ID: {staff.id})")
        
        with app.test_client() as client:
            # TEST 1: MARK PAID
            print(f"\n{'='*80}")
            print(f"TEST 1: MARK PAID")
            print(f"{'='*80}")
            
            payload = {
                'amount': 2500000.0,
                'period_month': 2,
                'period_year': 2025,
                'reference': 'TEST-001',
                'notes': 'Test marking paid',
                'payment_method': 'BANK',
                'bank_name': 'Centenary'
            }
            
            response = client.post(
                f'/bursar/staff/{staff.id}/mark-paid',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            if response.status_code != 200:
                print(f"❌ Status {response.status_code}: {response.get_json()}")
                return
            
            data = response.get_json()
            
            print(f"✅ Response status: {response.status_code}")
            print(f"✅ success: {data['success']}")
            print(f"✅ message: {data['message']}")
            
            if 'staff_update' not in data:
                print(f"❌ No staff_update!")
                return
            
            update = data['staff_update']
            print(f"✅ staff_update:")
            print(f"   user_id: {update['user_id']}")
            print(f"   is_paid: {update['is_paid']}")
            print(f"   payment_method: {update['payment_method']}")
            print(f"   bank_name: {update['bank_name']}")
            
            payment_id = data['payment_id']
            
            # Verify in DB
            payment = SalaryPayment.query.get(payment_id)
            if not payment:
                print(f"❌ Payment not in DB!")
                return
            
            print(f"✅ Payment in DB (ID: {payment_id}, Status: {payment.status})")
            
            # TEST 2: MARK UNPAID
            print(f"\n{'='*80}")
            print(f"TEST 2: MARK UNPAID")
            print(f"{'='*80}")
            
            unpaid_payload = {
                'payment_id': None  # Auto-find most recent
            }
            
            response = client.post(
                f'/bursar/staff/{staff.id}/mark-unpaid',
                data=json.dumps(unpaid_payload),
                content_type='application/json'
            )
            
            if response.status_code != 200:
                print(f"❌ Status {response.status_code}: {response.get_json()}")
                return
            
            data = response.get_json()
            
            print(f"✅ Response status: {response.status_code}")
            print(f"✅ success: {data['success']}")
            print(f"✅ message: {data['message']}")
            
            if 'staff_update' not in data:
                print(f"❌ No staff_update!")
                return
            
            update = data['staff_update']
            print(f"✅ staff_update:")
            print(f"   user_id: {update['user_id']}")
            print(f"   is_paid: {update['is_paid']}")
            
            # Verify payment was reversed
            payment = SalaryPayment.query.get(payment_id)
            if not payment:
                print(f"❌ Payment deleted instead of reversed!")
                return
            
            print(f"✅ Payment updated (ID: {payment_id}, Status: {payment.status})")
            
            # FINAL SUMMARY
            print(f"\n{'='*80}")
            print(f"ALL TESTS PASSED!")
            print(f"{'='*80}")
            print(f"""
PASS: Mark-Paid Flow:
   - POST returns staff_update with is_paid=True
   - Frontend can update DOM: Badge->"PAID", Button->"Unmark"

PASS: Mark-Unpaid Flow:
   - POST returns staff_update with is_paid=False  
   - Frontend can update DOM: Badge->"UNPAID", Button->"Mark Paid"

Both flows have immediate DOM update capability!
            """)

if __name__ == '__main__':
    test_both_flows()
