import os
import psycopg2
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Data to insert
streams = ["Green", "Red", "Green", "Blue"]
classes = [f"P{i}" for i in range(1, 8)]  # P1 to P7

try:
    # Connect to Neon PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # ✅ Insert streams
    for stream in streams:
        cur.execute("SELECT id FROM streams WHERE name = %s", (stream,))
        exists = cur.fetchone()
        if not exists:
            cur.execute("INSERT INTO streams (name) VALUES (%s)", (stream,))
            print(f"Inserted stream: {stream}")
        else:
            print(f"Stream {stream} already exists, skipping.")

    # ✅ Insert classes
    for cls in classes:
        cur.execute("SELECT id FROM classes WHERE name = %s", (cls,))
        exists = cur.fetchone()
        if not exists:
            cur.execute("INSERT INTO classes (name) VALUES (%s)", (cls,))
            print(f"Inserted class: {cls}")
        else:
            print(f"Class {cls} already exists, skipping.")

    conn.commit()
    print("✅ Streams and classes inserted successfully into Neon.")

except Exception as e:
    print("❌ Error:", e)

finally:
    if "conn" in locals():
        cur.close()
        conn.close()