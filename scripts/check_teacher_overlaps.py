import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print('DATABASE_URL not set in environment')
    raise SystemExit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Count overlapping pairs where same teacher is in two different class/stream at overlapping times
count_query = '''
SELECT COUNT(*)
FROM timetable_slots t1
JOIN timetable_slots t2 ON t1.teacher_id = t2.teacher_id
  AND t1.day_of_week = t2.day_of_week
  AND t1.id < t2.id
  AND t1.start_time < t2.end_time
  AND t1.end_time > t2.start_time
WHERE (t1.class_id != t2.class_id OR t1.stream_id != t2.stream_id)
'''
cur.execute(count_query)
count = cur.fetchone()[0]
print('Overlapping teacher assignments (different class/stream):', count)

if count > 0:
    print('\nSample overlapping pairs:')
    sample_query = '''
    SELECT t1.id as slot1, t2.id as slot2, t1.teacher_id, t1.day_of_week,
           t1.class_id as class1, t1.stream_id as stream1, t1.start_time as start1, t1.end_time as end1,
           t2.class_id as class2, t2.stream_id as stream2, t2.start_time as start2, t2.end_time as end2
    FROM timetable_slots t1
    JOIN timetable_slots t2 ON t1.teacher_id = t2.teacher_id
      AND t1.day_of_week = t2.day_of_week
      AND t1.id < t2.id
      AND t1.start_time < t2.end_time
      AND t1.end_time > t2.start_time
    WHERE (t1.class_id != t2.class_id OR t1.stream_id != t2.stream_id)
    ORDER BY t1.teacher_id
    LIMIT 100
    '''
    cur.execute(sample_query)
    rows = cur.fetchall()
    for r in rows:
        print(r)

cur.close()
conn.close()
