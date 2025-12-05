from app import app
from models.register_pupils import Pupil

# Adjust these IDs for your environment
PUPIL_ID = 1

with app.test_client() as client:
    # Set a session user (simulate a logged-in parent)
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['parent_selected_pupil_id'] = PUPIL_ID

    resp = client.get(f"/api/parent/pupil/{PUPIL_ID}/attendance-summary?period=week&date=2025-12-05")
    print('STATUS:', resp.status_code)
    try:
        print(resp.get_json())
    except Exception as e:
        print('Could not parse JSON response:', e)
