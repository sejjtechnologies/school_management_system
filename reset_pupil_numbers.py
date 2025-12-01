import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def reset_pupil_numbers():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Fetch all pupils sorted by current id to maintain order
        cursor.execute("SELECT id FROM pupils ORDER BY id")
        pupils = cursor.fetchall()

        for idx, (pupil_db_id,) in enumerate(pupils, start=1):
            # Generate new numbers
            admission_number = f"HPF{idx:03d}"      # HPF001, HPF002...
            receipt_number = f"RCT-{idx:03d}"       # RCT-001, RCT-002...
            pupil_id = f"ID{idx:03d}"               # ID001, ID002...
            roll_number = f"H25/{idx:03d}"          # H25/001, H25/002...
            admission_date = "2025-12-01"

            # Update the pupil record
            cursor.execute("""
                UPDATE pupils
                SET admission_number = %s,
                    receipt_number = %s,
                    pupil_id = %s,
                    roll_number = %s,
                    admission_date = %s
                WHERE id = %s
            """, (admission_number, receipt_number, pupil_id, roll_number, admission_date, pupil_db_id))

        # Commit changes
        conn.commit()
        print(f"Updated {len(pupils)} pupils successfully!")

    except Exception as e:
        print("Error:", e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    reset_pupil_numbers()
