from app import app, db
from models.register_pupils import Pupil
from routes.parent_routes import view_reports

# Simulate a request to the reports route
with app.test_request_context('/parent/pupil/24/reports?term=1&year=2025'):
    # Get what the route would return
    pupil = Pupil.query.get(24)

    # Calculate the same way the route does
    class_count = Pupil.query.filter_by(class_id=pupil.class_id).count() if getattr(pupil, 'class_id', None) else None
    stream_count = Pupil.query.filter_by(stream_id=pupil.stream_id).count() if getattr(pupil, 'stream_id', None) else None

    print(f'Pupil: {pupil.first_name} {pupil.last_name}')
    print(f'Stream ID: {pupil.stream_id}, Class ID: {pupil.class_id}')
    print(f'Stream count calculated: {stream_count}')
    print(f'Class count calculated: {class_count}')
