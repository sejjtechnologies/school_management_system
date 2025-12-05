from app import app
from models.register_pupils import Pupil
from models.timetable_model import TimeTableSlot

with app.app_context():
    pupil = Pupil.query.filter_by(class_id=1, stream_id=2).first()
    if not pupil:
        print('No pupil found for class 1 stream 2')
    else:
        print('Pupil:', pupil.first_name, pupil.last_name, 'id=', pupil.id)
        timetable = TimeTableSlot.query.filter_by(class_id=pupil.class_id, stream_id=pupil.stream_id).all()
        print('timetable raw count:', len(timetable))
        schedule = {}
        cnt_with = 0
        for slot in timetable:
            if not slot.teacher or not slot.subject:
                continue
            cnt_with += 1
            day = slot.day_of_week
            if day not in schedule:
                schedule[day] = []
            schedule[day].append({
                'start_time': slot.start_time,
                'end_time': slot.end_time,
                'subject': slot.subject.name,
                'teacher': f"{slot.teacher.first_name} {slot.teacher.last_name}".strip(),
                'classroom': getattr(slot, 'classroom', None)
            })
        print('slots with teacher+subject:', cnt_with)
        # print summary
        print('Total days with slots:', len(schedule))
        for day, slots in schedule.items():
            print(f"Day: {day} ({len(slots)} slots)")
            for s in slots[:3]:
                print('  ', s['start_time'], s['subject'], '->', s['teacher'], 'classroom=', s['classroom'])
            break
