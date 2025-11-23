import os
import psycopg2
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Admin user details
first_name = "Wilber"
last_name = "Sejjusa"
email = "sejjtechnologies@gmail.com"
raw_password = "sejjtech"
hashed_password = generate_password_hash(raw_password)

# Roles to insert
roles = [
    (1, "Admin"),
    (2, "Teacher"),
    (3, "Secretary"),
    (4, "Headteacher"),
    (5, "Parent"),
    (6, "Bursar"),
]

try:
    # Connect to PostgreSQL using DATABASE_URL from .env
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # ✅ Insert roles if they don't exist
    for role_id, role_name in roles:
        cur.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO roles (id, role_name) VALUES (%s, %s)",
                (role_id, role_name),
            )
            print(f"Inserted role: {role_name}")
        else:
            print(f"Role {role_name} already exists, skipping.")

    # ✅ Get role_id for Admin
    cur.execute("SELECT id FROM roles WHERE role_name = 'Admin'")
    role_id = cur.fetchone()
    if role_id is None:
        raise Exception("Role 'Admin' not found in roles table.")
    role_id = role_id[0]

    # ✅ Insert Admin user if not exists
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user_exists = cur.fetchone()
    if not user_exists:
        cur.execute(
            """
            INSERT INTO users (first_name, last_name, email, password, role_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (first_name, last_name, email, hashed_password, role_id),
        )
        print("✅ Admin user inserted successfully into Neon.")
    else:
        print("Admin user already exists, skipping.")

    conn.commit()

except Exception as e:
    print("❌ Error:", e)

finally:
    if "conn" in locals():
        cur.close()
        conn.close()