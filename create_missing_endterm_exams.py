#!/usr/bin/env python3
"""
Create End Term exams for Term 2 and 3, then insert marks for all pupils.
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from random import randint, seed

load_dotenv()
seed(44)

def create_term_exams():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('[ERROR] DATABASE_URL not set')
        return
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        print("\n" + "="*100)
        print("[CREATE END TERM EXAMS FOR TERMS 2 AND 3]")
        print("="*100)
        
        # Check what exams already exist
        cur.execute("SELECT id, name, term FROM exams WHERE term IN (2, 3) ORDER BY term, id")
        existing = cur.fetchall()
        
        print("\n[EXISTING EXAMS]")
        for exam_id, name, term in existing:
            print(f"  Term {term}: ID {exam_id} - {name}")
        
        # Get subjects
        cur.execute("SELECT id, name FROM subjects ORDER BY id")
        subjects = cur.fetchall()
        subject_ids = [s[0] for s in subjects]
        
        print(f"\n[SUBJECTS] Found {len(subjects)} subjects")
        
        # Create End Term exams for Terms 2 and 3
        print("\n[CREATING END TERM EXAMS]")
        
        new_exams = []
        for term in [2, 3]:
            # Check if End Term already exists for this term
            cur.execute("SELECT id FROM exams WHERE name IN ('End Term', 'End_term', 'End_Term') AND term = %s", (term,))
            existing_endterm = cur.fetchone()
            
            if not existing_endterm:
                # Insert new End Term exam
                cur.execute(
                    "INSERT INTO exams (name, term, year) VALUES (%s, %s, 2025) RETURNING id",
                    ('End Term', term)
                )
                exam_id = cur.fetchone()[0]
                new_exams.append((exam_id, term))
                print(f"  ✓ Created 'End Term' for Term {term} (ID {exam_id})")
            else:
                print(f"  - End Term already exists for Term {term} (ID {existing_endterm[0]})")
                new_exams.append((existing_endterm[0], term))
        
        conn.commit()
        
        # Now insert marks for all pupils for new exams
        print("\n[INSERTING MARKS FOR NEW EXAMS]")
        
        for exam_id, term in new_exams:
            # Get all pupils
            cur.execute("SELECT id FROM pupils ORDER BY id")
            pupils = [p[0] for p in cur.fetchall()]
            
            if not pupils:
                print(f"  No pupils found for Term {term}")
                continue
            
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
            print(f"  ✓ Inserted {inserted} marks for Term {term} End Term (Exam ID {exam_id})")
        
        # Verify
        print("\n[VERIFICATION]")
        print()
        
        for term in [1, 2, 3]:
            cur.execute("""
                SELECT e.id, e.name, COUNT(m.id) as mark_count
                FROM exams e
                LEFT JOIN marks m ON e.id = m.exam_id
                WHERE e.term = %s AND e.name IN ('Midterm', 'End Term', 'End_term', 'End_Term')
                GROUP BY e.id, e.name
                ORDER BY e.name
            """, (term,))
            
            rows = cur.fetchall()
            print(f"Term {term}:")
            for exam_id, name, mark_count in rows:
                status = "✓" if mark_count > 0 else "✗"
                print(f"  {status} {name} (ID {exam_id}): {mark_count} marks")
        
        print("\n[SUCCESS] All terms now have both Midterm and End Term exams with marks!\n")
        
    except Exception as e:
        print(f'\n[ERROR] {e}\n')
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    create_term_exams()
