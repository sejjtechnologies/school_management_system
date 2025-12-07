#!/usr/bin/env python
"""
Check if exam exists and what marks/reports are tied to it
"""
from app import app, db
from models.marks_model import Exam, Mark, Report
from models.register_pupils import Pupil

with app.app_context():
    # Check if the exam exists
    exam = Exam.query.filter_by(name='Midterm', term=1, year=2025).first()

    if exam:
        print(f"✅ Exam exists: ID={exam.id}, {exam.name} Term {exam.term} Year {exam.year}")

        # Find pupil 623 (first pupil)
        pupil = Pupil.query.first()
        print(f"\nPupil: ID={pupil.id}, {pupil.first_name} {pupil.last_name}")

        # Check for marks
        marks = Mark.query.filter_by(pupil_id=pupil.id, exam_id=exam.id).all()
        print(f"Marks for this pupil+exam: {len(marks)}")
        for m in marks:
            print(f"  - Subject {m.subject_id}: {m.score}")

        # Check for reports
        reports = Report.query.filter_by(pupil_id=pupil.id, exam_id=exam.id).all()
        print(f"Reports for this pupil+exam: {len(reports)}")
        for r in reports:
            print(f"  - Report {r.id}: grade={r.grade}")
    else:
        print("❌ Exam does NOT exist - test should succeed!")

        # Count total marks and reports
        total_marks = Mark.query.count()
        total_reports = Report.query.count()
        print(f"\nTotal marks in DB: {total_marks}")
        print(f"Total reports in DB: {total_reports}")
