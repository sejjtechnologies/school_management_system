import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print('DATABASE_URL not set in environment or .env')
    raise SystemExit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print('Connected to DB')
    # Roles
    res = conn.execute(text("SELECT id, role_name FROM roles ORDER BY id"))
    roles = res.fetchall()
    print('\nRoles:')
    for r in roles:
        print(f'  id={r.id} name={r.role_name}')

    # Teachers (users with role 'teacher')
    res = conn.execute(text(
        "SELECT u.id, u.first_name, u.last_name, u.email, u.role_id FROM users u JOIN roles r ON u.role_id=r.id WHERE r.role_name='teacher' ORDER BY u.id"
    ))
    teachers = res.fetchall()
    print(f"\nTeachers ({len(teachers)}):")
    for t in teachers:
        print(f"  id={t.id} {t.first_name} {t.last_name} <{t.email}> role_id={t.role_id}")

    # Classes and Streams
    res = conn.execute(text("SELECT id, name FROM classes ORDER BY id"))
    classes = res.fetchall()
    res = conn.execute(text("SELECT id, name FROM streams ORDER BY id"))
    streams = res.fetchall()
    print(f"\nClasses ({len(classes)}): {[c.name for c in classes]}")
    print(f"Streams ({len(streams)}): {[s.name for s in streams]}\n")

    # Count timetable slots per class-stream
    res = conn.execute(text(
        "SELECT class_id, stream_id, count(*) as cnt FROM timetable_slots GROUP BY class_id, stream_id ORDER BY class_id, stream_id"
    ))
    rows = res.fetchall()
    if rows:
        print('Timetable slots per class-stream:')
        for r in rows:
            print(f"  class_id={r.class_id} stream_id={r.stream_id} slots={r.cnt}")
    else:
        print('No timetable slots found')

    # Total slots
    res = conn.execute(text("SELECT count(*) FROM timetable_slots"))
    total = res.scalar()
    print(f"\nTotal timetable slots: {total}")
