#!/usr/bin/env python3
"""
Fast insert End_term marks for Term 1 for all classes and streams for 4 subjects.
Uses psycopg2.extras.execute_values for bulk insertion.
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from random import randint, seed

load_dotenv()
seed(43)

def find_endterm_exam(cur):
    # try several name variants
    cur.execute("SELECT id, name FROM exams WHERE term = 1 AND name IN ('End_term', 'End Term', 'End_Term', 'EndTerm', 'EndTerm') ORDER BY id")
    row = cur.fetchone()
    if row:
        return row[0], row[1]
    # fallback: any exam with name ILIKE '%end%term%' or name ILIKE 'end%'
    cur.execute("SELECT id, name FROM exams WHERE term = 1 AND (name ILIKE 'end%term%' OR name ILIKE 'end %' OR name ILIKE 'end_%') ORDER BY id")
    row = cur.fetchone()
    if row:
        return row[0], row[1]
    return None, None


def insert_endterm_fast(batch_size=2000):
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('[ERROR] DATABASE_URL not set')
        return

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        exam_id, exam_name = find_endterm_exam(cur)
        if not exam_id:
            print('[ERROR] Term 1 End_term exam not found. Please create it first.')
            return
        print(f"[*] Using Exam ID {exam_id} ({exam_name}) for Term 1 End_term\n")

        # subjects
        cur.execute("SELECT id, name FROM subjects ORDER BY id")
        subjects = cur.fetchall()
        if not subjects:
            print('[ERROR] No subjects found')
            return
        subject_ids = [s[0] for s in subjects]
        subject_names = [s[1] for s in subjects]
        print(f"[*] Subjects: {', '.join(subject_names)}\n")

        # classes
        cur.execute("SELECT id, name FROM classes ORDER BY id")
        classes = cur.fetchall()
        print(f"[*] Found {len(classes)} classes\n")

        total_inserted = 0
        # For each class, get streams via pupils
        for class_id, class_name in classes:
            cur.execute("SELECT DISTINCT s.id, s.name FROM streams s JOIN pupils p ON s.id = p.stream_id WHERE p.class_id = %s ORDER BY s.id", (class_id,))
            streams = cur.fetchall()
            for stream_id, stream_name in streams:
                # get pupils in this class/stream
                cur.execute("SELECT id FROM pupils WHERE class_id = %s AND stream_id = %s ORDER BY id", (class_id, stream_id))
                pupils = [r[0] for r in cur.fetchall()]
                if not pupils:
                    continue
                # prepare rows
                rows = []
                for pupil_id in pupils:
                    for subject_id in subject_ids:
                        score = randint(40, 95)
                        rows.append((pupil_id, subject_id, exam_id, score))
                # insert in batches
                i = 0
                n = len(rows)
                while i < n:
                    chunk = rows[i:i+batch_size]
                    execute_values(cur,
                                   "INSERT INTO marks (pupil_id, subject_id, exam_id, score) VALUES %s",
                                   chunk,
                                   template=None)
                    total_inserted += len(chunk)
                    i += batch_size
                print(f"  {class_name:6} > {stream_name:10} : {len(rows):5} marks inserted")
        conn.commit()

        print() 
        print(f"[SUMMARY] Total marks inserted: {total_inserted}")

        # verification per class/stream
        print('\n[VERIFICATION]')
        cur.execute("""
            SELECT c.name as class, s.name as stream, COUNT(m.id) as marks_count
            FROM pupils p
            JOIN classes c ON p.class_id = c.id
            JOIN streams s ON p.stream_id = s.id
            LEFT JOIN marks m ON p.id = m.pupil_id AND m.exam_id = %s
            WHERE m.id IS NOT NULL
            GROUP BY c.id, s.id, c.name, s.name
            ORDER BY c.id, s.id
        """, (exam_id,))

        print(f"{'Class':<10} {'Stream':<15} {'Marks Count':<15}")
        print('-'*60)
        verification_total = 0
        for row in cur.fetchall():
            class_name, stream_name, marks_count = row
            verification_total += marks_count
            print(f"{class_name:<10} {stream_name:<15} {marks_count:<15}")

        print() 
        print(f"[VERIFIED TOTAL] {verification_total}")
        expected = 2100 * len(subject_ids)
        print(f"[EXPECTED] {expected}")
        if verification_total == expected:
            print('\n[SUCCESS] End_term marks inserted correctly for Term 1!')
        else:
            print('\n[WARNING] Verification mismatch')

    except Exception as e:
        print('[ERROR]', e)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    insert_endterm_fast()
