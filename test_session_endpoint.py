#!/usr/bin/env python
"""
Test the /api/check-session endpoint for real-time session validation.
"""

import requests
import json
from dotenv import load_dotenv
from app import app, db
from models.user_models import User, AdminSession, Role
import os

load_dotenv()

def test_check_session_endpoint():
    """Test the session check API endpoint."""
    print("\n" + "=" * 80)
    print("TESTING /api/check-session ENDPOINT")
    print("=" * 80)
    
    with app.app_context():
        # Find admin user
        admin = User.query.join(Role).filter(Role.role_name == "Admin").first()
        if not admin:
            print("ERROR: No admin found")
            return False
        
        print(f"\n[1/4] Found admin: {admin.first_name} {admin.last_name}")
        
        # Clear old sessions
        AdminSession.query.filter_by(user_id=admin.id).delete()
        admin.active_session_id = None
        db.session.commit()
        
        # Create a test session
        print("\n[2/4] Creating test session...")
        test_session_id = "TEST_SESSION_" + os.urandom(8).hex()
        admin_session = AdminSession(
            user_id=admin.id,
            session_id=test_session_id,
            ip_address="127.0.0.1",
            user_agent="Test Script",
            is_active=True
        )
        admin.active_session_id = test_session_id
        db.session.add(admin_session)
        db.session.commit()
        print(f"[OK] Session created: {test_session_id[:20]}...")
        
        # Test 1: Valid session
        print("\n[3/4] Testing VALID session...")
        with app.test_client() as client:
            # Simulate authenticated request
            with client.session_transaction() as sess:
                sess['user_id'] = admin.id
                sess['role'] = 'Admin'
                sess['active_session_id'] = test_session_id
            
            response = client.get('/api/check-session')
            print(f"Status: {response.status_code}")
            data = response.get_json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 200 and data.get('valid'):
                print("[PASS] Valid session accepted ✓")
            else:
                print("[FAIL] Valid session rejected ✗")
                return False
        
        # Test 2: Invalid session (mismatch)
        print("\n[4/4] Testing INVALID session (mismatch)...")
        with app.test_client() as client:
            # Simulate request with different session ID
            with client.session_transaction() as sess:
                sess['user_id'] = admin.id
                sess['role'] = 'Admin'
                sess['active_session_id'] = "WRONG_SESSION_ID"
            
            response = client.get('/api/check-session')
            print(f"Status: {response.status_code}")
            data = response.get_json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 401 and not data.get('valid'):
                print("[PASS] Invalid session rejected ✓")
                print(f"Reason: {data.get('reason')}")
            else:
                print("[FAIL] Invalid session not rejected ✗")
                return False
        
        print("\n" + "=" * 80)
        print("[SUCCESS] /api/check-session endpoint working correctly!")
        print("=" * 80)
        print("\nHow it works:")
        print("1. Client sends session cookie with user_id, role, active_session_id")
        print("2. Server compares client's active_session_id with DB's user.active_session_id")
        print("3. If match + is_active=True: returns {valid: true}")
        print("4. If mismatch or inactive: returns {valid: false, reason: ...}")
        print("\nIn JavaScript, polling checks this every 3 seconds.")
        print("When invalid, auto-logs out with alert and redirects to login.")
        print("")
        
        return True

if __name__ == "__main__":
    success = test_check_session_endpoint()
    exit(0 if success else 1)
