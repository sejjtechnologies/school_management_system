from app import app
from models.timetable_model import TimeTableSlot

with app.app_context():
    slots = TimeTableSlot.query.filter_by(class_id=1, stream_id=2).order_by(TimeTableSlot.day_of_week, TimeTableSlot.start_time).all()
    print('queried slots count:', len(slots))
    if slots:
        s = slots[0]
        print('first slot:', s.id, s.day_of_week, s.start_time, getattr(s, 'classroom', None))
