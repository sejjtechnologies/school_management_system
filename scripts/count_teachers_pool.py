import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print('DATABASE_URL not set')
    raise SystemExit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM users u JOIN roles r ON u.role_id = r.id WHERE r.role_name ILIKE 'teacher'")
print('total teachers in users table:', cur.fetchone()[0])
cur.close()
conn.close()
