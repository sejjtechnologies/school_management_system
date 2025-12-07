#!/usr/bin/env python
"""
Force delete the exam and all related marks/reports
"""
from app import app, db
from models.marks_model import Exam, Mark, Report
from sqlalchemy import text

with app.app_context():
    # Find the exam
    exam = Exam.query.filter_by(name='Midterm', term=1, year=2025).first()
    
    if exam:
        print(f"Deleting Exam ID={exam.id} and all related data...")
        
        # Delete marks
        deleted_marks = Mark.query.filter_by(exam_id=exam.id).delete()
        print(f"  - Deleted {deleted_marks} marks")
        
        # Delete reports
        deleted_reports = Report.query.filter_by(exam_id=exam.id).delete()
        print(f"  - Deleted {deleted_reports} reports")
        
        # Delete exam
        db.session.delete(exam)
        db.session.commit()
        print(f"  - Deleted exam")
        
        print("\n✅ Cleanup complete!")
        
        # Verify
        remaining_marks = Mark.query.count()
        remaining_reports = Report.query.count()
        print(f"Remaining marks: {remaining_marks}")
        print(f"Remaining reports: {remaining_reports}")
    else:
        print("Exam not found")
