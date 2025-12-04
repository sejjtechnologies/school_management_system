from app import app, db
from models.timetable_model import TimeTableSlot
from models.user_models import User

app.app_context().push()

# Get one sample slot
slot = db.session.query(TimeTableSlot).first()
if slot:
    print(f"Sample slot - Class: {slot.class_id}, Stream: {slot.stream_id}, Subject: {slot.subject_id}")
    print(f"Teacher ID: {slot.teacher_id}")
    teacher = User.query.get(slot.teacher_id)
    if teacher:
        print(f"Teacher name: {teacher.first_name} {teacher.last_name}")
        print(f"Teacher email: {teacher.email}")
    print(f"\nTotal slots: {db.session.query(TimeTableSlot).count()}")
else:
    print("No timetable slots found in database")
