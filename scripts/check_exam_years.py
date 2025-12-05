"""
Utility: Query Exam table and list distinct years.
Run with: python scripts/check_exam_years.py [optional-year-to-check]

This script imports the application so it uses the same DB config. It prints:
 - all distinct integer-cast years found on Exam.year
 - even years (year % 2 == 0)
 - if a year arg is provided, prints whether that year exists.
"""
import sys
from app import app
from models.marks_model import Exam

if __name__ == '__main__':
    with app.app_context():
        years = set()
        try:
            rows = Exam.query.with_entities(Exam.year).filter(Exam.year != None).all()
        except Exception as e:
            print("Error querying Exam table:", e)
            raise

        for row in rows:
            # row may be a tuple like (year,)
            y = row[0] if isinstance(row, (list, tuple)) else row
            try:
                yi = int(y)
            except Exception:
                continue
            years.add(yi)

        if not years:
            print("No exam years found in the database.")
        else:
            all_years = sorted(years, reverse=True)
            even_years = sorted([y for y in years if y % 2 == 0], reverse=True)
            print("Distinct exam years found:", all_years)
            print("Even exam years:", even_years)

        # Optional: check specific year passed as arg
        if len(sys.argv) > 1:
            try:
                check = int(sys.argv[1])
            except Exception:
                print("Provided year is not an integer.")
                sys.exit(2)
            print(f"Year {check} exists in DB:", check in years)
