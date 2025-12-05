from app import app
from models.timetable_model import TimeTableSlot
import json, traceback

with app.app_context():
    s = TimeTableSlot.query.filter((TimeTableSlot.classroom!=None)&(TimeTableSlot.classroom!='')).first()
    print('sample slot id', s.id if s else None)
    from routes import admin_routes
    try:
        res = admin_routes.get_timetable(s.class_id, s.stream_id)
        print('get_timetable returned type:', type(res))
        try:
            data = res.get_data(as_text=True)
            print('response length', len(data))
            obj = json.loads(data)
            print('slots keys:', list(obj.keys()))
            print('first slot keys:', list(obj['slots'][0].keys()) if obj.get('slots') else None)
        except Exception as e:
            print('error reading response data:')
            traceback.print_exc()
    except Exception as e:
        print('error calling get_timetable:')
        traceback.print_exc()
