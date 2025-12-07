#!/usr/bin/env python3
"""
Check for pupils missing marks in both Midterm and End_term exams.
Count by class and stream combinations for all exam types.

Usage:
    python check_missing_marks_by_class_stream.py                    # show all missing
    python check_missing_marks_by_class_stream.py --summary          # summary view only
    python check_missing_marks_by_class_stream.py --detailed         # detailed names
"""

import os
import sys
import argparse
from dotenv import load_dotenv
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


def check_missing_marks_by_class_stream(detailed=False, summary=False):
    """Check for pupils missing marks in both Midterm and End_term across all class/streams"""
    
    with app.app_context():
        print("\n[*] Checking for pupils missing marks in both Midterm and End_term...\n")
        
        # Query to find pupils missing marks in BOTH Midterm AND End_term
        query_str = """
        SELECT 
            c.name as class_name,
            s.name as stream_name,
            p.id as pupil_id,
            p.admission_number,
            p.first_name,
            p.middle_name,
            p.last_name,
            COUNT(DISTINCT CASE WHEN e.name = 'Midterm' AND m.id IS NOT NULL THEN 1 END) as has_midterm,
            COUNT(DISTINCT CASE WHEN e.name = 'End_term' AND m.id IS NOT NULL THEN 1 END) as has_endterm,
            COUNT(DISTINCT CASE WHEN e.name = 'End Term' AND m.id IS NOT NULL THEN 1 END) as has_end_term_alt
        FROM pupils p
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        CROSS JOIN exams e
        LEFT JOIN marks m ON p.id = m.pupil_id AND m.exam_id = e.id
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        GROUP BY p.id, c.name, s.name, p.admission_number, p.first_name, p.middle_name, p.last_name
        HAVING 
            COUNT(DISTINCT CASE WHEN e.name = 'Midterm' AND m.id IS NOT NULL THEN 1 END) = 0
            OR COUNT(DISTINCT CASE WHEN e.name = 'End_term' AND m.id IS NOT NULL THEN 1 END) = 0
            OR COUNT(DISTINCT CASE WHEN e.name = 'End Term' AND m.id IS NOT NULL THEN 1 END) = 0
        ORDER BY c.name, s.name, p.first_name, p.last_name
        """
        
        try:
            result = db.session.execute(text(query_str))
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Query execution failed: {e}")
            return
        
        if not rows:
            print("[OK] All pupils have marks for both Midterm and End_term.\n")
            return
        
        print(f"[OK] Found {len(rows)} pupils with missing marks\n")
        
        # Group by class/stream
        by_class_stream = {}
        missing_by_exam = {}
        
        for row in rows:
            class_name, stream_name, pupil_id, admission_number, first_name, middle_name, last_name, has_midterm, has_endterm, has_end_term_alt = row
            
            key = f"{class_name} - {stream_name}"
            if key not in by_class_stream:
                by_class_stream[key] = []
            
            full_name = f"{first_name} {middle_name or ''} {last_name}".strip()
            
            # Determine which exams are missing
            missing_exams = []
            if has_midterm == 0:
                missing_exams.append("Midterm")
            if has_endterm == 0:
                missing_exams.append("End_term")
            if has_end_term_alt == 0:
                missing_exams.append("End Term")
            
            exam_str = ", ".join(missing_exams) if missing_exams else "Both"
            
            by_class_stream[key].append({
                'admission_number': admission_number,
                'pupil_id': pupil_id,
                'full_name': full_name,
                'missing_exams': exam_str
            })
            
            # Track missing by exam type
            for exam in missing_exams:
                if exam not in missing_by_exam:
                    missing_by_exam[exam] = 0
                missing_by_exam[exam] += 1
        
        # Display results
        print("=" * 130)
        print("[RESULTS] PUPILS MISSING MARKS IN BOTH MIDTERM AND END_TERM BY CLASS/STREAM")
        print("=" * 130)
        print()
        
        if summary:
            # Summary view
            print(f"{'Class':<8} {'Stream':<12} {'Missing Marks':<15}")
            print("-" * 130)
            
            for class_stream in sorted(by_class_stream.keys()):
                count = len(by_class_stream[class_stream])
                class_name, stream_name = class_stream.split(" - ")
                print(f"{class_name:<8} {stream_name:<12} {count:<15}")
            
            total_missing = sum(len(pupils) for pupils in by_class_stream.values())
            print("-" * 130)
            print(f"\n[SUMMARY] Total pupils missing marks: {total_missing}\n")
            
            print("[STATS] Missing Marks by Exam Type:")
            print("-" * 130)
            for exam_type, count in sorted(missing_by_exam.items()):
                print(f"  - {exam_type}: {count} pupils")
            print()
        
        elif detailed:
            # Detailed view with names
            for class_stream in sorted(by_class_stream.keys()):
                pupils = by_class_stream[class_stream]
                print(f"\n{class_stream}: {len(pupils)} pupils missing marks")
                print("-" * 130)
                print(f"{'#':<4} {'Admission':<12} {'ID':<8} {'Full Name':<35} {'Missing Exams':<30}")
                print("-" * 130)
                
                for idx, pupil in enumerate(pupils, 1):
                    print(f"{idx:<4} {pupil['admission_number']:<12} {pupil['pupil_id']:<8} "
                          f"{pupil['full_name']:<35} {pupil['missing_exams']:<30}")
                
                print()
        
        else:
            # Default view: expanded with exam breakdown
            for class_stream in sorted(by_class_stream.keys()):
                pupils = by_class_stream[class_stream]
                print(f"\n{class_stream}: {len(pupils)} pupils")
                print("-" * 130)
                print(f"{'#':<4} {'Admission':<12} {'ID':<8} {'Full Name':<35} {'Missing':<30}")
                print("-" * 130)
                
                for idx, pupil in enumerate(pupils, 1):
                    print(f"{idx:<4} {pupil['admission_number']:<12} {pupil['pupil_id']:<8} "
                          f"{pupil['full_name']:<35} {pupil['missing_exams']:<30}")
                
                print()
        
        # Overall statistics
        total_missing = sum(len(pupils) for pupils in by_class_stream.values())
        total_pupils = Pupil.query.count()
        
        print("=" * 130)
        print("[STATS] OVERALL STATISTICS")
        print("=" * 130)
        print(f"[OK] Total pupils missing marks in both exams: {total_missing}")
        print(f"[OK] Total pupils in system: {total_pupils}")
        print(f"[OK] Percentage: {(total_missing / total_pupils * 100):.2f}%")
        print()
        
        # Break down by exam type
        print("[STATS] Missing Marks by Exam Type:")
        print("-" * 130)
        for exam_type in sorted(missing_by_exam.keys()):
            count = missing_by_exam[exam_type]
            print(f"  - {exam_type}: {count} pupils ({(count / total_pupils * 100):.2f}%)")
        
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check pupils missing marks in both Midterm and End_term'
    )
    parser.add_argument('--summary', action='store_true', help='Show summary view only')
    parser.add_argument('--detailed', action='store_true', help='Show detailed view with names')
    
    args = parser.parse_args()
    
    try:
        check_missing_marks_by_class_stream(detailed=args.detailed, summary=args.summary)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
