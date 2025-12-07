#!/usr/bin/env python3
"""
Debug what exams are available for a pupil
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def debug_available_exams():
    db = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db)
    cur = conn.cursor()
    
    # Get a pupil
    cur.execute("SELECT id, first_name, last_name FROM pupils LIMIT 1")
    pupil = cur.fetchone()
    pupil_id, fname, lname = pupil
    
    print(f"[*] Testing with pupil: {fname} {lname} (ID {pupil_id})\n")
    
    # Get all exams with marks for this pupil
    cur.execute("""
        SELECT DISTINCT e.id, e.name, e.term, e.year, COUNT(m.id) as mark_count
        FROM exams e
        LEFT JOIN marks m ON e.id = m.exam_id AND m.pupil_id = %s
        WHERE m.id IS NOT NULL
        GROUP BY e.id, e.name, e.term, e.year
        ORDER BY e.term, e.name
    """, (pupil_id,))
    
    print("[EXAMS WITH MARKS FOR THIS PUPIL]")
    print(f"{'Term':<6} {'Exam ID':<8} {'Name':<30} {'Marks':<10}")
    print("-"*70)
    
    exams_found = cur.fetchall()
    for exam_id, name, term, year, mark_count in exams_found:
        print(f"{term:<6} {exam_id:<8} {name:<30} {mark_count:<10}")
    
    print(f"\nTotal exams found: {len(exams_found)}")
    
    # Check all exams that should be available
    print("\n[ALL EXAMS IN DATABASE]")
    cur.execute("""
        SELECT e.id, e.name, e.term, COUNT(m.id) as mark_count
        FROM exams e
        LEFT JOIN marks m ON e.id = m.exam_id
        WHERE e.name IN ('Midterm', 'End Term', 'End_term', 'End_Term')
        GROUP BY e.id, e.name, e.term
        ORDER BY e.term, e.name
    """)
    
    print(f"{'Term':<6} {'Exam ID':<8} {'Name':<30} {'Total Marks':<15}")
    print("-"*70)
    
    for exam_id, name, term, mark_count in cur.fetchall():
        print(f"{term:<6} {exam_id:<8} {name:<30} {mark_count:<15}")
    
    cur.close(); conn.close()

if __name__ == '__main__':
    debug_available_exams()
