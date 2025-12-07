#!/usr/bin/env python3
"""
Direct SQL insertion of End_term marks - fast and efficient.
Uses raw SQL for bulk insert.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from sqlalchemy import text

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def insert_endterm_sql():
    """Insert End_term marks using raw SQL"""
    
    with app.app_context():
        print("\n[*] Inserting End_term marks using SQL...\n")
        
        # First, find the End_term exam ID
        query = """
        SELECT id FROM exams 
        WHERE name = 'End_Term' OR name = 'End_term'
        LIMIT 1
        """
        
        result = db.session.execute(text(query))
        exam_row = result.fetchone()
        
        if not exam_row:
            print("[ERROR] No End_term exam found")
            return
        
        exam_id = exam_row[0]
        print(f"[OK] Using exam ID: {exam_id}\n")
        
        # Insert missing End_term marks with random scores
        insert_query = """
        INSERT INTO marks (pupil_id, subject_id, exam_id, score)
        SELECT 
            p.id as pupil_id,
            s.id as subject_id,
            :exam_id as exam_id,
            (RANDOM() * 100)::NUMERIC(10,2) as score
        FROM pupils p
        CROSS JOIN subjects s
        WHERE NOT EXISTS (
            SELECT 1 FROM marks m
            WHERE m.pupil_id = p.id 
            AND m.subject_id = s.id 
            AND m.exam_id = :exam_id
        )
        """
        
        try:
            result = db.session.execute(
                text(insert_query),
                {"exam_id": exam_id}
            )
            db.session.commit()
            
            rows_inserted = result.rowcount
            print(f"[OK] Inserted {rows_inserted} End_term marks!\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] {e}")
            return
        
        # Verify
        verify_query = """
        SELECT 
            e.name as exam_name,
            COUNT(*) as total_marks,
            COUNT(DISTINCT pupil_id) as pupils,
            COUNT(DISTINCT subject_id) as subjects,
            ROUND(AVG(score), 2) as avg_score
        FROM marks m
        JOIN exams e ON m.exam_id = e.id
        WHERE e.id = :exam_id
        GROUP BY e.name
        """
        
        result = db.session.execute(
            text(verify_query),
            {"exam_id": exam_id}
        )
        row = result.fetchone()
        
        if row:
            exam_name, total_marks, pupils, subjects, avg_score = row
            print("[VERIFY] Results:")
            print("-" * 80)
            print(f"  Exam: {exam_name}")
            print(f"  Total marks: {total_marks}")
            print(f"  Pupils: {pupils}")
            print(f"  Subjects: {subjects}")
            print(f"  Average score: {avg_score}\n")

if __name__ == '__main__':
    try:
        insert_endterm_sql()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
