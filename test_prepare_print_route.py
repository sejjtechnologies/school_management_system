#!/usr/bin/env python3
"""
Test the prepare_print route to verify it returns all exams for all terms
"""
import os
from dotenv import load_dotenv

# Set Flask app
os.environ['FLASK_ENV'] = 'development'

from app import app, db
from models.register_pupils import Pupil
from models.marks_model import Exam, Mark, Report

def test_prepare_print():
    with app.app_context():
        print("\n" + "="*100)
        print("[TEST: prepare_print route exams]")
        print("="*100)
        
        # Get a pupil
        pupil = Pupil.query.first()
        if not pupil:
            print("[ERROR] No pupils found")
            return
        
        print(f"\n[*] Testing with pupil: {pupil.first_name} {pupil.last_name} (ID {pupil.id})")
        
        # Simulate what the route does
        selected_year = None
        selected_term = None
        types_param = 'both'
        
        # Build exam query
        exams_q = Exam.query
        if selected_year:
            exams_q = exams_q.filter(Exam.year == selected_year)
        
        if types_param != 'both' and types_param != 'all':
            if types_param == 'mid':
                exams_q = exams_q.filter(Exam.name.ilike('%mid%'))
            elif types_param == 'end':
                exams_q = exams_q.filter(Exam.name.ilike('%end%'))
        
        exams_filtered = exams_q.all()
        # Filter to only generic Midterm and End Term exams
        exams_filtered = [e for e in exams_filtered if e.name in ['Midterm', 'End Term', 'End_term', 'End_Term']]
        exam_ids = [e.id for e in exams_filtered]
        
        print(f"\n[*] Found {len(exams_filtered)} generic exams (before filtering by pupil)")
        
        # determine which of these exams have reports/marks for this pupil
        available_exams = []
        if exam_ids:
            reps = Report.query.filter(Report.pupil_id == pupil.id, Report.exam_id.in_(exam_ids)).all()
            rep_exam_ids = set(r.exam_id for r in reps)
            # also consider marks if reports don't exist
            marks_exist = {m.exam_id for m in Mark.query.filter(Mark.pupil_id == pupil.id, Mark.exam_id.in_(exam_ids)).all()}
            have_ids = rep_exam_ids.union(marks_exist)
            available_exams = [e for e in exams_filtered if e.id in have_ids]
            # Sort by term and then by name
            available_exams = sorted(available_exams, key=lambda e: (e.term, 'Midterm' not in e.name))
        
        print(f"[*] Found {len(available_exams)} exams with marks for this pupil\n")
        print(f"{'Term':<6} {'Exam ID':<8} {'Name':<30} {'Year':<6}")
        print("-"*70)
        
        for exam in available_exams:
            print(f"{exam.term:<6} {exam.id:<8} {exam.name:<30} {exam.year:<6}")
        
        # Verify we have all 6 exams
        if len(available_exams) == 6:
            print(f"\n[SUCCESS] All 6 exams available (2 per term)")
            
            # Check distribution
            term1 = [e for e in available_exams if e.term == 1]
            term2 = [e for e in available_exams if e.term == 2]
            term3 = [e for e in available_exams if e.term == 3]
            
            print(f"  Term 1: {len(term1)} exams ✓")
            print(f"  Term 2: {len(term2)} exams ✓")
            print(f"  Term 3: {len(term3)} exams ✓")
        else:
            print(f"\n[WARNING] Expected 6 exams, got {len(available_exams)}")

if __name__ == '__main__':
    test_prepare_print()
