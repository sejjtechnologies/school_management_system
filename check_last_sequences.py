#!/usr/bin/env python3
"""
Query the database to find the last sequence numbers used for:
- admission_number (HPF format: HPF001, HPF002, ...)
- pupil_id (ID format: ID001, ID002, ...)
- receipt_number (RCT format: RCT-001, RCT-002, ...)
- roll_number (H25 format: H25/001, H25/002, ...)
"""

import os
from dotenv import load_dotenv
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

db.init_app(app)

def get_last_numbers():
    with app.app_context():
        # Get last pupil by ID
        last_pupil = Pupil.query.order_by(Pupil.id.desc()).first()
        
        if not last_pupil:
            print("❌ No pupils in database")
            return
        
        print("=" * 80)
        print("📊 LAST SEQUENCE NUMBERS IN DATABASE")
        print("=" * 80)
        print()
        
        # Extract numbers from each field
        admission_num = None
        if last_pupil.admission_number and last_pupil.admission_number.startswith("HPF"):
            try:
                admission_num = int(last_pupil.admission_number.replace("HPF", ""))
            except:
                pass
        
        pupil_id_num = None
        if last_pupil.pupil_id and last_pupil.pupil_id.startswith("ID"):
            try:
                pupil_id_num = int(last_pupil.pupil_id.replace("ID", ""))
            except:
                pass
        
        receipt_num = None
        if last_pupil.receipt_number and last_pupil.receipt_number.startswith("RCT-"):
            try:
                receipt_num = int(last_pupil.receipt_number.replace("RCT-", ""))
            except:
                pass
        
        roll_num = None
        if last_pupil.roll_number and last_pupil.roll_number.startswith("H25/"):
            try:
                roll_num = int(last_pupil.roll_number.replace("H25/", ""))
            except:
                pass
        
        print(f"📋 Last Pupil (ID: {last_pupil.id}):")
        print(f"   Name: {last_pupil.first_name} {last_pupil.last_name}")
        print(f"   Admission Date: {last_pupil.admission_date}")
        print()
        
        print("🔢 Last Sequence Numbers:")
        print(f"   admission_number:  {last_pupil.admission_number:<15} (sequence: {admission_num})")
        print(f"   pupil_id:          {last_pupil.pupil_id:<15} (sequence: {pupil_id_num})")
        print(f"   receipt_number:    {last_pupil.receipt_number:<15} (sequence: {receipt_num})")
        print(f"   roll_number:       {last_pupil.roll_number:<15} (sequence: {roll_num})")
        print()
        
        print("🚀 Next sequence numbers to use:")
        print(f"   admission_number:  HPF{str(admission_num + 1).zfill(3)}")
        print(f"   pupil_id:          ID{str(pupil_id_num + 1).zfill(3)}")
        print(f"   receipt_number:    RCT-{str(receipt_num + 1).zfill(3)}")
        print(f"   roll_number:       H25/{str(roll_num + 1).zfill(3)}")
        print()
        
        return {
            'admission': admission_num + 1,
            'pupil_id': pupil_id_num + 1,
            'receipt': receipt_num + 1,
            'roll': roll_num + 1,
            'admission_date': last_pupil.admission_date
        }

if __name__ == "__main__":
    get_last_numbers()
