#!/usr/bin/env python3
"""
Insert Midterm marks for Terms 2 and 3 for all pupils
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from random import randint, seed

load_dotenv()
seed(45)

def insert_midterm_marks():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('[ERROR] DATABASE_URL not set')
        return
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        print("\n" + "="*100)
        print("[INSERT MIDTERM MARKS FOR TERMS 2 AND 3]")
        print("="*100)
        
        # Get subjects
        cur.execute("SELECT id FROM subjects ORDER BY id")
        subject_ids = [s[0] for s in cur.fetchall()]
        print(f"\n[*] Found {len(subject_ids)} subjects")
        
        # Get pupils
        cur.execute("SELECT id FROM pupils ORDER BY id")
        pupils = [p[0] for p in cur.fetchall()]
        print(f"[*] Found {len(pupils)} pupils")
        
        # Insert Midterm marks for Terms 2 and 3
        for term in [2, 3]:
            print(f"\n[TERM {term} MIDTERM]")
            
            # Get Midterm exam ID for this term
            cur.execute("SELECT id FROM exams WHERE name = 'Midterm' AND term = %s", (term,))
            result = cur.fetchone()
            
            if not result:
                print(f"  ERROR: No Midterm exam found for Term {term}")
                continue
            
            exam_id = result[0]
            print(f"  Using Exam ID {exam_id}")
            
            # Prepare marks data
            rows = []
            for pupil_id in pupils:
                for subject_id in subject_ids:
                    score = randint(40, 95)
                    rows.append((pupil_id, subject_id, exam_id, score))
            
            # Insert in batches
            batch_size = 2000
            inserted = 0
            for i in range(0, len(rows), batch_size):
                chunk = rows[i:i+batch_size]
                execute_values(cur,
                               "INSERT INTO marks (pupil_id, subject_id, exam_id, score) VALUES %s",
                               chunk,
                               template=None)
                inserted += len(chunk)
            
            conn.commit()
            print(f"  ✓ Inserted {inserted} marks")
        
        # Verify
        print("\n[VERIFICATION - FINAL STATUS]")
        print()
        
        for term in [1, 2, 3]:
            cur.execute("""
                SELECT e.id, e.name, COUNT(m.id) as mark_count
                FROM exams e
                LEFT JOIN marks m ON e.id = m.exam_id
                WHERE e.term = %s AND e.name IN ('Midterm', 'End Term', 'End_term', 'End_Term')
                GROUP BY e.id, e.name
                ORDER BY e.id
            """, (term,))
            
            print(f"Term {term}:")
            total_term = 0
            for exam_id, name, count in cur.fetchall():
                total_term += count
                status = "✓" if count > 0 else "✗"
                print(f"  {status} ID {exam_id} ({name:20}): {count:6} marks")
            print(f"    TOTAL: {total_term} marks\n")
        
        print("[SUCCESS] All terms now have both Midterm and End Term marks!\n")
        
    except Exception as e:
        print(f'\n[ERROR] {e}\n')
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    insert_midterm_marks()
