#!/usr/bin/env python3
"""
Verify counts for Term 1 End_term exam.
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def verify():
    db = os.getenv('DATABASE_URL')
    if not db:
        print('DATABASE_URL not set')
        return
    conn = psycopg2.connect(db)
    cur = conn.cursor()
    # find end_term exam
    cur.execute("SELECT id, name FROM exams WHERE term=1 AND name IN ('End_term','End Term','End_Term','EndTerm') ORDER BY id")
    row = cur.fetchone()
    if not row:
        # try fuzzy
        cur.execute("SELECT id, name FROM exams WHERE term=1 AND (name ILIKE '%end%term%' OR name ILIKE '%end%') ORDER BY id")
        row = cur.fetchone()
    if not row:
        print('End_term exam for term 1 not found')
        cur.close(); conn.close(); return
    exam_id, exam_name = row
    print(f'Found exam id {exam_id} name "{exam_name}"')
    # total marks
    cur.execute('SELECT COUNT(*) FROM marks WHERE exam_id=%s', (exam_id,))
    total = cur.fetchone()[0]
    print(f'Total marks for exam {exam_id}: {total}')
    # verify per class/stream
    cur.execute("""
        SELECT c.name, s.name, COUNT(m.id) FROM pupils p
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        LEFT JOIN marks m ON p.id = m.pupil_id AND m.exam_id = %s
        GROUP BY c.name, s.name
        ORDER BY c.name, s.name
    """, (exam_id,))
    print('\nBreakdown by class/stream:')
    rows = cur.fetchall()
    for r in rows:
        class_name, stream_name, cnt = r
        print(f'{class_name:6} {stream_name:8} -> {cnt}')
    cur.close(); conn.close()

if __name__=='__main__':
    verify()
