import os
import psycopg2

def main():
    url = os.getenv('DATABASE_URL')
    print('Using DATABASE_URL:', url)
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='reports';")
    cols = cur.fetchall()
    for c in cols:
        print(c)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
