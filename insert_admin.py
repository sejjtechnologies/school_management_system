import psycopg2
from werkzeug.security import generate_password_hash

# Database connection details
DB_NAME = "school_management"
DB_USER = "postgres"
DB_PASSWORD = "sejjtechnologies"
DB_HOST = "localhost"
DB_PORT = "5432"

# Admin user details
first_name = "Wilber"
last_name = "Sejjusa"
email = "sejjtechnologies@gmail.com"
raw_password = "sejjtech"
hashed_password = generate_password_hash(raw_password)

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    # Get role_id for Admin
    cur.execute("SELECT id FROM roles WHERE role_name = 'Admin'")
    role_id = cur.fetchone()
    if role_id is None:
        raise Exception("Role 'Admin' not found in roles table.")
    role_id = role_id[0]

    # Insert user
    cur.execute("""
        INSERT INTO users (first_name, last_name, email, password, role_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (first_name, last_name, email, hashed_password, role_id))

    conn.commit()
    print("✅ Admin user inserted successfully.")

except Exception as e:
    print("❌ Error:", e)

finally:
    if conn:
        cur.close()
        conn.close()