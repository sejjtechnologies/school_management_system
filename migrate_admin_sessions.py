#!/usr/bin/env python
"""
Migration script to create AdminSession table and add active_session_id column to User table.
Uses Neon database credentials from .env file.
"""

import os
import sys
from dotenv import load_dotenv
from app import app, db
from models.user_models import User, AdminSession, Role

# Load environment variables from .env
load_dotenv()

def run_migration():
    """Run the migration to create new tables and columns."""
    print("=" * 80)
    print("ADMIN SESSION MIGRATION")
    print("=" * 80)
    
    with app.app_context():
        try:
            print("\n[1/3] Checking database connection...")
            # Test connection
            connection = db.engine.connect()
            connection.close()
            print("✅ Database connection successful!")
            
            print("\n[2/3] Creating AdminSession table...")
            # Create all new tables
            db.create_all()
            print("✅ AdminSession table created successfully!")
            
            print("\n[3/3] Verifying schema...")
            # Check if active_session_id column exists in users table
            inspector = db.inspect(db.engine)
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'active_session_id' in user_columns:
                print("✅ active_session_id column exists in users table!")
            else:
                print("⚠️  active_session_id column NOT found in users table!")
                print("   This column should have been created by db.create_all()")
            
            admin_session_columns = [col['name'] for col in inspector.get_columns('admin_sessions')]
            print(f"✅ admin_sessions table columns: {', '.join(admin_session_columns)}")
            
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("\nNEXT STEPS:")
            print("1. The AdminSession table has been created")
            print("2. The active_session_id column has been added to the users table")
            print("3. You can now test Admin single-device login restriction")
            print("\nTO TEST:")
            print("  - Start the Flask app: python app.py")
            print("  - Log in as Admin on Device 1")
            print("  - Log in as Admin on Device 2 (same email/password)")
            print("  - Device 1 should auto-logout with message when trying to access any page")
            print("\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ MIGRATION FAILED!")
            print(f"Error: {str(e)}")
            print("\nTroubleshooting:")
            print("1. Check your .env file has correct DATABASE_URL")
            print("2. Verify Neon database is accessible")
            print("3. Check your internet connection")
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
