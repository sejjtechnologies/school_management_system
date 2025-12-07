#!/usr/bin/env python3
"""
Ensure each stream in each class (P1-P7) has exactly 100 pupils.
Uses exact route formatting: HPF533+, ID533+, RCT-533+, H25/533+

Usage:
    python ensure_stream_capacity_v2.py        # dry run
    python ensure_stream_capacity_v2.py --apply  # perform inserts
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
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"sslmode": "require"}}

db.init_app(app)

# Formatting functions (matching secretary_routes.py)
def generate_admission_number(seq):
    return f"HPF{str(seq).zfill(3)}"


def generate_receipt_number(seq):
    return f"RCT-{str(seq).zfill(3)}"


def generate_pupil_id(seq):
    return f"ID{str(seq).zfill(3)}"


def generate_roll_number(seq):
    return f"H25/{str(seq).zfill(3)}"


GENDERS = ["Male", "Female"]
NATIONALITY = "UG"


def create_placeholder_pupil(class_id, stream_id, class_name, stream_name, seq):
    first_name = f"Auto_{class_name}_{stream_name}_{seq}"
    last_name = "Student"
    
    pupil = Pupil(
        pupil_id=generate_pupil_id(seq),
        admission_number=generate_admission_number(seq),
        admission_date=date.today(),
        first_name=first_name,
        middle_name=None,
        last_name=last_name,
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
        roll_number=generate_roll_number(seq),
        enrollment_status="active",
        receipt_number=generate_receipt_number(seq)
    )
    return pupil


def ensure_capacity(apply=False):
    with app.app_context():
        print("🔗 Connecting to database...\n")
        
        # Use raw SQL to get class/stream counts (faster)
        query_str = """
        SELECT 
            c.id, c.name, 
            s.id, s.name,
            COUNT(p.id) as count
        FROM classes c
        CROSS JOIN streams s
        LEFT JOIN pupils p ON p.class_id = c.id AND p.stream_id = s.id
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        GROUP BY c.id, c.name, s.id, s.name
        ORDER BY c.id, s.id
        """
        
        result = db.session.execute(text(query_str))
        rows = result.fetchall()
        
        print(f"📊 Classes and Streams found: {len(rows)} combinations\n")
        
        plan = []
        total_to_create = 0
        
        for class_id, class_name, stream_id, stream_name, count in rows:
            need = max(0, 100 - count)
            if need > 0:
                plan.append((class_id, class_name, stream_id, stream_name, count, need))
                total_to_create += need
        
        if not plan:
            print("✅ All class-streams already have >= 100 pupils. Nothing to do.")
            return
        
        print("📋 DRY RUN PLAN (items to create per class/stream):\n")
        print(f"{'Class':<8} {'Stream':<10} {'Current':<10} {'Need':<10}")
        print("-" * 40)
        
        for class_id, class_name, stream_id, stream_name, count, need in plan:
            print(f"{class_name:<8} {stream_name:<10} {count:<10} {need:<10}")
        
        print("-" * 40)
        print(f"\n📈 Total new pupils to create: {total_to_create}\n")
        
        if not apply:
            print("🚀 Run with --apply to perform inserts.")
            print(f"   Starting from: HPF533, ID533, RCT-533, H25/533")
            return
        
        # APPLY: Create records
        print("💾 APPLYING CHANGES: Creating placeholder pupils...\n")
        
        seq = 533  # Start from last+1 (HPF532 was last)
        created = 0
        
        try:
            for class_id, class_name, stream_id, stream_name, count, need in plan:
                print(f"   Creating {need} pupils for {class_name} - {stream_name}...")
                
                for i in range(need):
                    # Double-check no collision
                    while Pupil.query.filter_by(admission_number=generate_admission_number(seq)).first():
                        seq += 1
                    
                    pupil = create_placeholder_pupil(class_id, stream_id, class_name, stream_name, seq)
                    db.session.add(pupil)
                    created += 1
                    seq += 1
                
                # Commit per class/stream for safety
                db.session.commit()
            
            print(f"\n✅ Successfully created {created} new pupil records.\n")
            
            # Final verification
            print("=" * 80)
            print("📊 FINAL VERIFICATION")
            print("=" * 80)
            print()
            
            verify_query = """
            SELECT 
                c.name, s.name,
                COUNT(p.id) as count
            FROM classes c
            LEFT JOIN pupils p ON p.class_id = c.id
            LEFT JOIN streams s ON p.stream_id = s.id
            WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
            GROUP BY c.name, s.name
            ORDER BY c.name, s.name
            """
            
            verify_result = db.session.execute(text(verify_query))
            verify_rows = verify_result.fetchall()
            
            grand_total = 0
            for class_name, stream_name, count in verify_rows:
                status = "✅" if count == 100 else "⚠️ "
                print(f"{status} {class_name} - {stream_name}: {count}")
                grand_total += count
            
            print()
            print("=" * 80)
            print(f"🎯 GRAND TOTAL: {grand_total} pupils\n")
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ensure 100 pupils per stream per class')
    parser.add_argument('--apply', action='store_true', help='Apply changes (insert records).')
    args = parser.parse_args()
    ensure_capacity(apply=args.apply)
