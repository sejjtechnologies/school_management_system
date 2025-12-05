from app import app
from models.timetable_model import TimeTableSlot

with app.app_context():
    slots = TimeTableSlot.query.filter_by(class_id=1, stream_id=2).order_by(TimeTableSlot.day_of_week, TimeTableSlot.start_time).all()
    print('slots count', len(slots))
    for i, slot in enumerate(slots[:20]):
        print(f'[{i}] slot id', slot.id)
        try:
            tid = slot.teacher_id
            print('   teacher_id', tid)
        except Exception as e:
            print('   error reading teacher_id', e)
        try:
            tfirst = slot.teacher.first_name if slot.teacher else None
            print('   teacher.first_name', tfirst)
        except Exception as e:
            print('   error reading teacher.first_name', e)
        try:
            subj = slot.subject.name if slot.subject else None
            print('   subject', subj)
        except Exception as e:
            print('   error reading subject', e)
        try:
            cr = getattr(slot, 'classroom', None)
            print('   classroom', cr)
        except Exception as e:
            print('   error reading classroom', e)
