#!/usr/bin/env python3
"""Test immediate DB save and UI update responses"""
import os, sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from models.user_models import User
from models.salary_models import SalaryPayment

with app.app_context():
    with app.test_client() as client:
        # Find a teacher
        teacher = User.query.filter_by(role_id=3).first()
        if not teacher:
            print("No teacher found")
            sys.exit(1)
        
        print("=" * 70)
        print("TEST 1: Create payment with immediate DB save")
        print("=" * 70)
        
        payload = {
            "amount": 650000,
            "period_month": 12,
            "period_year": 2025,
            "reference": "TEST-PAY-001",
            "notes": "Test payment",
            "payment_method": "CASH",
            "bank_name": None
        }
        
        response = client.post(f'/bursar/staff/{teacher.id}/mark-paid', json=payload)
        data = response.get_json()
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        
        if data.get('success'):
            print(f"\nPayment data returned:")
            payment_data = data.get('payment')
            if payment_data:
                print(f"  - ID: {payment_data.get('id')}")
                print(f"  - Amount: UGX {payment_data.get('amount'):,.0f}")
                print(f"  - Method: {payment_data.get('payment_method')}")
                print(f"  - Status: {payment_data.get('status')}")
            
            print(f"\nStaff update data returned:")
            staff_data = data.get('staff_update')
            if staff_data:
                print(f"  - User ID: {staff_data.get('user_id')}")
                print(f"  - Name: {staff_data.get('first_name')} {staff_data.get('last_name')}")
                print(f"  - Is Paid: {staff_data.get('is_paid')}")
            
            # Verify in DB
            payment = SalaryPayment.query.get(data.get('payment_id'))
            if payment:
                print(f"\nVerified in DB:")
                print(f"  - Payment exists with ID: {payment.id}")
                print(f"  - Amount: UGX {payment.amount:,.0f}")
                print(f"  - Status: {payment.status}")
                print(f"\n✓ PASS: Payment immediately saved to database")
            else:
                print(f"\n✗ FAIL: Payment not found in DB")
        else:
            print(f"Error: {data.get('error')}")
        
        # Test 2: Unmark payment
        print("\n" + "=" * 70)
        print("TEST 2: Reverse payment with immediate DB update")
        print("=" * 70)
        
        unmark_response = client.post(f'/bursar/staff/{teacher.id}/mark-unpaid', json={"payment_id": None})
        unmark_data = unmark_response.get_json()
        
        print(f"\nResponse status: {unmark_response.status_code}")
        print(f"Success: {unmark_data.get('success')}")
        print(f"Message: {unmark_data.get('message')}")
        
        if unmark_data.get('success'):
            print(f"\nStaff update data returned:")
            staff_data = unmark_data.get('staff_update')
            if staff_data:
                print(f"  - Is Paid: {staff_data.get('is_paid')}")
                print(f"  - Status should now be: Unpaid (False)")
            
            # Verify in DB
            payment = SalaryPayment.query.get(unmark_data.get('payment_id'))
            if payment:
                print(f"\nVerified in DB:")
                print(f"  - Payment status: {payment.status}")
                if payment.status == 'reversed':
                    print(f"\n✓ PASS: Payment immediately updated in database")
                else:
                    print(f"\n✗ FAIL: Payment status not updated correctly")
            else:
                print(f"\n✗ FAIL: Payment not found in DB")
        else:
            print(f"Error: {unmark_data.get('error')}")
        
        print("\n" + "=" * 70)
        print("All tests completed")
        print("=" * 70)
