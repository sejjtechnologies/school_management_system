#!/usr/bin/env python
"""
Simple duplicate test - logs to file instead of printing interactively
"""
from app import app, db
from models.register_pupils import Pupil
from models.marks_model import Subject, Exam, Mark

import sys

results = []

try:
    with app.test_client() as client:
        with app.app_context():
            # Find a teacher user to set in session
            from models.user_models import User, Role
            teacher_role = Role.query.filter_by(role_name='Teacher').first()
            teacher_user = None
            if teacher_role:
                teacher_user = User.query.filter_by(role_id=teacher_role.id).first()

            if not teacher_user:
                results.append("❌ No teacher found in database")
                sys.exit(1)

            # set session to that teacher
            with client.session_transaction() as sess:
                sess['user_id'] = teacher_user.id
                sess['role'] = 'Teacher'

            pupil = Pupil.query.first()
            subjects = Subject.query.limit(3).all()
            
            if not pupil or not subjects:
                results.append("❌ Missing pupil or subjects")
                sys.exit(1)

            data = {
                'pupil_id': str(pupil.id),
                'term': '1',
                'year': '2025',
                'exam_name': 'Midterm'
            }
            for subj in subjects:
                data[f'score_{subj.id}'] = '50'

            # First POST (should succeed)
            headers = {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
            resp1 = client.post('/teacher/manage_marks', data=data, headers=headers)
            
            results.append(f"FIRST POST:")
            results.append(f"  Status: {resp1.status_code}")
            try:
                body = resp1.get_json()
                results.append(f"  Body: {body}")
            except:
                results.append(f"  Body: (non-JSON)")

            # Second POST (should fail with 400)
            resp2 = client.post('/teacher/manage_marks', data=data, headers=headers)
            
            results.append(f"\nSECOND POST (duplicate):")
            results.append(f"  Status: {resp2.status_code}")
            try:
                body = resp2.get_json()
                results.append(f"  Body: {body}")
            except:
                results.append(f"  Body: (non-JSON)")

            results.append(f"\n✅ TEST RESULTS:")
            if resp1.status_code == 200 and resp2.status_code == 400:
                results.append("✅✅✅ PASS: First POST succeeded (200), second POST rejected (400)")
            else:
                results.append(f"❌ FAIL: Expected 200 then 400, got {resp1.status_code} then {resp2.status_code}")

except Exception as e:
    results.append(f"❌ Exception: {e}")
    import traceback
    results.append(traceback.format_exc())

# Print results
for line in results:
    print(line)

# Also write to file
with open('test_result.txt', 'w') as f:
    for line in results:
        f.write(line + '\n')
print("\n✅ Results saved to test_result.txt")
