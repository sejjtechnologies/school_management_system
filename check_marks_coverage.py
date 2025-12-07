#!/usr/bin/env python3
"""
Quick verification of marks coverage for all pupils in all classes.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.class_model import Class
from models.stream_model import Stream
from models.register_pupils import Pupil
from models.marks_model import Mark, Exam, Subject
from sqlalchemy import text

# Load environment
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def check_marks_coverage():
    """Check marks coverage for all pupils"""
    
    with app.app_context():
        print("\n[*] Checking marks coverage...\n")
        
        # Query to get marks summary by exam
        query_str = """
        SELECT 
            e.name as exam_name,
            COUNT(DISTINCT m.pupil_id) as pupils_with_marks,
            COUNT(DISTINCT m.subject_id) as subjects_marked,
            COUNT(m.id) as total_marks,
            CAST(AVG(m.score) AS NUMERIC(10,2)) as avg_score,
            CAST(MIN(m.score) AS NUMERIC(10,2)) as min_score,
            CAST(MAX(m.score) AS NUMERIC(10,2)) as max_score
        FROM marks m
        JOIN exams e ON m.exam_id = e.id
        WHERE e.name IN ('Midterm', 'End_term', 'End_Term')
        GROUP BY e.id, e.name
        ORDER BY e.name
        """
        
        try:
            result = db.session.execute(text(query_str))
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return
        
        print("=" * 110)
        print("[MARKS COVERAGE] By Exam Type")
        print("=" * 110)
        print()
        print(f"{'Exam':<15} {'Pupils':<12} {'Subjects':<12} {'Total Marks':<15} "
              f"{'Avg':<12} {'Min':<12} {'Max':<12}")
        print("-" * 110)
        
        for exam_name, pupils_with_marks, subjects, total_marks, avg_score, min_score, max_score in rows:
            print(f"{exam_name:<15} {pupils_with_marks:<12} {subjects:<12} {total_marks:<15} "
                  f"{avg_score:<12} {min_score:<12} {max_score:<12}")
        
        print()
        
        # Total pupils in system
        total_pupils_query = "SELECT COUNT(*) FROM pupils"
        total_pupils = db.session.execute(text(total_pupils_query)).scalar()
        
        print(f"[INFO] Total pupils in system: {total_pupils}\n")
        
        # Check by class/stream
        class_stream_query = """
        SELECT 
            c.name as class_name,
            s.name as stream_name,
            COUNT(DISTINCT p.id) as total_pupils,
            COUNT(DISTINCT CASE WHEN e.name = 'Midterm' THEN m.pupil_id END) as midterm_pupils,
            COUNT(DISTINCT CASE WHEN e.name IN ('End_term', 'End_Term') THEN m.pupil_id END) as endterm_pupils
        FROM pupils p
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        LEFT JOIN marks m ON p.id = m.pupil_id
        LEFT JOIN exams e ON m.exam_id = e.id
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        GROUP BY c.id, c.name, s.id, s.name
        ORDER BY c.name, s.name
        """
        
        try:
            result = db.session.execute(text(class_stream_query))
            cs_rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Class/stream query failed: {e}")
            return
        
        print("=" * 110)
        print("[MARKS COVERAGE] By Class/Stream")
        print("=" * 110)
        print()
        print(f"{'Class':<8} {'Stream':<12} {'Total':<8} {'Midterm':<12} {'End_term':<12} {'Status':<20}")
        print("-" * 110)
        
        all_complete = True
        for class_name, stream_name, total_pupils, midterm_pupils, endterm_pupils in cs_rows:
            midterm_pupils = midterm_pupils or 0
            endterm_pupils = endterm_pupils or 0
            
            status = "[OK] Complete" if (midterm_pupils == total_pupils and endterm_pupils == total_pupils) else "[MISSING]"
            if "[MISSING]" in status:
                all_complete = False
            
            print(f"{class_name:<8} {stream_name:<12} {total_pupils:<8} {midterm_pupils:<12} {endterm_pupils:<12} {status:<20}")
        
        print()
        
        # Overall summary
        if all_complete:
            print("[OK] All pupils have marks for both Midterm and End_term exams!\n")
        else:
            print("[WARNING] Some pupils are still missing marks.\n")
            
            # Find missing
            missing_query = """
            SELECT 
                COUNT(DISTINCT p.id) as missing_pupils
            FROM pupils p
            LEFT JOIN marks m ON p.id = m.pupil_id
            LEFT JOIN exams e ON m.exam_id = e.id AND e.name IN ('Midterm', 'End_term')
            WHERE m.id IS NULL
            GROUP BY p.id
            HAVING COUNT(m.id) = 0
            """
            
            try:
                result = db.session.execute(text(missing_query))
                missing_count = result.scalar() or 0
                print(f"[INFO] Pupils completely missing marks: {missing_count}\n")
            except:
                pass


if __name__ == '__main__':
    try:
        check_marks_coverage()
    except Exception as e:
        print(f"\n[ERROR] {e}")
