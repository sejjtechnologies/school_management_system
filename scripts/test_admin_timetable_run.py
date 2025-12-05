from app import app
from models.timetable_model import TimeTableSlot
import json, traceback

with app.app_context():
    s = TimeTableSlot.query.filter((TimeTableSlot.classroom!=None)&(TimeTableSlot.classroom!='')).first()
    if not s:
        print('No slot with classroom found')
    else:
        print('Sample slot id:', s.id)
        print('class_id, stream_id:', s.class_id, s.stream_id)
        print('classroom:', s.classroom)

    from routes.admin_routes import get_timetable
    if s:
        try:
            res = get_timetable(s.class_id, s.stream_id)
            data = res.get_data(as_text=True)
            obj = json.loads(data)
            slots = obj.get('slots', [])
            print('\nslots returned:', len(slots))
            if len(slots) > 0:
                print('first slot keys:', list(slots[0].keys()))
                print('first slot sample:', slots[0])
        except Exception as e:
            print('Error calling get_timetable:')
            traceback.print_exc()
