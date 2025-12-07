#!/usr/bin/env python3
"""
Delete the duplicate/empty End_Term exam (ID 31)
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def cleanup_empty_exam():
    db = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db)
    cur = conn.cursor()

    try:
        print("\n" + "="*100)
        print("[CLEANUP: Remove empty duplicate exams]")
        print("="*100)

        # Find exams with 0 marks
        cur.execute("""
            SELECT e.id, e.name, e.term, COUNT(m.id) as mark_count
            FROM exams e
            LEFT JOIN marks m ON e.id = m.exam_id
            GROUP BY e.id, e.name, e.term
            HAVING COUNT(m.id) = 0
            ORDER BY e.term, e.id
        """)

        empty_exams = cur.fetchall()

        if not empty_exams:
            print("\n[OK] No empty exams found\n")
            cur.close(); conn.close(); return

        print("\n[FOUND] Empty exams with 0 marks:")
        print(f"{'Exam ID':<10} {'Name':<30} {'Term':<8} {'Marks':<8}")
        print("-"*70)

        for exam_id, name, term, mark_count in empty_exams:
            print(f"{exam_id:<10} {name:<30} {term:<8} {mark_count:<8}")

        # Delete only the "End_Term" (with underscore) duplicates, keep "End Term" (with space)
        to_delete = [eid for eid, name, term, count in empty_exams if 'End_Term' in name or 'End_term' in name]

        if to_delete:
            print(f"\n[*] Deleting {len(to_delete)} empty duplicate exams...")

            for exam_id in to_delete:
                # Delete related reports first
                cur.execute("DELETE FROM reports WHERE exam_id = %s", (exam_id,))
                # Delete the exam
                cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))

            conn.commit()
            print(f"[OK] Deleted {len(to_delete)} empty exams")

        # Verify
        print("\n[VERIFICATION - Final exam status]")
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
            total = 0
            for exam_id, name, count in cur.fetchall():
                total += count
                status = "✓" if count > 0 else "✗"
                print(f"  {status} ID {exam_id} ({name:20}): {count:6} marks")
            print(f"    TOTAL: {total} marks\n")

        print("[SUCCESS] Cleanup complete!\n")

    except Exception as e:
        print(f'\n[ERROR] {e}\n')
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    cleanup_empty_exam()
