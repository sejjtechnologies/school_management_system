"""
Inspect exams, reports and marks in DB and print samples.
Run with: python scripts/inspect_reports.py [year] [pupil_id]
If year is provided, it will also print reports for that year.
If pupil_id is provided, it will print reports for that pupil.
"""
import sys
from app import app
from models.marks_model import Exam, Report, Mark
from models.register_pupils import Pupil

def print_columns(model):
    try:
        cols = [c.name for c in model.__table__.columns]
        print(cols)
    except Exception as e:
        print('Error introspecting columns for', model, e)

if __name__ == '__main__':
    arg_year = None
    arg_pupil = None
    if len(sys.argv) > 1:
        try:
            arg_year = int(sys.argv[1])
        except Exception:
            arg_year = None
    if len(sys.argv) > 2:
        try:
            arg_pupil = int(sys.argv[2])
        except Exception:
            arg_pupil = None

    with app.app_context():
        # print counts
        try:
            exam_count = Exam.query.count()
            report_count = Report.query.count()
            mark_count = Mark.query.count()
        except Exception as e:
            print('Error querying counts:', e)
            raise

        print('Counts -> Exams:', exam_count, 'Reports:', report_count, 'Marks:', mark_count)
        print('\n-- Exam columns --')
        print_columns(Exam)
        print('\n-- Report columns --')
        print_columns(Report)
        print('\n-- Mark columns --')
        print_columns(Mark)

        print('\n-- Sample Exams (limit 10) --')
        try:
            exs = Exam.query.order_by(Exam.year.desc(), Exam.term.asc()).limit(10).all()
        except Exception as e:
            print('Error fetching exams:', e)
            exs = []
        for e in exs:
            print(f'Exam id={e.id} name={e.name} term={e.term} year={e.year}')

        print('\n-- Sample Reports (limit 10) --')
        try:
            reps = Report.query.order_by(Report.id.desc()).limit(10).all()
        except Exception as e:
            print('Error fetching reports:', e)
            reps = []
        for r in reps:
            ex = getattr(r, 'exam', None)
            print(f'Report id={r.id} pupil_id={r.pupil_id} exam_id={r.exam_id} total={r.total_score} avg={r.average_score} stream_pos={r.stream_position} class_pos={r.class_position} exam_name={getattr(ex, "name", None)} exam_year={getattr(ex, "year", None)}')

        if arg_year is not None:
            print(f'\n-- Reports for year {arg_year} --')
            try:
                rows = Report.query.join(Exam).filter(Exam.year == arg_year).all()
                print('Found', len(rows), 'reports for year', arg_year)
                for rr in rows[:20]:
                    ex = getattr(rr, 'exam', None)
                    print(rr.id, rr.pupil_id, getattr(ex, 'name', None), getattr(ex, 'term', None), getattr(ex, 'year', None), rr.total_score)
            except Exception as e:
                print('Error querying reports for year:', e)

        if arg_pupil is not None:
            print(f'\n-- Reports for pupil {arg_pupil} --')
            try:
                rows = Report.query.filter_by(pupil_id=arg_pupil).all()
                print('Found', len(rows), 'reports for pupil', arg_pupil)
                for rr in rows[:20]:
                    ex = getattr(rr, 'exam', None)
                    print(rr.id, rr.pupil_id, getattr(ex, 'name', None), getattr(ex, 'term', None), getattr(ex, 'year', None), rr.total_score)
            except Exception as e:
                print('Error querying reports for pupil:', e)

        print('\n-- Sample Marks (limit 20) --')
        try:
            mks = Mark.query.order_by(Mark.id.desc()).limit(20).all()
        except Exception as e:
            print('Error fetching marks:', e)
            mks = []
        for m in mks:
            subj = getattr(m, 'subject', None)
            print(f'Mark id={m.id} pupil_id={m.pupil_id} subject={getattr(subj, "name", None)} exam_id={m.exam_id} score={m.score}')

        # optionally show pupil info if one provided
        if arg_pupil is not None:
            p = Pupil.query.get(arg_pupil)
            print('\nPupil row:', p)
