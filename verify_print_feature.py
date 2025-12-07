#!/usr/bin/env python3
"""
Verify that the print feature can find both Midterm and End_term for Term 1
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def verify_print_data():
    db = os.getenv('DATABASE_URL')
    if not db:
        print('DATABASE_URL not set')
        return

    conn = psycopg2.connect(db)
    cur = conn.cursor()

    # Get a random pupil
    cur.execute("SELECT id, first_name, last_name, class_id, stream_id FROM pupils LIMIT 1")
    pupil = cur.fetchone()

    if not pupil:
        print("No pupils found")
        cur.close(); conn.close(); return

    pupil_id, fname, lname, class_id, stream_id = pupil
    print(f"[*] Testing with pupil: {fname} {lname} (ID {pupil_id})")

    # Get all Term 1 exams
    cur.execute("SELECT id, name, term FROM exams WHERE term = 1 ORDER BY id")
    term1_exams = cur.fetchall()

    print(f"\n[*] Term 1 Exams in database:")
    for exam_id, name, term in term1_exams:
        cur.execute("SELECT COUNT(*) FROM marks WHERE exam_id = %s AND pupil_id = %s", (exam_id, pupil_id))
        mark_count = cur.fetchone()[0]
        print(f"  - ID {exam_id}: {name} ({mark_count} marks for this pupil)")

    # Check if both Midterm and End_term exist for Term 1
    midterm_count = 0
    endterm_count = 0

    for exam_id, name, term in term1_exams:
        if 'mid' in name.lower():
            midterm_count += 1
        elif 'end' in name.lower():
            endterm_count += 1

    print(f"\n[SUMMARY]")
    print(f"  Midterm exams for Term 1: {midterm_count}")
    print(f"  End_term exams for Term 1: {endterm_count}")

    if midterm_count > 0 and endterm_count > 0:
        print(f"\n[SUCCESS] Both Midterm and End_term available for Term 1!")
        print(f"  -> The teacher can select Term 1 and print COMBINED report")
    else:
        print(f"\n[INFO] Need to create missing exams for Term 1")

    # Also check Terms 2 and 3
    for term_num in [2, 3]:
        cur.execute("SELECT COUNT(*) FROM exams WHERE term = %s", (term_num,))
        count = cur.fetchone()[0]
        print(f"\n[*] Term {term_num}: {count} exams")

    cur.close(); conn.close()

if __name__ == '__main__':
    verify_print_data()
