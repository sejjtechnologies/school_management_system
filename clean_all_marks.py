#!/usr/bin/env python3
"""
Clean all marks from database for all pupils, classes, streams, and terms.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def clean_all_marks():
    """Delete all marks from database"""
    
    database_url = os.getenv('DATABASE_URL')
    
    print("\n" + "=" * 100)
    print("[CLEAN ALL MARKS]")
    print("=" * 100)
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Get current mark counts by exam
        print("\n[*] Current marks by exam:\n")
        
        cur.execute("""
            SELECT e.id, e.name, e.term, COUNT(m.id) as mark_count
            FROM exams e
            LEFT JOIN marks m ON e.id = m.exam_id
            GROUP BY e.id, e.name, e.term
            ORDER BY e.id
        """)
        
        total_marks = 0
        print(f"{'Exam ID':<10} {'Exam Name':<30} {'Term':<8} {'Marks':<10}")
        print("-" * 100)
        
        for row in cur.fetchall():
            exam_id, exam_name, term, mark_count = row
            total_marks += mark_count
            print(f"{exam_id:<10} {exam_name:<30} {term:<8} {mark_count:<10}")
        
        print()
        print(f"[INFO] Total marks to delete: {total_marks}")
        print("\n[*] Deleting all marks...\n")
        
        # Delete all marks
        cur.execute("DELETE FROM marks")
        deleted_count = cur.rowcount
        
        conn.commit()
        
        print(f"[OK] Deleted {deleted_count} marks\n")
        
        # Verify deletion
        print("[*] Verifying deletion...\n")
        
        cur.execute("""
            SELECT e.id, e.name, e.term, COUNT(m.id) as mark_count
            FROM exams e
            LEFT JOIN marks m ON e.id = m.exam_id
            GROUP BY e.id, e.name, e.term
            ORDER BY e.id
        """)
        
        print(f"{'Exam ID':<10} {'Exam Name':<30} {'Term':<8} {'Marks':<10}")
        print("-" * 100)
        
        remaining_marks = 0
        for row in cur.fetchall():
            exam_id, exam_name, term, mark_count = row
            remaining_marks += mark_count
            print(f"{exam_id:<10} {exam_name:<30} {term:<8} {mark_count:<10}")
        
        print()
        print(f"[SUMMARY] Remaining marks in database: {remaining_marks}")
        print(f"[SUCCESS] All {deleted_count} marks deleted successfully!\n")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    clean_all_marks()
