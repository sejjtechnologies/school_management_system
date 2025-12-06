#!/usr/bin/env python3
"""Debug script to check stream_count calculation for a specific pupil"""

from app import app, db
from models.register_pupils import Pupil
from models.user_models import User

with app.app_context():
    # Test with pupil ID 24 (the one in the conversation)
    pupil_id = 24
    pupil = Pupil.query.get(pupil_id)

    if pupil:
        print(f"Pupil ID: {pupil.pupil_id}")
        print(f"Name: {pupil.first_name} {pupil.middle_name} {pupil.last_name}")
        print(f"Class ID: {pupil.class_id}")
        print(f"Stream ID: {pupil.stream_id}")
        print()

        # Calculate counts like the route does
        if getattr(pupil, 'class_id', None):
            class_count = Pupil.query.filter_by(class_id=pupil.class_id).count()
            print(f"Class {pupil.class_id} count: {class_count}")

        if getattr(pupil, 'stream_id', None):
            stream_count = Pupil.query.filter_by(stream_id=pupil.stream_id).count()
            print(f"Stream {pupil.stream_id} count: {stream_count}")
        else:
            print(f"Stream ID is None or falsy: {pupil.stream_id}")

        print()
        print("All pupils by class:")
        class_pupils = Pupil.query.filter_by(class_id=pupil.class_id).all()
        print(f"Total: {len(class_pupils)}")
        for p in class_pupils[:5]:
            print(f"  - {p.pupil_id}: {p.first_name} {p.last_name} (stream_id={p.stream_id})")
        if len(class_pupils) > 5:
            print(f"  ... and {len(class_pupils) - 5} more")

        print()
        print("All pupils by stream:")
        stream_pupils = Pupil.query.filter_by(stream_id=pupil.stream_id).all()
        print(f"Total: {len(stream_pupils)}")
        for p in stream_pupils[:5]:
            print(f"  - {p.pupil_id}: {p.first_name} {p.last_name}")
        if len(stream_pupils) > 5:
            print(f"  ... and {len(stream_pupils) - 5} more")
    else:
        print(f"Pupil ID {pupil_id} not found")
