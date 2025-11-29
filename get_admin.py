# get_admin.py

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Email of the Admin user to retrieve
admin_email = "ssejjtechnologies@gmail.com"

try:
    # Connect to Neon PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Query admin user and join with roles to get role name
    cur.execute(
        """
        SELECT u.id, u.first_name, u.last_name, u.email, u.password, r.role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.email = %s
        """,
        (admin_email,)
    )
    admin = cur.fetchone()

    if admin:
        user_id, first_name, last_name, email, password_hash, role_name = admin
        print("✅ Admin user details:")
        print(f"ID           : {user_id}")
        print(f"First Name   : {first_name}")
        print(f"Last Name    : {last_name}")
        print(f"Email        : {email}")
        print(f"Password Hash: {password_hash}")
        print(f"Role         : {role_name}")
    else:
        print(f"❌ No Admin user found with email: {admin_email}")

except Exception as e:
    print("❌ Error:", e)

finally:
    if "conn" in locals():
        cur.close()
        conn.close()
