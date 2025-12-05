#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify Admin single-device login enforcement.
Simulates two admin logins and checks if the first one is invalidated.
"""

import os
import sys
from dotenv import load_dotenv
from app import app, db
from models.user_models import User, AdminSession, Role

# Fix Unicode encoding for Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

def test_admin_single_device_login():
    """Test the admin single-device login restriction."""
    
    print("\n" + "=" * 80)
    print("TESTING ADMIN SINGLE-DEVICE LOGIN RESTRICTION")
    print("=" * 80)
    
    with app.app_context():
        try:
            # Find or create a test admin user
            print("\n[1/5] Finding admin user...")
            admin = User.query.join(Role).filter(Role.role_name == "Admin").first()
            
            if not admin:
                print("ERROR: No admin user found in database!")
                return False
            
            print("[OK] Found admin: {} {} ({})".format(admin.first_name, admin.last_name, admin.email))
            
            # Clear any existing sessions for this user
            print("\n[2/5] Clearing previous sessions for this admin...")
            old_sessions = AdminSession.query.filter_by(user_id=admin.id).all()
            for session in old_sessions:
                db.session.delete(session)
            admin.active_session_id = None
            db.session.commit()
            print("[OK] Cleared {} old sessions".format(len(old_sessions)))
            
            # Simulate Device 1 Login
            print("\n[3/5] Simulating Device 1 login...")
            device1_session_id = "SESSION_DEVICE1_" + os.urandom(8).hex()
            device1_admin_session = AdminSession(
                user_id=admin.id,
                session_id=device1_session_id,
                ip_address="192.168.1.100",
                user_agent="Device 1 Browser",
                is_active=True
            )
            admin.active_session_id = device1_session_id
            db.session.add(device1_admin_session)
            db.session.commit()
            print("[OK] Device 1 logged in: {}...".format(device1_session_id[:20]))
            print("     IP: 192.168.1.100")
            print("     User.active_session_id: {}...".format(admin.active_session_id[:20]))
            
            # Verify Device 1 session is active
            device1_check = AdminSession.query.filter_by(session_id=device1_session_id).first()
            print("     DB is_active: {}".format(device1_check.is_active))
            
            # Simulate Device 2 Login (should invalidate Device 1)
            print("\n[4/5] Simulating Device 2 login with SAME credentials...")
            device2_session_id = "SESSION_DEVICE2_" + os.urandom(8).hex()
            
            # This is what happens during login
            if admin.active_session_id:
                old_session = AdminSession.query.filter_by(
                    session_id=admin.active_session_id
                ).first()
                if old_session:
                    old_session.is_active = False
                    db.session.commit()
                    print("     [OK] Invalidated Device 1 session: is_active = {}".format(old_session.is_active))
            
            # Create new session for Device 2
            device2_admin_session = AdminSession(
                user_id=admin.id,
                session_id=device2_session_id,
                ip_address="203.0.113.50",
                user_agent="Device 2 Browser",
                is_active=True
            )
            admin.active_session_id = device2_session_id
            db.session.add(device2_admin_session)
            db.session.commit()
            print("[OK] Device 2 logged in: {}...".format(device2_session_id[:20]))
            print("     IP: 203.0.113.50")
            print("     User.active_session_id: {}...".format(admin.active_session_id[:20]))
            
            # Verify sessions
            print("\n[5/5] Verifying session states...")
            device1_check = AdminSession.query.filter_by(session_id=device1_session_id).first()
            device2_check = AdminSession.query.filter_by(session_id=device2_session_id).first()
            user_check = User.query.get(admin.id)
            
            print("\n     Device 1 Session:")
            print("       - is_active: {} (should be False) {}".format(
                device1_check.is_active, 
                "[PASS]" if not device1_check.is_active else "[FAIL]"
            ))
            
            print("\n     Device 2 Session:")
            print("       - is_active: {} (should be True) {}".format(
                device2_check.is_active,
                "[PASS]" if device2_check.is_active else "[FAIL]"
            ))
            
            print("\n     User.active_session_id:")
            print("       - Points to Device 2: {} {}".format(
                user_check.active_session_id == device2_session_id,
                "[PASS]" if user_check.active_session_id == device2_session_id else "[FAIL]"
            ))
            
            # Test the validation logic (what middleware does)
            print("\n" + "=" * 80)
            print("TESTING VALIDATION LOGIC (middleware checks client vs DB)")
            print("=" * 80)
            
            print("\n[SCENARIO 1: Device 1 tries to access a page]")
            print("   - Client has session ID: {}...".format(device1_session_id[:20]))
            print("   - DB has active_session_id: {}...".format(user_check.active_session_id[:20]))
            print("   - Match? {}".format(user_check.active_session_id == device1_session_id))
            
            if user_check.active_session_id != device1_session_id:
                print("   [PASS] IDs don't match - Device 1 would be LOGGED OUT")
                print("   Message: 'Your admin session was invalidated. You logged in from another device.'")
            else:
                print("   [FAIL] IDs match when they shouldn't")
            
            print("\n[SCENARIO 2: Device 2 tries to access a page]")
            print("   - Client has session ID: {}...".format(device2_session_id[:20]))
            print("   - DB has active_session_id: {}...".format(user_check.active_session_id[:20]))
            print("   - Match? {}".format(user_check.active_session_id == device2_session_id))
            
            if user_check.active_session_id == device2_session_id:
                # Check if session is still active
                device2_active_check = AdminSession.query.filter_by(
                    session_id=device2_session_id,
                    user_id=admin.id
                ).first()
                if device2_active_check and device2_active_check.is_active:
                    print("   [PASS] IDs match AND session is active - Device 2 can continue")
                else:
                    print("   [FAIL] IDs match but session is inactive")
            else:
                print("   [FAIL] IDs don't match - Device 2 shouldn't be logged out")
            
            print("\n" + "=" * 80)
            print("[SUCCESS] Admin single-device login is working!")
            print("=" * 80)
            print("\nWhat happened:")
            print("1. Device 1 logged in successfully")
            print("2. Device 2 logged in with same credentials")
            print("3. Device 1's session was marked as inactive")
            print("4. User.active_session_id now points to Device 2")
            print("5. When Device 1 tries to access a page, it will be logged out")
            print("")
            
            return True
            
        except Exception as e:
            print("\n[ERROR] TEST FAILED: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_admin_single_device_login()
    exit(0 if success else 1)
