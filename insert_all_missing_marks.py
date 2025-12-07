#!/usr/bin/env python3
"""
Insert realistic marks for ALL missing Midterm and End_term exams for all pupils.
Connects to Neon database using .env configuration.
Generates realistic marks for all subjects to enable system ranking.

Mark distribution:
- Excellent: 80-100 (15% weight)
- Good: 65-79 (25% weight)
- Average: 50-64 (35% weight)
- Below Average: 30-49 (20% weight)
- Poor: 0-29 (5% weight)

Usage:
    python insert_all_missing_marks.py                    # dry run: show plan
    python insert_all_missing_marks.py --apply            # apply: insert marks
    python insert_all_missing_marks.py --apply --verbose  # apply with detailed output
"""

import os
import sys
import argparse
import random
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.class_model import Class
from models.stream_model import Stream
from models.register_pupils import Pupil
from models.marks_model import Mark, Exam, Subject
from sqlalchemy import text

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
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


def insert_all_missing_marks(apply=False, verbose=False):
    """Insert marks for all pupils missing both Midterm and End_term"""
    
    with app.app_context():
        print("\n[*] Connecting to Neon database...\n")
        
        # Query to find ALL missing marks (both Midterm and End_term)
        query_str = """
        SELECT DISTINCT
            p.id as pupil_id,
            p.first_name || ' ' || p.last_name as pupil_name,
            c.name as class_name,
            s.name as stream_name,
            sub.id as subject_id,
            sub.name as subject_name,
            e.id as exam_id,
            e.name as exam_name
        FROM pupils p
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        CROSS JOIN subjects sub
        CROSS JOIN exams e
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        AND (e.name = 'Midterm' OR e.name = 'End_term' OR e.name LIKE '%End%')
        AND NOT EXISTS (
            SELECT 1 FROM marks m 
            WHERE m.pupil_id = p.id 
            AND m.subject_id = sub.id 
            AND m.exam_id = e.id
        )
        ORDER BY p.id, sub.id, e.name
        """
        
        try:
            result = db.session.execute(text(query_str))
            missing_marks = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return
        
        if not missing_marks:
            print("[OK] All pupils already have marks for both Midterm and End_term.\n")
            return
        
        print(f"[OK] Found {len(missing_marks)} missing marks to insert")
        
        # Analyze by exam and subject
        by_exam = {}
        by_subject = {}
        by_class_stream = {}
        
        for row in missing_marks:
            pupil_id, pupil_name, class_name, stream_name, subject_id, subject_name, exam_id, exam_name = row
            
            exam_key = exam_name
            if exam_key not in by_exam:
                by_exam[exam_key] = 0
            by_exam[exam_key] += 1
            
            subject_key = subject_name
            if subject_key not in by_subject:
                by_subject[subject_key] = 0
            by_subject[subject_key] += 1
            
            cs_key = f"{class_name} - {stream_name}"
            if cs_key not in by_class_stream:
                by_class_stream[cs_key] = 0
            by_class_stream[cs_key] += 1
        
        # Display plan
        print("=" * 120)
        print("[PLAN] MISSING MARKS INSERTION PLAN - ALL PUPILS")
        print("=" * 120)
        print()
        
        print(f"[SUMMARY] Total missing marks: {len(missing_marks)}")
        print(f"[SUMMARY] Total pupils affected: {len(set(m[0] for m in missing_marks))}")
        print(f"[SUMMARY] Total subjects: {len(by_subject)}")
        print(f"[SUMMARY] Total exams: {len(by_exam)}\n")
        
        print("[BREAKDOWN] Missing marks by exam:")
        print("-" * 120)
        for exam_name in sorted(by_exam.keys()):
            count = by_exam[exam_name]
            print(f"  - {exam_name}: {count} marks")
        
        print()
        print("[BREAKDOWN] Missing marks by subject:")
        print("-" * 120)
        for subject_name in sorted(by_subject.keys()):
            count = by_subject[subject_name]
            print(f"  - {subject_name}: {count} marks")
        
        print()
        print("[BREAKDOWN] Missing marks by class/stream (sample):")
        print("-" * 120)
        for cs_name in sorted(by_class_stream.keys())[:10]:
            count = by_class_stream[cs_name]
            print(f"  - {cs_name}: {count} marks")
        
        if len(by_class_stream) > 10:
            print(f"  ... and {len(by_class_stream) - 10} more class/stream combinations")
        
        print()
        
        if not apply:
            print("[RUN] Run with --apply to perform insertions.")
            return
        
        # ====================================================================
        # APPLY: Perform insertions
        # ====================================================================
        
        print("=" * 120)
        print("[SAVE] APPLYING MARK INSERTIONS FOR ALL MISSING MARKS")
        print("=" * 120)
        print()
        
        total_inserted = 0
        batch_size = 500
        marks_batch = []
        
        try:
            for row in missing_marks:
                pupil_id, pupil_name, class_name, stream_name, subject_id, subject_name, exam_id, exam_name = row
                
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
                marks_batch.append((pupil_name, subject_name, exam_name, mark_value))
                
                if verbose and len(marks_batch) <= 20:
                    print(f"[ADD] {pupil_name} - {subject_name} ({exam_name}): {mark_value:.2f}")
                
                # Flush every batch_size records
                if total_inserted % batch_size == 0:
                    try:
                        db.session.flush()
                        print(f"[+] Flushed {total_inserted} marks...")
                    except Exception as e:
                        print(f"[ERROR] Flush failed at {total_inserted} marks: {e}")
                        db.session.rollback()
                        raise
            
            # Final commit
            db.session.commit()
            print(f"\n[OK] Successfully inserted {total_inserted} marks into Neon database.\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Insertion failed: {e}")
            raise
        
        # ====================================================================
        # VERIFICATION
        # ====================================================================
        
        print("=" * 120)
        print("[VERIFY] FINAL VERIFICATION")
        print("=" * 120)
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
        WHERE e.name IN ('Midterm', 'End_term')
        GROUP BY e.id, e.name
        ORDER BY e.name
        """
        
        try:
            result = db.session.execute(text(verify_query))
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Verification query failed: {e}")
            return
        
        print(f"{'Exam':<15} {'Pupils':<12} {'Subjects':<12} {'Total Marks':<15} "
              f"{'Avg':<12} {'Min':<10} {'Max':<10}")
        print("-" * 120)
        
        for exam_name, pupils_marked, subjects, total_marks, avg_score, min_score, max_score in rows:
            print(f"{exam_name:<15} {pupils_marked:<12} {subjects:<12} {total_marks:<15} "
                  f"{float(avg_score):<12.2f} {min_score:<10.2f} {max_score:<10.2f}")
        
        print()
        
        # Sample inserted marks
        sample_query = """
        SELECT 
            p.first_name || ' ' || p.last_name as pupil_name,
            c.name as class_name,
            s.name as stream_name,
            sub.name as subject_name,
            e.name as exam_name,
            m.score as mark
        FROM marks m
        JOIN pupils p ON m.pupil_id = p.id
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        JOIN subjects sub ON m.subject_id = sub.id
        JOIN exams e ON m.exam_id = e.id
        WHERE e.name IN ('Midterm', 'End_term')
        ORDER BY m.id DESC
        LIMIT 15
        """
        
        try:
            result = db.session.execute(text(sample_query))
            sample_rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Sample query failed: {e}")
            return
        
        print("[INFO] Recent inserted marks sample (last 15):")
        print("-" * 120)
        print(f"{'Pupil':<20} {'Class':<8} {'Stream':<10} {'Subject':<20} {'Exam':<15} {'Mark':<8}")
        print("-" * 120)
        
        for pupil_name, class_name, stream_name, subject_name, exam_name, mark in sample_rows:
            print(f"{pupil_name:<20} {class_name:<8} {stream_name:<10} {subject_name:<20} {exam_name:<15} {mark:<8.2f}")
        
        print()
        
        # Summary statistics
        stats_query = """
        SELECT 
            COUNT(DISTINCT p.id) as total_pupils,
            COUNT(DISTINCT m.id) as total_marks,
            COUNT(DISTINCT e.id) as exam_types,
            COUNT(DISTINCT sub.id) as subjects
        FROM pupils p
        LEFT JOIN marks m ON p.id = m.pupil_id
        LEFT JOIN exams e ON m.exam_id = e.id AND e.name IN ('Midterm', 'End_term')
        LEFT JOIN subjects sub ON m.subject_id = sub.id
        WHERE p.id > 0
        """
        
        try:
            result = db.session.execute(text(stats_query))
            total_row = result.fetchone()
        except Exception as e:
            print(f"[ERROR] Stats query failed: {e}")
            return
        
        total_pupils, total_marks, exam_types, subjects = total_row
        
        print("=" * 120)
        print("[STATS] FINAL STATISTICS")
        print("=" * 120)
        print(f"[OK] Total pupils in system: {total_pupils}")
        print(f"[OK] Total marks inserted: {total_marks}")
        print(f"[OK] Exam types (Midterm & End_term): {exam_types}")
        print(f"[OK] Subjects: {subjects}")
        
        if exam_types and subjects:
            expected = total_pupils * exam_types * subjects
            print(f"[OK] Expected total marks: {expected} (pupils × exams × subjects)")
            print(f"[OK] Completion: {(total_marks / expected * 100):.2f}%")
        
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Insert all missing marks for Midterm and End_term exams'
    )
    parser.add_argument('--apply', action='store_true', help='Apply insertions (default is dry-run)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output during insertion')
    
    args = parser.parse_args()
    
    try:
        insert_all_missing_marks(apply=args.apply, verbose=args.verbose)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
