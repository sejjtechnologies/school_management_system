#!/usr/bin/env python3
"""
Insert realistic marks for Midterm and End_term exams for pupils in ID range 30-98.
Only inserts marks that are missing (not already in database).
Generates random marks for all subjects to allow the system to rank pupils.

Usage:
    python insert_missing_marks.py                    # dry run: show plan
    python insert_missing_marks.py --apply            # apply: insert marks
    python insert_missing_marks.py --apply --verbose  # apply with detailed output
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


def insert_missing_marks(apply=False, verbose=False, id_range=(30, 98)):
    """Insert marks for pupils in specified ID range - only missing marks"""
    
    with app.app_context():
        print("\n[*] Connecting to database...\n")
        
        start_id, end_id = id_range
        
        # Query to find pupils and their missing marks
        query_str = """
        SELECT DISTINCT
            p.id as pupil_id,
            p.first_name || ' ' || p.last_name as pupil_name,
            s.id as subject_id,
            s.name as subject_name,
            e.id as exam_id,
            e.name as exam_name
        FROM pupils p
        CROSS JOIN subjects s
        CROSS JOIN exams e
        WHERE p.id >= :start_id AND p.id <= :end_id
        AND (e.name = 'Midterm' OR e.name = 'End_term')
        AND NOT EXISTS (
            SELECT 1 FROM marks m 
            WHERE m.pupil_id = p.id 
            AND m.subject_id = s.id 
            AND m.exam_id = e.id
        )
        ORDER BY p.id, s.id, e.name
        """
        
        try:
            result = db.session.execute(
                text(query_str),
                {"start_id": start_id, "end_id": end_id}
            )
            missing_marks = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return
        
        if not missing_marks:
            print(f"[OK] All pupils in range {start_id}-{end_id} already have marks for both exams.\n")
            return
        
        print(f"[OK] Found {len(missing_marks)} missing marks to insert")
        print(f"[OK] ID Range: {start_id}-{end_id}\n")
        
        # Display plan
        print("=" * 110)
        print("[PLAN] MISSING MARKS INSERTION PLAN")
        print("=" * 110)
        print()
        
        # Group by pupil and exam
        by_pupil_exam = {}
        for pupil_id, pupil_name, subject_id, subject_name, exam_id, exam_name in missing_marks:
            key = f"{pupil_id}_{exam_id}"
            if key not in by_pupil_exam:
                by_pupil_exam[key] = {
                    'pupil_id': pupil_id,
                    'pupil_name': pupil_name,
                    'exam_id': exam_id,
                    'exam_name': exam_name,
                    'subjects': []
                }
            by_pupil_exam[key]['subjects'].append({'id': subject_id, 'name': subject_name})
        
        print(f"[SUMMARY] Total missing marks: {len(missing_marks)}")
        print(f"[SUMMARY] Pupils to update: {len(set(m[0] for m in missing_marks))}")
        
        # Count by exam
        midterm_count = sum(1 for m in missing_marks if m[5] == 'Midterm')
        endterm_count = sum(1 for m in missing_marks if m[5] == 'End_term')
        
        print(f"[SUMMARY] Missing Midterm marks: {midterm_count}")
        print(f"[SUMMARY] Missing End_term marks: {endterm_count}\n")
        
        print(f"{'Pupil':<20} {'Exam':<15} {'Subjects':<20}")
        print("-" * 110)
        
        for key in sorted(by_pupil_exam.keys()):
            item = by_pupil_exam[key]
            subject_names = ', '.join([s['name'] for s in item['subjects']])
            print(f"{item['pupil_name']:<20} {item['exam_name']:<15} {subject_names:<20}")
        
        print()
        
        if not apply:
            print("[RUN] Run with --apply to perform insertions.")
            return
        
        # ====================================================================
        # APPLY: Perform insertions
        # ====================================================================
        
        print("=" * 110)
        print("[SAVE] APPLYING MARK INSERTIONS")
        print("=" * 110)
        print()
        
        total_inserted = 0
        
        try:
            for pupil_id, pupil_name, subject_id, subject_name, exam_id, exam_name in missing_marks:
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
                
                if verbose:
                    print(f"[ADD] {pupil_name} - {subject_name} ({exam_name}): {mark_value:.2f}")
            
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
            CAST(AVG(m.score) AS NUMERIC(10,2)) as avg_score,
            MIN(m.score) as min_score,
            MAX(m.score) as max_score
        FROM marks m
        JOIN exams e ON m.exam_id = e.id
        JOIN pupils p ON m.pupil_id = p.id
        WHERE p.id >= :start_id AND p.id <= :end_id
        AND (e.name = 'Midterm' OR e.name = 'End_term')
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
        print("[INFO] Recent inserted marks sample (first 10):")
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
        AND (e.name = 'Midterm' OR e.name = 'End_term')
        ORDER BY m.id DESC
        LIMIT 10
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
        
        print(f"{'Pupil':<20} {'Subject':<20} {'Exam':<15} {'Mark':<10}")
        print("-" * 110)
        
        for pupil_name, subject_name, exam_name, mark in sample_rows:
            print(f"{pupil_name:<20} {subject_name:<20} {exam_name:<15} {mark:<10.2f}")
        
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Insert missing marks for Midterm and End_term exams'
    )
    parser.add_argument('--apply', action='store_true', help='Apply insertions (default is dry-run)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output during insertion')
    parser.add_argument('--id-start', type=int, default=30, help='Start of pupil ID range (default: 30)')
    parser.add_argument('--id-end', type=int, default=98, help='End of pupil ID range (default: 98)')
    
    args = parser.parse_args()
    
    try:
        insert_missing_marks(
            apply=args.apply,
            verbose=args.verbose,
            id_range=(args.id_start, args.id_end)
        )
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
