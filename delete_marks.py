#!/usr/bin/env python
"""
Delete all marks from the database.
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
print("DELETE ALL MARKS FROM DATABASE")
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
    marks_count = connection.execute(text("SELECT COUNT(*) FROM marks")).scalar()
    print(f"\n📊 Current marks in database: {marks_count}")

    if marks_count == 0:
        print("✅ No marks to delete, database is already clean")
        connection.close()
        engine.dispose()
        sys.exit(0)

    # Confirm deletion
    print("\n" + "=" * 60)
    print("⚠️  WARNING: You are about to DELETE:")
    print(f"   - {marks_count} marks records")
    print("=" * 60)

    user_input = input("\nType 'DELETE' to confirm (or press Enter to cancel): ").strip().upper()

    if user_input != "DELETE":
        print("❌ Deletion cancelled")
        connection.close()
        engine.dispose()
        sys.exit(0)

    print("\n🔄 DELETING DATA...")
    print("-" * 60)

    # Delete marks
    marks_deleted = connection.execute(text("DELETE FROM marks"))
    connection.commit()
    print(f"✅ Deleted {marks_deleted.rowcount} mark records")

    # Verify final count
    final_count = connection.execute(text("SELECT COUNT(*) FROM marks")).scalar()

    print("\n" + "=" * 60)
    print("✅ DELETION COMPLETE")
    print("=" * 60)
    print(f"Marks deleted: {marks_deleted.rowcount}")
    print(f"Marks remaining: {final_count}")
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
