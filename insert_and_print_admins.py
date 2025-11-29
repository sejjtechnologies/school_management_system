# insert_and_print_admins.py

import os
import psycopg2
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Admin user details (make sure this is consistent!)
first_name = "Wilber"
last_name = "Sejjusa"
email = "sejjtechnologies@gmail.com"
raw_password = "sejjtech"
hashed_password = generate_password_hash(raw_password)

try:
    # Connect to Neon PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Ensure Admin role exists
    cur.execute("SELECT id FROM roles WHERE role_name = 'Admin'")
    result = cur.fetchone()
    if not result:
        # Insert Admin role if missing
        cur.execute("INSERT INTO roles (id, role_name) VALUES (%s, %s) RETURNING id", (1, "Admin"))
        admin_role_id = cur.fetchone()[0]
        print("✅ Admin role inserted.")
    else:
        admin_role_id = result[0]

    # Insert Admin user if not exists
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    if not user:
        cur.execute(
            """
            INSERT INTO users (first_name, last_name, email, password, role_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (first_name, last_name, email, hashed_password, admin_role_id)
        )
        admin_id = cur.fetchone()[0]
        print(f"✅ Admin user inserted: ID={admin_id}, Email={email}")
    else:
        admin_id = user[0]
        print(f"⚠️ Admin user already exists: ID={admin_id}, Email={email}")

    conn.commit()

    # Query all Admin users
    cur.execute(
        """
        SELECT u.id, u.first_name, u.last_name, u.email, r.role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE r.role_name = 'Admin'
        """
    )
    admins = cur.fetchall()

    print("\n📋 All Admin users in the database:")
    for user_id, first_name, last_name, email, role_name in admins:
        print(f"ID={user_id}, Name={first_name} {last_name}, Email={email}, Role={role_name}")

    print(f"\nTotal Admin users: {len(admins)}")

except Exception as e:
    print("❌ Error:", e)

finally:
    if "conn" in locals():
        cur.close()
        conn.close()
