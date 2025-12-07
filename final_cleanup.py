#!/usr/bin/env python3
"""
Direct SQL cleanup - delete unwanted exams using PostgreSQL connection.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def final_cleanup():
    """Delete exam records directly via psycopg2"""
    
    database_url = os.getenv('DATABASE_URL')
    
    print("\n[*] Final cleanup - deleting exam records via SQL...\n")
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Get exams to delete
        cur.execute("""
            SELECT id, name, term, year FROM exams
            WHERE NOT (name IN ('Midterm', 'End_term', 'End_Term') AND term = 1)
            ORDER BY id
        """)
        
        exams_to_delete = cur.fetchall()
        
        if not exams_to_delete:
            print("[OK] No exams to delete.\n")
            cur.close()
            conn.close()
            return
        
        delete_ids = [str(e[0]) for e in exams_to_delete]
        print(f"[*] Deleting {len(delete_ids)} exams: {delete_ids}\n")
        
        # Delete marks
        cur.execute(f"""
            DELETE FROM marks 
            WHERE exam_id IN ({','.join(delete_ids)})
        """)
        marks_deleted = cur.rowcount
        print(f"  [OK] Deleted {marks_deleted} marks")
        
        # Delete exams
        cur.execute(f"""
            DELETE FROM exams 
            WHERE id IN ({','.join(delete_ids)})
        """)
        exams_deleted = cur.rowcount
        print(f"  [OK] Deleted {exams_deleted} exams\n")
        
        conn.commit()
        
        # Show final status
        print("=" * 100)
        print("[FINAL STATUS]")
        print("=" * 100)
        print()
        
        cur.execute("""
            SELECT e.id, e.name, e.term, e.year, COUNT(m.id) as mark_count
            FROM exams e
            LEFT JOIN marks m ON e.id = m.exam_id
            GROUP BY e.id, e.name, e.term, e.year
            ORDER BY e.id
        """)
        
        print(f"{'ID':<5} {'Name':<30} {'Term':<8} {'Year':<8} {'Marks':<10}")
        print("-" * 100)
        
        for row in cur.fetchall():
            print(f"{row[0]:<5} {row[1]:<30} {row[2]:<8} {row[3]:<8} {row[4]:<10}")
        
        print()
        
        # Count total
        cur.execute("SELECT COUNT(*) FROM exams")
        total = cur.fetchone()[0]
        print(f"[SUCCESS] Database now has {total} exams (expected 2)\n")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    final_cleanup()
