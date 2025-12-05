#!/usr/bin/env python3
"""Test the mark-paid endpoint flow to diagnose the issue."""

import json
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.user_models import User
from models.salary_models import SalaryPayment
from datetime import datetime

def test_mark_paid():
    """Test marking a staff member as paid."""
    
    with app.app_context():
        # Get first staff member
        from sqlalchemy import or_
        from models.user_models import Role
        
        staff = User.query.join(Role).filter(
            or_(Role.role_name == 'Teacher', 
                Role.role_name == 'Secretary',
                Role.role_name == 'Bursar')
        ).first()
        
        if not staff:
            print("❌ No staff members found in database")
            return
        
        print(f"📋 Testing with staff: {staff.first_name} {staff.last_name} (ID: {staff.id})")
        print(f"   Role: {staff.role.role_name if staff.role else 'N/A'}")
        print(f"   Salary: {staff.salary_amount}")
        
        # Prepare payload
        salary_amount = staff.salary_amount or 2500000  # Default if None
        payload = {
            'amount': float(salary_amount),
            'period_month': 12,
            'period_year': 2024,
            'reference': 'TEST-REF-001',
            'notes': 'Test payment',
            'payment_method': 'CASH',
            'bank_name': None
        }
        
        print(f"\n📤 Sending POST to /bursar/staff/{staff.id}/mark-paid")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        # Use test client
        with app.test_client() as client:
            # Need to login first if auth is required
            # For now, assuming no auth check in mark-paid
            response = client.post(
                f'/bursar/staff/{staff.id}/mark-paid',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            try:
                data = response.get_json()
                print(f"📄 Response JSON:")
                print(json.dumps(data, indent=2))
                
                if data.get('success'):
                    print("\n✅ SUCCESS - Endpoint returned success=True")
                    
                    # Verify staff_update is in response
                    if 'staff_update' in data:
                        staff_update = data['staff_update']
                        print(f"\n📋 staff_update received:")
                        print(f"   user_id: {staff_update.get('user_id')}")
                        print(f"   is_paid: {staff_update.get('is_paid')}")
                        print(f"   payment_method: {staff_update.get('payment_method')}")
                    else:
                        print("\n⚠️  WARNING - No staff_update in response!")
                    
                    # Check if payment was actually created
                    payment = SalaryPayment.query.filter_by(
                        user_id=staff.id,
                        period_month=12,
                        period_year=2024
                    ).first()
                    
                    if payment:
                        print(f"\n💾 Payment record created in DB:")
                        print(f"   Payment ID: {payment.id}")
                        print(f"   Status: {payment.status}")
                        print(f"   Amount: {payment.amount}")
                        print(f"   Method: {payment.payment_method}")
                        print(f"   Bank: {payment.bank_name}")
                    else:
                        print("\n❌ ERROR - Payment not found in DB!")
                else:
                    print(f"\n❌ FAILED - {data.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"\n❌ Failed to parse response: {e}")
                print(f"Response text: {response.get_data(as_text=True)}")

if __name__ == '__main__':
    test_mark_paid()
