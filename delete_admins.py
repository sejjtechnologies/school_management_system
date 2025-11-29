# delete_admins.py

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

try:
    # Connect to Neon PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get role_id for Admin
    cur.execute("SELECT id FROM roles WHERE role_name = 'Admin'")
    result = cur.fetchone()
    if not result:
        print("❌ No role 'Admin' found in roles table. Nothing to delete.")
    else:
        admin_role_id = result[0]

        # Delete all users with role Admin
        cur.execute("DELETE FROM users WHERE role_id = %s RETURNING id, email", (admin_role_id,))
        deleted_users = cur.fetchall()

        if deleted_users:
            print(f"✅ Deleted {len(deleted_users)} Admin user(s):")
            for user_id, email in deleted_users:
                print(f"   - ID: {user_id}, Email: {email}")
        else:
            print("⚠️ No Admin users found to delete.")

        conn.commit()

except Exception as e:
    print("❌ Error:", e)

finally:
    if "conn" in locals():
        cur.close()
        conn.close()
