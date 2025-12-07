#!/usr/bin/env python3
"""
Check which exams exist for all terms and if they have marks
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def check_exams():
    db = os.getenv('DATABASE_URL')
    if not db:
        print('DATABASE_URL not set')
        return
    
    conn = psycopg2.connect(db)
    cur = conn.cursor()
    
    print("\n" + "="*100)
    print("[EXAM STATUS BY TERM]")
    print("="*100)
    
    for term in [1, 2, 3]:
        print(f"\n[TERM {term}]")
        cur.execute("""
            SELECT e.id, e.name, COUNT(m.id) as mark_count
            FROM exams e
            LEFT JOIN marks m ON e.id = m.exam_id
            WHERE e.term = %s
            GROUP BY e.id, e.name
            ORDER BY e.id
        """, (term,))
        
        rows = cur.fetchall()
        total_marks = 0
        midterm_ids = []
        endterm_ids = []
        
        print(f"{'ID':<5} {'Name':<30} {'Marks':<10}")
        print("-"*60)
        
        for exam_id, name, mark_count in rows:
            total_marks += mark_count
            print(f"{exam_id:<5} {name:<30} {mark_count:<10}")
            
            if 'mid' in name.lower():
                midterm_ids.append(exam_id)
            elif 'end' in name.lower():
                endterm_ids.append(exam_id)
        
        print(f"\nSummary: {total_marks} total marks")
        print(f"  Midterm exams: {midterm_ids}")
        print(f"  End_term exams: {endterm_ids}")
        
        if midterm_ids and endterm_ids:
            print(f"  ✓ Can print combined reports")
        else:
            print(f"  ✗ Missing data for combined reports")
    
    cur.close(); conn.close()

if __name__ == '__main__':
    check_exams()
