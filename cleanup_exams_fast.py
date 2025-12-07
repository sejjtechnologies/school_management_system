#!/usr/bin/env python3
"""
Fast cleanup using raw SQL: Keep only Midterm and End_term for Term 1.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.marks_model import Exam, Mark
from sqlalchemy import text

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def cleanup_exams_fast():
    """Fast cleanup using raw SQL"""
    
    with app.app_context():
        print("\n[*] Starting fast cleanup...\n")
        
        try:
            # Show current status
            print("=" * 100)
            print("[CURRENT STATUS]")
            print("=" * 100)
            
            result = db.session.execute(text("""
                SELECT 
                    e.id, e.name, e.term, e.year,
                    COUNT(m.id) as mark_count
                FROM exam e
                LEFT JOIN mark m ON e.id = m.exam_id
                GROUP BY e.id, e.name, e.term, e.year
                ORDER BY e.id
            """))
            
            print(f"{'ID':<5} {'Name':<30} {'Term':<8} {'Year':<8} {'Marks':<10}")
            print("-" * 100)
            
            all_records = result.fetchall()
            for row in all_records:
                print(f"{row[0]:<5} {row[1]:<30} {row[2]:<8} {row[3]:<8} {row[4]:<10}")
            
            print()
            print("=" * 100)
            print("[ANALYSIS]")
            print("=" * 100)
            
            # Find exams to keep and delete
            keep_ids = []
            delete_ids = []
            
            for row in all_records:
                exam_id, name, term, year, mark_count = row
                if (name in ['Midterm', 'End_term', 'End_Term']) and term == 1:
                    keep_ids.append(exam_id)
                    print(f"✓ KEEP - ID {exam_id}: {name} (Term {term}, Year {year}) - {mark_count} marks")
                else:
                    delete_ids.append(exam_id)
                    print(f"✗ DELETE - ID {exam_id}: {name} (Term {term}, Year {year}) - {mark_count} marks")
            
            print()
            print(f"Total to KEEP: {len(keep_ids)}")
            print(f"Total to DELETE: {len(delete_ids)}")
            
            if not delete_ids:
                print("\n[OK] Nothing to delete!\n")
                return
            
            print()
            print("=" * 100)
            print("[DELETING]")
            print("=" * 100)
            
            # Delete marks for exams to delete
            delete_list_str = ','.join(str(id) for id in delete_ids)
            
            print(f"\n[*] Deleting marks for exams: {delete_list_str}")
            result = db.session.execute(text(f"""
                DELETE FROM mark 
                WHERE exam_id IN ({delete_list_str})
            """))
            marks_deleted = result.rowcount
            print(f"[OK] Deleted {marks_deleted} marks")
            
            # Delete exams
            print(f"\n[*] Deleting {len(delete_ids)} exams...")
            result = db.session.execute(text(f"""
                DELETE FROM exam 
                WHERE id IN ({delete_list_str})
            """))
            exams_deleted = result.rowcount
            print(f"[OK] Deleted {exams_deleted} exams")
            
            # Commit
            db.session.commit()
            print("\n[OK] Committed to database!")
            
            # Show final status
            print()
            print("=" * 100)
            print("[FINAL STATUS]")
            print("=" * 100)
            
            result = db.session.execute(text("""
                SELECT 
                    e.id, e.name, e.term, e.year,
                    COUNT(m.id) as mark_count
                FROM exam e
                LEFT JOIN mark m ON e.id = m.exam_id
                GROUP BY e.id, e.name, e.term, e.year
                ORDER BY e.id
            """))
            
            print(f"{'ID':<5} {'Name':<30} {'Term':<8} {'Year':<8} {'Marks':<10}")
            print("-" * 100)
            
            for row in result:
                print(f"{row[0]:<5} {row[1]:<30} {row[2]:<8} {row[3]:<8} {row[4]:<10}")
            
            print("\n[SUCCESS] Cleanup complete!\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    cleanup_exams_fast()
