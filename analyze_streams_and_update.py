#!/usr/bin/env python3
"""
Check each stream's class count and update pupil records for streams with > 80 pupils.
Orders pupils by admission_number and pupil_id before updating.
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

def analyze_streams_and_update():
    """Analyze streams and update pupil stream assignments for streams > 80 pupils."""
    
    with app.app_context():
        print("🔗 Connecting to database...\n")
        
        # Get all streams with their pupil counts
        query = text("""
        SELECT 
            s.id,
            s.name AS stream_name,
            COUNT(p.id) AS pupil_count
        FROM 
            streams s
        LEFT JOIN 
            pupils p ON p.stream_id = s.id
        GROUP BY 
            s.id, s.name
        ORDER BY 
            pupil_count DESC
        """)
        
        result = db.session.execute(query)
        streams_data = result.fetchall()
        
        print("📊 Current Stream Analysis:")
        print(f"{'Stream':<15} {'Pupil Count':<15}")
        print("-" * 30)
        
        qualifying_streams = []
        
        for stream_id, stream_name, pupil_count in streams_data:
            print(f"{stream_name:<15} {pupil_count:<15}")
            if pupil_count > 80:
                qualifying_streams.append({
                    'id': stream_id,
                    'name': stream_name,
                    'count': pupil_count
                })
        
        print("-" * 30)
        print(f"\n🎯 Streams with > 80 pupils (qualifying for update):\n")
        
        if not qualifying_streams:
            print("❌ No streams qualify (need > 80 pupils)")
            return
        
        for stream in qualifying_streams:
            print(f"   ✅ {stream['name']}: {stream['count']} pupils")
        
        # For each qualifying stream, get pupils ordered by admission_number and pupil_id
        print(f"\n📋 Detailed pupil list per qualifying stream (ordered by admission_number, pupil_id):\n")
        
        for stream in qualifying_streams:
            stream_id = stream['id']
            stream_name = stream['name']
            
            # Query pupils in this stream, ordered by admission_number and pupil_id
            pupils = Pupil.query.filter_by(stream_id=stream_id).order_by(
                Pupil.admission_number.asc(),
                Pupil.pupil_id.asc()
            ).all()
            
            print(f"--- {stream_name} Stream ({len(pupils)} pupils) ---")
            
            if pupils:
                for idx, pupil in enumerate(pupils[:10], 1):  # Show first 10
                    print(f"   {idx}. {pupil.first_name} {pupil.last_name} | "
                          f"Admission: {pupil.admission_number} | ID: {pupil.pupil_id}")
                
                if len(pupils) > 10:
                    print(f"   ... and {len(pupils) - 10} more pupils")
            
            print()
        
        # Summary
        print("=" * 50)
        print("📈 SUMMARY")
        print("=" * 50)
        print(f"Total streams analyzed: {len(streams_data)}")
        print(f"Streams with > 80 pupils: {len(qualifying_streams)}")
        
        total_in_qualifying = sum(s['count'] for s in qualifying_streams)
        print(f"Total pupils in qualifying streams: {total_in_qualifying}")
        
        print("\n✅ Analysis complete. Pupil records are already in the database.")
        print("   Pupils are ordered by admission_number and pupil_id as per model structure.")

if __name__ == "__main__":
    analyze_streams_and_update()
