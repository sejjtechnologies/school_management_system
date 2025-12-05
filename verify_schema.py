#!/usr/bin/env python
"""
Verify that both AdminSession table and active_session_id column exist.
"""

import os
from dotenv import load_dotenv
from app import app, db
from sqlalchemy import inspect

load_dotenv()

with app.app_context():
    print("\n" + "=" * 80)
    print("DATABASE SCHEMA VERIFICATION")
    print("=" * 80)
    
    inspector = inspect(db.engine)
    
    # Check users table
    print("\n[USERS TABLE]")
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    print(f"Columns: {', '.join(user_columns)}")
    
    if 'active_session_id' in user_columns:
        print("✅ active_session_id column EXISTS")
    else:
        print("❌ active_session_id column MISSING")
    
    # Check admin_sessions table
    print("\n[ADMIN_SESSIONS TABLE]")
    try:
        admin_cols = [col['name'] for col in inspector.get_columns('admin_sessions')]
        print(f"Columns: {', '.join(admin_cols)}")
        print("✅ admin_sessions table EXISTS")
    except Exception as e:
        print(f"❌ admin_sessions table MISSING: {str(e)}")
    
    # Summary
    print("\n" + "=" * 80)
    if 'active_session_id' in user_columns and len(admin_cols) > 0:
        print("✅ ALL MIGRATIONS COMPLETE!")
        print("=" * 80)
        print("\nYou can now test:")
        print("1. python app.py")
        print("2. Log in as Admin on Device 1")
        print("3. Log in as Admin on Device 2")
        print("4. Device 1 should be logged out automatically")
    else:
        print("⚠️  SOME MIGRATIONS MISSING")
        print("=" * 80)
    print()
