#!/usr/bin/env python3
"""
Insert placeholder pupils for any class/stream combination with < 100 pupils.
Uses exact route formatting and matches ALL required fields from secretary_routes.py submit_pupil() function.

Numbering (starting from HPF533):
- admission_number: HPF533, HPF534, ... (from generate_admission_number)
- pupil_id: ID533, ID534, ... (from generate_pupil_id)
- receipt_number: RCT-533, RCT-534, ... (from generate_receipt_number)
- roll_number: H25/533, H25/534, ... (from generate_roll_number)

Usage:
    python insert_pupils_to_100.py                    # dry run: show plan
    python insert_pupils_to_100.py --apply            # apply: insert records
    python insert_pupils_to_100.py --apply --verbose  # apply with detailed output
"""

import os
import sys
import argparse
import random
from dotenv import load_dotenv
from datetime import date, datetime
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

# ============================================================================
# NUMBERING FUNCTIONS (matching secretary_routes.py)
# ============================================================================

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


# ============================================================================
# CONSTANTS
# ============================================================================

GENDERS = ["Male", "Female"]
NATIONALITIES = ["UG", "KE", "TZ", "RW", "ZA"]
ENROLLMENT_STATUS = "active"

GENDERS = ["Male", "Female"]
NATIONALITIES = ["UG", "KE", "TZ", "RW", "ZA"]
ENROLLMENT_STATUS = "active"

# Real East African Tribal Names (Baganda, Banyankole, Kikuyu, Maasai, Somali, Oromo, Samburu, Rendille, etc.)
EAST_AFRICAN_FIRST_NAMES = [
    # Baganda
    "Kabaka", "Nswaswa", "Mutaka", "Mwebaza", "Mugwanya", "Lubega", "Kawula", "Namulondo", "Nakawesi", "Namutebi",
    # Banyankole
    "Omugabe", "Kaguta", "Byamugisha", "Tumwesigire", "Karegyeya", "Kiregyeya", "Rujumbura", "Ruhinda", "Mwambutsa", "Kyabazinga",
    # Kikuyu
    "Kariuki", "Wanjiru", "Muthondu", "Gichuhi", "Njoroge", "Kamau", "Kinyanjui", "Mwangi", "Kinyata", "Muthoni",
    # Maasai
    "Lenapato", "Lesuuda", "Tepilil", "Sosian", "Kipchoge", "Nairobi", "Lengai", "Morintat", "Laikipia", "Kilimanjaro",
    # Somali
    "Mohamud", "Farah", "Hassan", "Ibrahim", "Ahmed", "Abdi", "Mohamed", "Nur", "Saeed", "Amina",
    # Oromo
    "Waaqo", "Gandi", "Tolossa", "Belay", "Muleta", "Tegegne", "Assefa", "Adugna", "Mekonnen", "Bekele",
    # Samburu
    "Laiboni", "Mpaka", "Parsimei", "Loperet", "Lemeyo", "Lemong", "Letoile", "Lefkir", "Lekuniet", "Lemisiyoi",
    # Rendille
    "Ariaal", "Dida", "Dasse", "Rendilli", "Garri", "Hurri", "Garre", "Somal", "Boran", "Gabbra",
    # Luo
    "Odhiambo", "Okello", "Kiplagat", "Kahumba", "Kipchoke", "Kiplagat", "Koech", "Kiplagat", "Kiplagat", "Kiplagat",
    # Sambaa
    "Nyaigoti", "Nyambane", "Nyakwaka", "Nyantiti", "Nyarwoth", "Nyagudi", "Nyabera", "Nyabiri", "Nyagudi", "Nyamuhanga"
]

EAST_AFRICAN_LAST_NAMES = [
    # Baganda
    "Ssemakula", "Kiggundu", "Kisamba", "Kigozi", "Bikira", "Birungi", "Ssenfuma", "Muwanga", "Tumuhairwe", "Byaruhanga",
    "Nkurunungi", "Kahigiriza", "Muhereza", "Mbabazi", "Karamagi", "Kalibala", "Kitaka", "Kisiragi", "Kiggundu", "Kakaire",
    # Banyankole
    "Byamugisha", "Tumwesigire", "Karegyeya", "Kiregyeya", "Rujumbura", "Ruhinda", "Mwambutsa", "Kyabazinga", "Kahigiriza", "Nyaigoti",
    # Kikuyu
    "Kariuki", "Wanjiru", "Mwangi", "Njoroge", "Gitau", "Kipchoge", "Kiplagat", "Koech", "Kamau", "Kinyanjui",
    "Muthondu", "Gichuhi", "Kipchoge", "Kiplagat", "Kipkemboi", "Kiprotich", "Kipketer", "Kipchoge", "Kipkemboi", "Kiplagat",
    # Maasai
    "Kipchoge", "Kiplagat", "Koech", "Kipkemboi", "Kiprotich", "Kipketer", "Kipchoge", "Kipkemboi", "Kiplagat", "Kipchoge",
    # Somali
    "Musa", "Ali", "Hassan", "Ibrahim", "Ahmed", "Abdulla", "Mohamed", "Juma", "Said", "Fatima",
    "Hassan", "Ahmed", "Abdi", "Mohamed", "Nur", "Saeed", "Hassan", "Ali", "Ibrahim", "Farah",
    # Oromo
    "Kebede", "Abebe", "Dawit", "Tadesse", "Assefa", "Feleke", "Getaneh", "Muleta", "Tegaye", "Bizunesh",
    "Tolossa", "Belay", "Tegegne", "Adugna", "Mekonnen", "Bekele", "Assefa", "Tolossa", "Belay", "Muleta",
    # Samburu & Rendille
    "Kipchoge", "Kiplagat", "Koech", "Kiplagat", "Kipchoge", "Kipkemboi", "Kiprotich", "Kipketer", "Kipchoge", "Kiplagat"
]

def create_placeholder_pupil(class_id, stream_id, class_name, stream_name, seq, verbose=False):
    """
    Create a pupil matching ALL fields required by secretary_routes.py submit_pupil()
    
    Required fields (from route):
    - pupil_id, admission_date, first_name, last_name, gender, dob, nationality,
      place_of_birth, home_address, phone, email, emergency_contact, emergency_phone,
      guardian_name, guardian_relationship, guardian_occupation, guardian_phone,
      guardian_address, class_id, stream_id, previous_school, roll_number, photo,
      admission_number, receipt_number, enrollment_status
    
    Optional fields (can be None):
    - middle_name, place_of_birth, email, guardian_occupation, guardian_address, photo, previous_school
    """
    
    # Generate IDs using the same logic as route
    admission_number = generate_admission_number(seq)
    receipt_number = generate_receipt_number(seq)
    pupil_id = generate_pupil_id(seq)
    roll_number = generate_roll_number(seq)
    
    # Generate names from East African tribal names
    first_name = random.choice(EAST_AFRICAN_FIRST_NAMES)
    middle_name = random.choice(EAST_AFRICAN_FIRST_NAMES)
    last_name = random.choice(EAST_AFRICAN_LAST_NAMES)
    gender = GENDERS[seq % len(GENDERS)]
    dob = date(2015, 1, 1)
    nationality = NATIONALITIES[seq % len(NATIONALITIES)]
    place_of_birth = ""
    home_address = "Auto-generated Placeholder"
    phone = "0000000000"
    email = None
    emergency_contact = "Auto Guardian"
    emergency_phone = "0000000000"
    guardian_name = "Placeholder Guardian"
    guardian_relationship = "Parent"
    guardian_occupation = ""
    guardian_phone = "0000000000"
    guardian_address = ""
    previous_school = None
    photo = None
    
    # Today's date for admission_date
    admission_date = date.today()
    
    pupil = Pupil(
        # Auto-generated by route
        pupil_id=pupil_id,
        admission_number=admission_number,
        receipt_number=receipt_number,
        roll_number=roll_number,
        admission_date=admission_date,
        
        # Personal info
        first_name=first_name,
        middle_name=None,
        last_name=last_name,
        gender=gender,
        dob=dob,
        nationality=nationality,
        place_of_birth=place_of_birth,
        photo=photo,
        
        # Contacts
        home_address=home_address,
        phone=phone,
        email=email,
        emergency_contact=emergency_contact,
        emergency_phone=emergency_phone,
        
        # Guardian
        guardian_name=guardian_name,
        guardian_relationship=guardian_relationship,
        guardian_occupation=guardian_occupation,
        guardian_phone=guardian_phone,
        guardian_address=guardian_address,
        
        # Academic
        class_id=class_id,
        stream_id=stream_id,
        previous_school=previous_school,
        enrollment_status=ENROLLMENT_STATUS,
    )
    
    if verbose:
        print(f"      [{seq}] Created: {first_name} {last_name} | "
              f"Admission: {admission_number} | Pupil ID: {pupil_id}")
    
    return pupil


def insert_pupils_to_100(apply=False, verbose=False):
    """Main insertion logic"""
    
    with app.app_context():
        print("[*] Connecting to database...\n")
        
        # Query to find class/stream combinations and their current pupil counts
        query_str = """
        SELECT 
            c.id as class_id,
            c.name as class_name, 
            s.id as stream_id,
            s.name as stream_name,
            COUNT(p.id) as pupil_count
        FROM classes c
        CROSS JOIN streams s
        LEFT JOIN pupils p ON p.class_id = c.id AND p.stream_id = s.id
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        GROUP BY c.id, c.name, s.id, s.name
        ORDER BY c.id, s.id
        """
        
        try:
            result = db.session.execute(text(query_str))
            rows = result.fetchall()
        except Exception as e:
            print(f"[ERROR] Database query error: {e}")
            return
        
        if not rows:
            print("[ERROR] No classes or streams found")
            return
        
        # Build insertion plan
        plan = []
        total_to_insert = 0
        
        for class_id, class_name, stream_id, stream_name, pupil_count in rows:
            need = max(0, 100 - pupil_count)
            if need > 0:
                plan.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'stream_id': stream_id,
                    'stream_name': stream_name,
                    'current_count': pupil_count,
                    'need': need
                })
                total_to_insert += need
        
        # Display plan
        print("=" * 90)
        print("📊 INSERTION PLAN (for class/streams with < 100 pupils)")
        print("=" * 90)
        print()
        
        if not plan:
            print("✅ All class/stream combinations already have 100 pupils. Nothing to do.")
            return
        
        print(f"{'Class':<8} {'Stream':<12} {'Current':<10} {'Need':<10} {'Total After':<12}")
        print("-" * 90)
        
        for item in plan:
            total_after = item['current_count'] + item['need']
            print(f"{item['class_name']:<8} {item['stream_name']:<12} "
                  f"{item['current_count']:<10} {item['need']:<10} {total_after:<12}")
        
        print("-" * 90)
        print(f"\n📈 Total pupils to insert: {total_to_insert}")
        print(f"   Numbering will start from: HPF533 / ID533 / RCT-533 / H25/533\n")
        
        if not apply:
            print("🚀 Run with --apply to perform insertions.")
            return
        
        # ====================================================================
        # APPLY: Perform insertions
        # ====================================================================
        
        print("=" * 90)
        print("💾 APPLYING INSERTIONS")
        print("=" * 90)
        print()
        
        seq = 533  # Start from last+1
        total_created = 0
        
        try:
            for item in plan:
                class_id = item['class_id']
                class_name = item['class_name']
                stream_id = item['stream_id']
                stream_name = item['stream_name']
                need = item['need']
                
                print(f"📝 {class_name} - {stream_name}: inserting {need} pupils")
                
                for i in range(need):
                    # Ensure no collision with existing admission numbers
                    while Pupil.query.filter_by(admission_number=generate_admission_number(seq)).first():
                        seq += 1
                    
                    # Create and add pupil
                    pupil = create_placeholder_pupil(class_id, stream_id, class_name, stream_name, seq, verbose=verbose)
                    db.session.add(pupil)
                    total_created += 1
                    seq += 1
                
                # Flush per class/stream to catch errors early
                try:
                    db.session.flush()
                except Exception as e:
                    print(f"   ❌ Error during flush for {class_name}-{stream_name}: {e}")
                    db.session.rollback()
                    raise
            
            # Commit all at once
            db.session.commit()
            print(f"\n✅ Successfully inserted {total_created} pupils into database.\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Insertion failed: {e}")
            raise
        
        # ====================================================================
        # VERIFICATION
        # ====================================================================
        
        print("=" * 90)
        print("📊 FINAL VERIFICATION")
        print("=" * 90)
        print()
        
        verify_query = """
        SELECT 
            c.name as class_name,
            s.name as stream_name,
            COUNT(p.id) as count
        FROM classes c
        CROSS JOIN streams s
        LEFT JOIN pupils p ON p.class_id = c.id AND p.stream_id = s.id
        WHERE c.name IN ('P1','P2','P3','P4','P5','P6','P7')
        GROUP BY c.id, c.name, s.id, s.name
        ORDER BY c.id, s.id
        """
        
        verify_result = db.session.execute(text(verify_query))
        verify_rows = verify_result.fetchall()
        
        print(f"{'Class':<8} {'Stream':<12} {'Total Pupils':<15} {'Status':<20}")
        print("-" * 55)
        
        grand_total = 0
        all_perfect = True
        
        for class_name, stream_name, count in verify_rows:
            status = "✅ 100" if count == 100 else f"⚠️  {count}"
            print(f"{class_name:<8} {stream_name:<12} {count:<15} {status:<20}")
            grand_total += count
            if count != 100:
                all_perfect = False
        
        print("-" * 55)
        print(f"{'TOTAL':<8} {'':<12} {grand_total:<15}\n")
        
        if all_perfect:
            print("🎉 SUCCESS: All class/stream combinations now have exactly 100 pupils!")
        else:
            print("⚠️  Some class/streams still don't have 100 pupils (may need manual adjustment).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Insert placeholder pupils to ensure 100 pupils per stream per class.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python insert_pupils_to_100.py                   # Show dry-run plan
  python insert_pupils_to_100.py --apply           # Apply insertions
  python insert_pupils_to_100.py --apply --verbose # Apply with details
        """
    )
    parser.add_argument('--apply', action='store_true', help='Apply insertions to database.')
    parser.add_argument('--verbose', action='store_true', help='Show detailed insertion info.')
    
    args = parser.parse_args()
    insert_pupils_to_100(apply=args.apply, verbose=args.verbose)
