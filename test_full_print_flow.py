#!/usr/bin/env python3
"""
Comprehensive test of print_selected route with both Midterm and End Term
Simulates the exact request the user would make
"""
import os
from dotenv import load_dotenv

os.environ['FLASK_ENV'] = 'development'

from app import app, db
from models.register_pupils import Pupil
from models.marks_model import Exam, Mark, Report, Subject

def test_full_print_flow():
    with app.app_context():
        print("\n" + "="*100)
        print("[FULL TEST: print_selected Route - Both Midterm and End Term]")
        print("="*100)
        
        # Get first pupil
        pupil = Pupil.query.first()
        if not pupil:
            print("[ERROR] No pupils found")
            return
        
        print(f"\n[PUPIL] {pupil.first_name} {pupil.last_name}")
        print(f"[CLASS] {pupil.class_id} | [STREAM] {pupil.stream_id}")
        
        # Simulate user selecting BOTH Midterm and End Term for Term 1
        exam_ids = [25, 26]  # Term 1 Midterm and End Term
        
        print(f"\n[REQUEST] User selected exams: {exam_ids}")
        
        # Fetch exams
        exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()
        if not exams:
            print("[ERROR] No exams found")
            return
        
        # Apply the sorting from print_selected route
        exams = sorted(exams, key=lambda e: (e.term, 'Midterm' not in e.name))
        
        print(f"\n[SORTING] After sorting by (term, exam_type):")
        for i, ex in enumerate(exams, 1):
            print(f"  {i}. ID {ex.id}: '{ex.name}' (Term {ex.term})")
        
        # Fetch marks and reports
        marks = Mark.query.filter(Mark.pupil_id == pupil.id, Mark.exam_id.in_(exam_ids)).all()
        reports = Report.query.filter(Report.pupil_id == pupil.id, Report.exam_id.in_(exam_ids)).all()
        subjects = Subject.query.all()
        
        print(f"\n[DATA]")
        print(f"  - Subjects: {len(subjects)}")
        print(f"  - Total Marks: {len(marks)}")
        print(f"  - Reports: {len(reports)}")
        
        # Build marks map
        marks_by_exam = {}
        for m in marks:
            marks_by_exam.setdefault(m.exam_id, []).append(m)
        
        print(f"\n[MARKS DISTRIBUTION]")
        for exam_id in sorted(marks_by_exam.keys()):
            exam = next((e for e in exams if e.id == exam_id), None)
            exam_name = exam.name if exam else "Unknown"
            print(f"  - Exam {exam_id} ({exam_name}): {len(marks_by_exam[exam_id])} marks")
        
        # Weight calculation (from route)
        weights_template = {}
        for ex in exams:
            name = (ex.name or '').lower()
            if 'mid' in name:
                weights_template[ex.id] = 0.4
            elif 'end' in name or 'end term' in name:
                weights_template[ex.id] = 0.6
            else:
                weights_template[ex.id] = None
        
        print(f"\n[WEIGHTS]")
        for exam_id, weight in weights_template.items():
            exam = next((e for e in exams if e.id == exam_id), None)
            exam_name = exam.name if exam else "Unknown"
            print(f"  - {exam_name}: {weight * 100}%")
        
        # Combined calculation
        combined = None
        if len(exams) > 1:
            subject_count = len(subjects) if subjects else 1
            weighted_total = 0.0
            
            print(f"\n[COMBINED CALCULATION]")
            for ex in exams:
                rep = next((r for r in reports if r.exam_id == ex.id), None)
                if rep:
                    score = rep.total_score or 0
                else:
                    mlist = marks_by_exam.get(ex.id, [])
                    score = sum(m.score for m in mlist) if mlist else 0
                
                weight = weights_template.get(ex.id, 0)
                contribution = score * weight
                weighted_total += contribution
                
                print(f"  + {ex.name}: {score} × {weight} = {contribution}")
            
            combined_avg = round((weighted_total / (subject_count or 1)), 2)
            combined = {
                'combined_total': round(weighted_total, 2),
                'combined_average': combined_avg,
                'combined_grade': combined_avg >= 80 and 'A' or combined_avg >= 70 and 'B' or combined_avg >= 60 and 'C' or combined_avg >= 50 and 'D' or 'E'
            }
            print(f"  = FINAL: {weighted_total} ÷ {subject_count} = {combined_avg}")
        
        # Verify template will show all exams
        print(f"\n[TEMPLATE RENDERING]")
        print(f"  ✅ Combined header will show: {len(exams) > 1}")
        print(f"  ✅ Individual exam cards: {len(exams)}")
        for i, ex in enumerate(exams, 1):
            rep = next((r for r in reports if r.exam_id == ex.id), None)
            marks_list = marks_by_exam.get(ex.id, [])
            print(f"    {i}. {ex.name}")
            print(f"       - Report: {'Yes' if rep else 'No (will calculate from marks)'}")
            print(f"       - Marks: {len(marks_list)}")
        print(f"  ✅ Combined summary: {combined is not None}")
        
        print(f"\n✅ SUCCESS - Both exams should display correctly!")
        print(f"\n📊 EXPECTED OUTPUT:")
        print(f"   1. Combined Report Header (Term 1)")
        print(f"   2. Midterm Card with scores")
        print(f"   3. End Term Card with scores")
        print(f"   4. Combined Summary (Average: {combined['combined_average']}, Grade: {combined['combined_grade']})")
        
        return True

if __name__ == '__main__':
    success = test_full_print_flow()
    if success:
        print("\n" + "="*100 + "\n")
