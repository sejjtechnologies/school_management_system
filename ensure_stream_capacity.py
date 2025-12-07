#!/usr/bin/env python3
"""
Ensure each stream in each class (P1-P7) has exactly 100 pupils.
This script runs in dry-run mode by default and will only INSERT records when run with --apply.

Usage:
    python ensure_stream_capacity.py        # dry run
    python ensure_stream_capacity.py --apply  # perform inserts

The script creates placeholder pupil records with unique admission_number and receipt_number.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from datetime import date
from flask import Flask
from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Mark, Report

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"sslmode": "require"}}

# Initialize DB
db.init_app(app)

# Minimal placeholder data generators
GENDERS = ["Male", "Female"]
NATIONALITY = "UG"


def generate_admission_number(seq):
    """Format: HPF533, HPF534, ..."""
    return f"HPF{str(seq).zfill(3)}"


def generate_receipt_number(seq):
    """Format: RCT-533, RCT-534, ..."""
    return f"RCT-{str(seq).zfill(3)}"


def generate_pupil_id(seq):
    """Format: ID533, ID534, ..."""
    return f"ID{str(seq).zfill(3)}"


def generate_roll_number(seq):
    """Format: H25/533, H25/534, ..."""
    return f"H25/{str(seq).zfill(3)}"


def placeholder_name(class_name, stream_name, seq):
    return (f"Auto_{class_name}_{stream_name}_{seq}", "Student")


def create_placeholder_pupil(class_id, stream_id, class_name, stream_name, seq):
    first, last = placeholder_name(class_name, stream_name, seq)
    admission_number = generate_admission_number(seq)
    receipt_number = generate_receipt_number(seq)
    pupil_id = generate_pupil_id(seq)
    roll_number = generate_roll_number(seq)

    pupil = Pupil(
        pupil_id=pupil_id,
        admission_number=admission_number,
        admission_date=date.today(),
        first_name=first,
        middle_name=None,
        last_name=last,
        gender=GENDERS[seq % len(GENDERS)],
        dob=date(2015, 1, 1),
        nationality=NATIONALITY,
        place_of_birth="",
        photo=None,
        home_address="Auto-generated",
        phone="0000000000",
        email=None,
        emergency_contact="Auto Guardian",
        emergency_phone="0000000000",
        guardian_name="Auto Guardian",
        guardian_relationship="Parent",
        guardian_occupation="",
        guardian_phone="0000000000",
        guardian_address="",
        class_id=class_id,
        stream_id=stream_id,
        previous_school=None,
        roll_number=roll_number,
        enrollment_status="active",
        receipt_number=receipt_number
    )
    return pupil


def ensure_capacity(apply=False):
    with app.app_context():
        classes = Class.query.filter(Class.name.in_(['P1','P2','P3','P4','P5','P6','P7'])).order_by(Class.name).all()
        streams = Stream.query.order_by(Stream.name).all()

        if not classes:
            print("No classes P1-P7 found. Aborting.")
            return
        if not streams:
            print("No streams found. Aborting.")
            return

        print(f"Found classes: {[c.name for c in classes]}")
        print(f"Found streams: {[s.name for s in streams]}\n")

        total_to_create = 0
        plan = []

        # Compute existing counts per class/stream
        for c in classes:
            for s in streams:
                count = Pupil.query.filter_by(class_id=c.id, stream_id=s.id).count()
                need = max(0, 100 - count)
                if need > 0:
                    plan.append((c, s, count, need))
                    total_to_create += need

        if not plan:
            print("All class-streams already have >= 100 pupils. Nothing to do.")
            return

        print("Dry run plan (items to create per class/stream):")
        for c, s, count, need in plan:
            print(f"  Class {c.name} - Stream {s.name}: {count} present, need {need}")
        print(f"\nTotal new pupils to create: {total_to_create}\n")

        if not apply:
            print("Run with --apply to perform inserts.")
            return

        # APPLY mode: create records
        print("Applying changes: creating placeholder pupils...")
        created = 0
        seq = 533  # Start from HPF533 (last was HPF532)
        try:
            for c, s, count, need in plan:
                for i in range(need):
                    # Ensure no collision - check admission_number uniqueness
                    while Pupil.query.filter_by(admission_number=generate_admission_number(seq)).first():
                        seq += 1

                    pupil = create_placeholder_pupil(c.id, s.id, c.name, s.name, seq)
                    db.session.add(pupil)
                    created += 1
                    seq += 1

            db.session.commit()
            print(f"✅ Created {created} new pupil records and committed to database.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating pupils: {e}")
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ensure 100 pupils per stream per class (P1-P7)')
    parser.add_argument('--apply', action='store_true', help='Apply changes (insert records).')
    args = parser.parse_args()
    ensure_capacity(apply=args.apply)
