#!/usr/bin/env python3
"""
Debug script to verify exam data and query parameters
"""
import sys
sys.path.insert(0, '/home/user/school_management_system-main')

from app import app
from models.marks_model import Exam, Pupil, Mark, Report
from models.marks_model import Subject

with app.app_context():
    # Check what exams we have
    all_exams = Exam.query.all()
    print(f"\nTotal exams in database: {len(all_exams)}")
    for exam in all_exams:
        print(f"  ID: {exam.id}, Name: {exam.name}, Term: {exam.term}, Year: {exam.year}")
    
    # Simulate what happens when term buttons are clicked
    print("\n--- Term 1 (both exams) ---")
    term1_exams = Exam.query.filter(Exam.term == 1).all()
    term1_ids = [e.id for e in term1_exams]
    print(f"Term 1 exam IDs: {term1_ids}")
    for exam in term1_exams:
        print(f"  {exam.name} (ID {exam.id})")
    
    # Test the database query used in print_selected
    print("\n--- Simulating print_selected query ---")
    exam_ids = term1_ids
    exams_for_print = Exam.query.filter(Exam.id.in_(exam_ids)).all()
    exams_for_print = sorted(exams_for_print, key=lambda e: (e.term, 'Midterm' not in e.name))
    print(f"Exams returned from query: {len(exams_for_print)}")
    for exam in exams_for_print:
        print(f"  {exam.name} (Term {exam.term}, ID {exam.id})")
    
    # Check a random pupil
    pupil = Pupil.query.first()
    if pupil:
        print(f"\n--- Sample pupil: {pupil.first_name} {pupil.last_name} ---")
        print(f"Pupil ID: {pupil.id}, Class: {pupil.class_id}, Stream: {pupil.stream_id}")
        
        # Check marks for this pupil for term 1 exams
        for exam in term1_exams:
            marks = Mark.query.filter(Mark.pupil_id == pupil.id, Mark.exam_id == exam.id).all()
            print(f"  {exam.name}: {len(marks)} marks")
            for mark in marks[:2]:
                print(f"    - {mark.subject_id}: {mark.score}")
