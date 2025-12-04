#!/usr/bin/env python3
"""
Test script to verify payment method tracking works.
Tests creating payments with different methods (Cash, Bank).
"""
import os
import sys
from dotenv import load_dotenv

# Load env
load_dotenv()

# Setup Flask app
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from models.user_models import User
from models.salary_models import SalaryPayment

def test_payment_methods():
    """Test creating payments with different payment methods"""
    
    with app.app_context():
        print("=" * 80)
        print("TEST: Payment Method Tracking")
        print("=" * 80 + "\n")
        
        with app.test_client() as client:
            # Find a teacher
            teacher = User.query.filter_by(role_id=3).first()
            if not teacher:
                print("❌ No teacher found")
                return False
            
            print(f"Testing with: {teacher.first_name} {teacher.last_name} (ID: {teacher.id})\n")
            
            # Test 1: Create CASH payment
            print("TEST 1: Creating CASH payment for December 2025...")
            payload1 = {
                "amount": 500000,
                "period_month": 12,
                "period_year": 2025,
                "reference": "CASH-001",
                "notes": "Cash payment test",
                "payment_method": "CASH",
                "bank_name": None
            }
            
            response1 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload1
            )
            data1 = response1.get_json()
            print(f"   Status: {response1.status_code}")
            print(f"   Success: {data1.get('success')}")
            
            if data1.get('success'):
                payment1 = SalaryPayment.query.get(data1.get('payment_id'))
                if payment1:
                    print(f"   OK: Payment created with ID: {payment1.id}")
                    print(f"     - Method: {payment1.payment_method}")
                    print(f"     - Bank: {payment1.bank_name}")
                    print(f"   PASS: CASH payment working!\n")
                else:
                    print(f"   FAIL: Payment not found in DB\n")
                    return False
            else:
                print(f"   FAIL: {data1.get('error')}\n")
                return False
            
            # Test 2: Try to create duplicate (should fail)
            print("TEST 2: Attempting duplicate CASH payment (should be rejected)...")
            payload2 = {
                "amount": 500000,
                "period_month": 12,
                "period_year": 2025,
                "reference": "CASH-002",
                "notes": "Duplicate attempt",
                "payment_method": "CASH",
                "bank_name": None
            }
            
            response2 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload2
            )
            data2 = response2.get_json()
            
            if not data2.get('success'):
                print(f"   PASS: Duplicate correctly rejected: {data2.get('error')}\n")
            else:
                print(f"   FAIL: Duplicate was allowed (should be rejected)\n")
                return False
            
            # Test 3: Create BANK payment for different month
            print("TEST 3: Creating BANK payment for November 2025...")
            payload3 = {
                "amount": 500000,
                "period_month": 11,
                "period_year": 2025,
                "reference": "BANK-001",
                "notes": "Bank transfer test",
                "payment_method": "BANK",
                "bank_name": "Centenary"
            }
            
            response3 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload3
            )
            data3 = response3.get_json()
            print(f"   Status: {response3.status_code}")
            print(f"   Success: {data3.get('success')}")
            
            if data3.get('success'):
                payment3 = SalaryPayment.query.get(data3.get('payment_id'))
                if payment3:
                    print(f"   OK: Payment created with ID: {payment3.id}")
                    print(f"     - Method: {payment3.payment_method}")
                    print(f"     - Bank: {payment3.bank_name}")
                    print(f"   PASS: BANK payment with Centenary working!\n")
                else:
                    print(f"   FAIL: Payment not found in DB\n")
                    return False
            else:
                print(f"   FAIL: {data3.get('error')}\n")
                return False
            
            # Test 4: Create BANK payment with different bank for October
            print("TEST 4: Creating BANK payment with Stanbic for October 2025...")
            payload4 = {
                "amount": 500000,
                "period_month": 10,
                "period_year": 2025,
                "reference": "BANK-002",
                "notes": "Stanbic transfer",
                "payment_method": "BANK",
                "bank_name": "Stanbic"
            }
            
            response4 = client.post(
                f'/bursar/staff/{teacher.id}/mark-paid',
                json=payload4
            )
            data4 = response4.get_json()
            
            if data4.get('success'):
                payment4 = SalaryPayment.query.get(data4.get('payment_id'))
                if payment4:
                    print(f"   OK: Payment created with ID: {payment4.id}")
                    print(f"     - Method: {payment4.payment_method}")
                    print(f"     - Bank: {payment4.bank_name}")
                    print(f"   PASS: BANK payment with Stanbic working!\n")
                else:
                    print(f"   FAIL: Payment not found in DB\n")
                    return False
            else:
                print(f"   FAIL: {data4.get('error')}\n")
                return False
            
            # Display all payments for this user
            print("TEST 5: All payments created for this staff member:\n")
            all_payments = SalaryPayment.query.filter_by(user_id=teacher.id).order_by(
                SalaryPayment.period_year.desc(),
                SalaryPayment.period_month.desc()
            ).all()
            
            for p in all_payments:
                month = p.period_month or '?'
                year = p.period_year or '?'
                method_display = f"{p.payment_method}"
                if p.payment_method == 'BANK':
                    method_display += f" ({p.bank_name})"
                print(f"   * {month:>2}/{year} | UGX {p.amount:>10,.0f} | {method_display:>20} | Ref: {p.reference}")
            
            print("\n" + "=" * 80)
            print("ALL TESTS PASSED! Payment method tracking is working correctly.")
            print("=" * 80 + "\n")
            return True

if __name__ == '__main__':
    success = test_payment_methods()
    sys.exit(0 if success else 1)
