from app import app, db
from models.register_pupils import Pupil
from models.marks_model import Subject, Exam, Mark

# This script will use Flask test client to POST marks for the first pupil and then attempt duplicate
with app.test_client() as client:
    with app.app_context():
        # Find a teacher user to set in session
        from models.user_models import User, Role
        teacher_role = Role.query.filter_by(role_name='Teacher').first()
        teacher_user = None
        if teacher_role:
            teacher_user = User.query.filter_by(role_id=teacher_role.id).first()

        if teacher_user:
            # set session to that teacher
            with client.session_transaction() as sess:
                sess['user_id'] = teacher_user.id
                sess['role'] = 'Teacher'

        pupil = Pupil.query.first()
        if not pupil:
            print('No pupils found in DB')
            exit(1)
        subjects = Subject.query.limit(3).all()
        if not subjects:
            print('No subjects found in DB')
            exit(1)

        data = {
            'pupil_id': str(pupil.id),
            'term': '1',
            'year': '2025',
            'exam_name': 'Midterm'
        }
        for subj in subjects:
            data[f'score_{subj.id}'] = '50'

        # First POST (simulate AJAX by sending headers)
        headers = {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
        resp1 = client.post('/teacher/manage_marks', data=data, headers=headers)
        print('First POST status:', resp1.status_code)
        try:
            print('First POST body:', resp1.get_json())
        except Exception:
            print('First POST non-json response body length:', len(resp1.data))

        # Second POST (duplicate)
        resp2 = client.post('/teacher/manage_marks', data=data, headers=headers)
        print('Second POST status:', resp2.status_code)
        try:
            print('Second POST body:', resp2.get_json())
        except Exception:
            print('Second POST non-json response body length:', len(resp2.data))
