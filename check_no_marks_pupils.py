#!/usr/bin/env python3
"""
Check for pupils with no marks in both Midterm and End_term across all class/stream combinations.
Shows which pupils have missing marks for each exam type.

Usage:
    python check_no_marks_pupils.py                    # show all pupils without marks
    python check_no_marks_pupils.py --summary          # show summary per class/stream
    python check_no_marks_pupils.py --detailed         # show detailed names and IDs
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from datetime import date
from flask import Flask
from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Mark, Exam, Report
from sqlalchemy import text

# Load environment
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def check_no_marks_pupils(detailed=False, summary=False):
    """Check for pupils with no marks in Midterm and End_term"""
    
    with app.app_context():
        print("\n[*] Querying pupils with no marks in both Midterm and End_term...\n")
        
        # Get all exams (Midterm and End_term)
        try:
            midterm_exams = Exam.query.filter(Exam.name.ilike('%Midterm%')).all()
            endterm_exams = Exam.query.filter(Exam.name.ilike('%End_term%') | Exam.name.ilike('%End Term%')).all()
        except Exception as e:
            print(f"[ERROR] Failed to query exams: {e}")
            return
        
        if not midterm_exams or not endterm_exams:
            print(f"[ERROR] No Midterm exams found: {bool(midterm_exams)}")
            print(f"[ERROR] No End_term exams found: {bool(endterm_exams)}")
            return
        
        print(f"[OK] Found Midterm exams: {[e.name for e in midterm_exams]}")
        print(f"[OK] Found End_term exams: {[e.name for e in endterm_exams]}\n")
        
        # Query structure to find pupils with NO marks in BOTH Midterm AND End_term
        query_str = """
        SELECT 
            c.name as class_name,
            s.name as stream_name,
            p.id as pupil_id,
            p.admission_number,
            p.first_name,
            p.middle_name,
            p.last_name,
            CASE 
                WHEN COUNT(CASE WHEN e.name ILIKE '%Midterm%' THEN 1 END) = 0 THEN 'NO'
                ELSE 'YES'
            END as has_midterm_marks,
            CASE 
                WHEN COUNT(CASE WHEN e.name ILIKE '%End_term%' OR e.name ILIKE '%End Term%' THEN 1 END) = 0 THEN 'NO'
                ELSE 'YES'
            END as has_endterm_marks
        FROM pupils p
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        LEFT JOIN marks m ON p.id = m.pupil_id
        LEFT JOIN exams e ON m.exam_id = e.id
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        GROUP BY p.id, c.name, s.name, p.admission_number, p.first_name, p.middle_name, p.last_name
        HAVING 
            COUNT(CASE WHEN e.name ILIKE '%Midterm%' THEN 1 END) = 0 
            AND COUNT(CASE WHEN e.name ILIKE '%End_term%' OR e.name ILIKE '%End Term%' THEN 1 END) = 0
        ORDER BY c.name, s.name, p.first_name, p.last_name
        """
        
        try:
            result = db.session.execute(text(query_str))
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Query execution failed: {e}")
            return
        
        if not rows:
            print("[OK] All pupils have marks in either Midterm or End_term.\n")
            return
        
        # Display results
        print("=" * 110)
        print("[RESULTS] PUPILS WITH NO MARKS IN BOTH MIDTERM AND END_TERM")
        print("=" * 110)
        print()
        
        # Group by class/stream
        by_class_stream = {}
        
        for class_name, stream_name, pupil_id, admission_number, first_name, middle_name, last_name, has_midterm, has_endterm in rows:
            key = f"{class_name} - {stream_name}"
            if key not in by_class_stream:
                by_class_stream[key] = []
            
            full_name = f"{first_name} {middle_name or ''} {last_name}".strip()
            by_class_stream[key].append({
                'admission_number': admission_number,
                'pupil_id': pupil_id,
                'full_name': full_name,
                'has_midterm': has_midterm,
                'has_endterm': has_endterm
            })
        
        if summary:
            # Summary view
            print(f"{'Class':<8} {'Stream':<12} {'No Marks':<12}")
            print("-" * 110)
            
            for class_stream in sorted(by_class_stream.keys()):
                count = len(by_class_stream[class_stream])
                class_name, stream_name = class_stream.split(" - ")
                print(f"{class_name:<8} {stream_name:<12} {count:<12}")
            
            total_no_marks = sum(len(pupils) for pupils in by_class_stream.values())
            print("-" * 110)
            print(f"\n[SUMMARY] Total pupils with no marks in both Midterm and End_term: {total_no_marks}\n")
        
        elif detailed:
            # Detailed view with names
            for class_stream in sorted(by_class_stream.keys()):
                pupils = by_class_stream[class_stream]
                print(f"\n{class_stream}: {len(pupils)} pupils without marks")
                print("-" * 110)
                print(f"{'#':<4} {'Admission':<12} {'ID':<8} {'Full Name':<35} {'Midterm':<10} {'End_term':<10}")
                print("-" * 110)
                
                for idx, pupil in enumerate(pupils, 1):
                    print(f"{idx:<4} {pupil['admission_number']:<12} {pupil['pupil_id']:<8} "
                          f"{pupil['full_name']:<35} {pupil['has_midterm']:<10} {pupil['has_endterm']:<10}")
                
                print()
        
        else:
            # Default view: show per class/stream with expanded info
            for class_stream in sorted(by_class_stream.keys()):
                pupils = by_class_stream[class_stream]
                print(f"\n{class_stream}: {len(pupils)} pupils")
                print("-" * 110)
                print(f"{'#':<4} {'Admission':<12} {'ID':<8} {'Full Name':<35}")
                print("-" * 110)
                
                for idx, pupil in enumerate(pupils, 1):
                    print(f"{idx:<4} {pupil['admission_number']:<12} {pupil['pupil_id']:<8} "
                          f"{pupil['full_name']:<35}")
                
                print()
        
        # Overall statistics
        total_no_marks = sum(len(pupils) for pupils in by_class_stream.values())
        total_pupils = Pupil.query.count()
        
        print("=" * 110)
        print(f"[STATS] Total pupils with NO marks in both Midterm & End_term: {total_no_marks}")
        print(f"[STATS] Total pupils in system: {total_pupils}")
        print(f"[STATS] Percentage: {(total_no_marks / total_pupils * 100):.2f}%\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check pupils with no marks in both Midterm and End_term'
    )
    parser.add_argument('--summary', action='store_true', help='Show summary view only')
    parser.add_argument('--detailed', action='store_true', help='Show detailed view with names')
    
    args = parser.parse_args()
    
    try:
        check_no_marks_pupils(detailed=args.detailed, summary=args.summary)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
