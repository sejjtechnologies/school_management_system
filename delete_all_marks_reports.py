#!/usr/bin/env python
"""
Delete all marks and reports for all pupils from the database.
Connects to Neon database using .env file.
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
print("DELETE ALL MARKS AND REPORTS")
print("=" * 60)
print(f"Database URL: {DATABASE_URL.split('@')[0]}...{DATABASE_URL.split('@')[1][-20:]}")
print()

# Create database connection
try:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("✅ Connected to Neon database")
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    sys.exit(1)

try:
    # Get initial counts
    print("\n📊 INITIAL STATE:")
    print("-" * 60)
    
    marks_count_result = connection.execute(text("SELECT COUNT(*) FROM marks"))
    marks_count = marks_count_result.scalar()
    print(f"   Total Marks: {marks_count}")
    
    reports_count_result = connection.execute(text("SELECT COUNT(*) FROM reports"))
    reports_count = reports_count_result.scalar()
    print(f"   Total Reports: {reports_count}")
    
    pupils_count_result = connection.execute(text("SELECT COUNT(*) FROM pupils WHERE class_id IS NOT NULL"))
    pupils_count = pupils_count_result.scalar()
    print(f"   Total Pupils with class: {pupils_count}")
    
    # Get breakdown by class
    print("\n📋 BREAKDOWN BY CLASS:")
    print("-" * 60)
    class_breakdown = connection.execute(
        text("""
        SELECT c.name, COUNT(p.id) as pupil_count
        FROM pupils p
        LEFT JOIN classes c ON p.class_id = c.id
        WHERE p.class_id IS NOT NULL
        GROUP BY c.id, c.name
        ORDER BY c.name
        """)
    )
    for row in class_breakdown:
        print(f"   {row[0]}: {row[1]} pupils")
    
    # Confirm deletion
    print("\n" + "=" * 60)
    print("⚠️  WARNING: You are about to DELETE:")
    print(f"   - {marks_count} marks records")
    print(f"   - {reports_count} reports records")
    print("=" * 60)
    
    user_input = input("\nType 'DELETE' to confirm (or press Enter to cancel): ").strip().upper()
    
    if user_input != "DELETE":
        print("❌ Deletion cancelled")
        connection.close()
        sys.exit(0)
    
    print("\n🔄 DELETING DATA...")
    print("-" * 60)
    
    # Delete reports first (foreign key constraint)
    reports_deleted = connection.execute(text("DELETE FROM reports"))
    connection.commit()
    print(f"✅ Deleted {reports_deleted.rowcount} report records")
    
    # Delete marks
    marks_deleted = connection.execute(text("DELETE FROM marks"))
    connection.commit()
    print(f"✅ Deleted {marks_deleted.rowcount} mark records")
    
    # Get final counts
    print("\n📊 FINAL STATE:")
    print("-" * 60)
    
    marks_count_final = connection.execute(text("SELECT COUNT(*) FROM marks")).scalar()
    reports_count_final = connection.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    
    print(f"   Total Marks: {marks_count_final}")
    print(f"   Total Reports: {reports_count_final}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ DELETION SUMMARY")
    print("=" * 60)
    print(f"Marks deleted: {marks_deleted.rowcount}")
    print(f"Reports deleted: {reports_deleted.rowcount}")
    print(f"Total records deleted: {marks_deleted.rowcount + reports_deleted.rowcount}")
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
