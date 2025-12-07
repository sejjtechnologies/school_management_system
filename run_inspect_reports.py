#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ensure project root is on sys.path
proj_root = os.path.dirname(__file__)
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from app import app
from models.marks_model import Exam, Report, Mark

def main():
    with app.app_context():
        try:
            exam_count = Exam.query.count()
            report_count = Report.query.count()
            mark_count = Mark.query.count()
        except Exception as e:
            print('Error querying counts:', e)
            return

        print('Counts -> Exams:', exam_count, 'Reports:', report_count, 'Marks:', mark_count)

if __name__ == '__main__':
    main()
