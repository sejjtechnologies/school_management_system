#!/usr/bin/env python3
"""
Analyze pupils per class and stream (P1-P7).
Show each class with all its streams, totals per stream and per class.
Highlight streams with < 100 pupils.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
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

def analyze_classes_and_streams():
    """Analyze pupils per class per stream, showing streams < 100 pupils."""

    with app.app_context():
        print("🔗 Connecting to database...\n")

        # Query: pupils per class per stream (P1-P7)
        query = text("""
        SELECT 
            c.id,
            c.name AS class,
            s.id,
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
        rows = result.fetchall()

        if not rows:
            print("❌ No data found")
            return

        # Organize data by class
        classes_data = {}

        for class_id, class_name, stream_id, stream_name, pupil_count in rows:
            if class_name not in classes_data:
                classes_data[class_name] = {
                    'class_id': class_id,
                    'streams': {}
                }

            if stream_name is not None:  # Only add if stream exists
                classes_data[class_name]['streams'][stream_name] = pupil_count

        # Print results
        print("=" * 80)
        print("📊 CLASS & STREAM ANALYSIS (P1-P7)")
        print("=" * 80)
        print()

        grand_total = 0
        streams_under_100 = []

        for class_name in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:
            if class_name not in classes_data:
                continue

            class_info = classes_data[class_name]
            streams = class_info['streams']

            print(f"\n{'─' * 80}")
            print(f"📚 CLASS: {class_name}")
            print(f"{'─' * 80}")

            class_total = 0

            # Print header
            print(f"{'Stream':<20} {'Pupil Count':<15} {'Status':<20}")
            print(f"{'-' * 20} {'-' * 15} {'-' * 20}")

            for stream_name in sorted(streams.keys()):
                count = streams[stream_name]
                class_total += count
                grand_total += count

                # Check if < 100
                if count < 100:
                    status = "⚠️  UNDER 100"
                    streams_under_100.append({
                        'class': class_name,
                        'stream': stream_name,
                        'count': count
                    })
                else:
                    status = "✅ 100+"

                print(f"{stream_name:<20} {count:<15} {status:<20}")

            print(f"{'-' * 20} {'-' * 15} {'-' * 20}")
            print(f"{'TOTAL for ' + class_name:<20} {class_total:<15}")
            print()

        # Summary section
        print("\n" + "=" * 80)
        print("📈 SUMMARY STATISTICS")
        print("=" * 80)

        print(f"\n🎯 Grand Total (All Classes & Streams): {grand_total} pupils\n")

        if streams_under_100:
            print(f"⚠️  Streams with < 100 pupils ({len(streams_under_100)} found):\n")
            print(f"{'Class':<10} {'Stream':<20} {'Pupil Count':<15}")
            print(f"{'-' * 10} {'-' * 20} {'-' * 15}")

            for item in streams_under_100:
                print(f"{item['class']:<10} {item['stream']:<20} {item['count']:<15}")

            print()
        else:
            print("✅ All streams have >= 100 pupils\n")

        # Stream totals across all classes
        print("\n📍 Stream Totals (Across All Classes):\n")

        query_stream_totals = text("""
        SELECT 
            s.name AS stream,
            COUNT(p.id) AS total_pupils
        FROM 
            streams s
        LEFT JOIN 
            pupils p ON p.stream_id = s.id
        GROUP BY 
            s.id, s.name
        ORDER BY 
            total_pupils DESC
        """)

        result = db.session.execute(query_stream_totals)
        stream_totals = result.fetchall()

        print(f"{'Stream':<20} {'Total Pupils':<15}")
        print(f"{'-' * 20} {'-' * 15}")

        for stream_name, total_pupils in stream_totals:
            print(f"{stream_name:<20} {total_pupils:<15}")

        print(f"{'-' * 20} {'-' * 15}")
        print(f"{'GRAND TOTAL':<20} {grand_total:<15}")
        print()

if __name__ == "__main__":
    analyze_classes_and_streams()
