#!/usr/bin/env python3
"""
Check marks for all terms
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def check_marks():
    db = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db)
    cur = conn.cursor()
    
    print("\n" + "="*100)
    print("[MARKS STATUS]")
    print("="*100)
    
    for term in [1, 2, 3]:
        cur.execute("""
            SELECT e.id, e.name, COUNT(m.id) as mark_count
            FROM exams e
            LEFT JOIN marks m ON e.id = m.exam_id
            WHERE e.term = %s AND e.name IN ('Midterm', 'End Term', 'End_term', 'End_Term')
            GROUP BY e.id, e.name
            ORDER BY e.id
        """, (term,))
        
        print(f"\nTerm {term}:")
        total_term = 0
        for exam_id, name, count in cur.fetchall():
            total_term += count
            print(f"  ID {exam_id} ({name:20}): {count:6} marks")
        print(f"  {'TOTAL':<26}: {total_term:6} marks")
    
    cur.close(); conn.close()

if __name__ == '__main__':
    check_marks()
