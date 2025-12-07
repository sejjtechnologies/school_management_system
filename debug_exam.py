#!/usr/bin/env python
"""
Debug: check which exam the test is using
"""
from app import app, db
from models.register_pupils import Pupil
from models.marks_model import Subject, Exam, Mark, Report

with app.app_context():
    # Find test pupil
    pupil = Pupil.query.first()
    print(f"Test pupil: ID={pupil.id}, name={pupil.first_name} {pupil.last_name}")
    
    # Check if exam exists for the test params
    exam = Exam.query.filter_by(name='Midterm', term=1, year=2025).first()
    print(f"\nExam (Midterm, Term 1, 2025): {exam}")
    if exam:
        print(f"  Exam ID: {exam.id}")
        
        # Check for marks and reports
        marks = Mark.query.filter_by(pupil_id=pupil.id, exam_id=exam.id).first()
        reports = Report.query.filter_by(pupil_id=pupil.id, exam_id=exam.id).first()
        
        print(f"  Marks for this pupil: {marks}")
        print(f"  Reports for this pupil: {reports}")
        
        if marks or reports:
            print(f"  ❌ Duplicate data exists - this is why first POST returns 400!")
