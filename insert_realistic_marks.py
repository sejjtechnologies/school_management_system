#!/usr/bin/env python3
"""
Insert realistic marks for Midterm and End_term exams for pupils in ID range 30-98.
Generates random marks for all subjects to allow the system to rank pupils.

Mark ranges:
- Excellent: 80-100
- Good: 65-79
- Average: 50-64
- Below Average: 30-49
- Poor: 0-29

Usage:
    python insert_realistic_marks.py                    # dry run: show plan
    python insert_realistic_marks.py --apply            # apply: insert marks
    python insert_realistic_marks.py --apply --verbose  # apply with detailed output
"""

import os
import sys
import argparse
import random
from dotenv import load_dotenv
from datetime import date
from flask import Flask
from models.user_models import db
from models.class_model import Class
from models.stream_model import Stream
from models.register_pupils import Pupil
from models.marks_model import Mark, Exam, Subject
from sqlalchemy import text

# Load environment
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Mark distribution weights for realistic data
MARK_RANGES = {
    "excellent": {"range": (80, 100), "weight": 15},
    "good": {"range": (65, 79), "weight": 25},
    "average": {"range": (50, 64), "weight": 35},
    "below_average": {"range": (30, 49), "weight": 20},
    "poor": {"range": (0, 29), "weight": 5}
}

EXAM_TYPES = {
    "midterm": "Midterm",
    "endterm": "End_term"
}


def get_random_mark():
    """Generate a realistic random mark based on weighted distribution"""
    rand = random.randint(1, 100)
    cumulative = 0
    
    for category, data in MARK_RANGES.items():
        cumulative += data["weight"]
        if rand <= cumulative:
            min_mark, max_mark = data["range"]
            return round(random.uniform(min_mark, max_mark), 2)
    
    # Fallback
    return round(random.uniform(MARK_RANGES["average"]["range"][0], MARK_RANGES["average"]["range"][1]), 2)


def insert_marks_for_pupils(apply=False, verbose=False, id_range=(30, 98)):
    """Insert marks for pupils in specified ID range"""
    
    with app.app_context():
        print("\n[*] Connecting to database...\n")
        
        # Get pupils in ID range
        start_id, end_id = id_range
        
        try:
            pupils = Pupil.query.filter(
                Pupil.id >= start_id,
                Pupil.id <= end_id
            ).all()
        except Exception as e:
            print(f"[ERROR] Failed to query pupils: {e}")
            return
        
        if not pupils:
            print(f"[ERROR] No pupils found in ID range {start_id}-{end_id}")
            return
        
        print(f"[OK] Found {len(pupils)} pupils in ID range {start_id}-{end_id}\n")
        
        # Get all subjects
        try:
            subjects = Subject.query.all()
        except Exception as e:
            print(f"[ERROR] Failed to query subjects: {e}")
            return
        
        if not subjects:
            print("[ERROR] No subjects found in database")
            return
        
        print(f"[OK] Found {len(subjects)} subjects: {[s.name for s in subjects]}\n")
        
        # Get or create exams for Midterm and End_term
        try:
            # Get the generic Midterm exam
            midterm_exam = Exam.query.filter(
                Exam.name == "Midterm"
            ).first()
            
            # Get the generic End_term exam
            endterm_exam = Exam.query.filter(
                Exam.name == "End_term"
            ).first()
            
            # If not found, try alternative names
            if not midterm_exam:
                midterm_exam = Exam.query.filter(Exam.name.ilike('%Midterm%')).first()
            if not endterm_exam:
                endterm_exam = Exam.query.filter(
                    (Exam.name.ilike('%End_term%')) | (Exam.name.ilike('%End Term%'))
                ).first()
        except Exception as e:
            print(f"[ERROR] Failed to query exams: {e}")
            return
        
        if not midterm_exam:
            print("[WARNING] No Midterm exam found - creating one")
            midterm_exam = Exam(name="Midterm", term=1, year=2025)
            db.session.add(midterm_exam)
        
        if not endterm_exam:
            print("[WARNING] No End_term exam found - creating one")
            endterm_exam = Exam(name="End_term", term=3, year=2025)
            db.session.add(endterm_exam)
        
        if apply and (not midterm_exam or not endterm_exam):
            try:
                db.session.flush()
            except Exception as e:
                print(f"[ERROR] Failed to create exams: {e}")
                db.session.rollback()
                return
        
        print(f"[OK] Using Midterm exam: {midterm_exam.name}")
        print(f"[OK] Using End_term exam: {endterm_exam.name}\n")
        
        midterm_exams = [midterm_exam]
        endterm_exams = [endterm_exam]
        
        # Build insertion plan
        total_marks_to_insert = 0
        plan = []
        
        for exam_type_key, exam_list in [("midterm", midterm_exams), ("endterm", endterm_exams)]:
            for exam in exam_list:
                for pupil in pupils:
                    for subject in subjects:
                        # Check if mark already exists
                        existing = Mark.query.filter_by(
                            pupil_id=pupil.id,
                            subject_id=subject.id,
                            exam_id=exam.id
                        ).first()
                        
                        if not existing:
                            plan.append({
                                'pupil_id': pupil.id,
                                'pupil_name': f"{pupil.first_name} {pupil.last_name}",
                                'subject_id': subject.id,
                                'subject_name': subject.name,
                                'exam_id': exam.id,
                                'exam_name': exam.name
                            })
                            total_marks_to_insert += 1
        
        # Display plan
        print("=" * 110)
        print("[PLAN] MARKS INSERTION PLAN")
        print("=" * 110)
        print()
        
        if not plan:
            print("[OK] All pupils in range already have marks for all subjects and exams.")
            return
        
        print(f"[SUMMARY] Total marks to insert: {total_marks_to_insert}")
        print(f"[SUMMARY] Pupils in range: {len(pupils)}")
        print(f"[SUMMARY] Subjects: {len(subjects)}")
        print(f"[SUMMARY] Exams: {len(midterm_exams) + len(endterm_exams)}")
        print(f"[SUMMARY] ID Range: {start_id}-{end_id}\n")
        
        if not apply:
            print("[RUN] Run with --apply to perform insertions.")
            print("[INFO] Sample pupils to be updated:")
            print("-" * 110)
            print(f"{'#':<4} {'Pupil ID':<10} {'Name':<25} {'Exams':<20} {'Subjects':<15}")
            print("-" * 110)
            
            pupils_to_show = pupils[:10]
            for idx, pupil in enumerate(pupils_to_show, 1):
                exam_count = len(midterm_exams) + len(endterm_exams)
                subject_count = len(subjects)
                total_per_pupil = exam_count * subject_count
                print(f"{idx:<4} {pupil.id:<10} {f'{pupil.first_name} {pupil.last_name}':<25} "
                      f"{exam_count:<20} {total_per_pupil:<15}")
            
            print()
            return
        
        # ====================================================================
        # APPLY: Perform insertions
        # ====================================================================
        
        print("=" * 110)
        print("[SAVE] APPLYING MARK INSERTIONS")
        print("=" * 110)
        print()
        
        total_inserted = 0
        exams_processed = {}
        
        try:
            for item in plan:
                pupil_id = item['pupil_id']
                subject_id = item['subject_id']
                exam_id = item['exam_id']
                exam_name = item['exam_name']
                
                # Track exams
                exam_key = f"{exam_id}_{exam_name}"
                if exam_key not in exams_processed:
                    exams_processed[exam_key] = 0
                
                # Generate realistic mark
                mark_value = get_random_mark()
                
                # Create mark record
                mark = Mark(
                    pupil_id=pupil_id,
                    subject_id=subject_id,
                    exam_id=exam_id,
                    score=mark_value
                )
                
                db.session.add(mark)
                total_inserted += 1
                exams_processed[exam_key] += 1
                
                if verbose and total_inserted % 100 == 0:
                    print(f"[ADD] Inserted {total_inserted} marks...")
            
            # Commit all at once
            db.session.commit()
            print(f"\n[OK] Successfully inserted {total_inserted} marks into database.\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Insertion failed: {e}")
            raise
        
        # ====================================================================
        # VERIFICATION
        # ====================================================================
        
        print("=" * 110)
        print("[SUMMARY] FINAL VERIFICATION")
        print("=" * 110)
        print()
        
        verify_query = """
        SELECT 
            e.name as exam_name,
            COUNT(DISTINCT m.pupil_id) as pupils_with_marks,
            COUNT(DISTINCT m.subject_id) as subjects_marked,
            COUNT(m.id) as total_marks,
            ROUND(AVG(m.score), 2) as avg_score,
            MIN(m.score) as min_score,
            MAX(m.score) as max_score
        FROM marks m
        JOIN exams e ON m.exam_id = e.id
        JOIN pupils p ON m.pupil_id = p.id
        WHERE p.id >= :start_id AND p.id <= :end_id
        GROUP BY e.id, e.name
        ORDER BY e.name
        """
        
        try:
            result = db.session.execute(
                text(verify_query),
                {"start_id": start_id, "end_id": end_id}
            )
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Verification query failed: {e}")
            return
        
        print(f"{'Exam':<15} {'Pupils':<10} {'Subjects':<12} {'Total Marks':<15} "
              f"{'Avg':<10} {'Min':<10} {'Max':<10}")
        print("-" * 110)
        
        for exam_name, pupils_marked, subjects, total_marks, avg_score, min_score, max_score in rows:
            print(f"{exam_name:<15} {pupils_marked:<10} {subjects:<12} {total_marks:<15} "
                  f"{avg_score:<10.2f} {min_score:<10.2f} {max_score:<10.2f}")
        
        print()
        
        # Sample marks by performance category
        print("[INFO] Mark Distribution Sample (first 5 marks):")
        print("-" * 110)
        
        sample_query = """
        SELECT 
            p.first_name || ' ' || p.last_name as pupil_name,
            s.name as subject_name,
            e.name as exam_name,
            m.score as mark
        FROM marks m
        JOIN pupils p ON m.pupil_id = p.id
        JOIN subjects s ON m.subject_id = s.id
        JOIN exams e ON m.exam_id = e.id
        WHERE p.id >= :start_id AND p.id <= :end_id
        ORDER BY m.id DESC
        LIMIT 5
        """
        
        try:
            result = db.session.execute(
                text(sample_query),
                {"start_id": start_id, "end_id": end_id}
            )
            sample_rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Sample query failed: {e}")
            return
        
        print(f"{'Pupil':<20} {'Subject':<15} {'Exam':<15} {'Mark':<10}")
        print("-" * 110)
        
        for pupil_name, subject_name, exam_name, mark in sample_rows:
            print(f"{pupil_name:<20} {subject_name:<15} {exam_name:<15} {mark:<10.2f}")
        
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Insert realistic marks for Midterm and End_term exams'
    )
    parser.add_argument('--apply', action='store_true', help='Apply insertions (default is dry-run)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output during insertion')
    parser.add_argument('--id-start', type=int, default=30, help='Start of pupil ID range (default: 30)')
    parser.add_argument('--id-end', type=int, default=98, help='End of pupil ID range (default: 98)')
    
    args = parser.parse_args()
    
    try:
        insert_marks_for_pupils(
            apply=args.apply,
            verbose=args.verbose,
            id_range=(args.id_start, args.id_end)
        )
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
