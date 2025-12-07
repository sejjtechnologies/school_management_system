#!/usr/bin/env python3
"""
Test print_selected route with both Midterm and End Term for Term 1
"""
import os
from dotenv import load_dotenv

os.environ['FLASK_ENV'] = 'development'

from app import app, db
from models.register_pupils import Pupil
from models.marks_model import Exam, Mark, Report, Subject

def test_print_route():
    with app.app_context():
        print("\n" + "="*100)
        print("[TEST: print_selected with both Midterm and End Term]")
        print("="*100)

        # Get a pupil
        pupil = Pupil.query.first()
        if not pupil:
            print("[ERROR] No pupils found")
            return

        print(f"\n[*] Testing with pupil: {pupil.first_name} {pupil.last_name} (ID {pupil.id})")

        # Get Term 1 Midterm and End Term exams
        exam_ids = [25, 26]  # Term 1 Midterm and End Term

        print(f"[*] Using exam IDs: {exam_ids}")

        # Fetch exams
        exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()
        exams = sorted(exams, key=lambda e: (e.term, 'Midterm' not in e.name))

        print(f"\n[EXAMS] Found {len(exams)} exams:")
        for ex in exams:
            print(f"  - ID {ex.id}: {ex.name} (Term {ex.term})")

        # Fetch marks for this pupil
        marks = Mark.query.filter(Mark.pupil_id == pupil.id, Mark.exam_id.in_(exam_ids)).all()

        # Build marks map
        marks_by_exam = {}
        for m in marks:
            marks_by_exam.setdefault(m.exam_id, []).append(m)

        print(f"\n[MARKS] Found {len(marks)} total marks for this pupil:")
        for exam_id, mark_list in marks_by_exam.items():
            exam = next((e for e in exams if e.id == exam_id), None)
            exam_name = exam.name if exam else "Unknown"
            print(f"  - Exam {exam_id} ({exam_name}): {len(mark_list)} marks")

        # Fetch reports
        reports = Report.query.filter(Report.pupil_id == pupil.id, Report.exam_id.in_(exam_ids)).all()

        print(f"\n[REPORTS] Found {len(reports)} reports for this pupil:")
        for rep in reports:
            exam = next((e for e in exams if e.id == rep.exam_id), None)
            exam_name = exam.name if exam else "Unknown"
            print(f"  - Exam {rep.exam_id} ({exam_name}): Total {rep.total_score}, Avg {rep.average_score}, Grade {rep.grade}")

        # Test weight calculation
        subjects = Subject.query.all()
        weights_template = {}
        for ex in exams:
            name = (ex.name or '').lower()
            if 'mid' in name:
                weights_template[ex.id] = 0.4
            elif 'end' in name:
                weights_template[ex.id] = 0.6
            else:
                weights_template[ex.id] = None

        print(f"\n[WEIGHTS]")
        for exam_id, weight in weights_template.items():
            exam = next((e for e in exams if e.id == exam_id), None)
            exam_name = exam.name if exam else "Unknown"
            print(f"  - Exam {exam_id} ({exam_name}): {weight}")

        # Test combined calculation
        combined = None
        if len(exams) > 1:
            subject_count = len(subjects) if subjects else 1
            weighted_total = 0.0
            for ex in exams:
                rep = next((r for r in reports if r.exam_id == ex.id), None)
                if rep:
                    weighted_total += (rep.total_score or 0) * weights_template.get(ex.id, 0)
                    print(f"[COMBINED] Adding {ex.name}: {rep.total_score} * {weights_template.get(ex.id, 0)} = {(rep.total_score or 0) * weights_template.get(ex.id, 0)}")
                else:
                    # fallback: sum marks
                    mlist = marks_by_exam.get(ex.id, [])
                    total = sum(m.score for m in mlist) if mlist else 0
                    weighted_total += total * weights_template.get(ex.id, 0)
                    print(f"[COMBINED] Adding {ex.name} (no report): {total} * {weights_template.get(ex.id, 0)} = {total * weights_template.get(ex.id, 0)}")

            combined_avg = round((weighted_total / (subject_count or 1)), 2)
            print(f"\n[COMBINED RESULT] Weighted Total: {weighted_total}, Average: {combined_avg}")

        print(f"\n[SUCCESS] Test complete - both exams should display!\n")

if __name__ == '__main__':
    test_print_route()
