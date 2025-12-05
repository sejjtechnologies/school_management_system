#!/usr/bin/env python
"""
Migration script to add active_session_id column to existing users table.
"""

import os
from dotenv import load_dotenv
from app import app, db
from sqlalchemy import inspect, Column, String, text

# Load environment variables
load_dotenv()

def add_active_session_id_column():
    """Add active_session_id column to users table if it doesn't exist."""
    print("=" * 80)
    print("ADDING active_session_id COLUMN TO users TABLE")
    print("=" * 80)
    
    with app.app_context():
        try:
            print("\n[1/2] Checking if active_session_id column exists...")
            
            # Check if column exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'active_session_id' in columns:
                print("✅ active_session_id column already exists!")
                return True
            
            print("⚠️  active_session_id column not found, adding it now...")
            
            print("\n[2/2] Adding active_session_id column to users table...")
            
            # Add the column using raw SQL
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN active_session_id VARCHAR(255) UNIQUE NULL"
                ))
            
            print("✅ active_session_id column added successfully!")
            
            # Verify
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'active_session_id' in columns:
                print("\n✅ Verification: Column exists in users table!")
                print(f"   Users table columns: {', '.join(columns)}")
                
                print("\n" + "=" * 80)
                print("✅ COLUMN ADDED SUCCESSFULLY!")
                print("=" * 80)
                print("\nYou can now:")
                print("1. Start Flask app: python app.py")
                print("2. Test Admin single-device login restriction")
                print("\n")
                return True
            else:
                print("❌ Verification failed: Column still not found!")
                return False
                
        except Exception as e:
            print(f"\n❌ ERROR adding column!")
            print(f"Error: {str(e)}")
            
            # Try alternative if PostgreSQL version issue
            if "syntax error" in str(e).lower():
                print("\n[RETRY] Attempting alternative syntax...")
                try:
                    with db.engine.begin() as connection:
                        connection.execute(text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_session_id VARCHAR(255)"
                        ))
                    print("✅ Column added with alternative syntax!")
                    return True
                except Exception as e2:
                    print(f"❌ Alternative also failed: {str(e2)}")
                    return False
            
            return False

if __name__ == "__main__":
    success = add_active_session_id_column()
    exit(0 if success else 1)
