#!/usr/bin/env python
from app import app
from models.register_pupils import Pupil
from models.marks_model import Exam, Mark, Report
from models.teacher_assignment_models import TeacherAssignment

with app.app_context():
    print("=== PUPIL 279 INFO ===")
    p279 = Pupil.query.get(279)
    print(f"Pupil 279: {p279.first_name} {p279.last_name}, class={p279.class_id}, stream={p279.stream_id}")

    print("\n=== EXAM ID 36 (Midterm, term=1, year=2025) ===")
    exam36 = Exam.query.get(36)
    print(f"Exam: name={exam36.name}, year={exam36.year}, term={exam36.term}")

    print("\n=== MARKS FOR PUPIL 279 & EXAM 36 ===")
    marks279_36 = Mark.query.filter_by(pupil_id=279, exam_id=36).all()
    print(f"Marks count: {len(marks279_36)}")
    if marks279_36:
        print(f"Sample marks: {[(m.subject_id, m.score) for m in marks279_36[:3]]}")

    print("\n=== REPORTS FOR PUPIL 279 & EXAM 36 ===")
    reports279_36 = Report.query.filter_by(pupil_id=279, exam_id=36).all()
    print(f"Reports count: {len(reports279_36)}")
    if reports279_36:
        print(f"Sample report: id={reports279_36[0].id}, total_score={reports279_36[0].total_score}")

    print("\n=== TEACHER ASSIGNMENTS ===")
    all_assignments = TeacherAssignment.query.all()
    print(f"Total teacher assignments: {len(all_assignments)}")
    for asgn in all_assignments[:5]:
        print(f"  Teacher {asgn.teacher_id}: class={asgn.class_id}, stream={asgn.stream_id}")

    print("\n=== PUPILS IN CLASS 1, STREAM 1 (typical teacher assignment) ===")
    pupils_1_1 = Pupil.query.filter_by(class_id=1, stream_id=1).all()
    print(f"Count: {len(pupils_1_1)}")
    print(f"First 5: {[(p.id, p.first_name) for p in pupils_1_1[:5]]}")

    print("\n=== PUPILS IN CLASS 1, STREAM 2 (where Nathan 279 is) ===")
    pupils_1_2 = Pupil.query.filter_by(class_id=1, stream_id=2).all()
    print(f"Count: {len(pupils_1_2)}")
    print(f"First 5: {[(p.id, p.first_name) for p in pupils_1_2[:5]]}")
    print(f"Is 279 in this list? {any(p.id == 279 for p in pupils_1_2)}")
