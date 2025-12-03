#!/usr/bin/env python
"""
Verify timetable_slots constraints
"""

import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

def verify_constraints():
    """Check the constraints on timetable_slots table"""
    
    database_url = os.getenv('DATABASE_URL')
    parsed = urlparse(database_url)
    
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    
    cursor = conn.cursor()
    
    # Query to get constraints
    sql = """
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'timetable_slots'
    ORDER BY constraint_name;
    """
    
    cursor.execute(sql)
    constraints = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    print("\n✅ Constraints on timetable_slots table:\n")
    for constraint_name, constraint_type in constraints:
        print(f"  • {constraint_name} ({constraint_type})")
    
    return constraints

if __name__ == "__main__":
    print("🔍 Verifying timetable_slots constraints...")
    verify_constraints()
