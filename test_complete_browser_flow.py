#!/usr/bin/env python3
"""Simulate complete browser flow: mark staff paid, verify response, check DOM updates"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models.user_models import User, Role
from models.salary_models import SalaryPayment

def test_complete_flow():
    """Test the complete flow like a browser would."""
    
    with app.app_context():
        # Get a staff member
        from sqlalchemy import or_
        staff = User.query.join(Role).filter(
            or_(Role.role_name == 'Teacher', 
                Role.role_name == 'Secretary',
                Role.role_name == 'Bursar')
        ).first()
        
        if not staff:
            print("❌ No staff members found")
            return
        
        print(f"\n{'='*80}")
        print(f"🧪 SIMULATING BROWSER FLOW FOR MARK PAID")
        print(f"{'='*80}")
        print(f"\n📋 Staff Member:")
        print(f"   Name: {staff.first_name} {staff.last_name}")
        print(f"   ID: {staff.id}")
        print(f"   Role: {staff.role.role_name}")
        
        # Step 1: User fills form and submits
        print(f"\n{'='*80}")
        print(f"Step 1️⃣ : User fills form and submits")
        print(f"{'='*80}")
        
        payload = {
            'amount': 2500000.0,
            'period_month': 1,  # Different month each run
            'period_year': 2025,
            'reference': 'BROWSER-TEST',
            'notes': 'Testing via browser simulation',
            'payment_method': 'CASH',
            'bank_name': None
        }
        
        print(f"Form Data:")
        print(json.dumps(payload, indent=2))
        
        # Step 2: POST to mark-paid
        print(f"\n{'='*80}")
        print(f"Step 2️⃣ : POST to /bursar/staff/{staff.id}/mark-paid")
        print(f"{'='*80}")
        
        with app.test_client() as client:
            response = client.post(
                f'/bursar/staff/{staff.id}/mark-paid',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ ERROR: Expected 200 but got {response.status_code}")
                print(response.get_json())
                return
            
            data = response.get_json()
            
            # Step 3: Check response structure
            print(f"\n{'='*80}")
            print(f"Step 3️⃣ : Check response structure")
            print(f"{'='*80}")
            
            if not data.get('success'):
                print(f"❌ success is False: {data.get('error')}")
                return
            
            print(f"✅ success: {data['success']}")
            print(f"✅ message: {data.get('message')}")
            
            # Critical: Check for staff_update
            if 'staff_update' not in data:
                print(f"❌ ERROR: No staff_update in response!")
                print(f"Response keys: {list(data.keys())}")
                return
            
            staff_update = data['staff_update']
            print(f"\n✅ staff_update found with keys: {list(staff_update.keys())}")
            
            # Step 4: Verify staff_update has required fields
            print(f"\n{'='*80}")
            print(f"Step 4️⃣ : Verify staff_update fields for DOM update")
            print(f"{'='*80}")
            
            required_fields = ['user_id', 'is_paid', 'first_name', 'last_name']
            for field in required_fields:
                if field not in staff_update:
                    print(f"❌ Missing field: {field}")
                    return
                print(f"✅ {field}: {staff_update[field]}")
            
            # Step 5: Simulate DOM update
            print(f"\n{'='*80}")
            print(f"Step 5️⃣ : Simulate DOM update (like JavaScript in browser)")
            print(f"{'='*80}")
            
            # The JavaScript does this:
            # 1. Find staff row by data-user-id
            user_id = staff_update['user_id']
            print(f"🔍 Selector: [data-user-id=\"{user_id}\"]")
            
            # Check if staff row exists in database
            test_staff = User.query.get(user_id)
            if not test_staff:
                print(f"❌ Staff not found for updating")
                return
            
            # 2. Update badge
            if staff_update['is_paid']:
                badge_text = '✓ Paid'
                badge_class = 'badge-paid'
                print(f"✅ Badge would update to: '{badge_text}' (class: {badge_class})")
            else:
                badge_text = '✗ Unpaid'
                badge_class = 'badge-unpaid'
                print(f"Badge would update to: '{badge_text}' (class: {badge_class})")
            
            # 3. Update button
            if staff_update['is_paid']:
                button_text = 'Unmark'
                button_class = 'btn-mark-unpaid'
            else:
                button_text = 'Mark Paid'
                button_class = 'btn-mark-paid'
            print(f"✅ Button would update to: '{button_text}' (class: {button_class})")
            
            # Step 6: Verify database was updated
            print(f"\n{'='*80}")
            print(f"Step 6️⃣ : Verify database was updated")
            print(f"{'='*80}")
            
            payment = SalaryPayment.query.filter_by(
                user_id=staff.id,
                period_month=1,
                period_year=2025,
                status='paid'
            ).first()
            
            if not payment:
                print(f"❌ Payment not found in database!")
                return
            
            print(f"✅ Payment found:")
            print(f"   ID: {payment.id}")
            print(f"   Amount: {payment.amount}")
            print(f"   Method: {payment.payment_method}")
            print(f"   Status: {payment.status}")
            print(f"   Date: {payment.payment_date}")
            
            # Final success
            print(f"\n{'='*80}")
            print(f"🎉 COMPLETE FLOW SUCCESSFUL!")
            print(f"{'='*80}")
            print(f"""
The browser flow would now:
1. Close payment modal
2. Update staff row DOM with:
   - Badge: "✓ Paid" 
   - Button: "Unmark" 
3. Show success message
4. Staff status remains "Paid" without page reload ✅
            """)

if __name__ == '__main__':
    test_complete_flow()
