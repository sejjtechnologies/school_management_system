#!/usr/bin/env python
"""
Check database state for reports and marks
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
connection = engine.connect()

marks_count = connection.execute(text("SELECT COUNT(*) FROM marks")).scalar()
reports_count = connection.execute(text("SELECT COUNT(*) FROM reports")).scalar()

print(f"Marks in DB: {marks_count}")
print(f"Reports in DB: {reports_count}")

# Check if there are orphaned reports for existing exams
if reports_count > 0:
    print("\n⚠️ Reports exist in database - these may block first insert if duplicate exam is detected")
    reports = connection.execute(text("SELECT id, pupil_id, exam_id FROM reports LIMIT 5"))
    for row in reports:
        print(f"  Report ID {row[0]}: pupil_id={row[1]}, exam_id={row[2]}")

connection.close()
engine.dispose()
