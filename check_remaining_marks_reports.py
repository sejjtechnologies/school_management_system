#!/usr/bin/env python
"""
Check for any remaining marks or reports for all pupils from P1-P7 across all streams.
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

print("=" * 70)
print("CHECK FOR REMAINING MARKS AND REPORTS")
print("=" * 70)
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
    # Get overall counts
    print("\n" + "=" * 70)
    print("📊 OVERALL DATABASE STATISTICS")
    print("=" * 70)
    
    marks_count = connection.execute(text("SELECT COUNT(*) FROM marks")).scalar()
    reports_count = connection.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    total_pupils = connection.execute(text("SELECT COUNT(*) FROM pupils")).scalar()
    pupils_with_class = connection.execute(text("SELECT COUNT(*) FROM pupils WHERE class_id IS NOT NULL")).scalar()
    
    print(f"Total Marks in DB: {marks_count}")
    print(f"Total Reports in DB: {reports_count}")
    print(f"Total Pupils in DB: {total_pupils}")
    print(f"Pupils with Class Assigned: {pupils_with_class}")
    
    # Check pupils per class
    print("\n" + "=" * 70)
    print("📋 PUPILS PER CLASS (P1-P7)")
    print("=" * 70)
    
    class_query = connection.execute(
        text("""
        SELECT c.id, c.name, COUNT(p.id) as pupil_count
        FROM classes c
        LEFT JOIN pupils p ON c.id = p.class_id
        WHERE c.name IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')
        GROUP BY c.id, c.name
        ORDER BY CAST(SUBSTRING(c.name FROM 2) AS INTEGER)
        """)
    )
    
    total_p1_to_p7 = 0
    for row in class_query:
        class_id, class_name, pupil_count = row
        print(f"  {class_name}: {pupil_count} pupils")
        total_p1_to_p7 += pupil_count
    
    print(f"  {'─' * 40}")
    print(f"  Total (P1-P7): {total_p1_to_p7} pupils")
    
    # Check streams
    print("\n" + "=" * 70)
    print("🌊 STREAMS")
    print("=" * 70)
    
    streams_query = connection.execute(
        text("""
        SELECT s.id, s.name, COUNT(DISTINCT p.id) as pupil_count
        FROM streams s
        LEFT JOIN pupils p ON s.id = p.stream_id
        GROUP BY s.id, s.name
        ORDER BY s.name
        """)
    )
    
    stream_data = []
    for row in streams_query:
        stream_id, stream_name, pupil_count = row
        print(f"  {stream_name}: {pupil_count} pupils")
        stream_data.append((stream_id, stream_name, pupil_count))
    
    # Check for marks/reports by class
    print("\n" + "=" * 70)
    print("📌 MARKS AND REPORTS BY CLASS (P1-P7)")
    print("=" * 70)
    
    class_marks_query = connection.execute(
        text("""
        SELECT c.name, COUNT(m.id) as mark_count
        FROM classes c
        LEFT JOIN pupils p ON c.id = p.class_id
        LEFT JOIN marks m ON p.id = m.pupil_id
        WHERE c.name IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')
        GROUP BY c.id, c.name
        ORDER BY CAST(SUBSTRING(c.name FROM 2) AS INTEGER)
        """)
    )
    
    print("\nMarks by Class:")
    total_marks_p1_p7 = 0
    for row in class_marks_query:
        class_name, mark_count = row
        status = "✅ Clean" if mark_count == 0 else f"⚠️  {mark_count} marks found"
        print(f"  {class_name}: {status}")
        total_marks_p1_p7 += mark_count
    
    class_reports_query = connection.execute(
        text("""
        SELECT c.name, COUNT(r.id) as report_count
        FROM classes c
        LEFT JOIN pupils p ON c.id = p.class_id
        LEFT JOIN reports r ON p.id = r.pupil_id
        WHERE c.name IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')
        GROUP BY c.id, c.name
        ORDER BY CAST(SUBSTRING(c.name FROM 2) AS INTEGER)
        """)
    )
    
    print("\nReports by Class:")
    total_reports_p1_p7 = 0
    for row in class_reports_query:
        class_name, report_count = row
        status = "✅ Clean" if report_count == 0 else f"⚠️  {report_count} reports found"
        print(f"  {class_name}: {status}")
        total_reports_p1_p7 += report_count
    
    # Check for marks/reports by stream
    print("\n" + "=" * 70)
    print("🌊 MARKS AND REPORTS BY STREAM")
    print("=" * 70)
    
    stream_marks_query = connection.execute(
        text("""
        SELECT s.name, COUNT(m.id) as mark_count
        FROM streams s
        LEFT JOIN pupils p ON s.id = p.stream_id
        LEFT JOIN marks m ON p.id = m.pupil_id
        GROUP BY s.id, s.name
        ORDER BY s.name
        """)
    )
    
    print("\nMarks by Stream:")
    for row in stream_marks_query:
        stream_name, mark_count = row
        status = "✅ Clean" if mark_count == 0 else f"⚠️  {mark_count} marks found"
        print(f"  {stream_name}: {status}")
    
    stream_reports_query = connection.execute(
        text("""
        SELECT s.name, COUNT(r.id) as report_count
        FROM streams s
        LEFT JOIN pupils p ON s.id = p.stream_id
        LEFT JOIN reports r ON p.id = r.pupil_id
        GROUP BY s.id, s.name
        ORDER BY s.name
        """)
    )
    
    print("\nReports by Stream:")
    for row in stream_reports_query:
        stream_name, report_count = row
        status = "✅ Clean" if report_count == 0 else f"⚠️  {report_count} reports found"
        print(f"  {stream_name}: {status}")
    
    # Detailed check for any leftover marks/reports
    print("\n" + "=" * 70)
    print("🔍 DETAILED LEFTOVER CHECK")
    print("=" * 70)
    
    leftover_marks = connection.execute(
        text("""
        SELECT p.pupil_id, c.name as class, s.name as stream, COUNT(m.id) as mark_count
        FROM pupils p
        LEFT JOIN classes c ON p.class_id = c.id
        LEFT JOIN streams s ON p.stream_id = s.id
        LEFT JOIN marks m ON p.id = m.pupil_id
        WHERE c.name IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')
        AND m.id IS NOT NULL
        GROUP BY p.id, p.pupil_id, c.name, s.name
        LIMIT 20
        """)
    )
    
    leftover_marks_list = leftover_marks.fetchall()
    if leftover_marks_list:
        print("\n⚠️  Found leftover MARKS:")
        print("  Pupil ID | Class | Stream | Mark Count")
        print("  " + "─" * 50)
        for row in leftover_marks_list:
            pupil_id, class_name, stream_name, mark_count = row
            print(f"  {pupil_id:>8} | {class_name:>5} | {stream_name:>15} | {mark_count}")
    else:
        print("\n✅ No leftover marks found for P1-P7")
    
    leftover_reports = connection.execute(
        text("""
        SELECT p.pupil_id, c.name as class, s.name as stream, COUNT(r.id) as report_count
        FROM pupils p
        LEFT JOIN classes c ON p.class_id = c.id
        LEFT JOIN streams s ON p.stream_id = s.id
        LEFT JOIN reports r ON p.id = r.pupil_id
        WHERE c.name IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')
        AND r.id IS NOT NULL
        GROUP BY p.id, p.pupil_id, c.name, s.name
        LIMIT 20
        """)
    )
    
    leftover_reports_list = leftover_reports.fetchall()
    if leftover_reports_list:
        print("\n⚠️  Found leftover REPORTS:")
        print("  Pupil ID | Class | Stream | Report Count")
        print("  " + "─" * 50)
        for row in leftover_reports_list:
            pupil_id, class_name, stream_name, report_count = row
            print(f"  {pupil_id:>8} | {class_name:>5} | {stream_name:>15} | {report_count}")
    else:
        print("\n✅ No leftover reports found for P1-P7")
    
    # Final Summary
    print("\n" + "=" * 70)
    print("📋 FINAL SUMMARY")
    print("=" * 70)
    print(f"Total Marks Remaining (P1-P7): {total_marks_p1_p7}")
    print(f"Total Reports Remaining (P1-P7): {total_reports_p1_p7}")
    print(f"Total Remaining Records: {total_marks_p1_p7 + total_reports_p1_p7}")
    
    if total_marks_p1_p7 == 0 and total_reports_p1_p7 == 0:
        print("\n✅ ✅ ✅ ALL CLEAN! No marks or reports remaining for P1-P7! ✅ ✅ ✅")
    else:
        print("\n⚠️  WARNING: Leftover data detected! Please review the details above.")
    
    print("=" * 70)

except Exception as e:
    print(f"\n❌ Error during check: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    connection.close()
    engine.dispose()
    print("\n✅ Database connection closed")
