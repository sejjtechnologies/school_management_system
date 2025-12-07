#!/usr/bin/env python3
"""
Insert Midterm marks for Term 1, all classes, all streams, all 4 subjects.
Shows progress class by class.
"""

import os
import psycopg2
from dotenv import load_dotenv
from random import randint, seed

load_dotenv()

# Set seed for reproducibility
seed(42)

def insert_term1_midterm_marks():
    """Insert Midterm marks for Term 1"""
    
    database_url = os.getenv('DATABASE_URL')
    
    print("\n" + "=" * 100)
    print("[INSERT TERM 1 MIDTERM MARKS]")
    print("=" * 100)
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Get Midterm exam ID for Term 1 (should be ID 25)
        cur.execute("SELECT id FROM exams WHERE name = 'Midterm' AND term = 1")
        result = cur.fetchone()
        
        if not result:
            print("[ERROR] Midterm exam for Term 1 not found!\n")
            cur.close()
            conn.close()
            return
        
        exam_id = result[0]
        print(f"\n[*] Using Exam ID {exam_id} (Midterm Term 1)\n")
        
        # Get all subjects
        cur.execute("SELECT id, name FROM subjects ORDER BY id")
        subjects = cur.fetchall()
        subject_ids = [s[0] for s in subjects]
        subject_names = [s[1] for s in subjects]
        
        print(f"[*] Found {len(subjects)} subjects: {', '.join(subject_names)}\n")
        
        # Get all classes (P1-P7)
        cur.execute("SELECT id, name FROM classes ORDER BY id")
        classes = cur.fetchall()
        
        print(f"[*] Found {len(classes)} classes\n")
        print("=" * 100)
        print("[INSERTING MARKS - CLASS BY CLASS]")
        print("=" * 100)
        print()
        
        total_marks_inserted = 0
        
        for class_id, class_name in classes:
            # Get all streams for this class (from pupils)
            cur.execute("""
                SELECT DISTINCT s.id, s.name 
                FROM streams s
                JOIN pupils p ON s.id = p.stream_id
                WHERE p.class_id = %s
                ORDER BY s.id
            """, (class_id,))
            streams = cur.fetchall()
            
            class_total = 0
            
            for stream_id, stream_name in streams:
                # Get all pupils in this class/stream
                cur.execute(
                    "SELECT id FROM pupils WHERE class_id = %s AND stream_id = %s",
                    (class_id, stream_id)
                )
                pupils = [p[0] for p in cur.fetchall()]
                
                if not pupils:
                    continue
                
                # Insert marks for each pupil and subject
                marks_to_insert = []
                for pupil_id in pupils:
                    for subject_id in subject_ids:
                        score = randint(40, 95)  # Score between 40-95
                        marks_to_insert.append((pupil_id, subject_id, exam_id, score))
                
                if marks_to_insert:
                    # Batch insert
                    cur.executemany(
                        "INSERT INTO marks (pupil_id, subject_id, exam_id, score) VALUES (%s, %s, %s, %s)",
                        marks_to_insert
                    )
                    stream_marks = len(marks_to_insert)
                    class_total += stream_marks
                    total_marks_inserted += stream_marks
                    
                    print(f"  {class_name:6} > {stream_name:10} : {stream_marks:5} marks inserted")
            
            print()
        
        conn.commit()
        
        # Verify insertion
        print("=" * 100)
        print("[VERIFICATION]")
        print("=" * 100)
        print()
        
        cur.execute("""
            SELECT 
                c.name as class,
                s.name as stream,
                COUNT(m.id) as marks_count
            FROM pupils p
            JOIN classes c ON p.class_id = c.id
            JOIN streams s ON p.stream_id = s.id
            LEFT JOIN marks m ON p.id = m.pupil_id AND m.exam_id = %s
            WHERE m.id IS NOT NULL
            GROUP BY c.id, s.id, c.name, s.name
            ORDER BY c.id, s.id
        """, (exam_id,))
        
        print(f"{'Class':<10} {'Stream':<15} {'Marks Count':<15}")
        print("-" * 100)
        
        verification_total = 0
        for row in cur.fetchall():
            class_name, stream_name, marks_count = row
            verification_total += marks_count
            print(f"{class_name:<10} {stream_name:<15} {marks_count:<15}")
        
        print()
        print(f"[SUMMARY]")
        print(f"  Total marks inserted: {total_marks_inserted}")
        print(f"  Total marks verified: {verification_total}")
        print(f"  Expected (2,100 pupils × 4 subjects): {2100 * 4}")
        
        if verification_total == 2100 * 4:
            print(f"\n[SUCCESS] All marks inserted correctly!\n")
        else:
            print(f"\n[WARNING] Mark count mismatch! Expected {2100 * 4}, got {verification_total}\n")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    insert_term1_midterm_marks()
