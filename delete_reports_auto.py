#!/usr/bin/env python
"""
Delete all reports from the database (non-interactive).
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

print("=" * 60)
print("DELETE ALL REPORTS FROM DATABASE")
print("=" * 60)

# Create database connection
try:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("✅ Connected to Neon database")
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    sys.exit(1)

try:
    # Get initial count
    reports_count = connection.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    print(f"\n📊 Current reports in database: {reports_count}")
    
    if reports_count == 0:
        print("✅ No reports to delete, database is already clean")
        connection.close()
        engine.dispose()
        sys.exit(0)
    
    print("\n🔄 DELETING DATA...")
    print("-" * 60)
    
    # Delete reports
    reports_deleted = connection.execute(text("DELETE FROM reports"))
    connection.commit()
    print(f"✅ Deleted {reports_deleted.rowcount} report records")
    
    # Verify final count
    final_count = connection.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    
    print("\n" + "=" * 60)
    print("✅ DELETION COMPLETE")
    print("=" * 60)
    print(f"Reports deleted: {reports_deleted.rowcount}")
    print(f"Reports remaining: {final_count}")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error during deletion: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    connection.close()
    engine.dispose()
    print("\n✅ Database connection closed")
