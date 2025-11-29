# delete_users_by_email.py

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Email to delete
EMAIL_TO_DELETE = "sejjtechnologies@gmail.com"

try:
    # Connect to Neon PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    print("? Connected to the Neon database.")

    # Check if any users exist with this email
    cur.execute("SELECT id, first_name, last_name, email FROM users WHERE email = %s", (EMAIL_TO_DELETE,))
    users = cur.fetchall()

    if not users:
        print(f"?? No users found with email: {EMAIL_TO_DELETE}")
    else:
        print(f"Found {len(users)} user(s) with email {EMAIL_TO_DELETE}:")
        for user_id, first_name, last_name, email in users:
            print(f"  - ID={user_id}, Name={first_name} {last_name}, Email={email}")

        # Delete all users with that email
        cur.execute("DELETE FROM users WHERE email = %s", (EMAIL_TO_DELETE,))
        conn.commit()
        print(f"? Deleted {cur.rowcount} user(s) with email: {EMAIL_TO_DELETE}")

except Exception as e:
    print("? Error:", e)

finally:
    if "conn" in locals():
        cur.close()
        conn.close()
        print("? Connection closed.")
