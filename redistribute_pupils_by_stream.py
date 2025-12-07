#!/usr/bin/env python3
"""
Redistribute pupils so each stream in each class has exactly 100 students.
- P1-P7: 3 streams each (Red, Green, Blue)
- Each stream: 100 pupils
- Total per class: 300 pupils
- Ordering: admission_number, pupil_id, roll_number
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Mark, Report
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"sslmode": "require"},
}

db.init_app(app)

def redistribute_pupils_by_stream():
    """Redistribute pupils: 100 per stream, 300 per class (P1-P7)."""
    
    with app.app_context():
        print("🔗 Connecting to database...\n")
        
        # Get all classes P1-P7 and streams
        classes = Class.query.filter(Class.name.in_(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'])).order_by(Class.name).all()
        streams = Stream.query.all()
        stream_map = {s.name: s.id for s in streams}  # Map stream name to ID
        
        if not classes:
            print("❌ No classes found")
            return
        
        if not streams:
            print("❌ No streams found")
            return
        
        print(f"📚 Found {len(classes)} classes (P1-P7)")
        print(f"🌊 Found {len(streams)} streams: {', '.join([s.name for s in streams])}\n")
        
        # Get all pupils, ordered by admission_number, then pupil_id, then roll_number
        all_pupils = Pupil.query.order_by(
            Pupil.admission_number.asc(),
            Pupil.pupil_id.asc(),
            Pupil.roll_number.asc()
        ).all()
        
        print(f"👥 Total pupils in database: {len(all_pupils)}\n")
        
        # Expected: 300 pupils per class × 7 classes = 2100 total
        expected_total = 300 * len(classes)
        
        if len(all_pupils) < expected_total:
            print(f"⚠️  WARNING: Only {len(all_pupils)} pupils available, need {expected_total}")
            print(f"   Will redistribute available pupils evenly.\n")
        
        # Redistribute pupils
        print("=" * 80)
        print("🔄 REDISTRIBUTING PUPILS")
        print("=" * 80)
        print()
        
        pupil_idx = 0
        updates_count = 0
        
        for class_obj in classes:
            class_name = class_obj.name
            class_id = class_obj.id
            
            print(f"\n📚 CLASS: {class_name}")
            print(f"{'─' * 80}")
            print(f"{'Stream':<15} {'Expected':<12} {'Assigned':<12} {'Actual Count':<15}")
            print(f"{'-' * 15} {'-' * 12} {'-' * 12} {'-' * 15}")
            
            class_total = 0
            
            for stream_name in sorted(stream_map.keys()):  # Red, Blue, Green alphabetically
                stream_id = stream_map[stream_name]
                pupils_to_assign = 100  # Each stream gets 100 pupils
                assigned_count = 0
                
                # Assign pupils to this stream
                while assigned_count < pupils_to_assign and pupil_idx < len(all_pupils):
                    pupil = all_pupils[pupil_idx]
                    
                    # Update pupil's class and stream
                    if pupil.class_id != class_id or pupil.stream_id != stream_id:
                        pupil.class_id = class_id
                        pupil.stream_id = stream_id
                        updates_count += 1
                    
                    pupil_idx += 1
                    assigned_count += 1
                
                class_total += assigned_count
                
                print(f"{stream_name:<15} {pupils_to_assign:<12} {assigned_count:<12} {assigned_count:<15}")
            
            print(f"{'-' * 15} {'-' * 12} {'-' * 12} {'-' * 15}")
            print(f"{'TOTAL':<15} {300:<12} {class_total:<12} {class_total:<15}")
        
        # Commit changes
        print("\n" + "=" * 80)
        print("💾 COMMITTING CHANGES TO DATABASE...")
        print("=" * 80)
        
        try:
            db.session.commit()
            print(f"✅ Successfully updated {updates_count} pupil records\n")
        except Exception as e:
            print(f"❌ Error committing changes: {e}\n")
            db.session.rollback()
            return
        
        # Verify and print final counts
        print("\n" + "=" * 80)
        print("📊 FINAL VERIFICATION")
        print("=" * 80)
        print()
        
        query = text("""
        SELECT 
            c.name AS class,
            s.name AS stream,
            COUNT(p.id) AS pupil_count
        FROM 
            classes c
        LEFT JOIN 
            pupils p ON p.class_id = c.id
        LEFT JOIN 
            streams s ON p.stream_id = s.id
        WHERE 
            c.name IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')
        GROUP BY 
            c.id, c.name, s.id, s.name
        ORDER BY 
            c.id, s.id
        """)
        
        result = db.session.execute(query)
        verification_rows = result.fetchall()
        
        grand_total = 0
        
        for class_name in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:
            class_rows = [r for r in verification_rows if r[0] == class_name]
            
            if not class_rows:
                continue
            
            print(f"📚 CLASS: {class_name}")
            print(f"{'Stream':<15} {'Pupil Count':<15} {'Status':<20}")
            print(f"{'-' * 15} {'-' * 15} {'-' * 20}")
            
            class_total = 0
            
            for _, stream_name, count in class_rows:
                if stream_name:
                    status = "✅ 100" if count == 100 else f"⚠️  {count}"
                    print(f"{stream_name:<15} {count:<15} {status:<20}")
                    class_total += count
                    grand_total += count
            
            print(f"{'-' * 15} {'-' * 15} {'-' * 20}")
            print(f"{'TOTAL':<15} {class_total:<15}")
            print()
        
        print("=" * 80)
        print(f"🎯 GRAND TOTAL: {grand_total} pupils across all classes and streams")
        print("=" * 80)

if __name__ == "__main__":
    redistribute_pupils_by_stream()
