#!/usr/bin/env python3
"""
Check pupil count per class and stream (P1-P7).
Connects to Neon database via DATABASE_URL from .env file.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in .env file")
    exit(1)

print(f"🔗 Connecting to database: {DATABASE_URL[:50]}...")

# Create engine and test connection
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        print("✅ Connected successfully!\n")
        
        # Query: count pupils per class per stream
        query = """
        SELECT 
            c.name AS class,
            s.name AS stream,
            COUNT(p.id) AS pupil_count
        FROM 
            pupils p
        RIGHT JOIN 
            classes c ON p.class_id = c.id
        LEFT JOIN 
            streams s ON p.stream_id = s.id
        GROUP BY 
            c.id, c.name, s.id, s.name
        ORDER BY 
            c.id, s.id
        """
        
        result = connection.execute(text(query))
        rows = result.fetchall()
        
        if not rows:
            print("❌ No data found in pupils/classes/streams tables")
            exit(1)
        
        # Convert to list of dicts for tabulate
        data = [
            {
                "Class": row[0],
                "Stream": row[1] if row[1] else "(No Stream)",
                "Pupil Count": row[2]
            }
            for row in rows
        ]
        
        print("📊 Pupils per Class & Stream:\n")
        print(f"{'Class':<10} {'Stream':<20} {'Pupil Count':<12}")
        print("-" * 42)
        for d in data:
            print(f"{d['Class']:<10} {d['Stream']:<20} {d['Pupil Count']:<12}")
        print("-" * 42)
        
        # Summary statistics
        total_pupils = sum(d["Pupil Count"] for d in data)
        print(f"\n📈 Total pupils: {total_pupils}\n")
        
        # Per-stream totals
        stream_totals = {}
        for d in data:
            stream = d["Stream"]
            if stream not in stream_totals:
                stream_totals[stream] = 0
            stream_totals[stream] += d["Pupil Count"]
        
        print("📍 Stream Summary:")
        for stream, count in sorted(stream_totals.items()):
            print(f"   {stream}: {count} pupils")

except Exception as e:
    print(f"❌ ERROR: {e}")
    exit(1)
finally:
    engine.dispose()
