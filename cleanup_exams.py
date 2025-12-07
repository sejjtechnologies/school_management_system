#!/usr/bin/env python3
"""
Clean up exams: Keep only Midterm and End_term for Term 1.
Delete all other term exams and their marks.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.class_model import Class
from models.stream_model import Stream
from models.register_pupils import Pupil
from models.marks_model import Exam, Mark
from sqlalchemy import text

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def cleanup_exams():
    """Keep only Term 1 Midterm and End_term exams"""
    
    with app.app_context():
        print("\n[*] Checking exams in database...\n")
        
        # Get all exams
        exams = Exam.query.all()
        
        print("=" * 100)
        print("[CURRENT] All exams in database:")
        print("=" * 100)
        print()
        print(f"{'ID':<5} {'Name':<30} {'Term':<8} {'Year':<8} {'Marks Count':<15}")
        print("-" * 100)
        
        exams_to_keep = []
        exams_to_delete = []
        
        for exam in exams:
            mark_count = Mark.query.filter_by(exam_id=exam.id).count()
            print(f"{exam.id:<5} {exam.name:<30} {exam.term:<8} {exam.year:<8} {mark_count:<15}")
            
            # Keep only Midterm and End_term for Term 1
            if (exam.name in ['Midterm', 'End_term', 'End_Term']) and exam.term == 1:
                exams_to_keep.append(exam)
            else:
                exams_to_delete.append(exam)
        
        print()
        print("=" * 100)
        print("[KEEP] These exams will be kept:")
        print("=" * 100)
        print()
        
        for exam in exams_to_keep:
            mark_count = Mark.query.filter_by(exam_id=exam.id).count()
            print(f"  ✓ {exam.name} (Term {exam.term}, Year {exam.year}) - {mark_count} marks")
        
        print()
        print("=" * 100)
        print("[DELETE] These exams will be deleted:")
        print("=" * 100)
        print()
        
        total_marks_to_delete = 0
        
        for exam in exams_to_delete:
            mark_count = Mark.query.filter_by(exam_id=exam.id).count()
            total_marks_to_delete += mark_count
            print(f"  ✗ {exam.name} (Term {exam.term}, Year {exam.year}) - {mark_count} marks")
        
        print()
        print(f"[SUMMARY] Total marks to delete: {total_marks_to_delete}")
        print(f"[SUMMARY] Total exams to delete: {len(exams_to_delete)}")
        print()
        print("[RUN] Run with --apply to perform deletion.\n")

def apply_cleanup():
    """Apply cleanup"""
    
    with app.app_context():
        print("\n[*] Starting cleanup...\n")
        
        exams = Exam.query.all()
        
        exams_to_delete = []
        exams_to_keep = []
        
        for exam in exams:
            if (exam.name in ['Midterm', 'End_term', 'End_Term']) and exam.term == 1:
                exams_to_keep.append(exam)
            else:
                exams_to_delete.append(exam)
        
        if not exams_to_delete:
            print("[OK] No exams to delete.\n")
            return
        
        print("=" * 100)
        print("[DELETE] DELETING UNWANTED EXAMS AND MARKS")
        print("=" * 100)
        print()
        
        try:
            # Get IDs of exams to delete
            delete_ids = [exam.id for exam in exams_to_delete]
            
            # Delete all marks for these exams in bulk
            total_marks_deleted = Mark.query.filter(Mark.exam_id.in_(delete_ids)).delete(synchronize_session=False)
            print(f"[DELETED MARKS] {total_marks_deleted} marks removed")
            
            # Delete all exams
            for exam in exams_to_delete:
                db.session.delete(exam)
                print(f"[DELETED EXAM] {exam.name} (Term {exam.term})")
            
            db.session.commit()
            print(f"\n[OK] Cleanup complete!\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Show final status
        print("=" * 100)
        print("[FINAL] Remaining exams:")
        print("=" * 100)
        print()
        
        final_exams = Exam.query.all()
        for exam in final_exams:
            mark_count = Mark.query.filter_by(exam_id=exam.id).count()
            print(f"  ✓ {exam.name} (Term {exam.term}, Year {exam.year}) - {mark_count} marks")
        
        print()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Clean up exams - keep only Term 1 Midterm and End_term')
    parser.add_argument('--apply', action='store_true', help='Apply cleanup')
    args = parser.parse_args()
    
    try:
        if args.apply:
            apply_cleanup()
        else:
            cleanup_exams()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
