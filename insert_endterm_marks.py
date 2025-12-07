#!/usr/bin/env python3
"""
Insert missing End_term marks for all pupils.
Simple and efficient - only inserts End_term marks that are missing.
"""

import os
import sys
import random
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.class_model import Class
from models.stream_model import Stream
from models.register_pupils import Pupil
from models.marks_model import Mark, Exam, Subject
from sqlalchemy import text

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

MARK_RANGES = {
    "excellent": {"range": (80, 100), "weight": 15},
    "good": {"range": (65, 79), "weight": 25},
    "average": {"range": (50, 64), "weight": 35},
    "below_average": {"range": (30, 49), "weight": 20},
    "poor": {"range": (0, 29), "weight": 5}
}

def get_random_mark():
    rand = random.randint(1, 100)
    cumulative = 0
    for category, data in MARK_RANGES.items():
        cumulative += data["weight"]
        if rand <= cumulative:
            min_mark, max_mark = data["range"]
            return round(random.uniform(min_mark, max_mark), 2)
    return round(random.uniform(50, 64), 2)

def insert_endterm_marks():
    """Insert End_term marks for all pupils"""
    
    with app.app_context():
        print("\n[*] Connecting to Neon database...\n")
        
        # Get the End_term exam
        endterm_exam = Exam.query.filter(
            (Exam.name == 'End_term') | (Exam.name == 'End_Term')
        ).first()
        
        if not endterm_exam:
            print("[ERROR] No End_term exam found in database")
            return
        
        print(f"[OK] Found End_term exam: {endterm_exam.name}\n")
        
        # Get all subjects
        subjects = Subject.query.all()
        if not subjects:
            print("[ERROR] No subjects found")
            return
        
        print(f"[OK] Found {len(subjects)} subjects\n")
        
        # Get all pupils
        pupils = Pupil.query.all()
        print(f"[OK] Found {len(pupils)} pupils\n")
        
        # Find missing End_term marks
        missing_count = 0
        for pupil in pupils:
            for subject in subjects:
                existing = Mark.query.filter_by(
                    pupil_id=pupil.id,
                    subject_id=subject.id,
                    exam_id=endterm_exam.id
                ).first()
                
                if not existing:
                    missing_count += 1
        
        print(f"[OK] Found {missing_count} missing End_term marks\n")
        
        if missing_count == 0:
            print("[OK] All pupils already have End_term marks.\n")
            return
        
        # Show plan
        print("=" * 90)
        print("[PLAN] INSERT END_TERM MARKS")
        print("=" * 90)
        print(f"[SUMMARY] Pupils: {len(pupils)}")
        print(f"[SUMMARY] Subjects: {len(subjects)}")
        print(f"[SUMMARY] Missing marks: {missing_count}\n")
        print("[RUN] Run with --apply to perform insertions.\n")
        
        return  # Dry run complete
        
def apply_insertion():
    """Apply insertion"""
    
    with app.app_context():
        print("\n[*] Connecting to Neon database...\n")
        
        # Get the End_term exam
        endterm_exam = Exam.query.filter(
            (Exam.name == 'End_term') | (Exam.name == 'End_Term')
        ).first()
        
        if not endterm_exam:
            print("[ERROR] No End_term exam found")
            return
        
        print(f"[OK] Using exam: {endterm_exam.name}\n")
        
        subjects = Subject.query.all()
        pupils = Pupil.query.all()
        
        print(f"[OK] Processing {len(pupils)} pupils with {len(subjects)} subjects\n")
        print("=" * 90)
        print("[INSERT] APPLYING END_TERM MARKS")
        print("=" * 90)
        print()
        
        total_inserted = 0
        batch_size = 500
        
        try:
            for idx, pupil in enumerate(pupils, 1):
                for subject in subjects:
                    existing = Mark.query.filter_by(
                        pupil_id=pupil.id,
                        subject_id=subject.id,
                        exam_id=endterm_exam.id
                    ).first()
                    
                    if not existing:
                        mark = Mark(
                            pupil_id=pupil.id,
                            subject_id=subject.id,
                            exam_id=endterm_exam.id,
                            score=get_random_mark()
                        )
                        db.session.add(mark)
                        total_inserted += 1
                
                # Flush every batch_size pupils
                if idx % 50 == 0:
                    db.session.flush()
                    print(f"[+] Processed {idx}/{len(pupils)} pupils ({total_inserted} marks)...")
            
            db.session.commit()
            print(f"\n[OK] Successfully inserted {total_inserted} End_term marks!\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] {e}")
            raise

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    
    try:
        if args.apply:
            apply_insertion()
        else:
            insert_endterm_marks()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
