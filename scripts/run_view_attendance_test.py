from app import app
from models.register_pupils import Pupil
from routes.parent_routes import view_attendance

with app.app_context():
    p = Pupil.query.first()
    if not p:
        print('no pupil found')
    else:
        print('testing pupil id', p.id)
        resp = view_attendance(p.id)
        try:
            data = resp.get_data(as_text=True)
            print('rendered length', len(data))
            print(data[:500])
        except Exception as e:
            print('response type', type(resp))
            print('error reading response:', e)
