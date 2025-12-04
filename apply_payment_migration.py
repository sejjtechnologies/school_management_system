#!/usr/bin/env python
"""
Direct migration script to add year and term columns to payments table
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

print(f"Connecting to database: {DATABASE_URL[:50]}...")

# Create engine
engine = create_engine(DATABASE_URL)

# SQL migration
migration_up = """
ALTER TABLE payments ADD COLUMN IF NOT EXISTS year INTEGER;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS term VARCHAR(20);
"""

migration_down = """
ALTER TABLE payments DROP COLUMN IF EXISTS term;
ALTER TABLE payments DROP COLUMN IF EXISTS year;
"""

try:
    with engine.connect() as conn:
        # Execute migration
        print("Applying migration: Adding year and term columns to payments table...")
        for statement in migration_up.strip().split(';'):
            if statement.strip():
                print(f"  Executing: {statement.strip()[:80]}...")
                conn.execute(text(statement))
        conn.commit()
        print("✅ Migration applied successfully!")
        
        # Verify
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='payments' AND (column_name='year' OR column_name='term');"))
        rows = result.fetchall()
        print(f"✅ Verified: Found {len(rows)} new columns")
        for row in rows:
            print(f"   - {row[0]}")
except Exception as e:
    print(f"❌ Error: {e}")
    raise
