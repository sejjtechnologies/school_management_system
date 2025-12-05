from app import app
from models.register_pupils import Pupil
from models.user_models import User
from routes.parent_routes import view_attendance

with app.app_context():
    p = Pupil.query.first()
    if not p:
        print('no pupil found')
    else:
        # find any user with role 'Parent'
        parent = User.query.join(User.role).filter(User.role.has()).first()
        # fallback: use first user id
        uid = parent.id if parent else 1
        path = f"/parent/pupil/{p.id}/attendance?period=week"
        # Use test_request_context to set session
        with app.test_request_context(path):
            # set session via flask session interface
            from flask import session
            session['user_id'] = uid
            session['parent_selected_pupil_id'] = p.id
            resp = view_attendance(p.id)
            try:
                data = resp.get_data(as_text=True)
                print('rendered length', len(data))
                print(data[:500])
            except Exception as e:
                print('response type', type(resp))
                print('error reading response:', e)
