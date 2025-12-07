#!/usr/bin/env python3
import time
import os
os.environ['FLASK_ENV'] = 'development'
from app import app
import logging

def measure():
    with app.test_client() as c:
        pupil = None
        # find a pupil id via app context
        with app.app_context():
            from models.register_pupils import Pupil
            p = Pupil.query.first()
            if not p:
                print('No pupil found')
                return
            pupil = p.id
            # find a teacher user id to simulate login
            from models.user_models import User, Role
            teacher = User.query.join(Role, User.role_id == Role.id).filter(Role.role_name == 'Teacher').first()
            teacher_id = teacher.id if teacher else None
            if not teacher_id:
                print('No teacher user found; cannot simulate login')
        # set session user_id for test client
        if teacher_id:
            with c.session_transaction() as sess:
                sess['user_id'] = teacher_id
        url = f'/teacher/pupil/{pupil}/print?exam_ids=25,26'
        print('Requesting', url)
        # enable SQL logging to see what queries are executed
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        t0 = time.time()
        resp = c.get(url)
        t1 = time.time()
        print('Status code:', resp.status_code)
        print('Elapsed seconds:', t1-t0)
        # print a small portion of the response for sanity
        print('Response length:', len(resp.get_data(as_text=True)))

if __name__ == '__main__':
    measure()
