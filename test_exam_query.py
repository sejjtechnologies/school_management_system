from app import app
from models.marks_model import Exam

with app.app_context():
    # Directly query what the backend would query
    result = Exam.query.filter_by(year=2025, term=1).all()
    print(f'Exam.query.filter_by(year=2025, term=1) found: {len(result)} exams')
    if result:
        for ex in result:
            print(f'  - id={ex.id}, name={ex.name}, year={ex.year}, term={ex.term}')
    else:
        print('  (No exams found!)')

    # Now try a broader query
    all_exams = Exam.query.filter_by(term=1).all()
    print(f'\nAll exams with term=1: {len(all_exams)}')
    year_counts = {}
    for ex in all_exams:
        year_counts[ex.year] = year_counts.get(ex.year, 0) + 1
    print(f'By year: {year_counts}')

    # Also check raw database to ensure data exists
    print('\n=== ALL EXAMS IN DATABASE ===')
    all_exams_db = Exam.query.all()
    print(f'Total exams: {len(all_exams_db)}')
    for ex in all_exams_db[:10]:
        print(f'  id={ex.id}, name={ex.name}, year={ex.year}, term={ex.term}')
