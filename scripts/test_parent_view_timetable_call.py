from app import app
from models.register_pupils import Pupil
import json

with app.app_context():
    # find a pupil in class 1 stream 2 (sample used earlier)
    pupil = Pupil.query.filter_by(class_id=1, stream_id=2).first()
    if not pupil:
        print('No pupil found in class 1 stream 2')
    else:
        print('Found pupil id', pupil.id, 'name', getattr(pupil, 'first_name', None))
        from routes.parent_routes import view_timetable
        html = view_timetable(pupil.id)
        # view_timetable returns a rendered template string
        print('Rendered timetable length:', len(html))
        # optionally write to file for inspection
        with open('tmp_parent_timetable.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('Wrote tmp_parent_timetable.html')
