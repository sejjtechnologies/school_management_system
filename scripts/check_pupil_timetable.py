from app import app
from models.register_pupils import Pupil
from models.timetable_model import TimeTableSlot

name_first = 'Ashaba'
name_last = 'Godwin'

with app.app_context():
    pupil = Pupil.query.filter_by(first_name=name_first, last_name=name_last).first()
    if not pupil:
        # fallback: search by first or last containing
        pupil = Pupil.query.filter(Pupil.first_name.ilike(f"%{name_first}%")).first()
    if not pupil:
        print('Pupil not found:', name_first, name_last)
    else:
        print('Pupil:', pupil.first_name, pupil.last_name, 'id=', pupil.id)
        print('Class:', getattr(pupil.class_, 'name', pupil.class_id), 'Stream:', getattr(pupil.stream, 'name', pupil.stream_id))
        slots = TimeTableSlot.query.filter_by(class_id=pupil.class_id, stream_id=pupil.stream_id).order_by(TimeTableSlot.day_of_week, TimeTableSlot.start_time).all()
        for slot in slots:
            if not slot.teacher or not slot.subject:
                continue
            print(slot.day_of_week, slot.start_time, slot.end_time, slot.subject.name, f"{slot.teacher.first_name} {slot.teacher.last_name}", getattr(slot, 'classroom', None))
