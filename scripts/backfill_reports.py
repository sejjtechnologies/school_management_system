#!/usr/bin/env python3
"""
Backfill Report rows from Marks.
Usage: python scripts/backfill_reports.py [year]
If year is provided, only exams for that year are processed. Commits in batches.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from app import app, db
from models.marks_model import Exam, Mark, Report, Subject
from models.register_pupils import Pupil
from utils.grades import calculate_grade, calculate_general_remark

BATCH = 200

def backfill(year=None):
    with app.app_context():
        exams_q = Exam.query
        if year:
            exams_q = exams_q.filter(Exam.year == year)
        exams = exams_q.all()
        if not exams:
            print('No exams found for year', year)
            return
        subjects = Subject.query.all()
        subject_count = len(subjects) if subjects else 1
        total_created = 0
        total_updated = 0
        print(f'Found {len(exams)} exams to process')
        for ex in exams:
            print(f'Processing exam id={ex.id} name={ex.name} term={ex.term} year={ex.year}')
            # find all pupils who have marks for this exam
            pupil_ids = set(m.pupil_id for m in Mark.query.filter_by(exam_id=ex.id).all())
            print(f'  Pupils with marks: {len(pupil_ids)}')
            processed = 0
            for pid in pupil_ids:
                marks = Mark.query.filter_by(pupil_id=pid, exam_id=ex.id).all()
                if not marks:
                    continue
                total = sum(m.score for m in marks)
                avg = total / len(marks) if marks else 0
                grade = calculate_grade(avg)
                rep = Report.query.filter_by(pupil_id=pid, exam_id=ex.id).first()
                if not rep:
                    rep = Report(pupil_id=pid, exam_id=ex.id, total_score=total, average_score=avg, grade=grade, remarks='Backfilled')
                    db.session.add(rep)
                    total_created += 1
                else:
                    rep.total_score = total
                    rep.average_score = avg
                    rep.grade = grade
                    rep.remarks = (rep.remarks or '') + ' | Backfilled'
                    total_updated += 1
                processed += 1
                if processed % BATCH == 0:
                    db.session.commit()
                    print(f'    Committed {processed} pupils for exam {ex.id}...')
            db.session.commit()
            print(f'  Done exam {ex.id}: created {total_created} updated {total_updated} so far')
        print(f'Backfill complete. Total created: {total_created}, total updated: {total_updated}')

if __name__ == '__main__':
    arg_year = None
    if len(sys.argv) > 1:
        try:
            arg_year = int(sys.argv[1])
        except Exception:
            arg_year = None
    backfill(arg_year)
