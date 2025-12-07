#!/usr/bin/env python
"""
Delete all marks and reports from database (cascade properly)
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
connection = engine.connect()

print("Deleting reports...")
reports_deleted = connection.execute(text("DELETE FROM reports"))
connection.commit()
print(f"✅ Deleted {reports_deleted.rowcount} reports")

print("\nDeleting marks...")
marks_deleted = connection.execute(text("DELETE FROM marks"))
connection.commit()
print(f"✅ Deleted {marks_deleted.rowcount} marks")

# Verify
marks_final = connection.execute(text("SELECT COUNT(*) FROM marks")).scalar()
reports_final = connection.execute(text("SELECT COUNT(*) FROM reports")).scalar()

print(f"\n✅ Final state: Marks={marks_final}, Reports={reports_final}")

connection.close()
engine.dispose()
