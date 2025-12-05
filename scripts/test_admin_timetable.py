from app import app
from models.timetable_model import TimeTableSlot
import json

"""
Test script that builds the same response as the admin get_timetable endpoint
but without calling the route function (some route calls hang in this environment).
This prints a sample slot and the keys returned (including 'classroom').
"""

with app.app_context():
    s = TimeTableSlot.query.filter((TimeTableSlot.classroom!=None)&(TimeTableSlot.classroom!='')).first()
    if not s:
        print('No slot with classroom found')
    else:
        print('Sample slot id:', s.id)
        print('class_id, stream_id:', s.class_id, s.stream_id)
        print('classroom:', s.classroom)

    # Build the slot_data payload similarly to admin_routes.get_timetable
    if s:
        slots = TimeTableSlot.query.filter_by(class_id=s.class_id, stream_id=s.stream_id)\
            .order_by(TimeTableSlot.day_of_week, TimeTableSlot.start_time).all()
        slot_data = []
        for slot in slots:
            slot_data.append({
                'id': slot.id,
                'teacher_id': slot.teacher_id,
                'teacher_name': f"{slot.teacher.first_name} {slot.teacher.last_name}" if slot.teacher else "Unassigned",
                'subject_id': slot.subject_id,
                'subject_name': slot.subject.name if slot.subject else "Unassigned",
                'classroom': getattr(slot, 'classroom', '') or '',
                'day_of_week': slot.day_of_week,
                'start_time': slot.start_time,
                'end_time': slot.end_time,
            })

        print('\nslots returned:', len(slot_data))
        if len(slot_data) > 0:
            print('first slot keys:', list(slot_data[0].keys()))
            print('first slot sample:', slot_data[0])
