#!/usr/bin/env python3
"""
Simple script to insert missing End_term marks for all pupils.
Shows class, stream, and insertion progress with percentage.
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

def get_random_mark():
    """Generate random mark"""
    return round(random.uniform(0, 100), 2)

def insert_missing_endterm_marks():
    """Insert missing End_term marks with progress tracking"""

    with app.app_context():
        print("\n[*] Connecting to Neon database...\n")

        # Get End_term exam
        endterm_exam = Exam.query.filter(
            (Exam.name == 'End_term') | (Exam.name == 'End_Term')
        ).first()

        if not endterm_exam:
            print("[ERROR] No End_term exam found")
            return

        print(f"[OK] Using exam: {endterm_exam.name}\n")

        # Get all classes and streams
        classes = db.session.query(Class).order_by(Class.name).all()
        streams = db.session.query(Stream).order_by(Stream.name).all()
        subjects = db.session.query(Subject).all()

        print(f"[OK] Found {len(classes)} classes, {len(streams)} streams, {len(subjects)} subjects\n")

        # Calculate total
        total_combinations = len(classes) * len(streams)
        processed = 0
        total_marks = 0

        print("=" * 100)
        print("[INSERT] INSERTING END_TERM MARKS BY CLASS/STREAM")
        print("=" * 100)
        print()
        print(f"{'Class':<8} {'Stream':<12} {'Pupils':<10} {'Marks':<10} {'Status':<15} {'Progress':<12}")
        print("-" * 100)

        try:
            for class_obj in classes:
                for stream_obj in streams:
                    # Get pupils for this class/stream
                    pupils = Pupil.query.filter_by(
                        class_id=class_obj.id,
                        stream_id=stream_obj.id
                    ).all()

                    if not pupils:
                        continue

                    marks_inserted = 0

                    # Insert marks for each pupil/subject combination
                    for pupil in pupils:
                        for subject in subjects:
                            # Check if mark already exists
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
                                marks_inserted += 1
                                total_marks += 1

                    # Flush after each class/stream
                    if marks_inserted > 0:
                        db.session.flush()

                    processed += 1
                    percentage = (processed / total_combinations) * 100
                    status = "[OK] Done" if marks_inserted == 0 else f"[+] {marks_inserted}"

                    print(f"{class_obj.name:<8} {stream_obj.name:<12} {len(pupils):<10} {marks_inserted:<10} {status:<15} {percentage:>6.1f}%")

            # Final commit
            db.session.commit()
            print()
            print("=" * 100)
            print(f"[OK] Successfully inserted {total_marks} End_term marks!\n")

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return

        # Verify
        print("[VERIFY] Final Status by Class/Stream:")
        print("-" * 100)
        print(f"{'Class':<8} {'Stream':<12} {'Total':<10} {'With Marks':<15} {'Completion':<15}")
        print("-" * 100)

        for class_obj in classes:
            for stream_obj in streams:
                total = Pupil.query.filter_by(
                    class_id=class_obj.id,
                    stream_id=stream_obj.id
                ).count()

                if total == 0:
                    continue

                with_marks = db.session.execute(text("""
                    SELECT COUNT(DISTINCT p.id)
                    FROM pupils p
                    JOIN marks m ON p.id = m.pupil_id
                    WHERE p.class_id = :class_id 
                    AND p.stream_id = :stream_id
                    AND m.exam_id = :exam_id
                """), {
                    'class_id': class_obj.id,
                    'stream_id': stream_obj.id,
                    'exam_id': endterm_exam.id
                }).scalar()

                completion = (with_marks / total * 100) if total > 0 else 0
                print(f"{class_obj.name:<8} {stream_obj.name:<12} {total:<10} {with_marks:<15} {completion:>6.1f}%")

        print()

if __name__ == '__main__':
    try:
        insert_missing_endterm_marks()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
