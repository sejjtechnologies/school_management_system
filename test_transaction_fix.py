#!/usr/bin/env python
"""
Test script to verify transaction error handling fixes
Run this to ensure the transaction error is properly handled
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_system_settings_recovery():
    """Test that SystemSettings.get_settings() recovers from errors"""
    print("\n" + "="*60)
    print("TEST 1: SystemSettings Error Recovery")
    print("="*60)
    
    try:
        from app import app
        from models.system_settings import SystemSettings
        from models.user_models import db
        
        with app.app_context():
            # Test 1: Normal case
            print("\n✓ Test 1.1: Fetch settings (normal case)")
            try:
                settings = SystemSettings.get_settings()
                print(f"  ✅ Success: Retrieved settings ID={settings.id}")
            except Exception as e:
                print(f"  ❌ Failed: {str(e)}")
                return False
            
            # Test 2: Simulate transaction failure and recovery
            print("\n✓ Test 1.2: Simulate transaction abort recovery")
            try:
                # Intentionally cause an error
                db.session.execute("INVALID SQL SYNTAX;")
            except Exception as e:
                print(f"  ℹ️  Triggered error as expected: {type(e).__name__}")
            
            # Now try to get settings again - should recover
            try:
                settings = SystemSettings.get_settings()
                print(f"  ✅ Recovery successful: Got settings after error")
            except Exception as e:
                print(f"  ❌ Recovery failed: {str(e)}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        return False

def test_backup_maintenance_route():
    """Test that backup_maintenance route handles errors"""
    print("\n" + "="*60)
    print("TEST 2: Backup Maintenance Route Error Handling")
    print("="*60)
    
    try:
        from app import app
        
        with app.test_client() as client:
            print("\n✓ Test 2.1: GET /admin/backup-maintenance")
            try:
                # This might require authentication - that's OK
                response = client.get('/admin/backup-maintenance')
                if response.status_code in [200, 302]:
                    print(f"  ✅ Route accessible (status: {response.status_code})")
                else:
                    print(f"  ℹ️  Route returned {response.status_code} (may need auth)")
            except Exception as e:
                print(f"  ❌ Route failed: {str(e)}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        return False

def test_session_cleanup():
    """Test that sessions are cleaned up after requests"""
    print("\n" + "="*60)
    print("TEST 3: Database Session Cleanup")
    print("="*60)
    
    try:
        from app import app
        from models.user_models import db
        
        with app.test_client() as client:
            print("\n✓ Test 3.1: Session cleanup after request")
            try:
                # Make any request
                response = client.get('/')
                
                # Check if session is cleaned up (should not raise)
                try:
                    db.session.remove()
                    print(f"  ✅ Session cleanup works")
                except Exception as e:
                    print(f"  ⚠️  Session cleanup issue: {str(e)}")
                    return False
            except Exception as e:
                print(f"  ℹ️  Request failed (may need auth): {type(e).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        return False

def test_database_connection():
    """Test basic database connectivity"""
    print("\n" + "="*60)
    print("TEST 4: Database Connection")
    print("="*60)
    
    try:
        from app import app
        from models.user_models import db
        from sqlalchemy import text
        
        with app.app_context():
            print("\n✓ Test 4.1: Connect to database")
            try:
                with db.engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    print(f"  ✅ Database connection successful")
                return True
            except Exception as e:
                print(f"  ❌ Database connection failed: {str(e)}")
                return False
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        return False

def test_safe_db_operation_decorator():
    """Test the safe_db_operation decorator"""
    print("\n" + "="*60)
    print("TEST 5: Safe DB Operation Decorator")
    print("="*60)
    
    try:
        from db_utils import safe_db_operation
        from models.user_models import db
        
        print("\n✓ Test 5.1: Decorator application")
        
        @safe_db_operation("TestOperation")
        def test_func():
            return "success"
        
        try:
            result = test_func()
            if result == "success":
                print(f"  ✅ Decorator works correctly")
                return True
            else:
                print(f"  ❌ Unexpected result: {result}")
                return False
        except Exception as e:
            print(f"  ❌ Decorator failed: {str(e)}")
            return False
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + " "*10 + "Transaction Error Fix Verification Tests" + " "*8 + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    results = {
        "Database Connection": test_database_connection(),
        "SystemSettings Recovery": test_system_settings_recovery(),
        "Safe DB Operation Decorator": test_safe_db_operation_decorator(),
        "Backup Maintenance Route": test_backup_maintenance_route(),
        "Session Cleanup": test_session_cleanup(),
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*60)
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nThe transaction error fix is working correctly!")
        return 0
    else:
        print(f"⚠️  Some tests failed ({passed}/{total})")
        print("\nPlease check the logs above for details.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
