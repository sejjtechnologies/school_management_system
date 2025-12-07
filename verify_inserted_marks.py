#!/usr/bin/env python3
"""
Verify the inserted marks for pupils in ID range 30-98.
Shows summary and sample marks.
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

def verify_marks(id_range=(30, 98)):
    """Verify inserted marks"""
    
    with app.app_context():
        print("\n[*] Verifying inserted marks...\n")
        
        start_id, end_id = id_range
        
        # Query marks summary
        verify_query = """
        SELECT 
            e.name as exam_name,
            COUNT(DISTINCT m.pupil_id) as pupils_with_marks,
            COUNT(DISTINCT m.subject_id) as subjects_marked,
            COUNT(m.id) as total_marks,
            CAST(AVG(m.score) AS NUMERIC(10,2)) as avg_score,
            MIN(m.score) as min_score,
            MAX(m.score) as max_score
        FROM marks m
        JOIN exams e ON m.exam_id = e.id
        JOIN pupils p ON m.pupil_id = p.id
        WHERE p.id >= :start_id AND p.id <= :end_id
        GROUP BY e.id, e.name
        ORDER BY e.name
        """
        
        try:
            result = db.session.execute(
                text(verify_query),
                {"start_id": start_id, "end_id": end_id}
            )
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Verification query failed: {e}")
            return
        
        print("=" * 110)
        print("[SUMMARY] MARKS VERIFICATION REPORT")
        print("=" * 110)
        print()
        
        print(f"{'Exam':<20} {'Pupils':<12} {'Subjects':<12} {'Total Marks':<15} "
              f"{'Avg':<12} {'Min':<10} {'Max':<10}")
        print("-" * 110)
        
        for exam_name, pupils_marked, subjects, total_marks, avg_score, min_score, max_score in rows:
            print(f"{exam_name:<20} {pupils_marked:<12} {subjects:<12} {total_marks:<15} "
                  f"{float(avg_score):<12.2f} {min_score:<10.2f} {max_score:<10.2f}")
        
        print()
        
        # Performance distribution
        distribution_query = """
        SELECT 
            CASE 
                WHEN score >= 80 THEN 'Excellent (80-100)'
                WHEN score >= 65 THEN 'Good (65-79)'
                WHEN score >= 50 THEN 'Average (50-64)'
                WHEN score >= 30 THEN 'Below Avg (30-49)'
                ELSE 'Poor (0-29)'
            END as category,
            COUNT(*) as count,
            CAST(ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM marks m2 
                JOIN pupils p2 ON m2.pupil_id = p2.id 
                WHERE p2.id >= :start_id AND p2.id <= :end_id), 2) AS NUMERIC(5,2)) as percentage
        FROM (
            SELECT m.score
            FROM marks m
            JOIN pupils p ON m.pupil_id = p.id
            WHERE p.id >= :start_id AND p.id <= :end_id
        ) subquery
        GROUP BY 
            CASE 
                WHEN score >= 80 THEN 'Excellent (80-100)'
                WHEN score >= 65 THEN 'Good (65-79)'
                WHEN score >= 50 THEN 'Average (50-64)'
                WHEN score >= 30 THEN 'Below Avg (30-49)'
                ELSE 'Poor (0-29)'
            END
        ORDER BY 
            CASE 
                WHEN score >= 80 THEN 1
                WHEN score >= 65 THEN 2
                WHEN score >= 50 THEN 3
                WHEN score >= 30 THEN 4
                ELSE 5
            END
        """
        
        try:
            result = db.session.execute(
                text(distribution_query),
                {"start_id": start_id, "end_id": end_id}
            )
            dist_rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Distribution query failed: {e}")
            return
        
        print("[INFO] Mark Distribution by Performance:")
        print("-" * 110)
        print(f"{'Category':<20} {'Count':<12} {'Percentage':<12}")
        print("-" * 110)
        
        for category, count, percentage in dist_rows:
            print(f"{category:<20} {count:<12} {percentage}%")
        
        print()
        
        # Sample by class/stream
        sample_query = """
        SELECT 
            c.name as class_name,
            s.name as stream_name,
            COUNT(DISTINCT p.id) as pupils,
            COUNT(m.id) as total_marks,
            CAST(AVG(m.score) AS NUMERIC(10,2)) as avg_score
        FROM marks m
        JOIN pupils p ON m.pupil_id = p.id
        JOIN classes c ON p.class_id = c.id
        JOIN streams s ON p.stream_id = s.id
        WHERE p.id >= :start_id AND p.id <= :end_id
        GROUP BY c.id, c.name, s.id, s.name
        ORDER BY c.name, s.name
        """
        
        try:
            result = db.session.execute(
                text(sample_query),
                {"start_id": start_id, "end_id": end_id}
            )
            sample_rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Sample query failed: {e}")
            return
        
        print("[INFO] Marks by Class/Stream:")
        print("-" * 110)
        print(f"{'Class':<10} {'Stream':<12} {'Pupils':<10} {'Total Marks':<15} {'Avg':<12}")
        print("-" * 110)
        
        for class_name, stream_name, pupils, total_marks, avg_score in sample_rows:
            print(f"{class_name:<10} {stream_name:<12} {pupils:<10} {total_marks:<15} {float(avg_score):<12.2f}")
        
        print()
        
        # Final statistics
        total_query = """
        SELECT 
            COUNT(DISTINCT p.id) as total_pupils,
            COUNT(DISTINCT m.id) as total_marks,
            COUNT(DISTINCT m.exam_id) as exam_types,
            COUNT(DISTINCT m.subject_id) as subjects
        FROM pupils p
        LEFT JOIN marks m ON p.id = m.pupil_id
        WHERE p.id >= :start_id AND p.id <= :end_id
        """
        
        try:
            result = db.session.execute(
                text(total_query),
                {"start_id": start_id, "end_id": end_id}
            )
            total_row = result.fetchone()
        except Exception as e:
            print(f"[ERROR] Total query failed: {e}")
            return
        
        total_pupils, total_marks, exam_types, subjects = total_row
        
        print("=" * 110)
        print("[STATS] FINAL STATISTICS")
        print("=" * 110)
        print(f"[OK] Total pupils in range {start_id}-{end_id}: {total_pupils}")
        print(f"[OK] Total marks inserted: {total_marks}")
        print(f"[OK] Exam types: {exam_types}")
        print(f"[OK] Subjects: {subjects}")
        print(f"[OK] Expected total marks: {total_pupils * exam_types * subjects} (pupils × exams × subjects)")
        print()

if __name__ == '__main__':
    try:
        verify_marks()
    except Exception as e:
        print(f"\n[ERROR] {e}")
