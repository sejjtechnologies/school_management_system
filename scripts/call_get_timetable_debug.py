from app import app
from models.timetable_model import TimeTableSlot
import json, traceback

with app.app_context():
    s = TimeTableSlot.query.filter((TimeTableSlot.classroom!=None)&(TimeTableSlot.classroom!='')).first()
    print('sample slot id', s.id if s else None)
    import routes.admin_routes as ar
    print('about to call ar.get_timetable')
    try:
        res = ar.get_timetable(s.class_id, s.stream_id)
        print('call returned, type:', type(res))
        try:
            data = res.get_data(as_text=True)
            print('data len', len(data))
            obj = json.loads(data)
            print('slots count', len(obj.get('slots', [])))
        except Exception:
            print('error reading response data')
            traceback.print_exc()
    except Exception:
        print('error calling get_timetable')
        traceback.print_exc()
print('done')
